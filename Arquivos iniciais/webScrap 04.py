"""
SISTEMA DE LEVANTAMENTO BIBLIOGRÁFICO AVANÇADO v4.0
Para pesquisas científicas

Melhorias principais:
- Integração completa com Google Scholar
- Interface simplificada para facilitar o uso
- Foco em links para PDFs
- Visualização aprimorada dos resultados
- Correções de bugs e otimizações

Autor: Sistema de Pesquisa (Versão Melhorada)
"""

import requests
import pandas as pd
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
from pathlib import Path
from abc import ABC, abstractmethod
import pickle
from urllib.parse import quote
import re

# Biblioteca para Google Scholar
try:
    from scholarly import scholarly, ProxyGenerator

    SCHOLARLY_DISPONIVEL = True
except ImportError:
    SCHOLARLY_DISPONIVEL = False
    print("⚠️  Biblioteca 'scholarly' não encontrada. Instale com: pip install scholarly")


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def configurar_logging(nome_arquivo: str = "levantamento_bibliografico.log", nivel=logging.INFO):
    """Configura sistema de logging para rastrear todas as operações"""
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
# ENUMERAÇÕES E CLASSES BASE
# ============================================================================

class FonteDados(Enum):
    """Fontes de dados disponíveis"""
    GOOGLE_SCHOLAR = "google_scholar"
    OPENALEX = "openalex"
    CROSSREF = "crossref"


class TipoExportacao(Enum):
    """Formatos de exportação disponíveis"""
    CSV = "csv"
    JSON = "json"
    BIBTEX = "bibtex"
    XLSX = "xlsx"
    MARKDOWN = "markdown"


@dataclass
class Artigo:
    """Classe que representa um artigo bibliográfico"""
    titulo: str
    autores: List[str]
    ano: int
    veiculo: str
    resumo: str
    link: str
    citacoes: int
    doi: Optional[str] = None
    link_pdf: Optional[str] = None
    fonte: str = "desconhecida"
    data_coleta: str = None
    palavras_chave: List[str] = field(default_factory=list)
    tipo_publicacao: str = "journal"
    idioma: Optional[str] = None

    def __post_init__(self):
        if self.data_coleta is None:
            self.data_coleta = datetime.now().isoformat()

    def gerar_hash_unico(self) -> str:
        """Gera hash único para identificar duplicatas"""
        # Normalizar título: remover acentos, pontuação, espaços extras
        titulo_normalizado = self.titulo.lower().strip()
        titulo_normalizado = re.sub(r'[^\w\s]', '', titulo_normalizado)
        titulo_normalizado = re.sub(r'\s+', ' ', titulo_normalizado)

        texto = f"{titulo_normalizado}{self.ano}".encode('utf-8')
        return hashlib.md5(texto).hexdigest()

    def para_dict(self) -> Dict:
        """Converte artigo para dicionário"""
        return asdict(self)

    def tem_pdf_disponivel(self) -> bool:
        """Verifica se há link para PDF disponível"""
        return self.link_pdf is not None and self.link_pdf != ""


# ============================================================================
# CLASSE BASE PARA PROVEDORES DE DADOS
# ============================================================================

