# Recomendações: Portos do Arco Norte e Granéis Sólidos

## 📋 RESUMO EXECUTIVO

**Pergunta:** Devo incorporar dataset de portos fluviais para treinar o modelo de ML?

**Resposta:** ✅ **SIM, mas com adaptações importantes!**

### Por que SIM:
1. **Importância econômica:** Arco Norte escoa 40% dos grãos do Brasil
2. **Competitividade:** Reduzir calado parado = mais operações/ano
3. **Dados já parcialmente disponíveis:** Santarém e Barcarena já estão no Dataset 2 v2
4. **ML funciona para híbridos:** Portos estuarinos podem usar maré astronômica + variáveis fluviais

### Por que COM ADAPTAÇÕES:
1. **Método diferente:** Portos puramente fluviais NÃO usam análise harmônica
2. **Variáveis diferentes:** Vazão de rio + precipitação > vento + ondas
3. **Separação necessária:** Criar categoria "Portos Híbridos (Estuário + Rio)"
4. **Modelos diferentes:** ML precisa aprender que alguns portos são dominados por vazão

---

## 🚢 STATUS ATUAL: PORTOS DO ARCO NORTE NO PROJETO

### ✅ Já Incluídos com Maré Astronômica:

| Porto | Status Dataset | Script Maré | Tipo | Observação |
|-------|---------------|-------------|------|------------|
| **Itaqui (MA)** | ✅ Dataset 2 v2 | ✅ `previsao_mares_itaqui.py` | Oceânico | **Perfeito!** Porto oceânico clássico |
| **Vila do Conde (PA)** | ✅ Dataset 2 v2 | ✅ `previsao_mares_viladoconde.py` | **Híbrido** | Tem maré + influência fluvial |

### ⚠️ Incluídos SEM Maré (apenas meteorologia):

| Porto | Status Dataset | Script Maré | Tipo | Problema |
|-------|---------------|-------------|------|----------|
| **Santarém (PA)** | ✅ Dataset 2 v2 | ❌ Não | Fluvial | Sem dados de vazão ANA |
| **Barcarena (PA)** | ✅ Dataset 2 v2 | ❌ Não | **Híbrido?** | Precisa verificar se tem maré |

### ❌ Importantes do Arco Norte que FALTAM:

| Porto | Tipo | Relevância Grãos | Recomendação |
|-------|------|------------------|--------------|
| **Miritituba (PA)** | Fluvial | ⭐⭐⭐⭐⭐ | ✅ Adicionar se expandir escopo |
| **Porto Velho (RO)** | Fluvial | ⭐⭐⭐⭐ | ✅ Adicionar se expandir escopo |

---

## 📊 ARCO NORTE: RANKING DE IMPORTÂNCIA PARA GRANÉIS SÓLIDOS

### 🥇 Tier 1 - CRÍTICOS (já no projeto):

#### 1. **Itaqui (MA)** ⭐⭐⭐⭐⭐
- **Tipo:** Oceânico (maré astronômica forte)
- **Granéis:** Soja, milho, minério de ferro
- **Movimentação:** ~30 milhões ton/ano
- **Status no projeto:** ✅ **COMPLETO** (Dataset 2 v2 + script maré)
- **ML:** Pode usar análise harmônica como baseline forte

```python
# Modelo para Itaqui:
nivel_previsto = mare_astronomica + ml_correcao_meteorologica
# Variáveis: vento, pressão, ondas (já no dataset)
```

#### 2. **Vila do Conde/Barcarena (PA)** ⭐⭐⭐⭐⭐
- **Tipo:** HÍBRIDO (maré + rio)
- **Granéis:** Bauxita, alumina, soja (crescente)
- **Movimentação:** ~20 milhões ton/ano
- **Status no projeto:** ✅ **PARCIAL** (Dataset 2 v2 + script maré, MAS falta vazão rio)
- **ML:** Precisa combinar maré astronômica + vazão Amazonas

