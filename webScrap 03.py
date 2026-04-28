import requests
import pandas as pd
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from pathlib import Path
from abc import ABC, abstractmethod
import pickle
from urllib.parse import quote


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def configurar_logging(nome_arquivo: str = "levantamento_bibliografico.log"):
    """Configura sistema de logging para rastrear todas as operações"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(nome_arquivo),
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
    OPENALEX = "openalex"
    CROSSREF = "crossref"
    SCHOLARLY = "scholarly"


class TipoExportacao(Enum):
    """Formatos de exportação disponíveis"""
    CSV = "csv"
    JSON = "json"
    BIBTEX = "bibtex"
    XLSX = "xlsx"


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
    fonte: str = "desconhecida"
    data_coleta: str = None
    palavras_chave: List[str] = None
    tipo_publicacao: str = "journal"

    def __post_init__(self):
        if self.data_coleta is None:
            self.data_coleta = datetime.now().isoformat()
        if self.palavras_chave is None:
            self.palavras_chave = []

    def gerar_hash_unico(self) -> str:
        """Gera hash único para identificar duplicatas"""
        texto = f"{self.titulo.lower().strip()}{self.ano}".encode()
        return hashlib.md5(texto).hexdigest()

    def para_dict(self) -> Dict:
        """Converte artigo para dicionário"""
        return asdict(self)


# ============================================================================
# CLASSE BASE PARA PROVEDORES DE DADOS
# ============================================================================

class ProvdorDados(ABC):
    """Classe abstrata para provedores de dados bibliográficos"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LevantamentoBibliografico/2.0 (Pesquisa Científica)'
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
        return response.json()


# ============================================================================
# IMPLEMENTAÇÕES DOS PROVEDORES
# ============================================================================

class OpenAlexProvider(ProvdorDados):
    """Provedor de dados usando OpenAlex API"""

    BASE_URL = "https://api.openalex.org/works"

    def buscar(self, query: str, ano_inicio: int, ano_fim: int,
               limite: int = 100) -> List[Artigo]:
        """
        Busca em OpenAlex com filtros de ano

        Args:
            query: Termo de busca
            ano_inicio: Ano inicial (inclusive)
            ano_fim: Ano final (inclusive)
            limite: Número máximo de resultados

        Returns:
            Lista de objetos Artigo
        """
        artigos = []
        pagina = 1
        coletados = 0

        while coletados < limite:
            try:
                # Montar filtro de ano
                filtro_ano = f"publication_year:[{ano_inicio} TO {ano_fim}]"

                params = {
                    'search': query,
                    'filter': filtro_ano,
                    'per-page': min(50, limite - coletados),
                    'page': pagina,
                    'sort': 'cited_by_count:desc'  # Ordenar por citações
                }

                logger.info(f"OpenAlex - Página {pagina}: {query} ({ano_inicio}-{ano_fim})")
                response = self.session.get(self.BASE_URL, params=params,
                                            timeout=self.timeout)
                dados = self._validar_resposta(response)

                if not dados or 'results' not in dados or not dados['results']:
                    logger.info(f"OpenAlex: Fim dos resultados na página {pagina}")
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
                time.sleep(1)  # Delay entre requisições

            except Exception as e:
                logger.error(f"Erro na busca OpenAlex: {e}")
                break

        logger.info(f"OpenAlex: {coletados} artigos coletados")
        return artigos

    def _processar_resultado_openalex(self, resultado: Dict) -> Artigo:
        """Processa um resultado do OpenAlex"""
        autores = [
            f"{autor.get('author', {}).get('display_name', 'Anônimo')}"
            for autor in resultado.get('authorships', [])[:10]  # Primeiros 10 autores
        ]

        return Artigo(
            titulo=resultado.get('title', 'Sem título'),
            autores=autores,
            ano=resultado.get('publication_year', 0),
            veiculo=resultado.get('venues', [{}])[0].get('display_name', 'N/A')
            if resultado.get('venues') else 'N/A',
            resumo=resultado.get('abstract', 'Resumo não disponível'),
            link=resultado.get('doi', '') or resultado.get('pdf_url', '') or 'N/A',
            citacoes=resultado.get('cited_by_count', 0),
            doi=resultado.get('doi'),
            fonte='OpenAlex',
            tipo_publicacao=resultado.get('type', 'journal')
        )


