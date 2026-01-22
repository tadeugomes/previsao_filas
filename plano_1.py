import json
import pickle
import joblib
import warnings
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import unicodedata
import re
from google.cloud import bigquery
import lightgbm as lgb
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
)

warnings.filterwarnings('ignore')

AIS_FEATURES_PATH = Path("data/ais_features.parquet")
PORT_MAPPING_PATH = Path("data/port_mapping.csv")
MARE_DIR = Path("data/mare_clima")
MARE_CLIMA_DATASET_1 = MARE_DIR / "portos_brasil_historico_portos_hibridos.parquet"
MARE_CLIMA_DATASET_2 = MARE_DIR / "dados_historicos_complementares_portos_oceanicos_v2.parquet"
MARE_CLIMA_DATASET_3 = MARE_DIR / "dados_historicos_portos_hibridos_arco_norte_v4_real.parquet"
MARE_PORT_FILE_BY_NORM = {
    "ANTONINA": "antonina_extremos_2020_2026.csv",
    "BARCARENA": "barcarena_extremos_2020_2026.csv",
    "ITAQUI": "itaqui_extremos_2020_2026.csv",
    "PARANAGUA": "paranagua_extremos_2020_2026.csv",
    "PECEM": "pecem_extremos_2020_2026.csv",
    "RECIFE": "recife_extremos_2020_2026.csv",
    "RIOGRANDE": "riograande_extremos_2020_2026.csv",
    "SALVADOR": "salvador_extremos_2020_2026.csv",
    "SANTOS": "santos_extremos_2020_2026.csv",
    "SUAPE": "suape_extremos_2020_2026.csv",
    "VILADOCONDE": "viladoconde_extremos_2020_2026.csv",
}
UF_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def _env_flag(name, default=True):
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


USE_MARE_FEATURES = _env_flag("USE_MARE_FEATURES", True)
USE_MARE_CLIMA = _env_flag("USE_MARE_CLIMA", True)
SAVE_MODELS = _env_flag("SAVE_MODELS", True)


class EnsembleRegressor:
    def __init__(self, lgb_model, xgb_model):
        self.lgb_model = lgb_model
        self.xgb_model = xgb_model

    def predict(self, X, X_lgb=None):
        if X_lgb is None:
            X_lgb = X
        pred_lgb = np.expm1(self.lgb_model.predict(X_lgb))
        pred_xgb = self.xgb_model.predict(X)
        return (pred_lgb + pred_xgb) / 2.0

# Perfis de modelagem por mercadoria (ajustar conforme base)
PROFILES_TO_RUN = ["VEGETAL"]

# HS/mercadoria (cdmercadoria) conforme mapeamento SH4
CARGA_PROFILES = {
    'VEGETAL': [
        '1201',  # soja
        '1005',  # milho
        '1701',  # acucar
        '2304',  # farelo de soja
        '1001',  # trigo
        '1003',  # cevada
        '1006',  # arroz
        '1107',  # malte
        '2302',  # farelos diversos
        '2306',  # tortas de oleaginosas
        '1205',  # colza
        '1206',  # girassol
    ],
    'MINERAL': [
        '2601',  # minerio de ferro
        '2606',  # bauxita
        '2602',  # manganes
        '2501',  # sal
        '2523',  # cimento/clinker
        '2603',  # cobre
        '2510',  # fosfatos naturais
    ],
    'FERTILIZANTE': [
        '3102',  # nitrogenados (ureia)
        '3104',  # potassicos (kcl)
        '3105',  # compostos (npk)
        '3103',  # fosfatados
        '3101',  # organicos
    ],
}

def extrair_dados_antaq_carga(project_id='antaqdados'):
    """Extrai dados de atracacao e carga da ANTAQ."""
    client = bigquery.Client(project=project_id)
    query = """
    WITH carga_agregada AS (
        SELECT
            idatracacao,
            ARRAY_AGG(
                tipo_operacao_da_carga
                ORDER BY SAFE_CAST(REPLACE(REPLACE(vlpesocargabruta, '.', ''), ',', '.') AS FLOAT64) DESC
                LIMIT 1
            )[OFFSET(0)] AS tipo_carga,
            ARRAY_AGG(
                natureza_da_carga
                ORDER BY SAFE_CAST(REPLACE(REPLACE(vlpesocargabruta, '.', ''), ',', '.') AS FLOAT64) DESC
                LIMIT 1
            )[OFFSET(0)] AS natureza_carga,
            ARRAY_AGG(
                cdmercadoria
                ORDER BY SAFE_CAST(REPLACE(REPLACE(vlpesocargabruta, '.', ''), ',', '.') AS FLOAT64) DESC
                LIMIT 1
            )[OFFSET(0)] AS cdmercadoria,
            ARRAY_AGG(
                stsh4
                ORDER BY SAFE_CAST(REPLACE(REPLACE(vlpesocargabruta, '.', ''), ',', '.') AS FLOAT64) DESC
                LIMIT 1
            )[OFFSET(0)] AS stsh4,
            SUM(SAFE_CAST(REPLACE(REPLACE(vlpesocargabruta, '.', ''), ',', '.') AS FLOAT64)) AS movimentacao_total_toneladas
        FROM
            `antaqdados.br_antaq_estatistico_aquaviario.carga`
        WHERE
            vlpesocargabruta IS NOT NULL
        GROUP BY
            idatracacao
    )
    SELECT
        a.idatracacao,
        a.data_chegada,
        a.data_atracacao,
        SAFE_CAST(a.ano AS INT64) AS ano,
        CASE LOWER(a.mes)
            WHEN 'jan' THEN 1
            WHEN 'fev' THEN 2
            WHEN 'mar' THEN 3
            WHEN 'abr' THEN 4
            WHEN 'mai' THEN 5
            WHEN 'jun' THEN 6
            WHEN 'jul' THEN 7
            WHEN 'ago' THEN 8
            WHEN 'set' THEN 9
            WHEN 'out' THEN 10
            WHEN 'nov' THEN 11
            WHEN 'dez' THEN 12
            ELSE NULL
        END AS mes,
        a.porto_atracacao AS nome_porto,
        a.terminal AS nome_terminal,
        a.tipo_de_navegacao_da_atracacao AS tipo_navegacao,
        a.tipo_de_operacao,
        a.municipio,
        a.sguf AS uf,
        c.tipo_carga,
        c.natureza_carga,
        c.cdmercadoria,
        c.stsh4,
        c.movimentacao_total_toneladas
    FROM
        `antaqdados.br_antaq_estatistico_aquaviario.atracacao` a
    LEFT JOIN
        carga_agregada c
    ON
        a.idatracacao = c.idatracacao
    WHERE
        a.data_chegada IS NOT NULL
        AND a.data_atracacao IS NOT NULL
        AND SAFE_CAST(a.ano AS INT64) >= 2020
        AND CASE LOWER(a.mes)
            WHEN 'jan' THEN 1
            WHEN 'fev' THEN 2
            WHEN 'mar' THEN 3
            WHEN 'abr' THEN 4
            WHEN 'mai' THEN 5
            WHEN 'jun' THEN 6
            WHEN 'jul' THEN 7
            WHEN 'ago' THEN 8
            WHEN 'set' THEN 9
            WHEN 'out' THEN 10
            WHEN 'nov' THEN 11
            WHEN 'dez' THEN 12
            ELSE NULL
        END IS NOT NULL
    ORDER BY
        a.data_chegada
    """
    print("[1/4] Extraindo dados ANTAQ...")
    df = client.query(query).to_dataframe()
    print(f"    OK. {len(df):,} registros")
    return df


