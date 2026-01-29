#!/usr/bin/env python3
"""
Maximizar coleta de dados AIS com créditos restantes.

Estratégia:
1. Estender período dos navios já coletados (60 → 120 dias)
2. Adicionar porto Vitória (5º maior do Brasil)
3. Se sobrar, adicionar Suape

Créditos disponíveis: 15.797
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import time

API_KEY = "8f4d73c7-0455-4afd-9032-4ad4878ec5b0"
BASE_URL = "https://api.datalastic.com/api/v0"

PORTOS = {
    "Santos": {
        "lat": -23.9511,
        "lon": -46.3344,
        "radius": 8.1,
        "bounds": {"lat_min": -24.05, "lat_max": -23.85, "lon_min": -46.45, "lon_max": -46.22},
    },
    "Paranaguá": {
        "lat": -25.5163,
        "lon": -48.5133,
        "radius": 5.4,
        "bounds": {"lat_min": -25.60, "lat_max": -25.43, "lon_min": -48.60, "lon_max": -48.42},
    },
    "Rio Grande": {
        "lat": -32.0350,
        "lon": -52.0993,
        "radius": 5.4,
        "bounds": {"lat_min": -32.15, "lat_max": -31.92, "lon_min": -52.20, "lon_max": -52.00},
    },
    "Vitória": {
        "lat": -20.3204,
        "lon": -40.3365,
        "radius": 5.4,
        "bounds": {"lat_min": -20.40, "lat_max": -20.24, "lon_min": -40.43, "lon_max": -40.24},
    },
    "Suape": {
        "lat": -8.3584,
        "lon": -34.9530,
        "radius": 5.4,
        "bounds": {"lat_min": -8.45, "lat_max": -8.27, "lon_min": -35.05, "lon_max": -34.86},
    },
}

RELEVANT_TYPES = ["Cargo", "Tanker"]

credits_used = 0
credits_start = 15797


def is_relevant_vessel(vessel_type):
    if not vessel_type:
        return False
    vessel_type_lower = vessel_type.lower()
    return any(rel_type.lower() in vessel_type_lower for rel_type in RELEVANT_TYPES)


def get_vessels_in_port(porto_name):
    global credits_used
    porto = PORTOS[porto_name]

    url = f"{BASE_URL}/vessel_inradius"
    params = {
        "api-key": API_KEY,
        "lat": porto["lat"],
        "lon": porto["lon"],
        "radius": porto["radius"],
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    vessels = data["data"]["vessels"]
    credits_used += 1

    return vessels


def get_vessel_history(imo, days):
    global credits_used

    url = f"{BASE_URL}/vessel_history"
    params = {"api-key": API_KEY, "imo": imo, "days": days}

    try:
        response = requests.get(url, params=params, timeout=60)
        if response.status_code != 200:
            return None

        data = response.json()
        credits_used += days
        return data["data"]

    except Exception as e:
        print(f"    ⚠️  Erro: {e}")
        return None


def detect_all_berthings(positions, bounds):
    if not positions:
        return []

    df = pd.DataFrame(positions)
    df["timestamp_dt"] = pd.to_datetime(df["last_position_UTC"], errors="coerce")
    df = df.sort_values("timestamp_dt")

    df["in_port"] = (
        (df["lat"] >= bounds["lat_min"]) & (df["lat"] <= bounds["lat_max"]) &
        (df["lon"] >= bounds["lon_min"]) & (df["lon"] <= bounds["lon_max"])
    )
    df["stopped"] = df["speed"] < 1.0
    df["berthed"] = df["in_port"] & df["stopped"]
    df["berthing_start"] = (df["berthed"] == True) & (df["berthed"].shift(1) == False)

    berthing_events = df[df["berthing_start"] == True]

    events = []
    for idx, row in berthing_events.iterrows():
        events.append({
            "berthing_time": row["last_position_UTC"],
            "lat": row["lat"],
            "lon": row["lon"],
            "speed": row["speed"],
        })

    return events


def calculate_waiting_time(positions, berthing_time):
    df = pd.DataFrame(positions)
    df["timestamp_dt"] = pd.to_datetime(df["last_position_UTC"], errors="coerce")
    df = df.sort_values("timestamp_dt")

    berthing_dt = pd.to_datetime(berthing_time)
    df_before = df[df["timestamp_dt"] <= berthing_dt]

    if df_before.empty:
        return None

    first_in_area = df_before.iloc[0]
    arrival_time = first_in_area["timestamp_dt"]
    waiting_time = (berthing_dt - arrival_time).total_seconds() / 3600

    if waiting_time < 0 or waiting_time > 720:
        return None

    return waiting_time


def extend_existing_ports(days_extension=60):
    """Estende período dos navios já coletados."""
    global credits_used

    print("\n" + "=" * 70)
    print("FASE 1: ESTENDER PERÍODO DOS PORTOS EXISTENTES")
    print("=" * 70)
    print(f"Objetivo: Coletar mais {days_extension} dias dos navios já conhecidos")
    print()

    # Carrega dados existentes
    df_existing = pd.read_parquet("data/ais/main_ports_60d.parquet")

    # Navios únicos por porto
    ports_to_extend = {}
    for porto in ["Santos", "Paranaguá", "Rio Grande"]:
        vessels = df_existing[df_existing["porto"] == porto]["imo"].unique()
        ports_to_extend[porto] = list(vessels)

    all_berthings = []

    for porto_name, vessel_imos in ports_to_extend.items():
        print(f"\n📊 {porto_name}: {len(vessel_imos)} navios × {days_extension} dias = {len(vessel_imos) * days_extension:,} créditos")

        for i, imo in enumerate(vessel_imos, 1):
            vessel_name = df_existing[df_existing["imo"] == imo]["name"].iloc[0]
            vessel_type = df_existing[df_existing["imo"] == imo]["type"].iloc[0]

            print(f"  [{i}/{len(vessel_imos)}] {vessel_name} ({vessel_type})", end="")

            history = get_vessel_history(imo, days=days_extension)

            if not history:
                print(f" ❌")
                continue

            positions = history.get("positions", [])
            print(f" → {len(positions)} pos", end="")

            berthings = detect_all_berthings(positions, PORTOS[porto_name]["bounds"])

            if berthings:
                print(f" → {len(berthings)} atracação(ões)")

                for berthing in berthings:
                    waiting_time = calculate_waiting_time(positions, berthing["berthing_time"])

                    all_berthings.append({
                        "imo": imo,
                        "name": vessel_name,
                        "type": vessel_type,
                        "porto": porto_name,
                        "berthing_time": berthing["berthing_time"],
                        "lat": berthing["lat"],
                        "lon": berthing["lon"],
                        "waiting_time_hours": waiting_time,
                        "num_positions": len(positions),
                    })
            else:
                print(f" → 0")

            if i % 10 == 0:
                print(f"    💳 Créditos: {credits_used:,} | Restantes: {credits_start - credits_used:,}")

        print(f"  ✅ {porto_name} concluído")

    print(f"\n📊 Total estendido: {len(all_berthings)} novas atracações")
    print(f"💳 Créditos usados: {credits_used:,} / {credits_start:,}")

    return all_berthings


def collect_new_port(porto_name, days=90):
    """Coleta novo porto."""
    global credits_used

    print(f"\n" + "=" * 70)
    print(f"COLETANDO NOVO PORTO: {porto_name.upper()}")
    print("=" * 70)

    print(f"\n📡 Buscando navios atuais...")
    vessels = get_vessels_in_port(porto_name)

    relevant_vessels = [v for v in vessels if v.get("imo") and is_relevant_vessel(v.get("type"))]

    print(f"✅ Total: {len(vessels)}")
    print(f"🎯 Cargo/Tanker: {len(relevant_vessels)}")
    print(f"💳 Estimativa: {len(relevant_vessels) * days:,} créditos")

    if not relevant_vessels:
        return []

    all_berthings = []

    for i, vessel in enumerate(relevant_vessels, 1):
        imo = vessel["imo"]
        name = vessel["name"]
        vtype = vessel.get("type", "Unknown")

        print(f"[{i}/{len(relevant_vessels)}] {name} ({vtype})", end="")

        history = get_vessel_history(imo, days=days)

        if not history:
            print(f" ❌")
            continue

        positions = history.get("positions", [])
        print(f" → {len(positions)} pos", end="")

        berthings = detect_all_berthings(positions, PORTOS[porto_name]["bounds"])

        if berthings:
            print(f" → {len(berthings)} atracação(ões)")

            for berthing in berthings:
                waiting_time = calculate_waiting_time(positions, berthing["berthing_time"])

                all_berthings.append({
                    "imo": imo,
                    "name": name,
                    "type": vtype,
                    "porto": porto_name,
                    "berthing_time": berthing["berthing_time"],
                    "lat": berthing["lat"],
                    "lon": berthing["lon"],
                    "waiting_time_hours": waiting_time,
                    "num_positions": len(positions),
                })
        else:
            print(f" → 0")

        if i % 10 == 0:
            print(f"  💳 Créditos: {credits_used:,} | Restantes: {credits_start - credits_used:,}")

    print(f"\n✅ {porto_name} concluído: {len(all_berthings)} atracações")
    return all_berthings


def main():
    global credits_used

    print("=" * 70)
    print("MAXIMIZAR COLETA DE DADOS AIS")
    print("=" * 70)
    print(f"💳 Créditos disponíveis: {credits_start:,}")
    print()

    all_results = []

    # FASE 1: Estender portos existentes (60 dias adicionais)
    print("📅 Fase 1: Estender Santos, Paranaguá, Rio Grande (60 → 120 dias)")
    extended = extend_existing_ports(days_extension=60)
    all_results.extend(extended)

    print(f"\n💳 Após Fase 1: {credits_used:,} usados | {credits_start - credits_used:,} restantes")

    # FASE 2: Adicionar Vitória
    if credits_start - credits_used > 2000:
        print(f"\n📅 Fase 2: Adicionar Porto de Vitória (90 dias)")
        vitoria = collect_new_port("Vitória", days=90)
        all_results.extend(vitoria)

        print(f"\n💳 Após Fase 2: {credits_used:,} usados | {credits_start - credits_used:,} restantes")

    # FASE 3: Adicionar Suape se sobrar
    if credits_start - credits_used > 1500:
        print(f"\n📅 Fase 3: Adicionar Porto de Suape (90 dias)")
        suape = collect_new_port("Suape", days=90)
        all_results.extend(suape)

        print(f"\n💳 Após Fase 3: {credits_used:,} usados | {credits_start - credits_used:,} restantes")

    # Consolidar tudo
    print("\n" + "=" * 70)
    print("RESULTADOS FINAIS")
    print("=" * 70)

    if not all_results:
        print("❌ Nenhum novo dado coletado")
        return

    df_new = pd.DataFrame(all_results)

    # Combina com dados existentes
    df_existing = pd.read_parquet("data/ais/all_ports_consolidated.parquet")
    df_all = pd.concat([df_existing, df_new], ignore_index=True)

    print(f"\n📊 Dados TOTAIS (antigos + novos):")
    print(f"   Atracações: {len(df_all)} ({len(df_existing)} antigas + {len(df_new)} novas)")
    print(f"   Navios únicos: {df_all['imo'].nunique()}")
    print(f"   Portos: {df_all['porto'].nunique()}")

    print(f"\n🚢 Por porto:")
    for porto, count in df_all['porto'].value_counts().items():
        print(f"   {porto}: {count}")

    valid = df_all["waiting_time_hours"].dropna()
    print(f"\n⏱️  Tempo de Espera:")
    print(f"   Válidos: {len(valid)}/{len(df_all)} ({len(valid)/len(df_all)*100:.1f}%)")
    print(f"   Média: {valid.mean():.1f}h ({valid.mean()/24:.1f} dias)")
    print(f"   Mediana: {valid.median():.1f}h ({valid.median()/24:.1f} dias)")

    print(f"\n💳 Créditos:")
    print(f"   Usados nesta coleta: {credits_used:,}")
    print(f"   Total acumulado: {4203 + credits_used:,} / 20.000")
    print(f"   Restantes: {20000 - 4203 - credits_used:,}")

    # Salvar
    output_file = Path("data/ais/all_ports_extended.parquet")
    df_all.to_parquet(output_file)

    csv_file = Path("data/ais/all_ports_extended.csv")
    df_all.to_csv(csv_file, index=False)

    print(f"\n💾 Dados salvos:")
    print(f"   {output_file} ({output_file.stat().st_size / 1024:.1f} KB)")
    print(f"   {csv_file} ({csv_file.stat().st_size / 1024:.1f} KB)")

    print("\n" + "=" * 70)
    print("✅ COLETA MAXIMIZADA CONCLUÍDA!")
    print("=" * 70)


if __name__ == "__main__":
    main()
