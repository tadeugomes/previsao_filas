# AIS + PortWatch Integration (Training)

## Objetivo
Definir schema, chaves de juncao e pipeline para integrar AIS (navio) e PortWatch (porto/dia)
no treino dos modelos de espera.

## Fontes de dados
- ANTAQ (publico): atracacoes + carga + clima/IBGE/IPEA (pipeline atual).
- Line-up (porto): CSV/XLSX com navios esperados (entrada do app).
- AIS (navio): posicoes ao vivo por MMSI/IMO (ex.: AISHub).
- PortWatch (porto/dia): atividade diaria agregada por porto.

## Arquivos existentes
- `portos_brasil_portwatch.csv` (lista de 102 portos BR, portid/portname).
- `portwatch_brasil_2020_2025.parquet` (historico BR limpo, 2020-2025).

## Schema (resumo)

### ANTAQ (treino atual)
Chaves e colunas principais:
- `data_chegada`, `data_atracacao`
- `nome_porto`, `nome_terminal`
- `tipo_carga`, `natureza_carga`, `cdmercadoria`, `stsh4`
- `movimentacao_total_toneladas`

### Line-up (porto)
Colunas esperadas:
- `Navio`, `Mercadoria`, `Chegada`, `Berco`, `DWT`
- opcionais: `IMO`/`MMSI`, `Pier`, `TX_EFETIVA`, `TX_COMERCIAL`, `Laytime`

### AIS (navio)
Colunas sugeridas (AISHub ou provedor equivalente):
- `mmsi`, `imo`, `callsign`, `shipname`
- `lat`, `lon`, `sog`, `cog`, `heading`
- `timestamp` (UTC)

### PortWatch (porto/dia)
Colunas principais:
- `date` (datetime)
- `portid`, `portname`, `country`, `ISO3`
- `portcalls_*`, `import_*`, `export_*`
- `ObjectId` (id unico)

## Chaves de juncao

### PortWatch -> ANTAQ (porto/dia)
1) Criar tabela de mapeamento:
   - `port_mapping.csv`: `portid`, `portname`, `nome_porto_antaq`, `municipio`, `uf`, `lat`, `lon`.
2) Normalizar nomes (upper/sem acento) para match inicial.
3) Join diario por:
   - `data_chegada_dt` (ANTAQ) == `date` (PortWatch, data)
   - `nome_porto_antaq` == `portname` (mapeado)

### AIS -> Line-up (navio)
Preferencia:
1) `MMSI` (line-up) == `mmsi` (AIS)
2) `IMO` == `imo`
Fallback:
3) `shipname` com fuzzy match (cuidado com homonimos)

### AIS -> ANTAQ (porto/dia)
Agregado por porto/dia (sem navio):
- usar `lat/lon` + raio do porto (ex.: 50 km) para contar navios ao largo.
- join por `nome_porto_antaq` + `data_chegada_dt`.

## Features novas

### AIS (navio)
- `eta_real_horas`: distancia ate porto / velocidade atual
- `dist_porto_km`: haversine(lat, lon, porto_lat, porto_lon)
- `velocidade_kn`: sog (knots)
- `desvio_rumo`: abs(cog - rumo_ideal_porto)
- `fila_ao_largo`: contagem de navios > 10 km do porto

### PortWatch (porto/dia)
- `portcalls_lag1`: portcalls dia anterior
- `portcalls_ma7`: media movel 7 dias
- `throughput_lag3`: media 3 dias de export/import
- `anomalia_portcalls`: z-score vs media historica

## Pipeline sugerido

### Historico (treino, uma vez)
1) PortWatch: usar `portwatch_brasil_2020_2025.parquet`.
2) Gerar features por porto/dia e salvar `portwatch_features.parquet`.
3) Merge com ANTAQ por porto/dia.

### Diario (producao)
1) AIS: baixar por porto/raio e salvar raw (`ais_raw_YYYYMMDD.csv`).
2) Agregar para features e salvar `ais_features_YYYYMMDD.parquet`.
3) PortWatch: atualizar janela movel (ultimos 30 dias).

## Checks de qualidade
- Cobertura de datas por porto (sem gaps longos).
- Match rate ANTAQ x PortWatch (ex.: % dias com features).
- Outliers AIS (velocidade > 30 kn, lat/lon nulos).
- Consistencia de timezone (AIS UTC, PortWatch diario).

## Proximos passos
1) Criar `port_mapping.csv` (mapeamento portname <-> nome_porto_antaq).
2) Script `build_portwatch_features.py` (lag/ma/ano).
3) Script `build_ais_features.py` (ETA real + fila ao largo).
4) Experimento de treino com ablation (baseline vs +PortWatch vs +AIS).