def extrair_dados_climaticos(project_id='antaqdados', station_ids=None):
    """Extrai dados meteorologicos do INMET via Base dos Dados."""
    client = bigquery.Client(project=project_id)
    station_filter = ""
    if station_ids:
        station_list = ",".join([f"'{sid}'" for sid in station_ids])
        station_filter = f"AND id_estacao IN ({station_list})"
    query = """
    SELECT
        CAST(ano AS INT64) AS ano,
        CAST(mes AS INT64) AS mes,
        data,
        id_estacao,
        AVG(temperatura_bulbo_hora) AS temp_media_dia,
        MAX(temperatura_max) AS temp_max_dia,
        MIN(temperatura_min) AS temp_min_dia,
        SUM(precipitacao_total) AS precipitacao_dia,
        MAX(vento_rajada_max) AS vento_rajada_max_dia,
        AVG(vento_velocidade) AS vento_velocidade_media,
        AVG(umidade_rel_hora) AS umidade_media_dia
    FROM
        `basedosdados.br_inmet_bdmep.microdados`
    WHERE
        CAST(ano AS INT64) >= 2020
        {station_filter}
    GROUP BY
        ano, mes, data, id_estacao
    """.format(station_filter=station_filter)
    print("[2/4] Extraindo dados climaticos (INMET)...")
    df_clima = client.query(query).to_dataframe()
    print(f"    OK. {len(df_clima):,} registros")
    return df_clima


def extrair_dados_producao_agricola(project_id='antaqdados'):
    """Extrai producao agricola municipal (PAM - IBGE)."""
    client = bigquery.Client(project=project_id)
    query = """
    SELECT
        ano,
        sigla_uf,
        id_municipio,
        produto,
        quantidade_produzida,
        area_plantada,
        area_colhida,
        rendimento_medio_producao,
        valor_producao
    FROM
        `basedosdados.br_ibge_pam.lavoura_temporaria`
    WHERE
        ano >= 2020
        AND LOWER(REGEXP_REPLACE(NORMALIZE(produto, NFD), r'\\pM', '')) IN (
            'soja (em grao)',
            'milho (em grao)',
            'algodao herbaceo (em caroco)',
            'cana-de-acucar'
        )
    ORDER BY
        ano, produto
    """
    print("[3/4] Extraindo producao agricola (PAM/IBGE)...")
    df_pam = client.query(query).to_dataframe()
    print(f"    OK. {len(df_pam):,} registros")
    return df_pam


def extrair_precos_commodities():
    """Extrai precos de commodities via API IPEA."""
    print("[4/4] Extraindo precos de commodities (IPEA)...")
    commodities = [
        ('PRECOS12_PSOIM12', 'Soja'),
        ('PRECOS12_PMIM12', 'Milho'),
        ('PRECOS12_PALG12', 'Algodao')
    ]
    df_precos_list = []
    for codigo, nome in commodities:
        try:
            url = f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{codigo}')"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data['value'])
                df['data'] = pd.to_datetime(df['VALDATA'])
                df['preco'] = pd.to_numeric(df['VALVALOR'], errors='coerce')
                df['produto'] = nome
                df = df[['data', 'preco', 'produto']].dropna()
                df_precos_list.append(df)
                print(f"    OK. {nome}: {len(df)} registros")
        except Exception:
            print(f"    WARN. {nome}: API indisponivel")
    if df_precos_list:
        df_precos = pd.concat(df_precos_list, ignore_index=True)
        print(f"    OK. Total: {len(df_precos):,} registros")
        return df_precos
    print("    WARN. Modo fallback: precos nao disponiveis")
    return None


def integrar_clima_com_atracacao(df_antaq, df_clima):
    """Join entre atracacao e clima por data + estacao."""
    print("Integrando clima com atracacoes...")
    df_antaq['data_chegada_date'] = pd.to_datetime(
        df_antaq['data_chegada'], dayfirst=True, errors='coerce'
    ).dt.date
    df_clima['data'] = pd.to_datetime(df_clima['data'], dayfirst=True, errors='coerce').dt.date
    df_clima_clean = df_clima.drop(columns=['ano', 'mes'], errors='ignore')
    df = df_antaq.merge(
        df_clima_clean,
        left_on=['data_chegada_date', 'id_estacao'],
        right_on=['data', 'id_estacao'],
        how='left'
    )
    print(f"    OK. {len(df):,} registros")
    return df


def filtrar_granel_solido(df):
    """Filtra apenas cargas de granel solido."""
    df = df.copy()
    natureza_norm = df['natureza_carga'].apply(normalizar_texto)
    mask = natureza_norm.str.contains('GRANELSOLIDO', na=False)
    return df[mask]


def filtrar_por_cdmercadoria(df, include_codes):
    """Filtra linhas com cdmercadoria na lista informada."""
    df = df.copy()
    mask = df['cdmercadoria'].isin(include_codes)
    return df[mask]


def normalizar_texto(valor):
    """Normaliza texto para comparacao simples."""
    if pd.isna(valor):
        return ""
    texto = str(valor).upper()
    texto = ''.join(ch for ch in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(ch))
    return re.sub(r'[^A-Z0-9]', '', texto)


def _normalizar_porto_base(nome_porto):
    """Remove prefixos comuns de porto para matching com dados de maré."""
    norm = normalizar_texto(nome_porto)
    for prefix in ("PORTODE", "PORTODO", "PORTO"):
        if norm.startswith(prefix):
            return norm[len(prefix):]
    return norm


def _normalizar_porto_clima(nome_porto):
    """Normaliza nome de porto (remove prefixos e UF) para clima.

    A remoção de UF só ocorre se o nome original continha parênteses
    (ex: 'Santos (SP)') indicando que a UF foi adicionada explicitamente,
    não quando faz parte do nome do porto (ex: 'Suape' não deve virar 'Sua').
    """
    if pd.isna(nome_porto):
        return ""
    original = str(nome_porto)
    norm = _normalizar_porto_base(nome_porto)
    # Só remove UF se o nome original tinha parênteses (ex: "Santos (SP)")
    # ou se tinha formato "NomeUF" colado (ex: "BarcarenaPA")
    has_parentheses = '(' in original
    has_uf_suffix = len(norm) > 4 and norm[-2:] in UF_CODES
    # Para nomes curtos (<=6 chars normalizados), não remover UF pois pode ser parte do nome
    if has_parentheses or (has_uf_suffix and len(norm) > 6):
        candidate = norm[:-2]
        # Verificar se a remoção não deixa um nome muito curto ou inválido
        if len(candidate) >= 3:
            norm = candidate
    return norm


def _resolver_arquivo_mare(nome_porto):
    """Retorna o arquivo de extremos de maré para o porto (se houver)."""
    if not nome_porto:
        return None
    norm = normalizar_texto(nome_porto)
    if norm in MARE_PORT_FILE_BY_NORM:
        return MARE_PORT_FILE_BY_NORM[norm]
    base = _normalizar_porto_base(nome_porto)
    return MARE_PORT_FILE_BY_NORM.get(base)


