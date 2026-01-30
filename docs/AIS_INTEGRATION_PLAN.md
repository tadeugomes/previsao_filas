# 🚢 Plano de Implementação: Integração Datalastic AIS Real-Time

## 📋 Sumário Executivo

**Objetivo:** Integrar dados AIS em tempo real da Datalastic para melhorar a precisão das previsões de fila portuária

**Benefício Esperado:** Redução de 50-70% no erro de previsão (MAE)

**Investimento:** €199-399/mês (planos Datalastic)

**ROI:** Break-even com 1-2 navios otimizados/mês

**Status Atual:** ✅ Datalastic já utilizada para treino de modelos (308 eventos AIS coletados)

---

## 🎯 Fases de Implementação

### **Fase 1: Integração com Datalastic Starter** ⏱️ 1-2 semanas
- Custo: **€199/mês** (20.000 créditos)
- Complexidade: **Baixa** (código base já existe)
- Impacto esperado: **+50-60% precisão**
- Base de código: `pipelines/datalastic_integration.py` (já implementado)

### **Fase 2: Upgrade para Datalastic Experimenter** ⏱️ 1 semana
- Custo: **€399/mês** (80.000 créditos)
- Complexidade: **Mínima** (apenas upgrade de plano)
- Impacto esperado: **+60-70% precisão** (maior volume de dados)

### **Fase 3: Otimização e Cache** ⏱️ 2-3 semanas
- Custo: **Mesmo €199-399/mês**
- Complexidade: **Média**
- Benefício: Redução de 50-70% no consumo de créditos via caching inteligente

---

## 🏗️ Arquitetura da Solução

```
┌─────────────────────────────────────────────────────┐
│           Camada de Aplicação                       │
│  ┌─────────────────────────────────────────────┐   │
│  │     predictor_enriched.py                   │   │
│  │  (consome dados AIS via DatalasticProvider) │   │
│  └────────────────┬────────────────────────────┘   │
└───────────────────┼─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│          Camada de Abstração AIS                    │
│  ┌─────────────────────────────────────────────┐   │
│  │        ais_provider.py                      │   │
│  │   (Interface abstrata + Factory Pattern)    │   │
│  └─────────────────┬───────────────────────────┘   │
└────────────────────┼───────────────────────────────┘
                     │
            ┌────────▼─────────┐
            │ DatalasticProvider│
            │   (€199-399/mês) │
            └────────┬─────────┘
                     │
   ┌─────────────────┼─────────────────┐
   │                 │                 │
┌──▼──────────┐ ┌───▼──────────┐ ┌───▼────────────┐
│ vessel_info │ │vessel_history│ │vessel_inradius │
│   (1 cred)  │ │ (N dias cred)│ │ (1 cred/navio) │
└─────────────┘ └──────────────┘ └────────────────┘
         https://api.datalastic.com/api/v0
```

**Componentes Existentes:**
- ✅ `pipelines/datalastic_integration.py` - Cliente Datalastic completo
- ✅ `DatalasticClient` - Classe com métodos para buscar dados AIS
- ✅ Definição de portos com coordenadas (Santos, Paranaguá, Rio Grande, Vitória, Itaqui)
- ✅ Funções de detecção de atracação e cálculo de tempo de espera

---

## 📝 Fase 1: Integração com Datalastic

### **1.1 Adicionar DatalasticProvider ao ais_provider.py**

O projeto já possui `pipelines/datalastic_integration.py` com a classe `DatalasticClient`. Vamos criar um wrapper que implementa a interface `AISProvider`:

**Arquivo:** `ais_provider.py` (adicionar DatalasticProvider)

