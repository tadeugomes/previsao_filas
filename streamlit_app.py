import json
import pickle
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st
from google.cloud import bigquery
import joblib

APP_TITLE = "Previsao de Fila - Vegetal (MVP)"
LINEUP_DIR = Path("lineups")
LINEUP_HISTORY_PATH = Path("data/lineup_history.parquet")
META_PATH = Path("data_extraction/processed/production/dataset_metadata.json")
MODEL_DIR = Path("models")
MODEL_METADATA_PATH = MODEL_DIR / "vegetal_metadata.json"
PREDICTED_DIR = Path("lineups_previstos")
PREMIUM_REGISTRY_PATH = Path("premium_registry.json")
AIS_FEATURES_DIR = Path("data/ais_features")
PORT_MAPPING_PATH = Path("data/port_mapping.csv")
PORT_MUNICIPIO_UF = {
    "ITAQUI": {"municipio": "SAO LUIS", "uf": "MA"},
    "PONTA_DA_MADEIRA": {"municipio": "SAO LUIS", "uf": "MA"},
}
PROFILE_KEYWORDS = {
    "VEGETAL": ["SOJA", "MILHO", "TRIGO", "CEVADA", "MALTE", "ARROZ", "FARELO", "ACUCAR"],
    "MINERAL": ["MINERIO", "BAUXITA", "MANGANES", "FERRO", "CIMENTO", "CLINKER", "COBRE"],
    "FERTILIZANTE": ["UREIA", "POTASSIO", "KCL", "NPK", "FOSFATO", "FERTIL"],
}
PROFILE_CODES = {
    "VEGETAL": [
        "1201", "1005", "1701", "2304", "1001", "1003",
        "1006", "1107", "2302", "2306", "1205", "1206",
    ],
    "MINERAL": [
        "2601", "2606", "2602", "2501", "2523", "2603", "2510",
    ],
    "FERTILIZANTE": [
        "3102", "3104", "3105", "3103", "3101",
    ],
}
CARGA_OPCOES_POR_PERFIL = {
    "VEGETAL": ["Soja em Graos", "Farelo", "Milho", "Acucar", "Trigo", "Cevada", "Malte"],
    "MINERAL": ["Minerio de Ferro", "Bauxita", "Manganes", "Cimento/Clinker", "Cobre", "Fosfatos"],
    "FERTILIZANTE": ["Ureia", "KCL", "NPK", "Fosfatado", "Nitrogenado", "Potassico", "Organico"],
}
BASE_CAT_FEATURES = [
    "nome_porto",
    "nome_terminal",
    "tipo_navegacao",
    "tipo_carga",
    "natureza_carga",
    "cdmercadoria",
    "stsh4",
]


@st.cache_data
def load_real_data(lineup_path):
    if lineup_path and lineup_path.exists():
        if lineup_path.suffix.lower() == ".xlsx":
            df_lineup = pd.read_excel(lineup_path)
            df_lineup = df_lineup.rename(
                columns={c: normalize_column_name(c) for c in df_lineup.columns}
            )
            rename_map = {
                "navio": "Navio",
                "produto": "Mercadoria",
                "carga": "Mercadoria",
                "chegada": "Chegada",
                "pier": "Pier",
                "berco": "Berco",
                "dwt": "DWT",
                "atracacao": "Atracacao",
                "tx_comercial": "TX_COMERCIAL",
                "tx_efetiva": "TX_EFETIVA",
                "laytime": "Laytime",
                "incoterm": "INCOTERM",
                "ano": "Ano",
                "mes": "Mes",
            }
            df_lineup = df_lineup.rename(columns=rename_map)
        else:
            df_lineup = pd.read_csv(lineup_path)
            df_lineup = df_lineup.rename(
                columns={c: normalize_column_name(c) for c in df_lineup.columns}
            )
            rename_map = {
                "navio": "Navio",
                "carga": "Mercadoria",
                "produto": "Mercadoria",
                "prev_chegada": "Chegada",
                "berco": "Berco",
                "dwt": "DWT",
                "ultima_atualizacao": "Atualizacao",
                "extracted_at": "ExtraidoEm",
            }
            df_lineup = df_lineup.rename(columns=rename_map)
        if "Pier" in df_lineup.columns and "Berco" not in df_lineup.columns:
            df_lineup["Berco"] = df_lineup["Pier"]
        df_lineup = df_lineup.copy()
    else:
        df_lineup = pd.DataFrame(columns=["Navio", "Mercadoria", "Chegada", "Berco"])

    return df_lineup, load_metadata()


@st.cache_data
def load_metadata():
    if META_PATH.exists():
        with META_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data
def list_lineup_files():
    if not LINEUP_DIR.exists():
        return []
    files = list(LINEUP_DIR.glob("*.csv")) + list(LINEUP_DIR.glob("*.xlsx"))
    return sorted(files, key=lambda p: p.name.lower())


@st.cache_data
def load_lineup_history():
    if not LINEUP_HISTORY_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(LINEUP_HISTORY_PATH)
    if df.empty:
        return df
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]
    return df


def prepare_lineup_history(df):
    df = df.copy()
    if "navio" in df.columns:
        df["Navio"] = df["navio"]
    if "produto" in df.columns:
        df["Mercadoria"] = df["produto"]
    elif "carga" in df.columns:
        df["Mercadoria"] = df["carga"]
    if "prev_chegada" in df.columns:
        df["Chegada"] = df["prev_chegada"]
    if "berco" in df.columns:
        df["Berco"] = df["berco"]
    if "dwt" in df.columns:
        df["DWT"] = df["dwt"]
    if "ultima_atualizacao" in df.columns:
        df["Atualizacao"] = df["ultima_atualizacao"]
    return df


@st.cache_data
def load_lineup_history_porto(porto_nome):
    df = load_lineup_history()
    if df.empty or "porto" not in df.columns:
        return pd.DataFrame()
    target = normalizar_texto(porto_nome)
    df = df.copy()
    df["porto_norm"] = df["porto"].apply(normalizar_texto)
    df = df[df["porto_norm"] == target].drop(columns=["porto_norm"], errors="ignore")
    if df.empty:
        return df
    return prepare_lineup_history(df)


@st.cache_data
def load_history_data(porto_nome):
    df_lineup = load_lineup_history_porto(porto_nome)
    if df_lineup.empty:
        df_lineup = pd.DataFrame(columns=["Navio", "Mercadoria", "Chegada", "Berco"])
    return df_lineup, load_metadata()


@st.cache_data
def list_lineup_ports():
    history = load_lineup_history()
    if history.empty or "porto" not in history.columns:
        return []
    return sorted(
        history["porto"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )


@st.cache_data
def load_models():
    if not MODEL_METADATA_PATH.exists():
        return None
    with MODEL_METADATA_PATH.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    artifacts = metadata.get("artifacts", {})
    reg_path = MODEL_DIR / artifacts.get("lgb_reg", "")
    clf_path = MODEL_DIR / artifacts.get("lgb_clf", "")
    if not reg_path.exists() or not clf_path.exists():
        return None
    with reg_path.open("rb") as f:
        model_reg = pickle.load(f)
    with clf_path.open("rb") as f:
        model_clf = pickle.load(f)
    return {
        "metadata": metadata,
        "model_reg": model_reg,
        "model_clf": model_clf,
    }


@st.cache_data
def load_models_for_profile(profile):
    metadata_path = MODEL_DIR / f"{profile.lower()}_metadata.json"
    if not metadata_path.exists():
        return None
    with metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    artifacts = metadata.get("artifacts", {})
    ensemble_path = MODEL_DIR / artifacts.get("ensemble_reg", "")
    reg_path = MODEL_DIR / artifacts.get("lgb_reg", "")
    clf_path = MODEL_DIR / artifacts.get("lgb_clf", "")
    ensemble_model = None
    if ensemble_path.exists():
        ensemble_model = joblib.load(ensemble_path)
    if not reg_path.exists() or not clf_path.exists():
        return None
    with reg_path.open("rb") as f:
        model_reg = pickle.load(f)
    with clf_path.open("rb") as f:
        model_clf = pickle.load(f)
    return {
        "metadata": metadata,
        "model_reg": model_reg,
        "model_ensemble": ensemble_model,
        "model_clf": model_clf,
    }


@st.cache_data
def load_premium_registry():
    if PREMIUM_REGISTRY_PATH.exists():
        with PREMIUM_REGISTRY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": 1,
        "terminals": [
            {
                "name": "PONTA_DA_MADEIRA",
                "ports": ["PONTA_DA_MADEIRA", "PONTA DA MADEIRA"],
                "profiles": ["MINERAL"],
                "mae_esperado": 30,
                "requires_terminal_data": True,
                "metadata_path": "models/ponta_da_madeira_metadata.json",
                "builder": "ponta_da_madeira",
            }
        ],
    }