```python
# Modelo para Vila do Conde:
nivel_previsto = mare_astronomica + ml_correcao(vazao_amazonas, meteorologia)
# FALTA no dataset: vazao_rio
```

**⚠️ AÇÃO NECESSÁRIA:** Adicionar dados ANA de vazão do Rio Pará/Amazonas

### 🥈 Tier 2 - MUITO IMPORTANTES (no dataset, mas incompletos):

#### 3. **Santarém (PA)** ⭐⭐⭐⭐
- **Tipo:** FLUVIAL (maré astronômica desprezível)
- **Granéis:** Soja (corredor Centro-Oeste)
- **Movimentação:** ~15 milhões ton/ano
- **Status no projeto:** ⚠️ **INCOMPLETO** (Dataset 2 v2 apenas meteorologia)
- **ML:** NÃO usar análise harmônica! Apenas modelo hidrológico

```python
# Modelo para Santarém:
nivel_previsto = ml_hidrologico(vazao_amazonas, precipitacao, sazonalidade)
# Análise harmônica = ERRO! (amplitude M2 < 2cm)
```

**⚠️ PROBLEMAS ATUAIS:**
1. ❌ Não tem script de maré (correto - não deveria ter)
2. ❌ Não tem dados de vazão ANA (erro na coleta v2)
3. ✅ Tem meteorologia (útil, mas não suficiente)

**✅ AÇÃO NECESSÁRIA:** Adicionar:
- Vazão ANA estação 17050001 (Santarém)
- Vazão ANA estação 17050000 (Óbidos - montante)
- Precipitação bacia do Amazonas (CHIRPS/INMET)

#### 4. **Barcarena (PA) - Porto Exclusivo** ⭐⭐⭐
- **Tipo:** HÍBRIDO? (precisa verificar)
- **Granéis:** Alumina, caulim
- **Status no projeto:** ⚠️ **INCOMPLETO**
- **Observação:** Está mais perto da foz que Santarém

**🔍 PESQUISA NECESSÁRIA:**
```python
# Verificar com DHN se Barcarena tem tábua de marés:
# - Se SIM → criar script análise harmônica
# - Se NÃO → tratar como fluvial (igual Santarém)
```

### 🥉 Tier 3 - IMPORTANTES (fora do projeto):

#### 5. **Miritituba (PA)** ⭐⭐⭐⭐
- **Tipo:** FLUVIAL puro
- **Granéis:** Soja (hidrovia Tapajós)
- **Crescimento:** Terminal novo, em expansão
- **Status no projeto:** ❌ NÃO INCLUÍDO
- **Distância do mar:** ~700 km
- **Maré astronômica:** Praticamente zero

**Estação ANA:**
```
Código: 17320000 (Itaituba - próximo)
Variável: Cota do rio
Período: Disponível
```

#### 6. **Porto Velho (RO)** ⭐⭐⭐⭐
- **Tipo:** FLUVIAL puro
- **Granéis:** Soja (corredor RO + MT + Bolívia)
- **Movimentação:** ~5 milhões ton/ano
- **Status no projeto:** ❌ NÃO INCLUÍDO
- **Peculiaridade:** Afetado por usinas hidrelétricas

**Estação ANA:**
```
Código: 15400000 (Porto Velho)
Variável: Cota + Vazão
Período: 1967-presente
```

---

## 🎯 RECOMENDAÇÃO ESTRATÉGICA

### ✅ **OPÇÃO RECOMENDADA: Expandir projeto em 2 fases**

#### **FASE 1 (CURTO PRAZO): Completar portos híbridos atuais**

**Objetivo:** Maximizar uso de maré astronômica já calculada

**Ações:**
1. ✅ **Vila do Conde:** Adicionar dados ANA vazão Rio Pará
2. ✅ **Barcarena:** Verificar com DHN se tem maré significativa
   - Se SIM: criar `previsao_mares_barcarena.py`
   - Se NÃO: tratar como fluvial puro