```python
"""
Adicionar ao ais_provider.py existente
"""

# Importar cliente existente
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / 'pipelines'))

from datalastic_integration import DatalasticClient as DatalasticClientBase, PORTOS


class DatalasticProvider(AISProvider):
    """
    Provider usando Datalastic API (já utilizado no projeto).

    Vantagens:
    - ✅ Busca direta por IMO
    - ✅ Dados históricos completos
    - ✅ Cobertura global de AIS
    - ✅ Já validado no projeto (308 eventos coletados)

    Custo:
    - Starter: €199/mês (20.000 créditos)
    - Experimenter: €399/mês (80.000 créditos)

    Consumo de créditos:
    - get_vessel_position(): 1 crédito
    - get_port_traffic(): 1 crédito por navio no raio
    - get_vessels_in_radius(): 1 crédito por navio

    Website: https://datalastic.com
    Docs: https://api.datalastic.com/docs
    """

    def __init__(self, api_key: str):
        """
        Inicializa provider Datalastic.

        Args:
            api_key: Chave API Datalastic (obter em datalastic.com)
        """
        if not api_key:
            raise ValueError(
                "API key Datalastic necessária. "
                "Configure: export DATALASTIC_API_KEY='sua_key'"
            )

        self.client = DatalasticClientBase(api_key)
        self.base_url = "https://api.datalastic.com/api/v0"

    def get_vessel_position(self, imo: str) -> Optional[VesselPosition]:
        """
        Obtém posição atual de um navio por código IMO.

        Custo: 1 crédito
        """
        try:
            # Usar endpoint vessel_info para posição atual
            data = self.client.get_real_time_position(imo)

            if not data:
                return None

            # Parsear resposta Datalastic
            return VesselPosition(
                imo=imo,
                mmsi=str(data.get('mmsi', '')),
                lat=float(data.get('latitude', 0)),
                lon=float(data.get('longitude', 0)),
                speed_knots=float(data.get('speed', 0)),
                course=float(data.get('course', 0)),
                heading=float(data.get('heading', 0)),
                timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
                status=data.get('navigational_status', 'unknown'),
                destination=data.get('destination'),
                eta=datetime.fromisoformat(data['eta']) if data.get('eta') else None,
                draught=float(data.get('draught', 0)) if data.get('draught') else None
            )

        except Exception as e:
            print(f"Erro ao buscar posição Datalastic para IMO {imo}: {e}")
            return None

    def get_port_traffic(self, lat: float, lon: float, radius_km: float) -> PortTraffic:
        """
        Obtém estatísticas de tráfego em uma área portuária.

        Custo: 1 crédito por navio encontrado no raio
        """
        vessels = self.get_vessels_in_radius(lat, lon, radius_km)

        if not vessels:
            # Fallback: retornar valores padrão
            return PortTraffic(
                vessels_in_radius=0,
                vessels_anchored=0,
                vessels_moored=0,
                vessels_underway=0,
                avg_distance_km=0.0,
                avg_speed_knots=0.0,
                timestamp=datetime.now()
            )

        # Contar por status
        anchored = sum(1 for v in vessels if 'anchor' in v.status.lower())
        moored = sum(1 for v in vessels if 'moored' in v.status.lower())
        underway = sum(1 for v in vessels if 'underway' in v.status.lower())

        # Calcular velocidade média (apenas navios em movimento)
        speeds = [v.speed_knots for v in vessels if v.speed_knots > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0

        # Calcular distância média do centro
        distances = [
            self.haversine_distance(lat, lon, v.lat, v.lon)
            for v in vessels
        ]
        avg_distance = sum(distances) / len(distances) if distances else 0.0

        return PortTraffic(
            vessels_in_radius=len(vessels),
            vessels_anchored=anchored,
            vessels_moored=moored,
            vessels_underway=underway,
            avg_distance_km=avg_distance,
            avg_speed_knots=avg_speed,
            timestamp=datetime.now()
        )

    def get_vessels_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        status_filter: Optional[str] = None
    ) -> List[VesselPosition]:
        """
        Lista todos os navios em um raio específico.

        Custo: 1 crédito por navio retornado

        Args:
            lat: Latitude do centro
            lon: Longitude do centro
            radius_km: Raio de busca em quilômetros
            status_filter: Filtro de status ('anchor', 'underway', etc)

        Returns:
            Lista de VesselPosition
        """
        try:
            # Usar endpoint vessel_inradius
            # Converter raio de km para milhas náuticas (1 km = 0.539957 NM)
            radius_nm = radius_km * 0.539957

            url = f"{self.base_url}/vessel_inradius"
            params = {
                'api-key': self.client.api_key,
                'lat': lat,
                'lon': lon,
                'radius': radius_nm
            }

            response = self.client.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                return []

            vessels = []

            for vessel_data in data:
                try:
                    # Parsear cada navio
                    vessel = VesselPosition(
                        imo=str(vessel_data.get('imo', '')),
                        mmsi=str(vessel_data.get('mmsi', '')),
                        lat=float(vessel_data.get('latitude', 0)),
                        lon=float(vessel_data.get('longitude', 0)),
                        speed_knots=float(vessel_data.get('speed', 0)),
                        course=float(vessel_data.get('course', 0)),
                        heading=float(vessel_data.get('heading', 0)),
                        timestamp=datetime.fromisoformat(vessel_data.get('timestamp', datetime.now().isoformat())),
                        status=vessel_data.get('navigational_status', 'unknown'),
                        destination=vessel_data.get('destination'),
                        eta=datetime.fromisoformat(vessel_data['eta']) if vessel_data.get('eta') else None,
                        draught=float(vessel_data.get('draught', 0)) if vessel_data.get('draught') else None
                    )

                    # Filtrar por status se especificado
                    if status_filter and status_filter.lower() not in vessel.status.lower():
                        continue

                    vessels.append(vessel)

                except (ValueError, KeyError) as e:
                    # Ignorar navios com dados inválidos
                    continue

            # Atualizar contador de créditos
            self.client.credits_used += len(vessels)

            return vessels

        except Exception as e:
            print(f"Erro ao buscar navios no raio via Datalastic: {e}")
            return []
```

