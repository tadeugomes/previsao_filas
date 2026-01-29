# Investigação: Aplicativo Streamlit - Previsões e Inconsistências

**Data da Investigação:** 2026-01-27
**Investigador:** Claude Agent
**Objetivo:** Avaliar se o aplicativo Streamlit está adequado para fazer previsões, identificar inconsistências entre ETA e previsões do modelo, e analisar o alinhamento entre colunas do app e variáveis do modelo.

---

## 1. Resumo Executivo

O aplicativo Streamlit (`streamlit_app.py`) está **funcional** mas apresenta **várias inconsistências e limitações** importantes:

### Problemas Identificados:
1. **Discrepância entre colunas do lineup e features do modelo** - O modelo Premium (Ponta da Madeira) requer dados específicos que geralmente não estão disponíveis nos lineups básicos
2. **Inconsistência entre ETA do lineup e ETA previsto** - O cálculo de `eta_mais_espera` soma a espera prevista ao ETA original, mas isso pode causar confusão sobre o que é ETA "real"
3. **Valores default inadequados** - Muitas features críticas recebem valores default (0 ou "DESCONHECIDO") quando não estão disponíveis
4. **Falta de validação de entrada** - O app não valida se os dados de entrada são adequados para o modelo selecionado
5. **Modelos com performance questionável** - O modelo Premium (Ponta da Madeira) tem métricas ruins (MAE: 120h, R²: 0.001)

---

## 2. Análise Detalhada das Colunas e Features

### 2.1 Modelo VEGETAL (Básico)

**Features Esperadas (54 features):**
```python
[
    "nome_porto", "nome_terminal", "tipo_navegacao", "tipo_carga",
    "natureza_carga", "cdmercadoria", "stsh4", "movimentacao_total_toneladas",
    "mes", "dia_semana", "navios_no_fundeio_na_chegada", "navios_na_fila_7d",
    "tempo_espera_ma5", "dia_do_ano", "porto_tempo_medio_historico",
    "temp_media_dia", "precipitacao_dia", "vento_rajada_max_dia",
    "vento_velocidade_media", "umidade_media_dia", "amplitude_termica",
    "restricao_vento", "restricao_chuva", "flag_celulose", "flag_algodao",
    "flag_soja", "flag_milho", "periodo_safra", "producao_soja",
    "producao_milho", "producao_algodao", "preco_soja_mensal",
    "preco_milho_mensal", "preco_algodao_mensal", "indice_pressao_soja",
    "indice_pressao_milho", "ais_navios_no_raio", "ais_fila_ao_largo",
    "ais_velocidade_media_kn", "ais_eta_media_horas", "ais_dist_media_km",
    "wave_height_max", "wave_height_media", "frente_fria",
    "pressao_anomalia", "ressaca", "mare_astronomica", "mare_subindo",
    "mare_horas_ate_extremo", "tem_mare_astronomica",
    "chuva_acumulada_ultimos_3dias"
]
```

**Colunas Esperadas no Lineup de Entrada:**
```python
["Navio", "Mercadoria", "Chegada", "Berco", "DWT"]
```

**PROBLEMA:** O modelo espera 54 features, mas o lineup fornece apenas 5 colunas básicas. O app preenche as 49 features restantes com:
- **Valores hardcoded** (tipo_navegacao="Longo Curso", tipo_carga="Granel")
- **Valores default** (cdmercadoria="0000", producao_soja=0, preços=valores fixos)
- **Valores derivados simples** (mes, dia_ano extraídos da data de chegada)
- **Valores de contexto** (clima do dia, dados AIS se disponíveis)

### 2.2 Modelo MINERAL (Básico)

**Features Esperadas (38 features):**
Similares ao VEGETAL, mas sem features específicas de oceano/maré como:
- `vento_velocidade_media` (presente no VEGETAL)
- Features de maré e oceano

**Observação:** O modelo MINERAL tem menos features mas ainda sofre do mesmo problema de valores default.

### 2.3 Modelo PONTA DA MADEIRA (Premium)

**Features Esperadas (10 features):**
```python
[
    "pier", "prancha_ma5_pier", "gap_prancha_pct", "dwt",
    "laytime_horas", "urgencia_alta", "navios_no_fundeio_na_chegada",
    "mes", "dia_ano", "incoterm"
]
```

