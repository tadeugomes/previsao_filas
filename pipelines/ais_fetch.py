import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://data.aishub.net/ws.php"


def load_ports(path):
    df = pd.read_csv(path)
    required = {"port_key", "port_name", "lat", "lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {missing}")
    if "radius_km" not in df.columns:
        df["radius_km"] = 50
    return df


def fetch_ais(port_row, username):
    radius_km = float(port_row["radius_km"])
    lat = float(port_row["lat"])
    lon = float(port_row["lon"])
    delta = radius_km / 111.0

    params = {
        "username": username,
        "format": "json",
        "msgtype": "ais",
        "latmin": lat - delta,
        "latmax": lat + delta,
        "lonmin": lon - delta,
        "lonmax": lon + delta,
        "limit": 1000,
    }
    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("data", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
    df["port_key"] = port_row["port_key"]
    df["port_name"] = port_row["port_name"]
    df["port_lat"] = lat
    df["port_lon"] = lon
    return df


def main():
    parser = argparse.ArgumentParser(description="Captura AIS por porto via AISHub.")
    parser.add_argument(
        "--ports",
        default="data/ports_config.csv",
        help="CSV com colunas port_key, port_name, lat, lon, radius_km.",
    )
    parser.add_argument(
        "--out",
        default="data/ais/raw",
        help="Diretorio de saida.",
    )
    args = parser.parse_args()

    username = os.environ.get("AISHUB_USER")
    if not username:
        raise RuntimeError("Defina a variavel de ambiente AISHUB_USER.")

    ports = load_ports(args.ports)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.utcnow().strftime("%Y%m%d")

    for _, row in ports.iterrows():
        try:
            df = fetch_ais(row, username)
            if df.empty:
                print(f"{row['port_key']}: sem dados")
                continue
            out_path = out_dir / f"ais_{row['port_key']}_{date_tag}.csv"
            df.to_csv(out_path, index=False)
            print(f"{row['port_key']}: {len(df)} registros -> {out_path}")
        except Exception as exc:
            print(f"{row['port_key']}: erro -> {exc}")


if __name__ == "__main__":
    main()
