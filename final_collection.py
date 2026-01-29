#!/usr/bin/env python3
"""
Coleta final: Usar TODOS os créditos restantes (10.785).

Estratégia:
1. Estender ainda mais os navios principais (120 → 180 dias)
2. Adicionar portos menores (Salvador, Belém, etc)
3. Continuar até esgotar créditos
"""

import requests
import pandas as pd
from pathlib import Path

API_KEY = "8f4d73c7-0455-4afd-9032-4ad4878ec5b0"
BASE_URL = "https://api.datalastic.com/api/v0"

PORTOS = {
    "Santos": {
        "lat": -23.9511, "lon": -46.3344, "radius": 8.1,
        "bounds": {"lat_min": -24.05, "lat_max": -23.85, "lon_min": -46.45, "lon_max": -46.22},
    },
    "Paranaguá": {
        "lat": -25.5163, "lon": -48.5133, "radius": 5.4,
        "bounds": {"lat_min": -25.60, "lat_max": -25.43, "lon_min": -48.60, "lon_max": -48.42},
    },
    "Rio Grande": {
        "lat": -32.0350, "lon": -52.0993, "radius": 5.4,
        "bounds": {"lat_min": -32.15, "lat_max": -31.92, "lon_min": -52.20, "lon_max": -52.00},
    },
    "Itaqui": {
        "lat": -2.5734, "lon": -44.3667, "radius": 4.3,
        "bounds": {"lat_min": -2.65, "lat_max": -2.50, "lon_min": -44.45, "lon_max": -44.28},
    },
    "Vitória": {
        "lat": -20.3204, "lon": -40.3365, "radius": 5.4,
        "bounds": {"lat_min": -20.40, "lat_max": -20.24, "lon_min": -40.43, "lon_max": -40.24},
    },
    "Suape": {
        "lat": -8.3584, "lon": -34.9530, "radius": 5.4,
        "bounds": {"lat_min": -8.45, "lat_max": -8.27, "lon_min": -35.05, "lon_max": -34.86},
    },
    "Salvador": {
        "lat": -12.9714, "lon": -38.5014, "radius": 5.4,
        "bounds": {"lat_min": -13.05, "lat_max": -12.89, "lon_min": -38.58, "lon_max": -38.42},
    },
    "Itajaí": {
        "lat": -26.9094, "lon": -48.6611, "radius": 5.4,
        "bounds": {"lat_min": -27.00, "lat_max": -26.82, "lon_min": -48.75, "lon_max": -48.57},
    },
}

RELEVANT_TYPES = ["Cargo", "Tanker"]
credits_used = 0
credits_start = 10785


def is_relevant_vessel(vessel_type):
    if not vessel_type:
        return False
    return any(rel.lower() in vessel_type.lower() for rel in RELEVANT_TYPES)


