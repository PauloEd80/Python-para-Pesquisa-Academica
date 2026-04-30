from scholarly import scholarly, ProxyGenerator
import pandas as pd
import time


class LevantamentoBibliografico:
    def __init__(self):
        self.resultados = []

    def realizar_busca(self, query, limite_resultados=10):
        print(f"Iniciando busca por: {query}...")

        # Realiza a pesquisa no Google Acadêmico
        search_query = scholarly.search_pubs(query)

        for i, resultado in enumerate(search_query):
            if i >= limite_resultados:
                break

            # Extração tratada dos metadados
            bib = resultado.get('bib', {})
            dados_artigo = {
                'Título': bib.get('title', 'N/A'),
                'Autor(es)': ", ".join(bib.get('author', [])),
                'Ano': bib.get('pub_year', 'N/A'),
                'Veículo': bib.get('venue', 'N/A'),
                'Resumo': bib.get('abstract', 'N/A'),
                'Link': resultado.get('pub_url', 'N/A'),
                'Citações': resultado.get('num_citations', 0)
            }

            self.resultados.append(dados_artigo)
            print(f"[{i + 1}] Coletado: {dados_artigo['Título'][:50]}...")

            # Delay ético para evitar bloqueio de IP
            time.sleep(10)

    def exportar_csv(self, nome_arquivo="levantamento.csv"):
        if not self.resultados:
            print("Nenhum dado para exportar.")
            return

        df = pd.DataFrame(self.resultados)
        df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig')
        print(f"\nSucesso! Arquivo '{nome_arquivo}' gerado com {len(df)} registros.")


# --- Execução do Script ---
if __name__ == "__main__":
    app = LevantamentoBibliografico()

    # Exemplo de busca focada em sua área de pesquisa
    termo_busca = 'Abandono AND "Desigualdade de Acesso." AND Determinantes Institucionais.'

    app.realizar_busca(termo_busca, limite_resultados=20)
    app.exportar_csv("bibliografia_doutorado.csv")