3. ✅ **Santarém:** Adicionar dados ANA vazão (sem criar script de maré)

**Dataset a criar:**
```
dados_historicos_portos_hibridos_arco_norte_v2.parquet
```

**Colunas:**
```python
df.columns = [
    'timestamp',
    'station',  # 'VilaDoCondePA', 'SantaremPA', 'BarcenaPA'

    # Maré (apenas para Vila do Conde e Barcarena se aplicável)
    'mare_astronomica_m',  # NaN para Santarém

    # Meteorologia (já existe no Dataset 2)
    'wind_speed_10m',
    'wind_direction_10m',
    'pressure_msl',

    # NOVO: Dados fluviais ANA
    'vazao_rio_m3s',        # Vazão do rio principal
    'cota_rio_m',           # Nível do rio medido
    'vazao_montante_m3s',   # Vazão estação a montante

    # NOVO: Precipitação
    'precip_bacia_30d_mm',  # Acumulado 30 dias na bacia

    # Indicadores
    'mes',                  # Sazonalidade
    'tem_mare_astronomica', # Boolean: True/False
]
```

**Estações ANA a buscar:**

| Porto | Estação Local | Estação Montante | Tipo |
|-------|---------------|------------------|------|
| **Vila do Conde** | 31140000 (Tucuruí - proxy) | 16350000 (Altamira) | Híbrido |
| **Santarém** | 17050001 (Santarém) | 17050000 (Óbidos) | Fluvial |
| **Barcarena** | 31140000 (Tucuruí - proxy) | 16350000 (Altamira) | Híbrido? |

#### **FASE 2 (MÉDIO PRAZO): Adicionar portos fluviais puros**

**Objetivo:** Expandir para terminais interiores (Miritituba, Porto Velho)

**Método:** Modelo ML puramente hidrológico (SEM análise harmônica)

**Dataset a criar:**
```
dados_historicos_portos_fluviais_puros.parquet
```

**Modelo de ML diferente:**
```python
# Para portos fluviais puros (Santarém, Miritituba, Porto Velho):
def prever_nivel_fluvial(features):
    """
    NÃO usar análise harmônica!
    Apenas features hidrológicas
    """
    return ml_model.predict([
        vazao_local,
        vazao_montante,
        precip_bacia_30d,
        precip_bacia_60d,
        mes,  # Sazonalidade
        ano_hidrologico,
        # SEM: mare_astronomica (irrelevante!)
        # SEM: ondas (não existe em rio)
    ])
```

---

## 📊 VARIÁVEIS NECESSÁRIAS PARA DATASET FLUVIAL/HÍBRIDO

### VARIÁVEL 1: Vazão do Rio (ANA) ⭐⭐⭐⭐⭐

**Importância:** CRÍTICA para portos fluviais e híbridos

**Fonte:** Sistema Hidroweb da ANA

**Como buscar:**
```python
import requests
import pandas as pd
from datetime import datetime, timedelta

def buscar_vazao_ana(codigo_estacao, data_inicio, data_fim):
    """
    Busca vazão de estação ANA

    Códigos importantes:
    - 17050001: Santarém
    - 17050000: Óbidos (montante Santarém)
    - 15400000: Porto Velho
    - 31140000: Tucuruí (proxy Vila do Conde)
    """
    url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieVazoes"

    params = {
        'codEstacao': codigo_estacao,
        'dataInicio': data_inicio.strftime('%d/%m/%Y'),
        'dataFim': data_fim.strftime('%d/%m/%Y'),
        'tipoDados': '3',  # 3 = dados consistidos
        'nivelConsistencia': ''
    }

    response = requests.get(url, params=params)

    # Parse XML response
    # ... (código de parsing)

    return df_vazao

# Exemplo de uso:
df_santarem = buscar_vazao_ana(
    codigo_estacao='17050001',
    data_inicio=datetime(2020, 1, 1),
    data_fim=datetime(2025, 12, 31)
)
```