@st.cache_data
def load_premium_models(metadata_path):
    path = Path(metadata_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    artifacts = metadata.get("artifacts", {})
    ensemble_path = MODEL_DIR / artifacts.get("ensemble_reg", "")
    dummy_columns = metadata.get("dummy_columns")
    if not ensemble_path.exists() or not dummy_columns:
        return None
    ensemble_model = joblib.load(ensemble_path)
    return {
        "metadata": metadata,
        "ensemble": ensemble_model,
        "dummy_columns": dummy_columns,
    }


@st.cache_data
def load_port_mapping():
    if not PORT_MAPPING_PATH.exists():
        return {}
    df_map = pd.read_csv(PORT_MAPPING_PATH)
    if df_map.empty:
        return {}
    df_map = df_map.dropna(subset=["portname", "nome_porto_antaq"])
    df_map["portname_norm"] = df_map["portname"].apply(normalizar_texto)
    df_map["porto_norm"] = df_map["nome_porto_antaq"].apply(normalizar_texto)
    return dict(zip(df_map["porto_norm"], df_map["portname_norm"]))


@st.cache_data
def load_latest_ais_features():
    if not AIS_FEATURES_DIR.exists():
        return None
    files = sorted(AIS_FEATURES_DIR.glob("ais_features_*.parquet"))
    if not files:
        return None
    return pd.read_parquet(files[-1])


def filter_features_by_port(df, porto_nome, mapping):
    if df is None or df.empty:
        return df
    porto_norm = normalizar_texto(porto_nome)
    target_norm = mapping.get(porto_norm, porto_norm)
    port_col = "portname" if "portname" in df.columns else "port_name"
    df = df.copy()
    df["portname_norm"] = df[port_col].apply(normalizar_texto)
    return df[df["portname_norm"] == target_norm]


def infer_profile(mercadoria):
    if pd.isna(mercadoria):
        return "VEGETAL"
    texto = normalizar_texto(mercadoria)
    for profile, keywords in PROFILE_KEYWORDS.items():
        if any(k in texto for k in keywords):
            return profile
    return "VEGETAL"


def infer_profile_from_code(codigo):
    if pd.isna(codigo):
        return None
    codigo_str = re.sub(r"[^0-9]", "", str(codigo))
    if len(codigo_str) < 4:
        return None
    prefix = codigo_str[:4]
    for profile, codes in PROFILE_CODES.items():
        if prefix in codes:
            return profile
    return None


def get_profile_from_row(row):
    for key in ["cdmercadoria", "cd_mercadoria", "stsh4"]:
        if key in row:
            profile = infer_profile_from_code(row.get(key))
            if profile:
                return profile
    for key in ["Mercadoria", "mercadoria", "PRODUTO", "produto"]:
        if key in row:
            return infer_profile(row.get(key))
    return "VEGETAL"


def get_premium_config(porto_nome):
    registry = load_premium_registry()
    target = normalizar_texto(porto_nome)
    for entry in registry.get("terminals", []):
        ports = entry.get("ports") or [entry.get("name", "")]
        for port in ports:
            if normalizar_texto(port) == target:
                return entry
    return None


def infer_port_profile(df_lineup, porto_nome):
    premium_cfg = get_premium_config(porto_nome)
    if premium_cfg and premium_cfg.get("profiles"):
        return premium_cfg["profiles"][0]
    if df_lineup is not None and not df_lineup.empty:
        profiles = df_lineup.apply(get_profile_from_row, axis=1)
        if not profiles.empty:
            return profiles.value_counts().idxmax()
    return "VEGETAL"


def compute_default_fila(df_lineup, lineup_path):
    if df_lineup is None or df_lineup.empty:
        return 0
    if lineup_path and lineup_path.suffix.lower() == ".xlsx":
        for col in ["Chegada", "Atracacao"]:
            if col in df_lineup.columns:
                dates = pd.to_datetime(df_lineup[col], errors="coerce", dayfirst=True)
                if dates.notna().any():
                    ref = dates.max()
                    window_start = ref - pd.Timedelta(days=7)
                    return int((dates >= window_start).sum())
    return int(len(df_lineup))


def has_terminal_data(df_lineup):
    normalized = {normalize_column_name(c) for c in df_lineup.columns}
    terminal_cols = {"pier", "tx_efetiva", "tx_comercial", "laytime"}
    return bool(normalized & terminal_cols)


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).upper()
    texto = "".join(
        ch for ch in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(ch)
    )
    return re.sub(r"[^A-Z0-9]", "", texto)


def normalize_column_name(valor):
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").lower()
    return texto


def find_column_by_norm(df, candidates):
    norm_map = {normalize_column_name(c): c for c in df.columns}
    for candidate in candidates:
        key = normalize_column_name(candidate)
        if key in norm_map:
            return norm_map[key]
    return None


def format_date_short(value):
    if value is None or pd.isna(value):
        return "-"
    return pd.to_datetime(value).strftime("%d/%m")


def format_datetime_short(value):
    if value is None or pd.isna(value):
        return "-"
    return pd.to_datetime(value).strftime("%d/%m %H:%M")


def get_lineup_updated_at(df_lineup):
    if df_lineup is None or df_lineup.empty:
        return None
    candidates = ["Atualizacao", "ExtraidoEm", "ultima_atualizacao", "extracted_at"]
    for col in candidates:
        if col in df_lineup.columns:
            series = pd.to_datetime(df_lineup[col], errors="coerce", dayfirst=True)
            if series.notna().any():
                return series.max()
    return None


@st.cache_data(ttl=21600)
def fetch_inmet_station_id(municipio="SAO LUIS", project_id="antaqdados"):
    client = bigquery.Client(project=project_id)
    query = """
    SELECT id_estacao, estacao
    FROM `basedosdados.br_inmet_bdmep.estacao`
    """
    df = client.query(query).to_dataframe()
    df["estacao_norm"] = df["estacao"].apply(normalizar_texto)
    muni_norm = normalizar_texto(municipio)
    match = df[df["estacao_norm"].str.contains(muni_norm, na=False)]
    if match.empty:
        return None
    return match.iloc[0]["id_estacao"]


