"""
SISTEMA DE LEVANTAMENTO BIBLIOGRÁFICO - GOOGLE SCHOLAR v5.0
Especializado em busca ampla com palavras-chave combinadas

Características:
- Google Scholar como fonte principal
- Palavras-chave combinadas e alternadas
- Sem limite de artigos (coleta o máximo possível)
- Período: 2020-2026
- Deduplicação robusta
- Múltiplos formatos de exportação
- Sistema de cache para continuidade

Autor: Sistema de Pesquisa Avançado
Data: Abril 2026
"""

import requests
import pandas as pd
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
from pathlib import Path
from abc import ABC, abstractmethod
import pickle
from urllib.parse import quote
import re
from itertools import combinations

# Biblioteca para Google Scholar
try:
    from scholarly import scholarly, ProxyGenerator

    SCHOLARLY_DISPONIVEL = True
except ImportError:
    SCHOLARLY_DISPONIVEL = False
    print("⚠️  Biblioteca 'scholarly' não encontrada.")
    print("   Instale com: pip install scholarly")


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def configurar_logging(nome_arquivo: str = "levantamento_google_scholar.log", nivel=logging.INFO):
    """Configura sistema de logging"""
    logging.basicConfig(
        level=nivel,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(nome_arquivo, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = configurar_logging()


# ============================================================================
# CLASSES E ESTRUTURAS
# ============================================================================

class TipoExportacao(Enum):
    """Formatos de exportação"""
    CSV = "csv"
    JSON = "json"
    BIBTEX = "bibtex"
    XLSX = "xlsx"
    MARKDOWN = "markdown"


@dataclass
class Artigo:
    """Estrutura de um artigo bibliográfico"""
    titulo: str
    autores: List[str]
    ano: int
    veiculo: str
    resumo: str
    link: str
    citacoes: int
    doi: Optional[str] = None
    link_pdf: Optional[str] = None
    fonte: str = "Google Scholar"
    data_coleta: str = None
    palavras_chave_encontradas: List[str] = field(default_factory=list)
    tipo_publicacao: str = "journal"

    def __post_init__(self):
        if self.data_coleta is None:
            self.data_coleta = datetime.now().isoformat()

    def gerar_hash_unico(self) -> str:
        """Hash para deduplicação"""
        titulo_norm = re.sub(r'[^\w\s]', '', self.titulo.lower().strip())
        titulo_norm = re.sub(r'\s+', ' ', titulo_norm)
        texto = f"{titulo_norm}{self.ano}".encode('utf-8')
        return hashlib.md5(texto).hexdigest()

    def para_dict(self) -> Dict:
        """Converte para dicionário"""
        return asdict(self)

    def tem_pdf(self) -> bool:
        """Verifica disponibilidade de PDF"""
        return self.link_pdf is not None and self.link_pdf != ""


# ============================================================================
# GERADOR DE COMBINAÇÕES DE PALAVRAS-CHAVE
# ============================================================================

class GeradorPalavrasChave:
    """Gera combinações estratégicas de palavras-chave"""

    def __init__(self):
        # Palavras-chave originais
        self.palavras = [
            "abandono escolar",
            "Evasão escolar",
            "fatores sociais",
            "ciências da natureza",
            "formação de professores"
        ]

        # Combinações geradas
        self.combinacoes = []
        self._gerar_combinacoes()

    def _gerar_combinacoes(self):
        """Gera todas as combinações possíveis"""
        # Adicionar cada palavra individual
        for palavra in self.palavras:
            self.combinacoes.append(palavra)

        # Adicionar combinações de 2 palavras
        for combo in combinations(range(len(self.palavras)), 2):
            i, j = combo
            termo = f"{self.palavras[i]} AND {self.palavras[j]}"
            self.combinacoes.append(termo)

        # Adicionar algumas combinações de 3 palavras (as mais relevantes)
        combinacoes_3 = [
            (0, 2, 4),  # abandono escolar + fatores sociais + formação de professores
            (1, 2, 3),  # evasão escolar + fatores sociais + ciências da natureza
            (0, 3, 4),  # abandono escolar + ciências da natureza + formação de professores
        ]

        for combo in combinacoes_3:
            termo = f"{self.palavras[combo[0]]} AND {self.palavras[combo[1]]} AND {self.palavras[combo[2]]}"
            self.combinacoes.append(termo)

    def obter_combinacoes(self) -> List[str]:
        """Retorna todas as combinações geradas"""
        return self.combinacoes

    def obter_combinacoes_resumidas(self) -> List[str]:
        """Retorna combinações principais (sem redundância)"""
        # Estratégia: palavras individuais + algumas combinações principais
        resumidas = self.palavras.copy()

        # Adicionar combinações estratégicas
        resumidas.append("abandono escolar AND fatores sociais")
        resumidas.append("evasão escolar AND formação de professores")
        resumidas.append("fatores sociais AND ciências da natureza")

        return resumidas


# ============================================================================
# PROVEDOR GOOGLE SCHOLAR
# ============================================================================

class GoogleScholarAmplo:
    """Busca ampla no Google Scholar sem limite de artigos"""

    def __init__(self, usar_proxy: bool = False, timeout_requisicoes: int = 2):
        """
        Inicializa o provedor

        Args:
            usar_proxy: Se True, tenta usar proxy para evitar bloqueios
            timeout_requisicoes: Segundos de espera entre requisições
        """
        if not SCHOLARLY_DISPONIVEL:
            raise ImportError("Biblioteca 'scholarly' não instalada")

        self.usar_proxy = usar_proxy
        self.timeout = timeout_requisicoes
        self.artigos_encontrados: Dict[str, Artigo] = {}  # Hash -> Artigo

        if self.usar_proxy:
            try:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                logger.info("✓ Proxy configurado")
            except Exception as e:
                logger.warning(f"Não foi possível configurar proxy: {e}")

    def buscar_amplo(self,
                     palavras_chave: List[str],
                     ano_inicio: int = 2020,
                     ano_fim: int = 2026,
                     max_iteracoes_por_termo: int = 100) -> Dict[str, Artigo]:
        """
        Realiza busca ampla com múltiplas palavras-chave

        Args:
            palavras_chave: Lista de termos/combinações para buscar
            ano_inicio: Ano inicial
            ano_fim: Ano final
            max_iteracoes_por_termo: Máximo de iterações por termo (aumenta cobertura)

        Returns:
            Dicionário com artigos encontrados (hash -> Artigo)
        """
        total_inicial = len(self.artigos_encontrados)

        for idx, termo in enumerate(palavras_chave, 1):
            logger.info(f"\n[{idx}/{len(palavras_chave)}] Buscando: '{termo}'")
            self._buscar_termo(termo, ano_inicio, ano_fim, max_iteracoes_por_termo)

            # Progresso
            novos = len(self.artigos_encontrados) - total_inicial
            logger.info(f"    Total até agora: {len(self.artigos_encontrados)} artigos únicos")

        return self.artigos_encontrados

    def _buscar_termo(self,
                      termo: str,
                      ano_inicio: int,
                      ano_fim: int,
                      max_iteracoes: int):
        """Busca um termo específico"""
        coletados_para_termo = 0
        iteracao = 0

        try:
            # Construir query com filtro de ano
            query_com_filtro = f"{termo} ({ano_inicio}:{ano_fim})"

            # Buscar
            search_query = scholarly.search_pubs(query_com_filtro)

            for resultado in search_query:
                if iteracao >= max_iteracoes:
                    logger.info(f"    → {coletados_para_termo} novos artigos para '{termo}'")
                    break

                try:
                    artigo = self._processar_resultado(resultado, termo)

                    # Validar período
                    if ano_inicio <= artigo.ano <= ano_fim:
                        hash_unico = artigo.gerar_hash_unico()

                        if hash_unico not in self.artigos_encontrados:
                            self.artigos_encontrados[hash_unico] = artigo
                            coletados_para_termo += 1

                        if coletados_para_termo % 20 == 0:
                            logger.info(f"    ... {coletados_para_termo} novos artigos")

                    # Delay para evitar bloqueios
                    time.sleep(self.timeout)
                    iteracao += 1

                except Exception as e:
                    logger.debug(f"Erro processando artigo: {e}")
                    iteracao += 1
                    continue

        except Exception as e:
            logger.warning(f"Erro na busca por '{termo}': {e}")

    def _processar_resultado(self, resultado: Dict, termo_busca: str) -> Artigo:
        """Processa um resultado do Google Scholar"""
        bib = resultado.get('bib', {})

        # Extrair informações
        titulo = bib.get('title', 'Sem título')
        autores = bib.get('author', [])
        if isinstance(autores, str):
            autores = [autores]

        # Ano
        try:
            ano = int(bib.get('pub_year', 0))
        except:
            ano = 0

        veiculo = bib.get('venue', 'Desconhecido')
        resumo = resultado.get('abstract', 'Sem resumo disponível')
        citacoes = resultado.get('num_citations', 0)

        # Links
        link = resultado.get('pub_url', resultado.get('url', 'N/A'))
        link_pdf = resultado.get('pdf_url', None)

        # DOI
        doi = bib.get('doi', None)

        return Artigo(
            titulo=titulo,
            autores=autores,
            ano=ano,
            veiculo=veiculo,
            resumo=resumo,
            link=link,
            citacoes=citacoes,
            doi=doi,
            link_pdf=link_pdf,
            palavras_chave_encontradas=[termo_busca]
        )

    def obter_artigos(self) -> List[Artigo]:
        """Retorna lista de artigos únicos"""
        return list(self.artigos_encontrados.values())


# ============================================================================
# SISTEMA COMPLETO DE LEVANTAMENTO
# ============================================================================

class LevantamentoBibliograficoGoogleScholar:
    """Sistema completo para levantamento no Google Scholar"""

    def __init__(self, usar_cache: bool = True, usar_proxy: bool = False):
        """Inicializa o sistema"""
        self.provedor = GoogleScholarAmplo(usar_proxy=usar_proxy)
        self.usar_cache = usar_cache
        self.arquivo_cache = Path("cache_google_scholar.pkl")
        self.historico_buscas = []

        # Carregar cache se disponível
        if self.usar_cache and self.arquivo_cache.exists():
            self._carregar_cache()

    def realizar_levantamento_completo(self,
                                       ano_inicio: int = 2020,
                                       ano_fim: int = 2026,
                                       max_iteracoes_por_termo: int = 100,
                                       usar_combinacoes_completas: bool = False) -> Dict:
        """
        Realiza levantamento completo com todas as combinações de palavras-chave

        Args:
            ano_inicio: Ano inicial
            ano_fim: Ano final
            max_iteracoes_por_termo: Máximo de resultados por termo
            usar_combinacoes_completas: Se True, usa todas as combinações possíveis

        Returns:
            Dicionário com estatísticas do levantamento
        """
        logger.info("\n" + "=" * 70)
        logger.info("🔍 INICIANDO LEVANTAMENTO AMPLO - GOOGLE SCHOLAR")
        logger.info(f"Período: {ano_inicio}-{ano_fim}")
        logger.info("=" * 70)

        # Gerar combinações de palavras-chave
        gerador = GeradorPalavrasChave()

        if usar_combinacoes_completas:
            palavras_chave = gerador.obter_combinacoes()
            logger.info(f"Usando {len(palavras_chave)} combinações completas")
        else:
            palavras_chave = gerador.obter_combinacoes_resumidas()
            logger.info(f"Usando {len(palavras_chave)} combinações estratégicas")

        logger.info(f"\nPalavras-chave a buscar:")
        for idx, termo in enumerate(palavras_chave, 1):
            logger.info(f"  {idx}. {termo}")

        # Realizar busca
        artigos_dict = self.provedor.buscar_amplo(
            palavras_chave=palavras_chave,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            max_iteracoes_por_termo=max_iteracoes_por_termo
        )

        # Registrar no histórico
        self.historico_buscas.append({
            'timestamp': datetime.now().isoformat(),
            'total_artigos': len(artigos_dict),
            'periodo': f"{ano_inicio}-{ano_fim}",
            'combinacoes_usadas': len(palavras_chave)
        })

        # Salvar cache
        if self.usar_cache:
            self._salvar_cache()

        # Retornar estatísticas
        return self._gerar_estatisticas(artigos_dict)

    def _gerar_estatisticas(self, artigos_dict: Dict[str, Artigo]) -> Dict:
        """Gera estatísticas dos artigos coletados"""
        artigos = list(artigos_dict.values())

        if not artigos:
            return {
                'total': 0,
                'periodo': 'N/A',
                'citacoes_totais': 0
            }

        df = pd.DataFrame([a.para_dict() for a in artigos])

        # Estatísticas
        stats = {
            'total': len(artigos),
            'periodo': f"{int(df['ano'].min())}-{int(df['ano'].max())}",
            'anos': df['ano'].unique().size,
            'citacoes_totais': int(df['citacoes'].sum()),
            'citacoes_media': round(df['citacoes'].mean(), 2),
            'citacoes_max': int(df['citacoes'].max()),
            'com_pdf': (df['link_pdf'].notna()).sum(),
            'com_resumo': (df['resumo'] != 'Sem resumo disponível').sum(),
            'artigos_por_ano': df['ano'].value_counts().to_dict(),
            'veiculos_principais': df['veiculo'].value_counts().head(10).to_dict()
        }

        return stats

    def exportar(self,
                 nome_arquivo: str,
                 formato: TipoExportacao = TipoExportacao.CSV):
        """Exporta artigos em diferentes formatos"""
        artigos = self.provedor.obter_artigos()

        if not artigos:
            logger.error("Nenhum artigo para exportar")
            return False

        df = pd.DataFrame([a.para_dict() for a in artigos])

        # Renomear colunas para português
        mapa_colunas = {
            'titulo': 'Título',
            'autores': 'Autores',
            'ano': 'Ano',
            'veiculo': 'Veículo',
            'resumo': 'Resumo',
            'link': 'Link',
            'citacoes': 'Citações',
            'link_pdf': 'Link PDF',
            'doi': 'DOI'
        }
        df = df.rename(columns=mapa_colunas)

        # Ordenar por citações
        df = df.sort_values('Citações', ascending=False)

        # Adicionar timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_base = Path(nome_arquivo).stem
        extensao = Path(nome_arquivo).suffix or f".{formato.value}"
        nome_final = f"{nome_base}_{timestamp}{extensao}"

        try:
            if formato == TipoExportacao.CSV:
                df.to_csv(nome_final, index=False, encoding='utf-8-sig')
                logger.info(f"✓ CSV exportado: {nome_final} ({len(df)} artigos)")

            elif formato == TipoExportacao.XLSX:
                with pd.ExcelWriter(nome_final, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Artigos', index=False)
                logger.info(f"✓ XLSX exportado: {nome_final}")

            elif formato == TipoExportacao.JSON:
                dados_json = {
                    'metadata': {
                        'data': datetime.now().isoformat(),
                        'total_artigos': len(df),
                        'fonte': 'Google Scholar'
                    },
                    'artigos': [a.para_dict() for a in artigos]
                }
                with open(nome_final, 'w', encoding='utf-8') as f:
                    json.dump(dados_json, f, indent=2, ensure_ascii=False)
                logger.info(f"✓ JSON exportado: {nome_final}")

            elif formato == TipoExportacao.BIBTEX:
                self._exportar_bibtex(df, nome_final)
                logger.info(f"✓ BibTeX exportado: {nome_final}")

            elif formato == TipoExportacao.MARKDOWN:
                self._exportar_markdown(df, nome_final)
                logger.info(f"✓ Markdown exportado: {nome_final}")

            return True

        except Exception as e:
            logger.error(f"Erro ao exportar: {e}")
            return False

    def _exportar_bibtex(self, df: pd.DataFrame, nome_arquivo: str):
        """Exporta em formato BibTeX"""
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            for idx, (_, row) in enumerate(df.iterrows(), 1):
                primeiro_autor = str(row['Autores']).split(',')[0].split()[-1] if row['Autores'] else 'Unknown'
                chave = f"{primeiro_autor}{row['Ano']}{idx}".replace(' ', '')

                f.write(f"@article{{{chave},\n")
                f.write(f"  title={{{row['Título']}}},\n")
                f.write(f"  author={{{row['Autores']}}},\n")
                f.write(f"  year={{{row['Ano']}}},\n")
                f.write(f"  journal={{{row['Veículo']}}},\n")

                if pd.notna(row['DOI']):
                    f.write(f"  doi={{{row['DOI']}}},\n")

                f.write(f"  url={{{row['Link']}}}\n")
                f.write("}\n\n")

    def _exportar_markdown(self, df: pd.DataFrame, nome_arquivo: str):
        """Exporta em formato Markdown"""
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write("# Levantamento Bibliográfico - Google Scholar\n\n")
            f.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"**Total de artigos:** {len(df)}\n\n")

            for idx, (_, row) in enumerate(df.iterrows(), 1):
                f.write(f"## {idx}. {row['Título']}\n\n")
                f.write(f"- **Autores:** {row['Autores']}\n")
                f.write(f"- **Ano:** {row['Ano']}\n")
                f.write(f"- **Veículo:** {row['Veículo']}\n")
                f.write(f"- **Citações:** {row['Citações']}\n")

                if pd.notna(row['Link PDF']) and row['Link PDF'] != 'None':
                    f.write(f"- **PDF:** [{row['Link PDF']}]({row['Link PDF']})\n")

                f.write(f"- **Link:** [{row['Link']}]({row['Link']})\n\n")
                f.write(f"**Resumo:** {row['Resumo']}\n\n")
                f.write("---\n\n")

    def visualizar_top_artigos(self, limite: int = 20):
        """Exibe top N artigos mais citados"""
        artigos = self.provedor.obter_artigos()

        if not artigos:
            logger.info("Nenhum artigo para exibir")
            return

        # Ordenar por citações
        artigos_ord = sorted(artigos, key=lambda x: x.citacoes, reverse=True)

        logger.info(f"\n{'=' * 70}")
        logger.info(f"TOP {limite} ARTIGOS MAIS CITADOS")
        logger.info(f"{'=' * 70}\n")

        for idx, artigo in enumerate(artigos_ord[:limite], 1):
            logger.info(f"{idx}. {artigo.titulo[:70]}")
            logger.info(f"   Autores: {', '.join(artigo.autores[:3])}")
            logger.info(f"   Ano: {artigo.ano} | Citações: {artigo.citacoes}")
            logger.info(f"   Veículo: {artigo.veiculo}")

            if artigo.tem_pdf():
                logger.info(f"   PDF: Disponível")

            logger.info(f"   Link: {artigo.link}\n")

    def _salvar_cache(self):
        """Salva cache local"""
        try:
            cache_data = {
                'artigos': self.provedor.artigos_encontrados,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.arquivo_cache, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.info(f"✓ Cache salvo com {len(self.provedor.artigos_encontrados)} artigos")
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")

    def _carregar_cache(self):
        """Carrega cache local"""
        try:
            with open(self.arquivo_cache, 'rb') as f:
                cache_data = pickle.load(f)
            self.provedor.artigos_encontrados = cache_data.get('artigos', {})
            logger.info(f"✓ Cache carregado: {len(self.provedor.artigos_encontrados)} artigos")
        except Exception as e:
            logger.warning(f"Erro ao carregar cache: {e}")

    def limpar_cache(self):
        """Limpa cache"""
        try:
            if self.arquivo_cache.exists():
                self.arquivo_cache.unlink()
            self.provedor.artigos_encontrados.clear()
            logger.info("✓ Cache limpo")
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")


# ============================================================================
# INTERFACE SIMPLIFICADA
# ============================================================================

class AssistenteGoogleScholar:
    """Interface simplificada para levantamento no Google Scholar"""

    def __init__(self, usar_cache: bool = True, usar_proxy: bool = False):
        """Inicializa o assistente"""
        print("\n🎓 Assistente Google Scholar v1.0")
        print("=" * 70)

        try:
            self.sistema = LevantamentoBibliograficoGoogleScholar(
                usar_cache=usar_cache,
                usar_proxy=usar_proxy
            )
            print("✓ Sistema inicializado com sucesso")
            print("✓ Cache habilitado" if usar_cache else "⚠️  Cache desabilitado")
            print("✓ Proxy habilitado" if usar_proxy else "⚠️  Proxy desabilitado")
        except ImportError as e:
            print(f"❌ Erro: {e}")
            raise

        print("=" * 70 + "\n")

    def buscar_amplo(self,
                     ano_inicio: int = 2020,
                     ano_fim: int = 2026,
                     max_por_termo: int = 100,
                     completo: bool = False) -> Dict:
        """Realiza busca ampla"""
        return self.sistema.realizar_levantamento_completo(
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            max_iteracoes_por_termo=max_por_termo,
            usar_combinacoes_completas=completo
        )

    def exportar(self, formato: str = 'csv'):
        """Exporta resultados"""
        mapa_formatos = {
            'csv': TipoExportacao.CSV,
            'json': TipoExportacao.JSON,
            'bibtex': TipoExportacao.BIBTEX,
            'xlsx': TipoExportacao.XLSX,
            'markdown': TipoExportacao.MARKDOWN
        }

        if formato not in mapa_formatos:
            logger.error(f"Formato inválido: {formato}")
            return

        tipo = mapa_formatos[formato]
        nome_base = f"levantamento_google_scholar"
        extensao = f".{formato}"

        self.sistema.exportar(nome_base, tipo)

    def mostrar_top(self, limite: int = 20):
        """Mostra top artigos"""
        self.sistema.visualizar_top_artigos(limite)

    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas"""
        artigos = self.sistema.provedor.obter_artigos()

        if not artigos:
            return {'total': 0}

        df = pd.DataFrame([a.para_dict() for a in artigos])

        print("\n" + "=" * 70)
        print("📊 ESTATÍSTICAS DO LEVANTAMENTO")
        print("=" * 70)
        print(f"Total de artigos: {len(df)}")
        print(f"Período coberto: {int(df['ano'].min())}-{int(df['ano'].max())}")
        print(f"Citações totais: {int(df['citacoes'].sum())}")
        print(f"Citações médias: {df['citacoes'].mean():.1f}")
        print(f"Artigos com PDF: {(df['link_pdf'].notna()).sum()}")
        print(f"Artigos com resumo: {(df['resumo'] != 'Sem resumo disponível').sum()}")
        print("=" * 70 + "\n")

        return df


# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == "__main__":

    if not SCHOLARLY_DISPONIVEL:
        print("\n❌ ERRO: Biblioteca 'scholarly' não encontrada!")
        print("Instale com: pip install scholarly")
        exit(1)

    print("\n" + "=" * 70)
    print("🔍 LEVANTAMENTO BIBLIOGRÁFICO - GOOGLE SCHOLAR v5.0")
    print("=" * 70)
    print("\nPalavras-chave:")
    print("  • abandono escolar")
    print("  • Evasão escolar")
    print("  • fatores sociais")
    print("  • ciências da natureza")
    print("  • formação de professores")
    print("\nPeríodo: 2020-2026")
    print("Sem limite de artigos (busca ampla)\n")

    # Criar assistente
    assistente = AssistenteGoogleScholar(usar_cache=True, usar_proxy=False)

    # ========== BUSCA AMPLA ==========
    print("📚 Iniciando levantamento amplo...\n")

    stats = assistente.buscar_amplo(
        ano_inicio=2020,
        ano_fim=2026,
        max_por_termo=100,  # Máximo por combinação
        completo=False  # False = combinações estratégicas; True = todas
    )

    print(f"\n✓ Levantamento concluído!")
    print(f"  Total de artigos únicos: {stats.get('total', 0)}")
    print(f"  Período: {stats.get('periodo', 'N/A')}")
    print(f"  Citações totais: {stats.get('citacoes_totais', 0)}")

    # ========== EXIBIR TOP ARTIGOS ==========
    print("\n" + "=" * 70)
    assistente.mostrar_top(limite=15)

    # ========== ESTATÍSTICAS ==========
    df = assistente.obter_estatisticas()

    # ========== EXPORTAR ==========
    print("💾 Exportando em múltiplos formatos...\n")

    assistente.exportar('csv')
    assistente.exportar('json')
    assistente.exportar('bibtex')
    assistente.exportar('xlsx')
    assistente.exportar('markdown')

    print("\n✅ LEVANTAMENTO CONCLUÍDO COM SUCESSO!")
    print("\nArquivos gerados:")
    print("  📊 levantamento_google_scholar_*.csv")
    print("  📄 levantamento_google_scholar_*.json")
    print("  📚 levantamento_google_scholar_*.bib")
    print("  📋 levantamento_google_scholar_*.xlsx")
    print("  📝 levantamento_google_scholar_*.md")
    print("  💾 cache_google_scholar.pkl (para reusar depois)")
    print()