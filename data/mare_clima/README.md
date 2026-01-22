# Previsão de Marés - Brasil

Scripts para cálculo de preamares e baixa-mares de portos brasileiros utilizando constantes harmônicas oficiais da Marinha do Brasil (DHN - Diretoria de Hidrografia e Navegação).

## Portos Disponíveis

### 1. Porto de Itaqui (MA)
- **Ficha:** 30110
- **Tipo de Maré:** Macromaré (amplitude > 4m)
- **Nível Médio (NM):** 3.43 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_itaqui.py`
- **Saída:** `itaqui_extremos_2020_2026.csv`

### 2. Terminal Gás Sul - São Francisco do Sul (SC)
- **Ficha:** 60266 (F-41)
- **Tipo de Maré:** Micro-maré (amplitude < 2m)
- **Nível Médio (NM):** 1.11 m
- **Constantes:** 27 componentes harmônicas
- **Script:** `previsao_mares_tgs.py`
- **Saída:** `tgs_extremos_2020_2026.csv`

### 3. Porto de Santos (SP)
- **Carta:** 1712 - Ficha 50231 (TIPLAM)
- **Tipo de Maré:** Micro-maré (amplitude < 2m)
- **Nível Médio (NM):** 0.736 m
- **Constantes:** 28 componentes harmônicas
- **Script:** `previsao_mares_santos.py`
- **Saída:** `santos_extremos_2020_2026.csv`
- **⚠️ Observação:** Efeitos meteorológicos (ressacas) podem elevar o nível em +1m

### 4. Porto do Rio Grande (RS)
- **Carta:** 2101 - Ficha 60380 (F-41)
- **Tipo de Maré:** Maré Mista (micro-amplitude < 0.5m)
- **Nível Médio (NM):** 0.858 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_riograande.py`
- **Saída:** `riograande_extremos_2020_2026.csv`
- **Estabelecimento de Porto:** 7h 28m

### 5. Porto de Paranaguá (PR)
- **Ficha:** 60141
- **Tipo de Maré:** Micro-maré com distorção (amplitude < 2m)
- **Nível Médio (NM):** 0.937 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_paranagua.py`
- **Saída:** `paranagua_extremos_2020_2026.csv`
- **⚠️ Observação:** Distorção por águas rasas (M4, MS4) e influência meteorológica

### 6. Ilha da Paz - São Francisco do Sul (SC)
- **Ficha:** 60208
- **Tipo de Maré:** Micro-maré (amplitude < 2m)
- **Nível Médio (NM):** 0.781 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_ilhadapaz.py`
- **Saída:** `ilhadapaz_extremos_2020_2026.csv`
- **Localização:** Baía da Babitonga, Santa Catarina
- **Estação Sentinela:** Referência para Itapoá e São Francisco do Sul
- **Nota:** Serve como previsão para ambos os portos da região

### 7. Vila do Conde - Barcarena (PA)
- **Ficha:** 10566
- **Tipo de Maré:** Grande amplitude com forte distorção fluvial (~3m)
- **Nível Médio (NM):** 2.15 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_viladoconde.py`
- **Saída:** `viladoconde_extremos_2020_2026.csv`
- **Localização:** Baía de Marajó - Foz do Rio Amazonas
- **⚠️ Observação:** Forte influência fluvial (Amazonas/Tocantins) e distorção de águas rasas
- **Nota:** Segunda maior amplitude do projeto, assimetria pronunciada (sobe mais rápido que desce)

### 8. Barcarena (PA) ⭐
- **Referência:** Vila do Conde (Ficha 10566 - DHN)
- **Tipo de Maré:** Semidiurna com grande amplitude (~3m)
- **Nível Médio (NM):** 1.71 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_barcarena.py`
- **Saída:** `barcarena_extremos_2020_2026.csv`
- **Localização:** Rio Pará, próximo a Vila do Conde (~30-40 km)
- **⚠️ Porto Híbrido:** Maré astronômica significativa + Vazão do Rio Pará
- **Confirmação DHN:** Influência de maré confirmada
- **Para ML:** Combinar maré astronômica + vazão ANA + meteorologia INMET
- **Nota:** Componentes de águas rasas (M4, MS4) importantes devido à morfologia fluvial

### 9. Suape (PE) ⭐
- **Referência:** Dados DHN
- **Tipo de Maré:** Semidiurna (amplitude ~2m)
- **Nível Médio (NM):** 1.50 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_suape.py`
- **Saída:** `suape_extremos_2020_2026.csv`
- **Localização:** Estuário - Maior complexo portuário do Nordeste
- **⚠️ Porto Estuarino:** Influência de ondas do Atlântico significativa
- **Para ML:** Combinar maré astronômica + meteorologia + ondas (Dataset 2 v2)
- **Nota:** Hub industrial e energético de Pernambuco

### 10. Recife (PE) ⭐
- **Referência:** Dados DHN
- **Tipo de Maré:** Semidiurna (amplitude ~1.9m)
- **Nível Médio (NM):** 1.45 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_recife.py`
- **Saída:** `recife_extremos_2020_2026.csv`
- **Localização:** Estuário do Rio Capibaribe - Porto histórico
- **⚠️ Porto Estuarino:** Águas rasas significativas (M4, MS4)
- **Para ML:** Combinar maré astronômica + meteorologia + ondas (Dataset 2 v2)
- **Nota:** Porto histórico de Pernambuco

### 11. Salvador (BA) ⭐
- **Referência:** Dados DHN
- **Tipo de Maré:** Semidiurna (amplitude ~1.7m)
- **Nível Médio (NM):** 1.35 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_salvador.py`
- **Saída:** `salvador_extremos_2020_2026.csv`
- **Localização:** Baía de Todos os Santos
- **⚠️ Porto em Baía:** Águas protegidas mas com influência oceânica
- **Para ML:** Combinar maré astronômica + meteorologia + ondas (Dataset 2 v2)
- **Nota:** Principal porto da Bahia

### 12. Pecém (CE) ⭐
- **Referência:** Dados DHN
- **Tipo de Maré:** Semidiurna (amplitude ~2.3m)
- **Nível Médio (NM):** 1.55 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_pecem.py`
- **Saída:** `pecem_extremos_2020_2026.csv`
- **Localização:** Porto oceânico - Hub industrial e energético do Ceará
- **⚠️ Porto Oceânico:** Maior amplitude M2 entre os portos do Nordeste (1.123m)
- **Para ML:** Combinar maré astronômica + meteorologia + ondas (Dataset 2 v2)
- **Nota:** Componentes de águas rasas menores (porto oceânico)