@st.cache_data(ttl=21600)
def fetch_inmet_latest(station_id, project_id="antaqdados"):
    if not station_id:
        return None
    client = bigquery.Client(project=project_id)
    query = f"""
    SELECT
        data,
        AVG(temperatura_bulbo_hora) AS temp_media_dia,
        MAX(temperatura_max) AS temp_max_dia,
        MIN(temperatura_min) AS temp_min_dia,
        SUM(precipitacao_total) AS precipitacao_dia,
        MAX(vento_rajada_max) AS vento_rajada_max_dia,
        AVG(umidade_rel_hora) AS umidade_media_dia
    FROM `basedosdados.br_inmet_bdmep.microdados`
    WHERE id_estacao = '{station_id}'
    GROUP BY data
    ORDER BY data DESC
    LIMIT 7
    """
    df = client.query(query).to_dataframe()
    if df.empty:
        return None
    df = df.sort_values("data").reset_index(drop=True)
    latest = df.iloc[-1].to_dict()
    chuva_3d = df["precipitacao_dia"].tail(3).sum()
    latest["chuva_acumulada_ultimos_3dias"] = float(chuva_3d)
    latest["amplitude_termica"] = float(latest["temp_max_dia"] - latest["temp_min_dia"])
    return latest


@st.cache_data(ttl=21600)
def fetch_pam_latest(uf="MA", project_id="antaqdados"):
    client = bigquery.Client(project=project_id)
    query = f"""
    SELECT
        ano,
        produto,
        SUM(quantidade_produzida) AS quantidade
    FROM `basedosdados.br_ibge_pam.lavoura_temporaria`
    WHERE
        sigla_uf = '{uf}'
        AND ano >= 2020
        AND LOWER(REGEXP_REPLACE(NORMALIZE(produto, NFD), r'\\pM', '')) IN (
            'soja (em grao)',
            'milho (em grao)',
            'algodao herbaceo (em caroco)',
            'cana-de-acucar'
        )
    GROUP BY ano, produto
    ORDER BY ano DESC
    """
    df = client.query(query).to_dataframe()
    if df.empty:
        return None
    latest_year = int(df["ano"].max())
    df = df[df["ano"] == latest_year].copy()
    def get_prod(prod_name):
        match = df[df["produto"].str.contains(prod_name, case=False, na=False)]
        return float(match["quantidade"].sum()) if not match.empty else 0.0
    return {
        "ano": latest_year,
        "producao_soja": get_prod("soja"),
        "producao_milho": get_prod("milho"),
        "producao_algodao": get_prod("algodao"),
    }


@st.cache_data(ttl=21600)
def fetch_ipea_latest():
    commodities = [
        ("PRECOS12_PSOIM12", "preco_soja_mensal"),
        ("PRECOS12_PMIM12", "preco_milho_mensal"),
        ("PRECOS12_PALG12", "preco_algodao_mensal"),
    ]
    output = {}
    for codigo, key in commodities:
        try:
            url = f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{codigo}')"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()["value"]
            if not data:
                continue
            df = pd.DataFrame(data)
            df["data"] = pd.to_datetime(df["VALDATA"])
            df["valor"] = pd.to_numeric(df["VALVALOR"], errors="coerce")
            df = df.dropna().sort_values("data")
            if df.empty:
                continue
            output[key] = float(df.iloc[-1]["valor"])
        except Exception:
            continue
    return output or None


def build_features_from_lineup(df_lineup, metadata, live_data, porto_nome):
    features = metadata["features"]
    df = df_lineup.copy()
    if "Chegada" in df.columns:
        df["data_chegada_dt"] = pd.to_datetime(df["Chegada"], errors="coerce", dayfirst=True)
    else:
        df["data_chegada_dt"] = pd.NaT
    if df["data_chegada_dt"].isna().all():
        for fallback in ["Atualizacao", "ExtraidoEm"]:
            if fallback in df.columns:
                df["data_chegada_dt"] = pd.to_datetime(df[fallback], errors="coerce", dayfirst=True)
                if not df["data_chegada_dt"].isna().all():
                    break
    df["data_chegada_dt"] = df["data_chegada_dt"].fillna(pd.Timestamp.today().normalize())
    df["mes"] = df["data_chegada_dt"].dt.month.fillna(1).astype(int)
    df["dia_do_ano"] = df["data_chegada_dt"].dt.dayofyear.fillna(1).astype(int)
    df["trimestre"] = df["data_chegada_dt"].dt.quarter.fillna(1).astype(int)
    df["dia_semana"] = df["data_chegada_dt"].dt.dayofweek.fillna(0).astype(int)

    df["nome_porto"] = porto_nome
    df["nome_terminal"] = df.get("Berco", "DESCONHECIDO")
    df["tipo_navegacao"] = "Longo Curso"
    df["tipo_carga"] = "Granel"
    df["natureza_carga"] = df.get("Mercadoria", "Desconhecida")
    df["cdmercadoria"] = "0000"
    df["stsh4"] = "0000"

    df["movimentacao_total_toneladas"] = 0.0
    if "DWT" in df_lineup.columns:
        df["movimentacao_total_toneladas"] = pd.to_numeric(df_lineup["DWT"], errors="coerce").fillna(0.0)

    df = df.sort_values("data_chegada_dt").reset_index(drop=True)
    df["navios_no_fundeio_na_chegada"] = df.index.astype(float)
    df["navios_na_fila_7d"] = (
        df.assign(navio_index=1)
        .set_index("data_chegada_dt")
        .rolling("7D")["navio_index"]
        .count()
        .fillna(0.0)
        .to_numpy()
    )
    df["tempo_espera_ma5"] = 0.0
    df["porto_tempo_medio_historico"] = 0.0

    clima = live_data.get("clima") or {}
    df["temp_media_dia"] = float(clima.get("temp_media_dia", 25.0))
    df["precipitacao_dia"] = float(clima.get("precipitacao_dia", 0.0))
    df["vento_rajada_max_dia"] = float(clima.get("vento_rajada_max_dia", 5.0))
    df["umidade_media_dia"] = float(clima.get("umidade_media_dia", 70.0))
    df["amplitude_termica"] = float(clima.get("amplitude_termica", 10.0))
    df["restricao_vento"] = 0
    df["restricao_chuva"] = 0

    df["flag_celulose"] = 0
    df["flag_algodao"] = 0
    df["flag_soja"] = df["natureza_carga"].astype(str).str.contains("SOJA", case=False, na=False).astype(int)
    df["flag_milho"] = df["natureza_carga"].astype(str).str.contains("MILHO", case=False, na=False).astype(int)
    df["periodo_safra"] = df["mes"].isin([3, 4, 5, 6]).astype(int)

    pam = live_data.get("pam") or {}
    df["producao_soja"] = float(pam.get("producao_soja", 0.0))
    df["producao_milho"] = float(pam.get("producao_milho", 0.0))
    df["producao_algodao"] = float(pam.get("producao_algodao", 0.0))
    precos = live_data.get("precos") or {}
    df["preco_soja_mensal"] = float(precos.get("preco_soja_mensal", 100.0))
    df["preco_milho_mensal"] = float(precos.get("preco_milho_mensal", 50.0))
    df["preco_algodao_mensal"] = float(precos.get("preco_algodao_mensal", 300.0))
    df["indice_pressao_soja"] = 0.0
    df["indice_pressao_milho"] = 0.0
    if "chuva_acumulada_ultimos_3dias" in features:
        df["chuva_acumulada_ultimos_3dias"] = float(
            clima.get("chuva_acumulada_ultimos_3dias", 0.0)
        )

    ais_cols = [
        "ais_navios_no_raio",
        "ais_fila_ao_largo",
        "ais_velocidade_media_kn",
        "ais_eta_media_horas",
        "ais_dist_media_km",
    ]
    ais_df = live_data.get("ais_df")
    if isinstance(ais_df, pd.DataFrame) and not ais_df.empty:
        ais = ais_df.copy()
        ais["ais_date"] = pd.to_datetime(ais["date"], errors="coerce").dt.date
        ais = ais.drop(columns=["date"], errors="ignore")
        df["data_chegada_date"] = df["data_chegada_dt"].dt.date
        df = df.merge(ais, left_on="data_chegada_date", right_on="ais_date", how="left")
        df = df.drop(columns=["ais_date"], errors="ignore")
        df = df.drop(columns=["data_chegada_date"], errors="ignore")
    for col in ais_cols:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in features:
        if col not in df.columns:
            df[col] = 0

    X = df[features].copy()
    for col in BASE_CAT_FEATURES:
        if col in X.columns:
            X[col] = X[col].astype("category")
    return X


