#!/usr/bin/env python3
"""
Script para criar modelos light mock/dummy para testar o sistema de fallback.

IMPORTANTE: Este script cria modelos MOCK para demonstração.
Para treinar modelos reais, você precisa:
1. Ter dados históricos em data/lineup_history.parquet
2. Instalar dependências: pandas, lightgbm, scikit-learn
3. Executar train_light_models_real.py (script completo documentado)

Este script mock permite testar o sistema de fallback SEM dados reais.
"""

import pickle
import json
from pathlib import Path
from datetime import datetime


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


class MockLightGBMModel:
    """Modelo mock que simula LightGBM para testar o sistema."""

    def __init__(self, features, profile):
        self.feature_names_ = features
        self.profile = profile

    def predict(self, X):
        """Retorna previsões mock baseadas em heurísticas simples."""
        import numpy as np

        # Converte para numpy se necessário
        if hasattr(X, 'values'):
            X_arr = X.values
        else:
            X_arr = np.array(X)

        n_samples = len(X_arr)

        # Heurística simples: tempo base + variação por fila
        if self.profile == "VEGETAL":
            tempo_base = 48.0  # 2 dias
        elif self.profile == "MINERAL":
            tempo_base = 36.0  # 1.5 dias
        else:  # FERTILIZANTE
            tempo_base = 84.0  # 3.5 dias

        # Adiciona variação aleatória
        predictions = np.random.normal(tempo_base, tempo_base * 0.3, n_samples)
        predictions = np.maximum(predictions, 0)  # Não pode ser negativo

        return predictions

    def predict_proba(self, X):
        """Retorna probabilidades mock para classificação."""
        import numpy as np
        n_samples = len(X)

        # 3 classes: Rápido, Médio, Longo
        proba = np.random.dirichlet([2, 3, 2], n_samples)
        return proba


def create_mock_model(profile, features, model_type="reg"):
    """Cria um modelo mock."""
    model = MockLightGBMModel(features, profile)
    return model


def save_mock_light_model(profile, features, output_dir="models"):
    """Salva modelos mock e metadados."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{profile.lower()}_light"

    print(f"\nCriando modelos MOCK para {profile}...")
    print(f"  Features: {len(features)}")

    # Cria modelos mock
    model_reg = create_mock_model(profile, features, "reg")
    model_clf = create_mock_model(profile, features, "clf")

    # Salva modelos
    with open(output_dir / f"{prefix}_lgb_reg.pkl", "wb") as f:
        pickle.dump(model_reg, f)

    with open(output_dir / f"{prefix}_lgb_clf.pkl", "wb") as f:
        pickle.dump(model_clf, f)

    # Metadata
    metadata = {
        "profile": profile,
        "model_type": "light",
        "is_mock": True,
        "features": features,
        "target": "tempo_espera_horas",
        "trained_at": datetime.now().isoformat() + "Z",
        "training_info": {
            "total_samples": "MOCK",
            "train_samples": "MOCK",
            "val_samples": "MOCK",
            "test_samples": "MOCK",
            "features_removed": len(features),
            "note": "Este é um modelo MOCK para demonstração do sistema de fallback"
        },
        "artifacts": {
            "lgb_reg": f"{prefix}_lgb_reg.pkl",
            "lgb_clf": f"{prefix}_lgb_clf.pkl",
        },
        "metrics": {
            "val": {
                "mae": "MOCK",
                "rmse": "MOCK",
                "r2": "MOCK"
            },
            "test": {
                "mae": "MOCK",
                "rmse": "MOCK",
                "r2": "MOCK"
            }
        },
        "warning": "⚠️ MODELO MOCK - Apenas para demonstração do sistema de fallback"
    }

    with open(output_dir / f"{prefix}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Modelos mock salvos: {output_dir}/{prefix}_*")


def main():
    """Função principal."""
    print("="*60)
    print("CRIANDO MODELOS LIGHT MOCK PARA DEMONSTRAÇÃO")
    print("="*60)
    print("\n⚠️  ATENÇÃO: Estes são modelos MOCK apenas para testar o sistema")
    print("    Para modelos reais, você precisa:")
    print("    1. Dados históricos (data/lineup_history.parquet)")
    print("    2. Dependências: pandas, lightgbm, scikit-learn")
    print("    3. Executar train_light_models_real.py")
    print()

    # Cria modelos mock para cada perfil
    for profile in ["VEGETAL", "MINERAL", "FERTILIZANTE"]:
        features = FEATURES_LIGHT[profile]
        save_mock_light_model(profile, features)

    print("\n" + "="*60)
    print("✅ Todos os modelos light MOCK foram criados!")
    print("="*60)
    print("\nArquivos criados em models/:")
    print("  - vegetal_light_*.pkl")
    print("  - mineral_light_*.pkl")
    print("  - fertilizante_light_*.pkl")
    print("\nPróximos passos:")
    print("  1. Testar o sistema de fallback no Streamlit")
    print("  2. Verificar badges e avisos na UI")
    print("  3. Quando tiver dados reais, treinar modelos reais")
    print()


if __name__ == "__main__":
    main()
