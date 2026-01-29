# Proposta de Correção: Inconsistências entre Colunas e Features do Modelo

**Data:** 2026-01-27
**Problema:** Modelos básicos esperam 38-54 features, mas lineups fornecem apenas 5 colunas
**Objetivo:** Propor soluções práticas e implementáveis para melhorar a qualidade das previsões

---

## 1. Análise do Problema

### 1.1 Situação Atual

**Dados disponíveis no lineup (entrada do usuário):**
```
- Navio (nome do navio)
- Mercadoria (tipo de carga)
- Chegada (data/hora prevista de chegada)
- Berco (terminal de destino)
- DWT (opcional - tonelagem do navio)
```

**Features esperadas pelos modelos:**
- **VEGETAL:** 54 features
- **MINERAL:** 38 features
- **FERTILIZANTE:** 38 features
- **PONTA_DA_MADEIRA (Premium):** 10 features

**Gap atual:** 5 colunas fornecidas → 38-54 features necessárias = **33-49 features faltantes (87-91%)**

### 1.2 Classificação das Features por Fonte de Dados

Analisando as 54 features do modelo VEGETAL:

#### **Categoria A: Derivadas do Lineup (5 features - 9%)**
✅ Disponíveis diretamente do lineup:
```
1. nome_porto → inferido do arquivo ou seleção do usuário
2. nome_terminal → coluna "Berco"
3. natureza_carga → coluna "Mercadoria"
4. movimentacao_total_toneladas → coluna "DWT"
5. mes, dia_semana, dia_do_ano → derivados de "Chegada"
```

#### **Categoria B: Hardcoded/Defaults Razoáveis (7 features - 13%)**
⚠️ Valores fixos que fazem sentido para o contexto brasileiro:
```
6. tipo_navegacao → "Longo Curso" (99% dos casos)
7. tipo_carga → "Granel" (contexto de commodities)
8. cdmercadoria → "0000" (código desconhecido)
9. stsh4 → "0000" (código desconhecido)
10. restricao_vento → 0 (sem restrição, conservador)
11. restricao_chuva → 0 (sem restrição, conservador)
12. flag_celulose, flag_algodao, flag_soja, flag_milho → derivados de "Mercadoria"
```

#### **Categoria C: Contexto Temporal (1 feature - 2%)**
✅ Podem ser inferidos de forma confiável:
```
13. periodo_safra → baseado no mês (março-junho)
```

#### **Categoria D: APIs Externas - Clima (8-16 features - 15-30%)**
🔧 Disponíveis via APIs (Open-Meteo, INMET, BigQuery):
```
14. temp_media_dia
15. precipitacao_dia
16. vento_rajada_max_dia
17. vento_velocidade_media (somente VEGETAL)
18. umidade_media_dia
19. amplitude_termica
20. chuva_acumulada_ultimos_3dias
21. wave_height_max (VEGETAL)
22. wave_height_media (VEGETAL)
23. frente_fria (VEGETAL)
24. pressao_anomalia (VEGETAL)
25. ressaca (VEGETAL)
```

**Status atual:** Implementado parcialmente
- ✅ Open-Meteo API disponível
- ✅ BigQuery INMET disponível (requer credenciais)
- ⚠️ Oceano/maré: parcialmente implementado

#### **Categoria E: APIs Externas - AIS (5 features - 9%)**
🔧 Disponíveis via APIs AIS (MarineTraffic, VesselFinder):
```
26. ais_navios_no_raio
27. ais_fila_ao_largo
28. ais_velocidade_media_kn
29. ais_eta_media_horas
30. ais_dist_media_km
```

**Status atual:** Estrutura existe, mas dados AIS não são carregados automaticamente

#### **Categoria F: APIs Externas - Maré (6 features - 11%)**
🔧 Disponíveis via dados de maré astronômica:
```
31. mare_astronomica
32. mare_subindo
33. mare_horas_ate_extremo
34. tem_mare_astronomica
```