**Colunas Esperadas no Lineup de Entrada (Premium):**
```python
[
    "Pier", "DWT", "TX_COMERCIAL", "TX_EFETIVA", "Laytime",
    "INCOTERM", "Chegada" (ou "Atracacao"), "Estadia"
]
```

**PROBLEMA CRÍTICO:** Este modelo requer dados operacionais específicos que:
- **Raramente estão disponíveis** em lineups públicos
- **São dados internos** do terminal (taxas comerciais, taxas efetivas, laytime)
- **Requerem histórico** para calcular `prancha_ma5_pier` (média móvel das últimas 5 taxas efetivas por pier)

**Configuração Premium Registry:**
```json
{
  "name": "PONTA_DA_MADEIRA",
  "requires_terminal_data": true,  // ← Indica que precisa de dados do terminal
  "mae_esperado": 30,               // ← MAE esperado (vs 120h real!)
  "profiles": ["MINERAL"]
}
```

---

## 3. Inconsistências entre ETA e Previsões

### 3.1 Definições no Código

**streamlit_app.py:1258-1262**
```python
eta = pd.to_datetime(df_out["data_chegada_dt"], errors="coerce")
eta_espera = eta + pd.to_timedelta(df_out["tempo_espera_previsto_horas"].fillna(0), unit="h")
df_out["eta_mais_espera"] = eta_espera
```

### 3.2 O Problema de Nomenclatura

**ETA_lineup vs ETA_com_espera:**
- `ETA_lineup` = Data/hora de chegada informada no lineup (coluna "Chegada")
- `Espera_prevista_h` = Horas de espera previstas pelo modelo
- `ETA_com_espera` = ETA_lineup + Espera_prevista_h
- `Atraso_vs_ETA_h` = Diferença em horas entre ETA_com_espera e ETA_lineup

**Fonte de Confusão:**
O termo "ETA" (Estimated Time of Arrival) tradicionalmente significa a hora prevista de CHEGADA ao fundeio, não de atracação. O app calcula:
```
ETA_com_espera = ETA_chegada + tempo_espera
```

Isso é na verdade um **ETB (Estimated Time of Berthing)** - hora estimada de atracação.

### 3.3 Comparativo de Lineup

**streamlit_app.py:2281-2288** - Definições exibidas ao usuário:
```
- ETA_lineup: horário de chegada informado no line-up
- Espera_prevista_h: horas estimadas de espera antes de atracar
- ETA_com_espera: data e hora estimadas de atracação considerando ETA + espera
- Atraso_vs_ETA_h: diferença em horas entre ETA do lineup e atracação prevista
```

**INCONSISTÊNCIA:**
O "Atraso_vs_ETA_h" na verdade não é um atraso no sentido tradicional - é o tempo de espera previsto. Se um navio tem:
- ETA_lineup: 2026-01-27 10:00
- Espera_prevista_h: 48h
- ETA_com_espera: 2026-01-29 10:00
- Atraso_vs_ETA_h: 48h

O valor "48h" **NÃO significa que o navio está atrasado** em relação ao plano original. Significa que o modelo prevê que o navio vai esperar 48h no fundeio antes de atracar.

### 3.4 Posições na Fila

**streamlit_app.py:1781-1791**
```python
df["posicao_lineup"] = np.arange(1, len(df) + 1)  # Ordem no lineup original
if "eta_mais_espera" in df.columns:
    eta = pd.to_datetime(df["eta_mais_espera"], errors="coerce")
    df["posicao_prevista"] = eta.rank(method="first")  # Ordem prevista pelo modelo
```

**PROBLEMA:**
- `posicao_lineup` assume que a ordem no arquivo CSV/Excel é a ordem de chegada planejada
- `posicao_prevista` é baseada em `eta_mais_espera` (ETA + espera prevista)
- Se dois navios têm ETAs próximos mas esperas muito diferentes, podem trocar de posição

**Exemplo de Inconsistência:**
```
Navio A: ETA = 10:00, Espera = 10h → eta_mais_espera = 20:00, Posicao = 2
Navio B: ETA = 12:00, Espera = 2h  → eta_mais_espera = 14:00, Posicao = 1
```
Navio B "passa na frente" de A na previsão, mas isso pode ser confuso se o lineup original previa A antes de B.

---

## 4. Análise da Qualidade dos Modelos

### 4.1 Modelo PONTA DA MADEIRA (Premium)