def build_xgb_features_from_lgb(X_lgb, model_xgb):
    cat_cols = [col for col in BASE_CAT_FEATURES if col in X_lgb.columns]
    X_xgb = pd.get_dummies(X_lgb.copy(), columns=cat_cols, dummy_na=True)
    feature_names = None
    try:
        feature_names = model_xgb.get_booster().feature_names
    except Exception:
        feature_names = None
    if feature_names:
        X_xgb = X_xgb.reindex(columns=feature_names, fill_value=0)
    return X_xgb


def build_premium_features_ponta_da_madeira(df_lineup, model_info):
    df = df_lineup.copy()
    df = df.rename(columns={c: normalize_column_name(c) for c in df.columns})
    def col_or_default(col, default):
        if col in df:
            return df[col]
        return pd.Series([default] * len(df))

    df["pier"] = col_or_default("pier", "DESCONHECIDO")
    df["dwt"] = pd.to_numeric(col_or_default("dwt", 0.0), errors="coerce").fillna(0.0)
    df["tx_comercial"] = pd.to_numeric(col_or_default("tx_comercial", 0.0), errors="coerce").fillna(0.0)
    df["tx_efetiva"] = pd.to_numeric(col_or_default("tx_efetiva", 0.0), errors="coerce").fillna(0.0)
    df["laytime"] = pd.to_numeric(col_or_default("laytime", 0.0), errors="coerce").fillna(0.0)
    df["incoterm"] = col_or_default("incoterm", "DESCONHECIDO").fillna("DESCONHECIDO")

    chegada = pd.to_datetime(col_or_default("chegada", pd.NaT), errors="coerce", dayfirst=True)
    if chegada.isna().all():
        chegada = pd.to_datetime(col_or_default("atracacao", pd.NaT), errors="coerce", dayfirst=True)
    chegada = chegada.fillna(pd.Timestamp.today().normalize())
    df["chegada_dt"] = chegada

    df = df.sort_values("chegada_dt").reset_index(drop=True)
    df["prancha_ma5_pier"] = (
        df.groupby("pier")["tx_efetiva"]
        .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
        .fillna(0.0)
    )
    tx_com = df["tx_comercial"].replace(0, np.nan)
    df["gap_prancha_pct"] = ((tx_com - df["tx_efetiva"]) / tx_com).fillna(0.0)
    df["laytime_horas"] = df["laytime"] * 24.0
    if "estadia" in df:
        estadia_raw = df["estadia"]
    else:
        estadia_raw = col_or_default("estadia3", 0.0)
    estadia = pd.to_numeric(estadia_raw, errors="coerce").fillna(0.0)
    estadia_horas = estadia * 24.0
    df["urgencia_alta"] = ((df["laytime_horas"] - estadia_horas) < 24).astype(int)
    df["navios_no_fundeio_na_chegada"] = df.index.astype(float)
    df["mes"] = df["chegada_dt"].dt.month.astype(int)
    df["dia_ano"] = df["chegada_dt"].dt.dayofyear.astype(int)

    feature_cols = model_info["metadata"]["features"]
    cat_cols = ["pier", "incoterm"]
    X = df[feature_cols].copy()
    X = pd.get_dummies(X, columns=cat_cols, dummy_na=True)
    dummy_columns = model_info["dummy_columns"]
    X = X.reindex(columns=dummy_columns, fill_value=0)
    return X


PREMIUM_BUILDERS = {
    "ponta_da_madeira": build_premium_features_ponta_da_madeira,
}


def predict_lineup_basico(df_lineup, live_data, porto_nome):
    df = df_lineup.copy()
    df["perfil_modelo"] = df.apply(get_profile_from_row, axis=1)
    dfs = []
    for profile, sub in df.groupby("perfil_modelo", dropna=False):
        models = load_models_for_profile(profile)
        if not models:
            sub["tempo_espera_previsto_horas"] = np.nan
            sub["tempo_espera_previsto_dias"] = np.nan
            sub["classe_espera_prevista"] = "Indisponivel"
            sub["risco_previsto"] = "Indisponivel"
            sub["probabilidade_prevista"] = np.nan
            dfs.append(sub)
            continue
        features_data = build_features_from_lineup(sub, models["metadata"], live_data, porto_nome)
        preds_horas = None
        if models.get("model_ensemble") is not None:
            ensemble = models["model_ensemble"]
            try:
                if hasattr(ensemble, "xgb_model"):
                    X_xgb = build_xgb_features_from_lgb(features_data, ensemble.xgb_model)
                    preds = ensemble.predict(X_xgb, X_lgb=features_data)
                else:
                    preds = ensemble.predict(features_data)
                preds_horas = pd.Series(preds).apply(lambda v: float(max(0.0, v)))
            except Exception:
                preds_horas = None
        if preds_horas is None:
            preds_horas = pd.Series(models["model_reg"].predict(features_data)).apply(
                lambda v: float(max(0.0, np.expm1(v)))
            )
        sub["tempo_espera_previsto_horas"] = preds_horas.round(2)
        sub["tempo_espera_previsto_dias"] = (sub["tempo_espera_previsto_horas"] / 24.0).round(2)
        class_pred = models["model_clf"].predict(features_data)
        class_map = {0: "Rapido", 1: "Medio", 2: "Longo"}
        risco_map = {0: "Baixo", 1: "Medio", 2: "Alto"}
        sub["classe_espera_prevista"] = pd.Series(class_pred).map(class_map).fillna("Desconhecido")
        sub["risco_previsto"] = pd.Series(class_pred).map(risco_map).fillna("Desconhecido")
        try:
            proba = models["model_clf"].predict_proba(features_data)
            sub["probabilidade_prevista"] = np.max(proba, axis=1).round(3)
        except Exception:
            sub["probabilidade_prevista"] = np.nan
        dfs.append(sub)
    df_out = pd.concat(dfs, ignore_index=True)
    if "data_chegada_dt" not in df_out.columns:
        if "Chegada" in df_out.columns:
            df_out["data_chegada_dt"] = pd.to_datetime(
                df_out["Chegada"], errors="coerce", dayfirst=True
            )
        else:
            df_out["data_chegada_dt"] = pd.NaT
    if df_out["data_chegada_dt"].isna().all():
        for fallback in ["Atualizacao", "ExtraidoEm"]:
            if fallback in df_out.columns:
                df_out["data_chegada_dt"] = pd.to_datetime(
                    df_out[fallback], errors="coerce", dayfirst=True
                )
                if not df_out["data_chegada_dt"].isna().all():
                    break
    df_out["data_chegada_dt"] = df_out["data_chegada_dt"].fillna(
        pd.Timestamp.today().normalize()
    )
    eta = pd.to_datetime(df_out["data_chegada_dt"], errors="coerce")
    eta_espera = eta + pd.to_timedelta(df_out["tempo_espera_previsto_horas"].fillna(0), unit="h")
    df_out["eta_mais_espera"] = eta_espera
    df_out = df_out.sort_values("eta_mais_espera")
    return df_out