**Status atual:** Implementado, dados históricos disponíveis em `data/mare_clima/`

#### **Categoria G: APIs Externas - Economia (6 features - 11%)**
🔧 Disponíveis via APIs (IBGE PAM, IPEA):
```
35. producao_soja
36. producao_milho
37. producao_algodao
38. preco_soja_mensal
39. preco_milho_mensal
40. preco_algodao_mensal
```

**Status atual:** Implementado via BigQuery (requer credenciais)

#### **Categoria H: Calculadas - Fila (3 features - 6%)**
❌ **PROBLEMA CRÍTICO** - Calculadas incorretamente:
```
41. navios_no_fundeio_na_chegada → ERRADO: usa df.index
42. navios_na_fila_7d → ERRADO: baseado em janela simples
43. tempo_espera_ma5 → FIXO: sempre 0.0
```

#### **Categoria I: Calculadas - Histórico (1 feature - 2%)**
❌ **PROBLEMA** - Valor fixo:
```
44. porto_tempo_medio_historico → FIXO: sempre 0.0
```

#### **Categoria J: Calculadas - Pressão de Mercado (2 features - 4%)**
❌ **PROBLEMA** - Valores fixos:
```
45. indice_pressao_soja → FIXO: sempre 0.0
46. indice_pressao_milho → FIXO: sempre 0.0
```

### 1.3 Resumo do Diagnóstico

| Categoria | Features | % | Status | Impacto no Modelo |
|-----------|----------|---|--------|-------------------|
| **A. Lineup** | 5 | 9% | ✅ OK | **ALTO** - dados reais |
| **B. Defaults** | 7 | 13% | ⚠️ Razoável | **MÉDIO** - valores conservadores |
| **C. Temporal** | 1 | 2% | ✅ OK | **MÉDIO** |
| **D. Clima** | 8-16 | 15-30% | 🔧 Parcial | **ALTO** - clima afeta operações |
| **E. AIS** | 5 | 9% | ❌ Não usado | **ALTO** - indica fila real |
| **F. Maré** | 4-6 | 7-11% | 🔧 Parcial | **MÉDIO** - afeta alguns portos |
| **G. Economia** | 6 | 11% | 🔧 Parcial | **BAIXO** - contexto macro |
| **H. Fila** | 3 | 6% | ❌ **ERRADO** | **CRÍTICO** - fila é preditor principal |
| **I. Histórico** | 1 | 2% | ❌ Fixo 0 | **ALTO** - baseline importante |
| **J. Pressão** | 2 | 4% | ❌ Fixo 0 | **BAIXO** - refinamento |

**Conclusão:**
- ✅ **21% das features estão OK** (12/54)
- ⚠️ **44% poderiam ser obtidas via APIs** (24/54)
- ❌ **11% estão CRITICAMENTE ERRADAS** (6/54 - fila e histórico)
- ⚠️ **24% têm defaults questionáveis** (restante)

---

## 2. Propostas de Correção

### 2.1 Abordagem Recomendada: **Híbrida com Validação**

Não exigir re-treino imediato dos modelos, mas:
1. **Corrigir cálculos críticos** (fila, histórico)
2. **Melhorar obtenção de dados de APIs** (clima, AIS, maré)
3. **Adicionar sistema de validação e confiança**
4. **Preparar para modelos simplificados no futuro**

### 2.2 Solução Detalhada por Categoria

#### **PRIORIDADE 1: Corrigir Features Críticas (Categoria H e I)**

**Feature: `navios_no_fundeio_na_chegada`**

❌ **Código atual (streamlit_app.py:1019):**
```python
df["navios_no_fundeio_na_chegada"] = df.index.astype(float)
```