### 13. Paranaguá Cais Oeste I (PR)
- **Ficha:** 60151
- **Tipo de Maré:** Micro-maré com distorção (amplitude < 2m)
- **Nível Médio (NM):** 0.916 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_paranagua_cais_oeste.py`
- **Saída:** `paranagua_cais_oeste_extremos_2020_2026.csv`
- **Localização:** Interior da Baía de Paranaguá (mais para oeste)
- **Par com:** Paranaguá Cais Leste/TCP (Ficha 60141)
- **⚠️ Observação:** Complementa Cais Leste para modelagem de gradiente e propagação no canal
- **Para ML:** Lag temporal entre Cais Oeste e Cais Leste permite prever velocidade de propagação da onda de maré

### 14. Porto de Antonina (PR)
- **Ficha:** 60110
- **Tipo de Maré:** Micro-maré com amplificação por efeito funil
- **Nível Médio (NM):** 1.11 m
- **Constantes:** 35 componentes harmônicas
- **Script:** `previsao_mares_antonina.py`
- **Saída:** `antonina_extremos_2020_2026.csv`
- **Localização:** Fundo da Baía de Paranaguá (mais interior)
- **Conjunto completo:** Cais Leste → Cais Oeste I → Antonina
- **⚠️ Observação:** Efeito funil amplifica a maré (M2: 0.536m > Cais Leste: 0.470m)
- **⚠️ Atraso da onda:** Fase M2: 100.2° (vs Cais Leste: 85.5°) = ~14.7° de diferença
- **Para ML:** Amplificação + lag temporal permitem modelar como a maré se propaga e intensifica ao longo da baía

## Descrição

Este projeto calcula os extremos de maré (preamares e baixa-mares) para diferentes portos brasileiros no período de 2020 a 2026, utilizando análise harmônica de componentes de maré.

### Constantes Harmônicas

Os modelos utilizam constantes harmônicas incluindo:
- **Principais semidiurnas:** M2, S2, N2, K2
- **Principais diurnas:** K1, O1, P1, Q1
- **Componentes de águas rasas:** M4, MS4, M6, MK3, S4, MN4
- **Componentes de longo período:** MF, MM, SSA, SA, MSF

### Diferenças Regionais

**Porto de Itaqui (MA):**
- Macromaré equatorial com grandes amplitudes (até 7 metros)
- Fortemente influenciado pela proximidade do equador
- Variação significativa entre marés de sizígia e quadratura

**Terminal Gás Sul (SC):**
- Micro-maré com amplitudes pequenas (geralmente 0.4m a 1.8m)
- Influência meteorológica proporcionalmente maior
- Variações mais sutis e regulares

**Porto de Santos (SP):**
- Micro-maré com amplitudes pequenas (geralmente 0.2m a 1.5m)
- **Forte influência meteorológica:** ressacas podem adicionar +1m ou mais
- Frentes frias e ventos sul causam sobre-elevação significativa
- Previsões astronômicas devem ser combinadas com previsões meteorológicas

**Porto do Rio Grande (RS):**
- Maré mista com amplitudes muito pequenas (< 0.5m)
- Menor amplitude de maré entre todos os portos do projeto
- Localizado em estuário, sofre influência de vazão fluvial
- Estabelecimento de porto de 7h 28m

**Sistema Completo da Baía de Paranaguá (PR):**
- Micro-maré com distorção significativa (amplitude ~2m)
- **Forte distorção de águas rasas:** constantes M4, MS4, M6 significativas
- A forma da onda de maré se deforma ao entrar na Baía de Paranaguá
- **Influência meteorológica:** ventos sul causam sobre-elevação
- **Três estações disponíveis formando gradiente espacial:**
  - **Cais Leste/TCP (Ficha 60141):** NM = 0.937m, entrada da baía, M2 = 0.470m, Fase = 85.5°
  - **Cais Oeste I (Ficha 60151):** NM = 0.916m, meio da baía, M2 = 0.470m, Fase = 85.5°
  - **Antonina (Ficha 60110):** NM = 1.11m, fundo da baía, M2 = 0.536m, Fase = 100.2°
- **Efeito funil:** A baía estreita em direção a Antonina, amplificando a maré (M2 aumenta 14% de Cais Leste para Antonina)
- **Gradiente de fase:** ~14.7° de diferença entre Cais Leste e Antonina representa o tempo de propagação da onda ao longo da baía
- **Para ML:** Conjunto único permitindo modelar amplificação, atenuação, atraso e distorção da onda de maré em um estuário

**Ilha da Paz - São Francisco do Sul (SC):**
- Micro-maré oceânica (amplitude ~1.5m)
- Localizada na Baía da Babitonga
- Comportamento similar ao Terminal Gás Sul (mesma região)
- Menor influência de águas rasas comparado a Paranaguá
- **Estação sentinela:** Serve de referência para portos próximos (Itapoá, São Francisco do Sul)
- **Para ML:** O lag temporal entre Ilha da Paz e portos internos da baía é feature forte para prever propagação da onda de maré

**Vila do Conde - Barcarena (PA):**
- Grande amplitude com forte distorção (~3m - segunda maior do projeto)
- **Localização fascinante:** Foz do Rio Amazonas (Baía de Marajó)
- **Influência fluvial extrema:** Gigantesco volume de água doce do Amazonas/Tocantins
- **Distorção de águas rasas pronunciada:** M4 (0.054m) e M6 (0.021m) muito significativas
- **Assimetria:** Maré sobe mais rápido do que desce
- **Para ML:** Vazão fluvial (Amazonas/Tocantins) é feature crítica para desvios sazonais
- **Dois portos próximos:**
  - **Vila do Conde:** NM = 2.15m, Ficha 10566
  - **Barcarena ⭐:** NM = 1.71m, mesmas características (usa Vila do Conde como referência DHN)

## Instalação

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

Ou instalar manualmente:

```bash
pip install pandas numpy
```

## Uso

### Opção 1: Executar scripts diretamente

**Porto de Itaqui:**
```bash
python previsao_mares_itaqui.py
```

**Terminal Gás Sul:**
```bash
python previsao_mares_tgs.py
```

**Porto de Santos:**
```bash
python previsao_mares_santos.py
```

**Porto do Rio Grande:**
```bash
python previsao_mares_riograande.py
```

**Porto de Paranaguá:**
```bash
python previsao_mares_paranagua.py
```

**Porto de Paranaguá - Cais Oeste I:**
```bash
python previsao_mares_paranagua_cais_oeste.py
```

**Porto de Antonina:**
```bash
python previsao_mares_antonina.py
```

**Ilha da Paz:**
```bash
python previsao_mares_ilhadapaz.py
```

**Vila do Conde:**
```bash
python previsao_mares_viladoconde.py
```

**Barcarena:**
```bash
python previsao_mares_barcarena.py
```

**Suape:**
```bash
python previsao_mares_suape.py
```

**Recife:**
```bash
python previsao_mares_recife.py
```

**Salvador:**
```bash
python previsao_mares_salvador.py
```

**Pecém:**
```bash
python previsao_mares_pecem.py
```

### Opção 2: Usar script auxiliar interativo

```bash
chmod +x run.sh
./run.sh
```

O script auxiliar permite escolher qual porto você deseja calcular.

## Saída

Cada script gera:

1. **Console:** Exibe as primeiras 20 previsões e resumo estatístico
2. **Arquivo CSV:** Com todas as previsões de extremos de maré

### Formato do CSV

| Data_Hora | Altura_m | Evento |
|-----------|----------|--------|
| 2020-01-01 00:15:00 | 5.87 | Preamar |
| 2020-01-01 06:30:00 | 0.99 | Baixa-mar |

### Estrutura dos Dados

- **Data_Hora:** Timestamp do evento de maré (fuso horário UTC)
- **Altura_m:** Altura da maré em metros (já inclui o nível médio)
- **Evento:** Tipo do evento ("Preamar" ou "Baixa-mar")

## Arquivos do Projeto

```
mares/
├── previsao_mares_itaqui.py              # Script Porto de Itaqui
├── previsao_mares_tgs.py                 # Script Terminal Gás Sul
├── previsao_mares_santos.py              # Script Porto de Santos
├── previsao_mares_riograande.py          # Script Porto do Rio Grande
├── previsao_mares_paranagua.py           # Script Porto de Paranaguá (Cais Leste/TCP)
├── previsao_mares_paranagua_cais_oeste.py # Script Paranaguá Cais Oeste I
├── previsao_mares_antonina.py            # Script Porto de Antonina
├── previsao_mares_ilhadapaz.py           # Script Ilha da Paz
├── previsao_mares_viladoconde.py         # Script Vila do Conde
├── previsao_mares_barcarena.py           # Script Barcarena
├── previsao_mares_suape.py               # Script Suape (PE)
├── previsao_mares_recife.py              # Script Recife (PE)
├── previsao_mares_salvador.py            # Script Salvador (BA)
├── previsao_mares_pecem.py               # Script Pecém (CE)
├── portos_brasil_historico_portos_hibridos.parquet  # Dataset 1: Portos estuarinos Sul (2020-2024)
├── dados_historicos_complementares_portos_oceanicos_v2.parquet  # Dataset 2 v2: Oceanográficos (2020-2025, 13 portos)
├── dados_historicos_portos_hibridos_arco_norte_v2.parquet  # Dataset 3: Arco Norte híbridos+fluviais (2020-2025, 3 portos)
├── exemplo_uso_dataset_historico.py      # Script de exemplo: Datasets 1 e 2
├── exemplo_uso_dataset_arco_norte.py     # Script de exemplo: Dataset 3 (Arco Norte)
├── RECOMENDACOES_PORTOS_FOZ_RIOS.md      # Análise: portos em foz (com maré)
├── ANALISE_PORTOS_FLUVIAIS.md            # Análise: portos fluviais (sem maré)
├── RECOMENDACOES_PORTOS_ARCO_NORTE.md    # Recomendações: Arco Norte e granéis sólidos
├── requirements.txt                       # Dependências Python
├── run.sh                                 # Script auxiliar de execução
└── README.md                              # Esta documentação
```

## Requisitos

- Python 3.7+
- pandas >= 1.3.0
- numpy >= 1.20.0

## Observações Técnicas

### Precisão e Limitações

**Previsões Astronômicas (este projeto):**
- ✅ Baseadas exclusivamente em componentes astronômicas (Lua, Sol)
- ❌ **NÃO incluem** efeitos meteorológicos (vento, pressão atmosférica)
- ❌ **NÃO incluem** efeitos fluviais (vazão de rios)
- ❌ **NÃO incluem** efeitos de ondas (ressacas)

**Quando usar este projeto:**
- ✅ Portos oceânicos e costeiros (baseline confiável)
- ✅ Portos estuarinos como **baseline** + correções de ML
- ✅ Estudo de propagação de marés em baías
- ✅ Feature engineering para modelos de ML

**Quando NÃO usar (ou usar com muito cuidado):**
- ⚠️ Portos puramente fluviais (ex: Manaus) - maré astronômica é insignificante
- ⚠️ Períodos de ressaca (Santos, Rio de Janeiro) - erro pode ser >1m
- ⚠️ Períodos de cheia na Amazônia (Vila do Conde) - vazão domina
- ⚠️ Vento sul forte (Rio Grande, Santos) - sobre-elevação significativa

**Para navegação oficial:** Sempre consulte as Tábuas de Marés da DHN

### Fuso Horário
- Os horários são calculados em UTC
- Porto de Itaqui: UTC-3
- Terminal Gás Sul: UTC-3
- Porto de Santos: UTC-3
- Porto do Rio Grande: UTC-3
- Porto de Paranaguá (todos): UTC-3
- Porto de Antonina: UTC-3
- Ilha da Paz: UTC-3
- Vila do Conde: UTC-3

### Período de Validade
- Previsões calculadas para 2020-2026
- As constantes harmônicas são atualizadas periodicamente pela DHN

### Como Identificar se um Porto tem Maré Astronômica Significativa

**Indicadores de que o porto TEM maré astronômica (análise harmônica é válida):**
- ✅ Amplitude M2 > 0.05m (quanto maior, mais confiável)
- ✅ Componentes semidiurnas (M2, S2) são as maiores do espectro
- ✅ Localizado < 100km da costa (varia por estuário)
- ✅ DHN publica Tábua de Marés para o local
- ✅ Variação de nível tem período dominante de ~12.4h

**Indicadores de porto PURAMENTE fluvial (análise harmônica NÃO funciona):**
- ❌ Amplitude M2 < 0.01m (praticamente zero)
- ❌ Localizado muito longe da costa (>200km rio acima)
- ❌ Variação dominante é sazonal (meses, não horas)
- ❌ DHN não publica tábuas de marés para o local
- ❌ Variação de nível correlaciona com precipitação/vazão, não com fase da Lua

**Exemplos de portos puramente fluviais no Brasil:**
- Manaus (AM) - Variação ~10-15m anual, 100% fluvial
- Porto Velho (RO) - Variação fluvial
- Corumbá (MS) - Variação fluvial (Pantanal)

Para esses portos, você precisa de um **modelo hidrológico**, não harmônico.

### Expansão para Portos Fluviais e Híbridos (Arco Norte)

**⚠️ Importante:** Este projeto foca primariamente em **marés astronômicas**. Portos puramente fluviais (Manaus, Porto Velho, Santarém, Miritituba) têm dinâmica dominada por vazão de rios, não por marés.

**🚢 Classificação de Portos:**

1. **Oceânicos puros** (análise harmônica funciona muito bem):
   - Itaqui (MA), Santos (SP), Suape (PE), Pecém (CE), Salvador (BA), etc.
   - Maré astronômica é o componente dominante
   - Scripts de previsão deste projeto: ✅ Alta precisão

2. **Híbridos estuarinos** (maré + vazão fluvial):
   - Vila do Conde (PA), Rio Grande (RS), Paranaguá (PR), Antonina (PR)
   - Têm maré astronômica significativa + influência de rio
   - Necessitam: Análise harmônica (baseline) + ML com vazão fluvial

3. **Fluviais puros** (apenas vazão, sem maré):
   - Santarém (PA), Barcarena (PA), Miritituba (PA), Porto Velho (RO), Manaus (AM)
   - Maré astronômica < 5cm (desprezível)
   - Necessitam: Modelo hidrológico puro (vazão + precipitação)

**📊 Arco Norte e Granéis Sólidos:**

Para orientação completa sobre incorporar portos fluviais/híbridos do Arco Norte (importantes para escoamento de grãos) ao projeto, incluindo:
- ✅ Recomendação de incorporar ou não dataset fluvial
- ✅ Ranking de portos por importância para granéis sólidos
- ✅ Variáveis necessárias (vazão ANA, precipitação CHIRPS, etc.)
- ✅ Pipeline de ML específico para cada tipo de porto
- ✅ Checklist de implementação em fases

**Consulte:** [`RECOMENDACOES_PORTOS_ARCO_NORTE.md`](RECOMENDACOES_PORTOS_ARCO_NORTE.md)

**Status atual dos portos do Arco Norte neste projeto:**
- ✅ **Itaqui (MA):** Completo (oceânico, com script de maré)
- ✅ **Vila do Conde (PA):** Parcial (híbrido, tem maré mas falta vazão ANA)
- ⚠️ **Santarém (PA):** Incompleto (fluvial, só meteorologia, falta vazão)
- ⚠️ **Barcarena (PA):** Incompleto (híbrido?, precisa verificar maré + adicionar vazão)
- ❌ **Miritituba (PA):** Não incluído (fluvial puro)
- ❌ **Porto Velho (RO):** Não incluído (fluvial puro)

## Aplicações em Machine Learning

### Ilha da Paz como Estação Sentinela

A Ilha da Paz funciona como uma **estação sentinela** para a região da Baía da Babitonga:

**Portos de referência:**
- Itapoá (SC)
- São Francisco do Sul (SC)
- Outros portos internos da Baía da Babitonga

**Feature de lag temporal:**
A diferença de tempo entre o pico da maré na Ilha da Paz (oceânica) e o pico dentro da baía é uma característica muito forte para prever a propagação da onda de maré. Em modelos de ML, use:

```python
# Exemplo de feature engineering
lag_ilha_porto = tempo_preamar_porto_interno - tempo_preamar_ilha_da_paz
```

### Outras Aplicações de ML

**Sistema Completo da Baía de Paranaguá - Modelagem de Propagação e Amplificação:**

Ter três estações em Paranaguá (Cais Leste, Cais Oeste I, e Antonina) permite modelar o gradiente completo de pressão, amplificação por efeito funil, e o tempo de deslocamento da massa de água ao longo de toda a baía:

```python
# Features de lag temporal entre estações (propagação da onda)
lag_leste_oeste = tempo_preamar_oeste - tempo_preamar_leste
lag_oeste_antonina = tempo_preamar_antonina - tempo_preamar_oeste
lag_total = tempo_preamar_antonina - tempo_preamar_leste

# Features de gradiente de altura
gradiente_leste_oeste = altura_leste - altura_oeste
gradiente_oeste_antonina = altura_oeste - altura_antonina

# Feature de amplificação (efeito funil)
# M2 aumenta de 0.470m (Cais Leste) para 0.536m (Antonina) = 14% de amplificação
fator_amplificacao = amplitude_antonina / amplitude_cais_leste

# Feature de diferença de fase (usando M2)
# Fase Antonina: 100.2° vs Fase Cais Leste: 85.5° = 14.7° de atraso
diferenca_fase_M2 = fase_M2_antonina - fase_M2_cais_leste
# Converter para tempo: 14.7° / (360°/12.42h) ≈ 30 minutos de atraso

# Velocidade de propagação da onda de maré na baía
velocidade_propagacao = distancia_total_baia / lag_total
```

**Aplicações práticas:**
- Prever condições de corrente em qualquer ponto da baía
- Otimizar janelas de manobra para navios de grande porte em diferentes portos
- Estimar tempo de chegada da maré em diferentes pontos (Paranaguá → Antonina)
- Corrigir efeitos de atrito, distorção e amplificação ao longo da baía
- Modelar efeito funil: como o estreitamento da baía amplifica a maré
- Prever inundações no fundo da baía (Antonina) com base em observações na entrada (Cais Leste)

---

## Variáveis Complementares para Machine Learning

As previsões astronômicas (fornecidas por este projeto) são apenas o **baseline**. Para portos estuarinos e costeiros, você precisa de variáveis adicionais para capturar desvios causados por rios, vento, pressão e ondas.

### 📊 Classificação dos Portos e Variáveis Necessárias

#### **Tipo 1: Portos Oceânicos/Costeiros**
**Exemplos:** Itaqui (MA), Santos (SP), Ilha da Paz (SC)

**Variáveis necessárias:**

| Variável | Importância | Fonte de Dados (Brasil) | Detalhes |
|----------|-------------|-------------------------|----------|
| **Maré astronômica** | ⭐⭐⭐⭐⭐ | Este projeto | Baseline principal |
| **Vento (vel. e dir.)** | ⭐⭐⭐⭐ | INMET, Copernicus Marine | Ventos sul causam sobre-elevação |
| **Pressão atmosférica** | ⭐⭐⭐ | INMET | Efeito de barômetro invertido (~1cm/hPa) |
| **Altura de onda** | ⭐⭐⭐ | Copernicus Marine, SMC-Brasil | Ressacas podem adicionar +1m |
| **Período de onda** | ⭐⭐ | Copernicus Marine | Ondas longas penetram mais no porto |

**Exemplo: Porto de Santos**
```python
features = {
    'mare_astronomica': altura_prevista_harmonica,      # Este projeto
    'vento_sul_intensidade': max(vel_vento_sul_48h),   # INMET
    'vento_sul_persistencia': horas_vento_sul,         # INMET
    'pressao_atm': pressao_atual - pressao_media,      # INMET (anomalia)
    'altura_onda_significativa': Hs,                    # Copernicus/SMC
    'periodo_onda': Tp,                                 # Copernicus
    'frente_fria': booleano_frente_proximas_48h,      # CPTEC/INPE
}
```

---

#### **Tipo 2: Portos Estuarinos com Influência Fluvial Moderada**
**Exemplos:** Rio Grande (RS), Paranaguá (PR), Antonina (PR)

**Variáveis necessárias:**

| Variável | Importância | Fonte de Dados (Brasil) | Detalhes |
|----------|-------------|-------------------------|----------|
| **Maré astronômica** | ⭐⭐⭐⭐ | Este projeto | Ainda dominante |
| **Vazão fluvial** | ⭐⭐⭐⭐ | ANA (HidroWeb) | Pode adicionar +0.2 a +0.5m ao NM |
| **Vento (vel. e dir.)** | ⭐⭐⭐⭐ | INMET | Vento sul "empurra" água para dentro |
| **Precipitação (bacia)** | ⭐⭐⭐ | ANA, INMET | Indica vazão futura |
| **Pressão atmosférica** | ⭐⭐ | INMET | Menos relevante que vento |

**Exemplo: Porto do Rio Grande (RS)**
```python
features = {
    'mare_astronomica': altura_prevista_harmonica,         # Este projeto (pequena)
    'vazao_lagoa_dos_patos': vazao_m3_s,                  # ANA (estações próximas)
    'vento_sul_vel': velocidade_vento_sul,                # INMET Rio Grande
    'vento_sul_duracao': horas_consecutivas_vento_sul,    # INMET
    'chuva_bacia_30d': precipitacao_acumulada_30dias,     # ANA/INMET (bacia)
    'nivel_lagoa_guaiba': nivel_agua_guaiba,              # ANA (montante)
    'mare_meteorologica': desvio_observado - astronomico, # Calcular com dados históricos
}
```

**Exemplo: Antonina (PR)**
```python
features = {
    'mare_astronomica_antonina': altura_prevista_harmonica,     # Este projeto
    'mare_astronomica_cais_leste': altura_cais_leste,          # Sentinel (propagação)
    'lag_temporal': tempo_preamar_leste - tempo_preamar_antonina, # Feature chave
    'vazao_rios_locais': vazao_rios_pequenos_bacia,            # ANA (se disponível)
    'vento_sul_vel': velocidade_vento_sul,                     # INMET Paranaguá
    'chuva_local_7d': precipitacao_acumulada_7dias,            # INMET
}
```

---

#### **Tipo 3: Portos em Foz de Grandes Rios (Híbrido Complexo)**
**Exemplos:** Vila do Conde (PA)

**Variáveis necessárias:**

| Variável | Importância | Fonte de Dados (Brasil) | Detalhes |
|----------|-------------|-------------------------|----------|
| **Maré astronômica** | ⭐⭐⭐⭐ | Este projeto | Base, mas vazão pode dominar |
| **Vazão Rio Amazonas** | ⭐⭐⭐⭐⭐ | ANA (Óbidos) | CRÍTICO - pode adicionar +2m na cheia |
| **Vazão Rio Tocantins** | ⭐⭐⭐⭐ | ANA (Tucuruí) | Contribui significativamente |
| **Precipitação Amazônia** | ⭐⭐⭐ | ANA, INMET, CHIRPS | Indica vazão futura (lag ~30-60 dias) |
| **Sazonalidade** | ⭐⭐⭐⭐ | Mês do ano | Cheia (mar-mai) vs Seca (set-nov) |
| **Vento local** | ⭐⭐ | INMET Belém/Barcarena | Menos relevante que vazão |

**Exemplo: Vila do Conde (PA)**
```python
features = {
    # Astronômica (baseline)
    'mare_astronomica': altura_prevista_harmonica,           # Este projeto

    # Fluvial (DOMINANTE em alguns períodos)
    'vazao_amazonas_obidos': vazao_m3_s,                    # ANA (Óbidos - estação 15400000)
    'vazao_tocantins_tucurui': vazao_m3_s,                  # ANA (Tucuruí)
    'vazao_total': vazao_amazonas + vazao_tocantins,

    # Sazonalidade
    'mes': mes_do_ano,                                       # 1-12
    'estacao_hidrologica': 'cheia' | 'vazante' | 'seca',    # Classificação

    # Precipitação (feature antecedente)
    'chuva_amazonia_30d': precip_acumulada_bacia_30d,       # CHIRPS/ANA
    'chuva_amazonia_60d': precip_acumulada_bacia_60d,       # Lag maior

    # Meteorológico
    'vento_vel': velocidade_vento,                           # INMET
    'pressao': pressao_atm,                                  # INMET

    # Target
    'nivel_observado': altura_real_medida,                   # Régua/Sensor local
}

