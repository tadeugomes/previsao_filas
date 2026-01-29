#!/usr/bin/env python3
"""
Coleta de dados dos 3 portos principais para treino de modelos.

Portos: Santos, Paranaguá, Rio Grande
Período: 60 dias
Filtro: Apenas Cargo e Tanker (relevantes para modelo)

Estimativa de créditos:
- Santos:     ~100 navios × 60 dias = 6.000 créditos
- Paranaguá:  ~70 navios × 60 dias  = 4.200 créditos
- Rio Grande: ~50 navios × 60 dias  = 3.000 créditos
Total: ~13.200 créditos (de 16.939 disponíveis)
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import time

API_KEY = "8f4d73c7-0455-4afd-9032-4ad4878ec5b0"
BASE_URL = "https://api.datalastic.com/api/v0"

# Configuração dos portos
PORTOS = {
    "Santos": {
        "lat": -23.9511,
        "lon": -46.3344,
        "radius": 8.1,  # 15 km → 8.1 NM
        "bounds": {
            "lat_min": -24.05,
            "lat_max": -23.85,
            "lon_min": -46.45,
            "lon_max": -46.22,
        },
    },
    "Paranaguá": {
        "lat": -25.5163,
        "lon": -48.5133,
        "radius": 5.4,  # 10 km → 5.4 NM
        "bounds": {
            "lat_min": -25.60,
            "lat_max": -25.43,
            "lon_min": -48.60,
            "lon_max": -48.42,
        },
    },
    "Rio Grande": {
        "lat": -32.0350,
        "lon": -52.0993,
        "radius": 5.4,  # 10 km → 5.4 NM
        "bounds": {
            "lat_min": -32.15,
            "lat_max": -31.92,
            "lon_min": -52.20,
            "lon_max": -52.00,
        },
    },
}

# Tipos de navio relevantes para treino
RELEVANT_TYPES = ["Cargo", "Tanker"]

credits_used = 0
credits_start = 16939  # Créditos disponíveis antes desta coleta


def is_relevant_vessel(vessel_type):
    """Verifica se o tipo de navio é relevante para treino."""
    if not vessel_type:
        return False

    vessel_type_lower = vessel_type.lower()
    return any(rel_type.lower() in vessel_type_lower for rel_type in RELEVANT_TYPES)


def get_vessels_in_port(porto_name):
    """Busca navios atuais no porto."""
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


def get_vessel_history(imo, days=60):
    """Busca histórico de um navio."""
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
    """Detecta todas as atracações no período."""
    if not positions:
        return []

    df = pd.DataFrame(positions)
    df["timestamp_dt"] = pd.to_datetime(df["last_position_UTC"], errors="coerce")
    df = df.sort_values("timestamp_dt")

    # Marca posições atracadas
    df["in_port"] = (
        (df["lat"] >= bounds["lat_min"])
        & (df["lat"] <= bounds["lat_max"])
        & (df["lon"] >= bounds["lon_min"])
        & (df["lon"] <= bounds["lon_max"])
    )
    df["stopped"] = df["speed"] < 1.0
    df["berthed"] = df["in_port"] & df["stopped"]

    # Detecta início de atracação
    df["berthing_start"] = (df["berthed"] == True) & (df["berthed"].shift(1) == False)

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
    """Calcula tempo de espera."""
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

    # Valida: 0-720h (0-30 dias)
    if waiting_time < 0 or waiting_time > 720:
        return None

    return waiting_time


def process_port(porto_name, days=60):
    """Processa um porto completo."""
    global credits_used

    print("\n" + "=" * 70)
    print(f"PROCESSANDO: {porto_name.upper()}")
    print("=" * 70)

    # 1. Buscar navios atuais
    print(f"\n📡 Buscando navios atuais...")
    vessels = get_vessels_in_port(porto_name)

    # 2. Filtrar apenas Cargo/Tanker com IMO
    relevant_vessels = [
        v for v in vessels
        if v.get("imo") and is_relevant_vessel(v.get("type"))
    ]

    print(f"✅ Total de navios: {len(vessels)}")
    print(f"🎯 Cargo/Tanker com IMO: {len(relevant_vessels)}")
    print(f"💳 Estimativa: {len(relevant_vessels) * days:,} créditos")

    if not relevant_vessels:
        print(f"⚠️  Nenhum navio relevante encontrado no {porto_name}")
        return []

    print(f"\n📊 Tipos de navios relevantes encontrados:")
    types_count = {}
    for v in relevant_vessels:
        vtype = v.get("type", "Unknown")
        types_count[vtype] = types_count.get(vtype, 0) + 1

    for vtype, count in sorted(types_count.items()):
        print(f"   {vtype}: {count}")

    # 3. Processar cada navio
    print(f"\n🚢 Processando {len(relevant_vessels)} navios ({days} dias cada)...")
    print()

    all_berthings = []
    processed = 0
    errors = 0

    for i, vessel in enumerate(relevant_vessels, 1):
        imo = vessel["imo"]
        name = vessel["name"]
        vtype = vessel.get("type", "Unknown")

        print(f"[{i}/{len(relevant_vessels)}] {name} ({vtype})", end="")

        # Busca histórico
        history = get_vessel_history(imo, days=days)

        if not history:
            print(f" ❌ Erro")
            errors += 1
            continue

        positions = history.get("positions", [])
        print(f" → {len(positions)} pos", end="")

        # Detecta atracações
        berthings = detect_all_berthings(positions, PORTOS[porto_name]["bounds"])

        if berthings:
            print(f" → {len(berthings)} atracação(ões)", end="")

            for berthing in berthings:
                waiting_time = calculate_waiting_time(positions, berthing["berthing_time"])

                all_berthings.append(
                    {
                        "imo": imo,
                        "name": name,
                        "type": vtype,
                        "porto": porto_name,
                        "berthing_time": berthing["berthing_time"],
                        "lat": berthing["lat"],
                        "lon": berthing["lon"],
                        "waiting_time_hours": waiting_time,
                        "num_positions": len(positions),
                    }
                )

            if waiting_time is not None:
                print(f" → ~{waiting_time:.0f}h")
            else:
                print(f" → N/A")
        else:
            print(f" → Nenhuma atracação")

        processed += 1

        # Progress a cada 10 navios
        if i % 10 == 0:
            print(f"\n  💳 Créditos: {credits_used:,} | Restantes: {credits_start - credits_used:,}\n")

    # 4. Resultados
    print("\n" + "-" * 70)
    print(f"RESUMO - {porto_name}")
    print("-" * 70)
    print(f"Navios processados: {processed}/{len(relevant_vessels)}")
    print(f"Atracações detectadas: {len(all_berthings)}")
    print(f"Erros: {errors}")
    print(f"💳 Créditos usados (este porto): {len(relevant_vessels) * days:,}")
    print(f"💳 Créditos acumulados: {credits_used:,}")
    print(f"💰 Créditos restantes: {credits_start - credits_used:,}")

    return all_berthings


def main():
    """Função principal."""
    global credits_used

    print("=" * 70)
    print("COLETA: SANTOS + PARANAGUÁ + RIO GRANDE")
    print("=" * 70)
    print(f"\n📅 Período: 60 dias")
    print(f"🎯 Filtro: Cargo e Tanker apenas")
    print(f"💳 Créditos disponíveis: {credits_start:,}")
    print()

    input("Pressione ENTER para iniciar a coleta...")

    # Processar os 3 portos
    all_results = []

    for porto_name in ["Santos", "Paranaguá", "Rio Grande"]:
        try:
            berthings = process_port(porto_name, days=60)
            all_results.extend(berthings)

            # Pequena pausa entre portos
            time.sleep(2)

        except Exception as e:
            print(f"\n❌ Erro ao processar {porto_name}: {e}")
            continue

    # Consolidar resultados
    print("\n" + "=" * 70)
    print("RESULTADOS FINAIS - TODOS OS PORTOS")
    print("=" * 70)

    if not all_results:
        print("\n❌ Nenhum dado coletado")
        return

    df = pd.DataFrame(all_results)

    print(f"\n📊 Estatísticas Gerais:")
    print(f"   Total de atracações: {len(df)}")
    print(f"   Portos: {df['porto'].nunique()}")
    print(f"   Navios únicos: {df['imo'].nunique()}")

    # Por porto
    print(f"\n🚢 Atracações por porto:")
    for porto, count in df['porto'].value_counts().items():
        print(f"   {porto}: {count}")

    # Por tipo
    print(f"\n📦 Atracações por tipo:")
    for vtype, count in df['type'].value_counts().items():
        print(f"   {vtype}: {count}")

    # Tempo de espera
    valid_waiting = df["waiting_time_hours"].dropna()

    if not valid_waiting.empty:
        print(f"\n⏱️  Tempo de Espera:")
        print(f"   Registros válidos: {len(valid_waiting)}/{len(df)} ({len(valid_waiting)/len(df)*100:.1f}%)")
        print(f"   Média: {valid_waiting.mean():.1f}h ({valid_waiting.mean()/24:.1f} dias)")
        print(f"   Mediana: {valid_waiting.median():.1f}h ({valid_waiting.median()/24:.1f} dias)")
        print(f"   Mín: {valid_waiting.min():.1f}h ({valid_waiting.min()/24:.1f} dias)")
        print(f"   Máx: {valid_waiting.max():.1f}h ({valid_waiting.max()/24:.1f} dias)")
        print(f"   Desvio: {valid_waiting.std():.1f}h")

    # Créditos
    print(f"\n💳 Créditos:")
    print(f"   Usados nesta coleta: {credits_used - 3061:,}  (Itaqui anterior: 3.061)")
    print(f"   Total acumulado: {credits_used:,} / 20.000")
    print(f"   Restantes: {20000 - credits_used:,}")

    # Salvar
    output_dir = Path("data/ais")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parquet
    output_file = output_dir / "main_ports_60d.parquet"
    df.to_parquet(output_file)
    print(f"\n💾 Dados salvos:")
    print(f"   {output_file} ({output_file.stat().st_size / 1024:.1f} KB)")

    # CSV
    csv_file = output_dir / "main_ports_60d.csv"
    df.to_csv(csv_file, index=False)
    print(f"   {csv_file} ({csv_file.stat().st_size / 1024:.1f} KB)")

    # Amostra
    print(f"\n📋 Amostra (10 primeiros):")
    print(df[['porto', 'name', 'type', 'berthing_time', 'waiting_time_hours']].head(10).to_string(index=False))

    print("\n" + "=" * 70)
    print("PRÓXIMOS PASSOS")
    print("=" * 70)
    print(f"\n✅ Dados de 3 portos principais coletados!")
    print(f"📊 Total: {len(df)} atracações")
    print(f"💳 Créditos restantes: {20000 - credits_used:,}")
    print(f"\n💡 Agora você pode:")
    print(f"   1. Combinar com dados de Itaqui")
    print(f"   2. Preprocessar para treino")
    print(f"   3. Treinar modelos light reais")
    print(f"   4. Substituir modelos mock")
    print("=" * 70)


if __name__ == "__main__":
    main()
