#!/usr/bin/env python3
"""
Script para treinar modelos light REAIS com dados históricos.

Este script substitui os modelos MOCK por modelos treinados com dados reais
do arquivo lineup_history.parquet.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import pickle
import sys

# Tenta importar LightGBM
try:
    import lightgbm as lgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    DEPENDENCIES_OK = True
except ImportError as e:
    DEPENDENCIES_OK = False
    MISSING_LIB = str(e)

import warnings
warnings.filterwarnings('ignore')

# Features por perfil (conforme análise Fase 4)
FEATURES_LIGHT = {
    "VEGETAL": [
        "navios_no_fundeio_na_chegada",
        "porto_tempo_medio_historico",
        "tempo_espera_ma5",
        "navios_na_fila_7d",
        "nome_porto",
        "nome_terminal",
        "natureza_carga",
        "movimentacao_total_toneladas",
        "mes",
        "periodo_safra",
        "dia_semana",
        "flag_soja",
        "flag_milho",
        "precipitacao_dia",
        "vento_rajada_max_dia",
    ],
    "MINERAL": [
        "navios_no_fundeio_na_chegada",
        "porto_tempo_medio_historico",
        "tempo_espera_ma5",
        "navios_na_fila_7d",
        "nome_porto",
        "nome_terminal",
        "natureza_carga",
        "movimentacao_total_toneladas",
        "mes",
        "dia_semana",
        "precipitacao_dia",
        "vento_rajada_max_dia",
        "temp_media_dia",
        "tipo_navegacao",
        "ais_fila_ao_largo",
    ],
    "FERTILIZANTE": [
        "navios_no_fundeio_na_chegada",
        "porto_tempo_medio_historico",
        "tempo_espera_ma5",
        "navios_na_fila_7d",
        "nome_porto",
        "nome_terminal",
        "natureza_carga",
        "movimentacao_total_toneladas",
        "mes",
        "periodo_safra",
        "dia_semana",
        "precipitacao_dia",
        "vento_rajada_max_dia",
        "tipo_navegacao",
        "dia_do_ano",
    ],
}


def check_dependencies():
    """Verifica se todas as dependências estão instaladas."""
    if not DEPENDENCIES_OK:
        print("❌ ERRO: Dependências faltando!")
        print(f"   {MISSING_LIB}")
        print("\nInstale as dependências:")
        print("  pip install pandas pyarrow lightgbm scikit-learn numpy")
        return False
    return True


def load_historical_data():
    """Carrega dados históricos."""
    parquet_file = Path("lineups_previstos/lineup_history.parquet")

    if not parquet_file.exists():
        print(f"❌ Arquivo não encontrado: {parquet_file}")
        print("\nVerifique se o arquivo existe:")
        print("  ls -lh lineups_previstos/lineup_history.parquet")
        raise FileNotFoundError(f"Arquivo não encontrado: {parquet_file}")

    df = pd.read_parquet(parquet_file)
    print(f"✅ Dados carregados: {len(df):,} registros, {len(df.columns)} colunas")

    return df


def train_light_model(profile, X_train, y_train, X_val, y_val, X_test, y_test):
    """Treina modelo light para um perfil."""
    print(f"\n{'='*60}")
    print(f"Treinando modelo LIGHT REAL: {profile}")
    print(f"{'='*60}")
    print(f"Features: {len(X_train.columns)}")
    print(f"Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    # LightGBM Regressor
    lgb_reg = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    lgb_reg.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        eval_metric="mae",
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)],
    )

    # LightGBM Classifier (classes de tempo: Rápido < 48h, Médio 48-120h, Longo > 120h)
    y_train_class = pd.cut(y_train, bins=[0, 48, 120, 10000], labels=[0, 1, 2])
    y_val_class = pd.cut(y_val, bins=[0, 48, 120, 10000], labels=[0, 1, 2])
    y_test_class = pd.cut(y_test, bins=[0, 48, 120, 10000], labels=[0, 1, 2])

    lgb_clf = lgb.LGBMClassifier(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    lgb_clf.fit(
        X_train,
        y_train_class,
        eval_set=[(X_val, y_val_class)],
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)],
    )

    # Avaliação no conjunto de validação
    y_pred_val = lgb_reg.predict(X_val)
    val_mae = mean_absolute_error(y_val, y_pred_val)
    val_rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
    val_r2 = r2_score(y_val, y_pred_val)

    # Avaliação no conjunto de teste
    y_pred_test = lgb_reg.predict(X_test)
    test_mae = mean_absolute_error(y_test, y_pred_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    test_r2 = r2_score(y_test, y_pred_test)

    print(f"\n📊 Resultados:")
    print(f"   Val  → MAE: {val_mae:.2f}h | RMSE: {val_rmse:.2f}h | R²: {val_r2:.4f}")
    print(f"   Test → MAE: {test_mae:.2f}h | RMSE: {test_rmse:.2f}h | R²: {test_r2:.4f}")

    # Critérios de aceitação
    acceptable = test_mae < 30 and test_r2 > 0.40
    status = "✅ ACEITÁVEL" if acceptable else "⚠️  REVISAR"
    print(f"\n   Status: {status}")

    if not acceptable:
        if test_mae >= 30:
            print(f"   ⚠️  MAE alto: {test_mae:.1f}h (esperado < 30h)")
        if test_r2 <= 0.40:
            print(f"   ⚠️  R² baixo: {test_r2:.3f} (esperado > 0.40)")

    return {
        "lgb_reg": lgb_reg,
        "lgb_clf": lgb_clf,
        "metrics": {
            "val": {"mae": float(val_mae), "rmse": float(val_rmse), "r2": float(val_r2)},
            "test": {"mae": float(test_mae), "rmse": float(test_rmse), "r2": float(test_r2)},
        },
        "acceptable": acceptable,
    }


def save_light_model(profile, models, features, metrics, output_dir="models"):
    """Salva modelo light treinado."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{profile.lower()}_light"

    # Salva modelos
    with open(output_dir / f"{prefix}_lgb_reg.pkl", "wb") as f:
        pickle.dump(models["lgb_reg"], f)

    with open(output_dir / f"{prefix}_lgb_clf.pkl", "wb") as f:
        pickle.dump(models["lgb_clf"], f)

    # Metadata
    metadata = {
        "profile": profile,
        "model_type": "light",
        "is_mock": False,  # MODELO REAL!
        "features": features,
        "target": "tempo_espera_horas",
        "trained_at": datetime.now().isoformat() + "Z",
        "training_info": {
            "total_samples": len(features),
            "features_count": len(features),
            "note": "Modelo treinado com dados reais de lineup_history.parquet"
        },
        "artifacts": {
            "lgb_reg": f"{prefix}_lgb_reg.pkl",
            "lgb_clf": f"{prefix}_lgb_clf.pkl",
        },
        "metrics": metrics,
    }

    with open(output_dir / f"{prefix}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Modelo salvo: models/{prefix}_*")