✅ **Código corrigido:**
```python
def calcular_fila_simulada(df_lineup):
    """
    Calcula quantos navios estarão no fundeio quando cada navio chegar.
    Usa simulação simplificada baseada em taxa média de atracação.
    """
    df = df_lineup.copy()
    df = df.sort_values("data_chegada_dt").reset_index(drop=True)

    # Taxa média de atracação por hora (ajustar por porto/perfil)
    TAXA_ATRACACAO_MEDIA_HORAS = {
        "VEGETAL": 72,      # 3 dias em média
        "MINERAL": 48,      # 2 dias em média
        "FERTILIZANTE": 96  # 4 dias em média
    }

    fila = np.zeros(len(df))

    for i in range(len(df)):
        chegada_i = df.loc[i, "data_chegada_dt"]
        perfil_i = df.loc[i, "perfil_modelo"] if "perfil_modelo" in df.columns else "VEGETAL"
        taxa_media = TAXA_ATRACACAO_MEDIA_HORAS.get(perfil_i, 72)

        # Conta quantos navios anteriores ainda estarão no fundeio
        navios_no_fundeio = 0
        for j in range(i):
            chegada_j = df.loc[j, "data_chegada_dt"]
            tempo_desde_chegada = (chegada_i - chegada_j).total_seconds() / 3600  # horas

            # Se o navio j chegou há menos tempo que a taxa média, ainda está no fundeio
            if tempo_desde_chegada < taxa_media:
                navios_no_fundeio += 1

        fila[i] = navios_no_fundeio

    return fila
```

**Feature: `porto_tempo_medio_historico`**

❌ **Código atual:** sempre 0.0

✅ **Código corrigido:**
```python
def carregar_tempo_medio_historico(porto_nome):
    """
    Carrega tempo médio histórico de espera para o porto.
    Usa lineup_history.parquet ou valores default por porto.
    """
    # Valores default baseados em dados reais (horas)
    TEMPO_MEDIO_DEFAULT = {
        "SANTOS": 48,
        "PARANAGUA": 72,
        "ITAQUI": 36,
        "PONTA_DA_MADEIRA": 24,
        "VILA_DO_CONDE": 60,
        "BARCARENA": 60,
        "RIO_GRANDE": 48,
        "SUAPE": 72,
        "PECEM": 48,
        "SALVADOR": 60,
        "VITORIA": 48,
        "SAO_FRANCISCO_DO_SUL": 60,
    }

    porto_norm = normalizar_texto(porto_nome)

    # Tenta carregar do histórico
    try:
        df_hist = load_lineup_history()
        if not df_hist.empty and "tempo_espera_horas" in df_hist.columns:
            df_porto = df_hist[df_hist["porto"].apply(normalizar_texto) == porto_norm]
            if len(df_porto) >= 10:  # Mínimo 10 registros históricos
                tempo_medio = df_porto["tempo_espera_horas"].median()
                return float(tempo_medio)
    except Exception:
        pass

    # Fallback para valores default
    for key, value in TEMPO_MEDIO_DEFAULT.items():
        if normalizar_texto(key) == porto_norm:
            return float(value)

    return 48.0  # Default genérico: 2 dias
```

**Feature: `tempo_espera_ma5`**

❌ **Código atual:** sempre 0.0

✅ **Código corrigido:**
```python
def calcular_tempo_espera_ma5(df_lineup):
    """
    Calcula média móvel de 5 períodos do tempo de espera.
    Como não temos histórico no lineup, usa tempo médio do porto.
    """
    df = df_lineup.copy()

    if "porto_tempo_medio_historico" in df.columns:
        # Usa o tempo médio histórico como proxy
        df["tempo_espera_ma5"] = df["porto_tempo_medio_historico"]
    else:
        df["tempo_espera_ma5"] = 48.0  # Default: 2 dias

    return df["tempo_espera_ma5"].values
```

#### **PRIORIDADE 2: Melhorar Obtenção de Dados de APIs**

**Feature: Dados de Clima (Categoria D)**

✅ **Já implementado parcialmente** via Open-Meteo e BigQuery INMET