def inferir_lineup_inteligente(lineup_df, live_data, porto_nome, tem_dados_terminal=False):
    df_out = predict_lineup_basico(lineup_df, live_data, porto_nome)
    df_out["perfil"] = df_out.apply(get_profile_from_row, axis=1)
    mae_map = {"VEGETAL": 38, "MINERAL": 31, "FERTILIZANTE": 79}
    df_out["mae_esperado"] = df_out["perfil"].map(mae_map)
    df_out["tier"] = "BASIC"

    premium_cfg = get_premium_config(porto_nome)
    usar_premium = premium_cfg is not None and (
        not premium_cfg.get("requires_terminal_data", True) or tem_dados_terminal
    )
    if usar_premium:
        premium = load_premium_models(premium_cfg["metadata_path"])
        builder = PREMIUM_BUILDERS.get(premium_cfg.get("builder", ""))
        if premium and builder:
            profiles = premium_cfg.get("profiles") or ["MINERAL"]
            mask = df_out["perfil"].isin(profiles)
            if mask.any():
                X_premium = builder(df_out.loc[mask], premium)
                preds = premium["ensemble"].predict(X_premium)
                preds = pd.Series(preds).apply(lambda v: float(max(0.0, v)))
                df_out.loc[mask, "tempo_espera_previsto_horas"] = preds.round(2)
                df_out.loc[mask, "tempo_espera_previsto_dias"] = (preds / 24.0).round(2)
                df_out.loc[mask, "mae_esperado"] = premium_cfg.get("mae_esperado", 30)
                df_out.loc[mask, "tier"] = "PREMIUM"

    eta = pd.to_datetime(df_out["data_chegada_dt"], errors="coerce")
    eta_espera = eta + pd.to_timedelta(df_out["tempo_espera_previsto_horas"].fillna(0), unit="h")
    df_out["eta_mais_espera"] = eta_espera
    df_out = df_out.sort_values("eta_mais_espera")
    return df_out


def calcular_risco(chuva_mm_3d, fila_atual, fila_media):
    if chuva_mm_3d > 20 or fila_atual > 20:
        return "Alto", "vermelho", "Chuva intensa ou fila critica"
    if chuva_mm_3d > 10 or fila_atual > fila_media:
        return "Medio", "amarelo", "Chuva relevante ou fila acima da media"
    return "Baixo", "verde", "Clima favoravel e fila abaixo da media"


st.set_page_config(page_title=APP_TITLE, layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&family=Roboto:wght@400;500;600&family=Inter:wght@600;700&display=swap');
:root {
  --ink: #0A2342;
  --muted: #1E5F9C;
  --accent: #F29F05;
  --bg: #F2F4F7;
  --card: #FFFFFF;
  --border: #D7DEE8;
}
html, body, [class*="css"] {
  font-family: "Roboto", sans-serif;
  color: var(--ink);
}
.stApp {
  background: var(--bg);
}
section[data-testid="stSidebar"] > div {
  background: linear-gradient(180deg, #0A2342, #1E5F9C);
  color: #FFFFFF;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] p {
  color: #FFFFFF !important;
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  color: #FFFFFF !important;
}
section[data-testid="stSidebar"] button {
  background: var(--accent);
  color: #0A2342;
  border: none;
  border-radius: 4px;
  font-weight: 600;
}
section[data-testid="stSidebar"] button:hover {
  background: #e38904;
}
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-radius: 4px;
  background: var(--card);
  border: 1px solid var(--border);
  box-shadow: 0 6px 20px rgba(10, 35, 66, 0.12);
  margin-bottom: 18px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}
.logo {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  background: linear-gradient(135deg, #0A2342, #1E5F9C);
  color: #FFFFFF;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.06em;
}
.brand-title {
  font-family: "Montserrat", sans-serif;
  font-size: 24px;
  font-weight: 700;
}
.brand-subtitle {
  color: var(--muted);
  font-size: 14px;
  max-width: 620px;
}
.section-title {
  font-family: "Montserrat", sans-serif;
  font-size: 18px;
  margin: 18px 0 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title svg {
  width: 18px;
  height: 18px;
  color: var(--accent);
  stroke: var(--accent);
}
.table-title {
  color: #000000;
}
.table-title svg {
  color: #000000;
  stroke: #000000;
}
.table-definitions {
  color: #000000;
}
.table-definitions li {
  color: #000000;
}
.table-definitions strong {
  color: #000000;
}
.table-caption {
  color: #000000;
  font-size: 13px;
  margin-bottom: 8px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 14px 16px;
  box-shadow: 0 6px 16px rgba(10, 35, 66, 0.08);
}
.card-label {
  color: #1E5F9C;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.card-value {
  font-family: "Inter", sans-serif;
  font-size: 20px;
  font-weight: 700;
  margin-top: 6px;
  color: #1E5F9C;
}
.card-sub {
  color: #1E5F9C;
  font-size: 11px;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 16px;
  box-shadow: 0 6px 18px rgba(10, 35, 66, 0.08);
}
.callout {
  background: #E8F2FF;
  border-left: 4px solid var(--accent);
  color: var(--ink);
  border-radius: 4px;
  padding: 12px 16px;
  font-weight: 600;
}
.mode-banner {
  background: #E8F2FF;
  border-left: 4px solid var(--muted);
  color: #000000;
  border-radius: 4px;
  padding: 10px 14px;
  font-weight: 600;
  margin-bottom: 10px;
}
.mode-banner.premium {
  border-left-color: var(--accent);
}
.question-text {
  color: var(--muted);
  font-size: 13px;
  margin-top: 6px;
}
.panel-list {
  margin: 0;
  padding-left: 16px;
  color: var(--muted);
}
.footer {
  margin-top: 24px;
  padding: 12px 16px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: #FFFFFF;
  color: var(--muted);
  font-size: 12px;
}
@media (max-width: 980px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .card-grid {
    grid-template-columns: 1fr;
  }
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <div class="brand">
    <div class="logo">PF</div>
    <div>
      <div class="brand-title">Previsao de Fila - Vegetal (MVP)</div>
      <div class="brand-subtitle">Sistema de previsao de espera e atracacao baseado em dados operacionais e modelos de machine learning.</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Selecao de Parametros")
    portos = list_lineup_ports()
    porto_selecionado = st.selectbox("Porto", portos)
    lineup_path = None
    if porto_selecionado != "NACIONAL":
        df_lineup, meta = load_history_data(porto_selecionado)
    else:
        df_lineup, meta = load_real_data(lineup_path)
    lineup_updated_at = get_lineup_updated_at(df_lineup)

    perfil_porto = infer_port_profile(df_lineup, porto_selecionado)
    opcoes_carga = CARGA_OPCOES_POR_PERFIL.get(perfil_porto, CARGA_OPCOES_POR_PERFIL["VEGETAL"])
    tipo_carga = st.selectbox("Tipo de Carga", opcoes_carga)
    data_chegada = st.date_input("Data de Chegada", value=datetime.today())

    berco_selecionado = "Todos"
    if porto_selecionado != "NACIONAL" and not df_lineup.empty and "Berco" in df_lineup.columns:
        berco_opcoes = ["Todos"] + sorted(df_lineup["Berco"].dropna().unique().tolist())
        berco_selecionado = st.selectbox("Berco", berco_opcoes)

    navio_selecionado = "Todos"
    navio_col = None
    if porto_selecionado != "NACIONAL" and not df_lineup.empty:
        navio_col = find_column_by_norm(df_lineup, ["Navio", "navio", "nome_navio", "embarcacao"])
    if navio_col:
        navios_raw = df_lineup[navio_col].dropna().astype(str).str.strip()
        navios = ["Todos"] + sorted(navios_raw.unique().tolist())
        navio_selecionado = st.selectbox("Navio", navios)

    tipo_navio_selecionado = "Todos"
    tipo_navio_col = None
    if porto_selecionado != "NACIONAL" and not df_lineup.empty:
        tipo_navio_col = find_column_by_norm(df_lineup, ["categoria", "tipo_navio", "tipo"])
    if tipo_navio_col:
        tipos_raw = df_lineup[tipo_navio_col].dropna().astype(str).str.strip()
        tipos = ["Todos"] + sorted(tipos_raw.unique().tolist())
        tipo_navio_label = f"Tipo de Navio ({str(tipo_navio_col).title()})"
        tipo_navio_selecionado = st.selectbox(tipo_navio_label, tipos)

    st.markdown("### Condicoes Climaticas")
    default_chuva = 0.0
    if porto_selecionado != "NACIONAL":
        try:
            porto_key = porto_selecionado.upper()
            porto_cfg = PORT_MUNICIPIO_UF.get(porto_key, {})
            municipio = porto_cfg.get("municipio", porto_selecionado)
            station_id = fetch_inmet_station_id(municipio=municipio)
            clima = fetch_inmet_latest(station_id) or {}
            default_chuva = float(clima.get("chuva_acumulada_ultimos_3dias", 0.0))
        except Exception:
            default_chuva = 0.0
    editar_clima = st.checkbox("Editar clima manualmente", value=False)
    chuva_prevista = st.number_input(
        "Chuva acumulada 72h (mm)",
        min_value=0.0,
        value=default_chuva,
        disabled=not editar_clima,
    )

    st.markdown("### Condicoes Operacionais")
    default_fila = compute_default_fila(df_lineup, lineup_path)
    st.session_state["fila_base"] = default_fila
    fila_atual = st.number_input("Navios no fundeio", min_value=0, value=default_fila)
    gerar = st.button("Gerar Previsao", use_container_width=True)
if porto_selecionado == "NACIONAL":
    pergunta_modelo = "Qual a previsao nacional de tempo de espera nos portos brasileiros?"
elif get_premium_config(porto_selecionado.upper()):
    pergunta_modelo = (
        "Qual a previsao de tempo de espera para o navio, berco ou categoria selecionados no terminal?"
    )
else:
    pergunta_modelo = (
        "Qual a previsao de tempo de espera para atracacao no porto selecionado?"
    )
st.markdown(
    f"<div class='question-text'>Pergunta do modelo: {pergunta_modelo}</div>",
    unsafe_allow_html=True,
)


def clima_tone(chuva_mm):
    if chuva_mm > 20:
        return "Criticas", "#F29F05"
    if chuva_mm > 10:
        return "Alerta", "#F29F05"
    return "Favoraveis", "#1E5F9C"




ICON_SUMMARY = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="18" y1="20" x2="18" y2="10"></line>'
    '<line x1="12" y1="20" x2="12" y2="4"></line>'
    '<line x1="6" y1="20" x2="6" y2="14"></line>'
    "</svg>"
)
ICON_TREND = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>'
    '<polyline points="17 6 23 6 23 12"></polyline>'
    "</svg>"
)
ICON_DETAILS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>'
    '<polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>'
    '<line x1="12" y1="22.08" x2="12" y2="12"></line>'
    "</svg>"
)
ICON_INSIGHTS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>'
    '<rect x="9" y="9" width="6" height="6"></rect>'
    '<line x1="9" y1="1" x2="9" y2="4"></line>'
    '<line x1="15" y1="1" x2="15" y2="4"></line>'
    '<line x1="9" y1="20" x2="9" y2="23"></line>'
    '<line x1="15" y1="20" x2="15" y2="23"></line>'
    '<line x1="20" y1="9" x2="23" y2="9"></line>'
    '<line x1="20" y1="14" x2="23" y2="14"></line>'
    '<line x1="1" y1="9" x2="4" y2="9"></line>'
    '<line x1="1" y1="14" x2="4" y2="14"></line>'
    "</svg>"
)
ICON_LOGS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="4 17 10 11 4 5"></polyline>'
    '<line x1="12" y1="19" x2="20" y2="19"></line>'
    "</svg>"
)