def _carregar_extremos_mare(caminho_csv):
    df = pd.read_csv(caminho_csv)
    if df.empty:
        return df
    df = df.rename(columns={'Data_Hora': 'data_hora', 'Altura_m': 'altura_m'})
    df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
    df['altura_m'] = pd.to_numeric(df['altura_m'], errors='coerce')
    df = df.dropna(subset=['data_hora', 'altura_m']).sort_values('data_hora')
    return df[['data_hora', 'altura_m']]


def _interpolar_mare_para_timestamps(df_extremos, timestamps):
    """Interpola maré astronômica para timestamps (linear entre extremos)."""
    out = pd.DataFrame(
        index=timestamps.index,
        data={
            'mare_astronomica': 0.0,
            'mare_subindo': 0,
            'mare_horas_ate_extremo': 0.0,
            'tem_mare_astronomica': 0,
        },
    )
    if df_extremos.empty:
        return out
    valid = timestamps.notna()
    if not valid.any():
        return out

    ts_df = pd.DataFrame({'ts': pd.to_datetime(timestamps[valid]), 'idx': timestamps[valid].index})
    ts_df = ts_df.sort_values('ts')
    extremos = df_extremos.rename(columns={'data_hora': 'ext_time', 'altura_m': 'ext_alt'})

    prev = pd.merge_asof(
        ts_df,
        extremos,
        left_on='ts',
        right_on='ext_time',
        direction='backward'
    ).rename(columns={'ext_time': 'prev_time', 'ext_alt': 'prev_alt'})

    next_ = pd.merge_asof(
        ts_df,
        extremos,
        left_on='ts',
        right_on='ext_time',
        direction='forward'
    ).rename(columns={'ext_time': 'next_time', 'ext_alt': 'next_alt'})

    joined = prev[['ts', 'idx', 'prev_time', 'prev_alt']].join(
        next_[['next_time', 'next_alt']]
    )

    delta = (joined['next_time'] - joined['prev_time']).dt.total_seconds()
    frac = (joined['ts'] - joined['prev_time']).dt.total_seconds() / delta
    altura = joined['prev_alt'] + (joined['next_alt'] - joined['prev_alt']) * frac

    invalid = delta.isna() | (delta == 0) | joined['prev_alt'].isna() | joined['next_alt'].isna()
    altura[invalid] = joined.loc[invalid, 'prev_alt']

    mare_subindo = (joined['next_alt'] > joined['prev_alt']).astype(int)
    horas_ate = (joined['next_time'] - joined['ts']).dt.total_seconds() / 3600.0

    res = pd.DataFrame(
        index=joined['idx'],
        data={
            'mare_astronomica': altura.to_numpy(),
            'mare_subindo': mare_subindo.to_numpy(),
            'mare_horas_ate_extremo': horas_ate.to_numpy(),
            'tem_mare_astronomica': (~invalid).astype(int).to_numpy(),
        },
    )
    out.loc[res.index, :] = res
    out = out.fillna(0.0)
    out['mare_subindo'] = out['mare_subindo'].astype(int)
    out['tem_mare_astronomica'] = out['tem_mare_astronomica'].astype(int)
    return out


def adicionar_features_mare(df):
    """Adiciona features de maré astronômica por porto."""
    df = df.copy()
    df['mare_astronomica'] = 0.0
    df['mare_subindo'] = 0
    df['mare_horas_ate_extremo'] = 0.0
    df['tem_mare_astronomica'] = 0

    if not MARE_DIR.exists():
        print("WARN. Pasta data/mare_clima nao encontrada; maré ignorada.")
        return df

    extremos_cache = {}
    df['porto_norm'] = df['nome_porto'].apply(_normalizar_porto_base)
    for porto_norm in df['porto_norm'].dropna().unique():
        arquivo = MARE_PORT_FILE_BY_NORM.get(porto_norm)
        if not arquivo:
            continue
        caminho = MARE_DIR / arquivo
        if not caminho.exists():
            continue
        if arquivo not in extremos_cache:
            extremos_cache[arquivo] = _carregar_extremos_mare(caminho)
        extremos = extremos_cache[arquivo]
        mask = df['porto_norm'] == porto_norm
        feats = _interpolar_mare_para_timestamps(extremos, df.loc[mask, 'data_chegada_dt'])
        df.loc[mask, ['mare_astronomica', 'mare_subindo', 'mare_horas_ate_extremo', 'tem_mare_astronomica']] = feats[
            ['mare_astronomica', 'mare_subindo', 'mare_horas_ate_extremo', 'tem_mare_astronomica']
        ].to_numpy()
    df = df.drop(columns=['porto_norm'], errors='ignore')
    return df


def _agregar_clima_diario(df, ts_col, port_col, precip_col=None, wind_speed_col=None, wind_gust_col=None):
    df = df.copy()
    df[ts_col] = pd.to_datetime(df[ts_col], errors='coerce')
    df = df.dropna(subset=[ts_col, port_col])
    df['data'] = df[ts_col].dt.date
    df['porto_norm'] = df[port_col].apply(_normalizar_porto_clima)

    agg_map = {}
    if precip_col and precip_col in df.columns:
        agg_map['mc_precip_dia'] = (precip_col, 'sum')
    if wind_speed_col and wind_speed_col in df.columns:
        agg_map['mc_wind_speed_media'] = (wind_speed_col, 'mean')
        agg_map['mc_wind_speed_max'] = (wind_speed_col, 'max')
    if wind_gust_col and wind_gust_col in df.columns:
        agg_map['mc_wind_gust_max'] = (wind_gust_col, 'max')

    if not agg_map:
        return pd.DataFrame(columns=['porto_norm', 'data'])

    agg = df.groupby(['porto_norm', 'data']).agg(**agg_map).reset_index()
    return agg