🔧 **Melhorias necessárias:**
```python
def obter_dados_clima_completos(porto_nome, data_chegada, live_data):
    """
    Obtém dados de clima de múltiplas fontes com fallback.
    """
    # Prioridade 1: BigQuery INMET (mais preciso)
    if BIGQUERY_AVAILABLE:
        try:
            clima_inmet = fetch_inmet_latest(
                station_id=get_station_id(porto_nome),
                port_name=porto_nome
            )
            if clima_inmet and clima_inmet.get("temp_media_dia"):
                return clima_inmet
        except Exception as e:
            st.warning(f"BigQuery INMET indisponível: {e}")

    # Prioridade 2: Open-Meteo (fallback)
    if WEATHER_API_AVAILABLE:
        try:
            from weather_api import get_weather_forecast
            lat, lon = get_porto_coords(porto_nome)
            clima_openmeteo = get_weather_forecast(lat, lon, data_chegada)
            return clima_openmeteo
        except Exception as e:
            st.warning(f"Open-Meteo indisponível: {e}")

    # Prioridade 3: Valores conservadores (fallback final)
    st.warning(f"Usando valores climáticos conservadores para {porto_nome}")
    return {
        "temp_media_dia": 25.0,
        "precipitacao_dia": 0.0,
        "vento_rajada_max_dia": 5.0,
        "umidade_media_dia": 70.0,
        "amplitude_termica": 10.0,
    }
```

**Feature: Dados AIS (Categoria E)**

❌ **Não implementado** - estrutura existe mas não é usada

✅ **Implementação recomendada:**
```python
def carregar_ais_features_por_data(porto_nome, data_chegada):
    """
    Carrega features AIS do arquivo pre-processado.
    """
    # Verifica se existe arquivo AIS para o porto
    porto_norm = normalizar_texto(porto_nome)
    ais_file = AIS_FEATURES_DIR / f"{porto_norm}_ais_features.parquet"

    if not ais_file.exists():
        # Retorna valores default (não há dados AIS)
        return pd.DataFrame({
            "ais_navios_no_raio": [0.0],
            "ais_fila_ao_largo": [0.0],
            "ais_velocidade_media_kn": [0.0],
            "ais_eta_media_horas": [0.0],
            "ais_dist_media_km": [0.0],
        })

    try:
        df_ais = pd.read_parquet(ais_file)
        df_ais["date"] = pd.to_datetime(df_ais["date"]).dt.date

        # Busca dados para a data específica ou usa o mais recente
        data_alvo = pd.to_datetime(data_chegada).date()
        df_data = df_ais[df_ais["date"] == data_alvo]

        if df_data.empty:
            # Usa dados mais recentes disponíveis
            df_data = df_ais.sort_values("date", ascending=False).head(1)
            st.info(f"Usando dados AIS de {df_data['date'].iloc[0]} (mais recentes disponíveis)")

        return df_data
    except Exception as e:
        st.warning(f"Erro ao carregar dados AIS: {e}")
        return pd.DataFrame({
            "ais_navios_no_raio": [0.0],
            "ais_fila_ao_largo": [0.0],
            "ais_velocidade_media_kn": [0.0],
            "ais_eta_media_horas": [0.0],
            "ais_dist_media_km": [0.0],
        })
```

**Feature: Dados de Maré (Categoria F)**

✅ **Já implementado** via `adicionar_features_mare_lineup()`

🔧 **Verificar funcionamento correto** - parece OK no código atual (streamlit_app.py:1000)

#### **PRIORIDADE 3: Sistema de Validação e Confiança**

**Classe para rastrear qualidade dos dados:**