**⚠️ PROBLEMA CONHECIDO:**
Na v2, o WebService da ANA retornou erro "Login failed for user".

**Soluções alternativas:**
1. ✅ Download manual via portal Hidroweb: https://www.snirh.gov.br/hidroweb/
2. ✅ API alternativa: usar biblioteca `hidrobr` (Python)
3. ✅ Dados via SOAP (mais estável que REST)

```python
# Alternativa: biblioteca hidrobr
from hidrobr import get_data

df = get_data.get_flow(
    station_code='17050001',
    start_date='2020-01-01',
    end_date='2025-12-31'
)
```

**Unidade:** m³/s (metros cúbicos por segundo)

**Frequência:** Diária ou horária (quando disponível)

**Lead time possível:**
- 7-14 dias (usando previsão meteorológica + modelo hidrológico)
- Vazão é resposta lenta da bacia (lag time ~10-30 dias)

---

### VARIÁVEL 2: Cota do Rio (ANA) ⭐⭐⭐⭐

**Importância:** ALTA (correlaciona diretamente com calado disponível)

**Diferença de Vazão:**
- **Vazão** = Volume de água passando (m³/s) → Causa
- **Cota** = Nível da água (m) → Efeito

**Relação:** Curva de Descarga (Rating Curve)
```python
# Em portos fluviais, geralmente:
cota = f(vazao, geometria_leito)

# Mas ML pode aprender direto da cota se for o target:
target = cota_rio_m
```

**Fonte:** Mesmo endpoint ANA, parâmetro diferente

```python
def buscar_cota_ana(codigo_estacao, data_inicio, data_fim):
    url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieCotas"
    # Similar ao de vazão, mas retorna nível em metros
```

**Uso no ML:**
```python
# Opção 1: Usar vazão para prever cota
features = ['vazao_local', 'vazao_montante', 'precip']
target = 'cota_rio_m'

# Opção 2: Usar cota diretamente se for disponível em tempo real
# (melhor para previsão de curto prazo)
```

---

### VARIÁVEL 3: Precipitação na Bacia (CHIRPS/INMET) ⭐⭐⭐⭐⭐

**Importância:** CRÍTICA (controla vazão com lag de 10-30 dias)

**Por que importante:**
- Chuva hoje → Vazão elevada em 2-4 semanas
- Permite previsão com antecedência (usando forecast de precipitação)

**Fonte 1: CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data)**

```python
import requests

def buscar_chirps_bacia(lat_min, lat_max, lon_min, lon_max, data_inicio, data_fim):
    """
    CHIRPS: Dados de precipitação por satélite
    Resolução: 0.05° (~5km)
    Frequência: Diária
    Cobertura: Global, 1981-presente
    """
    # API Google Earth Engine ou download direto
    # https://data.chc.ucsb.edu/products/CHIRPS-2.0/

    # Exemplo para bacia do Tapajós (Santarém):
    lat_min, lat_max = -10, 0
    lon_min, lon_max = -58, -54

    # Calcular média espacial da bacia
    precip_bacia_diaria = calcular_media_espacial(grid_chirps, poligono_bacia)

    # Criar features:
    precip_acum_7d = precip_bacia_diaria.rolling(7).sum()
    precip_acum_30d = precip_bacia_diaria.rolling(30).sum()
    precip_acum_90d = precip_bacia_diaria.rolling(90).sum()

    return precip_acum_7d, precip_acum_30d, precip_acum_90d
```

**Fonte 2: INMET (estações meteorológicas)**

```python
def buscar_precip_inmet(estacoes, data_inicio, data_fim):
    """
    INMET: Estações terrestres
    Mais preciso que satélite, mas cobertura esparsa
    """
    # API INMET (mesma usada no Dataset 1)
    # Para bacias grandes, usar múltiplas estações

    estacoes_bacia_tapajos = [
        'A001',  # Santarém
        'A002',  # Itaituba
        # ... outras
    ]
```