class ProvedorDados(ABC):
    """Classe abstrata para provedores de dados bibliográficos"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    @abstractmethod
    def buscar(self, query: str, ano_inicio: int, ano_fim: int,
               limite: int) -> List[Artigo]:
        """Método abstrato para busca"""
        pass

    def _validar_resposta(self, response: requests.Response) -> Dict:
        """Valida resposta HTTP"""
        if response.status_code != 200:
            logger.warning(f"Status code {response.status_code}: {response.text[:100]}")
            return {}
        try:
            return response.json()
        except:
            return {}


# ============================================================================
# IMPLEMENTAÇÃO GOOGLE SCHOLAR
# ============================================================================

class GoogleScholarProvider(ProvedorDados):
    """Provedor de dados usando Google Scholar (via scholarly)"""

    def __init__(self, usar_proxy: bool = False):
        super().__init__()
        self.usar_proxy = usar_proxy

        if not SCHOLARLY_DISPONIVEL:
            raise ImportError("Biblioteca 'scholarly' não instalada")

        # Configurar proxy se solicitado (evita bloqueios)
        if usar_proxy:
            try:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                logger.info("✓ Google Scholar: proxy configurado")
            except Exception as e:
                logger.warning(f"Não foi possível configurar proxy: {e}")

    def buscar(self, query: str, ano_inicio: int, ano_fim: int,
               limite: int = 50) -> List[Artigo]:
        """
        Busca em Google Scholar com filtros de ano

        Args:
            query: Termo de busca
            ano_inicio: Ano inicial (inclusive)
            ano_fim: Ano final (inclusive)
            limite: Número máximo de resultados

        Returns:
            Lista de objetos Artigo
        """
        artigos = []
        coletados = 0

        try:
            logger.info(f"Google Scholar: Buscando '{query}' ({ano_inicio}-{ano_fim})")

            # Configurar busca com filtro de ano
            search_query = scholarly.search_pubs(query, year_low=ano_inicio, year_high=ano_fim)

            for resultado in search_query:
                if coletados >= limite:
                    break

                try:
                    artigo = self._processar_resultado_scholar(resultado)

                    # Filtrar por ano (validação adicional)
                    if ano_inicio <= artigo.ano <= ano_fim:
                        artigos.append(artigo)
                        coletados += 1

                        if coletados % 10 == 0:
                            logger.info(f"  → {coletados} artigos coletados...")

                    # Delay para evitar bloqueios
                    time.sleep(2)

                except Exception as e:
                    logger.warning(f"Erro ao processar resultado Scholar: {e}")
                    continue

            logger.info(f"✓ Google Scholar: {coletados} artigos coletados")

        except Exception as e:
            logger.error(f"Erro na busca Google Scholar: {e}")
            logger.info("Dica: Se houver bloqueio, tente usar_proxy=True ou aguarde alguns minutos")

        return artigos

    def _processar_resultado_scholar(self, resultado: Dict) -> Artigo:
        """Processa um resultado do Google Scholar"""

        # Extrair informações básicas
        titulo = resultado.get('bib', {}).get('title', 'Sem título')
        autores = resultado.get('bib', {}).get('author', ['Autor desconhecido'])
        if isinstance(autores, str):
            autores = [autores]

        # Ano de publicação
        ano = 0
        pub_year = resultado.get('bib', {}).get('pub_year')
        if pub_year:
            try:
                ano = int(pub_year)
            except:
                pass

        # Veículo de publicação
        veiculo = resultado.get('bib', {}).get('venue', 'N/A')
        if not veiculo:
            veiculo = resultado.get('bib', {}).get('journal', 'N/A')
        if not veiculo or veiculo == 'N/A':
            veiculo = resultado.get('bib', {}).get('publisher', 'N/A')

        # Resumo
        resumo = resultado.get('bib', {}).get('abstract', 'Resumo não disponível')

        # Links
        link = resultado.get('pub_url', resultado.get('eprint_url', 'N/A'))
        link_pdf = resultado.get('eprint_url', None)

        # Citações
        citacoes = resultado.get('num_citations', 0)

        return Artigo(
            titulo=titulo,
            autores=autores,
            ano=ano,
            veiculo=veiculo,
            resumo=resumo,
            link=link,
            link_pdf=link_pdf,
            citacoes=citacoes,
            fonte='Google Scholar',
            tipo_publicacao='journal'
        )


# ============================================================================
# IMPLEMENTAÇÃO OPENALEX (CORRIGIDA)
# ============================================================================

class OpenAlexProvider(ProvedorDados):
    """Provedor de dados usando OpenAlex API (versão corrigida)"""

    BASE_URL = "https://api.openalex.org/works"

    def buscar(self, query: str, ano_inicio: int, ano_fim: int,
               limite: int = 100) -> List[Artigo]:
        """Busca em OpenAlex com filtros de ano"""
        artigos = []
        pagina = 1
        coletados = 0

        while coletados < limite:
            try:
                # Filtro de ano corrigido
                filtro_ano = f"publication_year:{ano_inicio}-{ano_fim}"

                params = {
                    'search': query,
                    'filter': filtro_ano,
                    'per-page': min(50, limite - coletados),
                    'page': pagina,
                    'sort': 'cited_by_count:desc'
                }

                logger.info(f"OpenAlex - Página {pagina}: {query}")
                response = self.session.get(self.BASE_URL, params=params,
                                            timeout=self.timeout)
                dados = self._validar_resposta(response)

                if not dados or 'results' not in dados or not dados['results']:
                    break

                for resultado in dados['results']:
                    if coletados >= limite:
                        break

                    try:
                        artigo = self._processar_resultado_openalex(resultado)
                        artigos.append(artigo)
                        coletados += 1
                    except Exception as e:
                        logger.warning(f"Erro ao processar resultado OpenAlex: {e}")
                        continue

                pagina += 1
                time.sleep(1)

            except Exception as e:
                logger.error(f"Erro na busca OpenAlex: {e}")
                break

        logger.info(f"✓ OpenAlex: {coletados} artigos coletados")
        return artigos

    def _processar_resultado_openalex(self, resultado: Dict) -> Artigo:
        """Processa um resultado do OpenAlex (CORRIGIDO)"""

        # Autores
        autores = [
            autor.get('author', {}).get('display_name', 'Anônimo')
            for autor in resultado.get('authorships', [])[:10]
        ]

        # Veículo (CORRIGIDO - usar primary_location)
        veiculo = 'N/A'
        primary_location = resultado.get('primary_location', {})
        if primary_location:
            source = primary_location.get('source', {})
            if source:
                veiculo = source.get('display_name', 'N/A')

        # Link para PDF (tentar obter)
        link_pdf = None
        if primary_location:
            link_pdf = primary_location.get('pdf_url')

        # Link principal
        link = resultado.get('doi', '') or resultado.get('id', 'N/A')

        # Resumo (abstract_inverted_index precisa ser processado)
        resumo = 'Resumo não disponível'
        abstract_inverted = resultado.get('abstract_inverted_index')
        if abstract_inverted:
            try:
                # Reconstruir resumo a partir do índice invertido
                palavras = [(word, min(positions)) for word, positions in abstract_inverted.items()]
                palavras.sort(key=lambda x: x[1])
                resumo = ' '.join([palavra for palavra, _ in palavras])
            except:
                pass

        return Artigo(
            titulo=resultado.get('title', 'Sem título'),
            autores=autores,
            ano=resultado.get('publication_year', 0),
            veiculo=veiculo,
            resumo=resumo,
            link=link,
            link_pdf=link_pdf,
            citacoes=resultado.get('cited_by_count', 0),
            doi=resultado.get('doi'),
            fonte='OpenAlex',
            tipo_publicacao=resultado.get('type', 'journal')
        )


# ============================================================================
# IMPLEMENTAÇÃO CROSSREF (MANTIDA)
# ============================================================================

class CrossRefProvider(ProvedorDados):
    """Provedor de dados usando CrossRef API"""

    BASE_URL = "https://api.crossref.org/works"

    def buscar(self, query: str, ano_inicio: int, ano_fim: int,
               limite: int = 100) -> List[Artigo]:
        """Busca em CrossRef com filtros de ano"""
        artigos = []
        pagina = 0
        coletados = 0

        while coletados < limite:
            try:
                params = {
                    'query': query,
                    'filter': f'from-pub-date:{ano_inicio},until-pub-date:{ano_fim}',
                    'rows': min(100, limite - coletados),
                    'offset': pagina * 100,
                    'sort': 'is-referenced-by-count',
                    'order': 'desc'
                }

                logger.info(f"CrossRef - Offset {pagina * 100}: {query}")
                response = self.session.get(self.BASE_URL, params=params,
                                            timeout=self.timeout)
                dados = self._validar_resposta(response)

                if not dados or 'message' not in dados or not dados['message'].get('items'):
                    break

                for resultado in dados['message']['items']:
                    if coletados >= limite:
                        break

                    try:
                        artigo = self._processar_resultado_crossref(resultado)
                        artigos.append(artigo)
                        coletados += 1
                    except Exception as e:
                        logger.warning(f"Erro ao processar resultado CrossRef: {e}")
                        continue

                pagina += 1
                time.sleep(1)

            except Exception as e:
                logger.error(f"Erro na busca CrossRef: {e}")
                break

        logger.info(f"✓ CrossRef: {coletados} artigos coletados")
        return artigos

    def _processar_resultado_crossref(self, resultado: Dict) -> Artigo:
        """Processa um resultado do CrossRef"""
        autores = [
            f"{autor.get('given', '')} {autor.get('family', '')}".strip()
            for autor in resultado.get('author', [])[:10]
        ]

        # Extrair ano
        ano = 0
        if 'published' in resultado and 'date-parts' in resultado['published']:
            ano = resultado['published']['date-parts'][0][0]
        elif 'issued' in resultado and 'date-parts' in resultado['issued']:
            ano = resultado['issued']['date-parts'][0][0]

        # Link para PDF (tentar obter)
        link_pdf = None
        for link_obj in resultado.get('link', []):
            if 'application/pdf' in link_obj.get('content-type', ''):
                link_pdf = link_obj.get('URL')
                break

        return Artigo(
            titulo=resultado.get('title', ['Sem título'])[0],
            autores=autores,
            ano=ano,
            veiculo=resultado.get('container-title', ['N/A'])[0],
            resumo=resultado.get('abstract', 'Resumo não disponível'),
            link=resultado.get('URL', 'N/A'),
            link_pdf=link_pdf,
            citacoes=resultado.get('is-referenced-by-count', 0),
            doi=resultado.get('DOI'),
            fonte='CrossRef',
            tipo_publicacao=resultado.get('type', 'journal')
        )


# ============================================================================
# CLASSE PRINCIPAL - LEVANTAMENTO BIBLIOGRÁFICO
# ============================================================================

class LevantamentoBibliografico:
    """Sistema completo de levantamento bibliográfico"""

    def __init__(self, usar_cache: bool = True):
        self.artigos: Dict[str, Artigo] = {}
        self.usar_cache = usar_cache
        self.arquivo_cache = Path("cache_artigos.pkl")
        self.historico_buscas = []

        # Inicializar provedores
        self.provedores = {}

        # OpenAlex e CrossRef sempre disponíveis
        self.provedores[FonteDados.OPENALEX] = OpenAlexProvider()
        self.provedores[FonteDados.CROSSREF] = CrossRefProvider()

        # Google Scholar se disponível
        if SCHOLARLY_DISPONIVEL:
            try:
                self.provedores[FonteDados.GOOGLE_SCHOLAR] = GoogleScholarProvider()
                logger.info("✓ Google Scholar disponível")
            except Exception as e:
                logger.warning(f"Google Scholar não pôde ser inicializado: {e}")

        # Carregar cache
        if self.usar_cache and self.arquivo_cache.exists():
            self._carregar_cache()

    def buscar_multiplas_fontes(self,
                                termo: str,
                                ano_inicio: int,
                                ano_fim: int,
                                limite_por_fonte: int = 50,
                                fontes: Optional[List[FonteDados]] = None,
                                priorizar_pdf: bool = True) -> int:
        """
        Realiza buscas em múltiplas fontes

        Args:
            termo: Termo de busca (palavras-chave)
            ano_inicio: Ano inicial
            ano_fim: Ano final
            limite_por_fonte: Número máximo de artigos por fonte
            fontes: Lista de fontes (default: todas disponíveis)
            priorizar_pdf: Priorizar artigos com PDF disponível

        Returns:
            Número de artigos únicos adicionados
        """
        if fontes is None:
            fontes = list(self.provedores.keys())

        if ano_inicio > ano_fim:
            raise ValueError("ano_inicio não pode ser maior que ano_fim")

        logger.info(f"\n{'=' * 70}")
        logger.info(f"BUSCA: '{termo}' | Período: {ano_inicio}-{ano_fim}")
        logger.info(f"Fontes: {[f.value for f in fontes]}")
        logger.info(f"{'=' * 70}\n")

        artigos_antes = len(self.artigos)

        # Buscar em cada fonte
        for fonte in fontes:
            if fonte not in self.provedores:
                logger.warning(f"❌ Fonte {fonte.value} não disponível")
                continue

            try:
                provedor = self.provedores[fonte]
                novos_artigos = provedor.buscar(
                    query=termo,
                    ano_inicio=ano_inicio,
                    ano_fim=ano_fim,
                    limite=limite_por_fonte
                )

                # Adicionar artigos únicos
                for artigo in novos_artigos:
                    hash_unico = artigo.gerar_hash_unico()
                    if hash_unico not in self.artigos:
                        self.artigos[hash_unico] = artigo
                    else:
                        # Se já existe, atualizar informações se necessário
                        artigo_existente = self.artigos[hash_unico]
                        # Atualizar link PDF se o novo tem e o antigo não
                        if artigo.link_pdf and not artigo_existente.link_pdf:
                            artigo_existente.link_pdf = artigo.link_pdf
                        # Manter o maior número de citações
                        if artigo.citacoes > artigo_existente.citacoes:
                            artigo_existente.citacoes = artigo.citacoes

            except Exception as e:
                logger.error(f"❌ Erro ao buscar em {fonte.value}: {e}")

        artigos_adicionados = len(self.artigos) - artigos_antes

        # Registrar busca
        self.historico_buscas.append({
            'termo': termo,
            'ano_inicio': ano_inicio,
            'ano_fim': ano_fim,
            'timestamp': datetime.now().isoformat(),
            'artigos_adicionados': artigos_adicionados,
            'total_acumulado': len(self.artigos)
        })

        logger.info(f"\n✓ {artigos_adicionados} artigos únicos adicionados")
        logger.info(f"📚 Total acumulado: {len(self.artigos)} artigos\n")

        # Salvar cache automaticamente
        if self.usar_cache:
            self._salvar_cache()

        return artigos_adicionados

    def visualizar_resultados(self,
                              limite: int = 20,
                              ordenar_por: str = 'citacoes',
                              mostrar_resumo: bool = False) -> pd.DataFrame:
        """
        Visualiza resultados de forma formatada

        Args:
            limite: Número máximo de artigos a exibir
            ordenar_por: 'citacoes', 'ano', 'titulo'
            mostrar_resumo: Se deve mostrar resumo completo

        Returns:
            DataFrame com os resultados
        """
        df = self._artigos_para_dataframe()

        if df.empty:
            print("\n⚠️  Nenhum artigo encontrado ainda.\n")
            return df

        # Ordenar
        if ordenar_por == 'citacoes':
            df = df.sort_values(['Citações', 'Ano'], ascending=[False, False])
        elif ordenar_por == 'ano':
            df = df.sort_values(['Ano', 'Citações'], ascending=[False, False])
        elif ordenar_por == 'titulo':
            df = df.sort_values('Título')

        # Limitar
        df_exibir = df.head(limite).copy()

        # Exibir de forma formatada
        print(f"\n{'=' * 100}")
        print(f"📚 RESULTADOS DO LEVANTAMENTO BIBLIOGRÁFICO")
        print(f"{'=' * 100}")
        print(f"Total de artigos: {len(df)} | Exibindo: {len(df_exibir)}")
        print(f"{'=' * 100}\n")

        for idx, (_, row) in enumerate(df_exibir.iterrows(), 1):
            print(f"[{idx}] {row['Título']}")
            print(f"    📅 Ano: {row['Ano']} | 📊 Citações: {row['Citações']} | 🏛️ Fonte: {row['Fonte']}")
            print(f"    ✍️  Autores: {', '.join(row['Autores'][:3])}" +
                  (" et al." if len(row['Autores']) > 3 else ""))
            print(f"    📖 Veículo: {row['Veículo']}")

            # Link para PDF
            if row['Link PDF'] and row['Link PDF'] != 'None':
                print(f"    📄 PDF: {row['Link PDF']}")
            else:
                print(f"    🔗 Link: {row['Link']}")

            if mostrar_resumo and row['Resumo'] != 'Resumo não disponível':
                resumo_curto = row['Resumo'][:200] + "..." if len(row['Resumo']) > 200 else row['Resumo']
                print(f"    💡 {resumo_curto}")

            print()

        return df_exibir

    def filtrar_artigos(self,
                        citacoes_minimas: int = 0,
                        ano_inicio: Optional[int] = None,
                        ano_fim: Optional[int] = None,
                        com_pdf: bool = False,
                        palavras_no_titulo: Optional[List[str]] = None) -> pd.DataFrame:
        """Filtra artigos conforme critérios"""
        df = self._artigos_para_dataframe()

        if df.empty:
            return df

        # Filtros
        if citacoes_minimas > 0:
            df = df[df['Citações'] >= citacoes_minimas]

        if ano_inicio:
            df = df[df['Ano'] >= ano_inicio]
        if ano_fim:
            df = df[df['Ano'] <= ano_fim]

        if com_pdf:
            df = df[df['Link PDF'] != 'None']

        if palavras_no_titulo:
            mask = df['Título'].str.lower().str.contains(
                '|'.join(palavras_no_titulo),
                case=False,
                na=False
            )
            df = df[mask]

        logger.info(f"Filtros aplicados: {len(df)} artigos restantes")
        return df

    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas detalhadas"""
        if not self.artigos:
            return {}

        df = self._artigos_para_dataframe()

        stats = {
            'Total de Artigos': len(df),
            'Período': f"{int(df['Ano'].min())}-{int(df['Ano'].max())}",
            'Citações Totais': int(df['Citações'].sum()),
            'Citações Médias': round(df['Citações'].mean(), 2),
            'Artigos com PDF': int((df['Link PDF'] != 'None').sum()),
            'Artigos com DOI': int((df['DOI'] != 'None').sum()),
            'Fontes de Dados': df['Fonte'].unique().tolist(),
            'Distribuição por Ano': df.groupby('Ano').size().to_dict(),
            'Top 5 Mais Citados': df.nlargest(5, 'Citações')[['Título', 'Citações']].to_dict('records')
        }

        return stats

    def _artigos_para_dataframe(self) -> pd.DataFrame:
        """Converte artigos para DataFrame"""
        if not self.artigos:
            return pd.DataFrame()

        dados = [artigo.para_dict() for artigo in self.artigos.values()]
        df = pd.DataFrame(dados)

        # Filtrar anos válidos
        df = df[df['ano'] > 0].copy()

        # Renomear colunas
        mapeamento = {
            'titulo': 'Título',
            'autores': 'Autores',
            'ano': 'Ano',
            'veiculo': 'Veículo',
            'resumo': 'Resumo',
            'link': 'Link',
            'link_pdf': 'Link PDF',
            'citacoes': 'Citações',
            'doi': 'DOI',
            'fonte': 'Fonte',
            'tipo_publicacao': 'Tipo'
        }
        df = df.rename(columns=mapeamento)

        # Converter None para string
        df['Link PDF'] = df['Link PDF'].astype(str)
        df['DOI'] = df['DOI'].astype(str)

        return df

    def exportar(self,
                 nome_arquivo: str,
                 formato: TipoExportacao = TipoExportacao.CSV) -> bool:
        """Exporta resultados"""
        try:
            df = self._artigos_para_dataframe()

            if df.empty:
                logger.error("Nenhum artigo para exportar")
                return False

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = Path(nome_arquivo).stem

            if formato == TipoExportacao.CSV:
                nome_final = f"{nome_base}_{timestamp}.csv"
                df.to_csv(nome_final, index=False, encoding='utf-8-sig')
                logger.info(f"✓ Exportado CSV: {nome_final}")

            elif formato == TipoExportacao.XLSX:
                nome_final = f"{nome_base}_{timestamp}.xlsx"
                with pd.ExcelWriter(nome_final, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Artigos', index=False)
                logger.info(f"✓ Exportado XLSX: {nome_final}")

            elif formato == TipoExportacao.JSON:
                nome_final = f"{nome_base}_{timestamp}.json"
                dados = {
                    'metadata': self.obter_estatisticas(),
                    'artigos': [a.para_dict() for a in self.artigos.values()]
                }
                with open(nome_final, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False)
                logger.info(f"✓ Exportado JSON: {nome_final}")

            elif formato == TipoExportacao.BIBTEX:
                nome_final = f"{nome_base}_{timestamp}.bib"
                self._exportar_bibtex(nome_final, df)
                logger.info(f"✓ Exportado BibTeX: {nome_final}")

            elif formato == TipoExportacao.MARKDOWN:
                nome_final = f"{nome_base}_{timestamp}.md"
                self._exportar_markdown(nome_final, df)
                logger.info(f"✓ Exportado Markdown: {nome_final}")

            return True

        except Exception as e:
            logger.error(f"Erro ao exportar: {e}")
            return False

    def _exportar_bibtex(self, nome_arquivo: str, df: pd.DataFrame):
        """Exporta em formato BibTeX"""
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            for idx, (_, row) in enumerate(df.iterrows(), 1):
                primeiro_autor = row['Autores'][0].split()[-1] if row['Autores'] else 'Unknown'
                chave = f"{primeiro_autor}{row['Ano']}{idx}".replace(' ', '')

                f.write(f"@article{{{chave},\n")
                f.write(f"  title={{{row['Título']}}},\n")
                f.write(f"  author={{{', '.join(row['Autores'])}}},\n")
                f.write(f"  year={{{row['Ano']}}},\n")
                f.write(f"  journal={{{row['Veículo']}}},\n")
                if row['DOI'] != 'None':
                    f.write(f"  doi={{{row['DOI']}}},\n")
                f.write(f"  url={{{row['Link']}}}\n")
                f.write("}\n\n")

    def _exportar_markdown(self, nome_arquivo: str, df: pd.DataFrame):
        """Exporta em formato Markdown"""
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write("# Levantamento Bibliográfico\n\n")
            f.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}\n\n")
            f.write(f"**Total de artigos:** {len(df)}\n\n")

            f.write("## Artigos\n\n")
            for idx, (_, row) in enumerate(df.iterrows(), 1):
                f.write(f"### {idx}. {row['Título']}\n\n")
                f.write(f"- **Autores:** {', '.join(row['Autores'])}\n")
                f.write(f"- **Ano:** {row['Ano']}\n")
                f.write(f"- **Veículo:** {row['Veículo']}\n")
                f.write(f"- **Citações:** {row['Citações']}\n")
                if row['Link PDF'] != 'None':
                    f.write(f"- **PDF:** [{row['Link PDF']}]({row['Link PDF']})\n")
                f.write(f"- **Link:** [{row['Link']}]({row['Link']})\n")
                f.write(f"\n**Resumo:** {row['Resumo']}\n\n")
                f.write("---\n\n")

    def _salvar_cache(self):
        """Salva cache"""
        try:
            with open(self.arquivo_cache, 'wb') as f:
                pickle.dump(self.artigos, f)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")

    def _carregar_cache(self):
        """Carrega cache"""
        try:
            with open(self.arquivo_cache, 'rb') as f:
                self.artigos = pickle.load(f)
            logger.info(f"✓ Cache carregado: {len(self.artigos)} artigos")
        except Exception as e:
            logger.warning(f"Erro ao carregar cache: {e}")

    def limpar_cache(self):
        """Limpa cache"""
        try:
            if self.arquivo_cache.exists():
                self.arquivo_cache.unlink()
            self.artigos.clear()
            logger.info("✓ Cache limpo")
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")


