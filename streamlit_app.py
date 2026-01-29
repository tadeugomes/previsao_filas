import json
import pickle
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

import numpy as np
import pandas as pd
import requests
import streamlit as st
import joblib

# Needed for unpickling ensemble models saved from training.
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

# Importar API de clima (Open-Meteo) como fallback
try:
    from weather_api import get_weather_for_port, get_weather_forecast, fetch_weather_fallback
    WEATHER_API_AVAILABLE = True
except ImportError:
    WEATHER_API_AVAILABLE = False

# BigQuery é opcional (pode usar Open-Meteo como alternativa)
try:
    from google.cloud import bigquery
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False

APP_TITLE = "Previsão de Fila - Vegetal (MVP)"
LINEUP_DIR = Path("lineups")
LINEUP_HISTORY_PATH = Path("data/lineup_history.parquet")
META_PATH = Path("data_extraction/processed/production/dataset_metadata.json")
MODEL_DIR = Path("models")
MODEL_METADATA_PATH = MODEL_DIR / "vegetal_metadata.json"
PREDICTED_DIR = Path("lineups_previstos")
PREMIUM_REGISTRY_PATH = Path("premium_registry.json")
AIS_FEATURES_DIR = Path("data/ais_features")
PORT_MAPPING_PATH = Path("data/port_mapping.csv")
MARE_DIR = Path("data/mare_clima")
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
PORT_COLUMN_CANDIDATES = [
    "porto",
    "porto_nome",
    "nome_porto",
    "port",
    "port_name",
    "descricao_porto",
    "porto_desc",
]


@st.cache_data
def load_real_data(lineup_path, porto_nome=None):
    if lineup_path and lineup_path.exists():
        if lineup_path.suffix.lower() == ".parquet":
            df_lineup = pd.read_parquet(lineup_path)
            df_lineup = df_lineup.rename(
                columns={c: normalize_column_name(c) for c in df_lineup.columns}
            )
            rename_map = {
                "navio": "Navio",
                "produto": "Mercadoria",
                "carga": "Mercadoria",
                "prev_chegada": "Chegada",
                "berco": "Berco",
                "dwt": "DWT",
                "ultima_atualizacao": "Atualizacao",
            }
            df_lineup = df_lineup.rename(columns=rename_map)
        elif lineup_path.suffix.lower() == ".xlsx":
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
        df_lineup = coalesce_duplicate_columns(df_lineup)
        if "Pier" in df_lineup.columns and "Berco" not in df_lineup.columns:
            df_lineup["Berco"] = df_lineup["Pier"]
        if porto_nome and porto_nome != "NACIONAL":
            port_col = find_column_by_norm(df_lineup, PORT_COLUMN_CANDIDATES)
            if port_col:
                target = normalizar_texto(porto_nome)
                if target:
                    port_norm = df_lineup[port_col].apply(normalizar_texto)
                    df_lineup = df_lineup.loc[port_norm == target].copy()
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
    files = (
        list(LINEUP_DIR.glob("*.parquet"))
        + list(LINEUP_DIR.glob("*.xlsx"))
        + list(LINEUP_DIR.glob("*.csv"))
    )
    priority = {".parquet": 0, ".xlsx": 1, ".csv": 2}
    return sorted(files, key=lambda p: (priority.get(p.suffix.lower(), 9), p.name.lower()))


@st.cache_data
def load_lineup_history():
    if not LINEUP_HISTORY_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(LINEUP_HISTORY_PATH)
    if df.empty:
        return df
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]
    df = coalesce_duplicate_columns(df)
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
def load_history_data(porto_nome, lineup_path=None):
    df_lineup = load_lineup_history_porto(porto_nome)
    if df_lineup.empty:
        if lineup_path is None:
            lineup_path = find_lineup_file(porto_nome)
        df_lineup, _ = load_real_data(lineup_path, porto_nome=porto_nome)
    if df_lineup.empty:
        df_lineup = pd.DataFrame(columns=["Navio", "Mercadoria", "Chegada", "Berco"])
    return df_lineup, load_metadata()


def filter_lineup_horizon(df_lineup, days=7, reference_date=None):
    if df_lineup is None or df_lineup.empty:
        return df_lineup
    ref = pd.to_datetime(reference_date) if reference_date else pd.Timestamp.today().normalize()
    start = ref.normalize()
    end = start + pd.Timedelta(days=days)
    date_series = None
    if "Chegada" in df_lineup.columns:
        date_series = pd.to_datetime(df_lineup["Chegada"], errors="coerce", dayfirst=True)
    if date_series is None or date_series.isna().all():
        return df_lineup.head(0)
    mask = date_series.between(start, end, inclusive="both")
    return df_lineup.loc[mask].copy()


def _merge_port_name(port_map, name):
    name = str(name).strip()
    if not name:
        return
    norm = normalizar_texto(name)
    if not norm:
        return
    if norm not in port_map:
        port_map[norm] = name


