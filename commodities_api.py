"""
Módulo para obtenção de preços de commodities agrícolas e minerais.

Fontes de dados (em ordem de prioridade):
1. IPEA (séries históricas)
2. ComexStat (proxy FOB/KG)
3. Banco Central do Brasil (índices)
4. Dados em cache local (fallback)

Produtos suportados:
- Soja, Milho, Algodão (granel agrícola)
- Minério de ferro, Açúcar (outros granéis)
"""

import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import logging
import json

logger = logging.getLogger(__name__)

# Diretório para cache de dados
CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
COMEXSTAT_CACHE_DIR = CACHE_DIR / "comexstat"
COMEXSTAT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
COMEXSTAT_BQ_CACHE_DIR = CACHE_DIR / "comexstat_bq"
COMEXSTAT_BQ_CACHE_DIR.mkdir(parents=True, exist_ok=True)
COMEXSTAT_BQ_PROJECT = (
    os.getenv("COMEXSTAT_BQ_PROJECT")
    or os.getenv("BIGQUERY_PROJECT")
    or os.getenv("GOOGLE_CLOUD_PROJECT")
    or "antaqdados"
)

# Base URLs
IPEA_BASE_URL = "https://www.ipeadata.gov.br/api/odata4"
COMEXSTAT_BASE_URL = "https://api-comexstat.mdic.gov.br"

def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")

# SSL verify toggle for ComexStat (fallback to False on SSL errors)
COMEXSTAT_SSL_VERIFY = _env_flag("COMEXSTAT_SSL_VERIFY", True)

# Séries do IPEA para commodities
IPEA_SERIES = {
    # Preços internacionais (FMI/Banco Mundial)
    "Soja": ["IFS12_SOJAGP12"],
    "Milho": ["IFS12_MAIZE12"],
    # IPEA não possui série de preço recorrente para algodão no catálogo atual
    "Algodao": [],
    # Minerais e outros (mantidos vazios por ora)
    "Ferro": [],
    "Acucar": [],
}

# Séries do Banco Central (como proxy/índices)
BCB_SERIES = {
    "IGP-DI": 190,  # Índice Geral de Preços
    "IPA-Agropecuaria": 225,  # Índice de Preços por Atacado - Agropecuária
    "IPA-Industrial": 226,  # Índice de Preços por Atacado - Industrial
}

# Preços médios históricos (fallback) - em US$/tonelada ou R$/saca
PRECOS_FALLBACK = {
    "Soja": {
        "2020": 380, "2021": 500, "2022": 580, "2023": 480,
        "2024": 420, "2025": 400, "2026": 390
    },
    "Milho": {
        "2020": 165, "2021": 260, "2022": 310, "2023": 220,
        "2024": 180, "2025": 170, "2026": 165
    },
    "Algodao": {
        "2020": 1500, "2021": 2200, "2022": 2600, "2023": 1900,
        "2024": 1700, "2025": 1650, "2026": 1600
    },
    "Ferro": {
        "2020": 100, "2021": 160, "2022": 120, "2023": 110,
        "2024": 100, "2025": 95, "2026": 90
    },
    "Acucar": {
        "2020": 280, "2021": 400, "2022": 380, "2023": 450,
        "2024": 420, "2025": 400, "2026": 380
    },
}

COMEXSTAT_HEADINGS = {
    "Soja": 1201,
    "Milho": 1005,
    "Algodao": 5201,
}

def _request_comexstat(method: str, path: str, json_body: Optional[dict] = None, timeout: int = 30):
    url = f"{COMEXSTAT_BASE_URL}{path}"
    try:
        return requests.request(
            method,
            url,
            json=json_body,
            timeout=timeout,
            verify=COMEXSTAT_SSL_VERIFY,
        )
    except requests.exceptions.SSLError as exc:
        if COMEXSTAT_SSL_VERIFY:
            logger.warning("ComexStat SSL verify failed; retrying with verify=False")
            # Disable verification for subsequent calls to avoid repeated failures
            globals()["COMEXSTAT_SSL_VERIFY"] = False
            return requests.request(
                method,
                url,
                json=json_body,
                timeout=timeout,
                verify=False,
            )
        raise exc


def _get_bq_client(project_id: Optional[str] = None):
    try:
        from google.cloud import bigquery
    except Exception as exc:
        logger.debug(f"BigQuery client unavailable: {exc}")
        return None
    project = project_id or COMEXSTAT_BQ_PROJECT
    try:
        return bigquery.Client(project=project)
    except Exception as exc:
        logger.debug(f"BigQuery client init failed: {exc}")
        return None