**Features derivadas importantes:**
```python
# Para ML:
features_precipitacao = [
    'precip_local_7d',      # Chuva local última semana
    'precip_bacia_30d',     # Acumulado 30 dias (crucial!)
    'precip_bacia_60d',     # Acumulado 60 dias
    'precip_bacia_90d',     # Acumulado 90 dias (sazonalidade)
    'anomalia_precip_mes',  # Desvio da média histórica
]
```

**Bacias importantes:**

| Porto | Bacia | Área (km²) | Tempo de Concentração |
|-------|-------|------------|----------------------|
| **Santarém** | Amazonas | 6.1M | ~30-45 dias |
| **Porto Velho** | Madeira | 1.4M | ~20-30 dias |
| **Vila do Conde** | Amazonas (foz) | 6.1M | ~30-45 dias |
| **Miritituba** | Tapajós | 490k | ~15-25 dias |

---

### VARIÁVEL 4: Sazonalidade (calendário) ⭐⭐⭐⭐

**Importância:** ALTA em rios amazônicos

**Por que importante:**
- Regime de cheias e vazantes é MUITO previsível
- Cheia: Março-Maio (Amazonas) / Fev-Abr (Madeira)
- Vazante: Agosto-Outubro

**Features de tempo:**
```python
# Features temporais para ML em rios:
features_tempo = [
    'mes',                    # 1-12
    'dia_do_ano',            # 1-365
    'mes_hidrologico',       # Ciclo de chuvas regional
    'sin_mes',               # sin(2π * mes / 12) - ciclicidade
    'cos_mes',               # cos(2π * mes / 12)
    'ano_hidrologico',       # Ex: Out/2020 - Set/2021 = 2021
    'fase_ciclo_hidrologico' # 'cheia', 'vazante', 'seca', 'enchente'
]

import numpy as np

def criar_features_temporais(df):
    df['mes'] = df['timestamp'].dt.month
    df['dia_ano'] = df['timestamp'].dt.dayofyear
    df['sin_mes'] = np.sin(2 * np.pi * df['mes'] / 12)
    df['cos_mes'] = np.cos(2 * np.pi * df['mes'] / 12)

    # Fase do ciclo hidrológico (específico Amazonas):
    def fase_hidrologica(mes):
        if mes in [3, 4, 5]:
            return 'cheia'
        elif mes in [6, 7, 8]:
            return 'vazante'
        elif mes in [9, 10, 11]:
            return 'seca'
        else:  # [12, 1, 2]
            return 'enchente'

    df['fase_ciclo'] = df['mes'].apply(fase_hidrologica)

    return df
```

---

### VARIÁVEL 5: Vazão Montante (estação a montante) ⭐⭐⭐⭐

**Importância:** ALTA (onda de cheia propaga rio abaixo)

**Conceito:** Medir vazão em estação rio acima para prever nível rio abaixo

**Propagação de onda:**
```python
# Exemplo: Santarém
# Óbidos (100km montante) → Santarém
# Lag time: ~2-4 dias

# Vazão em Óbidos hoje → Nível em Santarém em +2 dias
vazao_obidos_t0 = 200000  # m³/s
nivel_santarem_t2 = f(vazao_obidos_t0, lag=2)
```

**Features lagged:**
```python
# Criar features com defasagem temporal:
df['vazao_montante_lag_1d'] = df['vazao_montante'].shift(1)
df['vazao_montante_lag_2d'] = df['vazao_montante'].shift(2)
df['vazao_montante_lag_3d'] = df['vazao_montante'].shift(3)
df['vazao_montante_lag_7d'] = df['vazao_montante'].shift(7)

# ML aprende: "vazão alta em Óbidos ontem = nível alto em Santarém hoje"
```

**Pares de estações recomendados:**