**Atualizar AISProviderFactory:**

```python
class AISProviderFactory:
    """Factory para criar providers AIS."""

    @staticmethod
    def create(provider_type: str, **kwargs) -> AISProvider:
        """
        Cria provider AIS baseado no tipo.

        Args:
            provider_type: 'datalastic', 'mock'
            **kwargs: Parâmetros específicos (api_key, etc)

        Returns:
            Instância do provider

        Exemplo:
            # Provider Datalastic (produção)
            provider = AISProviderFactory.create(
                'datalastic',
                api_key=os.getenv('DATALASTIC_API_KEY')
            )

            # Provider mock (testes)
            provider = AISProviderFactory.create('mock')
        """
        providers = {
            'datalastic': DatalasticProvider,
            'mock': MockAISProvider,
        }

        provider_class = providers.get(provider_type.lower())

        if not provider_class:
            available = ', '.join(providers.keys())
            raise ValueError(
                f"Provider desconhecido: {provider_type}. "
                f"Disponíveis: {available}"
            )

        return provider_class(**kwargs)
```

---

### **1.2 Integrar no predictor_enriched.py**

**Modificações no `predictor_enriched.py`:**

```python
# No início do arquivo
import os
from typing import Dict, List, Optional, Tuple

try:
    from ais_provider import AISProvider, AISProviderFactory, PortTraffic
    AIS_AVAILABLE = True
except ImportError:
    AIS_AVAILABLE = False
    print("[AVISO] Módulo AIS não disponível. Usando features estimadas.")


class EnrichedPredictor:
    """Preditor com suporte opcional a dados Datalastic AIS real-time."""

    def __init__(self, use_datalastic: bool = False):
        """
        Inicializa preditor.

        Args:
            use_datalastic: Se True, usa Datalastic API para features AIS em tempo real
        """
        self.models = self._load_models()
        self.lineup_history = self._load_lineup_history()
        self.porto_stats = self._calculate_porto_stats()

        # Configurar Datalastic provider (opcional)
        self.ais_provider = None
        if use_datalastic and AIS_AVAILABLE:
            api_key = os.getenv('DATALASTIC_API_KEY')

            if not api_key:
                print(Colors.warning(
                    "[AVISO] DATALASTIC_API_KEY não configurada. "
                    "Configure com: export DATALASTIC_API_KEY='sua_key'"
                ))
            else:
                try:
                    self.ais_provider = AISProviderFactory.create(
                        'datalastic',
                        api_key=api_key
                    )
                    print(Colors.success("[OK] Datalastic AIS Provider ativo"))
                    print(Colors.info(f"    Plano recomendado: Starter (€199/mês, 20K créditos)"))
                except Exception as e:
                    print(Colors.warning(f"[AVISO] Erro ao inicializar Datalastic: {e}"))
                    self.ais_provider = None

        print(Colors.success("[OK] EnrichedPredictor inicializado"))

    def _get_ais_features(
        self,
        porto: str,
        imo: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Obtém features AIS real-time da Datalastic ou usa fallback histórico.

        Args:
            porto: Nome do porto
            imo: Código IMO do navio (opcional)

        Returns:
            Dict com features AIS
        """
        # Coordenadas do porto (já disponíveis em PORTOS)
        from pipelines.datalastic_integration import PORTOS
        porto_coords = PORTOS.get(porto)

        if not porto_coords:
            print(f"[AVISO] Porto {porto} sem coordenadas. Usando fallback.")
            return self._get_ais_fallback(porto)

        # Tentar usar dados AIS reais da Datalastic
        if self.ais_provider:
            try:
                # Obter tráfego na área do porto
                traffic = self.ais_provider.get_port_traffic(
                    lat=porto_coords['lat'],
                    lon=porto_coords['lon'],
                    radius_km=porto_coords.get('radius', 50)  # Usar raio específico do porto
                )

                print(Colors.success(
                    f"[DATALASTIC] Porto {porto}: {traffic.vessels_in_radius} navios "
                    f"({traffic.vessels_anchored} ancorados)"
                ))

                # Calcular ETA média baseado em distância e velocidade
                eta_media_horas = 0.0
                if traffic.avg_speed_knots > 0:
                    # Converter milhas náuticas para horas de viagem
                    eta_media_horas = (traffic.avg_distance_km / 1.852) / traffic.avg_speed_knots

                return {
                    'ais_navios_no_raio': float(traffic.vessels_in_radius),
                    'ais_fila_ao_largo': float(traffic.vessels_anchored),
                    'ais_velocidade_media_kn': traffic.avg_speed_knots,
                    'ais_dist_media_km': traffic.avg_distance_km,
                    'ais_eta_media_horas': eta_media_horas,
                }

            except Exception as e:
                print(Colors.warning(f"[AVISO] Erro ao obter dados Datalastic: {e}. Usando fallback."))

        # Fallback: usar valores estimados baseados em histórico
        return self._get_ais_fallback(porto)

    def _get_ais_fallback(self, porto: str) -> Dict[str, float]:
        """
        Fallback: estima features AIS baseado em histórico.

        Este é o comportamento atual do sistema (antes da integração Datalastic).
        """
        fila_historica = self.estimate_fila_historica(porto, datetime.now())

        return {
            'ais_navios_no_raio': float(fila_historica),
            'ais_fila_ao_largo': float(fila_historica),
            'ais_velocidade_media_kn': 10.0,  # Valor fixo conservador
            'ais_dist_media_km': 100.0,       # Valor fixo conservador
            'ais_eta_media_horas': 10.0,      # Valor fixo conservador
        }

    def enrich_features(
        self,
        navio_data: Dict,
        use_complete_model: bool = False,
        force_profile: Optional[str] = None
    ) -> Tuple[Dict, str]:
        """
        Enriquece features (com suporte a Datalastic AIS real-time).
        """
        features = {}

        # ... código existente ...

        # ===== FEATURES AIS (DATALASTIC REAL-TIME OU ESTIMADAS) =====
        imo = navio_data.get('imo')  # Aceitar IMO como input
        ais_features = self._get_ais_features(porto, imo)
        features.update(ais_features)

        # ... resto do código ...

        return features, perfil
```

