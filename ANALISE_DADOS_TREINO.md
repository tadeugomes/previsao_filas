# Análise: Impossibilidade de Treinar Modelos Reais

**Data:** 2026-01-28
**Status:** ❌ **BLOQUEADO - Dados insuficientes**
**Branch:** `claude/investigate-streamlit-predictions-jjmNg`

---

## 🔍 Problema Identificado

O arquivo `lineups_previstos/lineup_history.parquet` **NÃO** possui os dados necessários para treinar modelos de machine learning.

### O que o arquivo TEM (389 registros, 19 colunas):

```
✅ Dados de previsão:
   - prev_chegada: Data/hora prevista de chegada
   - navio, imo: Identificação do navio
   - porto, berco: Localização
   - carga, produto, operacao: Tipo de carga
   - dwt, comp(m), calado(m): Características do navio
   - agencia, ultima_atualizacao: Metadados
```

### O que o arquivo NÃO TEM:

```
❌ Variável TARGET (crítico):
   - tempo_espera_horas: AUSENTE
   - data_atracacao: AUSENTE
   - hora_atracacao: AUSENTE
   - atracacao_efetiva: AUSENTE
   - data_inicio_operacao: AUSENTE

❌ Features engineeradas:
   - navios_no_fundeio_na_chegada
   - porto_tempo_medio_historico
   - tempo_espera_ma5
   - navios_na_fila_7d
   - precipitacao_dia
   - vento_rajada_max_dia
   - (e mais 9 features)
```

---

## ⚠️ Por Que Isso é Crítico

### 1. **Sem TARGET, não há treino**

Machine learning supervisionado requer:
```
X (features) → MODELO → y (target)
```

Para treinar modelos de previsão de tempo de espera, precisamos:

```python
# O que precisamos:
y = tempo_espera_horas = data_atracacao - prev_chegada

# O que temos:
prev_chegada = ✅ Disponível
data_atracacao = ❌ AUSENTE

# Resultado:
y = ❌ IMPOSSÍVEL CALCULAR
```

### 2. **Features históricas dependem do target**

Features como `porto_tempo_medio_historico` e `tempo_espera_ma5` são calculadas a partir de tempos de espera passados:

```python
# Exemplo:
porto_tempo_medio_historico = mean(tempo_espera_horas dos últimos 30 dias)

# Mas:
tempo_espera_horas = ❌ NÃO EXISTE
```

---

## 💡 Soluções Possíveis

### **Opção 1: Obter Dados Históricos Completos** ⭐ RECOMENDADO

Buscar fonte de dados que contenha **chegada prevista E atracação efetiva**:

#### Fontes potenciais:

1. **Sistema portuário oficial**
   - Autoridade Portuária
   - APIs de gestão portuária
   - Banco de dados operacional

2. **Dados AIS (Automatic Identification System)**
   - Serviços como MarineTraffic, VesselFinder
   - Logs de posição históricos
   - Timestamps de chegada/saída de área portuária

3. **Relatórios operacionais**
   - Planilhas de controle interno
   - Relatórios de atracação
   - Logs de berço

#### Formato ideal:

```csv
navio,imo,porto,berco,prev_chegada,data_atracacao,carga,operacao,dwt
MV Example,1234567,Santos,STS01,2025-01-15 08:00,2025-01-17 14:30,Soja,EMBARQUE,50000
...
```

Com isso, calculamos:
```python
tempo_espera_horas = (data_atracacao - prev_chegada).total_seconds() / 3600
# Resultado: 54.5 horas
```

#### Vantagens:
- ✅ Treino imediato de modelos reais
- ✅ Alta qualidade de dados
- ✅ Validação retroativa possível

#### Desvantagens:
- ❌ Pode não estar disponível
- ❌ Requer acesso a sistemas externos
- ❌ Pode ter custo (APIs comerciais)

---

### **Opção 2: Coletar Dados em Produção** ⭐ MAIS VIÁVEL

Usar o sistema Streamlit atual para **acumular dados de treino**:

#### Estratégia:

```
┌─────────────────────────────────────────────────────┐
│  1. Sistema faz previsão (T0)                       │
│     - Navio: MV Example                             │
│     - Chegada prevista: 2026-02-01 08:00            │
│     - Previsão: 48 horas de espera                  │
│     - Salvar: previsao_123.json                     │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  2. Acompanhamento manual (T0 + 7 dias)            │
│     - Verificar: navio atracou?                     │
│     - Registrar: data_atracacao = 2026-02-03 10:00  │
│     - Calcular: tempo real = 50 horas               │
│     - Salvar: resultado_123.json                    │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  3. Acumulação (2-3 meses)                          │
│     - 50 registros/mês → 150 registros totais       │
│     - Suficiente para treino inicial                │
│     - Retreino incremental                          │
└─────────────────────────────────────────────────────┘
```

#### Implementação:

**1. Adicionar no Streamlit:**

```python
# streamlit_app.py - após fazer previsão

def salvar_previsao_para_treino(navio_info, previsao, features):
    """Salva previsão para posterior validação."""

    registro = {
        "id": f"{navio_info['imo']}_{datetime.now().isoformat()}",
        "timestamp_previsao": datetime.now().isoformat(),
        "navio": navio_info['nome'],
        "imo": navio_info['imo'],
        "porto": navio_info['porto'],
        "prev_chegada": navio_info['prev_chegada'],
        "previsao_horas": previsao['tempo_espera_horas'],
        "features": features,
        "validado": False,
        "tempo_real_horas": None,
        "data_atracacao_real": None
    }

    # Salva em JSON
    Path("data/previsoes_pendentes").mkdir(exist_ok=True)
    with open(f"data/previsoes_pendentes/{registro['id']}.json", "w") as f:
        json.dump(registro, f, indent=2)
```

**2. Script de validação:**

```python
# validar_previsoes.py

def validar_previsoes_pendentes():
    """Interface para registrar atracações reais."""

    pendentes = list(Path("data/previsoes_pendentes").glob("*.json"))

    for arquivo in pendentes:
        with open(arquivo) as f:
            previsao = json.load(f)

        print(f"\nNavio: {previsao['navio']}")
        print(f"Prev. chegada: {previsao['prev_chegada']}")
        print(f"Previsão: {previsao['previsao_horas']:.1f}h")

        # Input manual
        atracou = input("Navio já atracou? (s/n): ")

        if atracou.lower() == 's':
            data_real = input("Data/hora atracação (YYYY-MM-DD HH:MM): ")
            tempo_real = calcular_tempo_real(
                previsao['prev_chegada'],
                data_real
            )

            # Atualiza registro
            previsao['validado'] = True
            previsao['data_atracacao_real'] = data_real
            previsao['tempo_real_horas'] = tempo_real

            # Move para validados
            Path("data/previsoes_validadas").mkdir(exist_ok=True)
            destino = Path("data/previsoes_validadas") / arquivo.name
            with open(destino, "w") as f:
                json.dump(previsao, f, indent=2)

            arquivo.unlink()  # Remove de pendentes
```

**3. Retreino automático:**

```python
# retreino_incremental.py

def retreinar_quando_suficiente():
    """Retreina modelos quando acumular dados suficientes."""

    validados = list(Path("data/previsoes_validadas").glob("*.json"))

    if len(validados) < 50:
        print(f"Aguardando mais dados: {len(validados)}/50")
        return

    # Carrega dados validados
    df_treino = carregar_previsoes_validadas()

    # Treina novos modelos
    treinar_modelos(df_treino)

    print(f"✅ Modelos retreinados com {len(df_treino)} registros!")
```

#### Vantagens:
- ✅ Totalmente viável (não depende de terceiros)
- ✅ Dados de alta qualidade (mesma pipeline de features)
- ✅ Retreino incremental contínuo
- ✅ Validação em produção

#### Desvantagens:
- ❌ Requer tempo (2-3 meses para dados suficientes)
- ❌ Trabalho manual de validação
- ❌ Modelos mock no interim

---

### **Opção 3: Integração com AIS** 🛰️

Usar dados de AIS para detectar atracações:

#### Estratégia:

```python
# Lógica:
1. Sistema prevê chegada: 2026-02-01 08:00
2. Após 7 dias, consulta AIS:
   - Verifica posição do navio (IMO)
   - Se velocidade < 1 knot E dentro do porto: ATRACADO
   - Pega timestamp da primeira posição atracada
3. Calcula tempo real de espera
```

#### APIs AIS disponíveis:

- **MarineTraffic API** (pago)
- **VesselFinder API** (pago)
- **AISHub** (gratuito, limitado)
- **Integrações locais** (se houver)

#### Vantagens:
- ✅ Automático (sem validação manual)
- ✅ Cobertura global
- ✅ Alta precisão de timestamps

#### Desvantagens:
- ❌ Custo (APIs comerciais)
- ❌ Complexidade de integração
- ❌ Pode ter atrasos/gaps de dados

---

### **Opção 4: Ajustar Modelos Mock** 🔧

Refinar os modelos mock atuais com **heurísticas baseadas em conhecimento do domínio**:

#### Estratégia:

```python
# Modelo mock atual (genérico):
tempo_vegetal = 48h ± 30%

# Modelo mock ajustado (heurística):
tempo_base = {
    "Santos": 36h,
    "Paranaguá": 48h,
    "Rio Grande": 60h,
}

# Ajustes por fila:
if navios_na_fila > 5:
    tempo_base *= 1.5

# Ajustes por safra:
if periodo_safra and carga in ["SOJA", "MILHO"]:
    tempo_base *= 1.3

# Ajustes por clima:
if vento_max > 50:  # Condições adversas
    tempo_base *= 1.2
```

#### Como ajustar:

1. **Coletar conhecimento especialista:**
   - Conversar com operadores portuários
   - Analisar relatórios públicos
   - Benchmarks de mercado

2. **Calibrar heurísticas:**
   - Testar com casos conhecidos
   - Ajustar multiplicadores
   - Validar contra expectativas

3. **Documentar regras:**
   - Deixar claro que são aproximações
   - Manter transparência com usuário

#### Vantagens:
- ✅ Implementação imediata
- ✅ Melhor que aleatório
- ✅ Não requer dados históricos

#### Desvantagens:
- ❌ Baixa precisão
- ❌ Não aprende com dados
- ❌ Limitado a conhecimento explícito

---

## 📊 Comparação de Opções

| Opção | Tempo | Custo | Precisão | Viabilidade | Recomendação |
|-------|-------|-------|----------|-------------|--------------|
| **1. Dados completos** | Imediato | Variável | ⭐⭐⭐⭐⭐ | ❓ Depende | ⭐⭐⭐⭐⭐ SE disponível |
| **2. Coleta em produção** | 2-3 meses | Baixo | ⭐⭐⭐⭐ | ✅ Alta | ⭐⭐⭐⭐⭐ MAIS VIÁVEL |
| **3. Integração AIS** | 1-2 semanas | Médio/Alto | ⭐⭐⭐⭐ | ⚠️ Média | ⭐⭐⭐⭐ SE orçamento |
| **4. Mock ajustado** | Imediato | Zero | ⭐⭐ | ✅ Alta | ⭐⭐⭐ Temporário |

---

## 🎯 Recomendação Final

### **Estratégia Híbrida (Melhor Abordagem):**

```
FASE 1 (Agora - 2 semanas):
├─ ✅ Manter modelos MOCK
├─ ✅ Ajustar heurísticas com conhecimento do domínio
├─ ✅ Implementar sistema de coleta de dados
└─ ✅ Buscar dados históricos completos (em paralelo)

FASE 2 (Semanas 3-12):
├─ 📊 Coletar previsões + validações manuais
├─ 📊 Acumular 50-150 registros validados
├─ 📊 Opcionalmente: integrar AIS para automação
└─ 📊 Monitorar qualidade dos dados coletados

FASE 3 (Mês 3+):
├─ 🤖 Treinar primeiros modelos reais (150+ registros)
├─ 🤖 Validar performance vs modelos mock
├─ 🤖 Deploy gradual (A/B test)
└─ 🤖 Retreino incremental mensal

FASE 4 (Mês 6+):
├─ 🚀 Modelos maduros (500+ registros)
├─ 🚀 Retreino automático
├─ 🚀 Monitoramento de drift
└─ 🚀 Otimização contínua
```

