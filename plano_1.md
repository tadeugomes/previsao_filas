# Plano 1 - Producao (modelo de previsao de tempo de espera)

Este documento descreve o pipeline de dados e treino. O codigo executavel esta em `plano_1.py`.

## Fontes de dados
- ANTAQ: atracacao e carga portuaria
- INMET (Base dos Dados): dados meteorologicos
- IBGE PAM (Base dos Dados): producao agricola municipal
- IPEA Data: precos de commodities

## Pipeline
1) Extracao das fontes
2) Integracao (clima, producao, precos)
3) Feature engineering
4) Treino com LightGBM e validacao temporal

## Execucao
- Ative o venv e instale dependencias:
  - `pip install -r requirements.txt`
- Rode o pipeline:
  - `python plano_1.py`

## Observacoes
- O acesso ao BigQuery depende do projeto `antaqdados` e credenciais via `gcloud auth application-default login`.
- Se a API do IPEA estiver indisponivel, o pipeline usa valores fallback para precos.