---

### **1.3 Configuração no Streamlit**

**Adicionar no `streamlit_prediction_app.py`:**

```python
# Na sidebar, adicionar configuração Datalastic
with st.sidebar.expander("🛰️ Dados AIS em Tempo Real (Datalastic)", expanded=False):
    st.markdown("""
    ### O que é Datalastic AIS?

    Sistema de rastreamento de navios em tempo real via satélite.

    **Benefícios:**
    - 📍 Posição exata de navios (lat/lon, velocidade)
    - 🔍 Conta navios ancorados em tempo real
    - 🎯 Melhora precisão de previsão em 50-70%

    **Custo:**
    - Starter: €199/mês (20.000 créditos)
    - Experimenter: €399/mês (80.000 créditos)

    **Status atual:**
    - ✅ Já usado para treinar modelos (308 eventos)
    - ✅ Código de integração pronto
    """)

    use_datalastic = st.checkbox(
        "Usar Datalastic AIS real-time",
        value=False,
        help="Ativa busca de dados AIS em tempo real. Requer API key configurada."
    )

    if use_datalastic:
        # Verificar se API key está configurada
        api_key = os.getenv('DATALASTIC_API_KEY')

        if not api_key:
            st.error("""
            ⚠️ **DATALASTIC_API_KEY não configurada**

            Configure a API key com:
            ```bash
            export DATALASTIC_API_KEY='sua_key_aqui'
            ```

            Obtenha sua key em: https://datalastic.com/pricing/
            """)

            # Permitir input manual temporário
            api_key_input = st.text_input(
                "API Key (temporária)",
                type="password",
                help="Cole sua API key Datalastic aqui (apenas para esta sessão)"
            )

            if api_key_input:
                os.environ['DATALASTIC_API_KEY'] = api_key_input
                api_key = api_key_input

        if api_key:
            # Recarregar predictor com Datalastic
            predictor = EnrichedPredictor(use_datalastic=True)

            st.success("✅ Datalastic AIS ativo")
            st.info(f"💳 Consumo de créditos: ~1-5 créditos por previsão")

            # Mostrar contador de créditos (se disponível)
            if hasattr(predictor.ais_provider, 'client'):
                credits_used = predictor.ais_provider.client.credits_used
                st.metric("Créditos usados (sessão)", credits_used)
    else:
        # Predictor padrão (sem Datalastic)
        predictor = load_predictor()
        st.info("ℹ️ Usando estimativas históricas (sem AIS real-time)")
```

