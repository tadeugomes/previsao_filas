import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from google.cloud import bigquery
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

from plano_1 import EnsembleRegressor

TERMINAL_FILE = Path("lineups/Ponta_da_Madeira.xlsx")
OUTPUT_DIR = Path("models")
TERMINAL_LIKE = "ponta da madeira"
MINERAL_CODES = [
    "2601",  # minerio de ferro
    "2606",  # bauxita
    "2602",  # manganes
    "2501",  # sal
    "2523",  # cimento/clinker
    "2603",  # cobre
    "2510",  # fosfatos naturais
]


def normalize_columns(df):
    def norm(text):
        text = unicodedata.normalize("NFKD", str(text))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^A-Za-z0-9]+", "_", text)
        return text.strip("_").lower()

    df = df.copy()
    df.columns = [norm(c) for c in df.columns]
    return df


def load_terminal_data(path):
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    df = pd.read_excel(path)
    df = normalize_columns(df)
    rename_map = {
        "pier": "pier",
        "dwt": "dwt",
        "produtos": "produto",
        "produto": "produto",
        "tipo": "tipo",
        "chegada": "chegada",
        "atracacao": "atracacao",
        "inicio": "inicio",
        "termino": "termino",
        "desatracacao": "desatracacao",
        "tx_comercial": "tx_comercial",
        "tx_efetiva": "tx_efetiva",
        "laytime": "laytime",
        "incoterm": "incoterm",
        "ano": "ano",
        "mes": "mes",
    }
    df = df.rename(columns=rename_map)
    for col in ["chegada", "atracacao", "inicio", "termino", "desatracacao"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    if "ano" in df.columns:
        df = df[df["ano"].between(2020, 2022)]
    else:
        df = df[df["atracacao"].dt.year.between(2020, 2022)]

    df["tempo_espera_horas"] = (
        df["atracacao"] - df["chegada"]
    ).dt.total_seconds() / 3600.0
    df["tempo_espera_horas"] = df["tempo_espera_horas"].clip(lower=0, upper=720)
    df = df[df["tempo_espera_horas"].notna()]

    df = df.sort_values(["pier", "atracacao"]).reset_index(drop=True)
    df["prancha_ma5_pier"] = (
        df.groupby("pier")["tx_efetiva"]
        .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
        .fillna(0.0)
    )
    tx_com = pd.to_numeric(df["tx_comercial"], errors="coerce").replace(0, np.nan)
    tx_efe = pd.to_numeric(df["tx_efetiva"], errors="coerce")
    df["gap_prancha_pct"] = ((tx_com - tx_efe) / tx_com).fillna(0.0)
    df["laytime_horas"] = pd.to_numeric(df["laytime"], errors="coerce").fillna(0.0) * 24.0
    df["urgencia_alta"] = (
        (df["laytime_horas"] - df["tempo_espera_horas"]) < 24
    ).astype(int)

    df["mes"] = df["atracacao"].dt.month
    df["dia_ano"] = df["atracacao"].dt.dayofyear
    df["data_atracacao_date"] = df["atracacao"].dt.date
    return df


def extract_antaq_terminal(project_id="antaqdados", min_year=2020, max_year=2025):
    client = bigquery.Client(project=project_id)
    query = f"""
    WITH carga_agregada AS (
        SELECT
            idatracacao,
            ARRAY_AGG(
                cdmercadoria
                ORDER BY SAFE_CAST(REPLACE(REPLACE(vlpesocargabruta, '.', ''), ',', '.') AS FLOAT64) DESC
                LIMIT 1
            )[OFFSET(0)] AS cdmercadoria
        FROM antaqdados.br_antaq_estatistico_aquaviario.carga
        WHERE vlpesocargabruta IS NOT NULL
        GROUP BY idatracacao
    )
    SELECT
        a.idatracacao,
        a.data_chegada,
        a.data_atracacao,
        SAFE_CAST(a.ano AS INT64) AS ano,
        a.porto_atracacao AS nome_porto,
        a.terminal AS nome_terminal,
        a.tipo_de_navegacao_da_atracacao AS tipo_navegacao,
        c.cdmercadoria
    FROM antaqdados.br_antaq_estatistico_aquaviario.atracacao a
    LEFT JOIN carga_agregada c ON a.idatracacao = c.idatracacao
    WHERE
        a.data_chegada IS NOT NULL
        AND a.data_atracacao IS NOT NULL
        AND SAFE_CAST(a.ano AS INT64) BETWEEN {min_year} AND {max_year}
        AND LOWER(a.terminal) LIKE '%{TERMINAL_LIKE}%'
    ORDER BY a.data_chegada
    """
    df = client.query(query).to_dataframe()
    df["cdmercadoria"] = df["cdmercadoria"].astype(str).str[:4]
    df = df[df["cdmercadoria"].isin(MINERAL_CODES)]
    df["data_chegada_dt"] = pd.to_datetime(df["data_chegada"], dayfirst=True, errors="coerce")
    df["data_atracacao_dt"] = pd.to_datetime(df["data_atracacao"], dayfirst=False, errors="coerce")
    df = df[df["data_chegada_dt"].notna() & df["data_atracacao_dt"].notna()]
    df["tempo_espera_horas"] = (
        df["data_atracacao_dt"] - df["data_chegada_dt"]
    ).dt.total_seconds() / 3600.0
    df["tempo_espera_horas"] = df["tempo_espera_horas"].clip(lower=0, upper=720)
    df = df[df["tempo_espera_horas"].notna()]

    df = df.sort_values("data_chegada_dt").reset_index(drop=True)
    arrivals = df["data_chegada_dt"].to_numpy()
    departures = np.sort(df["data_atracacao_dt"].to_numpy())
    fila = np.zeros(len(df), dtype=float)
    for i, t in enumerate(arrivals):
        departures_before = np.searchsorted(departures, t, side="right")
        fila[i] = max(i - departures_before, 0)
    df["navios_no_fundeio_na_chegada"] = fila
    df["mes"] = df["data_atracacao_dt"].dt.month
    df["dia_ano"] = df["data_atracacao_dt"].dt.dayofyear
    df["data_atracacao_date"] = df["data_atracacao_dt"].dt.date
    return df


def build_train_dataset(df_terminal, df_antaq):
    df_antaq_train = df_antaq[df_antaq["ano"].between(2020, 2022)].copy()
    an_day = (
        df_antaq_train.groupby("data_atracacao_date")["navios_no_fundeio_na_chegada"]
        .mean()
        .reset_index()
    )
    df_train = df_terminal.merge(an_day, on="data_atracacao_date", how="left")
    df_train["navios_no_fundeio_na_chegada"] = df_train["navios_no_fundeio_na_chegada"].fillna(0.0)
    return df_train


def build_antaq_dataset(df_antaq, years):
    df = df_antaq[df_antaq["ano"].isin(years)].copy()
    df["pier"] = "DESCONHECIDO"
    df["prancha_ma5_pier"] = 0.0
    df["gap_prancha_pct"] = 0.0
    df["dwt"] = 0.0
    df["laytime_horas"] = 0.0
    df["urgencia_alta"] = 0
    df["incoterm"] = "DESCONHECIDO"
    return df


def prepare_features(df, feature_cols, cat_cols):
    X = df[feature_cols].copy()
    for col in cat_cols:
        if col in X.columns:
            X[col] = X[col].fillna("DESCONHECIDO").astype(str)
    X = X.fillna(0)
    X = pd.get_dummies(X, columns=cat_cols, dummy_na=True)
    return X


def train_models(df_train, df_val, df_test, feature_cols, cat_cols):
    X_train = prepare_features(df_train, feature_cols, cat_cols)
    dummy_columns = X_train.columns.tolist()
    y_train = df_train["tempo_espera_horas"].copy()
    X_val = prepare_features(df_val, feature_cols, cat_cols).reindex(columns=X_train.columns, fill_value=0)
    y_val = df_val["tempo_espera_horas"].copy()
    X_test = prepare_features(df_test, feature_cols, cat_cols).reindex(columns=X_train.columns, fill_value=0)
    y_test = df_test["tempo_espera_horas"].copy()

    lgb_model = LGBMRegressor(
        n_estimators=2000,
        max_depth=8,
        learning_rate=0.02,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbose=-1,
    )
    lgb_model.fit(X_train, np.log1p(y_train))

    xgb_model = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=2000,
        max_depth=10,
        learning_rate=0.02,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        tree_method="hist",
    )
    xgb_model.fit(X_train, y_train)

    def eval_metrics(y_true, pred, label):
        mae = mean_absolute_error(y_true, pred)
        rmse = np.sqrt(mean_squared_error(y_true, pred))
        r2 = r2_score(y_true, pred)
        print(f"{label} -> MAE: {mae:.2f}h | RMSE: {rmse:.2f}h | R2: {r2:.3f}")
        return {"mae": mae, "rmse": rmse, "r2": r2}

    lgb_val = np.expm1(lgb_model.predict(X_val))
    xgb_val = xgb_model.predict(X_val)
    ens_val = (lgb_val + xgb_val) / 2.0
    lgb_test = np.expm1(lgb_model.predict(X_test))
    xgb_test = xgb_model.predict(X_test)
    ens_test = (lgb_test + xgb_test) / 2.0

    metrics = {
        "val_lgb": eval_metrics(y_val, lgb_val, "Validacao LGBM (2023)"),
        "val_xgb": eval_metrics(y_val, xgb_val, "Validacao XGB (2023)"),
        "val_ensemble": eval_metrics(y_val, ens_val, "Validacao Ensemble (2023)"),
        "test_lgb": eval_metrics(y_test, lgb_test, "Teste LGBM (2024-2025)"),
        "test_xgb": eval_metrics(y_test, xgb_test, "Teste XGB (2024-2025)"),
        "test_ensemble": eval_metrics(y_test, ens_test, "Teste Ensemble (2024-2025)"),
    }
    return lgb_model, xgb_model, metrics, dummy_columns