| Porto (target) | Estação Montante | Distância | Lag Estimado |
|----------------|------------------|-----------|--------------|
| **Santarém** | Óbidos (17050000) | 100 km | 2-4 dias |
| **Porto Velho** | Guajará-Mirim (15320002) | 300 km | 3-5 dias |
| **Vila do Conde** | Altamira (16350000) | 700 km | 7-15 dias |

---

### VARIÁVEL 6: Maré Astronômica (apenas para híbridos) ⭐⭐⭐⭐

**Importância:** ALTA para Vila do Conde, ZERO para Santarém/Porto Velho

**Quando usar:**
- ✅ **Vila do Conde:** Maré M2 ~1-2m (significativo!)
- ✅ **Barcarena:** Se DHN confirmar maré
- ❌ **Santarém:** Maré M2 ~0.02m (desprezível)
- ❌ **Miritituba:** Sem maré
- ❌ **Porto Velho:** Sem maré

**Como usar no ML:**
```python
# Para portos híbridos (ex: Vila do Conde):
features = [
    'mare_astronomica_m',      # Do script já existente!
    'vazao_rio_m3s',           # ANA
    'precip_bacia_30d',        # CHIRPS
    'vento_10m',               # INMET/ERA5
    'pressao_msl',             # INMET/ERA5
]

target = 'nivel_observado_m'

# ML aprende a combinar:
# nivel_real = mare_astronomica + efeito_vazao + efeito_vento + efeito_pressao
```

**Para portos fluviais puros:**
```python
# NÃO incluir mare_astronomica!
features = [
    'vazao_local',
    'vazao_montante_lag_3d',
    'precip_bacia_30d',
    'mes',
    # SEM mare_astronomica (seria ruído)
]
```

---

### VARIÁVEL 7: Efeito de Barragens (para Porto Velho) ⭐⭐⭐

**Importância:** MÉDIA (específico para rios regularizados)

**Caso: Porto Velho (Rio Madeira)**
- Usina Jirau (montante)
- Usina Santo Antônio (montante)

**Problema:** Vazão não é mais natural, é controlada

**Dados possíveis:**
```python
# 1. Vazão defluente das usinas (ONS - Operador Nacional do Sistema)
url_ons = "http://sdro.ons.org.br/SDRO/"

# 2. Nível do reservatório
# 3. Geração de energia (proxy de turbinamento)

features_barragem = [
    'vazao_defluente_jirau',
    'nivel_reservatorio_jirau',
    'vazao_defluente_sto_antonio',
]
```

**Disponibilidade:**
- ✅ ONS publica dados horários
- ⚠️ Acesso pode requerer cadastro

---

## 📦 ESTRUTURA DE DATASETS RECOMENDADA

### Dataset Atual (manter):
```
dados_historicos_complementares_portos_oceanicos_v2.parquet
├── 11 portos oceânicos (Santos, Paranaguá, Itaqui, etc.)
├── 2 portos fluviais (Santarém, Barcarena) - só meteorologia
└── Período: 2020-2025
```

### Novo Dataset a Criar:
```
dados_historicos_portos_hibridos_arco_norte.parquet
├── Vila do Conde (PA) - híbrido
├── Santarém (PA) - fluvial
├── Barcarena (PA) - híbrido?
├── Período: 2020-2025
└── Variáveis:
    ├── mare_astronomica_m (só Vila do Conde/Barcarena)
    ├── vazao_rio_m3s (ANA)
    ├── cota_rio_m (ANA)
    ├── vazao_montante_m3s (ANA)
    ├── precip_bacia_7d_mm (CHIRPS)
    ├── precip_bacia_30d_mm (CHIRPS)
    ├── precip_bacia_90d_mm (CHIRPS)
    ├── vento, pressão (INMET/ERA5)
    └── features temporais (mes, fase_ciclo, etc.)
```

