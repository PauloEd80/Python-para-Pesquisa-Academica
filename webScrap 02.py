from scholarly import scholarly, ProxyGenerator
import pandas as pd
import time
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class LevantamentoBibliografico:
    def __init__(self, usar_proxy=False):
        self.resultados = []
        self.logger = logging.getLogger(__name__)

        # Configurar proxy se necessário (evita bloqueio IP)
        if usar_proxy:
            pg = ProxyGenerator()
            pg.SingleProxy(proxy="socks5://127.0.0.1:9050")
            scholarly.use_proxy(pg)

    def realizar_busca(self, query, limite_resultados=10, delay_min=5, delay_max=20):
        """
        Realiza busca com tratamento robusto de erros

        Args:
            query: Termo de busca
            limite_resultados: Máximo de artigos
            delay_min/max: Intervalo aleatório entre requisições
        """
        self.logger.info(f"Iniciando busca por: {query}")

        try:
            search_query = scholarly.search_pubs(query)
            coletados = 0

            for resultado in search_query:
                if coletados >= limite_resultados:
                    break

                try:
                    # Extração segura dos metadados
                    bib = resultado.get('bib', {})
                    autores = bib.get('author', [])

                    dados_artigo = {
                        'Título': bib.get('title', 'N/A'),
                        'Autor(es)': ', '.join(autores) if autores else 'N/A',
                        'Ano': bib.get('pub_year', 'N/A'),
                        'Veículo': bib.get('venue', 'N/A'),
                        'Resumo': bib.get('abstract', 'N/A'),
                        'Link': resultado.get('pub_url', 'N/A'),
                        'Citações': resultado.get('num_citations', 0),
                        'DOI': bib.get('doi', 'N/A')
                    }

                    # Validação mínima
                    if dados_artigo['Título'] != 'N/A':
                        self.resultados.append(dados_artigo)
                        coletados += 1
                        self.logger.info(
                            f"[{coletados}/{limite_resultados}] {dados_artigo['Título'][:50]}..."
                        )

                except Exception as e:
                    self.logger.warning(f"Erro ao processar artigo: {e}")
                    continue

                # Delay aleatório para evitar bloqueio
                delay = time.sleep(delay_min + (delay_max - delay_min) *
                                   (coletados / max(limite_resultados, 1)))

        except Exception as e:
            self.logger.error(f"Erro na busca: {e}")
            raise

    def exportar_csv(self, nome_arquivo="levantamento.csv"):
        """Exporta resultados para CSV com timestamp"""
        if not self.resultados:
            self.logger.warning("Nenhum dado para exportar")
            return False

        try:
            df = pd.DataFrame(self.resultados)

            # Adicionar timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_final = nome_arquivo.replace('.csv', f'_{timestamp}.csv')

            df.to_csv(nome_final, index=False, encoding='utf-8-sig')
            self.logger.info(
                f"✓ Arquivo '{nome_final}' gerado com {len(df)} registros"
            )
            return True

        except Exception as e:
            self.logger.error(f"Erro ao exportar: {e}")
            return False

    def obter_estatisticas(self):
        """Retorna estatísticas dos resultados"""
        if not self.resultados:
            return None

        df = pd.DataFrame(self.resultados)
        return {
            'Total': len(df),
            'Anos': df['Ano'].value_counts().to_dict(),
            'Citações médias': df['Citações'].mean(),
            'Artigos sem resumo': (df['Resumo'] == 'N/A').sum()
        }


# --- Execução ---
if __name__ == "__main__":
    # Opções de busca mais simples
    buscas = [
        'Abandono escolar desigualdade',
        'Determinantes institucionais educação',
        'Acesso educacional Brasil'
    ]

    app = LevantamentoBibliografico(usar_proxy=False)

    for termo in buscas:
        try:
            app.realizar_busca(termo, limite_resultados=5)
        except Exception as e:
            print(f"Erro na busca '{termo}': {e}")

    app.exportar_csv("bibliografia_doutorado.csv")

    # Exibir estatísticas
    stats = app.obter_estatisticas()
    if stats:
        print(f"\n📊 Estatísticas:\n{stats}")