**Métricas de Performance:**
```json
"test_ensemble": {
  "mae": 120.61,      // MAE de 120 horas (~5 dias)
  "rmse": 152.67,     // RMSE de 152 horas (~6.3 dias)
  "r2": 0.0016        // R² próximo de zero (modelo não explica variância)
}
```

**Análise:**
- **MAE de 120h é MUITO ALTO** - erros médios de 5 dias não são aceitáveis para operação portuária
- **R² de 0.001 indica que o modelo é quase tão bom quanto prever a média** para todos os casos
- O premium_registry.json diz `"mae_esperado": 30` mas o real é **120h** (4x pior!)

### 4.2 Modelos Básicos (VEGETAL, MINERAL, FERTILIZANTE)

**Observação:** Não há reports JSON para esses modelos, apenas os arquivos de metadados. Isso dificulta avaliar a performance real.

**Arquivos de modelo muito pequenos (132-133 bytes):**
```bash
-rw-r--r-- 132 fertilizante_lgb_reg.pkl
-rw-r--r-- 132 mineral_lgb_reg.pkl
-rw-r--r-- 132 vegetal_lgb_reg.pkl
```

**ALERTA:** Modelos LightGBM/XGBoost treinados normalmente têm centenas de KB ou MB. Arquivos de 132 bytes sugerem:
- Modelos não foram treinados adequadamente
- São placeholders/stubs
- Podem ser apenas metadados sem árvores reais

---

## 5. Fluxo de Dados e Transformações

### 5.1 Pipeline de Previsão

```
1. Usuário carrega lineup (CSV/Excel/Parquet)
   ↓
2. App normaliza colunas e extrai ["Navio", "Mercadoria", "Chegada", "Berco", "DWT"]
   ↓
3. App identifica perfil (VEGETAL/MINERAL/FERTILIZANTE) baseado em keywords na "Mercadoria"
   ↓
4. App carrega modelo correspondente ao perfil
   ↓
5. build_features_from_lineup() cria as 38-54 features:
   - Copia colunas disponíveis (DWT → movimentacao_total_toneladas)
   - Adiciona features temporais (mes, dia_ano, dia_semana)
   - Adiciona features de contexto (clima, AIS se disponível)
   - Preenche features faltantes com valores default (0, "DESCONHECIDO")
   ↓
6. Modelo faz previsão:
   - Regressor: tempo_espera_horas
   - Classificador: classe_espera (Rápido/Médio/Longo)
   ↓
7. App calcula métricas derivadas:
   - eta_mais_espera = ETA_chegada + tempo_espera_horas
   - posicao_prevista (ranking por eta_mais_espera)
   ↓
8. Se porto é PREMIUM (Ponta da Madeira) e tem dados de terminal:
   build_premium_features_ponta_da_madeira() cria features específicas
   - Requer: Pier, DWT, TX_COMERCIAL, TX_EFETIVA, Laytime, INCOTERM
   - Calcula: prancha_ma5_pier, gap_prancha_pct, urgencia_alta
   - Modelo premium sobrescreve previsão básica
   ↓
9. App exibe comparativo ao usuário
```

### 5.2 Problemas no Fluxo

**Problema 1: Validação Ausente**
- Não há validação se o lineup tem as colunas mínimas necessárias
- Se "Chegada" estiver faltando, app usa "Atualizacao" ou "ExtraidoEm" como fallback
- Isso pode causar previsões baseadas em datas erradas

**Problema 2: Modo Premium Sem Dados**
```python
# streamlit_app.py:1272-1275
usar_premium = premium_cfg is not None and (
    not premium_cfg.get("requires_terminal_data", True) or tem_dados_terminal
)
```

Se `tem_dados_terminal=False` mas `requires_terminal_data=True`, o app usa modelo básico, mas **não avisa o usuário** que está usando um modelo inferior.

**Problema 3: Features Calculadas Incorretamente**
```python
# streamlit_app.py:1019
df["navios_no_fundeio_na_chegada"] = df.index.astype(float)
```

Isso simplesmente usa o índice da linha como "navios no fundeio", o que é **incorreto**. O correto seria calcular quantos navios já chegaram mas ainda não atracaram no momento da chegada deste navio.

---

## 6. Recomendações

### 6.1 Recomendações Críticas (Alta Prioridade)

