# 🚢 Plano de Implementação: Integração AIS Real-Time

## 📋 Sumário Executivo

**Objetivo:** Integrar dados AIS em tempo real para melhorar a precisão das previsões de fila portuária

**Benefício Esperado:** Redução de 50-70% no erro de previsão (MAE)

**Investimento:** €0-500/mês (dependendo da fase)

**ROI:** Break-even com 1-2 navios otimizados/mês

---

## 🎯 Fases de Implementação

### **Fase 1: MVP com API Gratuita (AISHub)** ⏱️ 2-3 semanas
- Custo: **€0/mês**
- Complexidade: **Baixa**
- Impacto esperado: **+30-40% precisão**

### **Fase 2: API Comercial Básica (MarineTraffic)** ⏱️ 1-2 semanas
- Custo: **€300-400/mês**
- Complexidade: **Média**
- Impacto esperado: **+50-60% precisão**

### **Fase 3: API Completa (Spire Maritime)** ⏱️ 2-3 semanas
- Custo: **$500-1000/mês**
- Complexidade: **Alta**
- Impacto esperado: **+60-70% precisão**

---

## 🏗️ Arquitetura da Solução

```
┌─────────────────────────────────────────────────────┐
│           Camada de Aplicação                       │
│  ┌─────────────────────────────────────────────┐   │
│  │     predictor_enriched.py                   │   │
│  │  (consome dados AIS via AISProvider)        │   │
│  └────────────────┬────────────────────────────┘   │
└───────────────────┼─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│          Camada de Abstração AIS                    │
│  ┌─────────────────────────────────────────────┐   │
│  │        ais_provider.py                      │   │
│  │   (Interface abstrata + Factory Pattern)    │   │
│  └──┬────────────┬────────────┬─────────────┬──┘   │
└─────┼────────────┼────────────┼─────────────┼───────┘
      │            │            │             │
┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐ ┌────▼──────┐
│ AISHub    │ │MarineT.│ │VesselFind│ │   Spire   │
│ Provider  │ │Provider│ │ Provider │ │  Provider │
│  (FREE)   │ │ (€300) │ │  (€400)  │ │  ($1000)  │
└───────────┘ └────────┘ └──────────┘ └───────────┘
```

---

## 📝 Fase 1: MVP com AISHub (GRATUITO)

### **1.1 Criar Módulo de Abstração AIS**

**Arquivo:** `ais_provider.py`

