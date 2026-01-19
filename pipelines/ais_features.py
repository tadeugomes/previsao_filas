import argparse
import math
from datetime import datetime
from pathlib import Path

import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_raw(files):
    frames = []
    for path in files:
        df = pd.read_csv(path, low_memory=False)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build_features(df):
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
    df = df.dropna(subset=["timestamp", "lat", "lon", "port_lat", "port_lon"])
    df["date"] = df["timestamp"].dt.date

    df["sog"] = pd.to_numeric(df.get("sog"), errors="coerce")
    df["cog"] = pd.to_numeric(df.get("cog"), errors="coerce")
    df["dist_km"] = df.apply(
        lambda r: haversine_km(r["lat"], r["lon"], r["port_lat"], r["port_lon"]), axis=1
    )
    df["velocidade_kn"] = df["sog"]
    df["eta_horas"] = df["dist_km"] / df["velocidade_kn"].replace(0, math.nan)

    grouped = df.groupby(["port_key", "port_name", "date"])
    feat = grouped.agg(
        ais_navios_no_raio=("mmsi", "count"),
        ais_fila_ao_largo=("dist_km", lambda x: (x > 10).sum()),
        ais_velocidade_media_kn=("velocidade_kn", "mean"),
        ais_eta_media_horas=("eta_horas", "mean"),
        ais_dist_media_km=("dist_km", "mean"),
    ).reset_index()

    feat = feat.fillna(0)
    return feat


def main():
    parser = argparse.ArgumentParser(description="Gerar features AIS por porto/dia.")
    parser.add_argument(
        "--input-dir",
        default="data/ais/raw",
        help="Diretorio com CSVs AIS.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Data YYYYMMDD (padrao: hoje).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Arquivo de saida (Parquet).",
    )
    args = parser.parse_args()

    date_tag = args.date or datetime.utcnow().strftime("%Y%m%d")
    in_dir = Path(args.input_dir)
    files = sorted(in_dir.glob(f"*_{date_tag}.csv"))
    if not files:
        print("Nenhum arquivo AIS encontrado.")
        return

    df = load_raw(files)
    if df.empty:
        print("Sem dados AIS.")
        return

    feat = build_features(df)
    out_path = Path(args.output) if args.output else Path("data/ais_features") / f"ais_features_{date_tag}.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    feat.to_parquet(out_path, index=False)
    print(f"Salvo: {out_path} ({len(feat)} linhas)")


if __name__ == "__main__":
    main()