#### 1. **Re-treinar ou Desabilitar o Modelo Premium**
- **Motivo:** MAE de 120h (5 dias) não é aceitável para operação portuária
- **Ação:** Investigar por que o modelo tem performance tão ruim
  - Verificar qualidade dos dados de treino (lineups/Ponta_da_Madeira.xlsx)
  - Considerar adicionar mais features (clima, AIS, dados de mercado)
  - Avaliar se há vazamento de dados (data leakage) ou overfitting

#### 2. **Validar Tamanho dos Modelos Básicos**
- **Motivo:** Arquivos de 132 bytes são suspeitos
- **Ação:**
  ```bash
  python3 -c "import joblib; m = joblib.load('models/vegetal_lgb_reg.pkl'); print(m)"
  ```
  Se os modelos não estiverem treinados, re-treinar antes de usar em produção

#### 3. **Corrigir Nomenclatura de ETA**
- **Motivo:** Confusão entre ETA (chegada) e ETB (atracação)
- **Ação:** Renomear colunas:
  - `ETA_com_espera` → `ETB_previsto` (Estimated Time of Berthing)
  - `Atraso_vs_ETA_h` → `Tempo_espera_h` (tempo de espera, não atraso)

**Código sugerido:**
```python
# Antes
df_out["eta_mais_espera"] = eta_espera
data["ETA_com_espera"] = format_datetime_table(eta_espera)
data["Atraso_vs_ETA_h"] = atraso_h.round(2)

# Depois
df_out["etb_previsto"] = eta_espera
data["ETB_previsto"] = format_datetime_table(eta_espera)
data["Tempo_espera_previsto_h"] = atraso_h.round(2)
```

#### 4. **Adicionar Validação de Entrada**
- **Motivo:** Prevenir previsões com dados inadequados
- **Ação:** Adicionar checks em `build_features_from_lineup()`:

```python
def validate_lineup_data(df_lineup, profile, is_premium=False):
    """Valida se o lineup tem os dados mínimos necessários"""
    errors = []
    warnings = []

    # Validações básicas
    required_cols = ["Navio", "Chegada"]
    for col in required_cols:
        if col not in df_lineup.columns:
            errors.append(f"Coluna obrigatória ausente: {col}")

    # Validações específicas de premium
    if is_premium:
        premium_cols = ["Pier", "DWT", "TX_COMERCIAL", "TX_EFETIVA", "Laytime", "INCOTERM"]
        missing = [c for c in premium_cols if c not in df_lineup.columns]
        if missing:
            warnings.append(f"Modelo premium requer: {', '.join(missing)}")
            warnings.append("Usando modelo básico como fallback")

    return errors, warnings
```

#### 5. **Corrigir Cálculo de `navios_no_fundeio_na_chegada`**
- **Motivo:** Feature crítica calculada incorretamente
- **Ação:** Implementar cálculo correto baseado em eventos de chegada/atracação:

```python
def calcular_fila_real(df_lineup):
    """Calcula número de navios no fundeio no momento da chegada de cada navio"""
    df = df_lineup.copy()
    df = df.sort_values("data_chegada_dt").reset_index(drop=True)

    # Supondo que temos ou estimamos tempo de atracação
    if "data_atracacao_dt" not in df.columns:
        # Estima atracação = chegada + espera prevista (ou média histórica)
        df["data_atracacao_dt"] = df["data_chegada_dt"] + pd.Timedelta(hours=48)

    chegadas = df["data_chegada_dt"].to_numpy()
    atracacoes = np.sort(df["data_atracacao_dt"].to_numpy())

    fila = np.zeros(len(df))
    for i, chegada in enumerate(chegadas):
        # Quantos navios já chegaram mas ainda não atracaram?
        atracadas_antes = np.searchsorted(atracacoes, chegada, side="right")
        fila[i] = max(i - atracadas_antes, 0)

    return fila
```

### 6.2 Recomendações Importantes (Média Prioridade)

#### 6. **Adicionar Métricas de Confiança**
- Exibir ao usuário o MAE esperado para cada previsão
- Adicionar intervalos de confiança (ex: "Espera prevista: 48h ± 30h")

#### 7. **Melhorar Feedback Visual**
- Usar cores/ícones para indicar qualidade dos dados:
  - 🟢 Verde: Dados completos, modelo premium
  - 🟡 Amarelo: Dados parciais, modelo básico
  - 🔴 Vermelho: Dados insuficientes, previsão não confiável

#### 8. **Adicionar Log de Features**
- Permitir usuário ver quais features foram usadas e seus valores
- Ajuda a debugar previsões estranhas

