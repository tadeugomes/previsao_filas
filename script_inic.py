import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import re
import time
import urllib3
from io import StringIO
import unicodedata

# Suprime avisos de SSL se necessÃ¡rio (sites governamentais Ã s vezes tÃªm certificados estranhos)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ItaquiMonitor:
    def __init__(self):
        self.emap_base_url = "https://www.portodoitaqui.com"
        self.emap_endpoint = f"{self.emap_base_url}/porto-agora/navios/esperados"
        self.apem_endpoint = "http://www.apem-ma.com.br/?module=berthedships"
        
        # User-Agent robusto para evitar bloqueios simples
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

    def _get_timestamp(self):
        """Retorna timestamp atual string para logs."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _clean_column_name(self, col_name):
        """Padroniza nomes de colunas (lowercase, sem espacos)."""
        base = str(col_name).strip().lower().replace(' ', '_').replace('/', '_').replace('.', '')
        base = ''.join(
            ch for ch in unicodedata.normalize('NFKD', base)
            if not unicodedata.combining(ch)
        )
        return base

    def _normalize_ship_name(self, name):
        """
        Normaliza nomes de navios para facilitar o cruzamento (JOIN).
        Remove espaÃ§os extras, transforma em maiÃºsculas e remove caracteres especiais comuns.
        Ex: ' MV. BLUE FIN ' -> 'BLUEFIN'
        """
        if pd.isna(name): return ""
        clean = str(name).upper().strip()
        clean = re.sub(r'[^A-Z0-9]', '', clean) # MantÃ©m apenas letras e nÃºmeros
        return clean

    # ---------------------------------------------------------
    # MÃDULO 1: EMAP (Porto do Itaqui Oficial)
    # ---------------------------------------------------------
    def fetch_emap_data(self):
        print(f"[{self._get_timestamp()}] >>> Iniciando coleta EMAP...")
        try:
            response = requests.get(self.emap_endpoint, headers=self.headers, verify=False, timeout=20)
            response.raise_for_status()
            
            # O Pandas extrai todas as tabelas encontradas no HTML
            dfs = pd.read_html(StringIO(response.text), flavor='bs4')
            
            if not dfs:
                print("ERRO EMAP: Nenhuma tabela encontrada na pÃ¡gina.")
                return None

            # Concatena todas as tabelas (Esperados, Atracados, Fundeados)
            # Geralmente a estrutura de colunas Ã© similar
            combined_df = pd.concat(dfs, ignore_index=True)
            
            # Limpeza de cabeÃ§alhos
            combined_df.columns = [self._clean_column_name(c) for c in combined_df.columns]
            
            # Cria coluna normalizada para chave de cruzamento
            if 'navio' in combined_df.columns:
                combined_df['join_key'] = combined_df['navio'].apply(self._normalize_ship_name)
            
            combined_df['source_system'] = 'EMAP'
            combined_df['extracted_at'] = self._get_timestamp()
            
            print(f"[{self._get_timestamp()}] Sucesso EMAP: {len(combined_df)} registros encontrados.")
            return combined_df

        except Exception as e:
            print(f"ERRO CRÃTICO NA COLETA EMAP: {e}")
            return None

    def check_emap_pdf_updates(self):
        """Verifica se hÃ¡ novos PDFs oficiais de programaÃ§Ã£o."""
        print(f"[{self._get_timestamp()}] >>> Verificando PDFs Oficiais EMAP...")
        try:
            response = requests.get(self.emap_endpoint, headers=self.headers, verify=False, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Busca links que contenham padrÃµes de data atual e palavras-chave
            today_dia = datetime.now().strftime("%d") # Ex: 17
            today_mes = datetime.now().strftime("%m") # Ex: 01
            
            # Procura links (<a>) que tenham 'mapa' e 'atrac' no href ou texto
            # E que contenham o dia de hoje (filtro simples)
            candidates = soup.find_all('a', href=re.compile(r'mapa.*atrac', re.IGNORECASE))
            
            new_files = []
            for link in candidates:
                txt = (link.get_text() + str(link.get('href'))).lower()
                # Verifica se a data de hoje estÃ¡ presente (formato flexÃ­vel)
                if today_dia in txt and today_mes in txt:
                    full_url = link.get('href')
                    if not full_url.startswith('http'):
                        full_url = f"{self.emap_base_url}{full_url}" if full_url.startswith('/') else f"{self.emap_base_url}/{full_url}"
                    
                    new_files.append({
                        'doc_name': link.get_text().strip(),
                        'url': full_url,
                        'found_at': self._get_timestamp()
                    })
            
            return new_files

        except Exception as e:
            print(f"Erro ao verificar PDFs: {e}")
            return []

    # ---------------------------------------------------------
    # MÃDULO 2: APEM (AssociaÃ§Ã£o dos PrÃ¡ticos)
    # ---------------------------------------------------------
    def fetch_apem_data(self):
        print(f"[{self._get_timestamp()}] >>> Iniciando coleta APEM (PrÃ¡ticos)...")
        try:
            # APEM Ã© HTTP puro, sem SSL
            response = requests.get(self.apem_endpoint, headers=self.headers, timeout=15)
            
            # Dica: Use match='BerÃ§o' para pegar apenas tabelas que tenham essa coluna
            # Isso filtra tabelas de layout ou menus que o pandas poderia pegar errado
            dfs = pd.read_html(StringIO(response.text), match='Berco', flavor='bs4')
            
            if not dfs:
                print("AVISO APEM: Nenhuma tabela de navios detectada.")
                return None
            
            processed_dfs = []
            for df in dfs:
                # Limpa colunas
                df.columns = [self._clean_column_name(c) for c in df.columns]
                
                # Verifica se Ã© uma tabela de dados vÃ¡lida
                if 'navio' in df.columns and 'berco' in df.columns:
                    # Remove linhas sujas (cabeÃ§alhos repetidos no meio da tabela)
                    valid_rows = df[df['navio'].notna() & (df['navio'].str.lower() != 'navio')].copy()
                    
                    if not valid_rows.empty:
                        # Cria chave normalizada
                        valid_rows['join_key'] = valid_rows['navio'].apply(self._normalize_ship_name)
                        processed_dfs.append(valid_rows)
            
            if processed_dfs:
                final_apem = pd.concat(processed_dfs, ignore_index=True)
                final_apem['source_system'] = 'APEM'
                final_apem['extracted_at'] = self._get_timestamp()
                print(f"[{self._get_timestamp()}] Sucesso APEM: {len(final_apem)} navios atracados.")
                return final_apem
            else:
                return None

        except Exception as e:
            print(f"ERRO CRÃTICO NA COLETA APEM: {e}")
            return None

    # ---------------------------------------------------------
    # ORQUESTRAÃÃO E UNIFICAÃÃO
    # ---------------------------------------------------------
    def run_full_etl(self):
        # 1. Busca dados
        df_emap = self.fetch_emap_data()
        df_apem = self.fetch_apem_data()
        
        # 2. Verifica PDFs (apenas imprime URL por enquanto)
        pdfs = self.check_emap_pdf_updates()
        if pdfs:
            print("\n=== NOVOS DOCUMENTOS OFICIAIS ===")
            for p in pdfs:
                print(f"[PDF] {p['doc_name']} -> {p['url']}")
            print("=================================\n")

        # 3. ConsolidaÃ§Ã£o (Merge)
        # Objetivo: Ter uma tabela mestre. 
        # Base = EMAP (que tem esperados e atracados).
        # Enriquecimento = APEM (confirmaÃ§Ã£o de atracaÃ§Ã£o real).
        
        if df_emap is None:
            print("Falha na fonte principal (EMAP). Abortando merge.")
            return

        final_df = df_emap.copy()

        if df_apem is not None and not df_apem.empty:
            print("Cruzando dados para enriquecimento...")

            # Seleciona colunas uteis da APEM para evitar duplicidade
            # Ex: Queremos saber a hora exata que o pratico informou ('data', 'hora')
            cols_apem = ['join_key', 'data', 'hora', 'berco']

            # Renomeia para nao colidir no merge
            missing_cols = [c for c in cols_apem if c not in df_apem.columns]
            if missing_cols:
                print(f"APEM sem colunas esperadas: {missing_cols}. Pulando enriquecimento.")
                df_apem_clean = None
            else:
                df_apem_clean = df_apem[cols_apem].rename(columns={
                    'data': 'apem_data_real',
                    'hora': 'apem_hora_real',
                    'berco': 'apem_berco_confirmado'
                })

            # Remove duplicatas de navio na APEM antes do merge (pega o ultimo registro se houver duplicidade)
            df_apem_clean = df_apem_clean.drop_duplicates(subset=['join_key'], keep='last') if df_apem_clean is not None else None

            # Left Join: Mantem todos da EMAP, traz dados da APEM onde der match
            if df_apem_clean is not None:
                final_df = pd.merge(
                    final_df,
                    df_apem_clean,
                    on='join_key',
                    how='left'
                )

            # Cria flag de consistencia
            # Se tem dados na APEM, o status na EMAP deveria ser algo como 'ATRACADO'
            # Se estiver 'ESPERADO' na EMAP mas tem match na APEM, e um 'atraso de informacao' do porto
            if 'apem_data_real' in final_df.columns:
                final_df['alert_delay_info'] = final_df.apply(
                    lambda row: 1 if pd.notna(row['apem_data_real']) and 'esperado' in str(row.get('situacao', '')).lower() else 0,
                    axis=1
                )

        # 4. ExibiÃ§Ã£o / ExportaÃ§Ã£o
        print("\n=== RESULTADO FINAL (Amostra) ===")
        
        # Seleciona colunas para visualizaÃ§Ã£o limpa
        display_cols = ['navio', 'situacao', 'berco', 'previsao', 'apem_data_real']
        # Filtra colunas que realmente existem no DF final (para evitar erro de chave)
        valid_cols = [c for c in display_cols if c in final_df.columns]
        
        print(final_df[valid_cols].head(10).to_string(index=False))
        
        # Exemplo de salvamento
        final_df.to_csv(
            f"itaqui_full_data_{datetime.now().strftime('%Y%m%d_%H')}.csv",
            index=False,
            encoding='utf-8-sig'
        )
        return final_df

if __name__ == "__main__":
    bot = ItaquiMonitor()
    data = bot.run_full_etl()
    # Aqui vocÃª pode adicionar lÃ³gica para salvar os dados, enviar alertas, etc.
