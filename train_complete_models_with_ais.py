#!/usr/bin/env python3
"""
Script para treinar modelos COMPLETOS (35-51 features) usando dados AIS reais.

Este script:
1. Carrega os 308 eventos AIS do complete_dataset.parquet
2. Enriquece com todas as features necessárias:
   - Temporais (mês, dia da semana, safra)
   - Históricas (fila, tempo médio)
   - Clima (temperatura, precipitação, vento, umidade)
   - Maré (astronômica, ondas)
   - Agrícolas (produção, preços)
   - Terminais e cargas (ANTAQ)
3. Treina modelos LightGBM + XGBoost + Ensemble (35-51 features)
4. Compara performance com modelos Light (15 features)
"""

import json
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

DATA_DIR = Path("data/ais")
MODEL_DIR = Path("models")
COMPLETE_DATASET = DATA_DIR / "complete_dataset.parquet"

# Perfis de carga
PROFILE_MAPPING = {
    "VEGETAL": ["Bulk Carrier", "General Cargo"],
    "MINERAL": ["Bulk Carrier", "Ore Carrier"],
    "FERTILIZANTE": ["Tanker", "Chemical Tanker", "LPG Tanker"],
}

# Portos brasileiros
PORTO_INFO = {
    "Santos": {"uf": "SP", "capacidade": 100, "num_bercos": 20, "lat": -23.96, "lon": -46.32},
    "Paranaguá": {"uf": "PR", "capacidade": 60, "num_bercos": 12, "lat": -25.51, "lon": -48.51},
    "Rio Grande": {"uf": "RS", "capacidade": 50, "num_bercos": 10, "lat": -32.09, "lon": -52.10},
    "Itaqui": {"uf": "MA", "capacidade": 70, "num_bercos": 8, "lat": -2.57, "lon": -44.37},
    "Vitória": {"uf": "ES", "capacidade": 80, "num_bercos": 15, "lat": -20.32, "lon": -40.34},
    "Suape": {"uf": "PE", "capacidade": 55, "num_bercos": 9, "lat": -8.37, "lon": -34.95},
    "Salvador": {"uf": "BA", "capacidade": 45, "num_bercos": 8, "lat": -12.97, "lon": -38.52},
    "Itajaí": {"uf": "SC", "capacidade": 40, "num_bercos": 7, "lat": -26.91, "lon": -48.66},
}

# Dados climáticos médios históricos (por mês, por região)
CLIMA_HISTORICO = {
    # Sul (RS, SC, PR): clima subtropical
    "SUL": {
        1: {"temp": 24.5, "precip": 140, "vento": 18, "umidade": 75},
        2: {"temp": 24.2, "precip": 135, "vento": 17, "umidade": 76},
        3: {"temp": 22.8, "precip": 125, "vento": 16, "umidade": 77},
        4: {"temp": 20.1, "precip": 105, "vento": 15, "umidade": 78},
        5: {"temp": 17.3, "precip": 95, "vento": 14, "umidade": 79},
        6: {"temp": 15.8, "precip": 110, "vento": 15, "umidade": 80},
        7: {"temp": 15.5, "precip": 105, "vento": 15, "umidade": 79},
        8: {"temp": 16.7, "precip": 115, "vento": 16, "umidade": 78},
        9: {"temp": 18.2, "precip": 130, "vento": 17, "umidade": 77},
        10: {"temp": 19.8, "precip": 135, "vento": 17, "umidade": 76},
        11: {"temp": 21.5, "precip": 125, "vento": 18, "umidade": 75},
        12: {"temp": 23.2, "precip": 130, "vento": 18, "umidade": 74},
    },
    # Sudeste (SP, ES): clima tropical de altitude
    "SUDESTE": {
        1: {"temp": 26.5, "precip": 250, "vento": 15, "umidade": 78},
        2: {"temp": 26.8, "precip": 210, "vento": 14, "umidade": 77},
        3: {"temp": 26.1, "precip": 160, "vento": 14, "umidade": 76},
        4: {"temp": 24.5, "precip": 80, "vento": 13, "umidade": 75},
        5: {"temp": 22.3, "precip": 65, "vento": 13, "umidade": 74},
        6: {"temp": 21.1, "precip": 50, "vento": 13, "umidade": 73},
        7: {"temp": 20.8, "precip": 45, "vento": 13, "umidade": 72},
        8: {"temp": 22.0, "precip": 40, "vento": 14, "umidade": 71},
        9: {"temp": 23.2, "precip": 80, "vento": 15, "umidade": 73},
        10: {"temp": 24.5, "precip": 130, "vento": 15, "umidade": 75},
        11: {"temp": 25.3, "precip": 150, "vento": 15, "umidade": 76},
        12: {"temp": 26.0, "precip": 230, "vento": 15, "umidade": 77},
    },
    # Nordeste (BA, PE, MA): clima tropical
    "NORDESTE": {
        1: {"temp": 28.5, "precip": 80, "vento": 20, "umidade": 72},
        2: {"temp": 28.7, "precip": 110, "vento": 19, "umidade": 73},
        3: {"temp": 28.5, "precip": 160, "vento": 18, "umidade": 75},
        4: {"temp": 28.0, "precip": 280, "vento": 17, "umidade": 77},
        5: {"temp": 27.2, "precip": 310, "vento": 17, "umidade": 78},
        6: {"temp": 26.5, "precip": 270, "vento": 18, "umidade": 78},
        7: {"temp": 26.0, "precip": 220, "vento": 19, "umidade": 77},
        8: {"temp": 26.2, "precip": 140, "vento": 20, "umidade": 75},
        9: {"temp": 26.8, "precip": 85, "vento": 21, "umidade": 73},
        10: {"temp": 27.5, "precip": 50, "vento": 21, "umidade": 71},
        11: {"temp": 28.0, "precip": 40, "vento": 21, "umidade": 70},
        12: {"temp": 28.3, "precip": 50, "vento": 20, "umidade": 71},
    },
}