def main():
    """Função principal."""
    print("="*60)
    print("TREINO DE MODELOS LIGHT REAIS")
    print("="*60)

    # Verifica dependências
    if not check_dependencies():
        return 1

    # Carrega dados
    try:
        df = load_historical_data()
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return 1

    if 'tempo_espera_horas' not in df.columns:
        print("❌ Coluna 'tempo_espera_horas' (target) não encontrada!")
        print(f"\nColunas disponíveis: {list(df.columns)}")
        return 1

    if 'perfil_modelo' not in df.columns:
        print("⚠️  Coluna 'perfil_modelo' não encontrada.")
        print("   Usando todos os dados como VEGETAL por padrão.")
        df['perfil_modelo'] = 'VEGETAL'

    # Treina para cada perfil
    results = {}

    for profile in ["VEGETAL", "MINERAL", "FERTILIZANTE"]:
        print(f"\n{'='*60}")
        print(f"Processando perfil: {profile}")
        print(f"{'='*60}")

        # Filtra dados do perfil
        df_profile = df[df['perfil_modelo'] == profile].copy()

        if len(df_profile) < 100:
            print(f"⚠️  Pulando {profile}: apenas {len(df_profile)} registros (mínimo: 100)")
            continue

        # Seleciona features disponíveis
        features = FEATURES_LIGHT[profile]
        available_features = [f for f in features if f in df_profile.columns]

        print(f"Registros: {len(df_profile):,}")
        print(f"Features disponíveis: {len(available_features)}/15")

        if len(available_features) < 10:
            print(f"⚠️  Pulando {profile}: poucas features ({len(available_features)}/15)")
            print(f"   Disponíveis: {available_features}")
            print(f"   Faltando: {set(features) - set(available_features)}")
            continue

        # Prepara dados
        X = df_profile[available_features]
        y = df_profile["tempo_espera_horas"]

        # Remove linhas com NaN
        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean = X[mask]
        y_clean = y[mask]

        print(f"Após limpeza de NaN: {len(X_clean):,} registros")

        if len(X_clean) < 100:
            print(f"⚠️  Dados insuficientes após limpeza: {len(X_clean)}")
            continue

        # Split train/val/test
        X_train, X_temp, y_train, y_temp = train_test_split(
            X_clean, y_clean, test_size=0.3, random_state=42
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42
        )

        # Treina modelo
        try:
            result = train_light_model(
                profile, X_train, y_train, X_val, y_val, X_test, y_test
            )

            # Salva modelo
            save_light_model(
                profile,
                result,
                available_features,
                result["metrics"]
            )

            results[profile] = result

        except Exception as e:
            print(f"❌ Erro ao treinar modelo {profile}: {e}")
            continue

    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DO TREINO")
    print("="*60)

    if not results:
        print("❌ Nenhum modelo foi treinado!")
        print("\nPossíveis causas:")
        print("  - Dados insuficientes (< 100 registros por perfil)")
        print("  - Features necessárias não disponíveis (< 10/15)")
        print("  - Coluna 'perfil_modelo' ausente ou vazia")
        print("  - Coluna 'tempo_espera_horas' ausente")
        print("\nRecomendação: Mantenha os modelos MOCK até coletar mais dados")
        return 1

    for profile, result in results.items():
        status = "✅" if result["acceptable"] else "⚠️"
        mae = result["metrics"]["test"]["mae"]
        r2 = result["metrics"]["test"]["r2"]
        print(f"{status} {profile:<20} MAE: {mae:.1f}h | R²: {r2:.3f}")

    print("\n✅ Treino concluído!")
    print("\nArquivos criados:")
    for profile in results.keys():
        print(f"  - models/{profile.lower()}_light_lgb_reg.pkl")
        print(f"  - models/{profile.lower()}_light_lgb_clf.pkl")
        print(f"  - models/{profile.lower()}_light_metadata.json")

    print("\nPróximos passos:")
    print("  1. Validar modelos: python3 test_fallback_system.py")
    print("  2. Testar no Streamlit: streamlit run streamlit_app.py")
    print("  3. Comparar previsões MOCK vs REAL")

    # Avisos finais
    unacceptable = [p for p, r in results.items() if not r["acceptable"]]
    if unacceptable:
        print(f"\n⚠️  ATENÇÃO: {len(unacceptable)} modelo(s) com performance abaixo do esperado:")
        for profile in unacceptable:
            print(f"   - {profile}")
        print("\nRecomendação: Coletar mais dados ou ajustar hiperparâmetros")

    return 0


if __name__ == "__main__":
    sys.exit(main())