def save_artifacts(lgb_model, xgb_model, feature_cols, metrics, dummy_columns):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ensemble = EnsembleRegressor(lgb_model, xgb_model)
    joblib.dump(ensemble, OUTPUT_DIR / "ponta_da_madeira_ensemble_reg.pkl")
    joblib.dump(lgb_model, OUTPUT_DIR / "ponta_da_madeira_lgb_reg.pkl")
    joblib.dump(xgb_model, OUTPUT_DIR / "ponta_da_madeira_xgb_reg.pkl")
    report = {
        "modelo": "ponta_da_madeira",
        "treino": "2020-2022 (terminal + ANTAQ)",
        "validacao": "2023 (ANTAQ puro)",
        "teste": "2024-2025 (ANTAQ puro)",
        "features": feature_cols,
        "dummy_columns": dummy_columns,
        "metricas": metrics,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    with (OUTPUT_DIR / "ponta_da_madeira_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=True)
    metadata = {
        "profile": "PONTA_DA_MADEIRA",
        "features": feature_cols,
        "dummy_columns": dummy_columns,
        "target": "tempo_espera_horas",
        "trained_at": report["timestamp"],
        "artifacts": {
            "lgb_reg": "ponta_da_madeira_lgb_reg.pkl",
            "xgb_reg": "ponta_da_madeira_xgb_reg.pkl",
            "ensemble_reg": "ponta_da_madeira_ensemble_reg.pkl",
        },
    }
    with (OUTPUT_DIR / "ponta_da_madeira_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=True)


def main():
    print("=" * 70)
    print("MODELO PONTA DA MADEIRA (MINERAL ENRIQUECIDO)")
    print("=" * 70)
    df_terminal = load_terminal_data(TERMINAL_FILE)
    print(f"Terminal (2020-2022): {len(df_terminal):,} registros")
    df_antaq = extract_antaq_terminal()
    print(f"ANTAQ total (2020-2025): {len(df_antaq):,} registros")

    df_train = build_train_dataset(df_terminal, df_antaq)
    df_val = build_antaq_dataset(df_antaq, [2023])
    df_test = build_antaq_dataset(df_antaq, [2024, 2025])

    feature_cols = [
        "pier",
        "prancha_ma5_pier",
        "gap_prancha_pct",
        "dwt",
        "laytime_horas",
        "urgencia_alta",
        "navios_no_fundeio_na_chegada",
        "mes",
        "dia_ano",
        "incoterm",
    ]
    cat_cols = ["pier", "incoterm"]

    lgb_model, xgb_model, metrics, dummy_columns = train_models(
        df_train, df_val, df_test, feature_cols, cat_cols
    )
    save_artifacts(lgb_model, xgb_model, feature_cols, metrics, dummy_columns)
    print("Modelos e relatorio salvos em models/")


if __name__ == "__main__":
    main()