def carregar_clima_mare_clima_diario():
    """Carrega e agrega dados climáticos dos parquets mare_clima (diário)."""
    frames_inmet = []

    if MARE_CLIMA_DATASET_1.exists():
        cols = ['timestamp', 'station', 'precip', 'wind_speed', 'wind_gust']
        df1 = pd.read_parquet(MARE_CLIMA_DATASET_1, columns=cols)
        frames_inmet.append(
            _agregar_clima_diario(
                df1, ts_col='timestamp', port_col='station',
                precip_col='precip', wind_speed_col='wind_speed', wind_gust_col='wind_gust'
            )
        )

    if MARE_CLIMA_DATASET_3.exists():
        cols = ['timestamp', 'station', 'precip', 'wind_speed_10m']
        df3 = pd.read_parquet(MARE_CLIMA_DATASET_3, columns=cols)
        df3 = df3.rename(columns={'wind_speed_10m': 'wind_speed'})
        frames_inmet.append(
            _agregar_clima_diario(
                df3, ts_col='timestamp', port_col='station',
                precip_col='precip', wind_speed_col='wind_speed'
            )
        )

    df_inmet = pd.concat(frames_inmet, ignore_index=True) if frames_inmet else pd.DataFrame()
    if not df_inmet.empty:
        df_inmet = (
            df_inmet.groupby(['porto_norm', 'data'], as_index=False)
            .agg({
                'mc_precip_dia': 'sum',
                'mc_wind_speed_media': 'mean',
                'mc_wind_speed_max': 'max',
                'mc_wind_gust_max': 'max',
            })
        )

    df_era5 = pd.DataFrame()
    df_ocean = pd.DataFrame()
    if MARE_CLIMA_DATASET_2.exists():
        # Carregar vento para clima
        cols_wind = ['time', 'port', 'wind_speed_10m']
        df2 = pd.read_parquet(MARE_CLIMA_DATASET_2, columns=cols_wind)
        df2 = df2.rename(columns={'wind_speed_10m': 'wind_speed'})
        df_era5 = _agregar_clima_diario(
            df2, ts_col='time', port_col='port', wind_speed_col='wind_speed'
        )
        # Carregar features oceanográficas (ondas, frente fria)
        cols_ocean = ['time', 'port', 'wave_height', 'frente_fria', 'pressao_anomalia']
        try:
            df2_ocean = pd.read_parquet(MARE_CLIMA_DATASET_2, columns=cols_ocean)
            df2_ocean['time'] = pd.to_datetime(df2_ocean['time'], errors='coerce')
            df2_ocean = df2_ocean.dropna(subset=['time', 'port'])
            df2_ocean['data'] = df2_ocean['time'].dt.date
            df2_ocean['porto_norm'] = df2_ocean['port'].apply(_normalizar_porto_clima)
            # Agregar por dia
            df_ocean = df2_ocean.groupby(['porto_norm', 'data']).agg(
                mc_wave_height_max=('wave_height', 'max'),
                mc_wave_height_media=('wave_height', 'mean'),
                mc_frente_fria=('frente_fria', 'max'),  # Se houve frente fria no dia
                mc_pressao_anomalia=('pressao_anomalia', 'mean'),
            ).reset_index()
        except Exception:
            df_ocean = pd.DataFrame()

    if df_inmet.empty and df_era5.empty:
        return pd.DataFrame()

    if df_inmet.empty:
        df_final = df_era5
    elif df_era5.empty:
        df_final = df_inmet
    else:
        df_final = df_inmet.merge(
            df_era5,
            on=['porto_norm', 'data'],
            how='outer',
            suffixes=('', '_era5')
        )
        for col in ['mc_wind_speed_media', 'mc_wind_speed_max']:
            era5_col = f"{col}_era5"
            if era5_col in df_final.columns:
                df_final[col] = df_final[col].fillna(df_final[era5_col])
        df_final = df_final.drop(columns=[c for c in df_final.columns if c.endswith('_era5')], errors='ignore')

    if 'mc_wind_gust_max' not in df_final.columns:
        df_final['mc_wind_gust_max'] = np.nan
    if 'mc_wind_speed_max' in df_final.columns:
        df_final['mc_wind_gust_max'] = df_final['mc_wind_gust_max'].fillna(df_final['mc_wind_speed_max'])

    # Integrar features oceanográficas (ondas, frente fria)
    if not df_ocean.empty:
        df_final = df_final.merge(
            df_ocean,
            on=['porto_norm', 'data'],
            how='left'
        )
    # Garantir colunas oceanográficas existem
    for col in ['mc_wave_height_max', 'mc_wave_height_media', 'mc_frente_fria', 'mc_pressao_anomalia']:
        if col not in df_final.columns:
            df_final[col] = np.nan

    return df_final


def integrar_clima_mare_clima(df):
    """Integra clima dos arquivos mare_clima para complementar o INMET."""
    df = df.copy()
    clima_mc = carregar_clima_mare_clima_diario()
    if clima_mc.empty:
        return df

    if 'data_chegada_date' not in df.columns:
        df['data_chegada_date'] = pd.to_datetime(df['data_chegada'], dayfirst=True, errors='coerce').dt.date
    df['porto_norm'] = df['nome_porto'].apply(_normalizar_porto_clima)

    merged = df.merge(
        clima_mc,
        left_on=['porto_norm', 'data_chegada_date'],
        right_on=['porto_norm', 'data'],
        how='left'
    )

    if 'precipitacao_dia' in merged.columns:
        merged['precipitacao_dia'] = merged['precipitacao_dia'].fillna(merged['mc_precip_dia'])
    if 'vento_rajada_max_dia' in merged.columns:
        merged['vento_rajada_max_dia'] = merged['vento_rajada_max_dia'].fillna(merged['mc_wind_gust_max'])
    if 'vento_velocidade_media' in merged.columns:
        merged['vento_velocidade_media'] = merged['vento_velocidade_media'].fillna(
            merged['mc_wind_speed_media']
        )

    # Criar features oceanográficas finais com valores default para portos sem dados
    merged['wave_height_max'] = merged.get('mc_wave_height_max', pd.Series([np.nan] * len(merged))).fillna(0.0)
    merged['wave_height_media'] = merged.get('mc_wave_height_media', pd.Series([np.nan] * len(merged))).fillna(0.0)
    merged['frente_fria'] = merged.get('mc_frente_fria', pd.Series([False] * len(merged))).fillna(False).astype(int)
    merged['pressao_anomalia'] = merged.get('mc_pressao_anomalia', pd.Series([np.nan] * len(merged))).fillna(0.0)

    # Criar feature de ressaca (ondas > 2.5m)
    merged['ressaca'] = (merged['wave_height_max'] > 2.5).astype(int)

    merged = merged.drop(columns=['porto_norm', 'data'], errors='ignore')
    return merged


def _load_port_mapping():
    if not PORT_MAPPING_PATH.exists():
        return {}
    mapping_df = pd.read_csv(PORT_MAPPING_PATH)
    if mapping_df.empty:
        return {}
    mapping_df = mapping_df.dropna(subset=['portname', 'nome_porto_antaq'])
    mapping_df['portname_norm'] = mapping_df['portname'].apply(normalizar_texto)
    mapping_df['nome_porto_norm'] = mapping_df['nome_porto_antaq'].apply(normalizar_texto)
    return dict(zip(mapping_df['nome_porto_norm'], mapping_df['portname_norm']))


def integrar_ais_features(df, ais_path=AIS_FEATURES_PATH):
    """Integra features AIS por porto/dia (agregadas)."""
    df = df.copy()
    feature_cols = [
        'ais_navios_no_raio',
        'ais_fila_ao_largo',
        'ais_velocidade_media_kn',
        'ais_eta_media_horas',
        'ais_dist_media_km',
    ]
    if not Path(ais_path).exists():
        print("WARN. AIS features nao encontradas; preenchendo zeros.")
        for col in feature_cols:
            df[col] = 0.0
        return df

    ais = (
        pd.read_parquet(ais_path)
        if str(ais_path).lower().endswith(".parquet")
        else pd.read_csv(ais_path, low_memory=False)
    )
    if ais.empty:
        for col in feature_cols:
            df[col] = 0.0
        return df

    if 'port_name' in ais.columns:
        ais_port_col = 'port_name'
    else:
        ais_port_col = 'portname'

    ais['date'] = pd.to_datetime(ais['date'], errors='coerce').dt.date
    ais = ais.dropna(subset=['date', ais_port_col])
    ais['portname_norm'] = ais[ais_port_col].apply(normalizar_texto)

    mapping = _load_port_mapping()
    df['porto_norm'] = df['nome_porto'].apply(normalizar_texto)
    df['ais_norm'] = df['porto_norm'].map(mapping).fillna(df['porto_norm'])
    df['data_chegada_date'] = df['data_chegada_dt'].dt.date

    merged = df.merge(
        ais[['date', 'portname_norm'] + feature_cols],
        left_on=['data_chegada_date', 'ais_norm'],
        right_on=['date', 'portname_norm'],
        how='left'
    )

    for col in feature_cols:
        merged[col] = merged[col].fillna(0.0)

    return merged.drop(
        columns=['date', 'portname_norm', 'ais_norm', 'porto_norm', 'data_chegada_date'],
        errors='ignore'
    )