def _fetch_ipea_serie(codigo: str, timeout: int = 10) -> Optional[pd.DataFrame]:
    """Busca dados de uma série do IPEA."""
    url = f"{IPEA_BASE_URL}/Metadados('{codigo}')/Valores"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if "value" in data and len(data["value"]) > 0:
                df = pd.DataFrame(data["value"])
                df["data"] = pd.to_datetime(df["VALDATA"], errors="coerce", utc=True).dt.tz_convert(None)
                df["preco"] = pd.to_numeric(df["VALVALOR"], errors="coerce")
                df = df[["data", "preco"]].dropna()
                if not df.empty:
                    return df.sort_values("data")
    except Exception as e:
        logger.debug(f"IPEA {codigo}: {e}")
    return None


def _fetch_bcb_serie(codigo: int, timeout: int = 10) -> Optional[pd.DataFrame]:
    """Busca dados de uma série do Banco Central."""
    # Últimos 5 anos
    data_inicio = (datetime.now() - timedelta(days=365*5)).strftime("%d/%m/%Y")
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={data_inicio}"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
                df["preco"] = pd.to_numeric(df["valor"], errors="coerce")
                df = df[["data", "preco"]].dropna()
                if not df.empty:
                    return df.sort_values("data")
    except Exception as e:
        logger.debug(f"BCB {codigo}: {e}")
    return None


