"""
Módulo de integração com APIs de clima gratuitas.

Fornece dados meteorológicos e marinhos em tempo real e previsão,
usando Open-Meteo como fonte principal (gratuita, sem API key).

Uso:
    from weather_api import fetch_weather, fetch_marine, get_weather_for_port

Fontes:
    - Open-Meteo Weather API: https://open-meteo.com/en/docs
    - Open-Meteo Marine API: https://open-meteo.com/en/docs/marine-weather-api
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Configuração dos portos brasileiros com coordenadas
PORTS_COORDINATES = {
    "ITAQUI": {"lat": -2.5900, "lon": -44.3600, "name": "Porto do Itaqui (MA)"},
    "PONTA DA MADEIRA": {"lat": -2.5700, "lon": -44.3500, "name": "Ponta da Madeira (MA)"},
    "SANTOS": {"lat": -23.9600, "lon": -46.3000, "name": "Porto de Santos (SP)"},
    "PARANAGUA": {"lat": -25.5160, "lon": -48.5220, "name": "Porto de Paranaguá (PR)"},
    "RIO GRANDE": {"lat": -32.0350, "lon": -52.0980, "name": "Porto de Rio Grande (RS)"},
    "SAO FRANCISCO DO SUL": {"lat": -26.2400, "lon": -48.6350, "name": "São Francisco do Sul (SC)"},
    "SUAPE": {"lat": -8.3900, "lon": -34.9600, "name": "Porto de Suape (PE)"},
    "SALVADOR": {"lat": -12.9700, "lon": -38.5100, "name": "Porto de Salvador (BA)"},
    "VITORIA": {"lat": -20.3200, "lon": -40.2900, "name": "Porto de Vitória (ES)"},
    "RECIFE": {"lat": -8.0500, "lon": -34.8700, "name": "Porto de Recife (PE)"},
    "PECEM": {"lat": -3.5400, "lon": -38.8100, "name": "Porto de Pecém (CE)"},
    "BARCARENA": {"lat": -1.5100, "lon": -48.6200, "name": "Porto de Barcarena (PA)"},
    "VILA DO CONDE": {"lat": -1.5500, "lon": -48.7500, "name": "Vila do Conde (PA)"},
    "SANTAREM": {"lat": -2.4400, "lon": -54.7100, "name": "Porto de Santarém (PA)"},
    "ANTONINA": {"lat": -25.4300, "lon": -48.7100, "name": "Porto de Antonina (PR)"},
    "IMBITUBA": {"lat": -28.2300, "lon": -48.6500, "name": "Porto de Imbituba (SC)"},
    "ITAJAI": {"lat": -26.9000, "lon": -48.6600, "name": "Porto de Itajaí (SC)"},
}

# URLs base das APIs Open-Meteo
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"


def fetch_weather(
    lat: float,
    lon: float,
    days: int = 7,
    timezone: str = "America/Sao_Paulo"
) -> Optional[Dict[str, Any]]:
    """
    Busca dados meteorológicos da Open-Meteo Weather API.

    Args:
        lat: Latitude
        lon: Longitude
        days: Número de dias de previsão (1-16)
        timezone: Fuso horário

    Returns:
        Dict com dados meteorológicos ou None em caso de erro
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "wind_speed_10m",
            "wind_gusts_10m",
            "wind_direction_10m",
            "pressure_msl",
        ]),
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "rain_sum",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
        ]),
        "timezone": timezone,
        "forecast_days": min(days, 16),
    }

    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Erro ao buscar dados meteorológicos: {e}")
        return None