class CrossRefProvider(ProvdorDados):
    """Provedor de dados usando CrossRef API"""

    BASE_URL = "https://api.crossref.org/works"

    def buscar(self, query: str, ano_inicio: int, ano_fim: int,
               limite: int = 100) -> List[Artigo]:
        """
        Busca em CrossRef com filtros de ano

        Args:
            query: Termo de busca
            ano_inicio: Ano inicial
            ano_fim: Ano final
            limite: Número máximo de resultados
        """
        artigos = []
        pagina = 0
        coletados = 0

        while coletados < limite:
            try:
                params = {
                    'query': query,
                    'filter': f'from-pub-date:{ano_inicio}-01-01,until-pub-date:{ano_fim}-12-31',
                    'rows': min(100, limite - coletados),
                    'offset': pagina * 100,
                    'sort': 'is-referenced-by-count',
                    'order': 'desc'
                }

                logger.info(f"CrossRef - Página {pagina + 1}: {query} ({ano_inicio}-{ano_fim})")
                response = self.session.get(self.BASE_URL, params=params,
                                            timeout=self.timeout)
                dados = self._validar_resposta(response)

                if not dados or 'message' not in dados or not dados['message'].get('items'):
                    logger.info(f"CrossRef: Fim dos resultados na página {pagina + 1}")
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

        logger.info(f"CrossRef: {coletados} artigos coletados")
        return artigos

    def _processar_resultado_crossref(self, resultado: Dict) -> Artigo:
        """Processa um resultado do CrossRef"""
        autores = [
            f"{autor.get('given', '')} {autor.get('family', '')}".strip()
            for autor in resultado.get('author', [])[:10]
        ]

        # Extrair ano da publicação
        ano = 0
        if 'published' in resultado and 'date-parts' in resultado['published']:
            ano = resultado['published']['date-parts'][0][0]
        elif 'issued' in resultado and 'date-parts' in resultado['issued']:
            ano = resultado['issued']['date-parts'][0][0]

        return Artigo(
            titulo=resultado.get('title', ['Sem título'])[0],
            autores=autores,
            ano=ano,
            veiculo=resultado.get('container-title', ['N/A'])[0],
            resumo=resultado.get('abstract', 'Resumo não disponível'),
            link=resultado.get('URL', 'N/A'),
            citacoes=resultado.get('is-referenced-by-count', 0),
            doi=resultado.get('DOI'),
            fonte='CrossRef',
            tipo_publicacao=resultado.get('type', 'journal')
        )


# ============================================================================
# CLASSE PRINCIPAL - LEVANTAMENTO BIBLIOGRÁFICO
# ============================================================================