# Modelo de correção
desvio_fluvial = modelo_ML.predict(features) - mare_astronomica
nivel_final = mare_astronomica + desvio_fluvial
```

---

### 🌐 Fontes de Dados Brasileiras

#### **1. Dados Fluviais (Vazão e Nível)**

**ANA - Agência Nacional de Águas**
- **Site:** https://www.snirh.gov.br/hidroweb/
- **Dados:** Vazão (m³/s), Nível (cm), Precipitação
- **Formato:** CSV, API REST
- **Cobertura:** ~4.500 estações fluviométricas no Brasil

**Principais estações para o projeto:**

| Porto | Rio/Bacia | Estação ANA | Código |
|-------|-----------|-------------|--------|
| Vila do Conde | Amazonas | Óbidos | 15400000 |
| Vila do Conde | Tocantins | Tucuruí | 29280000 |
| Rio Grande | Lagoa dos Patos | São Gonçalo | 87560000 |
| Antonina | Rios locais PR | Antonina (se existir) | Consultar HidroWeb |

**Como acessar:**
```python
# Exemplo com API HidroWeb
import requests

url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
params = {
    'codEstacao': '15400000',  # Óbidos
    'dataInicio': '01/01/2020',
    'dataFim': '31/12/2026'
}
response = requests.get(url, params=params)
```

---

#### **2. Dados Meteorológicos**

**INMET - Instituto Nacional de Meteorologia**
- **Site:** https://portal.inmet.gov.br/
- **API:** https://apitempo.inmet.gov.br/
- **Dados:** Vento (vel/dir), Pressão, Temperatura, Precipitação
- **Frequência:** Horária (automáticas) ou diária (convencionais)
- **Formato:** JSON, CSV

**Estações próximas aos portos:**

| Porto | Estação INMET | Código |
|-------|---------------|--------|
| Santos | Santos (Ponta da Praia) | A701 |
| Rio Grande | Rio Grande | A802 |
| Paranaguá | Paranaguá | A851 |
| Itaqui | São Luís | A201 |
| Vila do Conde | Belém | A201 |

**Exemplo de uso da API:**
```python
import requests

url = "https://apitempo.inmet.gov.br/estacao/dados/A701"
params = {'dataInicio': '2020-01-01', 'dataFim': '2026-12-31'}
headers = {'Authorization': 'Bearer SEU_TOKEN'}

response = requests.get(url, params=params, headers=headers)
data = response.json()

# Extrair features
vento_sul = [x for x in data if x['VEN_DIR'] > 135 and x['VEN_DIR'] < 225]
```

---

#### **3. Dados Oceanográficos**

**Copernicus Marine Service**
- **Site:** https://marine.copernicus.eu/
- **Dados:** Altura de onda (Hs), Período (Tp), Direção, Correntes
- **Cobertura:** Oceano Atlântico Sul (costa brasileira)
- **Formato:** NetCDF
- **Gratuito:** Sim (requer cadastro)

**SMC-Brasil (Sistema de Modelagem Costeira)**
- **Site:** http://smcbrasil.cnpq.br/
- **Dados:** Ondas, marés, correntes (modelados para costa BR)

---

#### **4. Dados de Precipitação (Bacia Amazônica)**

**CHIRPS - Climate Hazards Group InfraRed Precipitation**
- **Site:** https://www.chc.ucsb.edu/data/chirps
- **Dados:** Precipitação em grade (0.05° resolução)
- **Cobertura:** Global, incluindo Amazônia
- **Formato:** GeoTIFF, NetCDF
- **Uso:** Calcular precipitação acumulada em bacias hidrográficas

---

### 📈 Workflow de Machine Learning Completo

#### **Fase 1: Treinamento do Modelo (Dados Históricos)**

Para treinar o modelo, você precisa de dados **HISTÓRICOS** tanto das features quanto do target:

```python
# FASE DE TREINAMENTO - Usa dados PASSADOS

# 1. Carregar previsão astronômica (este projeto) - HISTÓRICO 2020-2023
df_astro = pd.read_csv('viladoconde_extremos_2020_2026.csv')
df_astro_treino = df_astro[df_astro['Data_Hora'] < '2024-01-01']  # Só até 2023

# 2. Buscar dados fluviais HISTÓRICOS (ANA) - 2020-2023
vazao_amazonas = buscar_vazao_ana(estacao='15400000', inicio='2020-01-01', fim='2023-12-31')
vazao_tocantins = buscar_vazao_ana(estacao='29280000', inicio='2020-01-01', fim='2023-12-31')

# 3. Buscar dados meteorológicos OBSERVADOS (INMET) - 2020-2023
meteo = buscar_inmet(estacao='A201', inicio='2020-01-01', fim='2023-12-31')

# 4. Buscar precipitação HISTÓRICA (CHIRPS ou ANA) - 2020-2023
chuva_amazonia = buscar_precipitacao_bacia(bacia='amazonia', inicio='2020-01-01', fim='2023-12-31')

# 5. Criar dataset de features
features_treino = pd.DataFrame({
    'data': df_astro_treino['Data_Hora'],
    'mare_astro': df_astro_treino['Altura_m'],
    'vazao_total': vazao_amazonas + vazao_tocantins,
    'vento_vel': meteo['VEN_VEL'],
    'pressao': meteo['PRE_INS'],
    'chuva_30d': chuva_amazonia.rolling(30).sum(),
    'mes': pd.to_datetime(df_astro_treino['Data_Hora']).dt.month,
})

# 6. CRÍTICO: Buscar observações REAIS (régua/sensor do porto) - 2020-2023
#    Você precisa do nível de água que REALMENTE aconteceu para treinar!
observacoes_historicas = buscar_observacoes_porto_historicas('viladoconde', '2020-01-01', '2023-12-31')

# 7. Treinar modelo
from sklearn.ensemble import RandomForestRegressor

X_treino = features_treino[['mare_astro', 'vazao_total', 'vento_vel', 'pressao', 'chuva_30d', 'mes']]
y_treino = observacoes_historicas['nivel_real']  # TARGET = nível OBSERVADO no passado

modelo = RandomForestRegressor(n_estimators=100)
modelo.fit(X_treino, y_treino)

# 8. Salvar modelo treinado
import joblib
joblib.dump(modelo, 'modelo_viladoconde.pkl')
```

**Resumo Fase 1:**
- ✅ Todos os dados são **HISTÓRICOS** (passado conhecido)
- ✅ Você precisa de **observações reais** do nível de água (target)
- ✅ Período típico: 3-10 anos de dados históricos
- ✅ Faz uma vez, depois só retreina periodicamente

---

#### **Fase 2: Previsão Operacional (Dados Atuais + Previsões)**

Para fazer previsões **FUTURAS** (operação real), você precisa de:

```python
# FASE DE PREVISÃO - Quer prever o FUTURO (próximas 24-72h)

import joblib
from datetime import datetime, timedelta

# 1. Carregar modelo treinado
modelo = joblib.load('modelo_viladoconde.pkl')

# 2. Definir horizonte de previsão
agora = datetime.now()
horizonte = agora + timedelta(hours=48)  # Quer prever próximas 48h

# 3. Previsão astronômica (este projeto) - DISPONÍVEL para o futuro!
#    As constantes harmônicas permitem calcular para QUALQUER data futura
df_astro_futuro = calcular_mare_astronomica(agora, horizonte)  # Esse projeto já faz isso!

# 4. CRÍTICO: Buscar PREVISÕES meteorológicas (não observações!)
#    Você precisa de PREVISÃO de vento/pressão, não do passado!
previsao_meteo = buscar_previsao_inmet_cptec(
    local='viladoconde',
    inicio=agora,
    fim=horizonte
)  # Modelos numéricos de previsão do tempo

# 5. Vazão fluvial - PROBLEMA: Dados são do passado recente
#    Opções:
#    A) Usar última vazão observada (simplificação)
#    B) Usar modelo hidrológico para prever vazão futura
vazao_atual = buscar_vazao_ana_tempo_real(estacao='15400000')  # Último dado disponível
# OU
vazao_prevista = modelo_hidrologico.prever(chuva_prevista, vazao_atual)  # Mais sofisticado

# 6. Precipitação acumulada - Usa passado recente + previsão
chuva_30d_passado = buscar_precipitacao_bacia(
    bacia='amazonia',
    inicio=agora - timedelta(days=30),
    fim=agora
)
chuva_futura_prevista = buscar_previsao_chuva_gfs(bacia='amazonia', dias=2)

# 7. Criar features para previsão
features_previsao = pd.DataFrame({
    'data': df_astro_futuro['Data_Hora'],
    'mare_astro': df_astro_futuro['Altura_m'],           # FUTURO calculado (harmônico)
    'vazao_total': vazao_atual,                           # ATUAL observado (lag aceito)
    'vento_vel': previsao_meteo['VEN_VEL_PREV'],        # FUTURO previsto (modelo numérico)
    'pressao': previsao_meteo['PRE_PREV'],               # FUTURO previsto
    'chuva_30d': chuva_30d_passado.sum(),                # PASSADO recente (antecedente)
    'mes': pd.to_datetime(df_astro_futuro['Data_Hora']).dt.month,
})

# 8. PREVER nível futuro
X_futuro = features_previsao[['mare_astro', 'vazao_total', 'vento_vel', 'pressao', 'chuva_30d', 'mes']]
previsao_nivel = modelo.predict(X_futuro)

# 9. Resultado: Previsão de nível para as próximas 48h
resultado = pd.DataFrame({
    'data_hora': features_previsao['data'],
    'nivel_previsto': previsao_nivel,
    'mare_astronomica': features_previsao['mare_astro'],
    'correcao_ML': previsao_nivel - features_previsao['mare_astro']
})

print(resultado)
```

**Resumo Fase 2:**
- ✅ Maré astronômica → **Calculável para o futuro** (constantes harmônicas)
- ⚠️ Meteorologia (vento, pressão) → Precisa de **previsão numérica** (GFS, ECMWF, CPTEC)
- ⚠️ Vazão fluvial → Pode usar **valor atual** (com lag) ou **modelo hidrológico**
- ✅ Precipitação acumulada → Usa **passado recente** (antecedente) + previsão
- ❌ **NÃO** tem observações do nível futuro (é isso que você quer prever!)

---

### 🎯 Conceitos Importantes: Lead Time e Horizonte de Previsão

#### **Lead Time (Tempo de Antecedência)**

É quanto tempo **ANTES** você consegue fazer a previsão:

| Tipo de Previsão | Lead Time | Limitações |
|------------------|-----------|------------|
| **Nowcasting** (0-6h) | Minutos a horas | Usa observações atuais, alta precisão |
| **Curto prazo** (6-48h) | 6-48 horas | Usa previsões meteorológicas, boa precisão |
| **Médio prazo** (2-7 dias) | 2-7 dias | Incerteza meteorológica aumenta |
| **Longo prazo** (>7 dias) | >7 dias | Apenas maré astronômica é confiável |

**Exemplo: Vila do Conde**
```python
# Lead time depende das features:

# 1. Maré astronômica: Lead time INFINITO (pode calcular para 2050 se quiser!)
mare_2050 = calcular_mare_astronomica('2050-01-01')  # Funciona!

# 2. Meteorologia: Lead time ~7-10 dias (depois disso, previsão é ruim)
vento_7d = previsao_gfs(dias=7)  # OK
vento_30d = previsao_gfs(dias=30)  # Não confiável!

# 3. Vazão Amazonas: Lead time ~30-60 dias (depende da chuva na bacia)
#    A chuva que caiu hoje em Manaus leva 30-60 dias para chegar em Óbidos
chuva_hoje_manaus = 100mm  # → afeta vazão em Óbidos daqui 45 dias

# 4. Precipitação acumulada (antecedente): Lead time negativo (usa passado)
chuva_30d = precipitacao_ultimos_30_dias()  # Olha para trás, não para frente
```

**Implicação prática:**
- **0-48h:** Previsão boa (meteo + astronômico)
- **2-7 dias:** Previsão razoável (meteo degrada, mas astronômico OK)
- **7-30 dias:** Apenas astronômico confiável (meteo é "climatologia")
- **30-60 dias Vila do Conde:** Pode usar precipitação passada para prever vazão futura!

---

### 🌐 Fontes de Dados: Observações vs Previsões

#### **Dados HISTÓRICOS (para treinamento)**

| Variável | Fonte OBSERVAÇÕES | API/Acesso |
|----------|-------------------|------------|
| Nível de água (target) | Régua porto, ANA, Marinha | ANA HidroWeb, contato porto |
| Vazão fluvial | ANA estações | HidroWeb (histórico gratuito) |
| Vento observado | INMET estações | Portal INMET (CSV/API) |
| Pressão observada | INMET estações | Portal INMET |
| Precipitação observada | INMET, ANA, CHIRPS | INMET, HidroWeb, CHIRPS |
| Onda observada | Boias Copernicus, PNBOIA | Copernicus, Marinha |

#### **Dados FUTUROS (para previsão operacional)**

| Variável | Fonte PREVISÕES | API/Acesso | Lead Time |
|----------|-----------------|------------|-----------|
| Maré astronômica | **Este projeto!** | Cálculo local | ∞ (infinito) |
| Vento previsto | CPTEC/INPE, GFS, ECMWF | CPTEC API, OpenWeather | 7-10 dias |
| Pressão prevista | CPTEC/INPE, GFS | CPTEC API | 7-10 dias |
| Precipitação prevista | CPTEC/INPE, GFS, MERGE | CPTEC API | 7-10 dias |
| Vazão prevista | Modelo hidrológico próprio | - | Variável |
| Onda prevista | Copernicus Marine, WW3 | Copernicus API | 5-10 dias |

**APIs de Previsão Meteorológica no Brasil:**

1. **CPTEC/INPE** (Centro de Previsão de Tempo e Estudos Climáticos)
   - Site: https://www.cptec.inpe.br/
   - API: http://servicos.cptec.inpe.br/
   - Dados: Previsão de vento, temperatura, chuva (até 7 dias)
   - Gratuito: Sim

2. **GFS (Global Forecast System)**
   - Via NOAA: https://nomads.ncep.noaa.gov/
   - Resolução: 0.25° (~25km)
   - Lead time: 16 dias
   - Variáveis: Vento, pressão, temperatura, precipitação
   - Formato: GRIB2
   - Gratuito: Sim

3. **OpenWeather API** (comercial, mas tem plano free)
   - Site: https://openweathermap.org/api
   - Previsão: 5-7 dias
   - Fácil de usar (JSON)

**Exemplo de código:**
```python
# Buscar previsão meteorológica do CPTEC
import requests

