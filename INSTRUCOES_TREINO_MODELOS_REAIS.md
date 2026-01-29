# Instruções para Treinar Modelos Light REAIS

**Data:** 2026-01-28
**Arquivo de dados:** `lineups_previstos/lineup_history.parquet` (40KB)
**Objetivo:** Substituir modelos MOCK por modelos treinados com dados reais

---

## 📋 Pré-requisitos

### 1. Dependências Python

```bash
pip install pandas>=1.5.0 pyarrow lightgbm>=3.3.0 scikit-learn>=1.0.0 numpy
```

### 2. Arquivo de Dados

✅ **Já existe:** `lineups_previstos/lineup_history.parquet` (40KB)

---

## 🔍 PASSO 1: Analisar Dados Disponíveis

Execute o script de análise para verificar a estrutura dos dados:

```bash
cd /home/user/previsao_filas
python3 analise_dados_historicos.py
```

**O que este script faz:**
- Carrega o arquivo parquet
- Lista todas as colunas disponíveis
- Verifica quais das 15 features necessárias estão presentes
- Mostra estatísticas do target (tempo_espera_horas)
- Indica se há dados suficientes para treino

**Output esperado:**
```
📊 Informações Básicas:
   Linhas: X,XXX
   Colunas: XX

✅ Features Necessárias para Modelo Light (15):
   ✅ navios_no_fundeio_na_chegada    X/X (XX%)
   ✅ porto_tempo_medio_historico      X/X (XX%)
   ...

💡 Recomendações:
   ✅ Dados suficientes para treinar (XX/15 features)
```

---

## 🚀 PASSO 2: Treinar Modelos Light

Depois de confirmar que há dados suficientes, execute o script de treino:

```bash
python3 pipelines/train_light_models_real.py
```

### Script de Treino (`train_light_models_real.py`)

Crie o arquivo `pipelines/train_light_models_real.py` com o código abaixo:

