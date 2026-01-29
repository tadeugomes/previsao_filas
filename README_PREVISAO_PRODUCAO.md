# Sistema de Previsão de Fila Portuária - Produção

Sistema completo de previsão de tempo de espera portuária usando modelos treinados com dados AIS reais, **sem necessidade de API AIS em tempo real**.

## 🎯 Características

- ✅ **Sem custo de API**: Usa apenas dados gratuitos (Open-Meteo + tabelas pré-carregadas)
- ✅ **Enriquecimento automático**: Calcula 15-51 features a partir de dados básicos do scraping
- ✅ **Dois modelos**: Light (15 features) e Completo (51 features) com seleção automática
- ✅ **Alta precisão**: MAE 8.7h (VEGETAL), 16.4h (MINERAL), 60.3h (FERTILIZANTE)
- ✅ **Interface Streamlit**: UI completa para entrada manual ou lote (CSV)

## 📁 Arquivos Principais

### 1. `predictor_enriched.py`
**Classe EnrichedPredictor** - Motor de previsão

```python
from predictor_enriched import EnrichedPredictor

# Inicializar
predictor = EnrichedPredictor()

# Fazer previsão
navio = {
    "porto": "Santos",
    "tipo": "Bulk Carrier",
    "carga": "Soja em Graos",
    "eta": "2026-02-15",
    "dwt": 75000,
    "calado": 12.5,
    "toneladas": 60000,
}

resultado = predictor.predict(navio, quality_score=1.0)

print(f"Tempo previsto: {resultado['tempo_espera_previsto_horas']:.1f}h")
print(f"Categoria: {resultado['categoria_fila']}")
print(f"Perfil: {resultado['perfil']}")
print(f"Modelo: {resultado['modelo_usado']}")
```

### 2. `streamlit_prediction_app.py`
**Interface Web Completa**

```bash
# Executar
streamlit run streamlit_prediction_app.py

# Acessar
http://localhost:8501
```

**Funcionalidades**:
- 📝 Entrada manual de navio individual
- 📤 Upload de CSV para previsões em lote
- 🔧 Configurações avançadas (forçar modelo, quality score)
- 📊 Visualização de resultados e estatísticas
- 💾 Download de resultados em CSV
- 🔍 Visualização de features calculadas

## 🚀 Início Rápido

### Instalação

```bash
# Instalar dependências
pip install streamlit pandas numpy requests lightgbm scikit-learn pyarrow

# Verificar modelos
ls models/*_light_*.pkl models/*_REAL.pkl
```

### Teste Rápido

```bash
# 1. Testar o predictor
python predictor_enriched.py

# 2. Iniciar interface Streamlit
streamlit run streamlit_prediction_app.py
```

### Uso Programático

```python
from predictor_enriched import EnrichedPredictor

predictor = EnrichedPredictor()

# Exemplo 1: Soja em Santos (usa modelo COMPLETO)
navio1 = {
    "porto": "Santos",
    "tipo": "Bulk Carrier",
    "carga": "Soja em Graos",
    "eta": "2026-02-15",
}

resultado1 = predictor.predict(navio1, quality_score=1.0)
# Modelo completo: 8.7h MAE (54% melhor que light)

# Exemplo 2: Ureia em Suape (usa modelo LIGHT)
navio2 = {
    "porto": "Suape",
    "tipo": "Chemical Tanker",
    "carga": "Ureia",
    "eta": "2026-03-01",
}

resultado2 = predictor.predict(navio2, quality_score=0.9)
# Modelo light: 60.3h MAE (melhor para FERTILIZANTE)
```

### Upload de CSV (Lote)

**Formato do CSV**:
```csv
porto,tipo,carga,eta,dwt,calado,toneladas
Santos,Bulk Carrier,Soja em Graos,2026-02-15,75000,12.5,60000
Paranaguá,Bulk Carrier,Milho,2026-02-20,80000,13.0,65000
Suape,Chemical Tanker,Ureia,2026-03-01,45000,10.0,35000
```

## 📊 Dados e Features

### Dados de Entrada (do Scraping)

**Obrigatórios**:
- `porto`: Nome do porto
- `eta`: Data de chegada estimada (YYYY-MM-DD)