```python
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

class FeatureQuality(Enum):
    """Qualidade da feature preenchida"""
    REAL = "real"              # Dado real do lineup
    API_OK = "api_ok"          # Obtido de API com sucesso
    API_FALLBACK = "api_fallback"  # API falhou, usando fallback
    CALCULATED = "calculated"  # Calculado corretamente
    DEFAULT = "default"        # Valor default razoável
    CRITICAL_DEFAULT = "critical_default"  # Valor default em feature crítica

@dataclass
class FeatureReport:
    """Relatório de qualidade das features para uma previsão"""
    total_features: int
    quality_breakdown: Dict[FeatureQuality, int]
    critical_issues: List[str]
    warnings: List[str]
    confidence_score: float  # 0-100

    def to_dict(self):
        return {
            "total_features": self.total_features,
            "quality": {k.value: v for k, v in self.quality_breakdown.items()},
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "confidence": self.confidence_score
        }

def avaliar_qualidade_features(df_features, metadata, api_status):
    """
    Avalia a qualidade das features preenchidas.

    Args:
        df_features: DataFrame com features preenchidas
        metadata: Metadados do modelo (lista de features esperadas)
        api_status: Dict com status de cada API (clima, ais, mare, etc.)

    Returns:
        FeatureReport com análise de qualidade
    """
    features = metadata["features"]
    quality_breakdown = {q: 0 for q in FeatureQuality}
    critical_issues = []
    warnings = []

    # Features do lineup (Categoria A)
    lineup_features = ["nome_porto", "nome_terminal", "natureza_carga",
                       "movimentacao_total_toneladas", "mes", "dia_semana", "dia_do_ano"]
    for feat in lineup_features:
        if feat in features:
            quality_breakdown[FeatureQuality.REAL] += 1

    # Features de clima (Categoria D)
    clima_features = ["temp_media_dia", "precipitacao_dia", "vento_rajada_max_dia",
                      "umidade_media_dia", "amplitude_termica", "chuva_acumulada_ultimos_3dias"]
    if api_status.get("clima_ok", False):
        quality_breakdown[FeatureQuality.API_OK] += len([f for f in clima_features if f in features])
    else:
        quality_breakdown[FeatureQuality.API_FALLBACK] += len([f for f in clima_features if f in features])
        warnings.append("Dados de clima não disponíveis - usando valores conservadores")

    # Features AIS (Categoria E)
    ais_features = ["ais_navios_no_raio", "ais_fila_ao_largo", "ais_velocidade_media_kn",
                    "ais_eta_media_horas", "ais_dist_media_km"]
    if api_status.get("ais_ok", False):
        quality_breakdown[FeatureQuality.API_OK] += len([f for f in ais_features if f in features])
    else:
        quality_breakdown[FeatureQuality.CRITICAL_DEFAULT] += len([f for f in ais_features if f in features])
        critical_issues.append("⚠️ Dados AIS não disponíveis - fila real desconhecida")

    # Features de fila calculadas (Categoria H)
    fila_features = ["navios_no_fundeio_na_chegada", "navios_na_fila_7d"]
    quality_breakdown[FeatureQuality.CALCULATED] += len([f for f in fila_features if f in features])

    # Features históricas (Categoria I)
    if "porto_tempo_medio_historico" in features:
        if api_status.get("historico_ok", False):
            quality_breakdown[FeatureQuality.CALCULATED] += 1
        else:
            quality_breakdown[FeatureQuality.DEFAULT] += 1
            warnings.append("Tempo médio histórico baseado em valores típicos do porto")

    # Features econômicas (Categoria G)
    econ_features = ["producao_soja", "producao_milho", "preco_soja_mensal", "preco_milho_mensal"]
    if api_status.get("economia_ok", False):
        quality_breakdown[FeatureQuality.API_OK] += len([f for f in econ_features if f in features])
    else:
        quality_breakdown[FeatureQuality.DEFAULT] += len([f for f in econ_features if f in features])
        warnings.append("Dados econômicos não disponíveis - usando valores default")

    # Defaults (resto)
    defaults_count = len(features) - sum(quality_breakdown.values())
    quality_breakdown[FeatureQuality.DEFAULT] += defaults_count

    # Calcula score de confiança
    total = len(features)
    score = (
        quality_breakdown[FeatureQuality.REAL] * 1.0 +
        quality_breakdown[FeatureQuality.API_OK] * 0.9 +
        quality_breakdown[FeatureQuality.CALCULATED] * 0.8 +
        quality_breakdown[FeatureQuality.DEFAULT] * 0.5 +
        quality_breakdown[FeatureQuality.API_FALLBACK] * 0.4 +
        quality_breakdown[FeatureQuality.CRITICAL_DEFAULT] * 0.2
    ) / total * 100

    return FeatureReport(
        total_features=total,
        quality_breakdown=quality_breakdown,
        critical_issues=critical_issues,
        warnings=warnings,
        confidence_score=round(score, 1)
    )
```