# Previsão para cidade
url = "http://servicos.cptec.inpe.br/XML/cidade/7dias/241/previsao.xml"
resposta = requests.get(url)
previsao_xml = resposta.content

# OpenWeather (mais fácil de usar)
api_key = "SUA_API_KEY"
lat, lon = -1.38, -48.48  # Vila do Conde
url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}"
resposta = requests.get(url)
previsao = resposta.json()

# Extrair vento previsto para próximas 48h
for item in previsao['list'][:16]:  # 16 intervalos de 3h = 48h
    data_hora = item['dt_txt']
    vento_vel = item['wind']['speed']
    vento_dir = item['wind']['deg']
    print(f"{data_hora}: {vento_vel} m/s, {vento_dir}°")
```

---

### ⏱️ Estratégias por Horizonte de Previsão

#### **Nowcasting (0-6 horas) - Máxima Precisão**
```python
# Usa dados OBSERVADOS recentes
features_nowcast = {
    'mare_astro': calculado,              # Exato
    'vento_vel': observado_ultima_hora,   # Estação INMET
    'vazao': observada_tempo_real,        # ANA telemetria
    'pressao': observada_atual,           # INMET
}
# Precisão: Alta (erro ~5-10 cm)
```

#### **Curto Prazo (6-48 horas) - Operacional**
```python
# Usa PREVISÕES meteorológicas
features_curto = {
    'mare_astro': calculado,              # Exato
    'vento_vel': previsao_gfs_24h,        # Modelo numérico
    'vazao': observada_atual,             # Lag aceito (rio muda lento)
    'pressao': previsao_gfs_24h,          # Modelo numérico
    'chuva_30d': observada_passado,       # Antecedente
}
# Precisão: Boa (erro ~10-20 cm, depende de meteo)
```

#### **Médio Prazo (2-7 dias) - Planejamento**
```python
# Previsão meteorológica degrada, astronômico domina
features_medio = {
    'mare_astro': calculado,              # Exato (dominante!)
    'vento_vel': previsao_gfs_5d,         # Incerto
    'vazao': climatologia_mes,            # Usa média histórica
}
# Precisão: Moderada (erro ~20-40 cm)
# Útil para: Janelas de manobra, planejamento logístico
```

#### **Longo Prazo (>7 dias) - Apenas Astronômico**
```python
# Só maré astronômica é confiável
features_longo = {
    'mare_astro': calculado,              # Único confiável
    # Não use previsões meteorológicas > 7 dias!
}
# Precisão: Limitada (só baseline astronômico)
# Útil para: Identificar marés de sizígia, planejar manutenção
```

---

### 🔄 Sistema Operacional Completo (Tempo Real)

```python
# Script para rodar a cada 1 hora (cron job)
from datetime import datetime, timedelta
import joblib

def prever_mare_proximas_48h():
    # 1. Tempo atual
    agora = datetime.utcnow()

    # 2. Carregar modelo treinado
    modelo = joblib.load('modelo_viladoconde.pkl')

    # 3. Calcular maré astronômica (futuro)
    mare_astro = calcular_mare_astronomica_48h(agora)

    # 4. Buscar última vazão observada (ANA tempo real)
    vazao = buscar_ana_telemetria('15400000')

    # 5. Buscar previsão meteorológica (GFS/CPTEC)
    meteo_prev = buscar_previsao_gfs(lat=-1.38, lon=-48.48, horas=48)

    # 6. Precipitação acumulada (últimos 30 dias)
    chuva_30d = buscar_chirps_historico(dias=30).sum()

    # 7. Montar features e prever
    X = criar_features(mare_astro, vazao, meteo_prev, chuva_30d)
    previsao = modelo.predict(X)

    # 8. Salvar resultado
    salvar_previsao_database(agora, previsao)

    # 9. Gerar alertas se nível > limiar crítico
    if previsao.max() > NIVEL_CRITICO:
        enviar_alerta(previsao)

    return previsao

# Rodar a cada hora
if __name__ == '__main__':
    prever_mare_proximas_48h()
```

---

## 📦 Datasets Históricos Prontos para Uso

Para facilitar o desenvolvimento de modelos de ML, este projeto disponibiliza datasets históricos **pré-processados** com dados complementares já integrados.

### 🗺️ Escolha Rápida: Qual Dataset Usar?

| Dataset | Arquivo | Portos | Região | Foco | Use se... |
|---------|---------|--------|--------|------|-----------|
| **Dataset 1** | `portos_brasil_historico_portos_hibridos.parquet` | 3 portos (RG, Paranaguá, Antonina) | Sul | Estuarinos | Trabalha com Rio Grande, Paranaguá ou Antonina |
| **Dataset 2 v2** | `dados_historicos_complementares_portos_oceanicos_v2.parquet` | 13 portos | Nacional | Oceânicos + **Ondas** | Precisa de dados de **ONDAS**, trabalha com Nordeste (Suape, Recife, Pecém, Salvador, Itaqui), Santos, Vitória, SFS, Itajaí |
| **Dataset 3** ⭐ | `dados_historicos_portos_hibridos_arco_norte_v2.parquet` | 3 portos (Vila do Conde, Santarém, Barcarena) | Arco Norte (PA) | **Híbridos + Fluvial** | Trabalha com **Arco Norte**, precisa de **vazão ANA REAL**, foca em **granéis sólidos** |

**Diferenciais por dataset:**

- **Dataset 1:** Meteorologia INMET local + Maré (4 componentes) + Vazão estimada
- **Dataset 2 v2:** Meteorologia ERA5 + Oceanografia (ondas, nível do mar) + Indicadores (frente fria, anomalia pressão) + **13 portos**
- **Dataset 3 ⭐ NOVO:** Meteorologia INMET + Maré (27-35 componentes) + **Vazão ANA REAL** + Vazão montante + Precipitação bacia + Flag híbrido/fluvial

**Combine datasets para:**
- Comparar INMET vs ERA5 (Datasets 1 e 2)
- Comparar estuários Sul vs Norte (Datasets 1 e 3)
- Validar modelos com fontes diferentes

---

### 🎯 **Dataset 1: Portos Híbridos (Estuarinos)**

**Arquivo:** `portos_brasil_historico_portos_hibridos.parquet` (também disponível em CSV)

| Característica | Descrição |
|----------------|-----------|
| **Portos incluídos** | Rio Grande (RS), Paranaguá (PR), Antonina (PR) |
| **Período** | 2020-2024 (5 anos de dados históricos) |
| **Frequência** | Horária |
| **Formato** | Parquet (otimizado) + CSV (visualização) |
| **Tamanho** | ~[verificar tamanho do arquivo] |

**Variáveis incluídas:**

| Variável | Tipo | Descrição | Fonte |
|----------|------|-----------|-------|
| `timestamp` | datetime | Data e hora em UTC | - |
| `station` | string | Identificação do porto ('RioGrande', 'Paranagua', 'Antonina') | - |
| `precip` | float | Precipitação horária (mm) | INMET |
| `press` | float | Pressão atmosférica (mB) | INMET |
| `wind_dir` | float | Direção do vento (graus, 0-360) | INMET |
| `wind_speed` | float | Velocidade do vento (m/s) | INMET |
| `wind_gust` | float | Rajada de vento (m/s) | INMET |
| `mare_astronomica` | float | Maré astronômica calculada (m) | Componentes harmônicas |
| `vazao_fluvial` | float | Vazão fluvial estimada (m³/s) | Médias regionais* |

**Estações meteorológicas utilizadas:**
- **Rio Grande (RS):** INMET A802 - Rio Grande
- **Paranaguá/Antonina (PR):** INMET Morretes-PR (proxy para o complexo estuarino)

**Componentes harmônicas utilizadas para maré astronômica:**
- M2 (Principal lunar semidiurnal)
- S2 (Principal solar semidiurnal)
- O1 (Lunar diurnal)
- K1 (Lunisolar diurnal)

**⚠️ Nota sobre vazão fluvial:**
> A vazão fluvial foi estimada com base em médias regionais devido a restrições de download em massa do HidroWeb da ANA. Para modelos de produção, recomenda-se substituir por dados reais de telemetria da ANA.

**Script de exemplo:**
> Execute `python exemplo_uso_dataset_historico.py` para ver análises completas e exemplos de uso!

**Como usar:**

```python
import pandas as pd

# Carregar dataset (Parquet é mais rápido)
df = pd.read_parquet('portos_brasil_historico_portos_hibridos.parquet')

# Ou usar CSV se preferir
# df = pd.read_csv('portos_brasil_historico_portos_hibridos.csv')

# Converter timestamp se necessário
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filtrar por porto específico
df_riograande = df[df['station'] == 'RioGrande']
df_paranagua = df[df['station'] == 'Paranagua']
df_antonina = df[df['station'] == 'Antonina']

# Explorar dados
print(f"Período: {df['timestamp'].min()} até {df['timestamp'].max()}")
print(f"Total de registros: {len(df):,}")
print(f"\nRegistros por porto:")
print(df['station'].value_counts())

# Estatísticas básicas
print("\n📊 Estatísticas:")
print(df.groupby('station')[['mare_astronomica', 'wind_speed', 'press']].describe())
```

**Exemplo de uso para ML:**

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor

# 1. Carregar dados
df = pd.read_parquet('portos_brasil_historico_portos_hibridos.parquet')

# 2. Filtrar porto específico (ex: Paranaguá)
df_porto = df[df['station'] == 'Paranagua'].copy()

# 3. IMPORTANTE: Você precisa adicionar as observações reais (TARGET)
# Este dataset NÃO contém o nível de água observado - você deve obtê-lo separadamente
# observacoes = pd.read_csv('observacoes_paranagua_2020_2024.csv')
# df_porto = pd.merge(df_porto, observacoes, on='timestamp', how='inner')

# 4. Preparar features
features = [
    'mare_astronomica',  # Baseline
    'wind_speed',        # Vento
    'wind_dir',          # Direção do vento
    'press',             # Pressão
    'vazao_fluvial',     # Vazão (estimada)
    'precip'             # Precipitação
]

# 5. Criar features adicionais (vento sul)
df_porto['vento_sul'] = (
    (df_porto['wind_dir'] >= 135) &
    (df_porto['wind_dir'] <= 225)
).astype(int)
df_porto['vento_sul_vel'] = df_porto['wind_speed'] * df_porto['vento_sul']

# Adicionar à lista de features
features.extend(['vento_sul', 'vento_sul_vel'])

# 6. Treinar modelo (assumindo que você tem o target 'nivel_obs')
# X = df_porto[features]
# y = df_porto['nivel_obs']  # Você precisa obter isso separadamente!
#
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
# modelo = RandomForestRegressor()
# modelo.fit(X_train, y_train)
```

**Vantagens deste dataset:**
- ✅ **Pronto para uso:** Dados já limpos e integrados
- ✅ **Período longo:** 5 anos permitem treinar modelos robustos
- ✅ **Múltiplos portos:** Compare comportamento entre Rio Grande, Paranaguá e Antonina
- ✅ **Formato otimizado:** Parquet reduz tempo de carregamento em 80-90%
- ✅ **Maré astronômica incluída:** Não precisa calcular separadamente
- ✅ **INMET oficial:** Dados meteorológicos de estações oficiais

**Limitações:**
- ❌ **Vazão estimada:** Não são dados reais de telemetria (substituir para produção)
- ❌ **Sem target:** Você ainda precisa obter observações reais do nível de água
- ❌ **Componentes harmônicas simplificadas:** Apenas 4 componentes principais (M2, S2, O1, K1)
  - Para maior precisão, use os scripts Python deste projeto que calculam com 27-35 componentes

---

### 🎯 **Dataset 2: Dados Oceanográficos e Meteorológicos Completos (v2)**

**Arquivo:** `dados_historicos_complementares_portos_oceanicos_v2.parquet` (também disponível em CSV)

| Característica | Descrição |
|----------------|-----------|
| **Portos incluídos** | **13 portos**: Santos (SP), Paranaguá (PR), Itaqui (MA), Rio Grande (RS), São Francisco do Sul (SC), Vitória (ES), Santarém (PA), Barcarena (PA), **Suape (PE)**, **Itajaí (SC)**, **Recife (PE)**, **Pecém (CE)**, **Salvador (BA)** |
| **Novos na v2** | ⭐ Suape, Itajaí, Recife, Pecém, Salvador |
| **Tipo de portos** | Oceânicos/Costeiros (11) + Fluviais (2: Santarém, Barcarena) |
| **Período** | 2020-2025 (6 anos de dados históricos) |
| **Frequência** | Horária |
| **Formato** | Parquet (otimizado) + CSV (visualização) |
| **Foco** | Portos exportadores + **Cobertura completa Nordeste** |

**Variáveis incluídas:**

| Variável | Tipo | Descrição | Unidade | Disponível para |
|----------|------|-----------|---------|-----------------|
| `timestamp` | datetime | Data e hora em UTC | - | Todos |
| `station` | string | Identificação do porto | - | Todos |
| `wind_speed_10m` | float | Velocidade do vento a 10m altura | km/h | Todos |
| `wind_direction_10m` | float | Direção do vento (0-360°) | graus | Todos |
| `pressure_msl` | float | Pressão ao nível do mar | hPa | Todos |
| `wave_height` | float | Altura significativa de onda (Hs) | m | Apenas oceânicos* |
| `wave_period` | float | Período de onda (Tp) | s | Apenas oceânicos* |
| `sea_level_height_msl` | float | **Nível do mar incluindo marés** | m | Apenas oceânicos* |
| `pressao_anomalia` | float | Anomalia de pressão (atual - média histórica) | hPa | Todos |
| `frente_fria` | bool | Indicador de frente fria** | 0/1 | Todos |

