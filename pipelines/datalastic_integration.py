#!/usr/bin/env python3
"""
Integração com Datalastic API para coleta de dados históricos AIS.

Este script permite:
1. Coletar histórico de posições por IMO (navio específico)
2. Coletar tráfego histórico por localização (área portuária)
3. Detectar momentos de atracação a partir de posições AIS
4. Calcular tempo real de espera (target para treino)

Requisitos:
    pip install requests pandas pyarrow

Configuração:
    export DATALASTIC_API_KEY="sua_key_aqui"

Uso:
    # Teste básico
    python3 pipelines/datalastic_integration.py

    # Coletar dados de um porto
    python3 pipelines/datalastic_integration.py --porto Santos --meses 12

    # Processar lineup_history completo
    python3 pipelines/datalastic_integration.py --processar-lineup
"""

import os
import sys
import argparse
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import time

# Configuração
DATALASTIC_API_KEY = os.getenv("DATALASTIC_API_KEY", "")
BASE_URL = "https://api.datalastic.com/api/v0"

# Coordenadas dos portos brasileiros (centro + raio)
PORTOS = {
    "Santos": {
        "lat": -23.9511,
        "lon": -46.3344,
        "radius": 15,  # km
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
        "radius": 10,
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
        "radius": 10,
        "bounds": {
            "lat_min": -32.15,
            "lat_max": -31.92,
            "lon_min": -52.20,
            "lon_max": -52.00,
        },
    },
    "Vitória": {
        "lat": -20.3204,
        "lon": -40.3365,
        "radius": 10,
        "bounds": {
            "lat_min": -20.40,
            "lat_max": -20.24,
            "lon_min": -40.43,
            "lon_max": -40.24,
        },
    },
    "Itaqui": {
        "lat": -2.5734,
        "lon": -44.3667,
        "radius": 8,
        "bounds": {
            "lat_min": -2.65,
            "lat_max": -2.50,
            "lon_min": -44.45,
            "lon_max": -44.28,
        },
    },
}