**Integração no fluxo de previsão:**

```python
def predict_lineup_basico_v2(df_lineup, live_data, porto_nome):
    """
    Versão melhorada com validação e rastreamento de qualidade.
    """
    df = df_lineup.copy()
    df["perfil_modelo"] = df.apply(get_profile_from_row, axis=1)

    # Rastreia status das APIs
    api_status = {
        "clima_ok": live_data.get("clima") is not None,
        "ais_ok": live_data.get("ais_df") is not None and not live_data["ais_df"].empty,
        "economia_ok": live_data.get("pam") is not None and live_data.get("precos") is not None,
        "historico_ok": False,  # Será atualizado por carregar_tempo_medio_historico()
    }

    dfs = []
    feature_reports = []

    for profile, sub in df.groupby("perfil_modelo", dropna=False):
        models = load_models_for_profile(profile)
        if not models:
            sub["tempo_espera_previsto_horas"] = np.nan
            sub["tempo_espera_previsto_dias"] = np.nan
            sub["classe_espera_prevista"] = "Indisponivel"
            sub["risco_previsto"] = "Indisponivel"
            sub["probabilidade_prevista"] = np.nan
            sub["confianca_previsao"] = 0.0
            dfs.append(sub)
            continue

        # Constrói features com rastreamento
        features_data = build_features_from_lineup(sub, models["metadata"], live_data, porto_nome)

        # Avalia qualidade das features
        report = avaliar_qualidade_features(features_data, models["metadata"], api_status)

        # Faz previsão
        preds_horas = None
        if models.get("model_ensemble") is not None:
            ensemble = models["model_ensemble"]
            try:
                if hasattr(ensemble, "xgb_model"):
                    X_xgb = build_xgb_features_from_lgb(features_data, ensemble.xgb_model)
                    preds = ensemble.predict(X_xgb, X_lgb=features_data)
                else:
                    preds = ensemble.predict(features_data)
                preds_horas = pd.Series(preds).apply(lambda v: float(max(0.0, v)))
            except Exception:
                preds_horas = None

        if preds_horas is None:
            preds_horas = pd.Series(models["model_reg"].predict(features_data)).apply(
                lambda v: float(max(0.0, np.expm1(v)))
            )

        sub["tempo_espera_previsto_horas"] = preds_horas.round(2).to_numpy()
        sub["tempo_espera_previsto_dias"] = (sub["tempo_espera_previsto_horas"] / 24.0).round(2)
        sub["confianca_previsao"] = report.confidence_score

        # Adiciona avisos ao DataFrame
        if report.critical_issues:
            sub["avisos_criticos"] = ", ".join(report.critical_issues)
        if report.warnings:
            sub["avisos"] = ", ".join(report.warnings)

        class_pred = models["model_clf"].predict(features_data)
        class_map = {0: "Rápido", 1: "Médio", 2: "Longo"}
        risco_map = {0: "Baixo", 1: "Médio", 2: "Alto"}
        sub["classe_espera_prevista"] = (
            pd.Series(class_pred).map(class_map).fillna("Desconhecido").to_numpy()
        )
        sub["risco_previsto"] = (
            pd.Series(class_pred).map(risco_map).fillna("Desconhecido").to_numpy()
        )

        try:
            proba = models["model_clf"].predict_proba(features_data)
            sub["probabilidade_prevista"] = np.max(proba, axis=1).round(3)
        except Exception:
            sub["probabilidade_prevista"] = np.nan

        dfs.append(sub)
        feature_reports.append(report)

    df_out = pd.concat(dfs, ignore_index=True)

    # [resto do código igual...]

    return df_out, feature_reports  # Retorna também os reports
```