#### 9. **Implementar Modo "Simulação"**
- Permitir usuário ajustar features manualmente (ex: fila_atual, clima)
- Ver como a previsão muda com diferentes cenários

#### 10. **Adicionar Validação Cross-Model**
- Para portos com modelo premium, mostrar também previsão do modelo básico
- Alertar se há grande discrepância entre os dois

### 6.3 Recomendações de Longo Prazo

#### 11. **Criar Dataset de Validação Online**
- Salvar previsões feitas pelo app e comparar com realidade depois
- Calcular MAE real do app em produção

#### 12. **Adicionar Explicabilidade (SHAP)**
- Mostrar quais features mais influenciaram cada previsão
- Ajuda usuários a entender e confiar nas previsões

#### 13. **Implementar Modelo Híbrido**
- Combinar modelo de ML com regras de negócio (ex: prioridade de carga, políticas do porto)
- Melhorar acurácia em casos especiais

---

## 7. Checklist de Ações Imediatas

- [ ] **Verificar tamanho real dos modelos PKL** (se são >1KB, provavelmente estão OK)
- [ ] **Adicionar validation_report.py** para validar modelos carregados
- [ ] **Renomear `ETA_com_espera` → `ETB_previsto`** no código e interface
- [ ] **Adicionar função `validate_lineup_data()`** antes de fazer previsões
- [ ] **Corrigir cálculo de `navios_no_fundeio_na_chegada`**
- [ ] **Adicionar warnings quando usar modelo básico em vez de premium**
- [ ] **Atualizar `premium_registry.json` com MAE real (120h, não 30h)**
- [ ] **Adicionar coluna "Confiança" ou "MAE_esperado" na tabela de resultados**
- [ ] **Criar documentação clara sobre diferença entre ETA (chegada) e ETB (atracação)**
- [ ] **Investigar por que modelo Ponta da Madeira tem R² = 0.001**

---

## 8. Exemplo de Uso Correto vs Incorreto

### Uso Incorreto (Atual):
```
Usuário carrega lineup com apenas [Navio, Mercadoria, Chegada, Berco]
App faz previsão com 50+ features preenchidas com defaults
Modelo retorna tempo_espera = 72h (3 dias)
App mostra "ETA_com_espera" = Chegada + 72h
Usuário vê "Atraso_vs_ETA_h: 72h" e pensa que o navio está 3 dias atrasado
```

### Uso Correto (Proposto):
```
Usuário carrega lineup com apenas [Navio, Mercadoria, Chegada, Berco]
App detecta que faltam dados críticos e mostra warning:
  "⚠️ Dados insuficientes. Previsão baseada em dados limitados (MAE esperado: 79h)"
App faz previsão com modelo básico
Modelo retorna tempo_espera = 72h (3 dias)
App mostra:
  - "ETA (Chegada prevista)": <data original>
  - "Tempo de espera previsto": 72h ± 79h
  - "ETB (Atracação prevista)": <data + 72h>
  - "Confiança": Baixa 🔴
Usuário entende que é uma ESTIMATIVA de quando vai atracar, não um atraso
```

---

## 9. Conclusão

O aplicativo Streamlit está **funcional mas precisa de melhorias significativas** antes de ser usado em produção:

### Pontos Positivos:
- ✅ Arquitetura bem organizada (modelos separados por perfil)
- ✅ Interface de usuário clara e profissional
- ✅ Suporte a múltiplos formatos de entrada (CSV, Excel, Parquet)
- ✅ Integração com APIs de clima e AIS

### Pontos Críticos:
- ❌ Modelo premium tem performance muito ruim (MAE: 120h vs esperado: 30h)
- ❌ Nomenclatura confusa (ETA vs ETB, "atraso" vs "espera")
- ❌ Falta de validação de entrada
- ❌ Features críticas calculadas incorretamente (`navios_no_fundeio_na_chegada`)
- ❌ Tamanho suspeito dos modelos básicos (132 bytes)
- ❌ Uso excessivo de valores default sem avisar ao usuário

### Recomendação Final:
**Não usar o app em produção** sem antes:
1. Validar que os modelos estão corretamente treinados
2. Implementar validações de entrada
3. Corrigir nomenclatura e cálculos incorretos
4. Adicionar feedback claro sobre confiança das previsões

O app pode ser usado como **protótipo demonstrativo**, mas requer melhorias significativas para uso operacional real.

---

**Fim do Relatório**
