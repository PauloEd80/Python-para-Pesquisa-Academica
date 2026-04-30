"""
SISTEMA CIENTÍFICO DE ESTADO DA ARTE v6.0
Evasão Escolar em Licenciaturas de Ciências da Natureza: Uma Análise Sistêmica de Fatores Sociais

Características:
- Foco em construir Estado da Arte científico
- Palavras-chave estrategicamente selecionadas
- Combinações que representam o cenário real
- Análise temática automatizada
- Relatório de Estado da Arte
- Identificação de gaps de conhecimento
- Análise de tendências temporais
- Categorização de contribuições

Autor: Turma Engenharia de Software Positivo
Data: Abril 2026
Versão: 6.0
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
from collections import defaultdict

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

def configurar_logging(nome_arquivo: str = "estado_da_arte.log", nivel=logging.INFO):
    """Configura sistema de logging científico"""
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


class CategoriaTematica(Enum):
    """Categorias temáticas para análise"""
    EVASAO_FATORES = "evasao_e_fatores_sociais"
    FORMACAO_PROFESSORES = "formacao_de_professores"
    CIENCIAS_NATUREZA = "ciencias_da_natureza_ensino"
    DESIGUALDADE_ACESSO = "desigualdade_e_acesso"
    RETENCAO_ESTUDANTIL = "retencao_e_permanencia"
    MOTIVACAO_APRENDIZADO = "motivacao_e_desempenho"
    INTERDISCIPLINARIDADE = "abordagens_interdisciplinares"
    POLITICAS_EDUCACIONAIS = "politicas_e_acoes_institucionais"


@dataclass
class Artigo:
    """Estrutura científica de um artigo"""
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
    categoria_tematica: Optional[str] = None
    relevancia_cientifica: float = 0.0  # 0-1 score

    def __post_init__(self):
        if self.data_coleta is None:
            self.data_coleta = datetime.now().isoformat()

    def gerar_hash_unico(self) -> str:
        """Hash para deduplicação científica"""
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
# ESTRATÉGIA DE PALAVRAS-CHAVE CIENTÍFICA
# ============================================================================

class EstrategiaQuadroTeorico:
    """
    Define a estratégia científica de busca.

    Baseado em:
    - Evasão escolar como fenômeno central
    - Fatores sociais como contexto explicativo
    - Licenciaturas em Ciências da Natureza como locus
    - Formação de professores como dimensão pedagógica
    """

    def __init__(self):
        """Estrutura estratégica de busca científica"""

        # EIXO 1: Evasão/Abandono (Fenômeno Central)
        self.eixo_1_evasao = [
            "evasão escolar",
            "abandono escolar",
            "dropout estudantil",
            "desistência acadêmica",
            "evasão no ensino superior",
            "retenção escolar"
        ]

        # EIXO 2: Fatores Sociais (Explicação)
        self.eixo_2_fatores_sociais = [
            "fatores sociais evasão",
            "desigualdade social educação",
            "vulnerabilidade social estudante",
            "origem social desempenho",
            "classe social persistência",
            "contexto socioeconômico escolar"
        ]

        # EIXO 3: Licenciatura (Contexto Institucional)
        self.eixo_3_licenciatura = [
            "licenciatura ciências",
            "formação inicial docente",
            "curso licenciatura",
            "educação de professores",
            "carreira docente motivação"
        ]

        # EIXO 4: Ciências da Natureza (Disciplina)
        self.eixo_4_ciencias_natureza = [
            "ensino de física",
            "ensino de química",
            "ensino de biologia",
            "ciências da natureza",
            "ensino de matemática",
            "STEM educação"
        ]

        # COMBINAÇÕES ESTRATÉGICAS (nível científico)
        self.combinacoes_estrategicas = self._gerar_combinacoes_cientificas()

    def _gerar_combinacoes_cientificas(self) -> List[Tuple[str, str, List[str]]]:
        """
        Gera combinações estratégicas com significado científico.

        Retorna: (nome_busca, descrição, termos)
        """
        combinacoes = [
            # BUSCA 1: Núcleo central (Evasão + Fatores Sociais)
            (
                "NÚCLEO CENTRAL",
                "Evasão escolar explicada por fatores sociais",
                [
                    "evasão escolar AND fatores sociais",
                    "abandono escolar AND desigualdade social",
                    "dropout AND vulnerabilidade social"
                ]
            ),

            # BUSCA 2: Contexto institucional (Licenciatura + Evasão)
            (
                "CONTEXTO INSTITUCIONAL",
                "Evasão em cursos de licenciatura",
                [
                    "licenciatura AND evasão",
                    "formação inicial docente AND abandono",
                    "curso licenciatura AND desistência"
                ]
            ),

            # BUSCA 3: Especificidade disciplinar (Ciências + Evasão)
            (
                "ESPECIFICIDADE DISCIPLINAR",
                "Evasão em Ciências da Natureza",
                [
                    "evasão AND licenciatura ciências",
                    "abandono AND ensino física química biologia",
                    "dropout AND STEM licenciatura"
                ]
            ),

            # BUSCA 4: Formação de professores (Pedagogia da retenção)
            (
                "FORMAÇÃO DOCENTE",
                "Retenção na formação inicial de professores",
                [
                    "formação professores AND persistência",
                    "educação docente AND fatores sociais",
                    "carreira docente AND motivação evasão"
                ]
            ),

            # BUSCA 5: Dimensão socioeconômica (Classe + Educação)
            (
                "DIMENSÃO SOCIOECONÔMICA",
                "Origem social e trajetória educacional",
                [
                    "classe social AND desempenho educacional",
                    "origem socioeconômica AND permanência",
                    "vulnerabilidade AND educação superior"
                ]
            ),

            # BUSCA 6: Integração (Visão sistêmica)
            (
                "VISÃO SISTÊMICA",
                "Intersecção de fatores (social, institucional, disciplinar)",
                [
                    "evasão AND licenciatura AND fatores sociais",
                    "abandono AND formação professores AND ciências",
                    "dropout AND ensino AND desigualdade social"
                ]
            ),

            # BUSCA 7: Políticas e ações
            (
                "POLÍTICAS E INTERVENÇÕES",
                "Ações para reduzir evasão",
                [
                    "retenção estudantil AND políticas",
                    "permanência AND programa social",
                    "redução evasão AND intervenção"
                ]
            ),

            # BUSCA 8: Desempenho e motivação
            (
                "DESEMPENHO E MOTIVAÇÃO",
                "Fatores de desempenho e engajamento",
                [
                    "motivação AND desempenho educacional",
                    "engajamento estudantil AND evasão",
                    "sucesso académico AND origem social"
                ]
            ),

            # BUSCA 9: Pesquisas qualitativas
            (
                "PERSPECTIVAS ESTUDANTIS",
                "Experiências e trajetórias de estudantes",
                [
                    "trajetória estudantil AND evasão",
                    "experiência AND abandono",
                    "percepção estudante AND persistência"
                ]
            ),

            # BUSCA 10: Estado da arte recente
            (
                "TENDÊNCIAS RECENTES",
                "Desenvolvimentos nos últimos anos",
                [
                    "evasão 2023 2024 2025",
                    "licenciatura ciências 2022 2023 2024",
                    "fatores sociais educação recente"
                ]
            )
        ]

        return combinacoes

    def obter_todas_buscas(self) -> List[str]:
        """Retorna todas as strings de busca para executar"""
        buscas = []
        for nome, desc, termos in self.combinacoes_estrategicas:
            buscas.extend(termos)
        return buscas

    def obter_estrutura_tematica(self) -> Dict:
        """Retorna a estrutura temática para categorização"""
        return {
            CategoriaTematica.EVASAO_FATORES.value: {
                'palavras_chave': self.eixo_2_fatores_sociais + ['evasão', 'abandono'],
                'peso': 1.0
            },
            CategoriaTematica.FORMACAO_PROFESSORES.value: {
                'palavras_chave': self.eixo_3_licenciatura,
                'peso': 0.9
            },
            CategoriaTematica.CIENCIAS_NATUREZA.value: {
                'palavras_chave': self.eixo_4_ciencias_natureza,
                'peso': 0.85
            },
            CategoriaTematica.DESIGUALDADE_ACESSO.value: {
                'palavras_chave': ['desigualdade', 'acesso', 'oportunidade', 'vulnerabilidade'],
                'peso': 0.8
            },
            CategoriaTematica.RETENCAO_ESTUDANTIL.value: {
                'palavras_chave': ['retenção', 'permanência', 'persistência', 'sucesso'],
                'peso': 0.75
            }
        }


# ============================================================================
# PROVEDOR GOOGLE SCHOLAR CIENTÍFICO
# ============================================================================

class GoogleScholarCientifico:
    """Google Scholar otimizado para análise científica"""

    def __init__(self, usar_proxy: bool = False, timeout_requisicoes: int = 10):
        if not SCHOLARLY_DISPONIVEL:
            raise ImportError("Biblioteca 'scholarly' não instalada")

        self.usar_proxy = usar_proxy
        self.timeout = timeout_requisicoes
        self.artigos_encontrados: Dict[str, Artigo] = {}
        self.estrategia = EstrategiaQuadroTeorico()

        if self.usar_proxy:
            try:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                logger.info("✓ Proxy configurado")
            except Exception as e:
                logger.warning(f"Proxy não disponível: {e}")

    def realizar_busca_sistematica(self,
                                   ano_inicio: int = 2020,
                                   ano_fim: int = 2026,
                                   max_por_busca: int = 100) -> Dict[str, Artigo]:
        """
        Realiza busca sistemática seguindo estratégia científica
        """
        logger.info("\n" + "=" * 80)
        logger.info("BUSCA SISTEMÁTICA: Estado da Arte em Evasão Escolar")
        logger.info("Foco: Licenciaturas em Ciências da Natureza - Perspectiva de Fatores Sociais")
        logger.info(f"Período: {ano_inicio}-{ano_fim}")
        logger.info("=" * 80)

        buscas = self.estrategia.obter_todas_buscas()

        for idx, termo in enumerate(buscas, 1):
            logger.info(f"\n[{idx}/{len(buscas)}] Buscando: '{termo}'")
            self._buscar_termo_cientifico(termo, ano_inicio, ano_fim, max_por_busca)

            novos = len(self.artigos_encontrados)
            logger.info(f"    → Total acumulado: {novos} artigos únicos")

        return self.artigos_encontrados

    def _buscar_termo_cientifico(self,
                                 termo: str,
                                 ano_inicio: int,
                                 ano_fim: int,
                                 max_iteracoes: int):
        """Busca um termo com validação científica"""
        coletados = 0
        iteracao = 0

        try:
            search_query = scholarly.search_pubs(termo)

            for resultado in search_query:
                if iteracao >= max_iteracoes:
                    break

                try:
                    artigo = self._processar_resultado_cientifico(resultado, termo)

                    # Filtrar por período
                    if ano_inicio <= artigo.ano <= ano_fim:
                        hash_unico = artigo.gerar_hash_unico()

                        if hash_unico not in self.artigos_encontrados:
                            self.artigos_encontrados[hash_unico] = artigo
                            coletados += 1

                    time.sleep(self.timeout)
                    iteracao += 1

                except Exception as e:
                    logger.debug(f"Erro processando artigo: {e}")
                    iteracao += 1
                    continue

        except Exception as e:
            logger.warning(f"Erro na busca '{termo}': {e}")

    def _processar_resultado_cientifico(self, resultado: Dict, termo_busca: str) -> Artigo:
        """Processa resultado com análise científica"""
        bib = resultado.get('bib', {})

        titulo = bib.get('title', 'Sem título')
        autores = bib.get('author', [])
        if isinstance(autores, str):
            autores = [autores]

        try:
            ano = int(bib.get('pub_year', 0))
        except:
            ano = 0

        veiculo = bib.get('venue', 'Desconhecido')
        resumo = resultado.get('abstract', 'Sem resumo disponível')
        citacoes = resultado.get('num_citations', 0)

        link = resultado.get('pub_url', resultado.get('url', 'N/A'))
        link_pdf = resultado.get('pdf_url', None)
        doi = bib.get('doi', None)

        # Calcular relevância científica (0-1)
        relevancia = self._calcular_relevancia_cientifica(titulo, resumo, citacoes)

        # Categorizar tematicamente
        categoria = self._categorizar_tematicamente(titulo, resumo)

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
            palavras_chave_encontradas=[termo_busca],
            categoria_tematica=categoria,
            relevancia_cientifica=relevancia
        )

    def _calcular_relevancia_cientifica(self, titulo: str, resumo: str, citacoes: int) -> float:
        """Calcula score de relevância científica (0-1)"""
        score = 0.0

        # Citações (máximo até 100)
        score += min(citacoes / 100, 0.4)

        # Presença de termos científicos no título
        termos_cientificos = ['estudo', 'análise', 'investigação', 'pesquisa', 'investigação',
                              'comparative', 'systematic', 'systematic review', 'meta-análise',
                              'qualitativo', 'quantitativo', 'mixed methods']

        titulo_lower = titulo.lower()
        for termo in termos_cientificos:
            if termo in titulo_lower:
                score += 0.1
                break

        # Presença em resumo
        if resumo and resumo != 'Sem resumo disponível':
            score += 0.3

        return min(score, 1.0)

    def _categorizar_tematicamente(self, titulo: str, resumo: str) -> str:
        """Categoriza artigo tematicamente"""
        texto_completo = f"{titulo} {resumo}".lower()
        estrutura = self.estrategia.obter_estrutura_tematica()

        categoria_melhor = CategoriaTematica.EVASAO_FATORES.value
        peso_melhor = 0.0

        for categoria, info in estrutura.items():
            peso_categoria = 0.0
            for palavra in info['palavras_chave']:
                if palavra.lower() in texto_completo:
                    peso_categoria += 1.0

            peso_ponderado = (peso_categoria / len(info['palavras_chave'])) * info['peso']

            if peso_ponderado > peso_melhor:
                peso_melhor = peso_ponderado
                categoria_melhor = categoria

        return categoria_melhor

    def obter_artigos(self) -> List[Artigo]:
        """Retorna artigos encontrados"""
        return list(self.artigos_encontrados.values())


# ============================================================================
# ANALISADOR ESTADO DA ARTE
# ============================================================================

class AnalisadorEstadoDaArte:
    """Análise científica para gerar estado da arte"""

    def __init__(self, artigos: List[Artigo]):
        self.artigos = artigos
        self.df = None

    def gerar_analise_completa(self) -> Dict:
        """Gera análise científica completa"""
        if not self.artigos:
            return {}

        self.df = pd.DataFrame([a.para_dict() for a in self.artigos])

        analise = {
            'cobertura_geral': self._analise_cobertura(),
            'evolucao_temporal': self._analise_temporal(),
            'distribuicao_tematica': self._analise_tematica(),
            'autores_influentes': self._autores_influentes(),
            'veiculos_principais': self._veiculos_principais(),
            'gaps_conhecimento': self._identificar_gaps(),
            'tendencias': self._identificar_tendencias()
        }

        return analise

    def _analise_cobertura(self) -> Dict:
        """Análise de cobertura geral"""
        return {
            'total_artigos': len(self.df),
            'periodo': f"{int(self.df['ano'].min())}-{int(self.df['ano'].max())}",
            'artigos_com_pdf': (self.df['link_pdf'].notna()).sum(),
            'artigos_com_resumo': (self.df['resumo'] != 'Sem resumo disponível').sum(),
            'citacoes_totais': int(self.df['citacoes'].sum()),
            'citacoes_media': round(self.df['citacoes'].mean(), 2),
            'artigos_altamente_citados': len(self.df[self.df['citacoes'] >= 50])
        }

    def _analise_temporal(self) -> Dict:
        """Análise de evolução temporal"""
        por_ano = self.df.groupby('ano').agg({
            'titulo': 'count',
            'citacoes': 'mean'
        }).round(2)

        return {
            'artigos_por_ano': por_ano.to_dict('index'),
            'ano_mais_produtivo': int(por_ano['titulo'].idxmax()),
            'tendencia_publications': 'crescente' if por_ano['titulo'].iloc[-1] > por_ano['titulo'].iloc[
                0] else 'decrescente'
        }

    def _analise_tematica(self) -> Dict:
        """Análise de distribuição temática"""
        if 'categoria_tematica' not in self.df.columns:
            return {}

        temas = self.df['categoria_tematica'].value_counts()
        return {
            'distribuicao': temas.to_dict(),
            'tema_dominante': temas.idxmax(),
            'cobertura_tematica': len(temas)
        }

    def _autores_influentes(self, limite: int = 10) -> Dict:
        """Identifica autores mais influentes"""
        autores_dict = defaultdict(lambda: {'artigos': 0, 'citacoes_total': 0})

        for _, row in self.df.iterrows():
            for autor in row['autores'][:3]:  # Primeiros 3 autores
                autores_dict[autor]['artigos'] += 1
                autores_dict[autor]['citacoes_total'] += row['citacoes']

        # Ordenar por citações
        top_autores = sorted(
            autores_dict.items(),
            key=lambda x: x[1]['citacoes_total'],
            reverse=True
        )[:limite]

        return {nome: dados for nome, dados in top_autores}

    def _veiculos_principais(self, limite: int = 10) -> Dict:
        """Identifica veículos (journals, conferências) principais"""
        veiculos = self.df['veiculo'].value_counts().head(limite)

        resultado = {}
        for veiculo, count in veiculos.items():
            media_citacoes = self.df[self.df['veiculo'] == veiculo]['citacoes'].mean()
            resultado[veiculo] = {
                'artigos': int(count),
                'citacoes_media': round(media_citacoes, 2)
            }

        return resultado

    def _identificar_gaps(self) -> Dict:
        """Identifica gaps no conhecimento"""
        gaps = {
            'temas_pouco_explorados': [],
            'periodo_com_lacunas': [],
            'abordagens_faltantes': []
        }

        # Temas com poucos artigos
        por_tema = self.df['categoria_tematica'].value_counts()
        temas_raros = por_tema[por_tema < 5].index.tolist()
        gaps['temas_pouco_explorados'] = temas_raros

        # Anos com lacunas
        todos_anos = set(range(int(self.df['ano'].min()), int(self.df['ano'].max()) + 1))
        anos_com_artigos = set(self.df['ano'].unique())
        anos_faltantes = sorted(todos_anos - anos_com_artigos)
        gaps['periodo_com_lacunas'] = anos_faltantes

        # Abordagens faltantes (qualitativo vs quantitativo)
        qualitativas = self.df['resumo'].str.contains('qualitativ', case=False, na=False).sum()
        quantitativas = self.df['resumo'].str.contains('quantitativ|estatístic|número', case=False, na=False).sum()

        if qualitativas < quantitativas * 0.5:
            gaps['abordagens_faltantes'].append('Mais estudos qualitativos necessários')
        if quantitativas < qualitativas * 0.5:
            gaps['abordagens_faltantes'].append('Mais estudos quantitativos necessários')

        return gaps

    def _identificar_tendencias(self) -> Dict:
        """Identifica tendências de pesquisa"""
        tendencias = {}

        # Crescimento por tema
        por_ano_tema = self.df.groupby(['ano', 'categoria_tematica']).size().unstack(fill_value=0)

        for tema in por_ano_tema.columns:
            serie = por_ano_tema[tema]
            if len(serie) > 1 and serie.iloc[-1] > serie.iloc[0]:
                tendencias[f"Crescimento em {tema}"] = f"{serie.iloc[-1]} artigos em {int(serie.index[-1])}"

        # Citações crescentes
        citacoes_por_ano = self.df.groupby('ano')['citacoes'].mean()
        if citacoes_por_ano.iloc[-1] > citacoes_por_ano.iloc[0]:
            tendencias['Aumento de impacto citacional'] = f"Média: {citacoes_por_ano.iloc[-1]:.1f} citações"

        return tendencias


# ============================================================================
# SISTEMA COMPLETO ESTADO DA ARTE
# ============================================================================

class SistemaEstadoDaArte:
    """Sistema completo para gerar estado da arte científico"""

    def __init__(self, usar_cache: bool = True, usar_proxy: bool = False):
        """Inicializa o sistema"""
        self.provedor = GoogleScholarCientifico(usar_proxy=usar_proxy)
        self.usar_cache = usar_cache
        self.arquivo_cache = Path("cache_estado_da_arte.pkl")

        if self.usar_cache and self.arquivo_cache.exists():
            self._carregar_cache()

    def realizar_levantamento_cientifico(self,
                                         ano_inicio: int = 2020,
                                         ano_fim: int = 2026,
                                         max_por_busca: int = 100) -> Dict:
        """
        Realiza levantamento completo para estado da arte
        """
        logger.info("\n" + "=" * 80)
        logger.info("SISTEMA CIENTÍFICO DE ESTADO DA ARTE v6.0")
        logger.info("=" * 80)
        logger.info("\nTemática:")
        logger.info("  • Evasão/Abandono Escolar")
        logger.info("  • Em Licenciaturas")
        logger.info("  • Cursos de Ciências da Natureza (Física, Química, Biologia)")
        logger.info("  • Perspectiva de Fatores Sociais")
        logger.info("\nAbordagem: Análise Sistemática e Estado da Arte")
        logger.info("=" * 80)

        # Realizar busca sistemática
        artigos_dict = self.provedor.realizar_busca_sistematica(
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            max_por_busca=max_por_busca
        )

        # Salvar cache
        if self.usar_cache:
            self._salvar_cache()

        # Analisar
        artigos = list(artigos_dict.values())
        analisador = AnalisadorEstadoDaArte(artigos)
        analise = analisador.gerar_analise_completa()

        return {
            'total_artigos': len(artigos),
            'artigos': artigos,
            'analise': analise
        }

    def gerar_relatorio_estado_da_arte(self, dados: Dict, nome_arquivo: str = "estado_da_arte.md"):
        """Gera relatório científico de estado da arte"""
        artigos = dados.get('artigos', [])
        analise = dados.get('analise', {})

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_final = f"{Path(nome_arquivo).stem}_{timestamp}.md"

        with open(nome_final, 'w', encoding='utf-8') as f:
            # Cabeçalho
            f.write("# ESTADO DA ARTE\n\n")
            f.write("## Evasão Escolar em Licenciaturas de Ciências da Natureza\n")
            f.write("### Uma Análise Sistemática de Fatores Sociais (2020-2026)\n\n")

            f.write(f"**Data da coleta:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")

            # Resumo executivo
            f.write("---\n\n## RESUMO EXECUTIVO\n\n")
            cobertura = analise.get('cobertura_geral', {})
            f.write(f"- **Total de artigos analisados:** {cobertura.get('total_artigos', 0)}\n")
            f.write(f"- **Período de cobertura:** {cobertura.get('periodo', 'N/A')}\n")
            f.write(f"- **Citações totais:** {cobertura.get('citacoes_totais', 0)}\n")
            f.write(f"- **Artigos altamente citados (≥50):** {cobertura.get('artigos_altamente_citados', 0)}\n")
            f.write(f"- **Artigos com PDF disponível:** {cobertura.get('artigos_com_pdf', 0)}\n\n")

            # Evolução temporal
            f.write("---\n\n## EVOLUÇÃO TEMPORAL\n\n")
            temporal = analise.get('evolucao_temporal', {})
            f.write(f"Tendência: {temporal.get('tendencia_publications', 'N/A')}\n")
            f.write(f"Ano mais produtivo: {temporal.get('ano_mais_produtivo', 'N/A')}\n\n")

            f.write("### Publicações por Ano\n\n")
            por_ano = temporal.get('artigos_por_ano', {})
            for ano, dados_ano in sorted(por_ano.items()):
                count = int(dados_ano.get('titulo', 0))
                f.write(f"- **{ano}:** {count} artigos\n")
            f.write("\n")

            # Distribuição temática
            f.write("---\n\n## DISTRIBUIÇÃO TEMÁTICA\n\n")
            tematica = analise.get('distribuicao_tematica', {})
            distrib = tematica.get('distribuicao', {})
            if distrib:
                for tema, count in sorted(distrib.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- **{tema}:** {count} artigos\n")
            f.write("\n")

            # Autores influentes
            f.write("---\n\n## AUTORES E PESQUISADORES INFLUENTES\n\n")
            autores = analise.get('autores_influentes', {})
            for i, (autor, dados_autor) in enumerate(sorted(autores.items(),
                                                            key=lambda x: x[1]['citacoes_total'],
                                                            reverse=True)[:10], 1):
                f.write(f"{i}. **{autor}**\n")
                f.write(f"   - Artigos: {dados_autor['artigos']}\n")
                f.write(f"   - Citações totais: {dados_autor['citacoes_total']}\n\n")

            # Veículos principais
            f.write("---\n\n## PRINCIPAIS VEÍCULOS DE PUBLICAÇÃO\n\n")
            veiculos = analise.get('veiculos_principais', {})
            for i, (veiculo, dados_veiculo) in enumerate(list(veiculos.items())[:10], 1):
                f.write(f"{i}. **{veiculo}**\n")
                f.write(f"   - Artigos publicados: {dados_veiculo['artigos']}\n")
                f.write(f"   - Citações médias: {dados_veiculo['citacoes_media']}\n\n")

            # Gaps
            f.write("---\n\n## LACUNAS E OPORTUNIDADES DE PESQUISA\n\n")
            gaps = analise.get('gaps_conhecimento', {})

            f.write("### Temas Pouco Explorados\n")
            temas_raros = gaps.get('temas_pouco_explorados', [])
            if temas_raros:
                for tema in temas_raros:
                    f.write(f"- {tema}\n")
            else:
                f.write("- Todos os temas principais foram bem cobertos\n")
            f.write("\n")

            f.write("### Períodos com Lacunas Temporais\n")
            anos_faltantes = gaps.get('periodo_com_lacunas', [])
            if anos_faltantes:
                f.write(f"- Anos: {', '.join(map(str, anos_faltantes))}\n")
            else:
                f.write("- Cobertura temporal contínua\n")
            f.write("\n")

            f.write("### Abordagens Metodológicas Faltantes\n")
            abordagens = gaps.get('abordagens_faltantes', [])
            if abordagens:
                for abordagem in abordagens:
                    f.write(f"- {abordagem}\n")
            else:
                f.write("- Abordagens metodológicas equilibradas\n")
            f.write("\n")

            # Tendências
            f.write("---\n\n## TENDÊNCIAS EMERGENTES\n\n")
            tendencias = analise.get('tendencias', {})
            if tendencias:
                for tendencia, descricao in tendencias.items():
                    f.write(f"- **{tendencia}:** {descricao}\n")
            else:
                f.write("- Nenhuma tendência significativa detectada\n")
            f.write("\n")

            # Top artigos
            f.write("---\n\n## TOP 20 ARTIGOS MAIS CITADOS\n\n")
            artigos_ord = sorted(artigos, key=lambda x: x.citacoes, reverse=True)
            for i, artigo in enumerate(artigos_ord[:20], 1):
                f.write(f"### {i}. {artigo.titulo}\n\n")
                f.write(f"- **Autores:** {', '.join(artigo.autores[:5])}{'...' if len(artigo.autores) > 5 else ''}\n")
                f.write(f"- **Ano:** {artigo.ano}\n")
                f.write(f"- **Citações:** {artigo.citacoes}\n")
                f.write(f"- **Veículo:** {artigo.veiculo}\n")
                if artigo.doi:
                    f.write(f"- **DOI:** {artigo.doi}\n")
                f.write(f"- **Link:** {artigo.link}\n\n")

            # Conclusões
            f.write("---\n\n## CONCLUSÕES E RECOMENDAÇÕES\n\n")
            f.write("### Quadro Geral\n")
            f.write("Este estado da arte apresenta uma análise sistemática de ")
            f.write(f"{cobertura.get('total_artigos', 0)} artigos publicados entre ")
            f.write(f"{cobertura.get('periodo', '2020-2026')} sobre evasão escolar em ")
            f.write("licenciaturas de Ciências da Natureza, com foco em fatores sociais.\n\n")

            f.write("### Recomendações para Pesquisas Futuras\n")
            f.write("1. Aprofundar investigações em temas pouco explorados\n")
            f.write("2. Realizar estudos longitudinais que acompanhem trajetórias estudantis\n")
            f.write("3. Combinar abordagens qualitativas e quantitativas\n")
            f.write("4. Investigar impactos de políticas públicas de permanência\n")
            f.write("5. Examinar interseccionalidades de fatores sociais\n\n")

        logger.info(f"✓ Relatório Estado da Arte: {nome_final}")
        return nome_final

    def exportar_dados(self, artigos: List[Artigo], formato: str = 'csv'):
        """Exporta dados em múltiplos formatos"""
        if not artigos:
            return

        df = pd.DataFrame([a.para_dict() for a in artigos])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if formato == 'csv':
            nome = f"artigos_estado_da_arte_{timestamp}.csv"
            df.to_csv(nome, index=False, encoding='utf-8-sig')
            logger.info(f"✓ CSV: {nome}")

        elif formato == 'xlsx':
            nome = f"artigos_estado_da_arte_{timestamp}.xlsx"
            with pd.ExcelWriter(nome, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Artigos', index=False)
            logger.info(f"✓ XLSX: {nome}")

        elif formato == 'json':
            nome = f"artigos_estado_da_arte_{timestamp}.json"
            dados = {
                'metadata': {
                    'data': datetime.now().isoformat(),
                    'total_artigos': len(df),
                    'fonte': 'Google Scholar',
                    'proposito': 'Estado da Arte em Evasão Escolar'
                },
                'artigos': [a.para_dict() for a in artigos]
            }
            with open(nome, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ JSON: {nome}")

        elif formato == 'bibtex':
            nome = f"artigos_estado_da_arte_{timestamp}.bib"
            with open(nome, 'w', encoding='utf-8') as f:
                for idx, artigo in enumerate(artigos, 1):
                    primeiro_autor = str(artigo.autores[0]).split()[-1] if artigo.autores else 'Unknown'
                    chave = f"{primeiro_autor}{artigo.ano}{idx}".replace(' ', '')

                    f.write(f"@article{{{chave},\n")
                    f.write(f"  title={{{artigo.titulo}}},\n")
                    f.write(f"  author={{{', '.join(artigo.autores[:5])}}},\n")
                    f.write(f"  year={{{artigo.ano}}},\n")
                    f.write(f"  journal={{{artigo.veiculo}}},\n")
                    if artigo.doi:
                        f.write(f"  doi={{{artigo.doi}}},\n")
                    f.write(f"  url={{{artigo.link}}}\n")
                    f.write("}\n\n")
            logger.info(f"✓ BibTeX: {nome}")

    def _salvar_cache(self):
        """Salva cache"""
        try:
            with open(self.arquivo_cache, 'wb') as f:
                pickle.dump(self.provedor.artigos_encontrados, f)
            logger.info(f"✓ Cache salvo")
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")

    def _carregar_cache(self):
        """Carrega cache"""
        try:
            with open(self.arquivo_cache, 'rb') as f:
                self.provedor.artigos_encontrados = pickle.load(f)
            logger.info(f"✓ Cache carregado: {len(self.provedor.artigos_encontrados)} artigos")
        except Exception as e:
            logger.warning(f"Erro ao carregar cache: {e}")


# ============================================================================
# INTERFACE SIMPLIFICADA
# ============================================================================

class AssistenteEstadoDaArte:
    """Interface para gerar estado da arte científico"""

    def __init__(self, usar_cache: bool = True, usar_proxy: bool = False):
        print("\n" + "=" * 80)
        print("SISTEMA CIENTÍFICO DE ESTADO DA ARTE v6.0")
        print("=" * 80)
        print("\nTemática:")
        print("  Evasão Escolar em Licenciaturas de Ciências da Natureza")
        print("  Análise Sistemática de Fatores Sociais")
        print("=" * 80 + "\n")

        try:
            self.sistema = SistemaEstadoDaArte(usar_cache=usar_cache, usar_proxy=usar_proxy)
            print("✓ Sistema inicializado")
            print(f"✓ Cache: {'Habilitado' if usar_cache else 'Desabilitado'}")
        except ImportError as e:
            print(f"❌ Erro: {e}")
            raise

    def executar_levantamento(self, max_por_busca: int = 100) -> Dict:
        """Executa levantamento completo"""
        return self.sistema.realizar_levantamento_cientifico(
            ano_inicio=2020,
            ano_fim=2026,
            max_por_busca=max_por_busca
        )

    def gerar_relatorio(self, dados: Dict):
        """Gera relatório de estado da arte"""
        return self.sistema.gerar_relatorio_estado_da_arte(dados)

    def exportar(self, artigos: List[Artigo], formato: str = 'csv'):
        """Exporta dados"""
        self.sistema.exportar_dados(artigos, formato)


# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == "__main__":

    if not SCHOLARLY_DISPONIVEL:
        print("\n❌ Erro: Biblioteca 'scholarly' não encontrada!")
        print("Instale com: pip install scholarly")
        exit(1)

    # Criar assistente
    assistente = AssistenteEstadoDaArte(usar_cache=True, usar_proxy=False)

    # Executar levantamento
    print("\n📚 Iniciando levantamento científico...\n")
    dados = assistente.executar_levantamento(max_por_busca=100)

    # Gerar relatório
    print("\n📝 Gerando relatório Estado da Arte...\n")
    relatorio = assistente.gerar_relatorio(dados)

    # Exportar
    print("\n💾 Exportando dados em múltiplos formatos...\n")
    artigos = dados.get('artigos', [])

    for fmt in ['csv', 'json', 'bibtex', 'xlsx']:
        try:
            assistente.exportar(artigos, fmt)
        except Exception as e:
            print(f"  ⚠️  Erro ao exportar {fmt.upper()}: {e}")

    # Resumo
    print("\n" + "=" * 80)
    print("✅ LEVANTAMENTO CONCLUÍDO!")
    print("=" * 80)
    print(f"\nTotal de artigos: {dados.get('total_artigos', 0)}")
    print(f"Período: 2020-2026")
    print("\nArquivos gerados:")
    print("  📋 estado_da_arte_[timestamp].md")
    print("  📊 artigos_estado_da_arte_[timestamp].csv")
    print("  📄 artigos_estado_da_arte_[timestamp].json")
    print("  📚 artigos_estado_da_arte_[timestamp].bib")
    print("  📋 artigos_estado_da_arte_[timestamp].xlsx")
    print("  💾 cache_estado_da_arte.pkl")
    print("\n" + "=" * 80 + "\n")
