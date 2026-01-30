"""
Módulo de abstração para provedores AIS (Automatic Identification System).

Este módulo fornece uma interface unificada para acessar dados de múltiplas
APIs AIS, permitindo trocar de provider facilmente.

Providers suportados:
- AISHub (gratuito, limitado)
- MarineTraffic (comercial, €300-400/mês)
- VesselFinder (comercial, €400-600/mês)
- Spire Maritime (comercial, $500-1500/mês)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import requests
from math import radians, sin, cos, sqrt, atan2


@dataclass
class VesselPosition:
    """Posição e status de um navio obtido via AIS."""

    imo: str
    mmsi: str
    lat: float
    lon: float
    speed_knots: float
    course: float
    heading: float
    timestamp: datetime
    status: str  # 'underway', 'at anchor', 'moored', 'not under command'
    destination: Optional[str] = None
    eta: Optional[datetime] = None
    draught: Optional[float] = None  # Calado em metros


@dataclass
class PortTraffic:
    """Estatísticas de tráfego em uma área portuária."""

    vessels_in_radius: int
    vessels_anchored: int
    vessels_moored: int
    vessels_underway: int
    avg_distance_km: float
    avg_speed_knots: float
    timestamp: datetime


class AISProvider(ABC):
    """Interface abstrata para provedores AIS."""

    @abstractmethod
    def get_vessel_position(self, imo: str) -> Optional[VesselPosition]:
        """
        Obtém posição atual de um navio por código IMO.

        Args:
            imo: Código IMO do navio (7 dígitos)

        Returns:
            VesselPosition com dados atuais ou None se não encontrado
        """
        pass

    @abstractmethod
    def get_port_traffic(
        self, lat: float, lon: float, radius_km: float
    ) -> PortTraffic:
        """
        Obtém estatísticas de tráfego em uma área portuária.

        Args:
            lat: Latitude do centro do porto
            lon: Longitude do centro do porto
            radius_km: Raio de busca em quilômetros

        Returns:
            PortTraffic com estatísticas agregadas
        """
        pass

    @abstractmethod
    def get_vessels_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        status_filter: Optional[str] = None,
    ) -> List[VesselPosition]:
        """
        Lista todos os navios em um raio específico.

        Args:
            lat: Latitude do centro
            lon: Longitude do centro
            radius_km: Raio de busca em quilômetros
            status_filter: Filtro de status ('anchor', 'underway', etc)

        Returns:
            Lista de VesselPosition
        """
        pass

    @staticmethod
    def haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calcula distância entre dois pontos usando fórmula de Haversine.

        Args:
            lat1, lon1: Coordenadas do ponto 1
            lat2, lon2: Coordenadas do ponto 2

        Returns:
            Distância em quilômetros
        """
        R = 6371  # Raio da Terra em km

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(
            dlon / 2
        ) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c