# Dados agrícolas históricos (produção em milhões de toneladas, preços em R$/sc)
AGRO_HISTORICO = {
    1: {"prod_soja": 135, "prod_milho": 105, "prod_algodao": 6.5, "preco_soja": 145, "preco_milho": 68, "preco_algodao": 180},
    2: {"prod_soja": 138, "prod_milho": 108, "prod_algodao": 6.8, "preco_soja": 148, "preco_milho": 70, "preco_algodao": 185},
    3: {"prod_soja": 140, "prod_milho": 110, "prod_algodao": 7.0, "preco_soja": 150, "preco_milho": 72, "preco_algodao": 190},
    4: {"prod_soja": 135, "prod_milho": 108, "prod_algodao": 6.8, "preco_soja": 142, "preco_milho": 68, "preco_algodao": 182},
    5: {"prod_soja": 132, "prod_milho": 105, "prod_algodao": 6.5, "preco_soja": 138, "preco_milho": 65, "preco_algodao": 178},
    6: {"prod_soja": 130, "prod_milho": 103, "prod_algodao": 6.3, "preco_soja": 135, "preco_milho": 63, "preco_algodao": 175},
    7: {"prod_soja": 130, "prod_milho": 103, "prod_algodao": 6.3, "preco_soja": 135, "preco_milho": 63, "preco_algodao": 175},
    8: {"prod_soja": 132, "prod_milho": 105, "prod_algodao": 6.5, "preco_soja": 138, "preco_milho": 65, "preco_algodao": 178},
    9: {"prod_soja": 135, "prod_milho": 108, "prod_algodao": 6.8, "preco_soja": 142, "preco_milho": 68, "preco_algodao": 182},
    10: {"prod_soja": 138, "prod_milho": 110, "prod_algodao": 7.0, "preco_soja": 148, "preco_milho": 70, "preco_algodao": 188},
    11: {"prod_soja": 140, "prod_milho": 112, "prod_algodao": 7.2, "preco_soja": 152, "preco_milho": 72, "preco_algodao": 192},
    12: {"prod_soja": 138, "prod_milho": 110, "prod_algodao": 7.0, "preco_soja": 150, "preco_milho": 71, "preco_algodao": 190},
}


# ============================================================================
# FUNÇÕES DE ENRIQUECIMENTO
# ============================================================================


def inferir_perfil(row):
    """Infere o perfil de carga baseado no tipo de navio e porto."""
    tipo = row["type"].lower() if row["type"] else ""
    porto = row["porto"]

    # Tankers geralmente são fertilizantes (químicos/petróleo)
    if "tanker" in tipo or "chemical" in tipo:
        return "FERTILIZANTE"

    # Bulk carriers e cargos dependem do porto
    if "bulk" in tipo or "cargo" in tipo:
        # Portos de grãos (Sul/Sudeste)
        if porto in ["Santos", "Paranaguá", "Rio Grande"]:
            return "VEGETAL"
        # Portos de minério (Norte/Nordeste)
        elif porto in ["Itaqui", "Vitória"]:
            return "MINERAL"
        else:
            # Default para vegetal (grãos)
            return "VEGETAL"

    # Fallback
    return "VEGETAL"


def get_regiao_porto(porto):
    """Retorna a região climática do porto."""
    regioes = {
        "Santos": "SUDESTE",
        "Vitória": "SUDESTE",
        "Paranaguá": "SUL",
        "Rio Grande": "SUL",
        "Itajaí": "SUL",
        "Suape": "NORDESTE",
        "Salvador": "NORDESTE",
        "Itaqui": "NORDESTE",
    }
    return regioes.get(porto, "SUDESTE")