def render_section_title(title, icon_svg):
    st.markdown(
        f"<div class='section-title'>{icon_svg}<span>{title}</span></div>",
        unsafe_allow_html=True,
    )


def format_datetime_table(series):
    values = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return values.dt.strftime("%d/%m %H:%M").fillna("-")


def build_comparativo_lineup(df_pred_view, navio_col):
    if df_pred_view is None or df_pred_view.empty:
        return None
    df = df_pred_view.reset_index(drop=True).copy()
    navio_name_col = navio_col if navio_col in df.columns else None
    if not navio_name_col and "Navio" in df.columns:
        navio_name_col = "Navio"
    df["posicao_lineup"] = np.arange(1, len(df) + 1)
    if "eta_mais_espera" in df.columns:
        eta = pd.to_datetime(df["eta_mais_espera"], errors="coerce")
        df["posicao_prevista"] = eta.rank(method="first")
    elif "tempo_espera_previsto_horas" in df.columns:
        espera = pd.to_numeric(df["tempo_espera_previsto_horas"], errors="coerce")
        df["posicao_prevista"] = espera.rank(method="first")
    else:
        df["posicao_prevista"] = df["posicao_lineup"]
    df["posicao_prevista"] = df["posicao_prevista"].astype("Int64")
    df["delta_posicao"] = df["posicao_prevista"] - df["posicao_lineup"]

    data = {}
    if navio_name_col:
        data["Navio"] = df[navio_name_col].astype(str)
    if "Berco" in df.columns:
        data["Berco"] = df["Berco"].astype(str)
    if "Chegada" in df.columns:
        data["ETA_lineup"] = format_datetime_table(df["Chegada"])
        eta_lineup = pd.to_datetime(df["Chegada"], errors="coerce", dayfirst=True)
    else:
        eta_lineup = pd.Series([pd.NaT] * len(df))
    data["Posicao_lineup"] = df["posicao_lineup"]
    data["Posicao_prevista"] = df["posicao_prevista"]
    data["Delta_posicao"] = df["delta_posicao"]
    if "tempo_espera_previsto_horas" in df.columns:
        espera_prevista_h = pd.to_numeric(
            df["tempo_espera_previsto_horas"], errors="coerce"
        )
        data["Espera_prevista_h"] = espera_prevista_h.round(2)
    if "eta_mais_espera" in df.columns:
        eta_espera = pd.to_datetime(df["eta_mais_espera"], errors="coerce")
        data["ETA_com_espera"] = format_datetime_table(eta_espera)
        atraso_h = (eta_espera - eta_lineup).dt.total_seconds() / 3600
        data["Atraso_vs_ETA_h"] = atraso_h.round(2)
    if "risco_previsto" in df.columns:
        data["Risco"] = df["risco_previsto"].astype(str)
    return pd.DataFrame(data)


def style_comparativo(df):
    highlight_cols = [col for col in ["ETA_lineup", "ETA_com_espera"] if col in df.columns]
    if not highlight_cols:
        return df.style
    styles = {col: "color: #c00000; font-weight: 600;" for col in highlight_cols}
    return df.style.set_properties(**styles, subset=highlight_cols)


