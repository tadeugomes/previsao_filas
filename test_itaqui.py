#!/usr/bin/env python3
"""
Teste otimizado: Coletar dados históricos do Porto do Itaqui.

Estratégia para economizar créditos:
1. Buscar navios atuais no porto (1 crédito)
2. Selecionar apenas 5 navios
3. Buscar 30 dias de histórico de cada (5 × 30 = 150 créditos)
4. Detectar atracações
5. Calcular estatísticas

Total estimado: ~151 créditos (de 20.000 disponíveis)
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "8f4d73c7-0455-4afd-9032-4ad4878ec5b0"
BASE_URL = "https://api.datalastic.com/api/v0"

# Porto do Itaqui
ITAQUI = {
    "lat": -2.5734,
    "lon": -44.3667,
    "radius": 5,  # milhas náuticas
    "bounds": {
        "lat_min": -2.65,
        "lat_max": -2.50,
        "lon_min": -44.45,
        "lon_max": -44.28,
    },
}

credits_used = 0


def get_vessels_in_port():
    """Busca navios atuais no porto."""
    global credits_used

    url = f"{BASE_URL}/vessel_inradius"
    params = {
        "api-key": API_KEY,
        "lat": ITAQUI["lat"],
        "lon": ITAQUI["lon"],
        "radius": ITAQUI["radius"],
    }

    print("📡 Buscando navios atuais no Porto do Itaqui...")

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    vessels = data["data"]["vessels"]

    credits_used += 1  # 1 crédito

    print(f"✅ Encontrados {len(vessels)} navios")
    print(f"💳 Créditos usados: {credits_used}")

    return vessels


def get_vessel_history(imo, days=30):
    """Busca histórico de um navio."""
    global credits_used

    url = f"{BASE_URL}/vessel_history"
    params = {"api-key": API_KEY, "imo": imo, "days": days}

    response = requests.get(url, params=params, timeout=30)

    if response.status_code != 200:
        print(f"  ⚠️  Erro ao buscar IMO {imo}: {response.status_code}")
        return None

    data = response.json()
    credits_used += days  # 1 crédito por dia

    return data["data"]


def detect_berthing(positions, bounds):
    """Detecta atracação a partir de posições."""

    if not positions:
        return None

    for pos in reversed(positions):  # Do mais antigo ao mais recente
        lat = pos.get("lat")
        lon = pos.get("lon")
        speed = pos.get("speed", 0)
        timestamp = pos.get("last_position_UTC")

        if lat is None or lon is None:
            continue

        # Critérios de atracação:
        # 1. Dentro do porto
        # 2. Velocidade < 1 knot
        in_port = (
            bounds["lat_min"] <= lat <= bounds["lat_max"]
            and bounds["lon_min"] <= lon <= bounds["lon_max"]
        )

        stopped = speed < 1.0

        if in_port and stopped:
            return {
                "timestamp": timestamp,
                "lat": lat,
                "lon": lon,
                "speed": speed,
            }

    return None


def main():
    """Função principal."""
    global credits_used

    print("=" * 70)
    print("TESTE: COLETA DE DADOS - PORTO DO ITAQUI")
    print("=" * 70)
    print()

    # Passo 1: Navios atuais
    vessels = get_vessels_in_port()

    # Filtra apenas navios com IMO (ignora embarcações pequenas)
    vessels_with_imo = [v for v in vessels if v.get("imo")]

    print(f"\n📊 Navios com IMO: {len(vessels_with_imo)}")

    # Seleciona apenas 5 para teste
    sample_size = 5
    sample_vessels = vessels_with_imo[:sample_size]

    print(f"🎯 Amostra selecionada: {sample_size} navios")
    print()

    # Passo 2: Buscar histórico
    results = []

    for i, vessel in enumerate(sample_vessels, 1):
        imo = vessel["imo"]
        name = vessel["name"]

        print(f"\n[{i}/{sample_size}] {name} (IMO: {imo})")
        print(f"  Buscando 30 dias de histórico...")

        history = get_vessel_history(imo, days=30)

        if not history:
            continue

        positions = history.get("positions", [])
        print(f"  ✅ {len(positions)} posições retornadas")

        # Detecta atracação
        berthing = detect_berthing(positions, ITAQUI["bounds"])

        if berthing:
            print(f"  🚢 Atracação detectada: {berthing['timestamp']}")
            print(f"     Posição: {berthing['lat']:.4f}, {berthing['lon']:.4f}")
            print(f"     Velocidade: {berthing['speed']} knots")

            results.append(
                {
                    "imo": imo,
                    "name": name,
                    "berthing_time": berthing["timestamp"],
                    "num_positions": len(positions),
                }
            )
        else:
            print(f"  ⚠️  Atracação não detectada (pode estar em movimento)")

        print(f"  💳 Créditos acumulados: {credits_used}")

    # Passo 3: Resultados
    print("\n" + "=" * 70)
    print("RESULTADOS")
    print("=" * 70)
    print(f"\n📊 Navios processados: {sample_size}")
    print(f"✅ Atracações detectadas: {len(results)}")
    print(f"💳 Créditos totais usados: {credits_used} / 20.000")
    print(f"💰 Créditos restantes: {20000 - credits_used:,}")

    if results:
        print("\n📋 Detalhes das atracações:")
        df = pd.DataFrame(results)
        print(df.to_string(index=False))

        # Salva resultados
        df.to_parquet("data/ais/itaqui_test_results.parquet")
        print(f"\n💾 Resultados salvos: data/ais/itaqui_test_results.parquet")

    print("\n" + "=" * 70)
    print("ANÁLISE DE VIABILIDADE")
    print("=" * 70)

    print(f"\n📈 Estimativa para coleta completa:")
    print(f"   Navios ativos no Itaqui: {len(vessels_with_imo)}")
    print(f"   Custo por navio (30 dias): 30 créditos")
    print(f"   Custo total estimado: {len(vessels_with_imo) * 30:,} créditos")

    if len(vessels_with_imo) * 30 < 20000:
        print(f"   ✅ VIÁVEL com créditos disponíveis!")
    else:
        print(f"   ⚠️  Excede créditos. Considerar período menor ou amostragem.")

    print("\n💡 Próximos passos:")
    print("   1. Se resultados satisfatórios, processar mais navios")
    print("   2. Ou estender período histórico (60-90 dias)")
    print("   3. Repetir para outros portos (Santos, Paranaguá, etc)")
    print("=" * 70)


if __name__ == "__main__":
    main()