---

## 📊 Fase 2: Métricas e Monitoramento

### **2.1 Criar Dashboard de Comparação**

**Arquivo:** `ais_comparison_dashboard.py`

```python
"""
Dashboard para comparar previsões COM e SEM dados AIS.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from predictor_enriched import EnrichedPredictor

def compare_predictions():
    """Compara previsões com e sem AIS."""

    st.title("📊 Comparação: AIS vs Histórico")

    # Testar com mesmo navio
    test_vessel = {
        'porto': 'Santos',
        'tipo': 'Bulk Carrier',
        'carga': 'Soja em Graos',
        'eta': '2026-02-15',
        'dwt': 75000,
        'calado': 12.5,
        'toneladas': 60000,
        'imo': '9123456'
    }

    # Previsão SEM AIS
    predictor_no_ais = EnrichedPredictor()
    result_no_ais = predictor_no_ais.predict(test_vessel)

    # Previsão COM AIS
    predictor_with_ais = EnrichedPredictor(ais_provider='aishub')
    result_with_ais = predictor_with_ais.predict(test_vessel)

    # Comparar
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Sem AIS (Histórico)",
            f"{result_no_ais['tempo_espera_previsto_dias']:.1f} dias",
            f"{result_no_ais['categoria_fila']}"
        )

    with col2:
        delta = result_with_ais['tempo_espera_previsto_dias'] - result_no_ais['tempo_espera_previsto_dias']
        st.metric(
            "Com AIS (Real-time)",
            f"{result_with_ais['tempo_espera_previsto_dias']:.1f} dias",
            f"{delta:+.1f} dias",
            delta_color="inverse"
        )

    # Gráfico de features
    st.subheader("📈 Diferença nas Features AIS")

    features_comparison = pd.DataFrame({
        'Feature': ['Navios no Raio', 'Fila ao Largo', 'Velocidade Média', 'Distância Média'],
        'Sem AIS': [
            result_no_ais.get('ais_navios_no_raio', 0),
            result_no_ais.get('ais_fila_ao_largo', 0),
            10.0,  # Fixo
            100.0  # Fixo
        ],
        'Com AIS': [
            result_with_ais.get('ais_navios_no_raio', 0),
            result_with_ais.get('ais_fila_ao_largo', 0),
            result_with_ais.get('ais_velocidade_media_kn', 10.0),
            result_with_ais.get('ais_dist_media_km', 100.0)
        ]
    })

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Sem AIS', x=features_comparison['Feature'], y=features_comparison['Sem AIS']))
    fig.add_trace(go.Bar(name='Com AIS', x=features_comparison['Feature'], y=features_comparison['Com AIS']))
    fig.update_layout(barmode='group')

    st.plotly_chart(fig, use_container_width=True)
```

---

## 🎯 Métricas de Sucesso

### **KPIs para Avaliar Impacto AIS:**

1. **Redução de MAE (Mean Absolute Error)**
   - Target: -50% no erro médio
   - Medição: Comparar previsões vs realidade em 30 dias

2. **Melhoria no R²**
   - Target: +2-5% no R²
   - Medição: Re-treinar modelo com features AIS

3. **Taxa de Acerto de Categoria**
   - Target: +10-15% na acurácia de classificação
   - Medição: % de previsões na categoria correta

4. **Detecção de Anomalias**
   - Target: 100% de navios atrasados detectados
   - Medição: Alertas gerados vs atrasos reais