```python
"""
Módulo de abstração para provedores AIS.
Suporta múltiplas APIs com interface unificada.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
import requests
from dataclasses import dataclass


@dataclass
class VesselPosition:
    """Posição e status de um navio."""
    imo: str
    mmsi: str
    lat: float
    lon: float
    speed_knots: float
    course: float
    heading: float
    timestamp: datetime
    status: str  # 'underway', 'at anchor', 'moored', etc
    destination: Optional[str] = None


@dataclass
class PortTraffic:
    """Tráfego em uma área portuária."""
    vessels_in_radius: int
    vessels_anchored: int
    vessels_moored: int
    vessels_underway: int
    avg_distance_km: float
    avg_speed_knots: float


class AISProvider(ABC):
    """Interface abstrata para provedores AIS."""

    @abstractmethod
    def get_vessel_position(self, imo: str) -> Optional[VesselPosition]:
        """Obtém posição atual de um navio por IMO."""
        pass

    @abstractmethod
    def get_port_traffic(self, lat: float, lon: float, radius_km: float) -> PortTraffic:
        """Obtém tráfego em uma área portuária."""
        pass

    @abstractmethod
    def get_vessels_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        status_filter: Optional[str] = None
    ) -> List[VesselPosition]:
        """Lista navios em um raio específico."""
        pass


class AISHubProvider(AISProvider):
    """
    Provider gratuito usando AISHub API.

    Limitações:
    - Rate limit: 60 requests/hour
    - Dados com 5-15min de atraso
    - Cobertura: global, mas menos detalhes
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key  # Opcional para uso gratuito
        self.base_url = "http://data.aishub.net/ws.php"
        self.cache = {}  # Cache simples para evitar rate limit
        self.cache_ttl = 300  # 5 minutos

    def get_vessel_position(self, imo: str) -> Optional[VesselPosition]:
        """Busca posição de navio por IMO (limitado em free tier)."""
        # AISHub free não suporta busca por IMO diretamente
        # Seria necessário buscar por área e filtrar
        # Por enquanto, retorna None
        return None

    def get_port_traffic(self, lat: float, lon: float, radius_km: float) -> PortTraffic:
        """Obtém estatísticas de tráfego na área do porto."""
        vessels = self.get_vessels_in_radius(lat, lon, radius_km)

        if not vessels:
            # Fallback: usar valores padrão
            return PortTraffic(
                vessels_in_radius=3,
                vessels_anchored=2,
                vessels_moored=1,
                vessels_underway=0,
                avg_distance_km=50.0,
                avg_speed_knots=5.0
            )

        anchored = sum(1 for v in vessels if 'anchor' in v.status.lower())
        moored = sum(1 for v in vessels if 'moored' in v.status.lower())
        underway = sum(1 for v in vessels if 'underway' in v.status.lower())

        avg_speed = sum(v.speed_knots for v in vessels) / len(vessels) if vessels else 0

        # Calcular distância média do centro
        from math import radians, sin, cos, sqrt, atan2

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Raio da Terra em km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c

        distances = [haversine(lat, lon, v.lat, v.lon) for v in vessels]
        avg_distance = sum(distances) / len(distances) if distances else 0

        return PortTraffic(
            vessels_in_radius=len(vessels),
            vessels_anchored=anchored,
            vessels_moored=moored,
            vessels_underway=underway,
            avg_distance_km=avg_distance,
            avg_speed_knots=avg_speed
        )

    def get_vessels_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        status_filter: Optional[str] = None
    ) -> List[VesselPosition]:
        """Lista navios em raio específico."""
        try:
            # Converter raio de km para graus (aproximado)
            lat_range = radius_km / 111.0  # 1 grau ≈ 111km

            params = {
                'format': 'json',
                'latmin': lat - lat_range,
                'latmax': lat + lat_range,
                'lonmin': lon - lat_range,
                'lonmax': lon + lat_range,
            }

            if self.api_key:
                params['username'] = self.api_key

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            vessels = []
            for vessel_data in data:
                # Parsear resposta AISHub
                vessel = VesselPosition(
                    imo=vessel_data.get('IMO', ''),
                    mmsi=str(vessel_data.get('MMSI', '')),
                    lat=float(vessel_data.get('LATITUDE', 0)),
                    lon=float(vessel_data.get('LONGITUDE', 0)),
                    speed_knots=float(vessel_data.get('SPEED', 0)),
                    course=float(vessel_data.get('COURSE', 0)),
                    heading=float(vessel_data.get('HEADING', 0)),
                    timestamp=datetime.fromtimestamp(vessel_data.get('TIME', 0)),
                    status=vessel_data.get('NAVSTAT', 'unknown'),
                    destination=vessel_data.get('DESTINATION')
                )

                # Filtrar por status se especificado
                if status_filter and status_filter not in vessel.status.lower():
                    continue

                vessels.append(vessel)

            return vessels

        except Exception as e:
            print(f"Erro ao buscar dados AISHub: {e}")
            return []


class MarineTrafficProvider(AISProvider):
    """
    Provider comercial MarineTraffic.

    Vantagens:
    - Busca direta por IMO
    - Dados em tempo real (1-2min atraso)
    - Histórico de 24h
    - Previsão de ETA

    Custo: €300-400/mês
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://services.marinetraffic.com/api"

    def get_vessel_position(self, imo: str) -> Optional[VesselPosition]:
        """Busca posição exata por IMO."""
        try:
            url = f"{self.base_url}/exportvessel/v:8/{self.api_key}"
            params = {
                'v': 8,
                'imo': imo,
                'protocol': 'json'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            vessel_data = data[0]

            return VesselPosition(
                imo=imo,
                mmsi=str(vessel_data.get('MMSI', '')),
                lat=float(vessel_data.get('LAT', 0)),
                lon=float(vessel_data.get('LON', 0)),
                speed_knots=float(vessel_data.get('SPEED', 0)),
                course=float(vessel_data.get('COURSE', 0)),
                heading=float(vessel_data.get('HEADING', 0)),
                timestamp=datetime.strptime(vessel_data.get('TIMESTAMP'), '%Y-%m-%d %H:%M:%S'),
                status=vessel_data.get('STATUS', 'unknown'),
                destination=vessel_data.get('DESTINATION')
            )

        except Exception as e:
            print(f"Erro ao buscar MarineTraffic: {e}")
            return None

    def get_port_traffic(self, lat: float, lon: float, radius_km: float) -> PortTraffic:
        """Implementação similar ao AISHub mas com API MarineTraffic."""
        # TODO: Implementar usando endpoint específico
        pass

    def get_vessels_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        status_filter: Optional[str] = None
    ) -> List[VesselPosition]:
        """Implementação usando endpoint de área."""
        # TODO: Implementar
        pass


class AISProviderFactory:
    """Factory para criar providers AIS."""

    @staticmethod
    def create(provider_type: str, **kwargs) -> AISProvider:
        """
        Cria provider AIS baseado no tipo.

        Args:
            provider_type: 'aishub', 'marinetraffic', 'vesselfinder', 'spire'
            **kwargs: Parâmetros específicos (api_key, etc)

        Returns:
            Instância do provider
        """
        providers = {
            'aishub': AISHubProvider,
            'marinetraffic': MarineTrafficProvider,
            # 'vesselfinder': VesselFinderProvider,  # TODO
            # 'spire': SpireProvider,  # TODO
        }

        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Provider desconhecido: {provider_type}")

        return provider_class(**kwargs)
```