```python
#!/usr/bin/env python3
"""
Script para treinar modelos light REAIS com dados históricos.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import pickle
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Features por perfil
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


def load_historical_data():
    """Carrega dados históricos."""
    parquet_file = Path("lineups_previstos/lineup_history.parquet")

    if not parquet_file.exists():
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

    # LightGBM Classifier
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

    # Avaliação
    y_pred_val = lgb_reg.predict(X_val)
    val_mae = mean_absolute_error(y_val, y_pred_val)
    val_rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
    val_r2 = r2_score(y_val, y_pred_val)

    y_pred_test = lgb_reg.predict(X_test)
    test_mae = mean_absolute_error(y_test, y_pred_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    test_r2 = r2_score(y_test, y_pred_test)

    print(f"\n📊 Resultados:")
    print(f"   Val  → MAE: {val_mae:.2f}h | RMSE: {val_rmse:.2f}h | R²: {val_r2:.4f}")
    print(f"   Test → MAE: {test_mae:.2f}h | RMSE: {test_rmse:.2f}h | R²: {test_r2:.4f}")

    # Critério de aceitação
    acceptable = test_mae < 30 and test_r2 > 0.40
    status = "✅ ACEITÁVEL" if acceptable else "⚠️  REVISAR"
    print(f"\n   Status: {status}")

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

    # Carrega dados
    df = load_historical_data()

    if 'tempo_espera_horas' not in df.columns:
        print("❌ Coluna 'tempo_espera_horas' não encontrada!")
        return 1

    if 'perfil_modelo' not in df.columns:
        print("⚠️  Coluna 'perfil_modelo' não encontrada. Usando todos os dados.")
        df['perfil_modelo'] = 'VEGETAL'  # Default

    # Treina para cada perfil
    results = {}

    for profile in ["VEGETAL", "MINERAL", "FERTILIZANTE"]:
        # Filtra dados
        df_profile = df[df['perfil_modelo'] == profile].copy()

        if len(df_profile) < 100:
            print(f"\n⚠️  Pulando {profile}: apenas {len(df_profile)} registros")
            continue

        # Seleciona features
        features = FEATURES_LIGHT[profile]
        available_features = [f for f in features if f in df_profile.columns]

        if len(available_features) < 10:
            print(f"\n⚠️  Pulando {profile}: apenas {len(available_features)}/15 features disponíveis")
            continue

        print(f"\n{'='*60}")
        print(f"Perfil: {profile}")
        print(f"Registros: {len(df_profile):,}")
        print(f"Features: {len(available_features)}/15 disponíveis")
        print(f"{'='*60}")

        # Prepara dados
        X = df_profile[available_features]
        y = df_profile["tempo_espera_horas"]

        # Remove NaNs
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]

        print(f"Após limpeza: {len(X):,} registros")

        if len(X) < 100:
            print(f"⚠️  Dados insuficientes após limpeza")
            continue

        # Split
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.3, random_state=42
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42
        )

        # Treina
        result = train_light_model(
            profile, X_train, y_train, X_val, y_val, X_test, y_test
        )

        # Salva
        save_light_model(
            profile,
            result,
            available_features,
            result["metrics"]
        )

        results[profile] = result

    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DO TREINO")
    print("="*60)

    for profile, result in results.items():
        status = "✅" if result["acceptable"] else "⚠️"
        mae = result["metrics"]["test"]["mae"]
        r2 = result["metrics"]["test"]["r2"]
        print(f"{status} {profile:<20} MAE: {mae:.1f}h | R²: {r2:.3f}")

    if not results:
        print("❌ Nenhum modelo foi treinado!")
        print("\nPossíveis causas:")
        print("  - Dados insuficientes")
        print("  - Features necessárias não disponíveis")
        print("  - Coluna perfil_modelo ausente ou vazia")
        return 1

    print("\n✅ Treino concluído!")
    print("\nPróximos passos:")
    print("  1. Testar modelos: python3 test_fallback_system.py")
    print("  2. Executar Streamlit: streamlit run streamlit_app.py")
    print("  3. Validar previsões com dados reais")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

---

## 📝 PASSO 3: Validar Modelos Treinados

Após o treino, valide se os modelos foram criados corretamente:

```bash
# Verificar arquivos
ls -lh models/*_light_*

# Executar testes
python3 test_fallback_system.py
```

**Resultados esperados:**
```
✅ VEGETAL light model: OK (15 features)
✅ MINERAL light model: OK (15 features)
✅ FERTILIZANTE light model: OK (15 features)
✅ TODOS OS TESTES PASSARAM!
```

---

## 🎯 PASSO 4: Testar no Streamlit

Execute a aplicação e teste com dados reais:

```bash
streamlit run streamlit_app.py
```

**O que observar:**
1. Carregue um lineup
2. Veja o badge de qualidade (🟢🟡🔴)
3. Se qualidade < 80%, verá: 🔧 **Modelo Simplificado (REAL)**
4. Metadata JSON deve mostrar: `"is_mock": false`

---

## ✅ Critérios de Aceitação

Os modelos treinados serão aceitos se:

| Métrica | Critério | Importância |
|---------|----------|-------------|
| **MAE** | < 30h | ⭐⭐⭐ Crítico |
| **R²** | > 0.40 | ⭐⭐⭐ Crítico |
| **Degradação vs Completo** | < 20% | ⭐⭐ Importante |
| **Registros de treino** | >= 100 por perfil | ⭐ Desejável |

---

## ⚠️ Troubleshooting

### Problema 1: Poucas Amostras

```
⚠️ Pulando VEGETAL: apenas 50 registros
```

**Solução:**
- Coletar mais dados históricos
- Combinar perfis similares
- Reduzir número de features (10 ao invés de 15)

### Problema 2: Features Faltando

```
⚠️ Pulando MINERAL: apenas 7/15 features disponíveis
```

**Solução:**
- Treinar com features disponíveis
- Gerar features faltantes (ex: calcular flags)
- Usar modelo completo para esse perfil

### Problema 3: MAE Alto

```
⚠️ REVISAR - MAE: 45.2h | R²: 0.35
```

**Solução:**
- Aumentar dados de treino
- Ajustar hiperparâmetros (n_estimators, max_depth)
- Adicionar feature engineering
- Considerar manter modelo MOCK até melhorar dados

---

## 📦 Instruções para Agente de IA Local

Se você está usando um agente de IA local para treinar os modelos, forneça estas instruções:

```
TAREFA: Treinar modelos light reais para sistema de previsão de filas portuárias

CONTEXTO:
- Projeto: /home/user/previsao_filas
- Dados: lineups_previstos/lineup_history.parquet (40KB)
- Objetivo: Substituir modelos MOCK por modelos reais com 15 features

PASSOS:
1. Instalar dependências:
   pip install pandas pyarrow lightgbm scikit-learn numpy

2. Analisar dados disponíveis:
   python3 analise_dados_historicos.py

3. Criar script de treino (se não existir):
   - Copiar código do arquivo INSTRUCOES_TREINO_MODELOS_REAIS.md
   - Salvar em pipelines/train_light_models_real.py

4. Executar treino:
   python3 pipelines/train_light_models_real.py

5. Validar resultados:
   python3 test_fallback_system.py

CRITÉRIOS DE SUCESSO:
- MAE < 30h por perfil
- R² > 0.40 por perfil
- Modelos salvos em models/*_light_*.pkl
- Metadata com is_mock: false

ENTREGÁVEIS:
- 3 modelos treinados (VEGETAL, MINERAL, FERTILIZANTE)
- Metadata JSON atualizado
- Relatório de métricas (MAE, RMSE, R²)
```

---

## 📊 Output Esperado

Ao final do treino bem-sucedido:

```
============================================================
RESUMO DO TREINO
============================================================
✅ VEGETAL              MAE: 22.5h | R²: 0.480
✅ MINERAL              MAE: 28.3h | R²: 0.450
✅ FERTILIZANTE         MAE: 25.7h | R²: 0.420

✅ Treino concluído!

Próximos passos:
  1. Testar modelos: python3 test_fallback_system.py
  2. Executar Streamlit: streamlit run streamlit_app.py
  3. Validar previsões com dados reais
```

---

## 🎉 Finalização

Após o treino bem-sucedido:

1. ✅ Modelos MOCK serão substituídos por modelos REAIS
2. ✅ Metadata terá `"is_mock": false`
3. ✅ Sistema de fallback continuará funcionando automaticamente
4. ✅ Performance será validada com dados históricos

**Importante:** Se os resultados não forem aceitáveis (MAE > 30h ou R² < 0.40), é melhor **manter os modelos MOCK** até coletar mais dados ou melhorar feature engineering.

---

**Criado em:** 2026-01-28
**Arquivo de dados:** lineups_previstos/lineup_history.parquet
**Tamanho:** 40KB
**Status:** Pronto para treino