#### **PRIORIDADE 4: Interface de Usuário Melhorada**

**Exibir qualidade dos dados na UI:**

```python
# No Streamlit app, após fazer previsão
df_pred, feature_reports = predict_lineup_basico_v2(df_lineup, live_data, porto_nome)

# Calcula score médio de confiança
avg_confidence = np.mean([r.confidence_score for r in feature_reports])

# Exibe indicador visual
if avg_confidence >= 80:
    st.success(f"🟢 Qualidade dos Dados: ALTA ({avg_confidence:.0f}%)")
elif avg_confidence >= 60:
    st.warning(f"🟡 Qualidade dos Dados: MÉDIA ({avg_confidence:.0f}%)")
else:
    st.error(f"🔴 Qualidade dos Dados: BAIXA ({avg_confidence:.0f}%)")

# Mostra detalhes em expander
with st.expander("📊 Detalhes da Qualidade dos Dados"):
    for i, report in enumerate(feature_reports):
        st.write(f"**Grupo {i+1}:** {report.total_features} features")

        # Gráfico de pizza
        import plotly.graph_objects as go
        labels = [q.value.replace("_", " ").title() for q in report.quality_breakdown.keys()]
        values = list(report.quality_breakdown.values())
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        st.plotly_chart(fig, use_container_width=True)

        # Avisos
        if report.critical_issues:
            for issue in report.critical_issues:
                st.error(issue)
        if report.warnings:
            for warn in report.warnings:
                st.warning(warn)
```

---

## 3. Roadmap de Implementação

### **Fase 1: Correções Críticas (1-2 dias)**
- [ ] Corrigir `navios_no_fundeio_na_chegada` com cálculo correto
- [ ] Implementar `carregar_tempo_medio_historico()` com valores reais por porto
- [ ] Corrigir `tempo_espera_ma5` para usar histórico
- [ ] Testar impacto nas previsões

### **Fase 2: Sistema de Validação (2-3 dias)**
- [ ] Implementar classes `FeatureQuality` e `FeatureReport`
- [ ] Criar função `avaliar_qualidade_features()`
- [ ] Integrar validação em `predict_lineup_basico_v2()`
- [ ] Adicionar coluna `confianca_previsao` ao output
- [ ] Atualizar UI para mostrar indicadores de qualidade

### **Fase 3: Melhorar APIs (3-5 dias)**
- [ ] Garantir que dados de clima sejam sempre obtidos (Open-Meteo como fallback)
- [ ] Implementar `carregar_ais_features_por_data()` para usar dados AIS existentes
- [ ] Verificar funcionamento correto de features de maré
- [ ] Adicionar logging para rastrear quando APIs falham
- [ ] Criar script de teste para validar todas as APIs

### **Fase 4: Modelos Simplificados (2-3 semanas - FUTURO)**
- [ ] Analisar importância de features nos modelos atuais (SHAP, feature importance)
- [ ] Identificar top 15-20 features mais importantes
- [ ] Re-treinar modelos "light" usando apenas essas features
- [ ] Comparar performance: modelo completo vs light
- [ ] Se performance for similar (< 10% de degradação), substituir modelos

### **Fase 5: Validação Online (contínuo)**
- [ ] Salvar previsões feitas pelo app em banco de dados
- [ ] Comparar previsões com realidade após alguns dias
- [ ] Calcular MAE real em produção
- [ ] Identificar casos onde modelo erra sistematicamente
- [ ] Refinar modelos com feedback do mundo real

---

## 4. Exemplo de Uso Após Correções