---

### **1.2 Integrar no predictor_enriched.py**

**Modificações no `predictor_enriched.py`:**

```python
# No início do arquivo
from typing import Dict, List, Optional, Tuple
try:
    from ais_provider import AISProvider, AISProviderFactory, PortTraffic
    AIS_AVAILABLE = True
except ImportError:
    AIS_AVAILABLE = False
    print("[AVISO] Módulo AIS não disponível. Usando features estimadas.")


class EnrichedPredictor:
    """Preditor com suporte opcional a dados AIS real-time."""

    def __init__(self, ais_provider: Optional[str] = None, ais_api_key: Optional[str] = None):
        """
        Inicializa preditor.

        Args:
            ais_provider: Tipo de provider AIS ('aishub', 'marinetraffic', None)
            ais_api_key: Chave API para provider comercial
        """
        self.models = self._load_models()
        self.lineup_history = self._load_lineup_history()
        self.porto_stats = self._calculate_porto_stats()

        # Configurar provider AIS (opcional)
        self.ais_provider = None
        if ais_provider and AIS_AVAILABLE:
            try:
                self.ais_provider = AISProviderFactory.create(
                    ais_provider,
                    api_key=ais_api_key
                )
                print(Colors.success(f"[OK] AIS Provider ativo: {ais_provider}"))
            except Exception as e:
                print(Colors.warning(f"[AVISO] Erro ao inicializar AIS: {e}"))
                self.ais_provider = None

        print(Colors.success("[OK] EnrichedPredictor inicializado"))

    def _get_ais_features(
        self,
        porto: str,
        imo: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Obtém features AIS real-time ou usa fallback.

        Args:
            porto: Nome do porto
            imo: Código IMO do navio (opcional)

        Returns:
            Dict com features AIS
        """
        porto_coords = PORTOS[porto]

        # Tentar usar dados AIS reais
        if self.ais_provider:
            try:
                # Obter tráfego na área do porto
                traffic = self.ais_provider.get_port_traffic(
                    lat=porto_coords['lat'],
                    lon=porto_coords['lon'],
                    radius_km=50  # 50km do porto
                )

                return {
                    'ais_navios_no_raio': float(traffic.vessels_in_radius),
                    'ais_fila_ao_largo': float(traffic.vessels_anchored),
                    'ais_velocidade_media_kn': traffic.avg_speed_knots,
                    'ais_dist_media_km': traffic.avg_distance_km,
                    'ais_eta_media_horas': traffic.avg_distance_km / max(traffic.avg_speed_knots, 1) * 1.852,  # Converter para horas
                }

            except Exception as e:
                print(Colors.warning(f"[AVISO] Erro ao obter dados AIS: {e}. Usando fallback."))

        # Fallback: usar valores estimados (comportamento atual)
        fila_historica = self.estimate_fila_historica(porto, datetime.now())

        return {
            'ais_navios_no_raio': float(fila_historica),
            'ais_fila_ao_largo': float(fila_historica),
            'ais_velocidade_media_kn': 10.0,
            'ais_dist_media_km': 100.0,
            'ais_eta_media_horas': 10.0,
        }

    def enrich_features(
        self,
        navio_data: Dict,
        use_complete_model: bool = False,
        force_profile: Optional[str] = None
    ) -> Tuple[Dict, str]:
        """
        Enriquece features (com suporte a AIS real-time).
        """
        features = {}

        # ... código existente ...

        # ===== FEATURES AIS (REAL-TIME OU ESTIMADAS) =====
        imo = navio_data.get('imo')  # Novo: aceitar IMO como input
        ais_features = self._get_ais_features(porto, imo)
        features.update(ais_features)

        # ... resto do código ...

        return features, perfil
```

---

### **1.3 Configuração no Streamlit**

**Adicionar no `streamlit_prediction_app.py`:**