def mapear_estacoes_por_municipio(df_antaq, project_id='antaqdados'):
    """Mapeia municipio para id_estacao usando tabela de estacoes do INMET."""
    client = bigquery.Client(project=project_id)
    query = """
    SELECT id_estacao, estacao
    FROM `basedosdados.br_inmet_bdmep.estacao`
    """
    df_est = client.query(query).to_dataframe()
    df_est['estacao_norm'] = df_est['estacao'].apply(normalizar_texto)
    estacoes = list(zip(df_est['estacao_norm'], df_est['id_estacao']))
    municipios = df_antaq['municipio'].dropna().unique()
    mapping = {}
    for municipio in municipios:
        muni_norm = normalizar_texto(municipio)
        match = None
        for estacao_norm, est_id in estacoes:
            if muni_norm and muni_norm in estacao_norm:
                match = est_id
                break
        mapping[municipio] = match
    return mapping


def aplicar_corte_percentil(df, col, group_col, p=0.95):
    """Corta valores acima do percentil por grupo."""
    df = df.copy()
    limites = df.groupby(group_col)[col].quantile(p).to_dict()
    df['limite_percentil'] = df[group_col].map(limites)
    df = df[df[col] <= df['limite_percentil']]
    return df.drop(columns=['limite_percentil'])


def classificar_espera(series):
    """Classifica espera em tercis (qcut) para balancear as classes."""
    return pd.qcut(series, q=3, labels=[0, 1, 2]).astype(int)


def integrar_producao_agricola(df, df_pam):
    """Agrega producao por ano/UF e integra."""
    print("Integrando producao agricola...")
    df_pam_uf = df_pam.groupby(['ano', 'sigla_uf', 'produto']).agg({
        'quantidade_produzida': 'sum',
        'valor_producao': 'sum',
        'area_plantada': 'sum'
    }).reset_index()
    df_pam_pivot = df_pam_uf.pivot_table(
        index=['ano', 'sigla_uf'],
        columns='produto',
        values='quantidade_produzida',
        aggfunc='sum'
    ).reset_index()
    df_pam_pivot.columns = [
        'ano', 'sigla_uf', 'producao_algodao',
        'producao_cana', 'producao_milho', 'producao_soja'
    ]
    df = df.merge(
        df_pam_pivot,
        left_on=['ano', 'uf'],
        right_on=['ano', 'sigla_uf'],
        how='left'
    )
    print("    OK. Producao integrada")
    return df


def integrar_precos_commodities(df, df_precos):
    """Adiciona precos mensais de commodities."""
    print("Integrando precos de commodities...")
    if df_precos is None:
        df['preco_soja_mensal'] = 100.0
        df['preco_milho_mensal'] = 50.0
        df['preco_algodao_mensal'] = 300.0
        print("    WARN. Usando valores fallback")
        return df
    df['ano_mes'] = pd.to_datetime(df['data_chegada']).dt.to_period('M')
    df_precos['ano_mes'] = pd.to_datetime(df_precos['data']).dt.to_period('M')
    df_precos_pivot = df_precos.pivot_table(
        index='ano_mes',
        columns='produto',
        values='preco',
        aggfunc='mean'
    ).reset_index()
    df_precos_pivot.columns = [
        'ano_mes', 'preco_algodao_mensal',
        'preco_milho_mensal', 'preco_soja_mensal'
    ]
    df = df.merge(df_precos_pivot, on='ano_mes', how='left')
    df['preco_soja_mensal'] = df['preco_soja_mensal'].ffill().fillna(100.0)
    df['preco_milho_mensal'] = df['preco_milho_mensal'].ffill().fillna(50.0)
    df['preco_algodao_mensal'] = df['preco_algodao_mensal'].ffill().fillna(300.0)
    print("    OK. Precos integrados")
    return df


def calcular_target(df):
    """Calcula tempo de espera em horas entre chegada e atracacao."""
    df = df.copy()
    df['data_chegada_dt'] = pd.to_datetime(df['data_chegada'], dayfirst=True, errors='coerce')
    df['data_atracacao_dt'] = pd.to_datetime(df['data_atracacao'], dayfirst=False, errors='coerce')
    delta = df['data_atracacao_dt'] - df['data_chegada_dt']
    df['tempo_espera_horas'] = delta.dt.total_seconds() / 3600.0
    df = df[df['tempo_espera_horas'].notna()]
    df = df[df['tempo_espera_horas'] >= 6]
    df = aplicar_corte_percentil(df, col='tempo_espera_horas', group_col='natureza_carga', p=0.95)
    return df


def criar_features_climaticas_avancadas(df):
    """Cria features derivadas do clima."""
    print("Criando features climaticas...")
    df['vento_rajada_max_dia'] = df['vento_rajada_max_dia'].fillna(5.0)
    df['vento_velocidade_media'] = df.get('vento_velocidade_media', np.nan)
    df['vento_velocidade_media'] = df['vento_velocidade_media'].fillna(3.0)
    df['precipitacao_dia'] = df['precipitacao_dia'].fillna(0.0)
    df['temp_media_dia'] = df['temp_media_dia'].fillna(25.0)
    df['temp_max_dia'] = df['temp_max_dia'].fillna(30.0)
    df['temp_min_dia'] = df['temp_min_dia'].fillna(20.0)
    df['umidade_media_dia'] = df['umidade_media_dia'].fillna(70.0)
    df['restricao_vento'] = np.where(
        (df['vento_rajada_max_dia'] > 18) &
        (df['nome_porto'].str.contains('ITAQUI', case=False, na=False)),
        1, 0
    )
    is_granel = df['tipo_carga'].str.contains('Granel', case=False, na=False)
    df['restricao_chuva'] = np.where(
        (df['precipitacao_dia'] > 2) & (is_granel),
        1, 0
    )
    df['amplitude_termica'] = df['temp_max_dia'] - df['temp_min_dia']
    return df


def criar_chuva_acumulada_ultimos_3dias(df):
    """Soma chuva de D-1, D-2 e D-3 por estacao."""
    print("Calculando chuva acumulada ultimos 3 dias...")
    df = df.sort_values(['id_estacao', 'data_chegada_date']).reset_index(drop=True)
    df['chuva_acumulada_ultimos_3dias'] = (
        df.groupby('id_estacao')['precipitacao_dia']
        .rolling(window=3, min_periods=1)
        .sum()
        .shift(1)
        .reset_index(level=0, drop=True)
    )
    df['chuva_acumulada_ultimos_3dias'] = df['chuva_acumulada_ultimos_3dias'].fillna(0.0)
    return df


