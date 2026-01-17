import warnings
from datetime import datetime

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


def normalizar_texto(valor):
    """Normaliza texto para comparacao simples."""
    if pd.isna(valor):
        return ""
    texto = str(valor).upper()
    texto = ''.join(ch for ch in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(ch))
    return re.sub(r'[^A-Z0-9]', '', texto)


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
    station_map = mapear_estacoes_por_municipio(df_antaq)
    df_antaq['id_estacao'] = df_antaq['municipio'].map(station_map)
    station_ids = [sid for sid in df_antaq['id_estacao'].dropna().unique()]
    df_clima = extrair_dados_climaticos(station_ids=station_ids)
    df_pam = extrair_dados_producao_agricola()
    df_precos = extrair_precos_commodities()
    df = integrar_clima_com_atracacao(df_antaq, df_clima)
    df = integrar_producao_agricola(df, df_pam)
    df = integrar_precos_commodities(df, df_precos)
    print("=" * 70)
    print("FEATURE ENGINEERING")
    print("=" * 70)
    df = calcular_target(df)
    df = criar_features_temporais(df)
    df = criar_target_encoding_porto(df)
    df = criar_features_climaticas_avancadas(df)
    df = criar_features_commodities(df)
    df = calcular_fila_no_momento(df)
    df = calcular_densidade_fila(df)
    df = criar_lag_features(df)
    features = [
        'nome_porto', 'nome_terminal', 'tipo_navegacao', 'tipo_carga',
        'natureza_carga', 'cdmercadoria', 'stsh4',
        'movimentacao_total_toneladas', 'mes', 'dia_semana',
        'navios_no_fundeio_na_chegada', 'navios_na_fila_7d', 'tempo_espera_ma5',
        'dia_do_ano', 'porto_tempo_medio_historico',
        'temp_media_dia', 'precipitacao_dia', 'vento_rajada_max_dia',
        'umidade_media_dia', 'amplitude_termica',
        'restricao_vento', 'restricao_chuva',
        'flag_celulose', 'flag_algodao', 'flag_soja', 'flag_milho',
        'periodo_safra',
        'producao_soja', 'producao_milho', 'producao_algodao',
        'preco_soja_mensal', 'preco_milho_mensal', 'preco_algodao_mensal',
        'indice_pressao_soja', 'indice_pressao_milho'
    ]
    target = 'tempo_espera_horas'
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


def treinar_modelo_xgboost(df, features, target):
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
    return model


def main():
    print("=" * 70)
    print("MODELO DE PREVISAO DE TEMPO DE ESPERA PARA ATRACACAO")
    print("=" * 70)
    df_final, features, target = preparar_dados()
    treinar_modelo(df_final, features, target)
    treinar_modelo_xgboost(df_final, features, target)
    treinar_classificador(df_final, features, target)
    print("=" * 70)
    print("PIPELINE COMPLETO EXECUTADO COM SUCESSO")
    print("=" * 70)


if __name__ == '__main__':
    main()