### Futuro (Fase 2):
```
dados_historicos_portos_fluviais_puros.parquet
├── Miritituba (PA)
├── Porto Velho (RO)
└── Mesmo schema, mas SEM mare_astronomica
```

---

## 🎓 EXEMPLO DE PIPELINE ML PARA PORTO HÍBRIDO

```python
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

# 1. Carregar dados
df_oceanico = pd.read_parquet('dados_historicos_complementares_portos_oceanicos_v2.parquet')
df_hibrido = pd.read_parquet('dados_historicos_portos_hibridos_arco_norte.parquet')

# 2. Filtrar porto híbrido
df = df_hibrido[df_hibrido['station'] == 'VilaDoCondePA'].copy()

# 3. Features para porto híbrido
features_hibrido = [
    # Maré astronômica (baseline)
    'mare_astronomica_m',

    # Efeitos fluviais (complemento)
    'vazao_rio_m3s',
    'vazao_montante_lag_3d',
    'precip_bacia_30d_mm',
    'precip_bacia_90d_mm',

    # Efeitos meteorológicos
    'wind_speed_10m',
    'wind_direction_10m',
    'pressure_msl',

    # Temporal
    'sin_mes',
    'cos_mes',
]

X = df[features_hibrido]
y = df['nivel_observado_m']  # Target: nível real medido

# 4. Treinar modelo
model = GradientBoostingRegressor(
    n_estimators=500,
    max_depth=5,
    learning_rate=0.01
)

model.fit(X, y)

# 5. Análise de importância
importances = pd.DataFrame({
    'feature': features_hibrido,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(importances)
# Esperado:
# mare_astronomica_m: 0.35 (baseline forte)
# vazao_rio_m3s: 0.25 (complemento fluvial)
# precip_bacia_30d: 0.15
# ...
```

---

## 🎓 EXEMPLO DE PIPELINE ML PARA PORTO FLUVIAL PURO