def criar_features_commodities(df):
    """Identifica commodities e cria indices de mercado."""
    print("Criando features de commodities...")
    df['natureza_carga_norm'] = df['natureza_carga'].astype(str).str.upper()
    df['flag_celulose'] = df['natureza_carga_norm'].str.contains('CELULOSE|PASTA', na=False).astype(int)
    df['flag_algodao'] = df['natureza_carga_norm'].str.contains('ALGODAO', na=False).astype(int)
    df['flag_soja'] = df['natureza_carga_norm'].str.contains('SOJA', na=False).astype(int)
    df['flag_milho'] = df['natureza_carga_norm'].str.contains('MILHO', na=False).astype(int)
    df['periodo_safra'] = np.where(df['mes'].isin([3, 4, 5, 6]), 1, 0)
    df['producao_soja'] = df['producao_soja'].fillna(0)
    df['producao_milho'] = df['producao_milho'].fillna(0)
    df['producao_algodao'] = df['producao_algodao'].fillna(0)
    max_soja = df['producao_soja'].max() if df['producao_soja'].max() > 0 else 1
    max_milho = df['producao_milho'].max() if df['producao_milho'].max() > 0 else 1
    df['indice_pressao_soja'] = (
        (df['producao_soja'] / max_soja) *
        (df['preco_soja_mensal'] / df['preco_soja_mensal'].mean())
    )
    df['indice_pressao_milho'] = (
        (df['producao_milho'] / max_milho) *
        (df['preco_milho_mensal'] / df['preco_milho_mensal'].mean())
    )
    df['indice_pressao_soja'] = df['indice_pressao_soja'].fillna(0)
    df['indice_pressao_milho'] = df['indice_pressao_milho'].fillna(0)
    return df


def criar_features_temporais(df):
    """Features de sazonalidade."""
    df['dia_do_ano'] = df['data_chegada_dt'].dt.dayofyear
    df['trimestre'] = df['data_chegada_dt'].dt.quarter
    df['dia_semana'] = df['data_chegada_dt'].dt.dayofweek
    df['fim_de_semana'] = np.where(df['dia_semana'] >= 5, 1, 0)
    return df


def criar_target_encoding_porto(df):
    """Media historica de espera por porto (sem vazamento)."""
    print("Calculando target encoding por porto...")
    df = df.sort_values(['nome_porto', 'data_chegada_dt']).reset_index(drop=True)
    df['porto_tempo_medio_historico'] = (
        df.groupby('nome_porto')['tempo_espera_horas']
        .expanding()
        .mean()
        .shift(1)
        .reset_index(level=0, drop=True)
    )
    df['porto_tempo_medio_historico'] = df['porto_tempo_medio_historico'].fillna(
        df['tempo_espera_horas'].median()
    )
    return df


def calcular_densidade_fila(df):
    """Calcula densidade de fila por terminal."""
    print("Calculando densidade de fila...")
    df = df.sort_values(['nome_terminal', 'data_chegada_dt']).reset_index(drop=True)
    counts = (
        df.set_index('data_chegada_dt')
        .groupby('nome_terminal', sort=False)['idatracacao']
        .rolling('7D')
        .count()
        .reset_index(level=0, drop=True)
    )
    df['navios_na_fila_7d'] = counts.to_numpy()
    return df


def calcular_fila_no_momento(df):
    """Conta quantos navios estavam esperando no momento da chegada."""
    print("Calculando fila no momento da chegada...")
    df = df.sort_values(['nome_terminal', 'data_chegada_dt']).reset_index(drop=True)
    fila = np.zeros(len(df), dtype=float)
    for _, idx in df.groupby('nome_terminal', sort=False).groups.items():
        sub = df.loc[idx]
        chegadas = sub['data_chegada_dt'].to_numpy()
        atracacoes = sub['data_atracacao_dt'].to_numpy()
        order = np.argsort(chegadas)
        chegadas_sorted = chegadas[order]
        atracacoes_sorted = np.sort(atracacoes)
        for j, pos in enumerate(order):
            t = chegadas_sorted[j]
            arrivals_before = j
            departures_before = np.searchsorted(atracacoes_sorted, t, side='right')
            fila[idx[pos]] = max(arrivals_before - departures_before, 0)
    df['navios_no_fundeio_na_chegada'] = fila
    return df


def criar_lag_features(df):
    """Media movel do tempo de espera."""
    print("Criando lag features...")
    df = df.sort_values(['nome_terminal', 'data_chegada_dt']).reset_index(drop=True)
    df['tempo_espera_ma5'] = df.groupby('nome_terminal')['tempo_espera_horas'].transform(
        lambda x: x.rolling(5, min_periods=1).mean().shift(1)
    ).fillna(0)
    return df


def preparar_dados():
    """Pipeline de integracao e preparacao completo."""
    print("=" * 70)
    print("PIPELINE DE INTEGRACAO E PREPARACAO DE DADOS")
    print("=" * 70)
    df_antaq = extrair_dados_antaq_carga()
    df_antaq = filtrar_granel_solido(df_antaq)
    profile_key = PROFILE.upper()
    if profile_key in CARGA_PROFILES:
        df_antaq = filtrar_por_cdmercadoria(df_antaq, CARGA_PROFILES[profile_key])
    station_map = mapear_estacoes_por_municipio(df_antaq)
    df_antaq['id_estacao'] = df_antaq['municipio'].map(station_map)
    station_ids = [sid for sid in df_antaq['id_estacao'].dropna().unique()]
    df_clima = extrair_dados_climaticos(station_ids=station_ids)
    df_pam = extrair_dados_producao_agricola()
    df_precos = extrair_precos_commodities()
    df = integrar_clima_com_atracacao(df_antaq, df_clima)
    if USE_MARE_CLIMA:
        df = integrar_clima_mare_clima(df)
    df = integrar_producao_agricola(df, df_pam)
    df = integrar_precos_commodities(df, df_precos)
    print("=" * 70)
    print("FEATURE ENGINEERING")
    print("=" * 70)
    df = calcular_target(df)
    if PROFILE.upper() == "VEGETAL" and USE_MARE_FEATURES:
        df = adicionar_features_mare(df)
    df = criar_features_temporais(df)
    df = criar_target_encoding_porto(df)
    df = criar_features_climaticas_avancadas(df)
    if PROFILE.upper() == "VEGETAL":
        df = criar_chuva_acumulada_ultimos_3dias(df)
    df = criar_features_commodities(df)
    df = integrar_ais_features(df)
    df = calcular_fila_no_momento(df)
    df = calcular_densidade_fila(df)
    df = criar_lag_features(df)
    features = [
        'nome_porto', 'nome_terminal', 'tipo_navegacao', 'tipo_carga',
        'natureza_carga', 'cdmercadoria', 'stsh4',
        'movimentacao_total_toneladas', 'mes', 'dia_semana',
        'navios_no_fundeio_na_chegada', 'navios_na_fila_7d', 'tempo_espera_ma5',
        'dia_do_ano', 'porto_tempo_medio_historico',
        'temp_media_dia', 'precipitacao_dia', 'vento_rajada_max_dia', 'vento_velocidade_media',
        'umidade_media_dia', 'amplitude_termica',
        'restricao_vento', 'restricao_chuva',
        'flag_celulose', 'flag_algodao', 'flag_soja', 'flag_milho',
        'periodo_safra',
        'producao_soja', 'producao_milho', 'producao_algodao',
        'preco_soja_mensal', 'preco_milho_mensal', 'preco_algodao_mensal',
        'indice_pressao_soja', 'indice_pressao_milho',
        'ais_navios_no_raio', 'ais_fila_ao_largo', 'ais_velocidade_media_kn',
        'ais_eta_media_horas', 'ais_dist_media_km',
        # Features oceanográficas (ondas, frente fria)
        'wave_height_max', 'wave_height_media', 'frente_fria', 'pressao_anomalia', 'ressaca',
    ]
    if PROFILE.upper() == "VEGETAL":
        if USE_MARE_FEATURES:
            features.extend([
                'mare_astronomica', 'mare_subindo', 'mare_horas_ate_extremo',
                'tem_mare_astronomica'
            ])
        features.append('chuva_acumulada_ultimos_3dias')
    # Garantir que colunas oceanográficas existem (mesmo se USE_MARE_CLIMA=False)
    for col in ['wave_height_max', 'wave_height_media', 'frente_fria', 'pressao_anomalia', 'ressaca']:
        if col not in df.columns:
            df[col] = 0.0

    target = 'tempo_espera_horas'
    # Filtrar features que existem no dataframe
    available_features = [f for f in features if f in df.columns]
    missing_features = set(features) - set(available_features)
    if missing_features:
        print(f"WARN. Features não disponíveis (removidas): {missing_features}")
    features = available_features
    df_final = df[features + [target, 'data_chegada_dt']].dropna()
    print("=" * 70)
    print("RESUMO DO DATASET FINAL")
    print("=" * 70)
    print(f"OK. Registros: {len(df_final):,}")
    print(f"OK. Features: {len(features)}")
    print(f"OK. Periodo: {df_final['data_chegada_dt'].min()} ate {df_final['data_chegada_dt'].max()}")
    print("")
    print("Estatisticas do target (tempo de espera):")
    print(f"  Media:   {df_final[target].mean():.2f} horas")
    print(f"  Mediana: {df_final[target].median():.2f} horas")
    print(f"  Desvio:  {df_final[target].std():.2f} horas")
    print(f"  Minimo:  {df_final[target].min():.2f} horas")
    print(f"  Maximo:  {df_final[target].max():.2f} horas")
    return df_final, features, target