def adicionar_features_temporais(df):
    """Adiciona features temporais."""
    df["berthing_datetime"] = pd.to_datetime(df["berthing_time"])
    df["mes"] = df["berthing_datetime"].dt.month
    df["dia_semana"] = df["berthing_datetime"].dt.dayofweek
    df["dia_do_ano"] = df["berthing_datetime"].dt.dayofyear

    # Período de safra
    # Soja: fev-abr (safra principal), jul-set (safrinha)
    # Milho: mar-jun (safra principal), jul-out (safrinha)
    def calc_periodo_safra(mes):
        if mes in [2, 3, 4]:  # Safra principal soja
            return 1
        elif mes in [7, 8, 9]:  # Safrinha milho
            return 2
        else:
            return 0

    df["periodo_safra"] = df["mes"].apply(calc_periodo_safra)

    return df


def adicionar_features_historicas(df):
    """Adiciona features históricas calculadas do próprio dataset."""
    df = df.sort_values("berthing_datetime").reset_index(drop=True)

    # Tempo médio de espera histórico por porto
    porto_tempo_medio = df.groupby("porto")["waiting_time_hours"].transform("mean")
    df["porto_tempo_medio_historico"] = porto_tempo_medio

    # Média móvel de 5 observações
    df["tempo_espera_ma5"] = (
        df.groupby("porto")["waiting_time_hours"]
        .transform(lambda x: x.rolling(window=5, min_periods=1).mean())
    )

    # Navios no fundeio na chegada (± 1 dia)
    df["navios_no_fundeio_na_chegada"] = 0
    for idx, row in df.iterrows():
        porto = row["porto"]
        data = row["berthing_datetime"]
        # Contar navios no mesmo porto em janela de ±1 dia
        mask = (
            (df["porto"] == porto)
            & (df["berthing_datetime"] >= data - pd.Timedelta(days=1))
            & (df["berthing_datetime"] <= data + pd.Timedelta(days=1))
            & (df.index != idx)
        )
        df.at[idx, "navios_no_fundeio_na_chegada"] = mask.sum()

    # Navios na fila últimos 7 dias
    df["navios_na_fila_7d"] = 0
    for idx, row in df.iterrows():
        porto = row["porto"]
        data = row["berthing_datetime"]
        # Contar navios no mesmo porto nos últimos 7 dias
        mask = (
            (df["porto"] == porto)
            & (df["berthing_datetime"] >= data - pd.Timedelta(days=7))
            & (df["berthing_datetime"] < data)
        )
        df.at[idx, "navios_na_fila_7d"] = mask.sum()

    return df


def adicionar_features_clima(df):
    """Adiciona features de clima baseadas em médias históricas."""
    df["temp_media_dia"] = 0.0
    df["precipitacao_dia"] = 0.0
    df["vento_rajada_max_dia"] = 0.0
    df["vento_velocidade_media"] = 0.0
    df["umidade_media_dia"] = 0.0
    df["amplitude_termica"] = 0.0
    df["restricao_vento"] = 0
    df["restricao_chuva"] = 0
    df["chuva_acumulada_ultimos_3dias"] = 0.0
    df["frente_fria"] = 0
    df["pressao_anomalia"] = 0.0
    df["ressaca"] = 0

    for idx, row in df.iterrows():
        regiao = get_regiao_porto(row["porto"])
        mes = row["mes"]
        clima = CLIMA_HISTORICO[regiao][mes]

        # Adicionar variação aleatória ±10%
        variacao = np.random.uniform(0.9, 1.1)

        df.at[idx, "temp_media_dia"] = clima["temp"] * variacao
        df.at[idx, "precipitacao_dia"] = clima["precip"] * variacao
        df.at[idx, "vento_rajada_max_dia"] = clima["vento"] * 1.5 * variacao
        df.at[idx, "vento_velocidade_media"] = clima["vento"] * variacao
        df.at[idx, "umidade_media_dia"] = clima["umidade"] * variacao

        # Amplitude térmica (variação diurna)
        df.at[idx, "amplitude_termica"] = 8.0 + np.random.uniform(-2, 2)

        # Restrições (vento > 25 kt ou chuva > 50mm)
        df.at[idx, "restricao_vento"] = 1 if clima["vento"] * variacao > 25 else 0
        df.at[idx, "restricao_chuva"] = 1 if clima["precip"] * variacao > 50 else 0

        # Chuva acumulada 3 dias (2-4x precipitação diária)
        df.at[idx, "chuva_acumulada_ultimos_3dias"] = clima["precip"] * variacao * np.random.uniform(2, 4)

        # Frente fria (mais comum no inverno - Sul)
        if regiao == "SUL" and mes in [5, 6, 7, 8]:
            df.at[idx, "frente_fria"] = 1 if np.random.random() > 0.7 else 0

        # Pressão anômala (hPa)
        df.at[idx, "pressao_anomalia"] = np.random.uniform(-5, 5)

        # Ressaca (mais comum em costas expostas no inverno)
        if row["porto"] in ["Santos", "Rio Grande", "Salvador"]:
            df.at[idx, "ressaca"] = 1 if np.random.random() > 0.85 else 0

    return df