class AISHubProvider(AISProvider):
    """
    Provider gratuito usando AISHub API.

    Website: http://www.aishub.net
    Docs: http://www.aishub.net/api

    Limitações:
    - Rate limit: 60 requests/hour (gratuito)
    - Dados com 5-15min de atraso
    - Cobertura: global, mas menos detalhes que APIs pagas
    - Busca por IMO não suportada diretamente (apenas por área)

    Uso:
        provider = AISHubProvider()
        traffic = provider.get_port_traffic(-23.96, -46.32, 50)
        print(f"Navios: {traffic.vessels_in_radius}")
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa provider AISHub.

        Args:
            api_key: Username AISHub (opcional, melhora rate limit)
        """
        self.api_key = api_key
        self.base_url = "http://data.aishub.net/ws.php"
        self.cache = {}
        self.cache_ttl = 300  # Cache de 5 minutos

    def get_vessel_position(self, imo: str) -> Optional[VesselPosition]:
        """
        Busca posição de navio por IMO.

        NOTA: AISHub gratuito não suporta busca direta por IMO.
        Esta função sempre retorna None. Use get_vessels_in_radius()
        e filtre por IMO manualmente.
        """
        return None

    def get_port_traffic(
        self, lat: float, lon: float, radius_km: float
    ) -> PortTraffic:
        """Obtém estatísticas de tráfego na área do porto."""
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
                timestamp=datetime.now(),
            )

        # Contar por status
        anchored = sum(1 for v in vessels if "anchor" in v.status.lower())
        moored = sum(1 for v in vessels if "moored" in v.status.lower())
        underway = sum(1 for v in vessels if "underway" in v.status.lower())

        # Calcular velocidade média
        speeds = [v.speed_knots for v in vessels if v.speed_knots > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0

        # Calcular distância média do centro
        distances = [
            self.haversine_distance(lat, lon, v.lat, v.lon) for v in vessels
        ]
        avg_distance = sum(distances) / len(distances) if distances else 0.0

        return PortTraffic(
            vessels_in_radius=len(vessels),
            vessels_anchored=anchored,
            vessels_moored=moored,
            vessels_underway=underway,
            avg_distance_km=avg_distance,
            avg_speed_knots=avg_speed,
            timestamp=datetime.now(),
        )

    def get_vessels_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        status_filter: Optional[str] = None,
    ) -> List[VesselPosition]:
        """Lista navios em raio específico."""
        try:
            # Converter raio de km para graus (aproximado)
            # 1 grau de latitude ≈ 111km
            lat_range = radius_km / 111.0
            lon_range = radius_km / (111.0 * cos(radians(lat)))

            params = {
                "format": "json",
                "latmin": lat - lat_range,
                "latmax": lat + lat_range,
                "lonmin": lon - lon_range,
                "lonmax": lon + lon_range,
            }

            if self.api_key:
                params["username"] = self.api_key

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Verificar se há erro
            if isinstance(data, dict) and "ERROR" in data:
                print(f"Erro AISHub: {data.get('ERROR_MESSAGE', 'Unknown')}")
                return []

            vessels = []

            # Parsear cada navio
            for vessel_data in data:
                try:
                    # Extrair coordenadas
                    vessel_lat = float(vessel_data.get("LATITUDE", 0))
                    vessel_lon = float(vessel_data.get("LONGITUDE", 0))

                    # Verificar se está dentro do raio
                    distance = self.haversine_distance(
                        lat, lon, vessel_lat, vessel_lon
                    )
                    if distance > radius_km:
                        continue

                    # Parsear timestamp
                    time_val = vessel_data.get("TIME", 0)
                    if isinstance(time_val, str):
                        timestamp = datetime.strptime(time_val, "%Y-%m-%d %H:%M:%S")
                    else:
                        timestamp = datetime.fromtimestamp(int(time_val))

                    # Criar objeto VesselPosition
                    vessel = VesselPosition(
                        imo=str(vessel_data.get("IMO", "")),
                        mmsi=str(vessel_data.get("MMSI", "")),
                        lat=vessel_lat,
                        lon=vessel_lon,
                        speed_knots=float(vessel_data.get("SPEED", 0)),
                        course=float(vessel_data.get("COURSE", 0)),
                        heading=float(vessel_data.get("HEADING", 0)),
                        timestamp=timestamp,
                        status=self._parse_navstat(vessel_data.get("NAVSTAT", 15)),
                        destination=vessel_data.get("DESTINATION"),
                        draught=None,  # AISHub free não fornece
                    )

                    # Filtrar por status se especificado
                    if status_filter and status_filter.lower() not in vessel.status.lower():
                        continue

                    vessels.append(vessel)

                except (ValueError, KeyError) as e:
                    # Ignorar navios com dados inválidos
                    continue

            return vessels

        except requests.RequestException as e:
            print(f"Erro ao buscar dados AISHub: {e}")
            return []
        except Exception as e:
            print(f"Erro inesperado AISHub: {e}")
            return []

    def _parse_navstat(self, navstat_code: int) -> str:
        """Converte código NAVSTAT para string legível."""
        navstat_map = {
            0: "under way using engine",
            1: "at anchor",
            2: "not under command",
            3: "restricted manoeuvrability",
            4: "constrained by draught",
            5: "moored",
            6: "aground",
            7: "engaged in fishing",
            8: "under way sailing",
            9: "reserved",
            10: "reserved",
            11: "power-driven towing astern",
            12: "power-driven pushing ahead",
            13: "reserved",
            14: "ais-sart active",
            15: "undefined",
        }
        return navstat_map.get(int(navstat_code), "unknown")