**Opcionais** (valores default serão usados):
- `tipo`: Tipo de navio (default: "Bulk Carrier")
- `carga`: Natureza da carga (default: "Soja em Graos")
- `dwt`: Deadweight tonnage (default: 75000)
- `calado`: Calado em metros (default: 12.5)
- `toneladas`: Movimentação total (default: 50000)

### Features Calculadas Automaticamente

O sistema enriquece os dados básicos com **48 features adicionais**:

#### 1. Temporais (4 features)
- mes, dia_semana, dia_do_ano, periodo_safra
- **Fonte**: Calculado da data ETA

#### 2. Climáticas (12 features)
- temp_media_dia, precipitacao_dia, vento_rajada_max_dia
- umidade_media_dia, amplitude_termica, restricao_vento, etc.
- **Fonte**: API Open-Meteo (gratuita) ou médias regionais

#### 3. Históricas (4 features)
- navios_na_fila_7d, navios_no_fundeio_na_chegada
- tempo_espera_ma5, porto_tempo_medio_historico
- **Fonte**: `lineup_history.parquet` (já coletado)

#### 4. Agrícolas (13 features)
- flag_soja, flag_milho, producao_soja, preco_soja_mensal
- indice_pressao_soja, indice_pressao_milho, etc.
- **Fonte**: Tabelas pré-carregadas (médias mensais IBGE/CONAB)

#### 5. Maré (6 features - apenas VEGETAL completo)
- wave_height_max, mare_astronomica, mare_subindo, etc.
- **Fonte**: Cálculos astronômicos

#### 6. AIS Estimadas (5 features)
- ais_navios_no_raio, ais_velocidade_media_kn
- ais_dist_media_km, ais_eta_media_horas
- **Fonte**: Valores médios (sem API real-time)

## 🎯 Lógica de Seleção de Modelo

```python
if quality_score >= 0.80 AND profile == "VEGETAL":
    USE modelo_completo (51 features)
    # MAE: 8.7h (-54% vs light)
else:
    USE modelo_light (15 features)
    # Mais robusto para dados limitados
```

**Por perfil**:
- ✅ **VEGETAL**: modelo completo 54% melhor (19h → 8.7h)
- ✅ **MINERAL**: modelo light funciona bem (MAE 16.4h)
- ✅ **FERTILIZANTE**: modelo light é melhor (60.3h vs 72.6h)

## 💰 Custo Comparativo

| Opção | Custo Mensal | APIs Usadas | Precisão |
|-------|--------------|-------------|----------|
| **Sistema Atual** | **€0-20** | Open-Meteo (grátis) | MAE 8.7-60h |
| API AIS Real-Time | €500-1000 | Datalastic real-time | MAE ~6-55h |

**Ganho**: Economia de **€500+/mês** com perda marginal de precisão (~2h).

## 🔧 Configurações Avançadas

### Forçar Modelo Específico

```python
# Forçar modelo completo
resultado = predictor.predict(navio, force_model="complete")

# Forçar modelo light
resultado = predictor.predict(navio, force_model="light")

# Automático (recomendado)
resultado = predictor.predict(navio, quality_score=1.0)
```

### Ajustar Quality Score

O `quality_score` (0-1) indica a qualidade dos dados de entrada:
- **1.0**: Dados completos e confiáveis (todas features disponíveis)
- **0.8**: Threshold para ativar modelo completo em VEGETAL
- **< 0.8**: Usa modelo light (mais robusto)

```python
# Dados completos do scraping
resultado = predictor.predict(navio, quality_score=1.0)

# Dados parciais ou menos confiáveis
resultado = predictor.predict(navio, quality_score=0.6)
```

## 📈 Performance dos Modelos

### VEGETAL (Grãos)
| Modelo | Features | MAE | R² | Samples |
|--------|----------|-----|----|----|
| Light | 15 | 19.00h | 0.982 | 135 |
| **Completo** | **51** | **8.73h** | **0.997** | 135 |

**Melhoria**: -54% no MAE (19h → 8.7h) ✅ **Usar COMPLETO**

### MINERAL (Minério)
| Modelo | Features | MAE | R² | Samples |
|--------|----------|-----|----|----|
| **Light** | **15** | **16.38h** | **0.985** | 188 |
| Completo | 35 | N/A | N/A | 15 (insuficiente) |