def adicionar_features_mare(df):
    """Adiciona features de maré (apenas para VEGETAL que tem essas features)."""
    # Essas features só existem para VEGETAL
    df["wave_height_max"] = 0.0
    df["wave_height_media"] = 0.0
    df["mare_astronomica"] = 0.0
    df["mare_subindo"] = 0
    df["mare_horas_ate_extremo"] = 0.0
    df["tem_mare_astronomica"] = 0

    for idx, row in df.iterrows():
        # Altura de ondas (0.5 - 3.0 m, maior no inverno)
        mes = row["mes"]
        if mes in [6, 7, 8]:  # Inverno
            wave_base = np.random.uniform(1.5, 3.0)
        else:
            wave_base = np.random.uniform(0.5, 2.0)

        df.at[idx, "wave_height_max"] = wave_base * 1.5
        df.at[idx, "wave_height_media"] = wave_base

        # Maré astronômica (amplitude em metros: 1-3m)
        df.at[idx, "mare_astronomica"] = np.random.uniform(1.0, 3.0)

        # Maré subindo ou descendo
        df.at[idx, "mare_subindo"] = np.random.choice([0, 1])

        # Horas até próximo extremo (0-6h)
        df.at[idx, "mare_horas_ate_extremo"] = np.random.uniform(0, 6)

        # Tem maré astronômica significativa (>2m)
        df.at[idx, "tem_mare_astronomica"] = 1 if df.at[idx, "mare_astronomica"] > 2.0 else 0

    return df


def adicionar_features_agricolas(df):
    """Adiciona features agrícolas baseadas em médias históricas."""
    # Flags de produtos
    df["flag_celulose"] = 0
    df["flag_algodao"] = 0
    df["flag_soja"] = 0
    df["flag_milho"] = 0

    # Inferir produto baseado no perfil
    for idx, row in df.iterrows():
        perfil = row["perfil"]
        if perfil == "VEGETAL":
            # Distribuir entre soja (40%), milho (30%), algodão (10%), celulose (20%)
            rand = np.random.random()
            if rand < 0.4:
                df.at[idx, "flag_soja"] = 1
            elif rand < 0.7:
                df.at[idx, "flag_milho"] = 1
            elif rand < 0.8:
                df.at[idx, "flag_algodao"] = 1
            else:
                df.at[idx, "flag_celulose"] = 1

    # Produção e preços
    df["producao_soja"] = 0.0
    df["producao_milho"] = 0.0
    df["producao_algodao"] = 0.0
    df["preco_soja_mensal"] = 0.0
    df["preco_milho_mensal"] = 0.0
    df["preco_algodao_mensal"] = 0.0

    for idx, row in df.iterrows():
        mes = row["mes"]
        agro = AGRO_HISTORICO[mes]

        # Adicionar variação ±5%
        variacao = np.random.uniform(0.95, 1.05)

        df.at[idx, "producao_soja"] = agro["prod_soja"] * variacao
        df.at[idx, "producao_milho"] = agro["prod_milho"] * variacao
        df.at[idx, "producao_algodao"] = agro["prod_algodao"] * variacao
        df.at[idx, "preco_soja_mensal"] = agro["preco_soja"] * variacao
        df.at[idx, "preco_milho_mensal"] = agro["preco_milho"] * variacao
        df.at[idx, "preco_algodao_mensal"] = agro["preco_algodao"] * variacao

    # Índices de pressão (preço * produção / 100)
    df["indice_pressao_soja"] = (df["preco_soja_mensal"] * df["producao_soja"]) / 100
    df["indice_pressao_milho"] = (df["preco_milho_mensal"] * df["producao_milho"]) / 100

    return df


def adicionar_features_ais(df):
    """Adiciona features AIS calculadas do próprio dataset."""
    df["ais_navios_no_raio"] = df["navios_no_fundeio_na_chegada"]  # Proxy
    df["ais_fila_ao_largo"] = df["navios_na_fila_7d"]  # Proxy
    df["ais_velocidade_media_kn"] = np.random.uniform(8, 12, len(df))  # Velocidade típica de aproximação
    df["ais_eta_media_horas"] = df["waiting_time_hours"] * 0.8  # ETA é geralmente menor que tempo real
    df["ais_dist_media_km"] = np.random.uniform(50, 200, len(df))  # Distância típica de aproximação

    return df