---

## 📅 Cronograma Detalhado

### **Sprint 1 (Semana 1-2): Fundação**
- [ ] Criar `ais_provider.py` com interface abstrata
- [ ] Implementar `AISHubProvider` (gratuito)
- [ ] Testes unitários dos providers
- [ ] Documentação da API

### **Sprint 2 (Semana 2-3): Integração**
- [ ] Modificar `predictor_enriched.py` para usar AIS
- [ ] Adicionar configuração no Streamlit
- [ ] Implementar fallback gracioso
- [ ] Logs e monitoramento

### **Sprint 3 (Semana 3-4): Validação**
- [ ] Coletar dados reais por 1 semana
- [ ] Comparar previsões COM vs SEM AIS
- [ ] Medir melhoria nas métricas
- [ ] Ajustar thresholds se necessário

### **Sprint 4 (Semana 4-5): Otimização**
- [ ] Implementar cache inteligente
- [ ] Adicionar rate limiting
- [ ] Dashboard de comparação
- [ ] Documentação final

---

## 💰 Análise de Custo-Benefício (Datalastic)

### **Cenário 1: Datalastic Starter (€199/mês)**

**Investimento:** €199/mês (20.000 créditos)

**Ganho esperado:** +50-60% precisão nas previsões

**Capacidade:**
- ~20.000 previsões/mês (1 crédito/previsão)
- ~4.000 previsões/mês (5 créditos/previsão para dados mais completos)
- ~660 previsões/mês (30 créditos/previsão com histórico de 30 dias)

**ROI:** Break-even com 1 navio otimizado/mês
- Economia por navio: €300-1000 (custo de atraso evitado)
- Retorno: 150-500% em 1 mês

**Recomendado para:**
- ✅ 10-50 previsões/dia
- ✅ Operação contínua
- ✅ Portos com alta variabilidade de fila

---

### **Cenário 2: Datalastic Experimenter (€399/mês)**

**Investimento:** €399/mês (80.000 créditos)

**Ganho esperado:** +60-70% precisão nas previsões

**Capacidade:**
- ~80.000 previsões/mês (1 crédito/previsão)
- ~16.000 previsões/mês (5 créditos/previsão)
- ~2.600 previsões/mês (30 créditos/previsão)

**ROI:** Break-even com 1-2 navios otimizados/mês
- Economia por navio: €300-1000
- Retorno: 75-250% em 1 mês

**Recomendado para:**
- ✅ 50+ previsões/dia
- ✅ Múltiplos portos simultaneamente
- ✅ Histórico detalhado (30+ dias de tracking)
- ✅ Dashboards e análises contínuas

---

### **Comparação com Status Atual (Sem AIS)**

| Métrica | Sem AIS (Atual) | Com Datalastic | Melhoria |
|---------|-----------------|----------------|----------|
| MAE (Erro Médio) | 16-25 horas | 8-12 horas | **-50%** |
| R² (Qualidade) | 97-98% | 99-99.5% | **+2%** |
| Acurácia Categoria | 93-97% | 98-100% | **+5%** |
| Falsos Positivos | 3-7% | 0-2% | **-70%** |
| Custo Operacional | €0/mês | €199-399/mês | +€199-399 |
| ROI mensal | - | 150-500% | - |

**Conclusão:** Com apenas 1-2 navios otimizados por mês, o investimento já se paga.

---

## 🚀 Quick Start com Datalastic

### **Para começar HOJE com Datalastic:**

```bash
# 1. Obter API key Datalastic
# Acesse: https://datalastic.com/pricing/
# Escolha plano Starter (€199/mês) ou trial gratuito (14 dias)

# 2. Configurar API key
export DATALASTIC_API_KEY='sua_key_aqui'

# 3. Testar integração existente
cd /home/user/previsao_filas
python3 pipelines/datalastic_integration.py --teste

# Saída esperada:
# ✅ Cliente inicializado
# ✅ Posição obtida:
#    IMO: 9797058
#    Lat/Lon: -23.96, -46.32
#    Speed: 12.5 knots
#    Status: underway

# 4. Adicionar DatalasticProvider ao ais_provider.py
# (copiar código da seção 1.1 acima)

# 5. Testar provider
python3 -c "
import os
from ais_provider import AISProviderFactory

# Criar provider Datalastic
provider = AISProviderFactory.create(
    'datalastic',
    api_key=os.getenv('DATALASTIC_API_KEY')
)

# Testar Santos
traffic = provider.get_port_traffic(
    lat=-23.96,
    lon=-46.32,
    radius_km=50
)

print(f'✅ Navios na área: {traffic.vessels_in_radius}')
print(f'✅ Navios ancorados: {traffic.vessels_anchored}')
print(f'✅ Velocidade média: {traffic.avg_speed_knots:.1f} kn')
print(f'✅ Créditos usados: {provider.client.credits_used}')
"

# 6. Integrar no predictor
# Modificar predictor_enriched.py (ver seção 1.2)

# 7. Testar no Streamlit
streamlit run streamlit_prediction_app.py

# 8. Ativar Datalastic na sidebar:
# → 🛰️ Dados AIS em Tempo Real (Datalastic)
# → ☑️ Usar Datalastic AIS real-time
```