def get_vessels_in_port(porto_name):
    global credits_used
    url = f"{BASE_URL}/vessel_inradius"
    params = {
        "api-key": API_KEY,
        "lat": PORTOS[porto_name]["lat"],
        "lon": PORTOS[porto_name]["lon"],
        "radius": PORTOS[porto_name]["radius"],
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
    except:
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

    events = []
    for idx, row in df[df["berthing_start"] == True].iterrows():
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

    arrival_time = df_before.iloc[0]["timestamp_dt"]
    waiting_time = (berthing_dt - arrival_time).total_seconds() / 3600

    if waiting_time < 0 or waiting_time > 720:
        return None
    return waiting_time


def extend_top_vessels(top_n=30, days_extension=60):
    """Estende os navios com mais atracações detectadas."""
    global credits_used

    print("\n" + "=" * 70)
    print(f"ESTENDER TOP {top_n} NAVIOS MAIS ATIVOS (+ {days_extension} dias)")
    print("=" * 70)

    df_existing = pd.read_parquet("data/ais/all_ports_extended.parquet")

    # Identifica navios mais ativos
    vessel_activity = df_existing.groupby(["imo", "name", "type", "porto"]).size().reset_index(name="count")
    vessel_activity = vessel_activity.sort_values("count", ascending=False).head(top_n)

    print(f"\n📊 Top {top_n} navios mais ativos:")
    print(f"   Créditos estimados: {top_n * days_extension:,}")
    print()

    all_berthings = []

    for i, row in vessel_activity.iterrows():
        imo = row["imo"]
        name = row["name"]
        vtype = row["type"]
        porto = row["porto"]
        count = row["count"]

        print(f"[{i+1}/{top_n}] {name} ({vtype}) - {porto} ({count} atracações)", end="")

        history = get_vessel_history(imo, days=days_extension)

        if not history:
            print(f" ❌")
            continue

        positions = history.get("positions", [])
        print(f" → {len(positions)} pos", end="")

        berthings = detect_all_berthings(positions, PORTOS[porto]["bounds"])

        if berthings:
            print(f" → {len(berthings)} novas")

            for berthing in berthings:
                waiting_time = calculate_waiting_time(positions, berthing["berthing_time"])

                all_berthings.append({
                    "imo": imo,
                    "name": name,
                    "type": vtype,
                    "porto": porto,
                    "berthing_time": berthing["berthing_time"],
                    "lat": berthing["lat"],
                    "lon": berthing["lon"],
                    "waiting_time_hours": waiting_time,
                    "num_positions": len(positions),
                })
        else:
            print(f" → 0")

        if (i+1) % 10 == 0:
            print(f"    💳 {credits_used:,} usados | {credits_start - credits_used:,} restantes")

    print(f"\n✅ Total: {len(all_berthings)} novas atracações")
    print(f"💳 Créditos: {credits_used:,} / {credits_start:,}")

    return all_berthings


def collect_new_ports():
    """Coleta portos adicionais."""
    global credits_used

    all_berthings = []

    for porto_name in ["Salvador", "Itajaí"]:
        if credits_start - credits_used < 500:
            print(f"\n⚠️  Créditos insuficientes para {porto_name}")
            break

        print(f"\n" + "=" * 70)
        print(f"COLETANDO: {porto_name.upper()} (90 dias)")
        print("=" * 70)

        try:
            vessels = get_vessels_in_port(porto_name)
            relevant = [v for v in vessels if v.get("imo") and is_relevant_vessel(v.get("type"))]

            print(f"✅ Total: {len(vessels)} | Cargo/Tanker: {len(relevant)}")

            if not relevant:
                continue

            for i, vessel in enumerate(relevant, 1):
                if credits_start - credits_used < 90:
                    print(f"\n⚠️  Parando em {i-1}/{len(relevant)} - créditos acabando")
                    break

                imo = vessel["imo"]
                name = vessel["name"]
                vtype = vessel.get("type", "Unknown")

                print(f"[{i}/{len(relevant)}] {name}", end="")

                history = get_vessel_history(imo, days=90)

                if not history:
                    print(f" ❌")
                    continue

                positions = history.get("positions", [])
                print(f" → {len(positions)} pos", end="")

                berthings = detect_all_berthings(positions, PORTOS[porto_name]["bounds"])

                if berthings:
                    print(f" → {len(berthings)}")

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

        except Exception as e:
            print(f"\n❌ Erro em {porto_name}: {e}")
            continue

    return all_berthings


def main():
    global credits_used

    print("=" * 70)
    print("COLETA FINAL - USAR TODOS OS CRÉDITOS RESTANTES")
    print("=" * 70)
    print(f"💳 Créditos disponíveis: {credits_start:,}")
    print()

    all_results = []

    # Fase 1: Estender top navios
    if credits_start - credits_used > 2000:
        extended = extend_top_vessels(top_n=30, days_extension=60)
        all_results.extend(extended)

        print(f"\n💳 Após extensão: {credits_used:,} | Restantes: {credits_start - credits_used:,}")

    # Fase 2: Novos portos
    if credits_start - credits_used > 1000:
        new_ports = collect_new_ports()
        all_results.extend(new_ports)

        print(f"\n💳 Após novos portos: {credits_used:,} | Restantes: {credits_start - credits_used:,}")

    # Consolidar TUDO
    print("\n" + "=" * 70)
    print("DATASET FINAL - MÁXIMO POSSÍVEL")
    print("=" * 70)

    if not all_results:
        print("❌ Nenhum novo dado")
        return

    df_new = pd.DataFrame(all_results)
    df_existing = pd.read_parquet("data/ais/all_ports_extended.parquet")
    df_final = pd.concat([df_existing, df_new], ignore_index=True)

    print(f"\n📊 DATASET COMPLETO:")
    print(f"   Atracações: {len(df_final)} ({len(df_existing)} anteriores + {len(df_new)} novas)")
    print(f"   Navios únicos: {df_final['imo'].nunique()}")
    print(f"   Portos: {df_final['porto'].nunique()}")

    print(f"\n🚢 Por porto:")
    for porto, count in df_final['porto'].value_counts().items():
        print(f"   {porto}: {count}")

    valid = df_final["waiting_time_hours"].dropna()
    print(f"\n⏱️  Tempo de Espera:")
    print(f"   Válidos: {len(valid)}/{len(df_final)} ({len(valid)/len(df_final)*100:.1f}%)")
    print(f"   Média: {valid.mean():.1f}h ({valid.mean()/24:.1f} dias)")

    print(f"\n💳 CRÉDITOS FINAIS:")
    print(f"   Usados nesta coleta: {credits_used:,}")
    print(f"   Total GERAL: {9215 + credits_used:,} / 20.000")
    print(f"   Restantes: {20000 - 9215 - credits_used:,}")
    print(f"   Taxa de uso: {(9215 + credits_used) / 20000 * 100:.1f}%")

    # Salvar dataset final
    output = Path("data/ais/final_dataset.parquet")
    df_final.to_parquet(output)

    csv = Path("data/ais/final_dataset.csv")
    df_final.to_csv(csv, index=False)

    print(f"\n💾 DATASET FINAL salvo:")
    print(f"   {output} ({output.stat().st_size / 1024:.1f} KB)")
    print(f"   {csv} ({csv.stat().st_size / 1024:.1f} KB)")

    print("\n" + "=" * 70)
    print("✅ COLETA COMPLETA - CRÉDITOS MAXIMIZADOS!")
    print("=" * 70)


if __name__ == "__main__":
    main()