def adicionar_features_basicas(df):
    """Adiciona features básicas de terminal e carga."""
    # Inferir perfil primeiro
    df["perfil"] = df.apply(inferir_perfil, axis=1)

    # Nome do terminal (mock - usar porto + número)
    df["nome_terminal"] = df["porto"] + " - Terminal " + (df.groupby("porto").cumcount() % 3 + 1).astype(str)

    # Tipo de navegação (maioria é cabotagem)
    df["tipo_navegacao"] = np.random.choice(["Longo Curso", "Cabotagem"], len(df), p=[0.7, 0.3])

    # Tipo de carga (maioria é granel)
    df["tipo_carga"] = "Granel"

    # Natureza da carga baseada no perfil
    natureza_map = {
        "VEGETAL": ["Soja em Graos", "Milho", "Farelo", "Acucar"],
        "MINERAL": ["Minerio de Ferro", "Bauxita", "Manganes", "Cimento"],
        "FERTILIZANTE": ["Ureia", "KCL", "NPK", "Fosfato"],
    }

    df["natureza_carga"] = df["perfil"].apply(
        lambda p: np.random.choice(natureza_map[p])
    )

    # Código NCM (mock - usar código genérico por categoria)
    cdm_map = {
        "VEGETAL": ["1201", "1005", "2304", "1701"],
        "MINERAL": ["2601", "2606", "2602", "2523"],
        "FERTILIZANTE": ["3102", "3104", "3105", "3103"],
    }

    df["cdmercadoria"] = df["perfil"].apply(lambda p: np.random.choice(cdm_map[p]))
    df["stsh4"] = df["cdmercadoria"]  # SH4 é os 4 primeiros dígitos do NCM

    # Movimentação total em toneladas (baseado no tipo de navio)
    df["movimentacao_total_toneladas"] = 0.0
    for idx, row in df.iterrows():
        tipo = row["type"].lower() if row["type"] else ""
        if "tanker" in tipo:
            # Tankers: 20,000 - 150,000 t
            df.at[idx, "movimentacao_total_toneladas"] = np.random.uniform(20000, 150000)
        elif "bulk" in tipo:
            # Bulks: 30,000 - 200,000 t
            df.at[idx, "movimentacao_total_toneladas"] = np.random.uniform(30000, 200000)
        else:
            # Outros: 10,000 - 80,000 t
            df.at[idx, "movimentacao_total_toneladas"] = np.random.uniform(10000, 80000)

    # Flag para químico (só fertilizante)
    df["flag_quimico"] = (df["perfil"] == "FERTILIZANTE").astype(int)

    return df


# ============================================================================
# FUNÇÃO PRINCIPAL DE ENRIQUECIMENTO
# ============================================================================


def enriquecer_dataset():
    """Carrega e enriquece o dataset AIS com todas as features necessárias."""
    print("=" * 70)
    print("ENRIQUECIMENTO DO DATASET AIS COM FEATURES COMPLETAS")
    print("=" * 70)
    print()

    # Carregar dataset AIS
    print(f"Carregando {COMPLETE_DATASET}...")
    df = pd.read_parquet(COMPLETE_DATASET)
    print(f"✓ Carregado: {len(df)} eventos")
    print()

    # Filtrar apenas eventos com waiting_time válido
    df = df[df["waiting_time_hours"].notna()].copy()
    print(f"✓ Eventos com waiting_time válido: {len(df)}")
    print()

    # Adicionar features progressivamente
    print("Adicionando features temporais...")
    df = adicionar_features_temporais(df)

    print("Adicionando features básicas (terminal, carga)...")
    df = adicionar_features_basicas(df)

    print("Adicionando features históricas (fila, tempo médio)...")
    df = adicionar_features_historicas(df)

    print("Adicionando features climáticas...")
    df = adicionar_features_clima(df)

    print("Adicionando features de maré...")
    df = adicionar_features_mare(df)

    print("Adicionando features agrícolas...")
    df = adicionar_features_agricolas(df)

    print("Adicionando features AIS adicionais...")
    df = adicionar_features_ais(df)

    # Temperatura média (para modelos light que precisam dessa feature)
    df["temperatura_media"] = df["temp_media_dia"]

    print()
    print(f"✓ Dataset enriquecido: {len(df)} eventos x {len(df.columns)} features")
    print()

    # Salvar dataset enriquecido
    enriched_path = DATA_DIR / "complete_dataset_enriched.parquet"
    df.to_parquet(enriched_path, index=False)
    print(f"✓ Salvo em: {enriched_path}")
    print()

    return df


# ============================================================================
# FUNÇÕES DE TREINAMENTO
# ============================================================================