### **Validação Rápida (5 minutos):**

```python
# teste_datalastic_rapido.py
import os
from ais_provider import AISProviderFactory

# Configurar
api_key = os.getenv('DATALASTIC_API_KEY')
if not api_key:
    print("❌ Configure: export DATALASTIC_API_KEY='sua_key'")
    exit(1)

# Criar provider
provider = AISProviderFactory.create('datalastic', api_key=api_key)

# Testar todos os portos
portos = {
    'Santos': (-23.96, -46.32, 50),
    'Paranaguá': (-25.52, -48.51, 40),
    'Rio Grande': (-32.04, -52.10, 40),
    'Vitória': (-20.32, -40.34, 30),
    'Itaqui': (-2.57, -44.37, 30)
}

print("=" * 70)
print("TESTE DATALASTIC - TRÁFEGO PORTUÁRIO BRASIL")
print("=" * 70)

for porto, (lat, lon, radius) in portos.items():
    traffic = provider.get_port_traffic(lat, lon, radius)
    print(f"\n📍 {porto}:")
    print(f"   Navios no raio: {traffic.vessels_in_radius}")
    print(f"   Ancorados: {traffic.vessels_anchored}")
    print(f"   Em movimento: {traffic.vessels_underway}")
    print(f"   Velocidade média: {traffic.avg_speed_knots:.1f} kn")

print(f"\n💳 Total de créditos usados: {provider.client.credits_used}")
print("=" * 70)
```

---

## 📚 Recursos Adicionais

### **Datalastic API - Documentação:**

1. **Website Principal**
   - URL: https://datalastic.com
   - Pricing: https://datalastic.com/pricing/
   - Trial: 14 dias gratuitos

2. **Documentação API**
   - Base URL: https://api.datalastic.com/api/v0
   - Docs: https://api.datalastic.com/docs
   - Swagger: https://api.datalastic.com/swagger

3. **Planos Disponíveis:**

   | Plano | Créditos | Preço | Use Case |
   |-------|----------|-------|----------|
   | Trial | 1.000 | Grátis | Testes (14 dias) |
   | Starter | 20.000 | €199/mês | 10-50 previsões/dia |
   | Experimenter | 80.000 | €399/mês | 50+ previsões/dia |
   | Custom | 200.000+ | Negociar | Operação enterprise |

4. **Endpoints Principais:**

   ```
   GET /vessel_info?api-key={key}&imo={imo}
   # Posição atual de um navio (1 crédito)

   GET /vessel_history?api-key={key}&imo={imo}&from={date}&to={date}
   # Histórico de posições (N dias = N créditos)

   GET /vessel_inradius?api-key={key}&lat={lat}&lon={lon}&radius={nm}
   # Navios em área (1 crédito por navio retornado)
   ```

5. **Arquivos do Projeto:**
   - `pipelines/datalastic_integration.py` - Cliente completo
   - `ais_provider.py` - Interface abstrata (a criar)
   - `models/vegetal_metadata.json` - Modelo treinado com dados Datalastic
   - `models/mineral_metadata.json` - Modelo treinado com dados Datalastic

6. **Suporte:**
   - Email: support@datalastic.com
   - Documentação: https://datalastic.com/docs/api
   - Status: https://status.datalastic.com

---

## ✅ Checklist de Implementação Datalastic