def compute_results():
    live_data = {"clima": None, "pam": None, "precos": None}
    if porto_selecionado != "NACIONAL":
        try:
            porto_key = porto_selecionado.upper()
            porto_cfg = PORT_MUNICIPIO_UF.get(porto_key, {})
            municipio = porto_cfg.get("municipio", porto_selecionado)
            uf = porto_cfg.get("uf", "MA")
            station_id = fetch_inmet_station_id(municipio=municipio)
            live_data["clima"] = fetch_inmet_latest(station_id)
            live_data["pam"] = fetch_pam_latest(uf=uf)
            live_data["precos"] = fetch_ipea_latest()
        except Exception:
            live_data = {"clima": None, "pam": None, "precos": None}
        port_mapping = load_port_mapping()
        ais_df = load_latest_ais_features()
        if ais_df is not None:
            live_data["ais_df"] = filter_features_by_port(
                ais_df, porto_selecionado, port_mapping
            )

    df_pred = None
    df_pred_view = None
    modo = "BASIC"
    if porto_selecionado != "NACIONAL" and not df_lineup.empty:
        tem_dados_terminal = has_terminal_data(df_lineup)
        if lineup_path and lineup_path.suffix.lower() == ".xlsx":
            tem_dados_terminal = True
        df_pred = inferir_lineup_inteligente(
            df_lineup,
            live_data,
            porto_selecionado.upper(),
            tem_dados_terminal=tem_dados_terminal,
        )
        if "tier" in df_pred.columns and df_pred["tier"].eq("PREMIUM").any():
            modo = "PREMIUM"
        PREDICTED_DIR.mkdir(parents=True, exist_ok=True)
        data_tag = datetime.today().strftime("%Y%m%d")
        output_path = PREDICTED_DIR / f"lineup_previsto_{porto_selecionado}_{data_tag}.csv"
        df_pred.to_csv(output_path, index=False)

    df_pred_view = df_pred
    if df_pred is not None and berco_selecionado != "Todos" and "Berco" in df_pred.columns:
        df_pred_view = df_pred[df_pred["Berco"] == berco_selecionado]
    if (
        df_pred_view is not None
        and navio_selecionado != "Todos"
        and navio_col
        and navio_col in df_pred_view.columns
    ):
        navio_norm = df_pred_view[navio_col].astype(str).str.strip()
        df_pred_view = df_pred_view[navio_norm == str(navio_selecionado).strip()]
    if (
        df_pred_view is not None
        and tipo_navio_selecionado != "Todos"
        and tipo_navio_col
        and tipo_navio_col in df_pred_view.columns
    ):
        tipo_norm = df_pred_view[tipo_navio_col].astype(str).str.strip()
        df_pred_view = df_pred_view[tipo_norm == str(tipo_navio_selecionado).strip()]

    fila_base = st.session_state.get("fila_base", 0)
    fila_media = max(int(fila_base / 2), 10) if fila_base else 10
    risco, _, motivo = calcular_risco(chuva_prevista, fila_atual, fila_media)
    if risco == "Baixo":
        estimativa = "2-3 dias"
        dias_min, dias_max = 2, 3
    elif risco == "Medio":
        estimativa = "3-5 dias"
        dias_min, dias_max = 3, 5
    else:
        estimativa = "5-7 dias"
        dias_min, dias_max = 5, 7

    espera_range = estimativa
    atracacao_prevista = pd.Timestamp(data_chegada) + pd.Timedelta(days=dias_max)
    if df_pred_view is not None and "tempo_espera_previsto_dias" in df_pred_view.columns:
        dias = df_pred_view["tempo_espera_previsto_dias"].dropna()
        if not dias.empty:
            q25, q75 = dias.quantile([0.25, 0.75])
            espera_range = f"{int(max(1, np.floor(q25)))}-{int(np.ceil(q75))} dias"
    if df_pred_view is not None and "eta_mais_espera" in df_pred_view.columns:
        eta_min = pd.to_datetime(df_pred_view["eta_mais_espera"], errors="coerce").min()
        if not pd.isna(eta_min):
            atracacao_prevista = eta_min

    condicao_clima, condicao_cor = clima_tone(chuva_prevista)

    fila_diaria = pd.DataFrame()
    if df_lineup is not None and not df_lineup.empty:
        if "Chegada" in df_lineup.columns:
            data_base = pd.to_datetime(df_lineup["Chegada"], errors="coerce", dayfirst=True)
        else:
            data_base = pd.Series([pd.NaT] * len(df_lineup))
        if data_base.isna().all():
            for fallback in ["Atualizacao", "ExtraidoEm"]:
                if fallback in df_lineup.columns:
                    data_base = pd.to_datetime(
                        df_lineup[fallback], errors="coerce", dayfirst=True
                    )
                    if not data_base.isna().all():
                        break
        fila_diaria = (
            pd.DataFrame({"data": data_base.dt.date})
            .dropna()
            .groupby("data")
            .size()
            .reset_index(name="fila")
        )
        fila_diaria["data"] = pd.to_datetime(fila_diaria["data"], errors="coerce")
    if fila_diaria.empty:
        base = pd.date_range(datetime.today().date(), periods=7, freq="D")
        fila_diaria = pd.DataFrame({"data": base, "fila": [0] * 7})

    berco_previsto = "-"
    if df_pred_view is not None and "Berco" in df_pred_view.columns:
        berco_previsto = (
            df_pred_view["Berco"].dropna().mode().iloc[0]
            if not df_pred_view["Berco"].dropna().empty
            else "-"
        )
    tx_efetiva = (
        pd.to_numeric(df_lineup["TX_EFETIVA"], errors="coerce").median()
        if "TX_EFETIVA" in df_lineup.columns
        else np.nan
    )
    dwt_medio = (
        pd.to_numeric(df_lineup["DWT"], errors="coerce").median()
        if "DWT" in df_lineup.columns
        else np.nan
    )
    if not np.isnan(tx_efetiva):
        produtividade = f"{tx_efetiva:,.0f} t/h".replace(",", ".")
    else:
        produtividade = "-"
    if not np.isnan(tx_efetiva) and not np.isnan(dwt_medio) and tx_efetiva > 0:
        tempo_operacao = f"{(dwt_medio / tx_efetiva):.1f} h"
    else:
        tempo_operacao = "-"

    mae_esperado = None
    if df_pred_view is not None and "mae_esperado" in df_pred_view.columns:
        mae_esperado = df_pred_view["mae_esperado"].dropna().median()

    espera_horas_estimada = None
    if df_pred_view is not None and "tempo_espera_previsto_horas" in df_pred_view.columns:
        espera_horas_estimada = (
            pd.to_numeric(df_pred_view["tempo_espera_previsto_horas"], errors="coerce")
            .dropna()
            .median()
        )
    if espera_horas_estimada is None or np.isnan(espera_horas_estimada):
        espera_horas_estimada = float(dias_max * 24)
    mae_texto = (
        f" (MAE esperado: ~{int(round(mae_esperado))}h — "
        "margem tipica de erro do modelo)"
        if mae_esperado
        else ""
    )
    if navio_selecionado != "Todos":
        alvo = f"o navio {navio_selecionado}"
    elif tipo_navio_selecionado != "Todos":
        alvo = f"o tipo de navio {tipo_navio_selecionado}"
    elif berco_selecionado != "Todos":
        alvo = f"o berco {berco_selecionado}"
    else:
        alvo = f"o porto {porto_selecionado}"
    mensagem_espera = (
        f"A previsao e de {int(round(espera_horas_estimada))} horas "
        f"para o tempo estimado de espera de {alvo}.{mae_texto}"
    )
    if modo == "PREMIUM":
        confiabilidade = "Alta"
    elif mae_esperado is None:
        confiabilidade = "Media"
    elif mae_esperado <= 40:
        confiabilidade = "Alta"
    elif mae_esperado <= 80:
        confiabilidade = "Media"
    else:
        confiabilidade = "Baixa"

    insights = []
    if chuva_prevista > 10:
        insights.append("Chuva relevante nas proximas 72h.")
    if fila_atual > fila_media:
        insights.append("Fila acima da media historica do porto.")
    if modo == "PREMIUM":
        insights.append("Dados do terminal aplicados (premium).")
    insights.append(f"Confiabilidade da previsao: {confiabilidade}.")

    navio_previsto = "-"
    navio_espera = "-"
    navio_eta = "-"
    if navio_selecionado != "Todos":
        navio_previsto = navio_selecionado
        if df_pred_view is not None and not df_pred_view.empty:
            navio_row = df_pred_view.sort_values("eta_mais_espera").iloc[0]
            navio_espera_val = navio_row.get("tempo_espera_previsto_horas")
            if pd.notna(navio_espera_val):
                navio_espera = f"{float(navio_espera_val):.1f} h"
            navio_eta_val = navio_row.get("eta_mais_espera")
            if pd.notna(navio_eta_val):
                navio_eta = format_date_short(navio_eta_val)

    tipo_navio_previsto = "-"
    if tipo_navio_selecionado != "Todos":
        tipo_navio_previsto = tipo_navio_selecionado

    return {
        "df_pred": df_pred,
        "df_pred_view": df_pred_view,
        "modo": modo,
        "espera_range": espera_range,
        "atracacao_prevista": atracacao_prevista,
        "condicao_clima": condicao_clima,
        "condicao_cor": condicao_cor,
        "fila_diaria": fila_diaria,
        "berco_previsto": berco_previsto,
        "produtividade": produtividade,
        "tempo_operacao": tempo_operacao,
        "insights": insights,
        "confiabilidade": confiabilidade,
        "meta": meta,
        "fila_media": fila_media,
        "mensagem_espera": mensagem_espera,
        "navio_previsto": navio_previsto,
        "navio_espera": navio_espera,
        "navio_eta": navio_eta,
        "tipo_navio_previsto": tipo_navio_previsto,
    }


