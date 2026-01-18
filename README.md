# Previsao de Filas (MVP)

Aplicacao Streamlit para previsao de tempo de espera em filas de atracacao.

## Visao geral
- **Modelo Geral**: simulador simples (regras de chuva + fila).
- **Modelo por Porto**: usa line-up por porto e aplica modelos treinados (LightGBM).

## Estrutura de pastas
- `lineups/`: arquivos CSV de line-up (um por porto). Nome do arquivo = nome do porto (ex.: `Itaqui.csv`).
- `lineups_previstos/`: saidas geradas com previsoes por navio.
- `models/`: artefatos do modelo treinado (`*_lgb_reg.pkl`, `*_lgb_clf.pkl`, `*_metadata.json`).

## Dependencias
```bash
pip install -r requirements.txt
```

## Treinamento do modelo
O treino baixa dados do ANTAQ/INMET/IBGE/IPEA via BigQuery e API IPEA.

```bash
python plano_1.py
```

Requer autenticacao no BigQuery:
```bash
gcloud auth application-default login
```

## Execucao do app
```bash
streamlit run streamlit_app.py
```

## Fluxo de inferencia por porto
1) Coloque um CSV ou XLSX em `lineups/` com o nome do porto (ex.: `Itaqui.csv`, `Ponta_da_Madeira.xlsx`).
2) Selecione o porto no app.
3) O app monta features e aplica o modelo correspondente ao perfil da carga.
4) O resultado e salvo em `lineups_previstos/lineup_previsto_{porto}_{YYYYMMDD}.csv`.

## Modelo Ponta da Madeira (Mineral enriquecido)
Script dedicado usando dados internos do terminal (2020-2022) + ANTAQ.

```bash
python ponta_da_madeira_model.py
```

Saidas:
- `models/ponta_da_madeira_lgb_reg.pkl`
- `models/ponta_da_madeira_xgb_reg.pkl`
- `models/ponta_da_madeira_ensemble_reg.pkl`
- `models/ponta_da_madeira_metadata.json`
- `models/ponta_da_madeira_report.json`

Registro de terminais premium:
- `premium_registry.json` define quais portos usam modelo premium e qual builder aplicar.

Resultados (ultima execucao)
- Treino: 1,901 registros (terminal 2020-2022)
- ANTAQ 2020-2025: 3,731 registros (terminal Ponta da Madeira)
- Validacao 2023 (ANTAQ puro):
  - LGBM MAE 160.29h, XGB MAE 160.52h, Ensemble MAE 155.07h
- Teste 2024-2025 (ANTAQ puro):
  - LGBM MAE 112.55h, XGB MAE 141.21h, Ensemble MAE 120.61h

## Colunas de saida
O app adiciona ao line-up:
- `tempo_espera_previsto_horas`
- `tempo_espera_previsto_dias`
- `classe_espera_prevista` (Rapido/Medio/Longo)
- `risco_previsto` (Baixo/Medio/Alto)
- `probabilidade_prevista`
- `eta_mais_espera` (ordenacao da fila prevista)

## Observacoes
- O line-up nao altera o treino; ele eh apenas input da inferencia.
- Clima e producao sao obtidos ao vivo (INMET/IBGE/IPEA) por porto.
- Se faltar ETA (`prev_chegada`), o app usa `ultima_atualizacao`/`extracted_at` como fallback.
- O app usa o ensemble (LGBM + XGB) quando disponivel para previsao em producao.

## Resultados do modelo (ultimo treino)
Data/hora: 2026-01-18 13:10

Registros por perfil:
- VEGETAL: 55,804
- MINERAL: 20,893
- FERTILIZANTE: 7,669

VEGETAL
- LightGBM (CV): MAE 46.78h +- 10.01, RMSE 75.69h +- 15.00, R2 0.302 +- 0.106
- XGBoost (teste 6 meses): MAE 55.48h, RMSE 70.54h, R2 0.460
- XGBoost agressivo (Top 15): MAE 46.11h, RMSE 71.50h, R2 0.446
- Ensemble (LGBM + XGB): MAE 37.99h, RMSE 60.72h, R2 0.600
- Classificador: AUC-ROC (macro) 0.794, acuracia 0.600

MINERAL
- LightGBM (CV): MAE 50.61h +- 9.52, RMSE 79.35h +- 6.64, R2 0.164 +- 0.252
- XGBoost (teste 6 meses): MAE 38.86h, RMSE 57.57h, R2 0.469
- XGBoost agressivo (Top 15): MAE 54.41h, RMSE 77.35h, R2 0.041
- Ensemble (LGBM + XGB): MAE 30.89h, RMSE 48.77h, R2 0.619
- Classificador: AUC-ROC (macro) 0.828, acuracia 0.640

FERTILIZANTE
- LightGBM (CV): MAE 102.39h +- 15.23, RMSE 150.69h +- 20.01, R2 0.366 +- 0.108
- XGBoost (teste 6 meses): MAE 113.76h, RMSE 142.38h, R2 0.316
- XGBoost agressivo (Top 15): MAE 144.87h, RMSE 195.88h, R2 -0.295
- Ensemble (LGBM + XGB): MAE 78.70h, RMSE 105.14h, R2 0.627
- Classificador: AUC-ROC (macro) 0.780, acuracia 0.585
