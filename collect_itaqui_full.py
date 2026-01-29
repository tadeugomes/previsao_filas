#!/usr/bin/env python3
"""
Coleta COMPLETA de dados históricos do Porto do Itaqui.

Estratégia:
- Todos os 34 navios com IMO
- 90 dias de histórico (3 meses)
- Detecção de atracações
- Cálculo de tempo de espera (quando possível)

Estimativa de créditos: 34 × 90 = 3.060 créditos
"""

import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

API_KEY = "8f4d73c7-0455-4afd-9032-4ad4878ec5b0"
BASE_URL = "https://api.datalastic.com/api/v0"

# Porto do Itaqui
ITAQUI = {
    "name": "Itaqui",
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

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    vessels = data["data"]["vessels"]

    credits_used += 1

    return vessels


def get_vessel_history(imo, days=90):
    """Busca histórico de um navio."""
    global credits_used

    url = f"{BASE_URL}/vessel_history"
    params = {"api-key": API_KEY, "imo": imo, "days": days}

    response = requests.get(url, params=params, timeout=60)

    if response.status_code != 200:
        return None

    data = response.json()
    credits_used += days

    return data["data"]


def detect_all_berthings(positions, bounds):
    """
    Detecta TODAS as atracações no período (não apenas a primeira).

    Retorna lista de eventos de atracação.
    """
    if not positions:
        return []

    df = pd.DataFrame(positions)

    # Ordena por timestamp
    df["timestamp_dt"] = pd.to_datetime(df["last_position_UTC"], errors="coerce")
    df = df.sort_values("timestamp_dt")

    # Marca posições dentro do porto e paradas
    df["in_port"] = (
        (df["lat"] >= bounds["lat_min"])
        & (df["lat"] <= bounds["lat_max"])
        & (df["lon"] >= bounds["lon_min"])
        & (df["lon"] <= bounds["lon_max"])
    )

    df["stopped"] = df["speed"] < 1.0
    df["berthed"] = df["in_port"] & df["stopped"]

    # Detecta mudanças de estado (início de atracação)
    df["berthing_start"] = (df["berthed"] == True) & (df["berthed"].shift(1) == False)

    # Eventos de atracação
    berthing_events = df[df["berthing_start"] == True]

    events = []
    for idx, row in berthing_events.iterrows():
        events.append(
            {
                "berthing_time": row["last_position_UTC"],
                "lat": row["lat"],
                "lon": row["lon"],
                "speed": row["speed"],
            }
        )

    return events


def calculate_waiting_time(positions, berthing_time):
    """
    Tenta calcular tempo de espera.

    Estratégia:
    - Encontra quando navio chegou na área do porto (primeira entrada)
    - Calcula delta até atracação
    """
    df = pd.DataFrame(positions)
    df["timestamp_dt"] = pd.to_datetime(df["last_position_UTC"], errors="coerce")
    df = df.sort_values("timestamp_dt")

    # Filtra posições antes da atracação
    berthing_dt = pd.to_datetime(berthing_time)
    df_before = df[df["timestamp_dt"] <= berthing_dt]

    if df_before.empty:
        return None

    # Primeira posição na área portuária antes da atracação
    first_in_area = df_before.iloc[0]
    arrival_time = first_in_area["timestamp_dt"]

    # Tempo de espera
    waiting_time = (berthing_dt - arrival_time).total_seconds() / 3600  # horas

    # Valida (0-720h = 0-30 dias)
    if waiting_time < 0 or waiting_time > 720:
        return None

    return waiting_time


def main():
    """Função principal."""
    global credits_used

    print("=" * 70)
    print("COLETA COMPLETA: PORTO DO ITAQUI (90 DIAS)")
    print("=" * 70)
    print()

    # Passo 1: Navios atuais
    print("📡 Buscando navios atuais...")
    vessels = get_vessels_in_port()

    vessels_with_imo = [v for v in vessels if v.get("imo")]

    print(f"✅ Total de navios: {len(vessels)}")
    print(f"📊 Navios com IMO: {len(vessels_with_imo)}")
    print(f"🎯 Processando: {len(vessels_with_imo)} navios × 90 dias")
    print(f"💳 Estimativa: {len(vessels_with_imo) * 90:,} créditos")
    print()

    # Passo 2: Coletar históricos
    all_berthings = []
    processed = 0
    errors = 0

    for i, vessel in enumerate(vessels_with_imo, 1):
        imo = vessel["imo"]
        name = vessel["name"]
        vessel_type = vessel.get("type", "Unknown")

        print(f"[{i}/{len(vessels_with_imo)}] {name} ({vessel_type})")
        print(f"  IMO: {imo}")

        # Busca histórico
        history = get_vessel_history(imo, days=90)

        if not history:
            print(f"  ❌ Erro ao buscar histórico")
            errors += 1
            continue

        positions = history.get("positions", [])
        print(f"  ✅ {len(positions)} posições")

        # Detecta todas as atracações
        berthings = detect_all_berthings(positions, ITAQUI["bounds"])

        if berthings:
            print(f"  🚢 {len(berthings)} atracação(ões) detectada(s)")

            for berthing in berthings:
                # Tenta calcular tempo de espera
                waiting_time = calculate_waiting_time(positions, berthing["berthing_time"])

                all_berthings.append(
                    {
                        "imo": imo,
                        "name": name,
                        "type": vessel_type,
                        "porto": "Itaqui",
                        "berthing_time": berthing["berthing_time"],
                        "lat": berthing["lat"],
                        "lon": berthing["lon"],
                        "waiting_time_hours": waiting_time,
                        "num_positions": len(positions),
                    }
                )

                if waiting_time is not None:
                    print(f"     └─ {berthing['berthing_time']}: ~{waiting_time:.1f}h de espera")
                else:
                    print(f"     └─ {berthing['berthing_time']}: tempo de espera N/A")
        else:
            print(f"  ⚠️  Nenhuma atracação detectada (navio em trânsito?)")

        processed += 1

        # Progress
        if i % 5 == 0:
            print(f"\n  💳 Créditos usados: {credits_used:,} / 20.000")
            print(f"  📊 Progresso: {processed}/{len(vessels_with_imo)} navios\n")

    # Passo 3: Salvar resultados
    print("\n" + "=" * 70)
    print("RESULTADOS FINAIS")
    print("=" * 70)

    df_berthings = pd.DataFrame(all_berthings)

    print(f"\n📊 Estatísticas:")
    print(f"   Navios processados: {processed}")
    print(f"   Atracações detectadas: {len(df_berthings)}")
    print(f"   Erros: {errors}")
    print(f"   💳 Créditos totais: {credits_used:,} / 20.000")
    print(f"   💰 Créditos restantes: {20000 - credits_used:,}")

    if not df_berthings.empty:
        # Estatísticas de tempo de espera
        valid_waiting = df_berthings["waiting_time_hours"].dropna()

        if not valid_waiting.empty:
            print(f"\n⏱️  Tempo de Espera (horas):")
            print(f"   Registros válidos: {len(valid_waiting)}/{len(df_berthings)}")
            print(f"   Média: {valid_waiting.mean():.1f}h")
            print(f"   Mediana: {valid_waiting.median():.1f}h")
            print(f"   Mín: {valid_waiting.min():.1f}h")
            print(f"   Máx: {valid_waiting.max():.1f}h")
            print(f"   Desvio padrão: {valid_waiting.std():.1f}h")

        # Por tipo de navio
        print(f"\n🚢 Atracações por tipo de navio:")
        type_counts = df_berthings["type"].value_counts()
        for vtype, count in type_counts.items():
            print(f"   {vtype}: {count}")

        # Salva
        output_dir = Path("data/ais")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "itaqui_berthings_90d.parquet"
        df_berthings.to_parquet(output_file)

        print(f"\n💾 Dados salvos: {output_file}")
        print(f"   Tamanho: {output_file.stat().st_size / 1024:.1f} KB")

        # CSV para análise manual
        csv_file = output_dir / "itaqui_berthings_90d.csv"
        df_berthings.to_csv(csv_file, index=False)
        print(f"💾 CSV salvo: {csv_file}")

        # Amostra
        print(f"\n📋 Amostra dos dados (5 primeiros):")
        print(df_berthings.head().to_string(index=False))

    print("\n" + "=" * 70)
    print("PRÓXIMOS PASSOS")
    print("=" * 70)
    print(f"\n✅ Dados do Porto do Itaqui coletados!")
    print(f"💳 Créditos restantes: {20000 - credits_used:,}")
    print(f"\n💡 Sugestões:")
    print(f"   1. Analisar dados coletados (CSV/Parquet)")
    print(f"   2. Validar tempos de espera calculados")
    print(f"   3. Se satisfatório, coletar outros portos:")
    print(f"      - Santos (~300 navios × 90d = 27.000 créditos) ⚠️ Excede limite")
    print(f"      - Paranaguá (~150 navios × 90d = 13.500 créditos) ✅ Viável")
    print(f"      - Rio Grande (~100 navios × 90d = 9.000 créditos) ✅ Viável")
    print(f"   4. Ou reduzir período (30-60 dias) para coletar mais portos")
    print("=" * 70)


if __name__ == "__main__":
    main()