def _fetch_comexstat_bq_heading(produto: str, heading: int, project_id: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Busca série mensal de preço via ComexStat (BQ) para um SH4."""
    client = _get_bq_client(project_id)
    cache_path = COMEXSTAT_BQ_CACHE_DIR / f"{produto.lower()}_{heading}.parquet"
    if client is None:
        if cache_path.exists():
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                return None
        return None

    try:
        from google.cloud import bigquery
    except Exception:
        return None

    query = """
        SELECT
            ano,
            mes,
            SUM(valor_fob_dolar) AS valor_fob_dolar,
            SUM(peso_liquido_kg) AS peso_liquido_kg
        FROM `basedosdados.br_me_comex_stat.ncm_exportacao`
        WHERE ano >= 2020
          AND SAFE_CAST(SUBSTR(CAST(id_ncm AS STRING), 1, 4) AS INT64) = @heading
        GROUP BY ano, mes
        ORDER BY ano, mes
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("heading", "INT64", heading)]
    )
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
    except Exception as exc:
        logger.debug(f"ComexStat BQ {produto}: {exc}")
        if cache_path.exists():
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                return None
        return None

    if df is None or df.empty:
        return None
    df["valor_fob_dolar"] = pd.to_numeric(df["valor_fob_dolar"], errors="coerce")
    df["peso_liquido_kg"] = pd.to_numeric(df["peso_liquido_kg"], errors="coerce")
    df = df[(df["valor_fob_dolar"] > 0) & (df["peso_liquido_kg"] > 0)]
    if df.empty:
        return None
    df["data"] = pd.to_datetime(
        df["ano"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )
    df = df.dropna(subset=["data"])
    if df.empty:
        return None
    # Convert to USD/ton to align with IPEA series
    df["preco"] = (df["valor_fob_dolar"] / df["peso_liquido_kg"]) * 1000.0
    df["produto"] = produto
    df = df[["data", "preco", "produto"]].sort_values("data")
    try:
        df.to_parquet(cache_path, index=False)
    except Exception:
        pass
    return df


def _build_bcb_proxy_series(produto: str) -> Optional[pd.DataFrame]:
    """Usa o indice IPA-Agropecuaria como proxy para serie de preco."""
    df_idx = _fetch_bcb_serie(BCB_SERIES["IPA-Agropecuaria"])
    if df_idx is None or df_idx.empty:
        return None
    df_idx = df_idx.sort_values("data").reset_index(drop=True)
    base = _get_fallback_price(produto, df_idx.loc[0, "data"].year, df_idx.loc[0, "data"].month)
    idx_base = df_idx.loc[0, "preco"]
    if idx_base == 0:
        return None
    df_idx["preco"] = base * (df_idx["preco"] / idx_base)
    df_idx["produto"] = produto
    return df_idx[["data", "preco", "produto"]]


def _fetch_comexstat_heading(produto: str, heading: int, flow: str = "export") -> Optional[pd.DataFrame]:
    """Busca série mensal de preço via ComexStat (FOB/KG) para um SH4."""
    hoje = datetime.now()
    start_year = 2020
    end_year = hoje.year
    rows: List[dict] = []
    cache_path = COMEXSTAT_CACHE_DIR / f"{produto.lower()}_{heading}.parquet"

    for year in range(start_year, end_year + 1):
        to_month = 12 if year < end_year else hoje.month
        body = {
            "flow": flow,
            "monthDetail": True,
            "period": {"from": f"{year}-01", "to": f"{year}-{to_month:02d}"},
            "filters": [{"filter": "heading", "values": [heading]}],
            "details": ["heading"],
            "metrics": ["metricFOB", "metricKG"],
        }
        try:
            resp = None
            for attempt in range(5):
                resp = _request_comexstat("POST", "/general", json_body=body, timeout=45)
                if resp.status_code == 429:
                    time.sleep(1 + (2 ** attempt))
                    continue
                break
            if resp is None:
                continue
            if resp.status_code != 200:
                logger.debug(f"ComexStat {produto}: HTTP {resp.status_code} ({year})")
                continue
            payload = resp.json()
            rows.extend(payload.get("data", {}).get("list", []))
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"ComexStat {produto} ({year}): {e}")

    if not rows:
        if cache_path.exists():
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                return None
        return None

    df = pd.DataFrame(rows)
    df["metricFOB"] = pd.to_numeric(df["metricFOB"], errors="coerce")
    df["metricKG"] = pd.to_numeric(df["metricKG"], errors="coerce")
    df = df[(df["metricFOB"] > 0) & (df["metricKG"] > 0)]
    if df.empty:
        return None
    df["data"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["monthNumber"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )
    df = df.dropna(subset=["data"])
    if df.empty:
        return None
    df["preco"] = df["metricFOB"] / df["metricKG"]
    df["produto"] = produto
    df = df[["data", "preco", "produto"]].sort_values("data")
    try:
        df.to_parquet(cache_path, index=False)
    except Exception:
        pass
    return df


def _fetch_comexstat_precos(produto: str) -> Optional[pd.DataFrame]:
    heading = COMEXSTAT_HEADINGS.get(produto)
    if not heading:
        return None
    return _fetch_comexstat_heading(produto, heading)


def _get_fallback_price(produto: str, ano: int, mes: int) -> float:
    """Retorna preço de fallback com interpolação mensal."""
    if produto not in PRECOS_FALLBACK:
        return 100.0

    precos = PRECOS_FALLBACK[produto]
    ano_str = str(ano)

    if ano_str in precos:
        preco_base = precos[ano_str]
    else:
        # Usar último ano disponível
        ultimo_ano = max(int(k) for k in precos.keys())
        preco_base = precos[str(ultimo_ano)]

    # Adicionar variação sazonal (safra: março-junho tem preços menores)
    sazonalidade = {
        1: 1.02, 2: 1.01, 3: 0.95, 4: 0.93, 5: 0.94, 6: 0.96,
        7: 0.98, 8: 1.00, 9: 1.02, 10: 1.03, 11: 1.04, 12: 1.03
    }
    return preco_base * sazonalidade.get(mes, 1.0)


def extrair_precos_commodities_v2() -> Optional[pd.DataFrame]:
    """
    Extrai preços de commodities com múltiplas fontes.

    Tenta em ordem: IPEA -> ComexStat -> BCB (proxy) -> Fallback

    Returns:
        DataFrame com colunas [data, preco, produto]
    """
    print("[4/4] Extraindo precos de commodities...")

    produtos_alvo = ["Soja", "Milho", "Algodao"]
    df_list = []

    for produto in produtos_alvo:
        df_produto = None
        fonte = "fallback"

        # Tentar IPEA
        if produto in IPEA_SERIES:
            for codigo in IPEA_SERIES[produto]:
                df_temp = _fetch_ipea_serie(codigo)
                if df_temp is not None and len(df_temp) > 10:
                    df_produto = df_temp.copy()
                    df_produto["produto"] = produto
                    fonte = f"IPEA/{codigo}"
                    break

        # Tentar ComexStat via BigQuery
        if df_produto is None or df_produto.empty:
            heading = COMEXSTAT_HEADINGS.get(produto)
            if heading:
                df_temp = _fetch_comexstat_bq_heading(produto, heading)
                if df_temp is not None and len(df_temp) > 10:
                    df_produto = df_temp.copy()
                    fonte = "ComexStat/BQ"

        # Tentar ComexStat via API (proxy FOB/KG)
        if df_produto is None or df_produto.empty:
            df_temp = _fetch_comexstat_precos(produto)
            if df_temp is not None and len(df_temp) > 10:
                df_produto = df_temp.copy()
                fonte = "ComexStat/API"

        # Tentar BCB (proxy indice)
        if df_produto is None or df_produto.empty:
            df_temp = _build_bcb_proxy_series(produto)
            if df_temp is not None and len(df_temp) > 10:
                df_produto = df_temp.copy()
                fonte = "BCB/IPA-Agropecuaria"

        # Se não conseguiu, gerar fallback
        if df_produto is None or df_produto.empty:
            dates = pd.date_range("2020-01-01", datetime.now(), freq="MS")
            precos = [
                _get_fallback_price(produto, d.year, d.month)
                for d in dates
            ]
            df_produto = pd.DataFrame({
                "data": dates,
                "preco": precos,
                "produto": produto
            })
            fonte = "fallback"

        print(f"    {produto}: {len(df_produto)} registros ({fonte})")
        df_list.append(df_produto)

    if df_list:
        df_final = pd.concat(df_list, ignore_index=True)
        print(f"    OK. Total: {len(df_final):,} registros")

        # Salvar em cache
        cache_path = CACHE_DIR / "precos_commodities.parquet"
        try:
            df_final.to_parquet(cache_path, index=False)
        except Exception:
            pass

        return df_final

    return None


def carregar_precos_cache() -> Optional[pd.DataFrame]:
    """Carrega preços do cache local."""
    cache_path = CACHE_DIR / "precos_commodities.parquet"
    if cache_path.exists():
        try:
            return pd.read_parquet(cache_path)
        except Exception:
            pass
    return None


def obter_preco_atual(produto: str) -> Dict:
    """
    Obtém o preço atual de uma commodity.

    Args:
        produto: Nome do produto (Soja, Milho, Algodao, Ferro, Acucar)

    Returns:
        Dict com preco, data, fonte
    """
    hoje = datetime.now()

    # Tentar IPEA primeiro
    if produto in IPEA_SERIES:
        for codigo in IPEA_SERIES[produto]:
            df = _fetch_ipea_serie(codigo)
            if df is not None and not df.empty:
                ultimo = df.iloc[-1]
                return {
                    "produto": produto,
                    "preco": float(ultimo["preco"]),
                    "data": ultimo["data"].strftime("%Y-%m-%d"),
                    "fonte": f"IPEA/{codigo}"
                }

    # Tentar ComexStat via BigQuery
    heading = COMEXSTAT_HEADINGS.get(produto)
    if heading:
        df = _fetch_comexstat_bq_heading(produto, heading)
        if df is not None and not df.empty:
            ultimo = df.iloc[-1]
            return {
                "produto": produto,
                "preco": float(ultimo["preco"]),
                "data": ultimo["data"].strftime("%Y-%m-%d"),
                "fonte": "ComexStat/BQ"
            }

    # Tentar ComexStat (ultimo mes disponivel)
    df = _fetch_comexstat_precos(produto)
    if df is not None and not df.empty:
        ultimo = df.iloc[-1]
        return {
            "produto": produto,
            "preco": float(ultimo["preco"]),
            "data": ultimo["data"].strftime("%Y-%m-%d"),
            "fonte": "ComexStat/API"
        }

    # Fallback
    preco = _get_fallback_price(produto, hoje.year, hoje.month)
    return {
        "produto": produto,
        "preco": preco,
        "data": hoje.strftime("%Y-%m-%d"),
        "fonte": "fallback"
    }


def obter_indice_precos_agricolas() -> Optional[Dict]:
    """Obtém índice de preços agrícolas do BCB como proxy."""
    df = _fetch_bcb_serie(BCB_SERIES["IPA-Agropecuaria"])
    if df is not None and not df.empty:
        ultimo = df.iloc[-1]
        return {
            "indice": "IPA-Agropecuária",
            "valor": float(ultimo["preco"]),
            "data": ultimo["data"].strftime("%Y-%m-%d"),
            "fonte": "BCB"
        }
    return None


# Função de compatibilidade com plano_1.py
def extrair_precos_commodities():
    """Wrapper para manter compatibilidade com código existente."""
    return extrair_precos_commodities_v2()


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DO MÓDULO DE PREÇOS DE COMMODITIES")
    print("=" * 60)

    # Testar extração completa
    df = extrair_precos_commodities_v2()
    if df is not None:
        print(f"\nDataset: {len(df)} registros")
        print(df.groupby("produto").agg({"preco": ["count", "min", "max", "mean"]}))

    # Testar preço atual
    print("\n=== Preços Atuais ===")
    for produto in ["Soja", "Milho", "Algodao", "Ferro", "Acucar"]:
        info = obter_preco_atual(produto)
        print(f"{produto}: ${info['preco']:.2f} ({info['fonte']})")

    # Testar índice BCB
    print("\n=== Índice BCB ===")
    idx = obter_indice_precos_agricolas()
    if idx:
        print(f"{idx['indice']}: {idx['valor']:.2f} ({idx['fonte']})")