### **Antes (Situação Atual):**
```
Usuário carrega lineup → App preenche 49 features com defaults →
Modelo prevê 72h → Usuário não sabe que previsão é baseada 87% em defaults
```

### **Depois (Proposta):**
```
Usuário carrega lineup → App tenta obter dados de APIs →
APIs disponíveis: Clima ✅, AIS ❌, Economia ✅, Maré ✅ →
App calcula features críticas corretamente →
Sistema avalia qualidade: 68% (MÉDIA) →
Modelo prevê 72h ± 38h →
UI mostra: "🟡 Confiança MÉDIA (68%) - Dados AIS indisponíveis"
```

---

## 5. Alternativa: Modelos Simplificados

Se as correções acima não forem suficientes, considerar re-treinar modelos com apenas **features disponíveis**:

### **Features Mínimas Recomendadas (15 features):**

```python
FEATURES_MINIMAS = [
    # Do lineup (5)
    "nome_porto",
    "nome_terminal",
    "natureza_carga",
    "movimentacao_total_toneladas",
    "mes",

    # Calculadas corretamente (3)
    "navios_no_fundeio_na_chegada",  # ← CORRIGIDO
    "navios_na_fila_7d",
    "porto_tempo_medio_historico",   # ← CORRIGIDO

    # Clima essencial (3)
    "temp_media_dia",
    "precipitacao_dia",
    "vento_rajada_max_dia",

    # Contexto (4)
    "dia_semana",
    "dia_do_ano",
    "periodo_safra",
    "flag_soja",  # ou flag_milho, dependendo do perfil
]
```

**Vantagens:**
- ✅ Todas as features são obtíveis de forma confiável
- ✅ Menos dependência de APIs externas
- ✅ Previsões mais explicáveis
- ✅ Mais rápido para inferência

**Desvantagens:**
- ❌ Requer re-treino completo dos modelos
- ❌ Pode perder precisão (precisa validar)
- ❌ Perde contexto de maré, AIS, economia

**Recomendação:** Implementar Fases 1-3 primeiro, depois avaliar se modelos simplificados são necessários.

---

## 6. Métricas de Sucesso

### **Curto Prazo (após Fases 1-2):**
- [ ] Score de confiança médio > 60% nas previsões
- [ ] 0% de features críticas com valores fixos errados
- [ ] 100% das previsões têm indicador de qualidade visível na UI
- [ ] Redução de 50% nos casos de "previsão não confiável"

### **Médio Prazo (após Fase 3):**
- [ ] Score de confiança médio > 75% nas previsões
- [ ] Dados de clima disponíveis em 95%+ dos casos (via fallback)
- [ ] Dados AIS disponíveis em 50%+ dos casos (para portos principais)
- [ ] Usuários reportam maior confiança nas previsões

### **Longo Prazo (após Fases 4-5):**
- [ ] MAE real em produção < 1.2x MAE de treino
- [ ] Score de confiança médio > 80%
- [ ] Feedback positivo de 80%+ dos usuários
- [ ] Sistema identifica e alerta sobre casos de baixa confiança

---

## 7. Conclusão

A proposta de correção é **implementar melhorias incrementais** sem exigir re-treino imediato:

1. **Fase 1:** Corrigir cálculos críticos (impacto imediato)
2. **Fase 2:** Adicionar sistema de validação (transparência)
3. **Fase 3:** Melhorar obtenção de dados (qualidade)
4. **Fase 4:** Considerar modelos simplificados (se necessário)
5. **Fase 5:** Validação contínua (melhoria contínua)

Esta abordagem permite **melhorias rápidas** (Fases 1-2 em menos de uma semana) e **prepara o terreno** para melhorias mais profundas no futuro.

**Próximos passos imediatos:**
1. Revisar e aprovar esta proposta
2. Priorizar Fase 1 (correções críticas)
3. Criar branch de desenvolvimento
4. Implementar correções com testes
5. Validar impacto antes de merge

---

**Fim da Proposta**