def gerar_splits_temporais(df, n_splits=3, gap_days=7):
    """Gera splits temporais com gap para evitar vazamento."""
    df = df.sort_values('data_chegada_dt').reset_index(drop=True)
    dates = pd.to_datetime(df['data_chegada_dt']).dt.normalize()
    unique_dates = np.sort(dates.dropna().unique())
    if len(unique_dates) < n_splits + 1:
        raise ValueError("Poucas datas unicas para criar splits temporais.")

    fold_sizes = np.array_split(unique_dates, n_splits + 1)
    splits = []
    gap = np.timedelta64(gap_days, 'D')

    for i in range(1, n_splits + 1):
        val_dates = fold_sizes[i]
        if len(val_dates) == 0:
            continue
        val_start = val_dates[0]
        val_end = val_dates[-1]
        train_end = val_start - gap
        train_idx = df.index[dates <= train_end].to_numpy()
        val_idx = df.index[(dates >= val_start) & (dates <= val_end)].to_numpy()
        if len(train_idx) == 0 or len(val_idx) == 0:
            continue
        splits.append((train_idx, val_idx))

    if len(splits) == 0:
        raise ValueError("Nao foi possivel criar splits temporais validos.")
    return splits


def treinar_modelo(df, features, target):
    """Treina modelo LightGBM com validacao temporal."""
    print("=" * 70)
    print("TREINAMENTO DO MODELO (LightGBM)")
    print("=" * 70)
    X = df[features].copy()
    y = df[target].copy()
    cat_features = [
        'nome_porto', 'nome_terminal', 'tipo_navegacao',
        'tipo_carga', 'natureza_carga', 'cdmercadoria', 'stsh4'
    ]
    for col in cat_features:
        X[col] = X[col].astype('category')
    splits = gerar_splits_temporais(df, n_splits=3, gap_days=7)
    mae_scores = []
    rmse_scores = []
    r2_scores = []
    print("Executando Time Series Cross-Validation (3 folds)...")
    for fold, (train_idx, val_idx) in enumerate(splits):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        model = lgb.LGBMRegressor(
            objective='regression',
            n_estimators=500,
            learning_rate=0.05,
            max_depth=7,
            num_leaves=31,
            min_child_samples=20,
            random_state=42,
            verbose=-1
        )
        y_train_log = np.log1p(y_train)
        y_val_log = np.log1p(y_val)
        model.fit(
            X_train, y_train_log,
            eval_set=[(X_val, y_val_log)],
            callbacks=[lgb.early_stopping(50, verbose=False)]
        )
        preds = np.expm1(model.predict(X_val))
        mae = mean_absolute_error(y_val, preds)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        r2 = r2_score(y_val, preds)
        mae_scores.append(mae)
        rmse_scores.append(rmse)
        r2_scores.append(r2)
        print(
            f"Fold {fold + 1}/3 -> MAE: {mae:.2f}h | RMSE: {rmse:.2f}h | R2: {r2:.3f}"
        )
    print("=" * 70)
    print("RESULTADO FINAL (Cross-Validation)")
    print("=" * 70)
    print(f"MAE medio:  {np.mean(mae_scores):.2f} +- {np.std(mae_scores):.2f} horas")
    print(f"RMSE medio: {np.mean(rmse_scores):.2f} +- {np.std(rmse_scores):.2f} horas")
    print(f"R2 medio:   {np.mean(r2_scores):.3f} +- {np.std(r2_scores):.3f}")
    print("Treinando modelo final com dataset completo...")
    model_final = lgb.LGBMRegressor(
        objective='regression',
        n_estimators=500,
        learning_rate=0.05,
        max_depth=7,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )
    model_final.fit(X, np.log1p(y))
    importance = pd.DataFrame({
        'feature': features,
        'importance': model_final.feature_importances_
    }).sort_values('importance', ascending=False)
    print("TOP 20 FEATURES MAIS IMPORTANTES")
    for _, row in importance.head(20).iterrows():
        print(f"{row['feature']:.<50} {row['importance']:.2f}")
    return model_final, importance


def treinar_classificador(df, features, target):
    """Classifica o tempo de espera em faixas (curta/media/longa)."""
    print("=" * 70)
    print("TREINAMENTO DO MODELO (LightGBM - Classificacao)")
    print("=" * 70)
    df = df.sort_values('data_chegada_dt').reset_index(drop=True)
    cutoff = df['data_chegada_dt'].max() - pd.DateOffset(months=6)
    train_df = df[df['data_chegada_dt'] < cutoff].copy()
    test_df = df[df['data_chegada_dt'] >= cutoff].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Split temporal invalido: ajuste o periodo de teste.")

    y_train = classificar_espera(train_df[target])
    y_test = classificar_espera(test_df[target])
    X_train = train_df[features].copy()
    X_test = test_df[features].copy()

    cat_features = [
        'nome_porto', 'nome_terminal', 'tipo_navegacao',
        'tipo_carga', 'natureza_carga', 'cdmercadoria', 'stsh4'
    ]
    for col in cat_features:
        X_train[col] = X_train[col].astype('category')
        X_test[col] = X_test[col].astype('category')

    model = lgb.LGBMClassifier(
        objective='multiclass',
        num_class=3,
        n_estimators=400,
        learning_rate=0.05,
        max_depth=7,
        num_leaves=31,
        class_weight='balanced',
        random_state=42
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)

    auc = roc_auc_score(y_test, proba, multi_class='ovo', average='macro')
    print(f"AUC-ROC (macro): {auc:.3f}")
    print("Matriz de confusao:")
    print(confusion_matrix(y_test, preds))
    print("Relatorio:")
    print(classification_report(y_test, preds, digits=3))
    return model