---

## 📝 Ações Imediatas Recomendadas

### 1. **Investigar fontes de dados históricos**

Verificar se existem:
- [ ] APIs de autoridade portuária com dados históricos
- [ ] Bancos de dados internos com registros de atracação
- [ ] Parceiros/clientes com planilhas de operação
- [ ] Datasets públicos de operação portuária

**Tempo estimado:** 1-2 dias
**Prioridade:** ⭐⭐⭐⭐⭐ ALTA

### 2. **Implementar sistema de coleta de dados**

Criar infraestrutura para capturar:
- [ ] Adicionar `salvar_previsao_para_treino()` no Streamlit
- [ ] Criar script `validar_previsoes.py`
- [ ] Configurar diretórios `data/previsoes_*`
- [ ] Testar fluxo completo

**Tempo estimado:** 1 dia
**Prioridade:** ⭐⭐⭐⭐⭐ ALTA

### 3. **Ajustar modelos mock**

Melhorar heurísticas atuais:
- [ ] Levantar tempos médios por porto (pesquisa/especialistas)
- [ ] Implementar ajustes por fila
- [ ] Implementar ajustes por safra
- [ ] Implementar ajustes por clima
- [ ] Documentar regras de negócio

**Tempo estimado:** 2-3 dias
**Prioridade:** ⭐⭐⭐⭐ MÉDIA-ALTA

### 4. **Avaliar integração AIS**

Investigar viabilidade:
- [ ] Pesquisar APIs AIS disponíveis
- [ ] Verificar custos e limites
- [ ] Testar API gratuita (AISHub)
- [ ] POC de detecção de atracação

**Tempo estimado:** 3-4 dias
**Prioridade:** ⭐⭐⭐ MÉDIA

---

## 📁 Arquivos Criados Nesta Análise

```
previsao_filas/
├── analise_dados_historicos.py          ✅ Script de análise
├── pipelines/
│   ├── preprocess_historical_data.py   ✅ Script de preprocessamento
│   ├── train_light_models_real.py      ✅ Script de treino (aguardando dados)
│   └── train_light_models_mock.py      ✅ Script de mock (funcional)
├── ANALISE_DADOS_TREINO.md             ✅ Este documento
├── INSTRUCOES_TREINO_MODELOS_REAIS.md  ✅ Instruções (quando houver dados)
└── models/
    └── *_light_*.pkl                    ✅ Modelos mock (funcionando)
```

---

## 🔄 Status do Sistema Atual

### O que está FUNCIONANDO:

```
✅ Sistema de fallback inteligente implementado
✅ Seleção automática de modelos (completo vs light)
✅ Modelos mock operacionais (VEGETAL, MINERAL, FERTILIZANTE)
✅ Badges de qualidade (🟢🟡🔴)
✅ Interface transparente para usuário
✅ Sistema de coleta de features robusto
✅ Testes automatizados (100% passando)
```

### O que está BLOQUEADO:

```
❌ Treino de modelos reais (falta target)
❌ Validação de performance real (falta dados históricos)
❌ Retreino automático (falta pipeline de dados)
```

### O que pode ser MELHORADO (sem dados):

```
⚠️ Heurísticas dos modelos mock
⚠️ Documentação de regras de negócio
⚠️ Sistema de coleta de dados em produção
⚠️ Monitoramento de previsões
```

---

## 💬 Conclusão

**O sistema de fallback inteligente está 100% implementado e funcional**, mas os modelos atuais são **mock/demonstração**.

Para treinar **modelos reais**, é essencial ter:
1. ✅ Dados de chegada prevista (temos)
2. ❌ Dados de atracação efetiva (**NÃO temos**)

**Recomendação imediata:**
1. Investigar fontes de dados históricos completos (1-2 dias)
2. Se não disponível: implementar coleta em produção (1 dia)
3. Enquanto isso: ajustar modelos mock com heurísticas (2-3 dias)

Em 2-3 meses, com coleta em produção, teremos dados suficientes para treinar modelos reais de alta qualidade.

---

**Próxima ação:** Aguardando decisão do usuário sobre qual estratégia seguir.