if "resultado" not in st.session_state:
    st.session_state["resultado"] = None
if "erro_resultado" not in st.session_state:
    st.session_state["erro_resultado"] = None
if "params_key" not in st.session_state:
    st.session_state["params_key"] = None

params_key = json.dumps(
    {
        "porto": porto_selecionado,
        "tipo_carga": tipo_carga,
        "data_chegada": str(data_chegada),
        "chuva_prevista": chuva_prevista,
        "fila_atual": fila_atual,
        "berco": berco_selecionado,
        "navio": navio_selecionado,
        "tipo_navio": tipo_navio_selecionado,
    },
    sort_keys=True,
)

if gerar or st.session_state["resultado"] is None or st.session_state["params_key"] != params_key:
    try:
        st.session_state["resultado"] = compute_results()
        st.session_state["erro_resultado"] = None
        st.session_state["params_key"] = params_key
    except Exception as exc:
        st.session_state["erro_resultado"] = str(exc)

resultado = st.session_state.get("resultado")

if st.session_state.get("erro_resultado"):
    st.error(f"Falha ao gerar previsao: {st.session_state['erro_resultado']}")

if not resultado:
    st.info("Defina os parametros na barra lateral e clique em Gerar Previsao.")
    st.stop()

tabs = st.tabs(["Painel", "Logs"])
with tabs[0]:
    display_mode = resultado["modo"]
    if porto_selecionado != "NACIONAL" and get_premium_config(porto_selecionado.upper()):
        display_mode = "PREMIUM"
    if display_mode == "PREMIUM":
        st.markdown(
            "<div class='mode-banner premium'>MODO PREMIUM - Precisao aprimorada com dados do terminal</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='mode-banner'>MODO BASICO - Dados publicos ANTAQ + Clima</div>",
            unsafe_allow_html=True,
        )

    render_section_title("Resumo Executivo", ICON_SUMMARY)
    st.markdown(
        f"""
<div class="card-grid">
  <div class="card">
    <div class="card-label">Tempo estimado de espera</div>
    <div class="card-value" style="color: var(--accent);">{resultado['espera_range']}</div>
  </div>
  <div class="card">
    <div class="card-label">Previsao de atracacao</div>
    <div class="card-value">{format_date_short(resultado['atracacao_prevista'])}</div>
    <div class="card-sub">Line-up atualizado: {format_datetime_short(lineup_updated_at)}</div>
  </div>
  <div class="card">
    <div class="card-label">Navios no fundeio</div>
    <div class="card-value">{fila_atual}</div>
    <div class="card-sub">Line-up atualizado: {format_datetime_short(lineup_updated_at)}</div>
  </div>
    <div class="card">
      <div class="card-label">Condicoes climaticas</div>
      <div class="card-value" style="color: {resultado['condicao_cor']};">{resultado['condicao_clima']}</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='callout'>{resultado['mensagem_espera']}</div>",
        unsafe_allow_html=True,
    )

    render_section_title("Detalhes Operacionais", ICON_DETAILS)
    st.markdown(
        f"""
<div class="panel">
  <ul class="panel-list">
      <li>Tipo de carga: {tipo_carga}</li>
      <li>Navio selecionado: {resultado['navio_previsto']}</li>
      <li>Tipo de navio selecionado: {resultado['tipo_navio_previsto']}</li>
      <li>Espera prevista (navio): {resultado['navio_espera']}</li>
      <li>ETA com espera (navio): {resultado['navio_eta']}</li>
      <li>Berco previsto: {resultado['berco_previsto']}</li>
      <li>Produtividade estimada: {resultado['produtividade']}</li>
      <li>Tempo de operacao: {resultado['tempo_operacao']}</li>
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )

    render_section_title("Insights do Modelo", ICON_INSIGHTS)
    insights_html = "".join([f"<li>{item}</li>" for item in resultado["insights"]])
    st.markdown(
        f"""
<div class="panel">
  <ul class="panel-list">
    {insights_html}
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )

    comparativo = build_comparativo_lineup(resultado["df_pred_view"], navio_col)
    if comparativo is not None and not comparativo.empty:
        st.markdown(
            f"<div class='section-title table-title'>{ICON_TREND}<span>Tabela comparativa: Line-up x Modelo</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='table-caption'>Compara a ordem do line-up com a ordem prevista pelo modelo, "
            "incluindo impacto esperado e ETA com espera.</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(style_comparativo(comparativo), use_container_width=True, height=320)
        export_tag = normalizar_texto(porto_selecionado).lower()
        export_name = f"comparativo_lineup_{export_tag}_{datetime.today().strftime('%Y%m%d')}.csv"
        st.download_button(
            "Exportar comparativo CSV",
            data=comparativo.to_csv(index=False).encode("utf-8"),
            file_name=export_name,
            mime="text/csv",
        )
        st.markdown(
            """
<div class="table-definitions">
  <strong>Definicoes da tabela</strong>
  <ul>
    <li>ETA_lineup: horario de chegada informado no line-up.</li>
    <li>Posicao_lineup: ordem original do line-up (1 = primeiro).</li>
    <li>Posicao_prevista: ordem calculada pelo modelo com base na espera prevista.</li>
    <li>Delta_posicao: diferenca entre posicao prevista e posicao original.</li>
    <li>Espera_prevista_h: horas estimadas de espera antes de atracar.</li>
    <li>ETA_com_espera: tempo entre o ETA informado e o momento estimado de atracacao (ETA + espera).</li>
    <li>Atraso_vs_ETA_h: diferenca em horas entre ETA_com_espera e ETA_lineup.</li>
    <li>Risco: classificacao do risco operacional (baixo, medio, alto).</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )

with tabs[1]:
    render_section_title("Logs Tecnicos", ICON_LOGS)
    st.write("Porto selecionado:", porto_selecionado)
    st.write("Perfil inferido:", perfil_porto)
    st.write("Fila media calculada:", resultado["fila_media"])
    if resultado["df_pred_view"] is not None:
        st.dataframe(resultado["df_pred_view"].head(200), use_container_width=True)
    if resultado["meta"]:
        st.json(resultado["meta"])

ultima_atualizacao = "-"
if MODEL_METADATA_PATH.exists():
    ultima_atualizacao = datetime.fromtimestamp(MODEL_METADATA_PATH.stat().st_mtime).strftime("%d/%m/%Y")
st.markdown(
    f"<div class='footer'>Ultima atualizacao: {ultima_atualizacao} | (c) 2026 - Projeto Previsao de Fila</div>",
    unsafe_allow_html=True,
)