```python
# Para Santarém (SEM maré astronômica):

features_fluvial = [
    # Vazão (dominante)
    'vazao_local_m3s',
    'vazao_montante_lag_2d',  # Óbidos com 2 dias de lag
    'vazao_montante_lag_3d',

    # Precipitação
    'precip_bacia_30d_mm',
    'precip_bacia_60d_mm',
    'precip_bacia_90d_mm',

    # Sazonalidade
    'sin_mes',
    'cos_mes',
    'fase_ciclo_hidrologico',  # categorical: cheia/vazante/seca/enchente

    # SEM mare_astronomica!
    # SEM wave_height! (não existe em rio)
]

X = df[features_fluvial]
y = df['cota_rio_m']

model.fit(X, y)

# Importância esperada:
# vazao_local: 0.40
# precip_bacia_30d: 0.20
# vazao_montante_lag_2d: 0.15
# sin_mes: 0.10
# ...
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Completar Portos Híbridos Arco Norte

- [ ] **1. Verificar maré em Barcarena**
  - [ ] Consultar DHN: tem tábua de marés para Barcarena?
  - [ ] Se SIM: criar `previsao_mares_barcarena.py`
  - [ ] Se NÃO: documentar como fluvial puro

- [ ] **2. Buscar dados ANA**
  - [ ] Vazão Rio Pará (Vila do Conde): estação 31140000 (Tucuruí)
  - [ ] Vazão Amazonas (Santarém): estação 17050001
  - [ ] Vazão Amazonas montante (Óbidos): estação 17050000
  - [ ] Testar biblioteca `hidrobr` como alternativa ao WebService

- [ ] **3. Buscar dados precipitação CHIRPS**
  - [ ] Download CHIRPS para bacia Amazonas: 2020-2025
  - [ ] Calcular média espacial para sub-bacias
  - [ ] Criar features: acumulado 7d, 30d, 60d, 90d

- [ ] **4. Criar dataset híbrido**
  - [ ] Script: `criar_dataset_portos_hibridos_arco_norte.py`
  - [ ] Combinar: maré (scripts) + ANA + CHIRPS + ERA5
  - [ ] Validar: sem NaNs, período contínuo
  - [ ] Salvar: `dados_historicos_portos_hibridos_arco_norte.parquet`

- [ ] **5. Documentar**
  - [ ] Atualizar README com novo dataset
  - [ ] Criar exemplo de uso ML para híbridos
  - [ ] Explicar diferença híbrido vs fluvial vs oceânico

### Fase 2: Adicionar Portos Fluviais Puros (futuro)

- [ ] **6. Miritituba (PA)**
  - [ ] Buscar dados ANA estação 17320000 (Itaituba)
  - [ ] Adicionar ao dataset fluvial puro

- [ ] **7. Porto Velho (RO)**
  - [ ] Buscar dados ANA estação 15400000
  - [ ] Buscar dados ONS (usinas Jirau/Santo Antônio)
  - [ ] Adicionar ao dataset fluvial puro

- [ ] **8. Modelo ML específico**
  - [ ] Criar script: `modelo_ml_portos_fluviais.py`
  - [ ] NÃO usar análise harmônica
  - [ ] Validação: R² > 0.85 para vazante, > 0.70 para cheia

---

## 📚 REFERÊNCIAS E LINKS ÚTEIS

### Dados ANA:
- **Portal Hidroweb:** https://www.snirh.gov.br/hidroweb/
- **WebService:** http://telemetriaws1.ana.gov.br/ServiceANA.asmx
- **Biblioteca Python:** https://github.com/wallissoncarvalho/hidrobr

### Precipitação:
- **CHIRPS:** https://data.chc.ucsb.edu/products/CHIRPS-2.0/
- **CHIRPS via Google Earth Engine:** https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY

### DHN (Tábuas de Marés):
- **Previsões:** https://www.marinha.mil.br/chm/tabuas-de-mare

### ONS (Usinas):
- **Dados operacionais:** http://sdro.ons.org.br/SDRO/

---

## 🎯 RESUMO FINAL

### ✅ SIM, incorpore dataset fluvial, MAS:

1. **Separe em categorias:**
   - Oceânicos puros (Itaqui, Santos, etc.) → Análise harmônica funciona bem
   - **Híbridos (Vila do Conde, Barcarena)** → Maré + vazão
   - **Fluviais puros (Santarém, Miritituba, Porto Velho)** → Só vazão

2. **Priorize Fase 1:**
   - Complete Vila do Conde e Barcarena (híbridos)
   - São do Arco Norte e já têm maré astronômica calculada
   - Adicionar vazão ANA = ROI alto

3. **Variáveis essenciais:**
   - ⭐⭐⭐⭐⭐ Vazão ANA (local + montante)
   - ⭐⭐⭐⭐⭐ Precipitação bacia (CHIRPS)
   - ⭐⭐⭐⭐ Sazonalidade (sin/cos mês)
   - ⭐⭐⭐⭐ Maré astronômica (só híbridos)
   - ⭐⭐⭐ Meteorologia (vento, pressão)

4. **Modelo ML diferente para cada tipo:**
   - Oceânicos: `y = maré + ml_correcao(meteo)`
   - Híbridos: `y = maré + ml(vazao, precip, meteo)`
   - Fluviais: `y = ml(vazao, precip, sazonalidade)`  [SEM maré!]

### 🚢 Portos mais importantes Arco Norte:

**Já no projeto com maré:**
1. ✅ Itaqui (MA) - completo
2. ✅ Vila do Conde (PA) - falta vazão

**No projeto mas incompleto:**
3. ⚠️ Santarém (PA) - falta vazão + classificar como fluvial
4. ⚠️ Barcarena (PA) - verificar se tem maré + falta vazão

**Fora do projeto (Fase 2):**
5. ❌ Miritituba (PA) - fluvial puro
6. ❌ Porto Velho (RO) - fluvial puro