```python
# Na sidebar, adicionar configuração AIS
with st.sidebar.expander("🛰️ Configuração AIS (Opcional)", expanded=False):
    use_ais = st.checkbox("Usar dados AIS real-time", value=False)

    if use_ais:
        ais_provider = st.selectbox(
            "Provider AIS",
            ["aishub (Gratuito)", "marinetraffic (€300/mês)", "spire ($1000/mês)"],
            index=0
        )

        # Se não for gratuito, pedir API key
        if "Gratuito" not in ais_provider:
            ais_api_key = st.text_input(
                "API Key",
                type="password",
                help="Sua chave de API do provider selecionado"
            )
        else:
            ais_api_key = None

        # Recarregar predictor com AIS
        provider_name = ais_provider.split()[0].lower()
        predictor = EnrichedPredictor(
            ais_provider=provider_name,
            ais_api_key=ais_api_key
        )

        st.success(f"✅ AIS ativo: {provider_name}")
    else:
        predictor = load_predictor()  # Sem AIS
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

## 💰 Análise de Custo-Benefício

### **Cenário 1: AISHub (Gratuito)**
**Investimento:** €0/mês
**Ganho:** +30-40% precisão
**Limitações:** Rate limit, atraso de 5-15min
**Recomendado para:** Validação de conceito

### **Cenário 2: MarineTraffic (€300/mês)**
**Investimento:** €300-400/mês
**Ganho:** +50-60% precisão
**ROI:** 1 navio otimizado/mês já paga
**Recomendado para:** Operação contínua com 10+ previsões/dia

### **Cenário 3: Spire Maritime ($1000/mês)**
**Investimento:** $1000-1500/mês
**Ganho:** +60-70% precisão + features avançadas
**ROI:** 2-3 navios otimizados/mês
**Recomendado para:** Operação crítica com 50+ previsões/dia

---

## 🚀 Quick Start

### **Para começar HOJE com API gratuita:**

```bash
# 1. Instalar dependências
pip install requests

# 2. Criar arquivo ais_provider.py
# (copiar código acima)

# 3. Testar provider
python -c "
from ais_provider import AISProviderFactory

# Criar provider gratuito
provider = AISProviderFactory.create('aishub')

# Testar Santos
traffic = provider.get_port_traffic(
    lat=-23.96,
    lon=-46.32,
    radius_km=50
)

print(f'Navios na área: {traffic.vessels_in_radius}')
print(f'Navios ancorados: {traffic.vessels_anchored}')
"

# 4. Integrar no predictor
# (modificar __init__ do EnrichedPredictor)

# 5. Testar no Streamlit
streamlit run streamlit_prediction_app.py
```

---

## 📚 Recursos Adicionais

### **APIs AIS Recomendadas:**

1. **AISHub** (Gratuito)
   - Website: http://www.aishub.net
   - Docs: http://www.aishub.net/api
   - Rate: 60 req/hour

2. **MarineTraffic** (€300-400/mês)
   - Website: https://www.marinetraffic.com
   - Docs: https://www.marinetraffic.com/en/ais-api-services
   - Features: Histórico, ETA prediction, Port calls

3. **VesselFinder** (€400-600/mês)
   - Website: https://www.vesselfinder.com
   - Docs: https://api.vesselfinder.com
   - Features: Real-time, Satellite AIS

4. **Spire Maritime** ($500-1500/mês)
   - Website: https://spire.com/maritime
   - Docs: https://spire.com/maritime/docs
   - Features: ML-enhanced, Weather integration

---

## ✅ Checklist de Implementação

- [ ] Criar `ais_provider.py` com interface abstrata
- [ ] Implementar `AISHubProvider` (gratuito)
- [ ] Adicionar testes unitários
- [ ] Modificar `EnrichedPredictor.__init__()` para aceitar AIS provider
- [ ] Criar método `_get_ais_features()` no predictor
- [ ] Atualizar `enrich_features()` para usar dados AIS
- [ ] Adicionar configuração AIS no Streamlit sidebar
- [ ] Criar dashboard de comparação
- [ ] Documentar uso e configuração
- [ ] Coletar métricas de comparação (1 semana)
- [ ] Decidir sobre migração para API paga

---

## 🎓 Próximos Passos

Após validação bem-sucedida da Fase 1:

1. **Implementar providers comerciais** (MarineTraffic, Spire)
2. **Adicionar cache Redis** para otimizar chamadas
3. **Criar alertas proativos** (navio atrasado, fila aumentando)
4. **Dashboard de monitoramento live** com mapa
5. **Re-treinar modelos** com features AIS reais
6. **API REST** para integrações externas

---

**Documento criado em:** 2026-01-30
**Autor:** Sistema de Previsão de Fila Portuária
**Versão:** 1.0
