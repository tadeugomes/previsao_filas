# Previsao de Filas (MVP)

Aplicacao Streamlit para previsao de tempo de espera em filas de atracacao.

## Visao geral
- **Modelo Geral (Nacional)**: simulador simples (regras de chuva + fila) sem line-up.
- **Modelo por Porto (Basico)**: usa line-up por porto e aplica modelos treinados (LightGBM/XGBoost + ensemble).
- **Modelo Premium (Terminal)**: usa line-up com dados internos do terminal (ex.: Ponta da Madeira) para previsoes mais precisas.

## Estrutura de pastas
- `lineups/`: arquivos CSV de line-up (um por porto). Nome do arquivo = nome do porto (ex.: `Itaqui.csv`).
- `lineups_previstos/`: saidas geradas com previsoes por navio.
- `models/`: artefatos do modelo treinado (`*_lgb_reg.pkl`, `*_lgb_clf.pkl`, `*_metadata.json`).
- `premium_registry.json`: define quais portos usam modelo premium e qual builder aplicar.

## Dependencias
```bash
pip install -r requirements.txt
```

## AIS (novos dados)
Arquivos e configuracoes:
- `data/ports_config.csv`: portos com lat/lon e raio (AIS).
- `data/port_mapping.csv`: mapeamento de nomes de porto (ANTAQ/AIS).
- `data/ais_features.parquet` (opcional): features AIS agregadas por porto/dia.

Scripts (pipelines):
```bash
# AIS (captura diaria + features)
set AISHUB_USER=SEU_USER
python pipelines/ais_fetch.py --ports data/ports_config.csv --out data/ais/raw
python pipelines/ais_features.py --input-dir data/ais/raw --date 20250118 --output data/ais_features.parquet
```

Observacoes:
- O treino usa `ais_features.parquet` se existir (senao preenche zeros).

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

## Interface (Streamlit)
Sidebar (parametros):
- Porto, Tipo de Carga, Data de Chegada.
- Berco (se existir no line-up).
- Navio (se existir no line-up).
- Tipo de Navio (usa a coluna `Categoria` quando presente).
- Clima (INMET automatico com opcao de ajuste manual).
- Navios no fundeio (preenchido automaticamente pelo line-up).
- Botao de exportacao CSV aparece quando ha resultados.

Painel:
- Resumo Executivo (cards), Tendencia da Fila (grafico), Detalhes Operacionais, Insights.
- Banner de modo: Basico ou Premium.
- Pergunta do modelo exibida abaixo do botao, variando por modo:
  - Nacional: previsao geral do pais.
  - Premium: previsao por navio/berco/categoria.
  - Basico: previsao por porto.

Validacoes de entrada:
- Data de chegada limitada a 30 dias no passado ate 90 dias no futuro (reset automatico se invalida).
- Chuva acumulada e navios no fundeio nao aceitam valores negativos (reset para ultimo valor valido).
- Tooltip em "Chuva acumulada 72h (mm)" explica unidade.

Auditoria:
- Logs da aplicacao em `logs/app.log` (erros e inferencias).

## Fluxo de inferencia por porto
1) Coloque um CSV ou XLSX em `lineups/` com o nome do porto (ex.: `Itaqui.csv`, `Ponta_da_Madeira.xlsx`).
2) Selecione o porto no app.
3) O app monta features e aplica o modelo correspondente ao perfil da carga.
4) Se um navio/berco/tipo de navio for selecionado, a previsao e filtrada para esse alvo.
5) O resultado e salvo em `lineups_previstos/lineup_previsto_{porto}_{YYYYMMDD}.csv`.
6) Se `data/ais_features.parquet` existir, as features AIS entram na inferencia.

## Colunas esperadas no line-up
CSV (publico):
- `navio`, `carga`/`produto`, `prev_chegada`, `berco`, `dwt`, `ultima_atualizacao`, `extracted_at`.

XLSX (terminal):
- `navio` (se existir), `carga`/`produto`, `chegada`, `berco`/`pier`, `dwt`, `tx_efetiva`, `tx_comercial`, `laytime`.
- Para Ponta da Madeira, a coluna `categoria` habilita o filtro de tipo de navio.

Obs: o filtro de navio so aparece quando ha coluna de navio (ex.: `Navio`, `navio`, `nome_navio`, `embarcacao`).

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
  - Ponta da Madeira: usa o modelo premium e o filtro por `categoria` (tipo de navio).

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
- A mensagem de previsao em horas inclui MAE esperado quando o modelo fornece esse dado.

## Resultados do modelo (ultimo treino)
Data/hora: 2026-01-22 10:27
Perfis treinados: VEGETAL (baseline INMET; maré/clima mare_clima desativados)
Nota: ablação mostrou que o baseline (INMET) superou as variações com maré/clima mare_clima neste treino.
Resumo da ablacao (VEGETAL, Ensemble):
- Baseline (INMET): MAE 36.78h, R2 0.627
- INMET + clima mare_clima (sem mare): MAE 37.85h, R2 0.603
- INMET + mare (sem clima mare_clima): MAE 37.83h, R2 0.604
- Full (INMET + mare + clima mare_clima): MAE 37.59h, R2 0.608

Registros por perfil (treino VEGETAL):
- VEGETAL: 55,804

VEGETAL
- LightGBM (CV): MAE 46.60h +- 10.13, RMSE 75.43h +- 15.27, R2 0.308 +- 0.109
- XGBoost (teste 6 meses): MAE 54.81h, RMSE 70.02h, R2 0.468
- XGBoost agressivo (Top 15): MAE 43.41h, RMSE 68.17h, R2 0.496
- Ensemble (LGBM + XGB): MAE 36.78h, RMSE 58.65h, R2 0.627
- Classificador: AUC-ROC (macro) 0.793, acuracia 0.604

MINERAL (treino anterior 2026-01-18)
- LightGBM (CV): MAE 50.61h +- 9.52, RMSE 79.35h +- 6.64, R2 0.164 +- 0.252
- XGBoost (teste 6 meses): MAE 38.86h, RMSE 57.57h, R2 0.469
- XGBoost agressivo (Top 15): MAE 54.41h, RMSE 77.35h, R2 0.041
- Ensemble (LGBM + XGB): MAE 30.89h, RMSE 48.77h, R2 0.619
- Classificador: AUC-ROC (macro) 0.828, acuracia 0.640

FERTILIZANTE (treino anterior 2026-01-18)
- LightGBM (CV): MAE 102.39h +- 15.23, RMSE 150.69h +- 20.01, R2 0.366 +- 0.108
- XGBoost (teste 6 meses): MAE 113.76h, RMSE 142.38h, R2 0.316
- XGBoost agressivo (Top 15): MAE 144.87h, RMSE 195.88h, R2 -0.295
- Ensemble (LGBM + XGB): MAE 78.70h, RMSE 105.14h, R2 0.627
- Classificador: AUC-ROC (macro) 0.780, acuracia 0.585