def treinar_modelo_xgboost(df, features, target, model_reg=None):
    """Treina modelo XGBoost com validação temporal (últimos 6 meses)."""
    print("=" * 70)
    print("TREINAMENTO DO MODELO (XGBoost)")
    print("=" * 70)
    df = df.sort_values('data_chegada_dt').reset_index(drop=True)
    cutoff = df['data_chegada_dt'].max() - pd.DateOffset(months=6)
    train_df = df[df['data_chegada_dt'] < cutoff].copy()
    test_df = df[df['data_chegada_dt'] >= cutoff].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Split temporal invalido: ajuste o periodo de teste.")

    X_train = train_df[features].copy()
    y_train = train_df[target].copy()
    X_test = test_df[features].copy()
    y_test = test_df[target].copy()

    cat_cols = [
        'nome_porto', 'nome_terminal', 'tipo_navegacao',
        'tipo_carga', 'natureza_carga', 'cdmercadoria', 'stsh4'
    ]
    X_train = pd.get_dummies(X_train, columns=cat_cols, dummy_na=True)
    X_test = pd.get_dummies(X_test, columns=cat_cols, dummy_na=True)
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0)

    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        tree_method='hist'
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    print(f"Teste (ultimos 6 meses) -> MAE: {mae:.2f}h | RMSE: {rmse:.2f}h | R2: {r2:.3f}")
    booster = model.get_booster()
    score = booster.get_score(importance_type='gain')
    if score:
        imp = pd.DataFrame([
            {'feature': k, 'gain': v} for k, v in score.items()
        ]).sort_values('gain', ascending=False)
        imp.to_csv('xgb_feature_importance.csv', index=False)
        print("Top 15 features (XGBoost gain):")
        print(imp.head(15).to_string(index=False))
        try:
            import matplotlib.pyplot as plt
            ax = imp.head(20).plot.barh(x='feature', y='gain', legend=False, figsize=(8, 6))
            ax.invert_yaxis()
            ax.set_title('XGBoost Feature Importance (gain)')
            ax.set_xlabel('gain')
            plt.tight_layout()
            plt.savefig('xgb_feature_importance.png', dpi=150)
            plt.close()
            print("Salvo: xgb_feature_importance.png")
        except Exception:
            print("Matplotlib indisponivel; salvei apenas xgb_feature_importance.csv")

    # Experimento: hiperparametros mais agressivos com top 15 features
    top15 = None
    if score:
        top15 = imp['feature'].head(15).tolist()
    if top15:
        X_train_top = X_train[top15].copy()
        X_test_top = X_test[top15].copy()
        model_agressivo = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=2000,
            max_depth=10,
            learning_rate=0.02,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            tree_method='hist'
        )
        model_agressivo.fit(X_train_top, y_train)
        preds_agressivo = model_agressivo.predict(X_test_top)
        mae_agressivo = mean_absolute_error(y_test, preds_agressivo)
        rmse_agressivo = np.sqrt(mean_squared_error(y_test, preds_agressivo))
        r2_agressivo = r2_score(y_test, preds_agressivo)
        print(
            f"XGB agressivo (Top 15) -> MAE: {mae_agressivo:.2f}h | "
            f"RMSE: {rmse_agressivo:.2f}h | R2: {r2_agressivo:.3f}"
        )
        if mae_agressivo < mae:
            print("XGB agressivo melhorou MAE; mantendo o modelo agressivo.")
            model = model_agressivo
            preds = preds_agressivo
            mae = mae_agressivo

    # Ensemble simples com LightGBM (se disponivel)
    if model_reg is not None:
        X_test_lgb = test_df[features].copy()
        cat_features = [
            'nome_porto', 'nome_terminal', 'tipo_navegacao',
            'tipo_carga', 'natureza_carga', 'cdmercadoria', 'stsh4'
        ]
        for col in cat_features:
            X_test_lgb[col] = X_test_lgb[col].astype('category')
        lgbm_pred = np.expm1(model_reg.predict(X_test_lgb))
        ens_pred = (lgbm_pred + preds) / 2.0
        mae_ens = mean_absolute_error(y_test, ens_pred)
        rmse_ens = np.sqrt(mean_squared_error(y_test, ens_pred))
        r2_ens = r2_score(y_test, ens_pred)
        print(
            f"Ensemble (LGBM + XGB) -> MAE: {mae_ens:.2f}h | "
            f"RMSE: {rmse_ens:.2f}h | R2: {r2_ens:.3f}"
        )

    return model


def salvar_modelos(profile, features, target, model_reg, model_clf, model_xgb):
    if not SAVE_MODELS:
        print("SAVE_MODELS=0 -> pulando salvamento de modelos.")
        return
    output_dir = Path("models")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "profile": profile,
        "features": features,
        "target": target,
        "trained_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "artifacts": {
            "lgb_reg": f"{profile.lower()}_lgb_reg.pkl",
            "lgb_clf": f"{profile.lower()}_lgb_clf.pkl",
            "xgb_reg": f"{profile.lower()}_xgb_reg.pkl",
            "ensemble_reg": f"{profile.lower()}_ensemble_reg.pkl",
        },
    }
    with (output_dir / artifacts["artifacts"]["lgb_reg"]).open("wb") as f:
        pickle.dump(model_reg, f)
    with (output_dir / artifacts["artifacts"]["lgb_clf"]).open("wb") as f:
        pickle.dump(model_clf, f)
    with (output_dir / artifacts["artifacts"]["xgb_reg"]).open("wb") as f:
        pickle.dump(model_xgb, f)
    ensemble = EnsembleRegressor(model_reg, model_xgb)
    joblib.dump(ensemble, output_dir / artifacts["artifacts"]["ensemble_reg"])
    with (output_dir / f"{profile.lower()}_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(artifacts, f, ensure_ascii=True, indent=2)
    print(f"Modelos salvos em: {output_dir.resolve()}")


def main():
    print("=" * 70)
    print("MODELO DE PREVISAO DE TEMPO DE ESPERA PARA ATRACACAO")
    print("=" * 70)
    print(f"FLAGS: USE_MARE_FEATURES={int(USE_MARE_FEATURES)} | USE_MARE_CLIMA={int(USE_MARE_CLIMA)} | SAVE_MODELS={int(SAVE_MODELS)}")
    if PROFILES_TO_RUN:
        for profile in PROFILES_TO_RUN:
            global PROFILE
            PROFILE = profile
            print("\n" + "=" * 70)
            print(f"PERFIL: {PROFILE}")
            print("=" * 70)
            df_final, features, target = preparar_dados()
            model_reg, _ = treinar_modelo(df_final, features, target)
            model_xgb = treinar_modelo_xgboost(df_final, features, target, model_reg=model_reg)
            model_clf = treinar_classificador(df_final, features, target)
            salvar_modelos(PROFILE, features, target, model_reg, model_clf, model_xgb)
    else:
        df_final, features, target = preparar_dados()
        model_reg, _ = treinar_modelo(df_final, features, target)
        model_xgb = treinar_modelo_xgboost(df_final, features, target, model_reg=model_reg)
        model_clf = treinar_classificador(df_final, features, target)
        profile_name = globals().get("PROFILE", "default")
        salvar_modelos(profile_name, features, target, model_reg, model_clf, model_xgb)
    print("=" * 70)
    print("PIPELINE COMPLETO EXECUTADO COM SUCESSO")
    print("=" * 70)


if __name__ == '__main__':
    main()