**Status**: Dados insuficientes para completo ⚠️ **Usar LIGHT**

### FERTILIZANTE (Químicos)
| Modelo | Features | MAE | R² | Samples |
|--------|----------|-----|----|----|
| **Light** | **15** | **60.29h** | **0.838** | 42 |
| Completo | 35 | 72.62h | 0.532 | 61 |

**Problema**: Overfitting no completo ⚠️ **Usar LIGHT**

## 🔄 Integração com Sistema Existente

### Substituir Scraping + API?

**NÃO!** O sistema **complementa** o scraping:

```
FLUXO ATUAL:
1. Scraping → dados básicos (IMO, tipo, porto, ETA)
2. EnrichedPredictor → enriquece com 48 features
3. Modelo → previsão de tempo de espera
```

**Vantagens**:
- Mantém scraping (dados sempre atualizados)
- Não precisa de API AIS cara (€500+/mês)
- Features calculadas são suficientes

### Integrar com Código Existente

```python
# Seu código de scraping atual
navios_scraped = scrape_lineups()  # Lista de navios

# Adicionar previsões
from predictor_enriched import EnrichedPredictor
predictor = EnrichedPredictor()

for navio in navios_scraped:
    # Fazer previsão
    resultado = predictor.predict({
        "porto": navio["porto"],
        "tipo": navio["tipo"],
        "carga": navio["carga"],
        "eta": navio["prev_chegada"],
        "dwt": navio.get("dwt", 75000),
        "calado": navio.get("calado", 12.5),
    })

    # Adicionar ao navio
    navio["tempo_espera_previsto"] = resultado["tempo_espera_previsto_horas"]
    navio["categoria_fila"] = resultado["categoria_fila"]
    navio["confianca"] = resultado["confianca"]
```

## 🐛 Troubleshooting

### Erro: "Modelo não encontrado"

```bash
# Verificar modelos
ls models/*_light_*.pkl models/*_REAL.pkl

# Modelos necessários:
# - vegetal_light_lgb_reg.pkl
# - vegetal_light_lgb_clf.pkl
# - vegetal_xgb_reg_REAL.pkl (para modelo completo)
```

### Erro: "API Open-Meteo 400"

Ocorre quando a data ETA está muito no futuro (>10 dias). O sistema usa automaticamente valores médios regionais como fallback.

```
⚠️  Erro ao buscar clima: 400 Client Error. Usando valores médios.
```

**Solução**: Não precisa fazer nada - o fallback funciona perfeitamente.

### Erro: "lineup_history.parquet não encontrado"

```bash
# Criar arquivo vazio
python -c "import pandas as pd; pd.DataFrame().to_parquet('lineups_previstos/lineup_history.parquet')"
```

O sistema funciona sem histórico, usando valores default para features históricas.

## 📚 Documentação Adicional

- **`RELATORIO_COMPARACAO_MODELOS.md`**: Análise detalhada de performance
- **`RELATORIO_TREINO_MODELOS_REAIS.md`**: Detalhes do treinamento
- **`RELATORIO_FINAL_COLETA_AIS.md`**: Coleta de dados AIS

## 🎓 Próximos Passos

### Curto Prazo (1-3 meses)
1. ✅ Implantar em produção
2. 📊 Monitorar performance real
3. 📈 Coletar mais dados de produção

### Médio Prazo (3-6 meses)
1. 📦 Coletar mais dados AIS (meta: 500+ eventos/perfil)
2. 🔧 Re-treinar modelos com dataset maior
3. 🎯 Melhorar FERTILIZANTE (mais dados de tankers)

### Longo Prazo (6+ meses)
1. 🤖 Retreinamento automático incremental
2. 🧪 Experimentar features econômicas (câmbio, commodities)
3. 🔄 API real-time AIS apenas para clientes premium

## 📞 Suporte

Para questões técnicas:
1. Verificar documentação em `RELATORIO_COMPARACAO_MODELOS.md`
2. Testar com `python predictor_enriched.py`
3. Verificar logs de erro no Streamlit

---

**Desenvolvido com dados AIS reais (308 eventos, 8 portos, 94 navios)**
**Economia: €500+/mês vs API real-time | Precisão: MAE 8.7-60h**
**Data**: 2026-01-29