### **Fase 1: Preparação (Dia 1)**
- [ ] Criar conta Datalastic (https://datalastic.com/pricing/)
- [ ] Obter API key (Trial 14 dias ou Starter €199/mês)
- [ ] Configurar `export DATALASTIC_API_KEY='sua_key'`
- [ ] Testar `pipelines/datalastic_integration.py --teste`
- [ ] Validar acesso aos 5 portos brasileiros

### **Fase 2: Desenvolvimento (Dias 2-3)**
- [ ] Adicionar `DatalasticProvider` ao `ais_provider.py`
- [ ] Implementar `get_vessel_position()` usando `vessel_info`
- [ ] Implementar `get_port_traffic()` usando `vessel_inradius`
- [ ] Implementar `get_vessels_in_radius()` com filtro de status
- [ ] Atualizar `AISProviderFactory` para incluir 'datalastic'
- [ ] Adicionar testes unitários básicos

### **Fase 3: Integração no Predictor (Dias 4-5)**
- [ ] Modificar `EnrichedPredictor.__init__()` para aceitar `use_datalastic`
- [ ] Criar método `_get_ais_features()` com fallback
- [ ] Criar método `_get_ais_fallback()` (valores históricos)
- [ ] Atualizar `enrich_features()` para usar dados Datalastic
- [ ] Testar previsão COM e SEM Datalastic (mesmo navio)
- [ ] Validar que features AIS são populadas corretamente

### **Fase 4: Interface Streamlit (Dia 6)**
- [ ] Adicionar expander "Dados AIS em Tempo Real (Datalastic)"
- [ ] Criar checkbox "Usar Datalastic AIS real-time"
- [ ] Implementar verificação de API key
- [ ] Adicionar input manual temporário para API key
- [ ] Mostrar contador de créditos usados
- [ ] Testar toggle ON/OFF no Streamlit

### **Fase 5: Validação e Métricas (Semana 2)**
- [ ] Coletar 50 previsões COM Datalastic
- [ ] Coletar 50 previsões SEM Datalastic
- [ ] Calcular MAE, R², acurácia para ambos
- [ ] Criar dashboard de comparação
- [ ] Documentar melhoria nas métricas
- [ ] Calcular consumo médio de créditos/previsão

### **Fase 6: Otimização (Semana 3)**
- [ ] Implementar cache de 5 minutos para mesmo porto
- [ ] Adicionar rate limiting (evitar esgotar créditos)
- [ ] Criar alarme quando créditos < 10%
- [ ] Otimizar queries (usar raio específico por porto)
- [ ] Documentar best practices de uso

### **Fase 7: Documentação Final (Semana 4)**
- [ ] Atualizar README.md com seção Datalastic
- [ ] Criar guia de troubleshooting
- [ ] Documentar custo real mensal (créditos gastos)
- [ ] Criar FAQ sobre Datalastic
- [ ] Preparar apresentação de ROI

---

## 🎓 Próximos Passos (Após Datalastic Integrado)

Após validação bem-sucedida da integração Datalastic:

1. **Otimizar Consumo de Créditos**
   - Implementar cache Redis (TTL 5 minutos)
   - Agendar updates em batch (horário de baixa demanda)
   - Usar raios menores para portos pequenos

2. **Criar Alertas Proativos**
   - Navio atrasado > 12h do ETA original
   - Fila aumentou > 3 navios em 1 hora
   - Velocidade média caiu < 5 knots (congestionamento)
   - Créditos Datalastic < 1000 (alerta de recarga)

3. **Dashboard de Monitoramento Live**
   - Mapa com posição real dos navios
   - Heatmap de densidade portuária
   - Timeline de chegadas previstas vs reais
   - Gráfico de consumo de créditos

4. **Re-treinar Modelos com Dados AIS Reais**
   - Coletar 6-12 meses de dados Datalastic
   - Adicionar features: heading, draught, destination
   - Treinar modelo específico por porto
   - Validar melhoria > 60% no MAE

5. **API REST para Integrações Externas**
   - Endpoint `/predict` com suporte a Datalastic
   - Webhook para alertas de fila
   - Dashboard público (read-only)

6. **Expansão para Mais Portos**
   - Incluir portos secundários (Suape, Pecém, etc)
   - Configurar raios customizados por porto
   - Validar cobertura Datalastic

---

**Documento atualizado em:** 2026-01-30
**Autor:** Sistema de Previsão de Fila Portuária
**Versão:** 2.0 (Adaptado para Datalastic API)
**Base:** `pipelines/datalastic_integration.py` (já existente)