**\*Oceânicos (11):** Santos, Paranaguá, Itaqui, Rio Grande, São Francisco do Sul, Vitória, **Suape, Itajaí, Recife, Pecém, Salvador**
**\*\*Fluviais (2):** Santarém, Barcarena (sem dados de ondas/maré oceânica)

**Fontes de dados:**
- **Open-Meteo API** - Dados meteorológicos e oceanográficos
- **Modelo ERA5** (ECMWF/Copernicus) - Reanálise meteorológica
- **Modelo ERA5-Ocean** - Reanálise oceanográfica (ondas, nível do mar)

**🆕 Novidades da v2:**

✅ **+5 portos adicionados (Nordeste + SC):**
1. **Suape (PE)** - Maior complexo portuário do Nordeste, estuário
2. **Itajaí (SC)** - Maior porto de contêineres de SC, foz Rio Itajaí-Açu
3. **Recife (PE)** - Porto histórico, estuário Rio Capibaribe
4. **Pecém (CE)** - Hub industrial e energético do Ceará
5. **Salvador (BA)** - Porto da Baía de Todos os Santos

✅ **Cobertura geográfica completa:**
- **Nordeste:** Itaqui (MA), Pecém (CE), Salvador (BA), Recife (PE), Suape (PE) - **5 portos!**
- **Santa Catarina:** São Francisco do Sul, Itajaí (+ Ilha da Paz nos scripts) - **3 locais!**
- **Sudeste:** Santos (SP), Vitória (ES)
- **Sul:** Paranaguá (PR), Rio Grande (RS)
- **Norte:** Santarém (PA), Barcarena (PA)

**⚠️ Notas importantes:**

> **`sea_level_height_msl`** - Esta variável JÁ INCLUI a maré astronômica modelada pelo ERA5! Ela representa o nível total do mar (maré + efeitos meteorológicos + ondas). Para modelos de ML, compare com as previsões astronômicas deste projeto para extrair a componente meteorológica.

> **`frente_fria`** - Indicador simplificado baseado em:
> - Queda de pressão > 2 hPa em 6 horas
> - Vento do quadrante Sul (135-225°)
> - Útil como feature categórica para ML

> **Dados ANA (vazão fluvial):** ⚠️ O WebService da ANA apresentou erro de autenticação durante a coleta ("Login failed for user"). Por isso, **esta versão v2 NÃO contém dados de vazão fluvial**. Todos os dados meteorológicos e oceanográficos foram coletados com sucesso.

> **Coordenadas ajustadas:** Itaqui (MA) teve coordenadas ajustadas para mar aberto para capturar dados de ondas do modelo oceânico.

**Como usar:**

```python
import pandas as pd

# Carregar dataset
df = pd.read_parquet('dados_historicos_complementares_portos_oceanicos_v2.parquet')

# Converter timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Listar portos disponíveis
print("Portos disponíveis:")
print(df['station'].unique())

# Filtrar porto específico
df_santos = df[df['station'] == 'Santos']

# Separar portos oceânicos vs fluviais
portos_oceanicos = ['Santos', 'Paranagua', 'Itaqui', 'RioGrande',
                    'SaoFranciscoDoSul', 'Vitoria', 'Suape', 'Itajai',
                    'Recife', 'Pecem', 'Salvador']
portos_fluviais = ['Santarem', 'Barcarena']

df_oceanicos = df[df['station'].isin(portos_oceanicos)]
df_fluviais = df[df['station'].isin(portos_fluviais)]

# Explorar ondas (apenas portos oceânicos)
print("\n🌊 Estatísticas de Ondas (portos oceânicos):")
print(df_oceanicos.groupby('station')['wave_height'].describe())

# Identificar eventos de frente fria
df_frentes = df[df['frente_fria'] == True]
print(f"\n❄️  Total de eventos de frente fria: {len(df_frentes):,}")
print(f"   Por porto:")
print(df_frentes['station'].value_counts())
```

**Exemplo de uso para ML - Santos (Ressacas):**

```python
import pandas as pd
import numpy as np

# 1. Carregar dados de Santos
df = pd.read_parquet('dados_historicos_complementares_portos_oceanicos_v2.parquet')
df_santos = df[df['station'] == 'Santos'].copy()

# 2. Converter vento de km/h para m/s
df_santos['wind_speed_ms'] = df_santos['wind_speed_10m'] / 3.6

# 3. Vento sul (importante para Santos - ressacas)
df_santos['vento_sul'] = (
    (df_santos['wind_direction_10m'] >= 135) &
    (df_santos['wind_direction_10m'] <= 225)
).astype(int)

df_santos['vento_sul_speed'] = (
    df_santos['wind_speed_ms'] * df_santos['vento_sul']
)

# 4. Features de ondas (importante para ressacas)
df_santos['onda_significativa'] = df_santos['wave_height'] > 2.5  # Ressaca
df_santos['onda_alta'] = df_santos['wave_height'] > 3.5  # Ressaca forte

# 5. Rolling features (persistência)
df_santos['wave_height_max_24h'] = df_santos['wave_height'].rolling(24).max()
df_santos['wind_speed_max_24h'] = df_santos['wind_speed_ms'].rolling(24).max()
df_santos['vento_sul_horas_24h'] = df_santos['vento_sul'].rolling(24).sum()

# 6. Features para modelo (prever sobre-elevação do nível)
features = [
    'wind_speed_ms',
    'wind_direction_10m',
    'pressure_msl',
    'pressao_anomalia',
    'wave_height',
    'wave_period',
    'wave_height_max_24h',
    'vento_sul',
    'vento_sul_speed',
    'vento_sul_horas_24h',
    'frente_fria',
    'onda_significativa'
]

# 7. Se você tem observações reais de nível:
# df_obs = pd.read_csv('observacoes_santos.csv')
# df_final = pd.merge(df_santos, df_obs, on='timestamp')
#
# # Carregar maré astronômica de alta precisão
# df_mare = pd.read_csv('santos_extremos_2020_2026.csv')
# df_mare_hourly = interpolar_mare(df_mare)  # Interpolar para horário
# df_final = pd.merge(df_final, df_mare_hourly, on='timestamp')
#
# # Target: sobre-elevação meteorológica (storm surge)
# y = df_final['nivel_obs_real'] - df_final['mare_astronomica']
#
# X = df_final[features]
# modelo.fit(X, y)  # Treinar modelo para prever desvio meteorológico
```

**Aplicações específicas por variável:**

**🌊 `wave_height` + `wave_period` (Ondas):**
- **Santos:** Ressacas adicionam +0.5 a +1.5m ao nível previsto
- **Rio Grande:** Ondulações do sul afetam operações portuárias
- **Itaqui:** Ondas do Atlântico equatorial influenciam baía
- **Uso em ML:** Feature crítica para prever sobre-elevação do nível

**💨 `wind_speed` + `wind_direction`:**
- **Vento Sul:** Empurra água para a costa (wind setup)
- **Vento Norte:** Puxa água para fora (wind setdown)
- **Ventos > 15 m/s:** Efeito significativo no nível
- **Uso em ML:** Persistência e direção são features importantes

**🌡️ `pressure_msl` + `pressao_anomalia`:**
- **Efeito barômetro invertido:** -1 hPa ≈ +1 cm nível do mar
- **Anomalia negativa:** Ciclones, baixa pressão → nível sobe
- **Uso em ML:** Anomalia é mais informativa que pressão absoluta

**❄️ `frente_fria` (Indicador booleano):**
- **Feature categórica** pronta para uso
- **Combina:** Queda pressão + vento sul
- **Santos/Paranaguá:** Maioria dos eventos extremos
- **Uso em ML:** Feature de alta importância para classificação

**📊 `sea_level_height_msl`:**
- **Nível TOTAL do mar** (não é target!)
- **Inclui:** Maré astronômica + meteorológica + ondas
- **Uso:** Comparar com observações reais ou extrair componente meteorológica
- **Para treino:** Use como baseline, não como feature

**Vantagens deste dataset:**
- ✅ **Cobertura ampla:** 8 portos, incluindo todos os grandes exportadores
- ✅ **Dados oceanográficos:** Ondas e nível do mar incluídos
- ✅ **Features avançadas:** Anomalia de pressão, frente fria
- ✅ **Período estendido:** 2020-2025 (6 anos)
- ✅ **Alta qualidade:** Dados de reanálise ERA5 (padrão científico)
- ✅ **Pronto para uso:** Sem necessidade de download externo
- ✅ **Portos fluviais:** Santarém e Barcarena também incluídos

**Limitações:**
- ❌ **Sem target:** Observações reais do nível devem ser obtidas separadamente
- ⚠️ **Resolução espacial:** ERA5 tem ~31km (pode não capturar efeitos locais muito pequenos)
- ⚠️ **`sea_level_height_msl` é modelado:** Não são observações reais, são da reanálise
- ⚠️ **Portos fluviais:** Sem dados de ondas/maré oceânica (normal, são rios)

**Comparação com Dataset 1:**

| Aspecto | Dataset 1 (Híbridos) | Dataset 2 v2 (Oceanográficos) |
|---------|---------------------|---------------------------|
| **Portos** | 3 (RG, Paranaguá, Antonina) | **13** (Santos, Paranaguá, Itaqui, RG, SFS, Vitória, Suape, Itajaí, Recife, Pecém, Salvador, Santarém, Barcarena) |
| **Nordeste** | ❌ Não | ✅ **5 portos** (Itaqui, Pecém, Salvador, Recife, Suape) |
| **Tipo** | Estuarinos | Oceânicos (11) + Fluviais (2) |
| **Ondas** | ❌ Não | ✅ Sim (altura, período) |
| **Nível do mar** | ❌ Não | ✅ Sim (ERA5-Ocean) |
| **Frente fria** | ❌ Não | ✅ Sim (indicador) |
| **Anomalia pressão** | ❌ Não | ✅ Sim |
| **Vazão fluvial** | ✅ Sim (estimada) | ⚠️ **Não (erro ANA)** |
| **Fonte** | INMET (locais) | ERA5 (reanálise global) |
| **Período** | 2020-2024 (5 anos) | 2020-2025 (6 anos) |

**Quando usar cada dataset:**

**Use Dataset 1 se:**
- Trabalha com Rio Grande, Paranaguá ou Antonina
- Precisa de **vazão fluvial** (estimada)
- Quer dados de estações INMET locais
- Foca em portos estuarinos específicos

**Use Dataset 2 v2 se:**
- Trabalha com **NORDESTE** (Suape, Recife, Pecém, Salvador, Itaqui) ⭐
- Trabalha com **Santos, Itajaí, Vitória, São Francisco do Sul**
- Precisa de dados de **ONDAS** (ressacas!)
- Precisa do **NÍVEL DO MAR** modelado
- Quer **indicador de frente fria** pronto
- Trabalha com eventos extremos costeiros
- Precisa de **cobertura nacional ampla** (13 portos)

**Use AMBOS se:**
- Trabalha com **Paranaguá** ou **Rio Grande** (únicos em comum)
- Quer comparar INMET vs ERA5
- Quer combinar: vazão (Dataset 1) + ondas (Dataset 2)
- Desenvolve sistema multi-porto nacional
- Valida modelos com fontes diferentes

---

### 🎯 **Dataset 3: Portos Híbridos do Arco Norte (v2)**

**Arquivo:** `dados_historicos_portos_hibridos_arco_norte_v2.parquet`

| Característica | Descrição |
|----------------|-----------|
| **Portos incluídos** | **3 portos do Arco Norte**: Vila do Conde (PA), Santarém (PA), Barcarena (PA) |
| **Tipo de portos** | **Híbridos** (Vila do Conde, Barcarena: maré + vazão fluvial) + **Fluvial puro** (Santarém: apenas vazão) |
| **Período** | 2020-2025 (6 anos de dados históricos) |
| **Frequência** | Horária |
| **Formato** | Parquet (otimizado) |
| **Foco** | **Granéis sólidos** (soja, milho, bauxita, alumina) |

**🆕 Diferenciais deste dataset:**

✅ **Dados ANA REAIS integrados:**
- Vazão e cota de estações ANA (Tucuruí, Altamira, Óbidos, Santarém)
- Vazão montante (estação rio acima) para propagação de onda
- Dados horários de telemetria (não estimados!)

✅ **Maré astronômica confirmada (DHN):**
- **Vila do Conde:** Maré significativa (~1-2m amplitude)
- **Barcarena:** ⭐ **Confirmado pela DHN** - tem influência de maré!
- **Santarém:** Fluvial puro (maré < 2cm, desprezível)

✅ **Meteorologia INMET local:**
- Estações: Belém e Santarém
- Vento, pressão atmosférica e precipitação horários

✅ **Features para ML de portos fluviais:**
- Precipitação acumulada 30 dias na bacia
- Vazão montante com lag temporal
- Flag `tem_mare_astronomica` para diferenciar híbridos de fluviais puros
- Variável `mes` para sazonalidade (cheias/vazantes)

**Variáveis incluídas:**

| Variável | Tipo | Descrição | Unidade | Disponível para |
|----------|------|-----------|---------|-----------------|
| `timestamp` | datetime | Data e hora em UTC | - | Todos |
| `station` | string | Porto ('VilaDoCondePA', 'SantaremPA', 'BarcenaPA') | - | Todos |
| **MARÉ ASTRONÔMICA** |
| `mare_astronomica_m` | float | **Maré calculada (27-35 componentes)** | m | Vila do Conde, Barcarena |
| `tem_mare_astronomica` | bool | Flag: porto tem maré significativa? | 0/1 | Todos |
| **DADOS FLUVIAIS (ANA)** |
| `vazao_rio_m3s` | float | **Vazão do rio (estação local)** | m³/s | Todos |
| `cota_rio_m` | float | **Nível do rio medido** | m | Todos |
| `vazao_montante_m3s` | float | **Vazão rio acima** (propagação) | m³/s | Todos |
| **METEOROLOGIA (INMET)** |
| `wind_speed_10m` | float | Velocidade do vento a 10m altura | km/h | Todos |
| `wind_direction_10m` | float | Direção do vento (0-360°) | graus | Todos |
| `pressure_msl` | float | Pressão ao nível do mar | hPa | Todos |
| `precip_bacia_30d_mm` | float | **Precipitação acumulada 30 dias na bacia** | mm | Todos |
| **SAZONALIDADE** |
| `mes` | int | Mês (1-12) para sazonalidade | - | Todos |

**Estações ANA utilizadas:**