class LevantamentoBibliografico:
    """
    Sistema completo de levantamento bibliográfico para pesquisas científicas
    """

    def __init__(self, usar_cache: bool = True):
        """
        Inicializa o sistema

        Args:
            usar_cache: Se True, utiliza cache para evitar requisições duplicadas
        """
        self.artigos: Dict[str, Artigo] = {}  # Dict com hash como chave para evitar duplicatas
        self.usar_cache = usar_cache
        self.arquivo_cache = Path("cache_artigos.pkl")
        self.historico_buscas = []

        # Inicializar provedores
        self.provedores = {
            FonteDados.OPENALEX: OpenAlexProvider(),
            FonteDados.CROSSREF: CrossRefProvider()
        }

        # Carregar cache se disponível
        if self.usar_cache and self.arquivo_cache.exists():
            self._carregar_cache()

    def buscar_multiplas_fontes(self,
                                termo: str,
                                ano_inicio: int,
                                ano_fim: int,
                                limite_por_fonte: int = 50,
                                fontes: Optional[List[FonteDados]] = None) -> int:
        """
        Realiza buscas em múltiplas fontes simultaneamente

        Args:
            termo: Termo de busca
            ano_inicio: Ano inicial
            ano_fim: Ano final
            limite_por_fonte: Número máximo de artigos por fonte
            fontes: Lista de fontes a usar (default: todas)

        Returns:
            Número de artigos únicos adicionados
        """
        if fontes is None:
            fontes = [FonteDados.OPENALEX, FonteDados.CROSSREF]

        if ano_inicio > ano_fim:
            logger.error("Ano inicial não pode ser maior que ano final")
            raise ValueError("ano_inicio > ano_fim")

        logger.info(f"\n{'=' * 70}")
        logger.info(f"NOVA BUSCA: '{termo}' ({ano_inicio}-{ano_fim})")
        logger.info(f"Fontes: {[f.value for f in fontes]}")
        logger.info(f"{'=' * 70}\n")

        artigos_antes = len(self.artigos)

        # Buscar em cada fonte
        for fonte in fontes:
            if fonte not in self.provedores:
                logger.warning(f"Provedor {fonte.value} não disponível")
                continue

            try:
                provedor = self.provedores[fonte]
                novos_artigos = provedor.buscar(
                    query=termo,
                    ano_inicio=ano_inicio,
                    ano_fim=ano_fim,
                    limite=limite_por_fonte
                )

                # Adicionar artigos únicos (usando hash)
                for artigo in novos_artigos:
                    hash_unico = artigo.gerar_hash_unico()
                    if hash_unico not in self.artigos:
                        self.artigos[hash_unico] = artigo

            except Exception as e:
                logger.error(f"Erro ao buscar em {fonte.value}: {e}")

        artigos_adicionados = len(self.artigos) - artigos_antes

        # Registrar busca no histórico
        self.historico_buscas.append({
            'termo': termo,
            'ano_inicio': ano_inicio,
            'ano_fim': ano_fim,
            'timestamp': datetime.now().isoformat(),
            'artigos_adicionados': artigos_adicionados
        })

        logger.info(f"\n✓ {artigos_adicionados} artigos únicos adicionados")
        logger.info(f"Total acumulado: {len(self.artigos)} artigos\n")

        return artigos_adicionados

    def filtrar_artigos(self,
                        citacoes_minimas: int = 0,
                        ano_inicio: Optional[int] = None,
                        ano_fim: Optional[int] = None,
                        veiculos: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Filtra artigos conforme critérios específicos

        Args:
            citacoes_minimas: Número mínimo de citações
            ano_inicio: Ano mínimo
            ano_fim: Ano máximo
            veiculos: Lista de veículos/revistas a incluir

        Returns:
            DataFrame com artigos filtrados
        """
        df = self._artigos_para_dataframe()

        if df.empty:
            logger.warning("Nenhum artigo para filtrar")
            return df

        # Filtrar por citações
        if citacoes_minimas > 0:
            df = df[df['Citações'] >= citacoes_minimas]
            logger.info(f"Filtro citações: {len(df)} artigos com ≥{citacoes_minimas} citações")

        # Filtrar por período
        if ano_inicio:
            df = df[df['Ano'] >= ano_inicio]
        if ano_fim:
            df = df[df['Ano'] <= ano_fim]

        # Filtrar por veículos
        if veiculos:
            df = df[df['Veículo'].isin(veiculos)]
            logger.info(f"Filtro veículos: {len(df)} artigos de {len(veiculos)} veículos")

        return df

    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas detalhadas da coleção"""
        if not self.artigos:
            return {}

        df = self._artigos_para_dataframe()

        # Calcula estatísticas por ano
        stats_por_ano = df.groupby('Ano').agg({
            'Título': 'count',
            'Citações': ['mean', 'sum', 'max']
        }).round(2)

        # Calcula estatísticas por veículo
        stats_por_veiculo = df.groupby('Veículo').agg({
            'Título': 'count',
            'Citações': 'mean'
        }).round(2).sort_values('Citações', ascending=False).head(10)

        return {
            'Total de Artigos': len(df),
            'Período': f"{int(df['Ano'].min())}-{int(df['Ano'].max())}",
            'Artigos por Ano': stats_por_ano.to_dict(),
            'Artigos por Veículo (Top 10)': stats_por_veiculo.to_dict(),
            'Citações Totais': int(df['Citações'].sum()),
            'Citações Médias': round(df['Citações'].mean(), 2),
            'Citações Máximas': int(df['Citações'].max()),
            'Artigos com DOI': (df['DOI'] != 'nan').sum(),
            'Artigos com Resumo': (df['Resumo'] != 'Resumo não disponível').sum(),
            'Fontes de Dados': df['Fonte'].unique().tolist(),
            'Histórico de Buscas': self.historico_buscas
        }

    def _artigos_para_dataframe(self) -> pd.DataFrame:
        """Converte artigos para DataFrame pandas"""
        if not self.artigos:
            return pd.DataFrame()

        dados = [artigo.para_dict() for artigo in self.artigos.values()]
        df = pd.DataFrame(dados)

        # Limpar ano (remover 0s que indicam ano desconhecido)
        df = df[df['ano'] > 0].copy()

        # Renomear colunas para português
        mapeamento_colunas = {
            'titulo': 'Título',
            'autores': 'Autores',
            'ano': 'Ano',
            'veiculo': 'Veículo',
            'resumo': 'Resumo',
            'link': 'Link',
            'citacoes': 'Citações',
            'doi': 'DOI',
            'fonte': 'Fonte',
            'data_coleta': 'Data da Coleta',
            'palavras_chave': 'Palavras-chave',
            'tipo_publicacao': 'Tipo'
        }
        df = df.rename(columns=mapeamento_colunas)

        # Ordenar por citações (descendente) depois por ano (descendente)
        df = df.sort_values(['Citações', 'Ano'], ascending=[False, False])

        return df

    def exportar(self,
                 nome_arquivo: str,
                 formato: TipoExportacao = TipoExportacao.CSV,
                 incluir_resumos: bool = True) -> bool:
        """
        Exporta resultados em vários formatos

        Args:
            nome_arquivo: Nome do arquivo de saída
            formato: Formato de exportação
            incluir_resumos: Se incluir resumos (útil para CSV)

        Returns:
            True se bem-sucedido
        """
        try:
            df = self._artigos_para_dataframe()

            if df.empty:
                logger.error("Nenhum artigo para exportar")
                return False

            # Adicionar timestamp ao nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = Path(nome_arquivo).stem
            extensao = Path(nome_arquivo).suffix
            nome_final = f"{nome_base}_{timestamp}{extensao}"

            if formato == TipoExportacao.CSV:
                df.to_csv(nome_final, index=False, encoding='utf-8-sig')
                logger.info(f"✓ Exportado para CSV: {nome_final} ({len(df)} registros)")

            elif formato == TipoExportacao.XLSX:
                with pd.ExcelWriter(nome_final, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Artigos', index=False)

                    # Adicionar planilha com estatísticas
                    stats = self.obter_estatisticas()
                    stats_df = pd.DataFrame([stats])
                    stats_df.to_excel(writer, sheet_name='Estatísticas', index=False)

                logger.info(f"✓ Exportado para XLSX: {nome_final}")

            elif formato == TipoExportacao.JSON:
                dados_export = {
                    'metadata': {
                        'data_exportacao': datetime.now().isoformat(),
                        'total_artigos': len(df),
                        'periodo': f"{int(df['Ano'].min())}-{int(df['Ano'].max())}"
                    },
                    'artigos': [
                        artigo.para_dict() for artigo in self.artigos.values()
                    ]
                }

                with open(nome_final, 'w', encoding='utf-8') as f:
                    json.dump(dados_export, f, indent=2, ensure_ascii=False)

                logger.info(f"✓ Exportado para JSON: {nome_final}")

            elif formato == TipoExportacao.BIBTEX:
                self._exportar_bibtex(nome_final)
                logger.info(f"✓ Exportado para BibTeX: {nome_final}")

            return True

        except Exception as e:
            logger.error(f"Erro ao exportar: {e}")
            return False

    def _exportar_bibtex(self, nome_arquivo: str):
        """Exporta em formato BibTeX"""
        df = self._artigos_para_dataframe()

        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            for idx, (_, row) in enumerate(df.iterrows(), 1):
                # Gerar chave única para BibTeX
                primeiro_autor = row['Autores'][0].split()[-1] if row['Autores'] else 'Unknown'
                chave = f"{primeiro_autor}{row['Ano']}{idx}".replace(' ', '')

                f.write(f"@article{{{chave},\n")
                f.write(f"  title={{{row['Título']}}},\n")
                f.write(f"  author={{{row['Autores']}}},\n")
                f.write(f"  year={{{row['Ano']}}},\n")
                f.write(f"  journal={{{row['Veículo']}}},\n")

                if row['DOI'] and row['DOI'] != 'nan':
                    f.write(f"  doi={{{row['DOI']}}},\n")

                f.write(f"  url={{{row['Link']}}}\n")
                f.write("}\n\n")

    def gerar_relatorio_html(self, nome_arquivo: str = "relatorio_bibliografico.html"):
        """Gera relatório visual em HTML"""
        df = self._artigos_para_dataframe()
        stats = self.obter_estatisticas()

        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Relatório Bibliográfico</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-box {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .stat-number {{
                    font-size: 32px;
                    font-weight: bold;
                }}
                .stat-label {{
                    font-size: 14px;
                    opacity: 0.9;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                    padding: 12px;
                    text-align: left;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }}
                tr:hover {{
                    background-color: #f9f9f9;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #7f8c8d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📚 Relatório de Levantamento Bibliográfico</h1>
                <p><strong>Gerado em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>

                <h2>📊 Estatísticas Gerais</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-number">{stats.get('Total de Artigos', 0)}</div>
                        <div class="stat-label">Total de Artigos</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{stats.get('Citações Totais', 0)}</div>
                        <div class="stat-label">Citações Totais</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{stats.get('Citações Médias', 0)}</div>
                        <div class="stat-label">Citações Médias</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{stats.get('Período', 'N/A')}</div>
                        <div class="stat-label">Período</div>
                    </div>
                </div>

                <h2>📄 Top 20 Artigos Mais Citados</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Título</th>
                            <th>Autor(es)</th>
                            <th>Ano</th>
                            <th>Citações</th>
                            <th>Fonte</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for idx, (_, row) in enumerate(df.head(20).iterrows(), 1):
            autores = row['Autores'][:100] + "..." if len(str(row['Autores'])) > 100 else row['Autores']
            titulo = row['Título'][:80] + "..." if len(str(row['Título'])) > 80 else row['Título']

            html_content += f"""
                        <tr>
                            <td>{idx}</td>
                            <td><strong>{titulo}</strong></td>
                            <td>{autores}</td>
                            <td>{row['Ano']}</td>
                            <td><strong>{row['Citações']}</strong></td>
                            <td>{row['Fonte']}</td>
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>

                <div class="footer">
                    <p>Este relatório foi gerado automaticamente pelo Sistema de Levantamento Bibliográfico Avançado.</p>
                </div>
            </div>
        </body>
        </html>
        """

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_final = f"{Path(nome_arquivo).stem}_{timestamp}.html"

        with open(nome_final, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ Relatório HTML gerado: {nome_final}")
        return nome_final

    def _salvar_cache(self):
        """Salva artigos em cache local"""
        try:
            with open(self.arquivo_cache, 'wb') as f:
                pickle.dump(self.artigos, f)
            logger.info(f"Cache salvo: {self.arquivo_cache}")
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")

    def _carregar_cache(self):
        """Carrega artigos do cache local"""
        try:
            with open(self.arquivo_cache, 'rb') as f:
                self.artigos = pickle.load(f)
            logger.info(f"Cache carregado: {len(self.artigos)} artigos")
        except Exception as e:
            logger.warning(f"Erro ao carregar cache: {e}")

    def limpar_cache(self):
        """Limpa o cache"""
        try:
            if self.arquivo_cache.exists():
                self.arquivo_cache.unlink()
            self.artigos.clear()
            logger.info("Cache limpo com sucesso")
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":

    logger.info("\n" + "=" * 70)
    logger.info("SISTEMA DE LEVANTAMENTO BIBLIOGRÁFICO AVANÇADO v2.0")
    logger.info("=" * 70 + "\n")

    # Criar instância do sistema
    levantamento = LevantamentoBibliografico(usar_cache=True)

    # ========== EXEMPLO 1: Busca simples com intervalo de anos ==========
    logger.info("\n[1/4] EXEMPLO 1: Busca por Abandono Escolar (2015-2024)")
    levantamento.buscar_multiplas_fontes(
        termo="abandono escolar",
        ano_inicio=2015,
        ano_fim=2024,
        limite_por_fonte=30,
        fontes=[FonteDados.OPENALEX, FonteDados.CROSSREF]
    )

    # ========== EXEMPLO 2: Busca complementar com termo mais específico ==========
    logger.info("\n[2/4] EXEMPLO 2: Busca por Desigualdade Educacional (2018-2024)")
    levantamento.buscar_multiplas_fontes(
        termo="desigualdade educacional acesso",
        ano_inicio=2018,
        ano_fim=2024,
        limite_por_fonte=25,
        fontes=[FonteDados.OPENALEX]
    )

    # ========== EXEMPLO 3: Busca por período histórico ==========
    logger.info("\n[3/4] EXEMPLO 3: Busca Histórica (2010-2017)")
    levantamento.buscar_multiplas_fontes(
        termo="políticas educacionais determinantes",
        ano_inicio=2010,
        ano_fim=2017,
        limite_por_fonte=20
    )

    # ========== ESTATÍSTICAS GERAIS ==========
    logger.info("\n[4/4] Gerando Estatísticas e Relatórios")
    stats = levantamento.obter_estatisticas()

    logger.info("\n" + "=" * 70)
    logger.info("ESTATÍSTICAS GERAIS")
    logger.info("=" * 70)
    logger.info(f"Total de artigos coletados: {stats.get('Total de Artigos', 0)}")
    logger.info(f"Período coberto: {stats.get('Período', 'N/A')}")
    logger.info(f"Citações totais: {stats.get('Citações Totais', 0)}")
    logger.info(f"Citações médias: {stats.get('Citações Médias', 0)}")
    logger.info(f"Fontes de dados: {', '.join(stats.get('Fontes de Dados', []))}")

    # ========== FILTROS E ANÁLISES ==========
    logger.info("\n" + "=" * 70)
    logger.info("ANÁLISES FILTRADAS")
    logger.info("=" * 70)

    # Artigos mais relevantes (com pelo menos 10 citações, após 2018)
    logger.info("\nArtigos mais relevantes (≥10 citações, 2018+):")
    df_relevantes = levantamento.filtrar_artigos(
        citacoes_minimas=10,
        ano_inicio=2018
    )
    logger.info(f"Encontrados: {len(df_relevantes)} artigos")

    if not df_relevantes.empty:
        for idx, (_, row) in enumerate(df_relevantes.head(5).iterrows(), 1):
            logger.info(f"\n  [{idx}] {row['Título'][:70]}")
            logger.info(f"      Citações: {row['Citações']} | Ano: {row['Ano']} | Fonte: {row['Fonte']}")

    # ========== EXPORTAÇÕES ==========
    logger.info("\n" + "=" * 70)
    logger.info("EXPORTANDO RESULTADOS")
    logger.info("=" * 70 + "\n")

    # Exportar em múltiplos formatos
    levantamento.exportar(
        "levantamento_bibliografico.csv",
        formato=TipoExportacao.CSV
    )

    levantamento.exportar(
        "levantamento_bibliografico.json",
        formato=TipoExportacao.JSON
    )

    levantamento.exportar(
        "referencias.bib",
        formato=TipoExportacao.BIBTEX
    )

    # Gerar relatório HTML visual
    levantamento.gerar_relatorio_html()

    # Salvar cache para futuras consultas
    levantamento._salvar_cache()

    logger.info("\n" + "=" * 70)
    logger.info("✓ LEVANTAMENTO CONCLUÍDO COM SUCESSO!")
    logger.info("=" * 70 + "\n")

    logger.info("Arquivos gerados:")
    logger.info("  - levantamento_bibliografico_[timestamp].csv")
    logger.info("  - levantamento_bibliografico_[timestamp].json")
    logger.info("  - referencias_[timestamp].bib")
    logger.info("  - relatorio_bibliografico_[timestamp].html")
    logger.info("  - levantamento_bibliografico.log")
    logger.info("  - cache_artigos.pkl\n")