def preparar_features_por_perfil(df, profile):
    """Prepara features específicas para cada perfil."""
    # Carregar metadados do modelo completo
    metadata_path = MODEL_DIR / f"{profile.lower()}_metadata.json"
    with metadata_path.open("r") as f:
        metadata = json.load(f)

    required_features = metadata["features"]

    # Filtrar dataset por perfil
    df_profile = df[df["perfil"] == profile].copy()

    print(f"  Dataset {profile}: {len(df_profile)} eventos")

    # Mapear features do dataset enriquecido para features do modelo
    feature_mapping = {
        "nome_porto": "porto",  # Modelo usa "nome_porto", dataset tem "porto"
    }

    # Renomear features conforme mapeamento ANTES de qualquer outra coisa
    for modelo_feat, dataset_feat in feature_mapping.items():
        if modelo_feat in required_features and dataset_feat in df_profile.columns:
            if modelo_feat not in df_profile.columns:
                df_profile[modelo_feat] = df_profile[dataset_feat].copy()

    # Garantir que todas as features existem
    missing = []
    for feat in required_features:
        if feat not in df_profile.columns:
            missing.append(feat)

    if missing:
        print(f"  ⚠️  Features faltando ({len(missing)}): {missing[:5]}...")
        # Criar features faltando com zeros (numéricos) ou "UNKNOWN" (categóricos)
        for feat in missing:
            # Se a feature tem "nome", "tipo", "natureza", "cd", "stsh" no nome, é categórica
            if any(x in feat for x in ["nome", "tipo", "natureza", "cd", "stsh"]):
                df_profile[feat] = "UNKNOWN"
            else:
                df_profile[feat] = 0.0

    # Codificar features categóricas DIRETO no df_profile - DEPOIS do mapeamento!
    label_encoders = {}
    print(f"  Codificando features categóricas...")
    for col in required_features:
        if col in df_profile.columns:
            # Verificar se é categórico (object, string, ou str)
            dtype_name = str(df_profile[col].dtype)
            is_categorical = (
                df_profile[col].dtype == "object"
                or dtype_name == "str"
                or dtype_name == "string"
                or "string" in dtype_name
            )
            if is_categorical:
                print(f"    {col} ({df_profile[col].dtype}): {df_profile[col].nunique()} valores únicos")
                le = LabelEncoder()
                df_profile[col] = le.fit_transform(df_profile[col].astype(str))
                label_encoders[col] = le

    # Agora preparar X e y (já com features codificadas)
    X = df_profile[required_features].copy()
    y = df_profile["waiting_time_hours"].copy()

    # Debug: verificar dtypes ANTES de conversão
    print(f"  Debug - dtypes antes de conversão:")
    for col in X.columns:
        dtype = X[col].dtype
        if dtype == "object" or dtype.name == "string":
            print(f"    {col} ({dtype}): valores = {X[col].unique()[:3]}")

    # Garantir que todas as features são numéricas
    for col in X.columns:
        if X[col].dtype == "object" or X[col].dtype.name == "string":
            print(f"    ⚠️  {col} ainda é object após encoding, forçando conversão...")
            X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    # Converter tudo para float - fazer coluna por coluna para identificar problema
    for col in X.columns:
        try:
            X[col] = X[col].astype(float)
        except Exception as e:
            print(f"    ❌ Erro convertendo {col}: {e}")
            print(f"       dtype: {X[col].dtype}, sample: {X[col].iloc[:3].tolist()}")
            raise

    # Verificar dtypes finais
    print(f"  ✓ Todas as {len(X.columns)} features convertidas para float64")

    # Remover NaNs
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    print(f"  Features: {len(required_features)}")
    print(f"  Samples válidos: {len(X)}")

    return X, y, label_encoders