def fetch_marine(
    lat: float,
    lon: float,
    days: int = 7,
    timezone: str = "America/Sao_Paulo"
) -> Optional[Dict[str, Any]]:
    """
    Busca dados marinhos da Open-Meteo Marine API.

    Args:
        lat: Latitude
        lon: Longitude
        days: Número de dias de previsão (1-8)
        timezone: Fuso horário

    Returns:
        Dict com dados marinhos ou None em caso de erro
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "wave_height",
            "wave_direction",
            "wave_period",
            "wind_wave_height",
            "swell_wave_height",
        ]),
        "daily": ",".join([
            "wave_height_max",
            "wave_period_max",
            "wind_wave_height_max",
            "swell_wave_height_max",
        ]),
        "timezone": timezone,
        "forecast_days": min(days, 8),
    }

    try:
        response = requests.get(MARINE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Erro ao buscar dados marinhos: {e}")
        return None


def _aggregate_daily(hourly_data: Dict, date_str: str) -> Dict[str, float]:
    """Agrega dados horários para um dia específico."""
    times = hourly_data.get("time", [])
    result = {}

    for key, values in hourly_data.items():
        if key == "time" or not values:
            continue

        # Filtrar valores do dia
        day_values = [
            v for t, v in zip(times, values)
            if t.startswith(date_str) and v is not None
        ]

        if day_values:
            if "max" in key or "gusts" in key:
                result[key] = max(day_values)
            elif "min" in key:
                result[key] = min(day_values)
            elif "precipitation" in key or "rain" in key:
                result[key] = sum(day_values)
            else:
                result[key] = sum(day_values) / len(day_values)

    return result


def get_weather_for_port(
    port_name: str,
    include_marine: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Obtém dados meteorológicos e marinhos para um porto brasileiro.

    Args:
        port_name: Nome do porto (ex: "SANTOS", "ITAQUI")
        include_marine: Se deve incluir dados marinhos

    Returns:
        Dict no formato compatível com o app de previsão de filas
    """
    # Normalizar nome do porto
    port_key = port_name.upper().strip()
    port_key = port_key.replace("PORTO DE ", "").replace("PORTO DO ", "")

    # Buscar coordenadas
    port_info = PORTS_COORDINATES.get(port_key)
    if not port_info:
        # Tentar match parcial
        for key, info in PORTS_COORDINATES.items():
            if port_key in key or key in port_key:
                port_info = info
                break

    if not port_info:
        logger.warning(f"Porto não encontrado: {port_name}")
        return None

    lat, lon = port_info["lat"], port_info["lon"]

    # Buscar dados meteorológicos
    weather = fetch_weather(lat, lon, days=7)
    if not weather:
        return None

    # Processar dados diários
    daily = weather.get("daily", {})
    today = datetime.now().strftime("%Y-%m-%d")

    # Encontrar índice de hoje
    dates = daily.get("time", [])
    today_idx = dates.index(today) if today in dates else 0

    # Extrair dados de hoje e últimos dias
    result = {
        "porto": port_info["name"],
        "latitude": lat,
        "longitude": lon,
        "data": today,
        "fonte": "Open-Meteo",
        # Variáveis compatíveis com o app
        "temp_media_dia": daily.get("temperature_2m_mean", [25])[today_idx] or 25,
        "temp_max_dia": daily.get("temperature_2m_max", [30])[today_idx] or 30,
        "temp_min_dia": daily.get("temperature_2m_min", [20])[today_idx] or 20,
        "precipitacao_dia": daily.get("precipitation_sum", [0])[today_idx] or 0,
        "vento_rajada_max_dia": daily.get("wind_gusts_10m_max", [5])[today_idx] or 5,
        "vento_velocidade_media": daily.get("wind_speed_10m_max", [3])[today_idx] * 0.6 if daily.get("wind_speed_10m_max") else 3,
        "umidade_media_dia": 70,  # Open-Meteo não fornece umidade diária agregada
    }

    # Calcular amplitude térmica
    result["amplitude_termica"] = result["temp_max_dia"] - result["temp_min_dia"]

    # Calcular chuva acumulada últimos 3 dias
    precip_values = daily.get("precipitation_sum", [0, 0, 0])
    start_idx = max(0, today_idx - 2)
    result["chuva_acumulada_ultimos_3dias"] = sum(
        precip_values[start_idx:today_idx + 1]
    )

    # Buscar dados marinhos
    if include_marine:
        marine = fetch_marine(lat, lon, days=3)
        if marine:
            marine_daily = marine.get("daily", {})
            if marine_daily:
                result["wave_height_max"] = marine_daily.get("wave_height_max", [0])[0] or 0
                result["wave_period_max"] = marine_daily.get("wave_period_max", [0])[0] or 0
                result["swell_wave_height_max"] = marine_daily.get("swell_wave_height_max", [0])[0] or 0
                # Feature derivada: ressaca (ondas > 2.5m)
                result["ressaca"] = 1 if result["wave_height_max"] > 2.5 else 0
        else:
            result["wave_height_max"] = 0
            result["wave_period_max"] = 0
            result["swell_wave_height_max"] = 0
            result["ressaca"] = 0

    return result


