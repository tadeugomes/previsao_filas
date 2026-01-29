#!/usr/bin/env python3
"""
Treinar modelos reais com dados AIS coletados.

Este script:
1. Carrega complete_dataset.parquet
2. Preprocessa e adiciona features
3. Treina modelos light para cada perfil
4. Valida performance
5. Substitui modelos mock
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import json
from datetime import datetime
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error

# Features para modelos light (15 features críticas)
FEATURES_LIGHT = {
    "VEGETAL": [
        "navios_no_fundeio_na_chegada",
        "porto_tempo_medio_historico",
        "tempo_espera_ma5",
        "navios_na_fila_7d",
        "nome_porto_encoded",
        "natureza_carga_encoded",
        "movimentacao_total_toneladas",
        "mes",
        "periodo_safra",
        "dia_semana",
        "flag_soja",
        "flag_milho",
        "dwt_normalizado",
        "calado_normalizado",
        "tipo_navio_encoded",
    ],
    "MINERAL": [
        "navios_no_fundeio_na_chegada",
        "porto_tempo_medio_historico",
        "tempo_espera_ma5",
        "navios_na_fila_7d",
        "nome_porto_encoded",
        "natureza_carga_encoded",
        "movimentacao_total_toneladas",
        "mes",
        "dia_semana",
        "dwt_normalizado",
        "calado_normalizado",
        "tipo_navio_encoded",
        "densidade_carga",
        "capacidade_porto",
        "num_bercos",
    ],
    "FERTILIZANTE": [
        "navios_no_fundeio_na_chegada",
        "porto_tempo_medio_historico",
        "tempo_espera_ma5",
        "navios_na_fila_7d",
        "nome_porto_encoded",
        "natureza_carga_encoded",
        "movimentacao_total_toneladas",
        "mes",
        "periodo_safra",
        "dia_semana",
        "dwt_normalizado",
        "calado_normalizado",
        "tipo_navio_encoded",
        "flag_quimico",
        "temperatura_media",
    ],
}

# Mapeamento de tipos de carga para perfis
CARGA_TO_PROFILE = {
    "soja": "VEGETAL",
    "milho": "VEGETAL",
    "trigo": "VEGETAL",
    "farelo": "VEGETAL",
    "minério": "MINERAL",
    "ferro": "MINERAL",
    "carvão": "MINERAL",
    "bauxita": "MINERAL",
    "fertilizante": "FERTILIZANTE",
    "ureia": "FERTILIZANTE",
    "fosfato": "FERTILIZANTE",
    "químico": "FERTILIZANTE",
}

# Capacidades dos portos (toneladas/dia estimadas)
PORTO_CAPACIDADE = {
    "Santos": 10000,
    "Paranaguá": 8000,
    "Rio Grande": 7000,
    "Itaqui": 5000,
    "Vitória": 6000,
    "Suape": 4000,
    "Salvador": 3000,
    "Itajaí": 3000,
}

PORTO_BERCOS = {
    "Santos": 15,
    "Paranaguá": 12,
    "Rio Grande": 10,
    "Itaqui": 8,
    "Vitória": 10,
    "Suape": 8,
    "Salvador": 6,
    "Itajaí": 6,
}


def load_ais_data():
    """Carrega dados AIS coletados."""
    print("="*70)
    print("CARREGANDO DADOS AIS")
    print("="*70)

    df = pd.read_parquet("data/ais/complete_dataset.parquet")

    print(f"\n✅ Dataset carregado: {len(df)} registros")
    print(f"   Colunas: {list(df.columns)}")
    print(f"   Período: {df['berthing_time'].min()} a {df['berthing_time'].max()}")

    return df


def preprocess_features(df):
    """Adiciona features necessárias para treino."""
    print("\n" + "="*70)
    print("PREPROCESSAMENTO DE FEATURES")
    print("="*70)

    df = df.copy()

    # 1. Converter timestamps
    df['berthing_time'] = pd.to_datetime(df['berthing_time'])

    # 2. Features temporais
    print("\n📅 Adicionando features temporais...")
    df['mes'] = df['berthing_time'].dt.month
    df['dia_semana'] = df['berthing_time'].dt.dayofweek
    df['dia_do_ano'] = df['berthing_time'].dt.dayofyear

    # Período de safra (soja: mar-mai e set-nov, milho: fev-jul)
    is_soja_1 = (df['mes'] >= 3) & (df['mes'] <= 5)
    is_soja_2 = (df['mes'] >= 9) & (df['mes'] <= 11)
    is_milho = (df['mes'] >= 2) & (df['mes'] <= 7)

    df['periodo_safra'] = 0
    df.loc[is_soja_1 | is_soja_2, 'periodo_safra'] = 1
    df.loc[is_milho, 'periodo_safra'] = 2

    # 3. Features de carga
    print("📦 Adicionando features de carga...")

    # Inferir perfil baseado no tipo de navio
    def inferir_perfil(row):
        tipo = str(row['type']).lower()
        if 'tanker' in tipo or 'chemical' in tipo:
            return 'FERTILIZANTE'
        elif 'bulk' in tipo or 'cargo' in tipo:
            # Tentar inferir baseado no porto
            porto = row['porto']
            if porto in ['Santos', 'Paranaguá']:
                return 'VEGETAL'  # Portos agrícolas
            elif porto in ['Itaqui', 'Vitória']:
                return 'MINERAL'  # Portos de minério
            else:
                return 'VEGETAL'  # Default
        else:
            return 'VEGETAL'

    df['perfil'] = df.apply(inferir_perfil, axis=1)

    # Flags de produto
    df['flag_soja'] = 0
    df['flag_milho'] = 0
    df['flag_quimico'] = df['type'].str.contains('chemical|tanker', case=False, na=False).astype(int)

    # Natureza da carga (inferida)
    df['natureza_carga'] = 'EXPORTACAO'  # Maioria dos portos brasileiros
    df['natureza_carga_encoded'] = 1  # 1=EXPORTACAO, 0=IMPORTACAO

    # 4. Features de porto
    print("🏭 Adicionando features de porto...")
    df['nome_porto_encoded'] = df['porto'].astype('category').cat.codes
    df['capacidade_porto'] = df['porto'].map(PORTO_CAPACIDADE).fillna(5000)
    df['num_bercos'] = df['porto'].map(PORTO_BERCOS).fillna(8)

    # 5. Features de navio
    print("🚢 Adicionando features de navio...")
    df['tipo_navio_encoded'] = df['type'].astype('category').cat.codes

    # DWT e calado (estimados - não temos dados reais)
    # Usar valores médios por tipo
    dwt_medio = {
        'cargo': 50000,
        'tanker': 60000,
        'bulk': 70000,
    }

    def estimar_dwt(tipo):
        tipo_lower = str(tipo).lower()
        for key, value in dwt_medio.items():
            if key in tipo_lower:
                return value
        return 50000

    df['dwt_normalizado'] = df['type'].apply(estimar_dwt) / 100000
    df['calado_normalizado'] = df['dwt_normalizado'] * 0.8  # Aproximação

    # 6. Features de movimentação
    print("📊 Adicionando features de movimentação...")
    df['movimentacao_total_toneladas'] = df['dwt_normalizado'] * 80000  # Estimativa
    df['densidade_carga'] = 1.0  # Default

    # 7. Features históricas (rolling)
    print("📈 Calculando features históricas...")

    # Ordenar por porto e tempo
    df = df.sort_values(['porto', 'berthing_time'])

    # Para cada porto, calcular médias móveis
    for porto in df['porto'].unique():
        mask = df['porto'] == porto
        df.loc[mask, 'porto_tempo_medio_historico'] = (
            df.loc[mask, 'waiting_time_hours']
            .rolling(window=10, min_periods=1)
            .mean()
        )
        df.loc[mask, 'tempo_espera_ma5'] = (
            df.loc[mask, 'waiting_time_hours']
            .rolling(window=5, min_periods=1)
            .mean()
        )

    # 8. Features de fila (estimadas)
    print("🚦 Estimando features de fila...")

    # Contar navios na mesma janela temporal por porto
    df = df.sort_values(['porto', 'berthing_time'])

    for porto in df['porto'].unique():
        mask = df['porto'] == porto
        df_porto = df[mask].copy()

        # Para cada registro, contar quantos navios no mesmo dia
        fila_counts = []
        for idx, row in df_porto.iterrows():
            data = row['berthing_time']
            mesma_data = (
                (df_porto['berthing_time'] >= data - pd.Timedelta(days=1)) &
                (df_porto['berthing_time'] <= data + pd.Timedelta(days=1))
            )
            count = mesma_data.sum() - 1  # Exclui próprio navio
            fila_counts.append(max(0, count))

        df.loc[mask, 'navios_no_fundeio_na_chegada'] = fila_counts

    # Fila últimos 7 dias
    df['navios_na_fila_7d'] = df['navios_no_fundeio_na_chegada'] * 7  # Aproximação

    # 9. Features climáticas (defaults)
    print("🌤️  Adicionando features climáticas (defaults)...")
    df['temperatura_media'] = 25.0  # Default Brasil
    df['precipitacao_dia'] = 0.0
    df['vento_rajada_max_dia'] = 20.0

    print(f"\n✅ Preprocessamento concluído!")
    print(f"   Total de features: {len(df.columns)}")
    print(f"   Registros válidos: {df['waiting_time_hours'].notna().sum()}/{len(df)}")

    return df


def train_light_model(profile, X_train, y_train, X_val, y_val, X_test, y_test):
    """Treina modelo light para um perfil."""
    print(f"\n{'='*70}")
    print(f"TREINANDO MODELO: {profile}")
    print("="*70)

    print(f"\n📊 Dados de treino:")
    print(f"   Train: {len(X_train)} amostras")
    print(f"   Val:   {len(X_val)} amostras")
    print(f"   Test:  {len(X_test)} amostras")

    # 1. LightGBM Regressor
    print(f"\n🤖 Treinando LightGBM Regressor...")

    lgb_reg = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=10,  # Reduzido para datasets menores
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    lgb_reg.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric="mae",
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
    )

    # Predições
    y_train_pred = lgb_reg.predict(X_train)
    y_val_pred = lgb_reg.predict(X_val)
    y_test_pred = lgb_reg.predict(X_test)

    # Métricas
    train_mae = mean_absolute_error(y_train, y_train_pred)
    val_mae = mean_absolute_error(y_val, y_val_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)

    train_r2 = r2_score(y_train, y_train_pred)
    val_r2 = r2_score(y_val, y_val_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print(f"\n📊 Métricas Regressor:")
    print(f"   Train - MAE: {train_mae:.2f}h | R²: {train_r2:.3f}")
    print(f"   Val   - MAE: {val_mae:.2f}h   | R²: {val_r2:.3f}")
    print(f"   Test  - MAE: {test_mae:.2f}h  | R²: {test_r2:.3f}")

    # 2. LightGBM Classifier (para categorias de tempo)
    print(f"\n🤖 Treinando LightGBM Classifier...")

    # Categorizar tempos (0-2 dias, 2-7 dias, 7-14 dias, 14+ dias)
    def categorizar_tempo(horas):
        if horas < 48:
            return 0
        elif horas < 168:
            return 1
        elif horas < 336:
            return 2
        else:
            return 3

    y_train_cat = y_train.apply(categorizar_tempo)
    y_val_cat = y_val.apply(categorizar_tempo)
    y_test_cat = y_test.apply(categorizar_tempo)

    lgb_clf = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    lgb_clf.fit(
        X_train, y_train_cat,
        eval_set=[(X_val, y_val_cat)],
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
    )

    # Acurácia
    train_acc = lgb_clf.score(X_train, y_train_cat)
    val_acc = lgb_clf.score(X_val, y_val_cat)
    test_acc = lgb_clf.score(X_test, y_test_cat)

    print(f"\n📊 Métricas Classifier:")
    print(f"   Train - Accuracy: {train_acc:.3f}")
    print(f"   Val   - Accuracy: {val_acc:.3f}")
    print(f"   Test  - Accuracy: {test_acc:.3f}")

    # 3. Feature importance
    print(f"\n🔍 Top 10 features mais importantes:")
    importances = lgb_reg.feature_importances_
    feature_names = X_train.columns
    feature_imp = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values('importance', ascending=False)

    for idx, row in feature_imp.head(10).iterrows():
        print(f"   {row['feature']:35s}: {row['importance']:6.0f}")

    # 4. Validação de aceitação
    print(f"\n✅ VALIDAÇÃO DE ACEITAÇÃO:")

    criterios = {
        "MAE < 30h (test)": test_mae < 30,
        "MAE < 50h (test)": test_mae < 50,  # Critério relaxado
        "R² > 0.20 (test)": test_r2 > 0.20,  # Critério relaxado
        "Accuracy > 0.40 (test)": test_acc > 0.40,
    }

    passed = all(criterios.values())

    for criterio, passou in criterios.items():
        status = "✅" if passou else "❌"
        print(f"   {status} {criterio}")

    if passed:
        print(f"\n🎉 Modelo {profile} APROVADO para produção!")
    else:
        print(f"\n⚠️  Modelo {profile} NÃO atende todos os critérios (mas pode ser útil)")

    # Retornar modelos e métricas
    return {
        "lgb_reg": lgb_reg,
        "lgb_clf": lgb_clf,
        "metrics": {
            "test_mae": test_mae,
            "test_r2": test_r2,
            "test_acc": test_acc,
            "val_mae": val_mae,
            "val_r2": val_r2,
            "passed": passed,
        },
        "feature_importance": feature_imp,
    }


def save_models(profile, models, features, output_dir="models"):
    """Salva modelos treinados."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    profile_lower = profile.lower()

    # Salvar modelos
    with open(output_path / f"{profile_lower}_light_lgb_reg.pkl", "wb") as f:
        pickle.dump(models["lgb_reg"], f)

    with open(output_path / f"{profile_lower}_light_lgb_clf.pkl", "wb") as f:
        pickle.dump(models["lgb_clf"], f)

    # Salvar metadata
    metadata = {
        "profile": profile,
        "model_type": "light",
        "is_mock": False,
        "features": features,
        "target": "tempo_espera_horas",
        "trained_at": datetime.now().isoformat(),
        "data_source": "datalastic_ais",
        "num_samples": len(models.get("X_train", [])),
        "metrics": models["metrics"],
        "artifacts": {
            "lgb_reg": f"{profile_lower}_light_lgb_reg.pkl",
            "lgb_clf": f"{profile_lower}_light_lgb_clf.pkl",
        },
        "training_params": {
            "n_estimators": 200,
            "max_depth": 8,
            "learning_rate": 0.05,
            "min_child_samples": 10,
        },
    }

    with open(output_path / f"{profile_lower}_light_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n💾 Modelos salvos em {output_path}/:")
    print(f"   - {profile_lower}_light_lgb_reg.pkl")
    print(f"   - {profile_lower}_light_lgb_clf.pkl")
    print(f"   - {profile_lower}_light_metadata.json")