class DatalasticClient:
    """Cliente para API Datalastic."""

    def __init__(self, api_key):
        """Inicializa cliente."""
        if not api_key:
            raise ValueError(
                "API key não configurada. Use: export DATALASTIC_API_KEY='sua_key'"
            )

        self.api_key = api_key
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.credits_used = 0

    def get_vessel_history_by_imo(self, imo, from_date, to_date):
        """
        Busca histórico de posições de um navio por IMO.

        Args:
            imo: Número IMO do navio
            from_date: Data inicial (datetime)
            to_date: Data final (datetime)

        Returns:
            list: Lista de posições do navio

        Custo: (to_date - from_date).days créditos
        """
        url = f"{self.base_url}/vessel_history"
        params = {
            "api-key": self.api_key,
            "imo": imo,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Estima créditos usados
            days = (to_date - from_date).days
            self.credits_used += days

            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar histórico do IMO {imo}: {e}")
            return None

    def get_port_traffic_history(self, porto_name, days=365):
        """
        Busca todos os navios que passaram por um porto em N dias.

        Args:
            porto_name: Nome do porto (ex: "Santos")
            days: Número de dias retroativos

        Returns:
            list: Lista de posições de todos os navios

        Custo: min(navios_por_dia * days, 500 * days) créditos
        """
        if porto_name not in PORTOS:
            raise ValueError(f"Porto '{porto_name}' não configurado")

        porto = PORTOS[porto_name]

        url = f"{self.base_url}/inradius_history"
        params = {
            "api-key": self.api_key,
            "latitude": porto["lat"],
            "longitude": porto["lon"],
            "radius": porto["radius"],
            "days": days,
        }

        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()

            # Estima créditos (cap de 500/dia)
            positions_per_day = len(data) / days if data else 0
            credits_per_day = min(positions_per_day, 500)
            self.credits_used += int(credits_per_day * days)

            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar tráfego do porto {porto_name}: {e}")
            return None

    def get_real_time_position(self, imo):
        """
        Busca posição atual de um navio.

        Args:
            imo: Número IMO do navio

        Returns:
            dict: Posição atual do navio

        Custo: 1 crédito
        """
        url = f"{self.base_url}/vessel_info"
        params = {"api-key": self.api_key, "imo": imo}

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            self.credits_used += 1

            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar posição do IMO {imo}: {e}")
            return None


def detect_berthing(positions, porto_name):
    """
    Detecta momento de atracação a partir de posições AIS.

    Critérios:
    1. Dentro da área portuária (geofence)
    2. Velocidade < 1 knot
    3. Status = MOORED, AT ANCHOR, ou similar
    4. Posição estável

    Args:
        positions: Lista de posições (dicts com lat, lon, speed, status, timestamp)
        porto_name: Nome do porto para bounds

    Returns:
        datetime ou None: Timestamp da primeira atracação detectada
    """
    if not positions:
        return None

    if porto_name not in PORTOS:
        return None

    porto_bounds = PORTOS[porto_name]["bounds"]

    df = pd.DataFrame(positions)

    # Verifica colunas necessárias
    required_cols = ["latitude", "longitude", "speed", "timestamp"]
    if not all(col in df.columns for col in required_cols):
        print(f"⚠️  Colunas faltando: {set(required_cols) - set(df.columns)}")
        return None

    # Converte timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Remove linhas com timestamp inválido
    df = df.dropna(subset=["timestamp"])

    if df.empty:
        return None

    # Ordena por timestamp
    df = df.sort_values("timestamp")

    # Filtro 1: Dentro da área portuária
    in_port = (
        (df["latitude"] >= porto_bounds["lat_min"])
        & (df["latitude"] <= porto_bounds["lat_max"])
        & (df["longitude"] >= porto_bounds["lon_min"])
        & (df["longitude"] <= porto_bounds["lon_max"])
    )

    # Filtro 2: Velocidade baixa
    stopped = df["speed"] < 1.0

    # Filtro 3: Status navegacional (se disponível)
    if "navigational_status" in df.columns:
        # Status típicos de atracação
        berthed_statuses = [
            "MOORED",
            "AT ANCHOR",
            "Not under command",
            "Moored",
            "At anchor",
        ]
        moored = df["navigational_status"].isin(berthed_statuses)
    else:
        # Se não tem status, usa apenas posição + velocidade
        moored = pd.Series([True] * len(df), index=df.index)

    # Combina todos os critérios
    berthed = in_port & stopped & moored

    # Primeira posição que atende critérios
    if berthed.any():
        first_berth = df[berthed].iloc[0]
        return first_berth["timestamp"]

    return None


def calculate_waiting_time(prev_chegada, data_atracacao):
    """
    Calcula tempo de espera em horas.

    Args:
        prev_chegada: Data/hora prevista de chegada (datetime ou string)
        data_atracacao: Data/hora real de atracação (datetime ou string)

    Returns:
        float ou None: Tempo de espera em horas
    """
    # Converte para datetime se necessário
    if isinstance(prev_chegada, str):
        prev_chegada = pd.to_datetime(prev_chegada, errors="coerce")

    if isinstance(data_atracacao, str):
        data_atracacao = pd.to_datetime(data_atracacao, errors="coerce")

    # Valida
    if pd.isna(prev_chegada) or pd.isna(data_atracacao):
        return None

    # Calcula diferença
    delta = data_atracacao - prev_chegada

    # Converte para horas
    horas = delta.total_seconds() / 3600

    # Valida range (espera negativa ou > 30 dias é suspeito)
    if horas < 0 or horas > 720:  # 30 dias
        return None

    return horas


def processar_porto_historico(client, porto_name, meses=12, output_dir="data/ais"):
    """
    Coleta e processa dados históricos de um porto.

    Args:
        client: Instância de DatalasticClient
        porto_name: Nome do porto
        meses: Número de meses de histórico
        output_dir: Diretório para salvar resultados

    Returns:
        DataFrame com atracações detectadas
    """
    print("\n" + "=" * 70)
    print(f"PROCESSANDO PORTO: {porto_name}")
    print("=" * 70)

    days = meses * 30

    print(f"\n📡 Coletando {days} dias de histórico...")
    print(f"   Área: lat={PORTOS[porto_name]['lat']}, lon={PORTOS[porto_name]['lon']}")
    print(f"   Raio: {PORTOS[porto_name]['radius']} km")

    # Coleta tráfego histórico
    traffic = client.get_port_traffic_history(porto_name, days=days)

    if not traffic:
        print("❌ Nenhum dado retornado")
        return None

    print(f"✅ Retornadas {len(traffic):,} posições")

    # Converte para DataFrame
    df = pd.DataFrame(traffic)

    # Salva dados brutos (backup)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    raw_file = output_path / f"{porto_name.lower()}_raw_{meses}m.parquet"
    df.to_parquet(raw_file)
    print(f"💾 Dados brutos salvos: {raw_file}")

    # Analisa dados
    navios_unicos = df["imo"].nunique() if "imo" in df.columns else 0
    print(f"📊 Navios únicos: {navios_unicos:,}")

    # Detecta atracações
    print(f"\n🔍 Detectando atracações...")

    atracacoes = []

    if "imo" in df.columns:
        navios = df.groupby("imo")

        for imo, positions in navios:
            # Detecta atracação
            data_atracacao = detect_berthing(
                positions.to_dict("records"), porto_name
            )

            if data_atracacao:
                atracacoes.append(
                    {
                        "imo": imo,
                        "porto": porto_name,
                        "data_atracacao": data_atracacao,
                        "num_positions": len(positions),
                    }
                )

    df_atracacoes = pd.DataFrame(atracacoes)

    if not df_atracacoes.empty:
        print(f"✅ {len(df_atracacoes):,} atracações detectadas")

        # Salva atracações
        atracacoes_file = output_path / f"{porto_name.lower()}_atracacoes_{meses}m.parquet"
        df_atracacoes.to_parquet(atracacoes_file)
        print(f"💾 Atracações salvas: {atracacoes_file}")
    else:
        print("⚠️  Nenhuma atracação detectada")

    print(f"\n💳 Créditos usados até agora: {client.credits_used:,}")

    return df_atracacoes


def processar_lineup_history(client, output_dir="data/treino"):
    """
    Processa lineup_history.parquet e adiciona dados de atracação real.

    Args:
        client: Instância de DatalasticClient
        output_dir: Diretório para salvar dataset de treino

    Returns:
        DataFrame com targets calculados
    """
    print("\n" + "=" * 70)
    print("PROCESSANDO LINEUP_HISTORY.PARQUET")
    print("=" * 70)

    # Carrega lineup_history
    lineup_file = Path("lineups_previstos/lineup_history.parquet")

    if not lineup_file.exists():
        print(f"❌ Arquivo não encontrado: {lineup_file}")
        return None

    df_lineup = pd.read_parquet(lineup_file)
    print(f"\n✅ Carregado: {len(df_lineup):,} registros")
    print(f"   Colunas: {list(df_lineup.columns)}")

    # Verifica colunas necessárias
    required = ["imo", "porto", "prev_chegada"]
    missing = [col for col in required if col not in df_lineup.columns]

    if missing:
        print(f"❌ Colunas necessárias faltando: {missing}")
        return None

    # Converte prev_chegada
    df_lineup["prev_chegada"] = pd.to_datetime(
        df_lineup["prev_chegada"], errors="coerce"
    )

    # Remove registros sem data válida
    df_lineup = df_lineup.dropna(subset=["prev_chegada"])

    print(f"📊 Registros válidos: {len(df_lineup):,}")

    # Para cada registro, busca atracação real
    print(f"\n🔍 Buscando atracações reais...")

    atracacoes_reais = []

    for idx, row in df_lineup.iterrows():
        imo = row["imo"]
        porto = row["porto"]
        prev_chegada = row["prev_chegada"]

        # Busca histórico de 7 dias após chegada prevista
        from_date = prev_chegada
        to_date = prev_chegada + timedelta(days=7)

        print(f"\r   Processando {idx+1}/{len(df_lineup)}: IMO {imo}...", end="")

        # Busca posições
        positions = client.get_vessel_history_by_imo(imo, from_date, to_date)

        if not positions:
            continue

        # Detecta atracação
        data_atracacao = detect_berthing(positions, porto)

        if data_atracacao:
            atracacoes_reais.append(
                {
                    "imo": imo,
                    "porto": porto,
                    "prev_chegada": prev_chegada,
                    "data_atracacao": data_atracacao,
                }
            )

        # Rate limiting (600 req/min = 10 req/s)
        time.sleep(0.1)

    print(f"\n✅ {len(atracacoes_reais)} atracações encontradas")

    # Junta com lineup original
    df_atracacoes = pd.DataFrame(atracacoes_reais)

    if df_atracacoes.empty:
        print("❌ Nenhuma atracação detectada")
        return None

    df_treino = df_lineup.merge(df_atracacoes, on=["imo", "porto"], how="inner")

    # Calcula target
    df_treino["tempo_espera_horas"] = df_treino.apply(
        lambda row: calculate_waiting_time(
            row["prev_chegada_x"], row["data_atracacao"]
        ),
        axis=1,
    )

    # Remove registros sem target válido
    df_treino = df_treino.dropna(subset=["tempo_espera_horas"])

    print(f"\n📊 Dataset de treino: {len(df_treino):,} registros")
    print(f"   Tempo médio de espera: {df_treino['tempo_espera_horas'].mean():.1f}h")
    print(f"   Tempo mediano: {df_treino['tempo_espera_horas'].median():.1f}h")
    print(f"   Range: {df_treino['tempo_espera_horas'].min():.1f}h - {df_treino['tempo_espera_horas'].max():.1f}h")

    # Salva dataset
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    treino_file = output_path / "lineup_history_com_target.parquet"
    df_treino.to_parquet(treino_file)

    print(f"\n💾 Dataset salvo: {treino_file}")
    print(f"💳 Créditos usados: {client.credits_used:,}")

    return df_treino


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Integração com Datalastic API para coleta de dados históricos AIS"
    )
    parser.add_argument(
        "--porto", type=str, help="Nome do porto (Santos, Paranaguá, etc)"
    )
    parser.add_argument(
        "--meses", type=int, default=12, help="Número de meses de histórico"
    )
    parser.add_argument(
        "--processar-lineup",
        action="store_true",
        help="Processar lineup_history.parquet",
    )
    parser.add_argument(
        "--teste", action="store_true", help="Executar testes básicos da API"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("DATALASTIC API - INTEGRAÇÃO AIS")
    print("=" * 70)

    # Verifica API key
    if not DATALASTIC_API_KEY:
        print("\n❌ API key não configurada!")
        print("\nPara configurar:")
        print("   1. Crie conta em: https://datalastic.com/pricing/")
        print("   2. Obtenha API key no painel")
        print("   3. Configure: export DATALASTIC_API_KEY='sua_key'")
        print("\nTrial gratuito disponível: 14 dias")
        return 1

    # Inicializa cliente
    try:
        client = DatalasticClient(DATALASTIC_API_KEY)
        print(f"\n✅ Cliente inicializado")
    except Exception as e:
        print(f"\n❌ Erro ao inicializar cliente: {e}")
        return 1

    # Executa ações
    if args.teste:
        # Teste básico
        print("\n[TESTE] Buscando posição atual de navio exemplo...")
        # IMO de exemplo (substituir por real)
        imo_teste = "9797058"
        position = client.get_real_time_position(imo_teste)

        if position:
            print(f"✅ Posição obtida:")
            print(f"   IMO: {position.get('imo')}")
            print(f"   Lat/Lon: {position.get('latitude')}, {position.get('longitude')}")
            print(f"   Speed: {position.get('speed')} knots")
            print(f"   Status: {position.get('navigational_status')}")
        else:
            print("❌ Teste falhou")

    elif args.porto:
        # Processar porto específico
        processar_porto_historico(client, args.porto, meses=args.meses)

    elif args.processar_lineup:
        # Processar lineup_history
        processar_lineup_history(client)

    else:
        # Informações gerais
        print("\n💡 Uso:")
        print("   --teste              : Testar API")
        print("   --porto Santos       : Processar porto específico")
        print("   --processar-lineup   : Processar lineup_history.parquet")
        print("\n📖 Exemplos:")
        print("   python3 pipelines/datalastic_integration.py --teste")
        print("   python3 pipelines/datalastic_integration.py --porto Santos --meses 12")
        print("   python3 pipelines/datalastic_integration.py --processar-lineup")

    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