def get_weather_forecast(
    port_name: str,
    days: int = 7
) -> Optional[List[Dict[str, Any]]]:
    """
    Obtém previsão do tempo para os próximos dias.

    Args:
        port_name: Nome do porto
        days: Número de dias de previsão

    Returns:
        Lista de dicts com previsão diária
    """
    # Normalizar nome do porto
    port_key = port_name.upper().strip()
    port_key = port_key.replace("PORTO DE ", "").replace("PORTO DO ", "")

    port_info = PORTS_COORDINATES.get(port_key)
    if not port_info:
        for key, info in PORTS_COORDINATES.items():
            if port_key in key or key in port_key:
                port_info = info
                break

    if not port_info:
        return None

    lat, lon = port_info["lat"], port_info["lon"]

    # Buscar dados
    weather = fetch_weather(lat, lon, days=days)
    marine = fetch_marine(lat, lon, days=min(days, 8))

    if not weather:
        return None

    daily = weather.get("daily", {})
    dates = daily.get("time", [])

    # Processar dados marinhos
    marine_daily = marine.get("daily", {}) if marine else {}
    marine_dates = marine_daily.get("time", [])

    forecast = []
    for i, date in enumerate(dates):
        day_data = {
            "data": date,
            "porto": port_info["name"],
            "temp_max": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
            "temp_min": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
            "temp_media": daily.get("temperature_2m_mean", [])[i] if i < len(daily.get("temperature_2m_mean", [])) else None,
            "precipitacao": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else 0,
            "vento_max": daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None,
            "rajada_max": daily.get("wind_gusts_10m_max", [])[i] if i < len(daily.get("wind_gusts_10m_max", [])) else None,
        }

        # Adicionar dados marinhos se disponíveis
        if date in marine_dates:
            m_idx = marine_dates.index(date)
            day_data["wave_height_max"] = marine_daily.get("wave_height_max", [])[m_idx] if m_idx < len(marine_daily.get("wave_height_max", [])) else None
            day_data["wave_period_max"] = marine_daily.get("wave_period_max", [])[m_idx] if m_idx < len(marine_daily.get("wave_period_max", [])) else None
            day_data["ressaca"] = 1 if (day_data.get("wave_height_max") or 0) > 2.5 else 0

        forecast.append(day_data)

    return forecast


def fetch_weather_fallback(port_name: str) -> Optional[Dict[str, Any]]:
    """
    Função de fallback para substituir fetch_inmet_latest quando
    BigQuery não está disponível.

    Retorna dados no mesmo formato esperado pelo app.
    """
    data = get_weather_for_port(port_name, include_marine=True)
    if not data:
        # Retornar valores padrão
        return {
            "temp_media_dia": 25.0,
            "temp_max_dia": 30.0,
            "temp_min_dia": 20.0,
            "precipitacao_dia": 0.0,
            "vento_rajada_max_dia": 5.0,
            "vento_velocidade_media": 3.0,
            "umidade_media_dia": 70.0,
            "amplitude_termica": 10.0,
            "chuva_acumulada_ultimos_3dias": 0.0,
            "wave_height_max": 0.0,
            "ressaca": 0,
            "fonte": "default",
        }
    return data


# Teste rápido
if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DA API DE CLIMA")
    print("=" * 60)

    # Testar alguns portos
    test_ports = ["SANTOS", "ITAQUI", "PARANAGUA"]

    for port in test_ports:
        print(f"\n--- {port} ---")
        data = get_weather_for_port(port)
        if data:
            print(f"  Temperatura: {data['temp_min_dia']:.1f}°C - {data['temp_max_dia']:.1f}°C (média: {data['temp_media_dia']:.1f}°C)")
            print(f"  Precipitação: {data['precipitacao_dia']:.1f} mm")
            print(f"  Vento: {data['vento_velocidade_media']:.1f} m/s (rajada: {data['vento_rajada_max_dia']:.1f} m/s)")
            print(f"  Ondas: {data.get('wave_height_max', 'N/A')} m")
            print(f"  Ressaca: {'Sim' if data.get('ressaca') else 'Não'}")
        else:
            print("  ERRO: Dados não disponíveis")

    # Testar previsão
    print("\n" + "=" * 60)
    print("PREVISÃO 7 DIAS - SANTOS")
    print("=" * 60)
    forecast = get_weather_forecast("SANTOS", days=7)
    if forecast:
        for day in forecast:
            print(f"{day['data']}: {day.get('temp_min', 'N/A')}°C - {day.get('temp_max', 'N/A')}°C, chuva: {day.get('precipitacao', 0):.1f}mm, ondas: {day.get('wave_height_max', 'N/A')}m")