# ============================================================================
# CLASSE ASSISTENTE ACADÊMICO - INTERFACE SIMPLIFICADA
# ============================================================================

class AssistenteAcademico:
    """
    Interface simplificada para facilitar o uso do sistema

    Exemplo de uso:
        assistente = AssistenteAcademico()
        assistente.buscar(
            palavras_chave="machine learning education",
            periodo=(2018, 2024),
            limite=50
        )
        assistente.mostrar_resultados()
        assistente.exportar_excel("meu_levantamento.xlsx")
    """

    def __init__(self):
        """Inicializa o assistente"""
        self.sistema = LevantamentoBibliografico(usar_cache=True)
        print("\n🎓 Assistente Acadêmico iniciado!")
        print("✓ Cache habilitado")

        if FonteDados.GOOGLE_SCHOLAR in self.sistema.provedores:
            print("✓ Google Scholar disponível")
        else:
            print("⚠️  Google Scholar não disponível (instale: pip install scholarly)")

        print()

    def buscar(self,
               palavras_chave: str,
               periodo: Tuple[int, int],
               limite: int = 50,
               fontes: Optional[List[str]] = None,
               usar_google_scholar: bool = True):
        """
        Busca simplificada

        Args:
            palavras_chave: Termos de busca (ex: "machine learning education")
            periodo: Tupla (ano_inicio, ano_fim)
            limite: Número máximo de artigos por fonte
            fontes: Lista de fontes ['google_scholar', 'openalex', 'crossref']
            usar_google_scholar: Se deve usar Google Scholar (prioritário)
        """
        ano_inicio, ano_fim = periodo

        # Definir fontes
        if fontes is None:
            if usar_google_scholar and SCHOLARLY_DISPONIVEL:
                fontes_enum = [FonteDados.GOOGLE_SCHOLAR, FonteDados.OPENALEX]
            else:
                fontes_enum = [FonteDados.OPENALEX, FonteDados.CROSSREF]
        else:
            mapa_fontes = {
                'google_scholar': FonteDados.GOOGLE_SCHOLAR,
                'openalex': FonteDados.OPENALEX,
                'crossref': FonteDados.CROSSREF
            }
            fontes_enum = [mapa_fontes[f] for f in fontes if f in mapa_fontes]

        # Realizar busca
        self.sistema.buscar_multiplas_fontes(
            termo=palavras_chave,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            limite_por_fonte=limite,
            fontes=fontes_enum
        )

    def mostrar_resultados(self,
                           limite: int = 20,
                           ordenar_por: str = 'citacoes',
                           com_resumo: bool = False):
        """Mostra resultados formatados"""
        return self.sistema.visualizar_resultados(
            limite=limite,
            ordenar_por=ordenar_por,
            mostrar_resumo=com_resumo
        )

    def filtrar(self,
                citacoes_min: int = 0,
                apenas_com_pdf: bool = False,
                periodo: Optional[Tuple[int, int]] = None):
        """Filtra resultados"""
        kwargs = {'citacoes_minimas': citacoes_min, 'com_pdf': apenas_com_pdf}

        if periodo:
            kwargs['ano_inicio'], kwargs['ano_fim'] = periodo

        return self.sistema.filtrar_artigos(**kwargs)

    def estatisticas(self):
        """Mostra estatísticas"""
        stats = self.sistema.obter_estatisticas()

        print("\n" + "=" * 70)
        print("📊 ESTATÍSTICAS DO LEVANTAMENTO")
        print("=" * 70)
        for chave, valor in stats.items():
            if chave not in ['Distribuição por Ano', 'Top 5 Mais Citados']:
                print(f"{chave}: {valor}")
        print("=" * 70 + "\n")

        return stats

    def exportar_excel(self, nome_arquivo: str = "levantamento.xlsx"):
        """Exporta para Excel"""
        return self.sistema.exportar(nome_arquivo, TipoExportacao.XLSX)

    def exportar_csv(self, nome_arquivo: str = "levantamento.csv"):
        """Exporta para CSV"""
        return self.sistema.exportar(nome_arquivo, TipoExportacao.CSV)

    def exportar_bibtex(self, nome_arquivo: str = "referencias.bib"):
        """Exporta para BibTeX"""
        return self.sistema.exportar(nome_arquivo, TipoExportacao.BIBTEX)


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("🎓 SISTEMA DE LEVANTAMENTO BIBLIOGRÁFICO v3.0")
    print("=" * 70 + "\n")

    # ========== OPÇÃO 1: USO SIMPLIFICADO (RECOMENDADO) ==========
    print("📚 Iniciando levantamento bibliográfico...\n")

    # Criar assistente
    assistente = AssistenteAcademico()

    # Busca 1: Google Scholar + OpenAlex
    assistente.buscar(
        palavras_chave="abando escolar AND fatores sociais",
        periodo=(2016, 2026),
        limite=500,
        usar_google_scholar=True
    )

    # Busca 2: Termo complementar
    assistente.buscar(
        palavras_chave="evasão escolar AND ciências da natureza",
        periodo=(2016, 2026),
        limite=500
    )

    # Mostrar resultados
    print("\n" + "=" * 70)
    print("📖 RESULTADOS PRINCIPAIS")
    print("=" * 70)
    assistente.mostrar_resultados(limite=15, ordenar_por='citacoes')

    # Estatísticas
    assistente.estatisticas()

    # Filtrar artigos mais relevantes
    print("\n" + "=" * 70)
    print("🔍 ARTIGOS MAIS RELEVANTES (≥5 citações, com PDF)")
    print("=" * 70 + "\n")
    df_relevantes = assistente.filtrar(citacoes_min=5, apenas_com_pdf=True)
    if not df_relevantes.empty:
        print(f"✓ {len(df_relevantes)} artigos encontrados")
        for idx, (_, row) in enumerate(df_relevantes.head(10).iterrows(), 1):
            print(f"{idx}. {row['Título'][:60]}... ({row['Ano']}, {row['Citações']} citações)")
            print(f"   PDF: {row['Link PDF']}\n")

    # Exportar resultados
    print("\n" + "=" * 70)
    print("💾 EXPORTANDO RESULTADOS")
    print("=" * 70 + "\n")

    assistente.exportar_excel("levantamento_bibliografico.xlsx")
    assistente.exportar_csv("levantamento_bibliografico.csv")
    assistente.exportar_bibtex("referencias.bib")

    print("\n✅ LEVANTAMENTO CONCLUÍDO COM SUCESSO!")
    print("\nArquivos gerados:")
    print("  📊 levantamento_bibliografico_[timestamp].xlsx")
    print("  📄 levantamento_bibliografico_[timestamp].csv")
    print("  📚 referencias_[timestamp].bib")
    print("  💾 cache_artigos.pkl (para uso futuro)")
    print()