| Porto | Estação Local (vazão/cota) | Estação Montante (propagação) | Bacia |
|-------|---------------------------|-------------------------------|-------|
| **Vila do Conde** | 31140000 (Tucuruí) | 16350000 (Altamira) | Amazonas |
| **Santarém** | 17050001 (Santarém) | 17050000 (Óbidos, ~100km montante) | Amazonas |
| **Barcarena** | 31140000 (Tucuruí) | 16350000 (Altamira) | Amazonas |

**Estações INMET utilizadas:**

| Porto | Estação INMET | Localização | Distância |
|-------|---------------|-------------|-----------|
| **Vila do Conde / Barcarena** | Belém | Belém - PA | ~30-50 km |
| **Santarém** | Santarém | Santarém - PA | Local |

**Fontes de dados:**
- **ANA (Agência Nacional de Águas)** - Vazão e cota fluvial (telemetria)
- **INMET** - Dados meteorológicos (estações oficiais)
- **Scripts Python deste projeto** - Maré astronômica (27-35 componentes harmônicas)
- **CHIRPS** - Precipitação acumulada na bacia (dados de satélite)
- **DHN** - Confirmação de influência de maré em Barcarena

**Como usar:**

```python
import pandas as pd
import numpy as np

# Carregar dataset
df = pd.read_parquet('dados_historicos_portos_hibridos_arco_norte_v2.parquet')

# Converter timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Listar portos disponíveis
print("Portos disponíveis:")
print(df['station'].unique())
# Output: ['VilaDoCondePA', 'SantaremPA', 'BarcenaPA']

# Filtrar porto específico
df_santarem = df[df['station'] == 'SantaremPA']

# Separar portos híbridos (com maré) vs fluviais puros (sem maré)
df_hibridos = df[df['tem_mare_astronomica'] == True]   # Vila do Conde, Barcarena
df_fluviais = df[df['tem_mare_astronomica'] == False]  # Santarém

# Explorar dados fluviais
print("\n🌊 Estatísticas de Vazão (ANA):")
print(df.groupby('station')['vazao_rio_m3s'].describe())

print("\n📊 Estatísticas de Maré Astronômica (portos híbridos):")
print(df_hibridos.groupby('station')['mare_astronomica_m'].describe())

# Análise de sazonalidade (cheias e vazantes)
print("\n📅 Vazão média por mês (Santarém):")
sazonalidade = df_santarem.groupby('mes')['vazao_rio_m3s'].mean()
print(sazonalidade)
# Esperado: pico em Abril-Maio (cheia), mínimo em Out-Nov (seca)
```

**Exemplo de uso para ML - Porto Híbrido (Vila do Conde):**

```python
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

# 1. Carregar dados
df = pd.read_parquet('dados_historicos_portos_hibridos_arco_norte_v2.parquet')

# 2. Filtrar porto híbrido (Vila do Conde)
df_porto = df[df['station'] == 'VilaDoCondePA'].copy()

# 3. Criar features adicionais
# Features temporais para sazonalidade
df_porto['sin_mes'] = np.sin(2 * np.pi * df_porto['mes'] / 12)
df_porto['cos_mes'] = np.cos(2 * np.pi * df_porto['mes'] / 12)

# Lag da vazão montante (onda de cheia propaga em ~7-15 dias)
df_porto['vazao_montante_lag_7d'] = df_porto['vazao_montante_m3s'].shift(7*24)  # 7 dias
df_porto['vazao_montante_lag_14d'] = df_porto['vazao_montante_m3s'].shift(14*24)  # 14 dias

# Remover NaNs dos lags
df_porto = df_porto.dropna()

# 4. Definir features para porto HÍBRIDO
features_hibrido = [
    # Maré astronômica (baseline forte)
    'mare_astronomica_m',

    # Efeitos fluviais (complemento)
    'vazao_rio_m3s',
    'vazao_montante_lag_7d',
    'vazao_montante_lag_14d',
    'precip_bacia_30d_mm',

    # Efeitos meteorológicos
    'wind_speed_10m',
    'pressure_msl',

    # Sazonalidade
    'sin_mes',
    'cos_mes',
]

# 5. IMPORTANTE: Você precisa adicionar as observações reais (TARGET)
# Este dataset NÃO contém o nível de água observado - você deve obtê-lo separadamente
# Exemplo:
# observacoes = pd.read_csv('observacoes_viladoconde_2020_2025.csv')
# df_porto = pd.merge(df_porto, observacoes, on='timestamp', how='inner')

# 6. Treinar modelo (assumindo que você tem o target 'nivel_obs')
# X = df_porto[features_hibrido]
# y = df_porto['nivel_obs']  # Você precisa obter isso separadamente!
#
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
# modelo = GradientBoostingRegressor(n_estimators=500, max_depth=5, learning_rate=0.01)
# modelo.fit(X_train, y_train)
#
# # Analisar importância das features
# importances = pd.DataFrame({
#     'feature': features_hibrido,
#     'importance': modelo.feature_importances_
# }).sort_values('importance', ascending=False)
# print(importances)
#
# # Esperado para porto híbrido:
# # mare_astronomica_m: 0.30-0.40 (baseline forte)
# # vazao_rio_m3s: 0.20-0.30 (complemento fluvial importante)
# # precip_bacia_30d_mm: 0.10-0.15
```

**Exemplo de uso para ML - Porto Fluvial Puro (Santarém):**

```python
# Para Santarém, NÃO usar maré astronômica!

# 1. Carregar dados
df = pd.read_parquet('dados_historicos_portos_hibridos_arco_norte_v2.parquet')
df_santarem = df[df['station'] == 'SantaremPA'].copy()

# 2. Criar features temporais
df_santarem['sin_mes'] = np.sin(2 * np.pi * df_santarem['mes'] / 12)
df_santarem['cos_mes'] = np.cos(2 * np.pi * df_santarem['mes'] / 12)

# Lag da vazão montante (Óbidos → Santarém: ~2-4 dias)
df_santarem['vazao_montante_lag_2d'] = df_santarem['vazao_montante_m3s'].shift(2*24)
df_santarem['vazao_montante_lag_3d'] = df_santarem['vazao_montante_m3s'].shift(3*24)

df_santarem = df_santarem.dropna()

# 3. Features para porto FLUVIAL PURO
features_fluvial = [
    # Vazão (dominante)
    'vazao_rio_m3s',
    'vazao_montante_lag_2d',
    'vazao_montante_lag_3d',

    # Precipitação
    'precip_bacia_30d_mm',

    # Sazonalidade
    'sin_mes',
    'cos_mes',

    # SEM mare_astronomica! (seria ruído)
    # SEM ondas! (não existe em rio)
]

# 4. Target pode ser cota_rio_m ou nível observado
# X = df_santarem[features_fluvial]
# y = df_santarem['cota_rio_m']  # Ou 'nivel_obs' se tiver
#
# # Modelo ML
# modelo.fit(X, y)
#
# # Importância esperada:
# # vazao_rio_m3s: 0.40-0.50 (dominante!)
# # precip_bacia_30d_mm: 0.20-0.25
# # vazao_montante_lag_2d: 0.10-0.15
# # sin_mes/cos_mes: 0.10 (sazonalidade)
```

**Vantagens deste dataset:**
- ✅ **Dados ANA REAIS:** Vazão de telemetria, não estimada!
- ✅ **Maré astronômica de alta precisão:** 27-35 componentes (scripts deste projeto)
- ✅ **Confirmação DHN:** Barcarena verificado como porto híbrido
- ✅ **Propagação de onda:** Vazão montante para prever com antecedência
- ✅ **Precipitação na bacia:** Permite previsão de médio prazo (30-60 dias)
- ✅ **Flag híbrido/fluvial:** `tem_mare_astronomica` para modelos diferenciados
- ✅ **Arco Norte completo:** 3 principais portos de granéis sólidos da região
- ✅ **Sazonalidade:** Variável `mes` para capturar ciclos de cheia/vazante

**Limitações:**
- ❌ **Sem target:** Observações reais do nível devem ser obtidas separadamente
- ⚠️ **Estações proxy:** Tucuruí não é exatamente em Vila do Conde/Barcarena (melhor disponível)
- ⚠️ **Lags a calibrar:** Tempo de propagação montante→local pode variar (calibrar com dados)
- ⚠️ **Dados ANA:** Podem ter falhas (telemetria dependente de manutenção)

**Comparação com outros datasets:**

| Aspecto | Dataset 1 (Híbridos Sul) | Dataset 2 v2 (Oceanográficos) | **Dataset 3 (Arco Norte)** |
|---------|-------------------------|-------------------------------|----------------------------|
| **Portos** | 3 (RG, Paranaguá, Antonina) | 13 (nacional) | **3 (Arco Norte)** |
| **Região** | Sul | Nacional | **Norte (PA)** |
| **Tipo** | Estuarinos | Oceânicos + Fluviais | **Híbridos + Fluvial puro** |
| **Vazão ANA** | ⚠️ Estimada | ❌ Não (erro) | ✅ **REAL (telemetria)** |
| **Maré astronômica** | ✅ Sim (4 comp.) | ❌ Não | ✅ **Sim (27-35 comp.)** |
| **Precipitação bacia** | ❌ Não | ❌ Não | ✅ **Sim (30d acum.)** |
| **Vazão montante** | ❌ Não | ❌ Não | ✅ **Sim (propagação)** |
| **Flag híbrido/fluvial** | ❌ Não | ❌ Não | ✅ **Sim** |
| **Ondas** | ❌ Não | ✅ Sim | ❌ Não (fluvial) |
| **Foco** | Estuários Sul | Exportadores nacionais | **Granéis Arco Norte** |
| **Período** | 2020-2024 (5 anos) | 2020-2025 (6 anos) | **2020-2025 (6 anos)** |

**Quando usar este dataset:**

✅ **Use Dataset 3 (Arco Norte) se:**
- Trabalha com **Vila do Conde, Santarém ou Barcarena**
- Foca em **granéis sólidos** (soja, milho, bauxita, alumina)
- Precisa de **vazão fluvial REAL** (não estimada)
- Quer combinar **maré astronômica + vazão** em portos híbridos
- Desenvolve modelos para **portos fluviais puros** (Santarém)
- Precisa de **precipitação na bacia** para previsão de médio prazo
- Quer usar **propagação de onda** (vazão montante)

❌ **NÃO use este dataset se:**
- Precisa de dados de **ondas** (use Dataset 2 v2 - portos oceânicos)
- Trabalha com portos fora do Arco Norte (use Datasets 1 ou 2)
- Foca em portos oceânicos puros (use Dataset 2 v2)

**Combine com outros datasets:**
```python
# Exemplo: Comparar comportamento híbrido Sul vs Norte

# Dataset 1: Paranaguá (estuário Sul)
df_sul = pd.read_parquet('portos_brasil_historico_portos_hibridos.parquet')
df_sul = df_sul[df_sul['station'] == 'Paranagua']

# Dataset 3: Vila do Conde (estuário Norte)
df_norte = pd.read_parquet('dados_historicos_portos_hibridos_arco_norte_v2.parquet')
df_norte = df_norte[df_norte['station'] == 'VilaDoCondePA']

# Comparar importância relativa: maré vs vazão
# Sul: maré domina (amplitude ~1-2m, vazão menor)
# Norte: ambos importantes (maré ~1-2m, vazão Amazonas enorme)
```

**🎯 Casos de uso específicos:**

1. **Previsão de calado para operação de navios graneleiros:**
   - Features: vazão_rio, mare_astronomica, precip_30d
   - Target: calado disponível no berço
   - Lead time: 7-14 dias (usando vazão montante + previsão de chuva)

2. **Otimização de janelas de operação:**
   - Identificar períodos de maior calado (cheia + preamar)
   - Combinar sazonalidade (mes) + previsão de maré

3. **Análise de risco de interrupção:**
   - Vazante severa (Set-Nov) + baixa-mar = risco alto
   - Usar precip_30d como early warning

4. **Comparação híbridos vs fluviais:**
   - Modelo único com flag `tem_mare_astronomica`
   - ML aprende quando usar maré vs quando ignorar

---

### 📊 Comparação: Datasets Prontos vs Scripts Python

| Aspecto | Datasets Prontos (Parquet) | Scripts Python (Este Projeto) |
|---------|---------------------------|-------------------------------|
| **Maré astronômica** | Simplificada (4 componentes) | Completa (27-35 componentes) |
| **Precisão** | Boa (~85-90%) | Excelente (~95-99%) |
| **Facilidade** | ⭐⭐⭐⭐⭐ Pronto para usar | ⭐⭐⭐ Precisa executar scripts |
| **Flexibilidade** | ❌ Período fixo (2020-2024) | ✅ Qualquer período desejado |
| **Meteorologia** | ✅ Incluída (INMET) | ❌ Você precisa buscar |
| **Vazão** | ⚠️ Estimada | ❌ Você precisa buscar |
| **Target** | ❌ Não incluído | ❌ Não incluído |

**Recomendação:**
- **Prototipagem rápida:** Use os datasets Parquet
- **Produção/Alta precisão:** Use os scripts Python + dados reais de vazão
- **Melhor abordagem:** Combine ambos! Use Parquet para meteorologia + scripts para maré astronômica precisa

---

### 🔄 Workflow Híbrido Recomendado

```python
import pandas as pd

# 1. Carregar dataset pronto (meteorologia + vazão estimada)
df_meteo = pd.read_parquet('portos_brasil_historico_portos_hibridos.parquet')
df_meteo = df_meteo[df_meteo['station'] == 'Paranagua']

# 2. Carregar maré astronômica PRECISA (27-35 componentes)
df_mare = pd.read_csv('paranagua_extremos_2020_2026.csv')
df_mare['Data_Hora'] = pd.to_datetime(df_mare['Data_Hora'])

# 3. Interpolar maré para ter valores horários (não apenas extremos)
# Criar range horário
hourly_range = pd.date_range(
    start=df_meteo['timestamp'].min(),
    end=df_meteo['timestamp'].max(),
    freq='H'
)

# Calcular maré para cada hora usando os scripts deste projeto
# (você pode chamar a função calculate_tide dos scripts)

# 4. Merge meteorologia + maré astronômica precisa
df_completo = pd.merge(
    df_meteo[['timestamp', 'wind_speed', 'wind_dir', 'press', 'precip']],
    df_mare_horaria[['timestamp', 'mare_astronomica_precisa']],
    on='timestamp',
    how='inner'
)

# 5. Adicionar observações reais (target)
df_obs = pd.read_csv('observacoes_paranagua.csv')
df_final = pd.merge(df_completo, df_obs, on='timestamp', how='inner')

# 6. Agora você tem o melhor dos dois mundos!
# - Meteorologia completa (dataset pronto)
# - Maré astronômica precisa (scripts Python)
# - Observações reais (target)
```

---

## 📋 Guia Prático de Implementação: Busca de Dados por Variável

