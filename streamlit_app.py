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
META_PATH = Path("data_extraction/processed/production/dataset_metadata.json")
MODEL_DIR = Path("models")
MODEL_METADATA_PATH = MODEL_DIR / "vegetal_metadata.json"
PREDICTED_DIR = Path("lineups_previstos")
PREMIUM_REGISTRY_PATH = Path("premium_registry.json")
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

    if META_PATH.exists():
        with META_PATH.open("r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {}

    return df_lineup, meta


@st.cache_data
def list_lineup_files():
    if not LINEUP_DIR.exists():
        return []
    files = list(LINEUP_DIR.glob("*.csv")) + list(LINEUP_DIR.glob("*.xlsx"))
    return sorted(files, key=lambda p: p.name.lower())


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
    if df_lineup is not None and not df_lineup.empty:
        profiles = df_lineup.apply(get_profile_from_row, axis=1)
        if not profiles.empty:
            return profiles.value_counts().idxmax()
    premium_cfg = get_premium_config(porto_nome)
    if premium_cfg and premium_cfg.get("profiles"):
        return premium_cfg["profiles"][0]
    return "VEGETAL"


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

    X = df[features].copy()
    cat_features = [
        "nome_porto",
        "nome_terminal",
        "tipo_navegacao",
        "tipo_carga",
        "natureza_carga",
        "cdmercadoria",
        "stsh4",
    ]
    for col in cat_features:
        if col in X.columns:
            X[col] = X[col].astype("category")
    return X


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
        if models.get("model_ensemble") is not None:
            preds = models["model_ensemble"].predict(features_data)
            preds_horas = pd.Series(preds).apply(lambda v: float(max(0.0, v)))
        else:
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

st.title(APP_TITLE)

tab_geral, tab_porto = st.tabs(["Modelo Geral", "Modelo por Porto"])

with tab_geral:
    lineup_files = list_lineup_files()
    modelos = load_models()
    ultima_atualizacao = None
    if lineup_files:
        ultima_atualizacao = max(f.stat().st_mtime for f in lineup_files)
        ultima_atualizacao = datetime.fromtimestamp(ultima_atualizacao).strftime("%d/%m/%Y %H:%M")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Cobertura do modelo", "Nacional")
    kpi2.metric("Line-ups locais", len(lineup_files))
    kpi3.metric("Ultima atualizacao", ultima_atualizacao or "-")
    kpi4.metric("Fonte", "ANTAQ/INMET/IBGE/IPEA")

    col1 = st.container()
    with col1:
        st.subheader("Entrada")
        chegada = st.date_input("Data Estimada de Chegada (ETA)", value=datetime.today(), key="geral_eta")
        produto = st.selectbox(
            "Tipo de Carga",
            ["Soja em Graos", "Farelo", "Milho", "Acucar", "Trigo", "Cevada", "Malte"],
            key="geral_produto",
        )
        chuva_prevista = st.number_input(
            "Previsao Climatica (Acumulado 72h)",
            min_value=0.0,
            value=0.0,
            key="geral_chuva",
        )
        fila_atual = st.number_input(
            "Navios aguardando no Fundeio",
            min_value=0,
            value=0,
            key="geral_fila",
        )

    st.divider()
    with st.container():
        st.subheader("Resultado da Previsao")
        fila_media = 10
        risco, cor, motivo = calcular_risco(chuva_prevista, fila_atual, fila_media)

        if risco == "Baixo":
            estimativa = "2 a 3 dias"
            tendencia = "Fluxo Normal"
            dias_min, dias_max = 2, 3
        elif risco == "Medio":
            estimativa = "3 a 5 dias"
            tendencia = "Congestionamento Moderado"
            dias_min, dias_max = 3, 5
        else:
            estimativa = "5 a 7 dias"
            tendencia = "Congestionamento Critico"
            dias_min, dias_max = 5, 7

        data_prevista = chegada + pd.Timedelta(days=dias_max)
        st.metric("Estimativa de espera", estimativa)
        st.metric("Atracacao prevista", data_prevista.strftime("%d/%m (%A)"))
        st.metric("Tendencia", tendencia)
        st.metric("Risco", f"{risco} ({motivo})")

        st.caption("Regras: chuva > 10mm ou fila acima da media elevam risco. Chuva > 20mm ou fila > 20 = critico.")

with tab_porto:
    col1 = st.container()
    with col1:
        st.subheader("Entrada")
        lineup_files = list_lineup_files()
        portos = ["(selecione)"] + [f.stem for f in lineup_files]
        porto_selecionado = st.selectbox("Porto", portos, key="porto_select")
        lineup_path = next((p for p in lineup_files if p.stem == porto_selecionado), None)
        df_lineup, meta = load_real_data(lineup_path)
        berco_opcoes = ["Todos"]
        if not df_lineup.empty and "Berco" in df_lineup.columns:
            berco_opcoes += sorted(df_lineup["Berco"].dropna().unique().tolist())
        berco_selecionado = st.selectbox("Porto/Berco", berco_opcoes, key="porto_berco")
        models = load_models()

        chegada = st.date_input("Data Estimada de Chegada (ETA)", value=datetime.today(), key="porto_eta")
        perfil_porto = infer_port_profile(df_lineup, porto_selecionado)
        opcoes_carga = CARGA_OPCOES_POR_PERFIL.get(perfil_porto, CARGA_OPCOES_POR_PERFIL["VEGETAL"])
        produto = st.selectbox(
            "Tipo de Carga",
            opcoes_carga,
            key="porto_produto",
        )

        default_chuva = 0.0
        default_fila = int(df_lineup.shape[0]) if not df_lineup.empty else 0
        if porto_selecionado != "(selecione)":
            try:
                porto_key = porto_selecionado.upper()
                porto_cfg = PORT_MUNICIPIO_UF.get(porto_key, {})
                municipio = porto_cfg.get("municipio", porto_selecionado)
                station_id = fetch_inmet_station_id(municipio=municipio)
                clima = fetch_inmet_latest(station_id) or {}
                default_chuva = float(clima.get("chuva_acumulada_ultimos_3dias", 0.0))
            except Exception:
                default_chuva = 0.0

        chuva_prevista = float(default_chuva)
        st.metric("Previsao Climatica (Acumulado 72h)", f"{chuva_prevista:.1f} mm")
        fila_atual = st.number_input(
            "Navios aguardando no Fundeio",
            min_value=0,
            value=default_fila,
            key="porto_fila",
        )

    st.divider()
    with st.container():
        st.subheader("Resultado da Previsao")
        fila_media = max(int(df_lineup.shape[0] / 2), 10) if not df_lineup.empty else 10
        risco, cor, motivo = calcular_risco(chuva_prevista, fila_atual, fila_media)

        if risco == "Baixo":
            estimativa = "2 a 3 dias"
            tendencia = "Fluxo Normal"
            dias_min, dias_max = 2, 3
        elif risco == "Medio":
            estimativa = "3 a 5 dias"
            tendencia = "Congestionamento Moderado"
            dias_min, dias_max = 3, 5
        else:
            estimativa = "5 a 7 dias"
            tendencia = "Congestionamento Critico"
            dias_min, dias_max = 5, 7

        data_prevista = chegada + pd.Timedelta(days=dias_max)
        st.metric("Estimativa de espera", estimativa)
        st.metric("Atracacao prevista", data_prevista.strftime("%d/%m (%A)"))
        st.metric("Tendencia", tendencia)
        st.metric("Risco", f"{risco} ({motivo})")

        st.caption("Regras: chuva > 10mm ou fila acima da media elevam risco. Chuva > 20mm ou fila > 20 = critico.")

    st.divider()

    st.subheader("Line-up publico (se disponivel)")
    if porto_selecionado == "(selecione)":
        st.info("Selecione um porto para carregar o line-up.")
    elif df_lineup.empty:
        st.info("Aguardando atualizacao do line-up oficial... (Use o simulador manual acima)")
    else:
        live_data = {"clima": None, "pam": None, "precos": None}
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

        tem_dados_terminal = has_terminal_data(df_lineup)
        if lineup_path and lineup_path.suffix.lower() == ".xlsx":
            tem_dados_terminal = True
        df_lineup = inferir_lineup_inteligente(
            df_lineup,
            live_data,
            porto_selecionado.upper(),
            tem_dados_terminal=tem_dados_terminal,
        )
        cliente_e_premium = (
            "tier" in df_lineup.columns and df_lineup["tier"].eq("PREMIUM").any()
        )
        if cliente_e_premium:
            st.info("MODO PREMIUM - Precisao aprimorada com dados do terminal")
        else:
            st.info("MODO BASICO - Dados publicos ANTAQ + Clima")
        st.caption("Variaveis ao vivo carregadas de INMET/IBGE/IPEA (quando disponiveis).")
        PREDICTED_DIR.mkdir(parents=True, exist_ok=True)
        data_tag = datetime.today().strftime("%Y%m%d")
        output_path = PREDICTED_DIR / f"lineup_previsto_{porto_selecionado}_{data_tag}.csv"
        df_lineup.to_csv(output_path, index=False)
        if berco_selecionado != "Todos" and "Berco" in df_lineup.columns:
            df_lineup = df_lineup[df_lineup["Berco"] == berco_selecionado]
        st.dataframe(df_lineup, use_container_width=True)

    if meta:
        ops = meta.get("total_registros") or meta.get("n_registros")
        acc = meta.get("auc_macro") or meta.get("acuracia_ref")
        if ops or acc:
            texto = "Modelo calibrado"
            if ops:
                texto += f" com {ops} operacoes reais"
            if acc:
                texto += f" (Acuracia ref: {acc})"
            st.caption(texto)