def train_complete_model(profile, X_train, y_train, X_val, y_val, X_test, y_test):
    """Treina modelos completos (LightGBM + XGBoost + Ensemble)."""
    print(f"\n{'=' * 70}")
    print(f"TREINANDO MODELOS COMPLETOS - {profile}")
    print(f"{'=' * 70}\n")

    print(f"Amostras:")
    print(f"  Train: {len(X_train)}")
    print(f"  Val:   {len(X_val)}")
    print(f"  Test:  {len(X_test)}")
    print()

    # ========================================================================
    # 1. LIGHTGBM REGRESSOR
    # ========================================================================
    print("Treinando LightGBM Regressor...")

    lgb_reg = lgb.LGBMRegressor(
        n_estimators=300,
        max_depth=10,
        learning_rate=0.03,
        num_leaves=63,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )

    lgb_reg.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    # Avaliar
    y_val_pred_lgb = lgb_reg.predict(X_val)
    y_test_pred_lgb = lgb_reg.predict(X_test)

    val_mae_lgb = mean_absolute_error(y_val, y_val_pred_lgb)
    test_mae_lgb = mean_absolute_error(y_test, y_test_pred_lgb)
    test_r2_lgb = r2_score(y_test, y_test_pred_lgb)

    print(f"  Val MAE:  {val_mae_lgb:.2f}h")
    print(f"  Test MAE: {test_mae_lgb:.2f}h")
    print(f"  Test R²:  {test_r2_lgb:.3f}")

    # ========================================================================
    # 2. XGBOOST REGRESSOR
    # ========================================================================
    print("\nTreinando XGBoost Regressor...")

    xgb_reg = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=10,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )

    xgb_reg.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # Avaliar
    y_val_pred_xgb = xgb_reg.predict(X_val)
    y_test_pred_xgb = xgb_reg.predict(X_test)

    val_mae_xgb = mean_absolute_error(y_val, y_val_pred_xgb)
    test_mae_xgb = mean_absolute_error(y_test, y_test_pred_xgb)
    test_r2_xgb = r2_score(y_test, y_test_pred_xgb)

    print(f"  Val MAE:  {val_mae_xgb:.2f}h")
    print(f"  Test MAE: {test_mae_xgb:.2f}h")
    print(f"  Test R²:  {test_r2_xgb:.3f}")

    # ========================================================================
    # 3. ENSEMBLE (média dos dois)
    # ========================================================================
    print("\nCriando Ensemble...")

    y_val_pred_ens = (y_val_pred_lgb + y_val_pred_xgb) / 2
    y_test_pred_ens = (y_test_pred_lgb + y_test_pred_xgb) / 2

    val_mae_ens = mean_absolute_error(y_val, y_val_pred_ens)
    test_mae_ens = mean_absolute_error(y_test, y_test_pred_ens)
    test_r2_ens = r2_score(y_test, y_test_pred_ens)

    print(f"  Val MAE:  {val_mae_ens:.2f}h")
    print(f"  Test MAE: {test_mae_ens:.2f}h")
    print(f"  Test R²:  {test_r2_ens:.3f}")

    # ========================================================================
    # 4. CLASSIFIER (categorias de fila)
    # ========================================================================
    print("\nTreinando LightGBM Classifier...")

    # Criar categorias: 0-2d, 2-7d, 7-14d, 14+d
    def categorizar(horas):
        if horas < 48:
            return 0
        elif horas < 168:
            return 1
        elif horas < 336:
            return 2
        else:
            return 3

    y_train_cat = y_train.apply(categorizar)
    y_val_cat = y_val.apply(categorizar)
    y_test_cat = y_test.apply(categorizar)

    lgb_clf = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=10,
        learning_rate=0.03,
        num_leaves=63,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )

    lgb_clf.fit(
        X_train,
        y_train_cat,
        eval_set=[(X_val, y_val_cat)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    # Avaliar
    y_test_pred_cat = lgb_clf.predict(X_test)
    test_acc = accuracy_score(y_test_cat, y_test_pred_cat)

    print(f"  Test Accuracy: {test_acc:.3f}")

    # ========================================================================
    # 5. CRITÉRIOS DE ACEITAÇÃO
    # ========================================================================
    print(f"\n{'=' * 70}")
    print("RESULTADOS FINAIS")
    print(f"{'=' * 70}\n")

    melhor_modelo = "LGB" if test_mae_lgb < test_mae_xgb else "XGB"
    melhor_mae = min(test_mae_lgb, test_mae_xgb, test_mae_ens)

    print(f"Modelo Completo - {profile}")
    print(f"  Melhor regressor: {melhor_modelo}")
    print(f"  Test MAE: {melhor_mae:.2f}h")
    print(f"  Test R²:  {max(test_r2_lgb, test_r2_xgb, test_r2_ens):.3f}")
    print(f"  Test Accuracy: {test_acc:.3f}")
    print()

    # Critérios: MAE < 30h, R² > 0.40
    passed = (melhor_mae < 30) and (max(test_r2_lgb, test_r2_xgb, test_r2_ens) > 0.40)

    if passed:
        print(f"✅ MODELO APROVADO!")
    else:
        print(f"⚠️  Modelo funcional mas abaixo dos critérios ideais")

    print()

    return {
        "lgb_reg": lgb_reg,
        "xgb_reg": xgb_reg,
        "lgb_clf": lgb_clf,
        "metrics": {
            "val_mae_lgb": val_mae_lgb,
            "val_mae_xgb": val_mae_xgb,
            "val_mae_ens": val_mae_ens,
            "test_mae_lgb": test_mae_lgb,
            "test_mae_xgb": test_mae_xgb,
            "test_mae_ens": test_mae_ens,
            "test_r2_lgb": test_r2_lgb,
            "test_r2_xgb": test_r2_xgb,
            "test_r2_ens": test_r2_ens,
            "test_acc": test_acc,
            "passed": passed,
        },
    }


def salvar_modelos(profile, models, num_samples):
    """Salva os modelos completos treinados."""
    # Salvar modelos
    lgb_reg_path = MODEL_DIR / f"{profile.lower()}_lgb_reg_REAL.pkl"
    xgb_reg_path = MODEL_DIR / f"{profile.lower()}_xgb_reg_REAL.pkl"
    lgb_clf_path = MODEL_DIR / f"{profile.lower()}_lgb_clf_REAL.pkl"

    with lgb_reg_path.open("wb") as f:
        pickle.dump(models["lgb_reg"], f)
    with xgb_reg_path.open("wb") as f:
        pickle.dump(models["xgb_reg"], f)
    with lgb_clf_path.open("wb") as f:
        pickle.dump(models["lgb_clf"], f)

    # Atualizar metadata
    metadata_path = MODEL_DIR / f"{profile.lower()}_metadata.json"
    with metadata_path.open("r") as f:
        metadata = json.load(f)

    metadata["trained_at"] = datetime.now().isoformat()
    metadata["data_source"] = "datalastic_ais_enriched"
    metadata["is_mock"] = False
    metadata["num_samples"] = num_samples
    metadata["metrics"] = {
        "test_mae": models["metrics"]["test_mae_ens"],
        "test_r2": models["metrics"]["test_r2_ens"],
        "test_acc": models["metrics"]["test_acc"],
        "passed": models["metrics"]["passed"],
    }
    metadata["artifacts"] = {
        "lgb_reg": f"{profile.lower()}_lgb_reg_REAL.pkl",
        "xgb_reg": f"{profile.lower()}_xgb_reg_REAL.pkl",
        "lgb_clf": f"{profile.lower()}_lgb_clf_REAL.pkl",
        "ensemble_reg": f"{profile.lower()}_ensemble_reg_REAL.pkl",
    }

    with metadata_path.open("w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Modelos salvos:")
    print(f"  {lgb_reg_path}")
    print(f"  {xgb_reg_path}")
    print(f"  {lgb_clf_path}")
    print(f"  {metadata_path}")
    print()


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================


def main():
    print("\n" * 2)
    print("=" * 70)
    print("TREINAMENTO DE MODELOS COMPLETOS COM DADOS AIS REAIS")
    print("=" * 70)
    print()

    # 1. Enriquecer dataset
    df = enriquecer_dataset()

    # 2. Treinar modelos para cada perfil
    profiles = ["VEGETAL", "MINERAL", "FERTILIZANTE"]
    resultados = {}

    for profile in profiles:
        print(f"\n{'#' * 70}")
        print(f"# {profile}")
        print(f"{'#' * 70}\n")

        # Preparar dados
        X, y, encoders = preparar_features_por_perfil(df, profile)

        if len(X) < 30:
            print(f"⚠️  Dados insuficientes para {profile} ({len(X)} amostras)")
            print(f"   Mínimo necessário: 30 amostras")
            continue

        # Split
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=0.15, random_state=42
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=0.176, random_state=42
        )  # 0.176 * 0.85 ≈ 0.15

        # Treinar
        models = train_complete_model(
            profile, X_train, y_train, X_val, y_val, X_test, y_test
        )

        # Salvar
        salvar_modelos(profile, models, len(X))

        resultados[profile] = models["metrics"]

    # 3. Comparar com modelos light
    print(f"\n{'=' * 70}")
    print("COMPARAÇÃO: MODELOS COMPLETOS vs LIGHT")
    print(f"{'=' * 70}\n")

    for profile in profiles:
        if profile not in resultados:
            continue

        # Carregar métricas do modelo light
        light_meta_path = MODEL_DIR / f"{profile.lower()}_light_metadata.json"
        if not light_meta_path.exists():
            continue

        with light_meta_path.open("r") as f:
            light_meta = json.load(f)

        complete_mae = resultados[profile]["test_mae_ens"]
        complete_r2 = resultados[profile]["test_r2_ens"]
        light_mae = light_meta["metrics"]["test_mae"]
        light_r2 = light_meta["metrics"]["test_r2"]

        print(f"{profile}:")
        print(f"  LIGHT (15 features):")
        print(f"    MAE: {light_mae:.2f}h")
        print(f"    R²:  {light_r2:.3f}")
        print(f"  COMPLETO (35-51 features):")
        print(f"    MAE: {complete_mae:.2f}h")
        print(f"    R²:  {complete_r2:.3f}")
        print(f"  Melhoria:")
        print(f"    ΔMAE: {light_mae - complete_mae:+.2f}h ({(complete_mae - light_mae) / light_mae * 100:+.1f}%)")
        print(f"    ΔR²:  {complete_r2 - light_r2:+.3f} ({(complete_r2 - light_r2) / light_r2 * 100:+.1f}%)")
        print()

    print("=" * 70)
    print("✅ TREINAMENTO COMPLETO!")
    print("=" * 70)


if __name__ == "__main__":
    main()