Este guia serve como **checklist** para desenvolvedores implementarem um sistema de ML para previsão de marés. Siga as instruções específicas para cada tipo de variável.

**💡 DICA IMPORTANTE - Use os datasets prontos:**

> **Portos do Sul:** Se trabalha com **Rio Grande**, **Paranaguá** ou **Antonina**, use o **Dataset 1** (`portos_brasil_historico_portos_hibridos.parquet`) com dados meteorológicos e maré astronômica (2020-2024).
>
> **Portos do Arco Norte:** ⭐ Se trabalha com **Vila do Conde**, **Santarém** ou **Barcarena**, use o **Dataset 3** (`dados_historicos_portos_hibridos_arco_norte_v2.parquet`) com vazão ANA REAL, maré astronômica de alta precisão e precipitação na bacia (2020-2025).
>
> **Portos oceânicos nacionais:** Se trabalha com Santos, Itaqui, Suape, Recife, Pecém, Salvador, Itajaí, Vitória, SFS e precisa de dados de **ondas**, use o **Dataset 2 v2** (`dados_historicos_complementares_portos_oceanicos_v2.parquet`).
>
> Veja a seção [Datasets Históricos Prontos para Uso](#-datasets-históricos-prontos-para-uso) acima.
>
> Para outros portos ou períodos diferentes, siga o guia completo abaixo.

---

### 🎯 **VARIÁVEL 1: Maré Astronômica (Baseline)**

**Status:** ✅ **JÁ DISPONÍVEL NESTE PROJETO**

| Item | Descrição |
|------|-----------|
| **Tipo de dado** | Calculado (não precisa buscar) |
| **Período** | Qualquer (2020-2026 já gerado, pode estender) |
| **Fonte** | Este projeto (constantes harmônicas) |
| **Lead time** | Infinito (calculável para qualquer data futura) |
| **Formato** | CSV com colunas: Data_Hora, Altura_m, Evento |

**Opções disponíveis:**

**OPÇÃO A: CSVs gerados (RECOMENDADO - Alta precisão)**
- **Componentes:** 27-35 harmônicas completas
- **Precisão:** Excelente (~95-99%)
- **Formato:** Apenas extremos (preamares e baixa-mares)

**OPÇÃO B: Dataset Parquet (Rápido para prototipagem)**
- **Componentes:** 4 harmônicas simplificadas (M2, S2, O1, K1)
- **Precisão:** Boa (~85-90%)
- **Formato:** Valores horários
- **Portos:** Apenas Rio Grande, Paranaguá, Antonina
- **Período:** Fixo 2020-2024

**Como usar (OPÇÃO A - Alta precisão):**
```python
import pandas as pd

# Carregar previsão astronômica de alta precisão
df_mare = pd.read_csv('viladoconde_extremos_2020_2026.csv')
df_mare['Data_Hora'] = pd.to_datetime(df_mare['Data_Hora'])

# Filtrar período desejado
df_treino = df_mare[(df_mare['Data_Hora'] >= '2020-01-01') &
                     (df_mare['Data_Hora'] < '2024-01-01')]

print(f"✅ Maré astronômica: {len(df_treino)} registros carregados")
```

**Como usar (OPÇÃO B - Dataset pronto):**
```python
import pandas as pd

# Carregar dataset com maré já incluída
df = pd.read_parquet('portos_brasil_historico_portos_hibridos.parquet')
df_porto = df[df['station'] == 'Paranagua']

# A coluna 'mare_astronomica' já está calculada!
print(f"✅ Maré astronômica (simplificada): {len(df_porto)} registros horários")
print(f"   Amplitude: {df_porto['mare_astronomica'].min():.2f} a {df_porto['mare_astronomica'].max():.2f} m")
```

---

### 🎯 **VARIÁVEL 2: Vazão Fluvial**

**Necessário para:** Rio Grande, Paranaguá, Antonina, **Vila do Conde (CRÍTICO)**

| Item | Descrição |
|------|-----------|
| **Fonte** | ANA - Agência Nacional de Águas |
| **Site** | https://www.snirh.gov.br/hidroweb/ |
| **Tipo de dado** | Observações históricas (vazão em m³/s) |
| **Período recomendado** | Mínimo 3 anos (idealmente 5-10 anos) |
| **Frequência** | Diária ou horária (depende da estação) |
| **Formato** | CSV, TXT, ou API REST |

**Estações chave:**

| Porto | Código Estação | Nome | Rio |
|-------|----------------|------|-----|
| Vila do Conde | **15400000** | Óbidos | Amazonas |
| Vila do Conde | **29280000** | Tucuruí | Tocantins |
| Rio Grande | **87560000** | São Gonçalo | Lagoa dos Patos |

**Prompt para buscar dados:**

```
AÇÃO: Acessar HidroWeb da ANA e baixar dados de vazão

PASSO 1: Acesse https://www.snirh.gov.br/hidroweb/

PASSO 2: Clique em "Séries Históricas"

PASSO 3: Selecione:
- Tipo de Estação: Fluviométrica
- Variável: Vazão
- Código da Estação: [USE CÓDIGO DA TABELA ACIMA]
- Período: 01/01/2020 até 31/12/2023 (ou mais recente disponível)

PASSO 4: Clique em "Buscar" e depois "Download"

PASSO 5: Escolha formato CSV

RESULTADO ESPERADO: Arquivo CSV com colunas:
- Data
- Vazao (m³/s)
- NivelConsistencia (1=consistido, 2=não consistido)
```

**Código para processar dados da ANA:**
```python
import pandas as pd
import requests

# OPÇÃO 1: Carregar arquivo CSV baixado manualmente
def carregar_vazao_ana_csv(arquivo_csv):
    """Carrega dados de vazão do CSV da ANA"""
    # Formato típico da ANA (ajustar se necessário)
    df = pd.read_csv(arquivo_csv, sep=';', encoding='latin1', decimal=',')

    # Renomear colunas (verificar nomes no seu CSV)
    df = df.rename(columns={
        'Data': 'data',
        'Vazao': 'vazao_m3s'
    })

    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    df['vazao_m3s'] = pd.to_numeric(df['vazao_m3s'], errors='coerce')

    # Remover valores nulos
    df = df.dropna(subset=['vazao_m3s'])

    print(f"✅ Vazão ANA: {len(df)} registros carregados")
    print(f"   Período: {df['data'].min()} até {df['data'].max()}")
    print(f"   Vazão média: {df['vazao_m3s'].mean():.2f} m³/s")

    return df[['data', 'vazao_m3s']]

# OPÇÃO 2: API da ANA (mais avançado)
def buscar_vazao_ana_api(cod_estacao, data_inicio, data_fim):
    """Busca dados via API da ANA"""
    url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"

    params = {
        'codEstacao': cod_estacao,
        'dataInicio': data_inicio.strftime('%d/%m/%Y'),
        'dataFim': data_fim.strftime('%d/%m/%Y')
    }

    print(f"⏳ Buscando vazão da estação {cod_estacao}...")
    response = requests.get(url, params=params, timeout=60)

    if response.status_code == 200:
        # Parsear XML retornado (implementar conforme estrutura da resposta)
        print("✅ Dados recebidos da API ANA")
        # TODO: Implementar parser XML -> DataFrame
        return response.content
    else:
        print(f"❌ Erro ao buscar dados: {response.status_code}")
        return None

# Uso:
# Baixar manualmente do HidroWeb e carregar
df_vazao_amazonas = carregar_vazao_ana_csv('obidos_15400000_2020_2023.csv')
df_vazao_tocantins = carregar_vazao_ana_csv('tucurui_29280000_2020_2023.csv')

# Combinar vazões (Vila do Conde)
df_vazao_total = pd.merge(
    df_vazao_amazonas,
    df_vazao_tocantins,
    on='data',
    how='outer',
    suffixes=('_amazonas', '_tocantins')
).fillna(method='ffill')

df_vazao_total['vazao_total'] = (
    df_vazao_total['vazao_m3s_amazonas'] +
    df_vazao_total['vazao_m3s_tocantins']
)
```

**Troubleshooting:**
- ❌ **Dados faltando:** Use interpolação linear ou forward-fill
- ❌ **Formato diferente:** Ajuste separadores e encoding no `pd.read_csv()`
- ❌ **API não responde:** Prefira download manual via portal

---

### 🎯 **VARIÁVEL 3: Dados Meteorológicos (Vento, Pressão)**

**Necessário para:** Todos os portos (especialmente Santos, Rio Grande)

**💡 ATALHO:** Para **Rio Grande, Paranaguá e Antonina**, esses dados já estão no dataset Parquet pronto! Veja [Datasets Históricos](#-datasets-históricos-prontos-para-uso).

| Item | Descrição |
|------|-----------|
| **Fonte** | INMET - Instituto Nacional de Meteorologia |
| **Site** | https://portal.inmet.gov.br/ |
| **Tipo de dado** | Observações históricas (horária ou diária) |
| **Período recomendado** | Mesmo período da vazão (3-10 anos) |
| **Frequência** | Horária (estações automáticas) |
| **Formato** | CSV |

**Estações chave:**

| Porto | Código | Cidade |
|-------|--------|--------|
| Santos | **A701** | Santos - Ponta da Praia |
| Rio Grande | **A802** | Rio Grande |
| Paranaguá | **A851** | Paranaguá |
| São Luís (Itaqui) | **A201** | São Luís |
| Belém (Vila do Conde) | **A230** | Belém |

**Prompt para buscar dados:**

```
AÇÃO: Baixar dados meteorológicos do INMET

PASSO 1: Acesse https://portal.inmet.gov.br/

PASSO 2: Menu: "Dados" → "Estações Automáticas" → "Dados Históricos"

PASSO 3: Selecione:
- Estação: [USE CÓDIGO DA TABELA ACIMA]
- Período: 01/01/2020 até 31/12/2023
- Variáveis:
  ✅ Velocidade do Vento (m/s)
  ✅ Direção do Vento (°)
  ✅ Pressão Atmosférica (hPa)
  ✅ Temperatura (°C) [opcional]
  ✅ Precipitação (mm) [opcional]

PASSO 4: Clique em "Gerar Arquivo"

PASSO 5: Download do arquivo ZIP com CSVs

RESULTADO ESPERADO: CSV com colunas:
- Data, Hora
- VEN_VEL (m/s)
- VEN_DIR (graus)
- PRE_INS (hPa)
```

**Código para processar dados do INMET:**
```python
import pandas as pd
import numpy as np

def carregar_dados_inmet(arquivo_csv, cod_estacao):
    """Carrega dados meteorológicos do INMET"""
    # INMET usa formato específico com cabeçalhos em português
    df = pd.read_csv(
        arquivo_csv,
        sep=';',
        encoding='latin1',
        decimal=',',
        skiprows=8  # Pular cabeçalho do INMET (verificar seu arquivo!)
    )

    # Colunas típicas do INMET (nomes podem variar)
    df = df.rename(columns={
        'Data': 'data',
        'Hora UTC': 'hora',
        'VENTO, VELOCIDADE HORARIA (m/s)': 'vento_vel',
        'VENTO, DIRECAO HORARIA (gr)': 'vento_dir',
        'PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)': 'pressao'
    })

    # Combinar data e hora
    df['data_hora'] = pd.to_datetime(
        df['data'] + ' ' + df['hora'],
        format='%Y/%m/%d %H:%M'
    )

    # Converter para numérico
    for col in ['vento_vel', 'vento_dir', 'pressao']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Remover valores inválidos (-9999 é código de dado faltante no INMET)
    df = df.replace(-9999, np.nan)
    df = df.dropna(subset=['vento_vel', 'pressao'])

    print(f"✅ INMET {cod_estacao}: {len(df)} registros carregados")
    print(f"   Período: {df['data_hora'].min()} até {df['data_hora'].max()}")
    print(f"   Vento médio: {df['vento_vel'].mean():.2f} m/s")
    print(f"   Pressão média: {df['pressao'].mean():.2f} hPa")

    return df[['data_hora', 'vento_vel', 'vento_dir', 'pressao']]

# Criar features de vento sul (importante para portos sul/sudeste)
def calcular_features_vento_sul(df):
    """Cria features específicas de vento sul (135-225°)"""
    # Vento sul: direção entre 135° e 225°
    df['vento_sul'] = (
        (df['vento_dir'] >= 135) &
        (df['vento_dir'] <= 225)
    ).astype(int)

    df['vento_sul_vel'] = df['vento_vel'] * df['vento_sul']

    # Persistência: horas consecutivas de vento sul
    df['vento_sul_persistencia'] = (
        df.groupby((df['vento_sul'] != df['vento_sul'].shift()).cumsum())
        ['vento_sul']
        .cumsum()
    )

    # Máximo de vento sul nas últimas 48h (rolling)
    df['vento_sul_max_48h'] = (
        df['vento_sul_vel']
        .rolling(window=48, min_periods=1)
        .max()
    )

    return df

# Uso:
df_meteo = carregar_dados_inmet('INMET_SE_A701_SANTOS_2020_2023.csv', 'A701')
df_meteo = calcular_features_vento_sul(df_meteo)

print("\n📊 Features criadas:")
print(df_meteo[['data_hora', 'vento_vel', 'vento_dir', 'vento_sul',
                 'vento_sul_persistencia', 'vento_sul_max_48h']].head(10))
```

**Troubleshooting:**
- ❌ **Arquivo diferente:** INMET muda formato - ajuste `skiprows` e nomes de colunas
- ❌ **Dados faltando:** Use interpolação temporal ou busque estação próxima
- ❌ **Valores -9999:** São dados faltantes, substituir por `np.nan`

---

### 🎯 **VARIÁVEL 4: Precipitação de Bacia (Amazônia)**

**Necessário para:** Vila do Conde (previsão de vazão futura)

| Item | Descrição |
|------|-----------|
| **Fonte** | CHIRPS (Climate Hazards Group) |
| **Site** | https://www.chc.ucsb.edu/data/chirps |
| **Tipo de dado** | Precipitação em grade (satélite) |
| **Resolução** | 0.05° (~5km) |
| **Período** | 1981-presente (atualizado mensalmente) |
| **Formato** | GeoTIFF, NetCDF |

**Prompt para buscar dados:**

```
AÇÃO: Baixar precipitação CHIRPS para Bacia Amazônica

PASSO 1: Acesse https://data.chc.ucsb.edu/products/CHIRPS-2.0/

PASSO 2: Navegue até: global_daily/tifs/p05/ (resolução 0.05°)

PASSO 3: Selecione os anos desejados (ex: 2020/, 2021/, 2022/, 2023/)

PASSO 4: Baixe arquivos GeoTIFF diários para o período

ALTERNATIVA MAIS FÁCIL: Use Google Earth Engine API (requer cadastro)

RESULTADO ESPERADO: Arquivos TIFF diários com precipitação em mm
```

**Código para processar CHIRPS:**
```python
import rasterio
import numpy as np
import pandas as pd
from glob import glob

def extrair_precipitacao_bacia(tiff_files, bbox_amazonia):
    """
    Extrai precipitação média da Bacia Amazônica

    bbox_amazonia: (lon_min, lat_min, lon_max, lat_max)
    Exemplo: (-75, -10, -50, 2) # Bacia Amazônica aproximada
    """
    resultados = []

    for tiff_file in tiff_files:
        # Extrair data do nome do arquivo (formato: chirps-v2.0.2020.01.01.tif)
        data_str = tiff_file.split('.')[-4:-1]  # ['2020', '01', '01']
        data = pd.to_datetime('.'.join(data_str))

        # Abrir raster
        with rasterio.open(tiff_file) as src:
            # Recortar bbox da Amazônia
            window = src.window(*bbox_amazonia)
            data_array = src.read(1, window=window)

            # Calcular precipitação média na bacia (ignorar nodata)
            precip_media = np.nanmean(data_array[data_array >= 0])

            resultados.append({
                'data': data,
                'precip_mm': precip_media
            })

    df = pd.DataFrame(resultados)
    print(f"✅ CHIRPS: {len(df)} dias de precipitação processados")
    print(f"   Precipitação média: {df['precip_mm'].mean():.2f} mm/dia")

    return df

# ALTERNATIVA: Usar pacote Python chirps
# pip install chirps
from chirps import get_data

def buscar_chirps_api(bbox, data_inicio, data_fim):
    """Busca CHIRPS via API (mais fácil)"""
    lon_min, lat_min, lon_max, lat_max = bbox

    df = get_data(
        lon_min=lon_min,
        lat_min=lat_min,
        lon_max=lon_max,
        lat_max=lat_max,
        start_date=data_inicio,
        end_date=data_fim
    )

    return df

# Criar feature de precipitação acumulada
def calcular_precip_acumulada(df, dias=[7, 15, 30, 60]):
    """Calcula precipitação acumulada em diferentes janelas"""
    for d in dias:
        df[f'precip_{d}d'] = df['precip_mm'].rolling(window=d).sum()

    return df

# Uso:
# Bounding box da Bacia Amazônica
bbox_amazonia = (-75, -10, -50, 2)

tiff_files = glob('chirps_tiffs/*.tif')
df_chuva = extrair_precipitacao_bacia(tiff_files, bbox_amazonia)
df_chuva = calcular_precip_acumulada(df_chuva, dias=[30, 60])

print(df_chuva.head())
```

**Troubleshooting:**
- ❌ **Muitos arquivos:** Processe por mês, depois concatene
- ❌ **Memória insuficiente:** Use amostragem espacial (ex: 0.25° em vez de 0.05°)
- ❌ **Muito complexo:** Use apenas estações pluviométricas da ANA (mais simples)

---

### 🎯 **VARIÁVEL 5: Nível de Água Observado (TARGET)**

**CRÍTICO:** Sem isso você não consegue treinar o modelo!

| Item | Descrição |
|------|-----------|
| **Fonte** | Porto, Marinha, ou ANA |
| **Tipo de dado** | Observações de régua/sensor (nível em metros) |
| **Período** | Mesmo dos features (3-10 anos) |
| **Frequência** | Horária ou sub-horária |
| **Formato** | CSV, TXT, banco de dados |

**Prompt para buscar dados:**

```
AÇÃO: Obter observações reais do nível de água

OPÇÃO 1: Contato com o Porto
- Entre em contato com a Autoridade Portuária
- Solicite dados históricos de nível de água
- Especifique: período, frequência, datum de referência

OPÇÃO 2: Centro de Hidrografia da Marinha (CHM)
- Site: https://www.marinha.mil.br/chm/
- Alguns dados podem estar disponíveis publicamente
- Pode ser necessário solicitação formal

OPÇÃO 3: ANA (para portos fluviais/estuarinos)
- HidroWeb: https://www.snirh.gov.br/hidroweb/
- Busque estações linigráficas próximas ao porto
- Tipo: Fluviométrica, Variável: Cota (nível)

INFORMAÇÕES NECESSÁRIAS:
- Data e hora de cada observação
- Nível em metros (ou centímetros)
- Datum de referência (ex: marégrafo zero, DHN)
- Qualidade/consistência do dado

RESULTADO ESPERADO: CSV com:
- data_hora
- nivel_observado_m
- qualidade (opcional)
```

**Código para processar observações:**
```python
import pandas as pd

def carregar_observacoes_porto(arquivo_csv):
    """Carrega observações reais do nível de água"""
    # Formato varia por porto - ajustar conforme necessário
    df = pd.read_csv(arquivo_csv)

    df['data_hora'] = pd.to_datetime(df['data_hora'])
    df['nivel_obs_m'] = pd.to_numeric(df['nivel_obs_m'], errors='coerce')

    # Remover outliers óbvios
    q1 = df['nivel_obs_m'].quantile(0.01)
    q99 = df['nivel_obs_m'].quantile(0.99)
    df = df[(df['nivel_obs_m'] >= q1) & (df['nivel_obs_m'] <= q99)]

    print(f"✅ Observações: {len(df)} registros carregados")
    print(f"   Período: {df['data_hora'].min()} até {df['data_hora'].max()}")
    print(f"   Nível médio: {df['nivel_obs_m'].mean():.2f} m")
    print(f"   Amplitude: {df['nivel_obs_m'].min():.2f} a {df['nivel_obs_m'].max():.2f} m")

    return df

# Validar qualidade: comparar com previsão astronômica
def validar_observacoes(df_obs, df_mare_astro):
    """Verifica se observações são consistentes"""
    # Merge por data/hora
    df_merged = pd.merge(df_obs, df_mare_astro,
                         left_on='data_hora', right_on='Data_Hora',
                         how='inner')

    # Calcular resíduo (diferença entre observado e astronômico)
    df_merged['residuo'] = df_merged['nivel_obs_m'] - df_merged['Altura_m']

    print("\n📊 Validação das observações:")
    print(f"   Resíduo médio: {df_merged['residuo'].mean():.3f} m")
    print(f"   Std do resíduo: {df_merged['residuo'].std():.3f} m")
    print(f"   Resíduo máximo: {df_merged['residuo'].max():.3f} m")
    print(f"   Resíduo mínimo: {df_merged['residuo'].min():.3f} m")

    # Se resíduo médio >> 0, pode haver offset de datum
    if abs(df_merged['residuo'].mean()) > 0.5:
        print("   ⚠️  ALERTA: Resíduo médio muito alto - verificar datum de referência!")

    return df_merged

# Uso:
df_obs = carregar_observacoes_porto('viladoconde_observacoes_2020_2023.csv')
df_mare = pd.read_csv('viladoconde_extremos_2020_2026.csv')
df_validado = validar_observacoes(df_obs, df_mare)
```

---

### 🎯 **CHECKLIST FINAL: Antes de Treinar o Modelo**

Use este checklist para garantir que você tem todos os dados necessários:

```
PORT ESPECÍFICO: [Ex: Vila do Conde]

□ MARÉ ASTRONÔMICA (Baseline)
  ✅ Arquivo CSV deste projeto: viladoconde_extremos_2020_2026.csv
  ✅ Período coberto: 2020-2026
  ✅ Total de registros: _______

□ VAZÃO FLUVIAL (Se aplicável)
  □ Baixado da ANA HidroWeb
  □ Estação Amazonas (15400000): _______ registros
  □ Estação Tocantins (29280000): _______ registros
  □ Período: _______ até _______
  □ Vazão média: _______ m³/s

□ METEOROLOGIA (INMET)
  □ Baixado do portal INMET
  □ Estação: _______ (código: _______)
  □ Variáveis: ☐ Vento ☐ Pressão ☐ Temp ☐ Precip
  □ Período: _______ até _______
  □ Total de registros: _______

□ PRECIPITAÇÃO DE BACIA (Se aplicável)
  □ Fonte: ☐ CHIRPS ☐ ANA ☐ INMET
  □ Período: _______ até _______
  □ Acumulados calculados: ☐ 7d ☐ 15d ☐ 30d ☐ 60d

□ OBSERVAÇÕES REAIS (TARGET) **CRÍTICO**
  □ Fonte: ☐ Porto ☐ Marinha ☐ ANA
  □ Arquivo: _________________________
  □ Período: _______ até _______
  □ Total de registros: _______
  □ Nível médio: _______ m
  □ Validado com maré astronômica: ☐ Sim

□ INTEGRAÇÃO
  □ Todos os DataFrames no mesmo timezone (UTC)
  □ Todos os dados no mesmo período (overlap)
  □ Merge feito por data/hora (sem perda de registros)
  □ Valores faltantes tratados (interpolação/ffill)
  □ Outliers removidos

□ PRONTO PARA TREINAR!
  □ Features (X): _______ colunas
  □ Target (y): nivel_observado
  □ Total de amostras: _______
  □ Train/test split: ___ / ___
```

---

### 📝 Template de Script Completo

Use este template como ponto de partida:

```python
"""
Script de Treinamento - Previsão de Marés com ML
Porto: [NOME DO PORTO]
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

# ============================================
# 1. CARREGAR TODOS OS DADOS
# ============================================

print("📂 Carregando dados...")

# Maré astronômica (este projeto)
df_mare = pd.read_csv('viladoconde_extremos_2020_2026.csv')
df_mare['Data_Hora'] = pd.to_datetime(df_mare['Data_Hora'])

# Vazão (ANA)
df_vazao_amz = carregar_vazao_ana_csv('obidos_15400000.csv')
df_vazao_toc = carregar_vazao_ana_csv('tucurui_29280000.csv')

# Meteorologia (INMET)
df_meteo = carregar_dados_inmet('INMET_A230_BELEM.csv', 'A230')

# Precipitação (CHIRPS)
df_chuva = pd.read_csv('chirps_amazonia_2020_2023.csv')
df_chuva['data'] = pd.to_datetime(df_chuva['data'])

# Observações (TARGET)
df_obs = carregar_observacoes_porto('viladoconde_observacoes.csv')

print("✅ Todos os dados carregados")

# ============================================
# 2. MERGE DE TODOS OS DATAFRAMES
# ============================================

print("\n🔗 Fazendo merge dos dados...")

# Merge maré + observações
df = pd.merge(df_mare, df_obs,
              left_on='Data_Hora', right_on='data_hora',
              how='inner')

# Merge com vazão
df = pd.merge(df, df_vazao_amz,
              left_on='Data_Hora', right_on='data',
              how='left', suffixes=('', '_amz'))

df = pd.merge(df, df_vazao_toc,
              left_on='Data_Hora', right_on='data',
              how='left', suffixes=('', '_toc'))

# Merge com meteorologia
df = pd.merge(df, df_meteo,
              left_on='Data_Hora', right_on='data_hora',
              how='left', suffixes=('', '_meteo'))

# Merge com precipitação
df = pd.merge(df, df_chuva,
              left_on=df['Data_Hora'].dt.date, right_on='data',
              how='left')

print(f"✅ Merge completo: {len(df)} amostras")

# ============================================
# 3. FEATURE ENGINEERING
# ============================================

print("\n⚙️  Criando features...")

# Vazão total
df['vazao_total'] = df['vazao_m3s_amz'] + df['vazao_m3s_toc']

# Features temporais
df['mes'] = df['Data_Hora'].dt.month
df['dia_ano'] = df['Data_Hora'].dt.dayofyear
df['hora'] = df['Data_Hora'].dt.hour

# Features de vento sul
df = calcular_features_vento_sul(df)

# Precipitação acumulada
df = calcular_precip_acumulada(df, dias=[30, 60])

# Features finais
features_cols = [
    'Altura_m',          # Maré astronômica
    'vazao_total',       # Vazão
    'vento_vel',         # Vento
    'vento_sul_max_48h', # Vento sul
    'pressao',           # Pressão
    'precip_30d',        # Chuva 30d
    'precip_60d',        # Chuva 60d
    'mes',               # Sazonalidade
]

target_col = 'nivel_obs_m'

# Remover NaN
df = df.dropna(subset=features_cols + [target_col])

print(f"✅ Features criadas: {len(features_cols)} variáveis")
print(f"✅ Amostras finais: {len(df)}")

# ============================================
# 4. TREINAR MODELO
# ============================================

print("\n🤖 Treinando modelo...")

X = df[features_cols]
y = df[target_col]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

modelo = RandomForestRegressor(
    n_estimators=100,
    max_depth=20,
    random_state=42,
    n_jobs=-1
)

modelo.fit(X_train, y_train)

# ============================================
# 5. AVALIAR MODELO
# ============================================

print("\n📊 Avaliando modelo...")

y_pred_train = modelo.predict(X_train)
y_pred_test = modelo.predict(X_test)

mae_train = mean_absolute_error(y_train, y_pred_train)
mae_test = mean_absolute_error(y_test, y_pred_test)
r2_train = r2_score(y_train, y_pred_train)
r2_test = r2_score(y_test, y_pred_test)

print(f"   MAE Treino: {mae_train:.3f} m")
print(f"   MAE Teste:  {mae_test:.3f} m")
print(f"   R² Treino:  {r2_train:.3f}")
print(f"   R² Teste:   {r2_test:.3f}")

# Importância das features
importances = pd.DataFrame({
    'feature': features_cols,
    'importance': modelo.feature_importances_
}).sort_values('importance', ascending=False)

print("\n🔍 Importância das features:")
print(importances)

# ============================================
# 6. SALVAR MODELO
# ============================================

print("\n💾 Salvando modelo...")
joblib.dump(modelo, 'modelo_viladoconde.pkl')
print("✅ Modelo salvo: modelo_viladoconde.pkl")

print("\n🎉 Treinamento concluído com sucesso!")
```

---

**Porto de Paranaguá - Correções Meteorológicas:**
- Ventos sul e frentes frias como features meteorológicas
- Ressacas podem adicionar +1m ao nível previsto

**Vila do Conde (Barcarena):**
- Feature principal: Previsão astronômica (este projeto)
- **Feature fluvial crítica:** Vazão dos rios Amazonas e Tocantins
- Target: Altura real observada
- Desvios sazonais significativos devido à descarga fluvial
- Distorção de assimetria capturada por componentes M4 (0.054m) e M6 (0.021m)
- Modelo deve aprender que a maré sobe mais rápido do que desce

## Referências

- Marinha do Brasil - Centro de Hidrografia da Marinha (CHM)
- Diretoria de Hidrografia e Navegação (DHN)
- Fichas de Marés: https://www.marinha.mil.br/chm/

## Autor

Scripts baseados nas constantes harmônicas oficiais das fichas de maré da Marinha do Brasil.