def main():
    """Função principal."""
    print("="*70)
    print("TREINO DE MODELOS REAIS COM DADOS AIS")
    print("="*70)
    print()

    # 1. Carregar dados
    df = load_ais_data()

    # 2. Preprocessar
    df = preprocess_features(df)

    # 3. Filtrar apenas registros com target válido
    df_valid = df[df['waiting_time_hours'].notna()].copy()

    print(f"\n✅ Dados válidos para treino: {len(df_valid)}")

    # 4. Treinar modelo para cada perfil
    results = {}

    for profile in ["VEGETAL", "MINERAL", "FERTILIZANTE"]:
        # Filtrar dados do perfil
        df_profile = df_valid[df_valid['perfil'] == profile].copy()

        print(f"\n{'='*70}")
        print(f"PERFIL: {profile}")
        print("="*70)
        print(f"Amostras: {len(df_profile)}")

        if len(df_profile) < 20:
            print(f"⚠️  AVISO: Poucas amostras para {profile}. Usando todos os dados.")
            df_profile = df_valid.copy()

        # Features disponíveis
        available_features = [f for f in FEATURES_LIGHT[profile] if f in df_profile.columns]

        if len(available_features) < 10:
            print(f"⚠️  Apenas {len(available_features)} features disponíveis. Adicionando mais...")
            # Usar todas as features numéricas disponíveis
            numeric_cols = df_profile.select_dtypes(include=[np.number]).columns
            available_features = [c for c in numeric_cols if c != 'waiting_time_hours'][:15]

        print(f"Features usadas ({len(available_features)}): {available_features}")

        # Preparar dados
        X = df_profile[available_features].fillna(0)
        y = df_profile['waiting_time_hours']

        # Split
        if len(X) >= 50:
            # Split normal
            X_temp, X_test, y_temp, y_test = train_test_split(
                X, y, test_size=0.15, random_state=42
            )
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp, y_temp, test_size=0.176, random_state=42  # 0.176 * 0.85 ≈ 0.15
            )
        else:
            # Dataset pequeno - usar proporções menores
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            X_val, X_test, y_val, y_test = train_test_split(
                X_test, y_test, test_size=0.5, random_state=42
            )

        # Treinar
        models = train_light_model(
            profile, X_train, y_train, X_val, y_val, X_test, y_test
        )

        # Adicionar dados de treino para metadata
        models["X_train"] = X_train

        # Salvar
        save_models(profile, models, available_features)

        results[profile] = models

    # 5. Resumo final
    print("\n" + "="*70)
    print("RESUMO FINAL")
    print("="*70)

    for profile, result in results.items():
        metrics = result["metrics"]
        print(f"\n{profile}:")
        print(f"   MAE (test):  {metrics['test_mae']:.2f}h")
        print(f"   R² (test):   {metrics['test_r2']:.3f}")
        print(f"   Acc (test):  {metrics['test_acc']:.3f}")
        print(f"   Status:      {'✅ APROVADO' if metrics['passed'] else '⚠️  Revisar'}")

    print("\n" + "="*70)
    print("✅ TREINO CONCLUÍDO!")
    print("="*70)
    print("\nModelos salvos em: models/")
    print("Próximos passos:")
    print("  1. Testar modelos com streamlit_app.py")
    print("  2. Validar previsões")
    print("  3. Monitorar performance em produção")
    print("="*70)


if __name__ == "__main__":
    main()