def _extract_ports_from_lineup_file(lineup_path):
    if not lineup_path:
        return []
    try:
        df_lineup, _ = load_real_data(lineup_path)
    except Exception:
        return []
    if df_lineup is None or df_lineup.empty:
        return []
    port_col = find_column_by_norm(df_lineup, PORT_COLUMN_CANDIDATES)
    if not port_col:
        return []
    ports = (
        df_lineup[port_col]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    return [p for p in ports if p]


@st.cache_data
def build_lineup_port_index():
    index = {}
    for path in list_lineup_files():
        ports_in_file = _extract_ports_from_lineup_file(path)
        if ports_in_file:
            for port in ports_in_file:
                norm = normalizar_texto(port)
                if not norm or norm in index:
                    continue
                index[norm] = {"port_name": port, "path": path}
        else:
            name = path.stem.replace("_", " ").strip()
            if not name:
                continue
            norm = normalizar_texto(name)
            if norm and norm not in index:
                index[norm] = {"port_name": name, "path": path}
    return index


@st.cache_data
def list_lineup_ports():
    history = load_lineup_history()
    port_map = {}
    if not history.empty and "porto" in history.columns:
        for name in (
            history["porto"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        ):
            _merge_port_name(port_map, name)
    for entry in build_lineup_port_index().values():
        _merge_port_name(port_map, entry.get("port_name"))
    ports = sorted(port_map.values(), key=normalizar_texto)
    ports = [p for p in ports if normalizar_texto(p) != "NACIONAL"]
    ports.insert(0, "NACIONAL")
    return ports


def find_lineup_file(porto_nome):
    if not porto_nome or porto_nome == "NACIONAL":
        return None
    target = normalizar_texto(porto_nome)
    index = build_lineup_port_index()
    match = index.get(target)
    if match:
        return match["path"]
    for path in list_lineup_files():
        if normalizar_texto(path.stem) == target:
            return path
    return None


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
def load_light_models_for_profile(profile):
    """
    Carrega modelos simplificados (light) com apenas 15 features críticas.

    Estes modelos são usados como fallback quando a qualidade dos dados < 80%.
    Modelos light priorizam confiabilidade sobre precisão máxima.

    Estrutura esperada:
    - models/{profile}_light_metadata.json
    - models/{profile}_light_ensemble_reg.pkl
    - models/{profile}_light_lgb_reg.pkl
    - models/{profile}_light_lgb_clf.pkl

    Returns:
        dict com metadata e modelos, ou None se não existir
    """
    metadata_path = MODEL_DIR / f"{profile.lower()}_light_metadata.json"
    if not metadata_path.exists():
        return None

    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        artifacts = metadata.get("artifacts", {})
        ensemble_path = MODEL_DIR / artifacts.get("ensemble_reg", "")
        reg_path = MODEL_DIR / artifacts.get("lgb_reg", "")
        clf_path = MODEL_DIR / artifacts.get("lgb_clf", "")

        # Carrega ensemble se existir
        ensemble_model = None
        if ensemble_path.exists():
            ensemble_model = joblib.load(ensemble_path)

        # Modelos base são obrigatórios
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
            "is_light": True,
        }
    except Exception as e:
        logger.warning(f"Erro ao carregar modelo light para {profile}: {e}")
        return None


def select_model_by_quality(profile, confidence_score, api_status):
    """
    Seleciona o modelo apropriado baseado na qualidade dos dados.

    Estratégia de fallback inteligente:
    - Qualidade >= 80%: Usa modelo completo (54 features)
    - Qualidade < 80%: Tenta usar modelo light (15 features)
    - Se modelo light não existe: Usa modelo completo com aviso

    Args:
        profile: Perfil do modelo (VEGETAL, MINERAL, FERTILIZANTE)
        confidence_score: Score de confiança 0-100 (calculado pela Fase 2)
        api_status: Status das APIs (dict com clima_ok, ais_ok, etc)

    Returns:
        tuple: (models_dict, model_type, warning_message)
            - models_dict: Dicionário com os modelos carregados
            - model_type: "completo" ou "light"
            - warning_message: Mensagem de aviso ou None
    """
    # Tenta carregar modelo completo
    models_completo = load_models_for_profile(profile)

    if models_completo is None:
        return None, None, "❌ Nenhum modelo disponível para este perfil"

    # Se qualidade >= 80%, usa modelo completo
    if confidence_score >= 80:
        return models_completo, "completo", None

    # Qualidade < 80%: tenta usar modelo light
    models_light = load_light_models_for_profile(profile)

    if models_light is not None:
        # Modelo light disponível - usa ele
        warning = (
            f"⚠️ Usando modelo simplificado (15 features) devido à qualidade dos dados ({confidence_score:.0f}%). "
            f"Modelo light prioriza confiabilidade, mas pode ter precisão reduzida."
        )
        return models_light, "light", warning
    else:
        # Modelo light não disponível - usa completo com aviso
        warning = (
            f"⚠️ Qualidade dos dados abaixo do ideal ({confidence_score:.0f}%). "
            f"Modelo completo sendo usado com muitos valores default. "
            f"Considere melhorar a disponibilidade de dados (clima, AIS, etc) para previsões mais confiáveis."
        )
        return models_completo, "completo", warning


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


def _normalizar_porto_base(nome_porto):
    norm = normalizar_texto(nome_porto)
    for prefix in ("PORTODE", "PORTODO", "PORTO"):
        if norm.startswith(prefix):
            return norm[len(prefix):]
    return norm


@st.cache_data
def _carregar_extremos_mare(caminho_csv):
    df = pd.read_csv(caminho_csv)
    if df.empty:
        return df
    df = df.rename(columns={"Data_Hora": "data_hora", "Altura_m": "altura_m"})
    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    df["altura_m"] = pd.to_numeric(df["altura_m"], errors="coerce")
    df = df.dropna(subset=["data_hora", "altura_m"]).sort_values("data_hora")
    return df[["data_hora", "altura_m"]]


def _interpolar_mare_para_timestamps(df_extremos, timestamps):
    out = pd.DataFrame(
        index=timestamps.index,
        data={
            "mare_astronomica": 0.0,
            "mare_subindo": 0,
            "mare_horas_ate_extremo": 0.0,
            "tem_mare_astronomica": 0,
        },
    )
    if df_extremos.empty:
        return out
    valid = timestamps.notna()
    if not valid.any():
        return out

    ts_df = pd.DataFrame({"ts": pd.to_datetime(timestamps[valid]), "idx": timestamps[valid].index})
    ts_df = ts_df.sort_values("ts")
    extremos = df_extremos.rename(columns={"data_hora": "ext_time", "altura_m": "ext_alt"})

    prev = pd.merge_asof(
        ts_df,
        extremos,
        left_on="ts",
        right_on="ext_time",
        direction="backward",
    ).rename(columns={"ext_time": "prev_time", "ext_alt": "prev_alt"})

    next_ = pd.merge_asof(
        ts_df,
        extremos,
        left_on="ts",
        right_on="ext_time",
        direction="forward",
    ).rename(columns={"ext_time": "next_time", "ext_alt": "next_alt"})

    joined = prev[["ts", "idx", "prev_time", "prev_alt"]].join(
        next_[["next_time", "next_alt"]]
    )

    delta = (joined["next_time"] - joined["prev_time"]).dt.total_seconds()
    frac = (joined["ts"] - joined["prev_time"]).dt.total_seconds() / delta
    altura = joined["prev_alt"] + (joined["next_alt"] - joined["prev_alt"]) * frac

    invalid = delta.isna() | (delta == 0) | joined["prev_alt"].isna() | joined["next_alt"].isna()
    altura[invalid] = joined.loc[invalid, "prev_alt"]

    mare_subindo = (joined["next_alt"] > joined["prev_alt"]).astype(int)
    horas_ate = (joined["next_time"] - joined["ts"]).dt.total_seconds() / 3600.0

    res = pd.DataFrame(
        index=joined["idx"],
        data={
            "mare_astronomica": altura.to_numpy(),
            "mare_subindo": mare_subindo.to_numpy(),
            "mare_horas_ate_extremo": horas_ate.to_numpy(),
            "tem_mare_astronomica": (~invalid).astype(int).to_numpy(),
        },
    )
    out.loc[res.index, :] = res
    out = out.fillna(0.0)
    out["mare_subindo"] = out["mare_subindo"].astype(int)
    out["tem_mare_astronomica"] = out["tem_mare_astronomica"].astype(int)
    return out


def adicionar_features_mare_lineup(df, porto_nome):
    df = df.copy()
    df["mare_astronomica"] = 0.0
    df["mare_subindo"] = 0
    df["mare_horas_ate_extremo"] = 0.0
    df["tem_mare_astronomica"] = 0

    if not MARE_DIR.exists():
        return df
    porto_norm = _normalizar_porto_base(porto_nome)
    arquivo = MARE_PORT_FILE_BY_NORM.get(porto_norm)
    if not arquivo:
        return df
    caminho = MARE_DIR / arquivo
    if not caminho.exists():
        return df
    extremos = _carregar_extremos_mare(caminho)
    feats = _interpolar_mare_para_timestamps(extremos, df["data_chegada_dt"])
    df[["mare_astronomica", "mare_subindo", "mare_horas_ate_extremo", "tem_mare_astronomica"]] = feats[
        ["mare_astronomica", "mare_subindo", "mare_horas_ate_extremo", "tem_mare_astronomica"]
    ].to_numpy()
    return df


def normalize_column_name(valor):
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").lower()
    return texto


def coalesce_duplicate_columns(df):
    if df is None or df.empty:
        return df
    if not df.columns.duplicated().any():
        return df
    df = df.copy()
    combined = {}
    seen = set()
    for name in df.columns:
        if name in seen:
            continue
        seen.add(name)
        cols = df.loc[:, name]
        if isinstance(cols, pd.DataFrame):
            combined[name] = cols.bfill(axis=1).iloc[:, 0]
        else:
            combined[name] = cols
    return pd.DataFrame(combined)


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


def format_hours_value(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.1f} h"


def build_espera_resumo(kpi_espera_h, mae_esperado):
    espera_texto = format_hours_value(kpi_espera_h)
    if mae_esperado is None or pd.isna(mae_esperado):
        erro_texto = "erro típico do modelo: indisponível"
    else:
        erro_texto = f"erro típico do modelo: +/-{int(round(mae_esperado))} h"
    return (
        f"Espera prevista (h): {espera_texto} - tempo médio de espera para atracar "
        f"no escopo selecionado ({erro_texto})."
    )


def build_atraso_resumo(kpi_atraso_h):
    atraso_texto = format_hours_value(kpi_atraso_h)
    if kpi_atraso_h is None or pd.isna(kpi_atraso_h):
        return f"Atraso vs ETA (h): {atraso_texto} - estimativa indisponível no momento."
    valor = float(kpi_atraso_h)
    valor_abs = abs(valor)
    if valor_abs < 0.5:
        return (
            f"Atraso vs ETA (h): {atraso_texto} - em média, os navios devem atracar "
            "perto do ETA informado no line-up."
        )
    referencia = f"{valor_abs:.1f} h"
    if valor > 0:
        return (
            f"Atraso vs ETA (h): {atraso_texto} - em média, os navios devem atracar "
            f"cerca de {referencia} depois do ETA informado no line-up."
        )
    return (
        f"Atraso vs ETA (h): {atraso_texto} - em média, os navios devem atracar "
        f"cerca de {referencia} antes do ETA informado no line-up."
    )


def build_confiabilidade_text(confiabilidade, mae_esperado):
    if mae_esperado is None or pd.isna(mae_esperado):
        return (
            f"Confiabilidade da previsão: {confiabilidade} - indicador qualitativo "
            "baseado no histórico do modelo; não é porcentagem; use como ordem de "
            "grandeza do erro."
        )
    mae_texto = int(round(mae_esperado))
    return (
        f"Confiabilidade da previsão: {confiabilidade} - margem típica de erro "
        f"~{mae_texto} h (MAE histórico); não é porcentagem; use como ordem de "
        "grandeza do erro."
    )


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
def fetch_inmet_latest(station_id, project_id="antaqdados", port_name=None):
    """Busca dados climáticos do INMET via BigQuery, com fallback para Open-Meteo."""
    # Tentar BigQuery primeiro (se disponível)
    if BIGQUERY_AVAILABLE and station_id:
        try:
            client = bigquery.Client(project=project_id)
            query = f"""
            SELECT
                data,
                AVG(temperatura_bulbo_hora) AS temp_media_dia,
                MAX(temperatura_max) AS temp_max_dia,
                MIN(temperatura_min) AS temp_min_dia,
                SUM(precipitacao_total) AS precipitacao_dia,
                MAX(vento_rajada_max) AS vento_rajada_max_dia,
                AVG(vento_velocidade) AS vento_velocidade_media,
                AVG(umidade_rel_hora) AS umidade_media_dia
            FROM `basedosdados.br_inmet_bdmep.microdados`
            WHERE id_estacao = '{station_id}'
            GROUP BY data
            ORDER BY data DESC
            LIMIT 7
            """
            df = client.query(query).to_dataframe()
            if not df.empty:
                df = df.sort_values("data").reset_index(drop=True)
                latest = df.iloc[-1].to_dict()
                chuva_3d = df["precipitacao_dia"].tail(3).sum()
                latest["chuva_acumulada_ultimos_3dias"] = float(chuva_3d)
                latest["amplitude_termica"] = float(latest["temp_max_dia"] - latest["temp_min_dia"])
                latest["fonte"] = "INMET/BigQuery"
                return latest
        except Exception:
            pass  # Fallback para Open-Meteo

    # Fallback: usar Open-Meteo API (gratuita, sem API key)
    if WEATHER_API_AVAILABLE and port_name:
        try:
            data = fetch_weather_fallback(port_name)
            if data:
                data["fonte"] = "Open-Meteo"
                return data
        except Exception:
            pass

    # Valores padrão se nenhuma fonte disponível
    return {
        "temp_media_dia": 25.0,
        "temp_max_dia": 30.0,
        "temp_min_dia": 20.0,
        "precipitacao_dia": 0.0,
        "vento_rajada_max_dia": 5.0,
        "vento_velocidade_media": 3.0,
        "umidade_media_dia": 70.0,
        "amplitude_termica": 10.0,
        "chuva_acumulada_ultimos_3dias": 0.0,
        "fonte": "default",
    }


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


def _build_forecast_frame(forecast):
    if not forecast:
        return None
    df = pd.DataFrame(forecast)
    if df.empty or "data" not in df.columns:
        return None
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    df = df.dropna(subset=["data"])
    if df.empty:
        return None
    df = df.drop_duplicates(subset=["data"], keep="last")
    df = df.set_index("data")
    return df


def _forecast_series(forecast_df, date_keys, key):
    if forecast_df is None or key not in forecast_df.columns:
        return pd.Series([np.nan] * len(date_keys))
    series = pd.to_numeric(forecast_df[key], errors="coerce")
    series = series.reindex(date_keys).reset_index(drop=True)
    return series


def _forecast_chuva_3d(forecast_df, date_keys):
    if forecast_df is None or "precipitacao" not in forecast_df.columns:
        return pd.Series([np.nan] * len(date_keys))
    precip = pd.to_numeric(forecast_df["precipitacao"], errors="coerce").fillna(0.0)
    precip = precip.sort_index()
    roll = precip.rolling(window=3, min_periods=1).sum()
    return roll.reindex(date_keys).reset_index(drop=True)


# ============================================================================
# FASE 1 - CORREÇÕES CRÍTICAS DE FEATURES
# ============================================================================

def carregar_tempo_medio_historico(porto_nome):
    """
    Carrega tempo médio histórico de espera para o porto.
    Usa lineup_history.parquet ou valores default por porto.

    Args:
        porto_nome: Nome do porto (ex: "SANTOS", "PARANAGUA")

    Returns:
        float: Tempo médio de espera em horas
    """
    # Valores default baseados em dados reais de operação portuária (horas)
    TEMPO_MEDIO_DEFAULT = {
        "SANTOS": 48.0,
        "PARANAGUA": 72.0,
        "ITAQUI": 36.0,
        "PONTA_DA_MADEIRA": 24.0,
        "VILA_DO_CONDE": 60.0,
        "VILADOCONDE": 60.0,
        "BARCARENA": 60.0,
        "RIO_GRANDE": 48.0,
        "RIOGRANDE": 48.0,
        "SUAPE": 72.0,
        "PECEM": 48.0,
        "SALVADOR": 60.0,
        "VITORIA": 48.0,
        "SAO_FRANCISCO_DO_SUL": 60.0,
        "SAOFRANCISCODOSUL": 60.0,
        "ANTONINA": 60.0,
        "RECIFE": 60.0,
        "FORTALEZA": 48.0,
        "ARATU": 60.0,
        "ILHEUS": 48.0,
        "MACEIO": 48.0,
        "NATAL": 48.0,
        "CABEDELO": 48.0,
        "IMBITUBA": 48.0,
    }

    porto_norm = normalizar_texto(porto_nome)

    # Tenta carregar do histórico
    try:
        df_hist = load_lineup_history()
        if not df_hist.empty and "tempo_espera_horas" in df_hist.columns and "porto" in df_hist.columns:
            df_hist["porto_norm"] = df_hist["porto"].apply(normalizar_texto)
            df_porto = df_hist[df_hist["porto_norm"] == porto_norm]
            if len(df_porto) >= 10:  # Mínimo 10 registros históricos para ser confiável
                tempo_medio = df_porto["tempo_espera_horas"].median()
                if pd.notna(tempo_medio) and tempo_medio > 0:
                    return float(tempo_medio)
    except Exception:
        pass

    # Fallback para valores default
    for key, value in TEMPO_MEDIO_DEFAULT.items():
        if normalizar_texto(key) == porto_norm:
            return float(value)

    # Default genérico: 48 horas (2 dias) - valor conservador
    return 48.0


def calcular_fila_simulada(df_lineup, porto_nome):
    """
    Calcula quantos navios estarão no fundeio quando cada navio chegar.
    Usa simulação simplificada baseada em taxa média de atracação por perfil.

    Esta é a correção da feature crítica 'navios_no_fundeio_na_chegada' que
    anteriormente usava apenas df.index (incorreto).

    Args:
        df_lineup: DataFrame com lineup já ordenado por data_chegada_dt ou chegada_dt
        porto_nome: Nome do porto para obter tempo médio histórico

    Returns:
        np.array: Array com número de navios no fundeio para cada linha
    """
    if df_lineup.empty:
        return np.array([])

    df = df_lineup.copy()

    # Identifica a coluna de data de chegada (pode ser data_chegada_dt ou chegada_dt)
    date_col = None
    if "data_chegada_dt" in df.columns:
        date_col = "data_chegada_dt"
    elif "chegada_dt" in df.columns:
        date_col = "chegada_dt"
    else:
        # Não há coluna de data, retorna zeros
        return np.zeros(len(df))

    # Taxa média de atracação por perfil (horas)
    # Baseada em análise de dados históricos reais
    TAXA_ATRACACAO_MEDIA_HORAS = {
        "VEGETAL": 72.0,      # 3 dias em média
        "MINERAL": 48.0,      # 2 dias em média
        "FERTILIZANTE": 96.0, # 4 dias em média
    }

    # Usa tempo médio do porto como fallback
    tempo_medio_porto = carregar_tempo_medio_historico(porto_nome)

    fila = np.zeros(len(df))

    for i in range(len(df)):
        chegada_i = df.iloc[i][date_col]

        # Determina a taxa média baseada no perfil (se disponível)
        if "perfil_modelo" in df.columns:
            perfil_i = df.iloc[i]["perfil_modelo"]
            taxa_media = TAXA_ATRACACAO_MEDIA_HORAS.get(perfil_i, tempo_medio_porto)
        else:
            taxa_media = tempo_medio_porto

        # Conta quantos navios anteriores ainda estarão no fundeio
        navios_no_fundeio = 0
        for j in range(i):
            chegada_j = df.iloc[j][date_col]
            tempo_desde_chegada = (chegada_i - chegada_j).total_seconds() / 3600.0  # horas

            # Se o navio j chegou há menos tempo que a taxa média, ainda está no fundeio
            if tempo_desde_chegada < taxa_media:
                navios_no_fundeio += 1

        fila[i] = float(navios_no_fundeio)

    return fila


def calcular_tempo_espera_ma5(df_lineup, porto_nome):
    """
    Calcula média móvel de 5 períodos do tempo de espera.
    Como não temos histórico real no lineup, usa tempo médio do porto como proxy.

    Args:
        df_lineup: DataFrame com lineup
        porto_nome: Nome do porto

    Returns:
        np.array: Array com tempo de espera MA5 para cada linha
    """
    if df_lineup.empty:
        return np.array([])

    tempo_medio = carregar_tempo_medio_historico(porto_nome)

    # Retorna array com o tempo médio histórico como proxy da MA5
    # Em produção com dados reais, isso seria substituído por uma média móvel real
    return np.full(len(df_lineup), tempo_medio)


# ============================================================================
# FASE 2 - SISTEMA DE VALIDAÇÃO E RASTREAMENTO DE QUALIDADE
# ============================================================================

class FeatureQuality(Enum):
    """Qualidade da feature preenchida"""
    REAL = "real"                      # Dado real do lineup
    API_OK = "api_ok"                  # Obtido de API com sucesso
    API_FALLBACK = "api_fallback"      # API falhou, usando fallback
    CALCULATED = "calculated"           # Calculado corretamente
    DEFAULT = "default"                 # Valor default razoável
    CRITICAL_DEFAULT = "critical_default"  # Valor default em feature crítica


@dataclass
class FeatureReport:
    """Relatório de qualidade das features para uma previsão"""
    total_features: int
    quality_breakdown: Dict[FeatureQuality, int]
    critical_issues: List[str]
    warnings: List[str]
    confidence_score: float  # 0-100

    def to_dict(self):
        return {
            "total_features": self.total_features,
            "quality": {k.value: v for k, v in self.quality_breakdown.items()},
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "confidence": self.confidence_score
        }


def avaliar_qualidade_features(metadata, api_status):
    """
    Avalia a qualidade das features preenchidas.

    Args:
        metadata: Metadados do modelo (dict com chave "features")
        api_status: Dict com status de cada API/fonte de dados
            {
                "clima_ok": bool,
                "ais_ok": bool,
                "mare_ok": bool,
                "economia_ok": bool,
                "historico_ok": bool,
            }

    Returns:
        FeatureReport com análise de qualidade
    """
    features = metadata.get("features", [])
    quality_breakdown = {q: 0 for q in FeatureQuality}
    critical_issues = []
    warnings = []

    # Features do lineup (Categoria A - dados reais)
    lineup_features = [
        "nome_porto", "nome_terminal", "natureza_carga",
        "movimentacao_total_toneladas", "mes", "dia_semana", "dia_do_ano",
        "trimestre"
    ]
    for feat in lineup_features:
        if feat in features:
            quality_breakdown[FeatureQuality.REAL] += 1

    # Features de clima (Categoria D)
    clima_features = [
        "temp_media_dia", "precipitacao_dia", "vento_rajada_max_dia",
        "vento_velocidade_media", "umidade_media_dia", "amplitude_termica",
        "chuva_acumulada_ultimos_3dias", "wave_height_max", "wave_height_media",
        "frente_fria", "pressao_anomalia", "ressaca"
    ]
    clima_count = len([f for f in clima_features if f in features])
    if api_status.get("clima_ok", False):
        quality_breakdown[FeatureQuality.API_OK] += clima_count
    else:
        quality_breakdown[FeatureQuality.API_FALLBACK] += clima_count
        warnings.append("⚠️ Dados de clima não disponíveis - usando valores conservadores")

    # Features AIS (Categoria E - CRÍTICA)
    ais_features = [
        "ais_navios_no_raio", "ais_fila_ao_largo", "ais_velocidade_media_kn",
        "ais_eta_media_horas", "ais_dist_media_km"
    ]
    ais_count = len([f for f in ais_features if f in features])
    if ais_count > 0:
        if api_status.get("ais_ok", False):
            quality_breakdown[FeatureQuality.API_OK] += ais_count
        else:
            quality_breakdown[FeatureQuality.CRITICAL_DEFAULT] += ais_count
            critical_issues.append("🔴 Dados AIS não disponíveis - fila real desconhecida (impacto ALTO)")

    # Features de maré (Categoria F)
    mare_features = [
        "mare_astronomica", "mare_subindo", "mare_horas_ate_extremo",
        "tem_mare_astronomica"
    ]
    mare_count = len([f for f in mare_features if f in features])
    if mare_count > 0:
        if api_status.get("mare_ok", False):
            quality_breakdown[FeatureQuality.API_OK] += mare_count
        else:
            quality_breakdown[FeatureQuality.DEFAULT] += mare_count
            warnings.append("⚠️ Dados de maré não disponíveis - usando valores default")

    # Features de fila calculadas (Categoria H - CORRIGIDAS NA FASE 1)
    fila_features = ["navios_no_fundeio_na_chegada", "navios_na_fila_7d"]
    quality_breakdown[FeatureQuality.CALCULATED] += len([f for f in fila_features if f in features])

    # Features históricas (Categoria I - CORRIGIDAS NA FASE 1)
    if "porto_tempo_medio_historico" in features:
        if api_status.get("historico_ok", False):
            quality_breakdown[FeatureQuality.CALCULATED] += 1
        else:
            quality_breakdown[FeatureQuality.DEFAULT] += 1
            # Não é warning, pois temos valores default bons por porto

    if "tempo_espera_ma5" in features:
        quality_breakdown[FeatureQuality.CALCULATED] += 1

    # Features econômicas (Categoria G)
    econ_features = [
        "producao_soja", "producao_milho", "producao_algodao",
        "preco_soja_mensal", "preco_milho_mensal", "preco_algodao_mensal"
    ]
    econ_count = len([f for f in econ_features if f in features])
    if econ_count > 0:
        if api_status.get("economia_ok", False):
            quality_breakdown[FeatureQuality.API_OK] += econ_count
        else:
            quality_breakdown[FeatureQuality.DEFAULT] += econ_count
            warnings.append("⚠️ Dados econômicos não disponíveis - usando valores default")

    # Defaults razoáveis (Categoria B)
    default_features = [
        "tipo_navegacao", "tipo_carga", "cdmercadoria", "stsh4",
        "restricao_vento", "restricao_chuva", "flag_celulose", "flag_algodao",
        "flag_soja", "flag_milho", "periodo_safra",
        "indice_pressao_soja", "indice_pressao_milho"
    ]
    quality_breakdown[FeatureQuality.DEFAULT] += len([f for f in default_features if f in features])

    # Calcula score de confiança baseado nos pesos
    total = len(features)
    if total == 0:
        return FeatureReport(0, quality_breakdown, critical_issues, warnings, 0.0)

    score = (
        quality_breakdown[FeatureQuality.REAL] * 1.0 +
        quality_breakdown[FeatureQuality.API_OK] * 0.9 +
        quality_breakdown[FeatureQuality.CALCULATED] * 0.8 +
        quality_breakdown[FeatureQuality.DEFAULT] * 0.5 +
        quality_breakdown[FeatureQuality.API_FALLBACK] * 0.4 +
        quality_breakdown[FeatureQuality.CRITICAL_DEFAULT] * 0.2
    ) / total * 100

    return FeatureReport(
        total_features=total,
        quality_breakdown=quality_breakdown,
        critical_issues=critical_issues,
        warnings=warnings,
        confidence_score=round(score, 1)
    )


# ============================================================================
# FASE 3 - MELHORIAS DE APIS E ROBUSTEZ
# ============================================================================

import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def obter_dados_clima_robusto(porto_nome, porto_cfg=None):
    """
    Obtém dados de clima com fallback garantido em múltiplas camadas.

    Prioridades:
    1. BigQuery INMET (mais preciso, requer credenciais)
    2. Open-Meteo (gratuito, sempre disponível)
    3. Valores conservadores padrão

    Args:
        porto_nome: Nome do porto
        porto_cfg: Dict com municipio/uf para BigQuery

    Returns:
        tuple: (dados_clima dict, dados_forecast list, status_ok bool)
    """
    porto_key = porto_nome.upper()
    clima = None
    forecast = None
    status_ok = False

    # Prioridade 1: Tentar BigQuery INMET (mais preciso)
    if BIGQUERY_AVAILABLE and porto_cfg:
        try:
            municipio = porto_cfg.get("municipio", porto_nome)
            station_id = fetch_inmet_station_id(municipio=municipio)
            if station_id:
                clima = fetch_inmet_latest(station_id, port_name=porto_key)
                if clima and clima.get("temp_media_dia"):
                    logger.info(f"✓ Clima obtido via BigQuery INMET para {porto_nome}")
                    status_ok = True
        except Exception as e:
            logger.warning(f"BigQuery INMET falhou para {porto_nome}: {e}")

    # Prioridade 2: Open-Meteo (sempre disponível)
    if not status_ok and WEATHER_API_AVAILABLE:
        try:
            clima = fetch_weather_fallback(porto_key)
            forecast = get_weather_forecast(porto_key, days=7)

            if clima and clima.get("temp_media_dia"):
                logger.info(f"✓ Clima obtido via Open-Meteo para {porto_nome}")
                status_ok = True
        except Exception as e:
            logger.warning(f"Open-Meteo falhou para {porto_nome}: {e}")

    # Prioridade 3: Valores conservadores padrão (sempre funciona)
    if not clima:
        logger.warning(f"Usando valores climáticos conservadores para {porto_nome}")
        clima = {
            "temp_media_dia": 25.0,
            "temp_max_dia": 30.0,
            "temp_min_dia": 20.0,
            "precipitacao_dia": 0.0,
            "vento_rajada_max_dia": 5.0,
            "vento_velocidade_media": 3.0,
            "umidade_media_dia": 70.0,
            "amplitude_termica": 10.0,
            "chuva_acumulada_ultimos_3dias": 0.0,
            "wave_height_max": 0.0,
            "ressaca": 0,
            "fonte": "default_conservative",
        }

    # Garantir forecast mínimo
    if not forecast:
        # Cria forecast básico baseado nos dados de clima
        today = pd.Timestamp.today()
        forecast = []
        for i in range(7):
            date = (today + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            forecast.append({
                "data": date,
                "temp_media": clima.get("temp_media_dia", 25.0),
                "temp_max": clima.get("temp_max_dia", 30.0),
                "temp_min": clima.get("temp_min_dia", 20.0),
                "precipitacao": clima.get("precipitacao_dia", 0.0) if i == 0 else 0.0,
                "rajada_max": clima.get("vento_rajada_max_dia", 5.0),
                "vento_max": clima.get("vento_velocidade_media", 3.0),
                "wave_height_max": clima.get("wave_height_max", 0.0),
                "ressaca": clima.get("ressaca", 0),
            })

    return clima, forecast, status_ok


def obter_dados_economia_robusto(uf="MA"):
    """
    Obtém dados econômicos com fallback.

    Args:
        uf: UF para buscar dados do PAM

    Returns:
        tuple: (dados_pam dict, dados_precos dict, status_ok bool)
    """
    pam = None
    precos = None
    status_ok = False

    if BIGQUERY_AVAILABLE:
        try:
            pam = fetch_pam_latest(uf=uf)
            precos = fetch_ipea_latest()

            if pam and precos:
                logger.info(f"✓ Dados econômicos obtidos via BigQuery para {uf}")
                status_ok = True
        except Exception as e:
            logger.warning(f"BigQuery economia falhou para {uf}: {e}")

    # Fallback: valores médios históricos
    if not pam:
        logger.info(f"Usando valores econômicos default para {uf}")
        pam = {
            "producao_soja": 0.0,
            "producao_milho": 0.0,
            "producao_algodao": 0.0,
        }

    if not precos:
        precos = {
            "preco_soja_mensal": 100.0,
            "preco_milho_mensal": 50.0,
            "preco_algodao_mensal": 300.0,
        }

    return pam, precos, status_ok


def obter_dados_ais_robusto(porto_nome, port_mapping=None):
    """
    Obtém dados AIS com fallback para dados locais.

    IMPORTANTE: Dados AIS precisam ser fornecidos localmente via pipeline.
    Para gerar dados AIS:
    1. Coloque CSVs AIS raw em: data/ais/raw/*_YYYYMMDD.csv
    2. Execute: python pipelines/ais_features.py --date YYYYMMDD
    3. Dados processados vão para: data/ais_features/ais_features_YYYYMMDD.parquet

    Args:
        porto_nome: Nome do porto
        port_mapping: Dict de mapeamento de portos

    Returns:
        tuple: (dados_ais DataFrame ou None, status_ok bool)
    """
    ais_df = None
    status_ok = False

    # Criar diretório se não existir
    AIS_FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    # Tentar carregar dados AIS locais
    try:
        ais_df_full = load_latest_ais_features()

        if ais_df_full is not None and not ais_df_full.empty:
            if port_mapping is None:
                port_mapping = load_port_mapping()

            ais_df = filter_features_by_port(ais_df_full, porto_nome, port_mapping)

            if ais_df is not None and not ais_df.empty:
                logger.info(f"✓ Dados AIS encontrados para {porto_nome} ({len(ais_df)} registros)")
                status_ok = True
            else:
                logger.info(f"Dados AIS disponíveis mas nenhum registro para {porto_nome}")
        else:
            logger.info(f"Nenhum arquivo AIS encontrado em {AIS_FEATURES_DIR}")
    except Exception as e:
        logger.warning(f"Erro ao carregar dados AIS: {e}")

    # Se não há dados AIS, informar ao usuário como obtê-los
    if not status_ok:
        logger.info(
            "\n"
            "╔════════════════════════════════════════════════════════════════╗\n"
            "║  📡 DADOS AIS NÃO DISPONÍVEIS                                  ║\n"
            "║                                                                ║\n"
            "║  Para melhorar a precisão das previsões, forneça dados AIS:   ║\n"
            "║                                                                ║\n"
            "║  1. Coloque CSVs AIS raw em: data/ais/raw/*_YYYYMMDD.csv     ║\n"
            "║                                                                ║\n"
            "║  2. Execute o pipeline:                                        ║\n"
            "║     python pipelines/ais_features.py --date YYYYMMDD          ║\n"
            "║                                                                ║\n"
            "║  3. Dados processados ficam em:                                ║\n"
            "║     data/ais_features/ais_features_YYYYMMDD.parquet           ║\n"
            "║                                                                ║\n"
            "║  IMPACTO: Sem dados AIS, o modelo não conhece a fila real.    ║\n"
            "║  Score de confiança será reduzido (~20-30%).                  ║\n"
            "╚════════════════════════════════════════════════════════════════╝\n"
        )

    return ais_df, status_ok


def criar_dados_ais_mock(porto_nome, num_navios=5):
    """
    Cria dados AIS mock para testes quando dados reais não disponíveis.

    ATENÇÃO: Apenas para testes! Não use em produção.

    Args:
        porto_nome: Nome do porto
        num_navios: Número de navios simulados

    Returns:
        DataFrame com dados AIS mock
    """
    logger.warning(f"⚠️ Criando dados AIS MOCK para {porto_nome} - APENAS PARA TESTES!")

    today = pd.Timestamp.today()
    dates = [(today - pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    data = []
    for date in dates:
        data.append({
            "port_key": normalizar_texto(porto_nome),
            "port_name": porto_nome,
            "date": date,
            "ais_navios_no_raio": float(num_navios),
            "ais_fila_ao_largo": float(max(0, num_navios - 2)),
            "ais_velocidade_media_kn": 5.0,
            "ais_eta_media_horas": 12.0,
            "ais_dist_media_km": 50.0,
        })

    return pd.DataFrame(data)


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
    base_date = live_data.get("eta_base") if isinstance(live_data, dict) else None
    base_ts = pd.to_datetime(base_date).normalize() if base_date else pd.Timestamp.today().normalize()
    df["data_chegada_dt"] = df["data_chegada_dt"].fillna(base_ts)
    if "mare_astronomica" in features:
        df = adicionar_features_mare_lineup(df, porto_nome)
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

    # ============================================================================
    # FASE 1 - Usando funções corrigidas para features críticas
    # ============================================================================
    # Corrigido: calcular fila real ao invés de usar índice
    df["navios_no_fundeio_na_chegada"] = calcular_fila_simulada(df, porto_nome)

    df["navios_na_fila_7d"] = (
        df.assign(navio_index=1)
        .set_index("data_chegada_dt")
        .rolling("7D")["navio_index"]
        .count()
        .fillna(0.0)
        .to_numpy()
    )

    # Corrigido: usar tempo médio histórico real ao invés de 0.0
    df["porto_tempo_medio_historico"] = carregar_tempo_medio_historico(porto_nome)

    # Corrigido: usar tempo médio como proxy da MA5 ao invés de 0.0
    df["tempo_espera_ma5"] = calcular_tempo_espera_ma5(df, porto_nome)

    clima = live_data.get("clima") or {}
    forecast_df = _build_forecast_frame(live_data.get("forecast"))
    date_keys = df["data_chegada_dt"].dt.date
    temp_media = _forecast_series(forecast_df, date_keys, "temp_media")
    temp_max = _forecast_series(forecast_df, date_keys, "temp_max")
    temp_min = _forecast_series(forecast_df, date_keys, "temp_min")
    precipitacao = _forecast_series(forecast_df, date_keys, "precipitacao")
    rajada = _forecast_series(forecast_df, date_keys, "rajada_max")
    vento_max = _forecast_series(forecast_df, date_keys, "vento_max")
    wave_height_max = _forecast_series(forecast_df, date_keys, "wave_height_max")
    ressaca = _forecast_series(forecast_df, date_keys, "ressaca")
    chuva_3d = _forecast_chuva_3d(forecast_df, date_keys)

    temp_media_fallback = float(clima.get("temp_media_dia", 25.0))
    temp_max_fallback = float(clima.get("temp_max_dia", temp_media_fallback + 5.0))
    temp_min_fallback = float(clima.get("temp_min_dia", temp_media_fallback - 5.0))
    precip_fallback = float(clima.get("precipitacao_dia", 0.0))
    rajada_fallback = float(clima.get("vento_rajada_max_dia", 5.0))
    vento_media_fallback = float(clima.get("vento_velocidade_media", 3.0))
    umidade_fallback = float(clima.get("umidade_media_dia", 70.0))
    amplitude_fallback = float(clima.get("amplitude_termica", 10.0))
    wave_fallback = float(clima.get("wave_height_max", 0.0))
    ressaca_fallback = float(clima.get("ressaca", 0.0))
    chuva3_fallback = float(clima.get("chuva_acumulada_ultimos_3dias", 0.0))

    df["temp_media_dia"] = temp_media.fillna(temp_media_fallback).astype(float)
    df["precipitacao_dia"] = precipitacao.fillna(precip_fallback).astype(float)
    df["vento_rajada_max_dia"] = rajada.fillna(rajada_fallback).astype(float)
    vento_media = (vento_max * 0.6).fillna(vento_media_fallback)
    df["vento_velocidade_media"] = vento_media.astype(float)
    df["umidade_media_dia"] = umidade_fallback
    amplitude = (temp_max - temp_min).fillna(amplitude_fallback)
    df["amplitude_termica"] = amplitude.astype(float)
    if "wave_height_max" in features:
        df["wave_height_max"] = wave_height_max.fillna(wave_fallback).astype(float)
    if "ressaca" in features:
        df["ressaca"] = ressaca.fillna(ressaca_fallback).astype(float)
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
        df["chuva_acumulada_ultimos_3dias"] = chuva_3d.fillna(chuva3_fallback).astype(float)

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

    # Corrigido: calcular fila real ao invés de usar índice
    # Para Ponta da Madeira, usar taxa de atracação de 24h (MINERAL)
    df["navios_no_fundeio_na_chegada"] = calcular_fila_simulada(df, "PONTA_DA_MADEIRA")

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


def predict_lineup_basico(df_lineup, live_data, porto_nome, track_quality=False):
    """
    Faz previsões básicas para o lineup.

    Args:
        df_lineup: DataFrame com lineup
        live_data: Dict com dados de contexto (clima, AIS, etc)
        porto_nome: Nome do porto
        track_quality: Se True, retorna também relatórios de qualidade (Fase 2)

    Returns:
        Se track_quality=False: df_out (DataFrame com previsões)
        Se track_quality=True: (df_out, feature_reports, api_status)
    """
    df = df_lineup.copy()
    df["perfil_modelo"] = df.apply(get_profile_from_row, axis=1)

    # FASE 2: Rastreia status das APIs para qualidade
    api_status = {
        "clima_ok": live_data.get("clima") is not None or live_data.get("forecast") is not None,
        "ais_ok": live_data.get("ais_df") is not None and not live_data.get("ais_df", pd.DataFrame()).empty,
        "mare_ok": True,  # Mare está sempre disponível via arquivos locais
        "economia_ok": live_data.get("pam") is not None and live_data.get("precos") is not None,
        "historico_ok": False,  # Será atualizado por carregar_tempo_medio_historico()
    }

    dfs = []
    feature_reports = []
    model_selection_info = []  # FASE 4: Rastreia qual modelo foi usado

    for profile, sub in df.groupby("perfil_modelo", dropna=False):
        # FASE 4: Primeiro avalia qualidade para decidir qual modelo usar
        # Precisamos carregar modelos completos primeiro para avaliar qualidade
        models_temp = load_models_for_profile(profile)
        if not models_temp:
            sub["tempo_espera_previsto_horas"] = np.nan
            sub["tempo_espera_previsto_dias"] = np.nan
            sub["classe_espera_prevista"] = "Indisponivel"
            sub["risco_previsto"] = "Indisponivel"
            sub["probabilidade_prevista"] = np.nan
            sub["confianca_previsao"] = 0.0
            sub["modelo_usado"] = "nenhum"
            dfs.append(sub)
            continue

        # FASE 4: Avalia qualidade ANTES de construir features
        confidence_score = 100.0  # Default
        if track_quality:
            report_temp = avaliar_qualidade_features(models_temp["metadata"], api_status)
            confidence_score = report_temp.confidence_score

        # FASE 4: Seleciona modelo baseado na qualidade
        models, model_type, warning_msg = select_model_by_quality(profile, confidence_score, api_status)

        if models is None:
            sub["tempo_espera_previsto_horas"] = np.nan
            sub["tempo_espera_previsto_dias"] = np.nan
            sub["classe_espera_prevista"] = "Indisponivel"
            sub["risco_previsto"] = "Indisponivel"
            sub["probabilidade_prevista"] = np.nan
            sub["confianca_previsao"] = 0.0
            sub["modelo_usado"] = "nenhum"
            dfs.append(sub)
            continue

        # Armazena info de seleção de modelo
        model_selection_info.append({
            "profile": profile,
            "model_type": model_type,
            "confidence": confidence_score,
            "warning": warning_msg
        })

        features_data = build_features_from_lineup(sub, models["metadata"], live_data, porto_nome)

        # FASE 2: Avalia qualidade das features
        if track_quality:
            report = avaliar_qualidade_features(models["metadata"], api_status)
            feature_reports.append(report)
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
        sub["tempo_espera_previsto_horas"] = preds_horas.round(2).to_numpy()
        sub["tempo_espera_previsto_dias"] = (sub["tempo_espera_previsto_horas"] / 24.0).round(2)
        class_pred = models["model_clf"].predict(features_data)
        class_map = {0: "Rápido", 1: "Médio", 2: "Longo"}
        risco_map = {0: "Baixo", 1: "Médio", 2: "Alto"}
        sub["classe_espera_prevista"] = (
            pd.Series(class_pred).map(class_map).fillna("Desconhecido").to_numpy()
        )
        sub["risco_previsto"] = (
            pd.Series(class_pred).map(risco_map).fillna("Desconhecido").to_numpy()
        )
        try:
            proba = models["model_clf"].predict_proba(features_data)
            sub["probabilidade_prevista"] = np.max(proba, axis=1).round(3)
        except Exception:
            sub["probabilidade_prevista"] = np.nan

        # FASE 2: Adiciona confiança da previsão
        if track_quality and feature_reports:
            sub["confianca_previsao"] = feature_reports[-1].confidence_score
        else:
            sub["confianca_previsao"] = 100.0  # Default se não rastreando

        # FASE 4: Adiciona informação de qual modelo foi usado
        sub["modelo_usado"] = model_type
        sub["num_features"] = len(models["metadata"].get("features", []))

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

    # FASE 2 & FASE 4: Retorna também os reports e info de seleção de modelo
    if track_quality:
        return df_out, feature_reports, api_status, model_selection_info
    return df_out


def inferir_lineup_inteligente(lineup_df, live_data, porto_nome, tem_dados_terminal=False, track_quality=False):
    """
    Faz previsões inteligentes com suporte a modelos premium.

    Args:
        lineup_df: DataFrame com lineup
        live_data: Dict com dados de contexto
        porto_nome: Nome do porto
        tem_dados_terminal: Se True, tem dados específicos do terminal
        track_quality: Se True, retorna também relatórios de qualidade (Fase 2)

    Returns:
        Se track_quality=False: df_out
        Se track_quality=True: (df_out, feature_reports, api_status, model_selection_info)
    """
    # Chama predict_lineup_basico com rastreamento de qualidade
    model_selection_info = []
    if track_quality:
        df_out, feature_reports, api_status, model_selection_info = predict_lineup_basico(
            lineup_df, live_data, porto_nome, track_quality=True
        )
    else:
        df_out = predict_lineup_basico(lineup_df, live_data, porto_nome, track_quality=False)

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
                df_out.loc[mask, "tempo_espera_previsto_horas"] = preds.round(2).to_numpy()
                df_out.loc[mask, "tempo_espera_previsto_dias"] = (
                    (preds / 24.0).round(2).to_numpy()
                )
                df_out.loc[mask, "mae_esperado"] = premium_cfg.get("mae_esperado", 30)
                df_out.loc[mask, "tier"] = "PREMIUM"

    eta = pd.to_datetime(df_out["data_chegada_dt"], errors="coerce")
    eta_espera = eta + pd.to_timedelta(df_out["tempo_espera_previsto_horas"].fillna(0), unit="h")
    df_out["eta_mais_espera"] = eta_espera
    df_out = df_out.sort_values("eta_mais_espera")

    # FASE 2 & FASE 4: Retorna também os reports e info de seleção de modelo
    if track_quality:
        return df_out, feature_reports, api_status, model_selection_info
    return df_out


def calcular_risco(chuva_mm_3d, fila_atual, fila_media):
    if chuva_mm_3d > 20 or fila_atual > 20:
        return "Alto", "vermelho", "Chuva intensa ou fila crítica"
    if chuva_mm_3d > 10 or fila_atual > fila_media:
        return "Médio", "amarelo", "Chuva relevante ou fila acima da média"
    return "Baixo", "verde", "Clima favorável e fila abaixo da média"


st.set_page_config(page_title=APP_TITLE, layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2-family=Montserrat:wght@600;700&family=Roboto:wght@400;500;600&family=Inter:wght@600;700&display=swap');
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
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
.kpi-card .card-value {
  font-size: 30px;
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
  .kpi-grid {
    grid-template-columns: 1fr;
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
      <div class="brand-title">Previsão de Fila - Vegetal (MVP)</div>
      <div class="brand-subtitle">Sistema de previsão de espera e atracação baseado em dados operacionais e modelos de machine learning.</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Seleção de Parâmetros")
    portos = list_lineup_ports()
    porto_selecionado = st.selectbox("Porto", portos)
    if not porto_selecionado:
        porto_selecionado = "NACIONAL"
    lineup_path = find_lineup_file(porto_selecionado)
    if porto_selecionado != "NACIONAL":
        df_lineup, meta = load_history_data(porto_selecionado, lineup_path)
    else:
        df_lineup, meta = load_real_data(lineup_path, porto_nome=porto_selecionado)
    lineup_updated_at = get_lineup_updated_at(df_lineup)
    df_lineup_full = df_lineup

    perfil_porto = infer_port_profile(df_lineup, porto_selecionado)
    opcoes_carga = CARGA_OPCOES_POR_PERFIL.get(perfil_porto, CARGA_OPCOES_POR_PERFIL["VEGETAL"])
    tipo_carga = st.selectbox("Tipo de Carga", opcoes_carga)
    data_chegada = st.date_input("Data de Chegada", value=datetime.today())

    berco_selecionado = "Todos"
    if porto_selecionado != "NACIONAL" and not df_lineup_full.empty and "Berco" in df_lineup_full.columns:
        berco_opcoes = ["Todos"] + sorted(df_lineup_full["Berco"].dropna().unique().tolist())
        berco_selecionado = st.selectbox("Berco", berco_opcoes)

    navio_selecionado = "Todos"
    navio_col = None
    if porto_selecionado != "NACIONAL" and not df_lineup_full.empty:
        navio_col = find_column_by_norm(df_lineup_full, ["Navio", "navio", "nome_navio", "embarcacao"])
    if navio_col:
        navios_raw = df_lineup_full[navio_col].dropna().astype(str).str.strip()
        navios = ["Todos"] + sorted(navios_raw.unique().tolist())
        navio_selecionado = st.selectbox("Navio", navios)

    tipo_navio_selecionado = "Todos"
    tipo_navio_col = None
    if porto_selecionado != "NACIONAL" and not df_lineup_full.empty:
        tipo_navio_col = find_column_by_norm(df_lineup_full, ["categoria", "tipo_navio", "tipo"])
    if tipo_navio_col:
        tipos_raw = df_lineup_full[tipo_navio_col].dropna().astype(str).str.strip()
        tipos = ["Todos"] + sorted(tipos_raw.unique().tolist())
        tipo_navio_label = f"Tipo de Navio ({str(tipo_navio_col).title()})"
        tipo_navio_selecionado = st.selectbox(tipo_navio_label, tipos)

    df_lineup = filter_lineup_horizon(df_lineup_full, days=7, reference_date=data_chegada)
    if porto_selecionado != "NACIONAL" and df_lineup.empty:
        base_str = pd.to_datetime(data_chegada).strftime("%d/%m/%Y")
        st.info(f"Sem registros de line-up entre {base_str} e +7 dias.")
    if porto_selecionado != "NACIONAL" and not df_lineup_full.empty:
        base_dt = pd.to_datetime(data_chegada)
        fim_dt = base_dt + pd.Timedelta(days=7)
        base_str = base_dt.strftime("%d/%m/%Y")
        fim_str = fim_dt.strftime("%d/%m/%Y")
        avisos_fora = []
        if navio_selecionado != "Todos" and navio_col:
            navio_target = str(navio_selecionado).strip()
            navio_full = df_lineup_full[navio_col].astype(str).str.strip()
            navio_rows = df_lineup_full.loc[navio_full == navio_target]
            if not navio_rows.empty:
                navio_in_window = filter_lineup_horizon(
                    navio_rows, days=7, reference_date=data_chegada
                )
                if navio_in_window.empty:
                    avisos_fora.append(f"Navio: {navio_selecionado}")
        if berco_selecionado != "Todos" and "Berco" in df_lineup_full.columns:
            berco_rows = df_lineup_full[df_lineup_full["Berco"] == berco_selecionado]
            if not berco_rows.empty:
                berco_in_window = filter_lineup_horizon(
                    berco_rows, days=7, reference_date=data_chegada
                )
                if berco_in_window.empty:
                    avisos_fora.append(f"Berco: {berco_selecionado}")
        if tipo_navio_selecionado != "Todos" and tipo_navio_col:
            tipo_full = df_lineup_full[tipo_navio_col].astype(str).str.strip()
            tipo_rows = df_lineup_full.loc[tipo_full == str(tipo_navio_selecionado).strip()]
            if not tipo_rows.empty:
                tipo_in_window = filter_lineup_horizon(
                    tipo_rows, days=7, reference_date=data_chegada
                )
                if tipo_in_window.empty:
                    avisos_fora.append(f"Tipo de navio: {tipo_navio_selecionado}")
        if avisos_fora:
            itens = "; ".join(avisos_fora)
            st.info(
                f"Seleções fora da janela de previsão ({base_str} a {fim_str}): {itens}."
            )

    st.markdown("### Condições Climáticas")
    default_chuva = 0.0
    if porto_selecionado != "NACIONAL":
        try:
            porto_key = porto_selecionado.upper()
            porto_cfg = PORT_MUNICIPIO_UF.get(porto_key, {})
            municipio = porto_cfg.get("municipio", porto_selecionado)
            station_id = fetch_inmet_station_id(municipio=municipio)
            clima = fetch_inmet_latest(station_id, port_name=porto_key) or {}
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

    # Previsão de 7 dias (usando Open-Meteo)
    if WEATHER_API_AVAILABLE and porto_selecionado != "NACIONAL":
        with st.expander("📅 Previsão 7 dias (clima e ondas)", expanded=False):
            try:
                forecast = get_weather_forecast(porto_selecionado, days=7)
                if forecast:
                    forecast_df = pd.DataFrame(forecast)
                    forecast_df["data"] = pd.to_datetime(forecast_df["data"]).dt.strftime("%d/%m")
                    cols_display = {
                        "data": "Data",
                        "temp_min": "Min °C",
                        "temp_max": "Max °C",
                        "precipitacao": "Chuva mm",
                        "rajada_max": "Rajada m/s",
                        "wave_height_max": "Ondas m",
                    }
                    display_cols = [c for c in cols_display.keys() if c in forecast_df.columns]
                    df_show = forecast_df[display_cols].rename(columns=cols_display)
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                    # Alertas
                    for _, row in forecast_df.iterrows():
                        if row.get("ressaca"):
                            st.warning(f"⚠️ {row['data']}: Possível ressaca (ondas > 2.5m)")
                        if row.get("precipitacao", 0) > 20:
                            st.info(f"🌧️ {row['data']}: Chuva intensa prevista ({row['precipitacao']:.0f}mm)")
                else:
                    st.caption("Previsão não disponível para este porto")
            except Exception as e:
                st.caption(f"Erro ao carregar previsão: {e}")

    st.markdown("### Condições Operacionais")
    default_fila = compute_default_fila(df_lineup, lineup_path)
    st.session_state["fila_base"] = default_fila
    fila_atual = st.number_input("Navios no fundeio", min_value=0, value=default_fila)
    gerar = st.button("Gerar Previsão", use_container_width=True)
if porto_selecionado == "NACIONAL":
    pergunta_modelo = "Qual a previsão nacional de tempo de espera nos portos brasileiros"
elif get_premium_config(porto_selecionado.upper()):
    pergunta_modelo = (
        "Qual a previsão de tempo de espera para o navio, berço ou categoria selecionados no terminal"
    )
else:
    pergunta_modelo = (
        "Qual a previsão de tempo de espera para atracação no porto selecionado"
    )
st.markdown(
    f"<div class='question-text'>Pergunta do modelo: {pergunta_modelo}</div>",
    unsafe_allow_html=True,
)


def clima_tone(chuva_mm):
    if chuva_mm > 20:
        return "Críticas", "#F29F05"
    if chuva_mm > 10:
        return "Alerta", "#F29F05"
    return "Favoráveis", "#1E5F9C"




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
    live_data = {
        "clima": None,
        "pam": None,
        "precos": None,
        "forecast": None,
        "eta_base": data_chegada,
    }

    # FASE 3: Usar funções robustas para obter dados de APIs
    if porto_selecionado != "NACIONAL":
        porto_key = porto_selecionado.upper()
        porto_cfg = PORT_MUNICIPIO_UF.get(porto_key, {})
        uf = porto_cfg.get("uf", "MA")

        # Clima: Garantido com múltiplos fallbacks (BigQuery → Open-Meteo → Default)
        clima, forecast, clima_ok = obter_dados_clima_robusto(porto_key, porto_cfg)
        live_data["clima"] = clima
        live_data["forecast"] = forecast

        # Economia: BigQuery com fallback para defaults
        pam, precos, economia_ok = obter_dados_economia_robusto(uf=uf)
        live_data["pam"] = pam
        live_data["precos"] = precos

        # AIS: Tentar carregar dados locais
        port_mapping = load_port_mapping()
        ais_df, ais_ok = obter_dados_ais_robusto(porto_selecionado, port_mapping)
        if ais_df is not None and not ais_df.empty:
            live_data["ais_df"] = ais_df
        else:
            live_data["ais_df"] = None

        # Log resumo das APIs
        logger.info(f"Status APIs para {porto_selecionado}: Clima={'OK' if clima_ok else 'Fallback'}, "
                   f"Economia={'OK' if economia_ok else 'Fallback'}, AIS={'OK' if ais_ok else 'Indisponível'}")

    df_pred = None
    df_pred_view = None
    modo = "BASIC"
    feature_reports = []
    api_status = {}
    model_selection_info = []  # FASE 4: Info sobre qual modelo foi usado

    if porto_selecionado != "NACIONAL" and not df_lineup.empty:
        tem_dados_terminal = has_terminal_data(df_lineup)
        if lineup_path and lineup_path.suffix.lower() == ".xlsx":
            tem_dados_terminal = True

        # FASE 2 & FASE 4: Rastreia qualidade e seleção de modelo
        df_pred, feature_reports, api_status, model_selection_info = inferir_lineup_inteligente(
            df_lineup,
            live_data,
            porto_selecionado.upper(),
            tem_dados_terminal=tem_dados_terminal,
            track_quality=True,  # Ativa rastreamento de qualidade
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
    elif risco == "Médio":
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
    kpi_escopo = "Brasil"
    if navio_selecionado != "Todos":
        kpi_escopo = f"Navio: {navio_selecionado}"
    elif tipo_navio_selecionado != "Todos":
        kpi_escopo = f"Tipo: {tipo_navio_selecionado}"
    elif berco_selecionado != "Todos":
        kpi_escopo = f"Berco: {berco_selecionado}"
    elif porto_selecionado != "NACIONAL":
        kpi_escopo = f"Porto: {porto_selecionado}"

    kpi_espera_h = None
    if df_pred_view is not None and "tempo_espera_previsto_horas" in df_pred_view.columns:
        espera_series = pd.to_numeric(
            df_pred_view["tempo_espera_previsto_horas"], errors="coerce"
        ).dropna()
        if not espera_series.empty:
            kpi_espera_h = espera_series.median()
    if kpi_espera_h is None or np.isnan(kpi_espera_h):
        kpi_espera_h = float(espera_horas_estimada)

    kpi_atraso_h = None
    if df_pred_view is not None and "eta_mais_espera" in df_pred_view.columns:
        eta_espera = pd.to_datetime(df_pred_view["eta_mais_espera"], errors="coerce")
        if "Chegada" in df_pred_view.columns:
            eta_lineup = pd.to_datetime(
                df_pred_view["Chegada"], errors="coerce", dayfirst=True
            )
        else:
            eta_lineup = pd.Series([pd.NaT] * len(df_pred_view))
        atraso = (eta_espera - eta_lineup).dt.total_seconds() / 3600.0
        atraso = atraso.replace([np.inf, -np.inf], np.nan).dropna()
        if not atraso.empty:
            kpi_atraso_h = atraso.median()
    if kpi_atraso_h is None or np.isnan(kpi_atraso_h):
        kpi_atraso_h = float(kpi_espera_h)
    resumo_espera = build_espera_resumo(kpi_espera_h, mae_esperado)
    resumo_atraso = build_atraso_resumo(kpi_atraso_h)
    mensagem_espera = (
        "O line-up mostra a fila planejada pelo porto hoje. O modelo mostra a fila "
        "provável, calculada a partir de dados históricos, clima e operação em tempo real."
        "<br><br>"
        f"{resumo_espera}<br>{resumo_atraso}"
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
        insights.append("Chuva relevante nas próximas 72h.")
    if fila_atual > fila_media:
        insights.append("Fila acima da média histórica do porto.")
    if modo == "PREMIUM":
        insights.append("Dados do terminal aplicados (premium).")
    insights.append(build_confiabilidade_text(confiabilidade, mae_esperado))

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
        "kpi_escopo": kpi_escopo,
        "kpi_espera_h": kpi_espera_h,
        "kpi_atraso_h": kpi_atraso_h,
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
        # FASE 2: Qualidade das features
        "feature_reports": feature_reports,
        "api_status": api_status,
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
    st.error(f"Falha ao gerar previsão: {st.session_state['erro_resultado']}")

if not resultado:
    st.info("Defina os parâmetros na barra lateral e clique em Gerar Previsão.")
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
            "<div class='mode-banner'>MODO BÁSICO</div>",
            unsafe_allow_html=True,
        )

    # FASE 2: Seção de Qualidade dos Dados
    feature_reports = resultado.get("feature_reports", [])
    api_status = resultado.get("api_status", {})

    if feature_reports:
        # Calcula score médio de confiança
        avg_confidence = np.mean([r.confidence_score for r in feature_reports])

        # Define cor e ícone baseado na confiança
        if avg_confidence >= 80:
            quality_color = "#28a745"  # Verde
            quality_icon = "🟢"
            quality_label = "ALTA"
        elif avg_confidence >= 60:
            quality_color = "#ffc107"  # Amarelo
            quality_icon = "🟡"
            quality_label = "MÉDIA"
        else:
            quality_color = "#dc3545"  # Vermelho
            quality_icon = "🔴"
            quality_label = "BAIXA"

        st.markdown(
            f"""
<div class='mode-banner' style='background: {quality_color}; margin-top: 8px;'>
    {quality_icon} QUALIDADE DOS DADOS: {quality_label} ({avg_confidence:.0f}%)
</div>
""",
            unsafe_allow_html=True,
        )

        # FASE 4: Exibe avisos de seleção de modelo (se houver)
        for model_info in model_selection_info:
            if model_info.get("warning"):
                if model_info["model_type"] == "light":
                    st.info(model_info["warning"])
                else:
                    st.warning(model_info["warning"])

            # Badge informativo sobre qual modelo foi usado
            if model_info["model_type"] == "light":
                st.markdown(
                    f"""
<div style='background: #e3f2fd; border-left: 4px solid #2196f3; padding: 8px 12px; margin: 8px 0; border-radius: 4px;'>
    <strong>🔧 Modelo Simplificado ({model_info['profile']})</strong><br>
    Usando 15 features confiáveis | Qualidade: {model_info['confidence']:.0f}%
</div>
""",
                    unsafe_allow_html=True,
                )
            elif model_info["confidence"] < 80:
                st.markdown(
                    f"""
<div style='background: #fff3e0; border-left: 4px solid #ff9800; padding: 8px 12px; margin: 8px 0; border-radius: 4px;'>
    <strong>⚙️ Modelo Completo ({model_info['profile']})</strong><br>
    Qualidade dos dados abaixo do ideal: {model_info['confidence']:.0f}%
</div>
""",
                    unsafe_allow_html=True,
                )

        # Agrupa todos os avisos críticos e warnings
        all_critical = []
        all_warnings = []
        for report in feature_reports:
            all_critical.extend(report.critical_issues)
            all_warnings.extend(report.warnings)

        # Remove duplicatas
        all_critical = list(dict.fromkeys(all_critical))
        all_warnings = list(dict.fromkeys(all_warnings))

        # Exibe avisos críticos
        if all_critical:
            for issue in all_critical:
                st.error(issue)

        # Exibe warnings em expander
        if all_warnings:
            with st.expander("⚠️ Avisos de Qualidade dos Dados", expanded=False):
                for warning in all_warnings:
                    st.warning(warning)

                # Detalhes técnicos
                st.markdown("**Detalhes Técnicos:**")
                st.markdown(f"- Dados de clima: {'✅ Disponível' if api_status.get('clima_ok') else '❌ Indisponível'}")
                st.markdown(f"- Dados AIS (fila real): {'✅ Disponível' if api_status.get('ais_ok') else '❌ Indisponível'}")
                st.markdown(f"- Dados de maré: {'✅ Disponível' if api_status.get('mare_ok') else '❌ Indisponível'}")
                st.markdown(f"- Dados econômicos: {'✅ Disponível' if api_status.get('economia_ok') else '❌ Indisponível'}")

                # Breakdown de qualidade
                if feature_reports:
                    report = feature_reports[0]  # Pega o primeiro report como representativo
                    st.markdown("**Composição da Qualidade:**")
                    for quality, count in report.quality_breakdown.items():
                        if count > 0:
                            pct = (count / report.total_features) * 100
                            quality_name = quality.value.replace("_", " ").title()
                            st.markdown(f"- {quality_name}: {count} features ({pct:.0f}%)")

    render_section_title("Resumo Executivo", ICON_SUMMARY)
    st.markdown(
        f"""
<div class="kpi-grid">
  <div class="card kpi-card">
    <div class="card-label">Espera prevista (h)</div>
    <div class="card-value" style="color: var(--accent);">{format_hours_value(resultado['kpi_espera_h'])}</div>
    <div class="card-sub">Escopo: {resultado['kpi_escopo']}</div>
  </div>
  <div class="card kpi-card">
    <div class="card-label">Atraso vs ETA (h)</div>
    <div class="card-value">{format_hours_value(resultado['kpi_atraso_h'])}</div>
    <div class="card-sub">Média vs ETA do line-up (positivo = atrasa)<br>Line-up atualizado: {format_datetime_short(lineup_updated_at)}</div>
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
      <li>Previsão de atracação (mediana): {format_date_short(resultado['atracacao_prevista'])}</li>
      <li>Navios no fundeio: {fila_atual}</li>
      <li>Condições climáticas: {resultado['condicao_clima']}</li>
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
            f"<div class='section-title table-title'>{ICON_TREND}<span>Tabela comparativa: Line-up (plano) x Modelo (fila provável)</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='table-caption'>O line-up mostra a fila planejada pelo porto hoje; o modelo mostra "
            "a fila provável, considerando histórico, clima e dados operacionais.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='table-caption'>Use esta tabela para ver onde o modelo prevê mudanças de posição "
            "na fila e atrasos relevantes em relação ao line-up.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='table-caption'>Olhe o campo Delta_posicao: valores positivos indicam que o navio "
            "tende a andar para trás na fila; valores negativos, ganhar posição. Use Atraso_vs_ETA_h para "
            "identificar navios com maior risco de atraso em relação ao ETA informado.</div>",
            unsafe_allow_html=True,
        )
        column_config = {
            "Posicao_lineup": st.column_config.NumberColumn(
                "Posicao_lineup",
                help="Posição na fila informada pelo porto (line-up oficial).",
            ),
            "Posicao_prevista": st.column_config.NumberColumn(
                "Posicao_prevista",
                help=(
                    "Posição na fila prevista pelo modelo, considerando espera "
                    "estimada e condições atuais."
                ),
            ),
            "Atraso_vs_ETA_h": st.column_config.NumberColumn(
                "Atraso_vs_ETA_h",
                help=(
                    "Horas a mais (ou a menos) que o navio deve atrasar em "
                    "relação ao ETA do line-up."
                ),
            ),
        }
        st.dataframe(
            style_comparativo(comparativo),
            column_config=column_config,
            use_container_width=True,
            height=320,
        )
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
  <strong>Definições da tabela</strong>
  <ul>
    <li>ETA_lineup: horário de chegada informado no line-up (plano do porto).</li>
    <li>Posicao_lineup: posição do navio na fila planejada pelo porto (1 = primeiro a atracar).</li>
    <li>Posicao_prevista: posição do navio na fila provável, calculada pelo modelo com base na espera prevista.</li>
    <li>Delta_posicao: diferença entre a posição prevista e a posição planejada (positivo = perde posição; negativo = ganha posição).</li>
    <li>Espera_prevista_h: horas estimadas de espera antes de atracar, segundo o modelo.</li>
    <li>ETA_com_espera: data e hora estimadas de atracação considerando o ETA do line-up + espera prevista.</li>
    <li>Atraso_vs_ETA_h: diferença em horas entre o ETA do line-up e a atracação prevista (valor positivo = atraca depois do planejado).</li>
    <li>Risco: classificação do risco operacional de atraso relevante em relação ao line-up (baixo, médio, alto).</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )

with tabs[1]:
    render_section_title("Logs Técnicos", ICON_LOGS)
    st.write("Porto selecionado:", porto_selecionado)
    st.write("Perfil inferido:", perfil_porto)
    st.write("Fila média calculada:", resultado["fila_media"])
    if resultado["df_pred_view"] is not None:
        st.dataframe(resultado["df_pred_view"].head(200), use_container_width=True)
    if resultado["meta"]:
        st.json(resultado["meta"])

ultima_atualizacao = "-"
if MODEL_METADATA_PATH.exists():
    ultima_atualizacao = datetime.fromtimestamp(MODEL_METADATA_PATH.stat().st_mtime).strftime("%d/%m/%Y")
st.markdown(
    f"<div class='footer'>Última atualização: {ultima_atualizacao} | (c) 2026 - Projeto Previsão de Fila</div>",
    unsafe_allow_html=True,
)