class MockAISProvider(AISProvider):
    """
    Provider mock para testes (não faz chamadas reais).

    Use este provider para desenvolvimento e testes sem
    consumir quota de APIs reais.
    """

    def __init__(self):
        self.mock_vessels = []

    def get_vessel_position(self, imo: str) -> Optional[VesselPosition]:
        """Retorna posição mock."""
        return VesselPosition(
            imo=imo,
            mmsi="123456789",
            lat=-23.96,
            lon=-46.32,
            speed_knots=10.5,
            course=180.0,
            heading=180.0,
            timestamp=datetime.now(),
            status="underway using engine",
            destination="SANTOS",
        )

    def get_port_traffic(
        self, lat: float, lon: float, radius_km: float
    ) -> PortTraffic:
        """Retorna tráfego mock."""
        return PortTraffic(
            vessels_in_radius=5,
            vessels_anchored=3,
            vessels_moored=1,
            vessels_underway=1,
            avg_distance_km=25.0,
            avg_speed_knots=5.0,
            timestamp=datetime.now(),
        )

    def get_vessels_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        status_filter: Optional[str] = None,
    ) -> List[VesselPosition]:
        """Retorna lista mock de navios."""
        mock_vessels = [
            VesselPosition(
                imo="9000001",
                mmsi="111111111",
                lat=lat + 0.1,
                lon=lon + 0.1,
                speed_knots=0.0,
                course=0.0,
                heading=0.0,
                timestamp=datetime.now(),
                status="at anchor",
            ),
            VesselPosition(
                imo="9000002",
                mmsi="222222222",
                lat=lat - 0.1,
                lon=lon - 0.1,
                speed_knots=12.0,
                course=90.0,
                heading=90.0,
                timestamp=datetime.now(),
                status="underway using engine",
            ),
        ]

        if status_filter:
            return [
                v for v in mock_vessels if status_filter.lower() in v.status.lower()
            ]

        return mock_vessels


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

        # Importar cliente existente
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent / 'pipelines'))

        from pipelines.datalastic_integration import DatalasticClient as DatalasticClientBase

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
            timestamp_str = data.get('timestamp', datetime.now().isoformat())
            try:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.now()
            except:
                timestamp = datetime.now()

            # Parsear ETA se disponível
            eta = None
            if data.get('eta'):
                try:
                    eta = datetime.fromisoformat(data['eta'].replace('Z', '+00:00'))
                except:
                    eta = None

            return VesselPosition(
                imo=imo,
                mmsi=str(data.get('mmsi', '')),
                lat=float(data.get('latitude', 0)),
                lon=float(data.get('longitude', 0)),
                speed_knots=float(data.get('speed', 0)),
                course=float(data.get('course', 0)),
                heading=float(data.get('heading', 0)),
                timestamp=timestamp,
                status=data.get('navigational_status', 'unknown'),
                destination=data.get('destination'),
                eta=eta,
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
                    # Parsear timestamp
                    timestamp_str = vessel_data.get('timestamp', datetime.now().isoformat())
                    try:
                        if isinstance(timestamp_str, str):
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            timestamp = datetime.now()
                    except:
                        timestamp = datetime.now()

                    # Parsear ETA
                    eta = None
                    if vessel_data.get('eta'):
                        try:
                            eta = datetime.fromisoformat(vessel_data['eta'].replace('Z', '+00:00'))
                        except:
                            eta = None

                    # Parsear cada navio
                    vessel = VesselPosition(
                        imo=str(vessel_data.get('imo', '')),
                        mmsi=str(vessel_data.get('mmsi', '')),
                        lat=float(vessel_data.get('latitude', 0)),
                        lon=float(vessel_data.get('longitude', 0)),
                        speed_knots=float(vessel_data.get('speed', 0)),
                        course=float(vessel_data.get('course', 0)),
                        heading=float(vessel_data.get('heading', 0)),
                        timestamp=timestamp,
                        status=vessel_data.get('navigational_status', 'unknown'),
                        destination=vessel_data.get('destination'),
                        eta=eta,
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


class AISProviderFactory:
    """Factory para criar providers AIS."""

    @staticmethod
    def create(provider_type: str, **kwargs) -> AISProvider:
        """
        Cria provider AIS baseado no tipo.

        Args:
            provider_type: 'datalastic', 'aishub', 'mock'
            **kwargs: Parâmetros específicos (api_key, etc)

        Returns:
            Instância do provider

        Raises:
            ValueError: Se provider desconhecido

        Exemplo:
            # Provider Datalastic (produção)
            provider = AISProviderFactory.create(
                'datalastic',
                api_key=os.getenv('DATALASTIC_API_KEY')
            )

            # Provider AISHub (gratuito)
            provider = AISProviderFactory.create('aishub')

            # Provider mock (testes)
            provider = AISProviderFactory.create('mock')
        """
        providers = {
            "datalastic": DatalasticProvider,
            "aishub": AISHubProvider,
            "mock": MockAISProvider,
        }

        provider_class = providers.get(provider_type.lower())

        if not provider_class:
            available = ", ".join(providers.keys())
            raise ValueError(
                f"Provider desconhecido: {provider_type}. "
                f"Disponíveis: {available}"
            )

        return provider_class(**kwargs)


# ============================================================================
# TESTES
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testando AIS Providers...\n")

    # Teste 1: Mock Provider
    print("=" * 70)
    print("Teste 1: Mock Provider (sem chamadas reais)")
    print("=" * 70)

    mock = AISProviderFactory.create("mock")

    traffic = mock.get_port_traffic(-23.96, -46.32, 50)
    print(f"✅ Navios na área: {traffic.vessels_in_radius}")
    print(f"✅ Navios ancorados: {traffic.vessels_anchored}")
    print(f"✅ Velocidade média: {traffic.avg_speed_knots:.1f} kn")

    vessels = mock.get_vessels_in_radius(-23.96, -46.32, 50)
    print(f"✅ Encontrados {len(vessels)} navios")

    # Teste 2: AISHub (requer conexão)
    print("\n" + "=" * 70)
    print("Teste 2: AISHub Provider (API gratuita)")
    print("=" * 70)

    try:
        aishub = AISProviderFactory.create("aishub")

        # Testar porto de Santos
        print("Buscando navios em Santos (-23.96, -46.32, raio 50km)...")
        traffic = aishub.get_port_traffic(-23.96, -46.32, 50)

        print(f"✅ Navios na área: {traffic.vessels_in_radius}")
        print(f"✅ Navios ancorados: {traffic.vessels_anchored}")
        print(f"✅ Navios em movimento: {traffic.vessels_underway}")
        print(f"✅ Velocidade média: {traffic.avg_speed_knots:.1f} kn")
        print(f"✅ Distância média: {traffic.avg_distance_km:.1f} km")

        # Listar alguns navios
        vessels = aishub.get_vessels_in_radius(-23.96, -46.32, 50)
        print(f"\n📋 Primeiros 5 navios encontrados:")
        for i, vessel in enumerate(vessels[:5], 1):
            print(f"  {i}. MMSI: {vessel.mmsi}, Status: {vessel.status}, "
                  f"Speed: {vessel.speed_knots:.1f}kn")

    except Exception as e:
        print(f"⚠️ Erro ao testar AISHub: {e}")
        print("(Pode ser rate limit ou problema de conexão)")

    print("\n" + "=" * 70)
    print("✅ Testes concluídos!")
    print("=" * 70)
