#!/usr/bin/env python3
"""
Sistema de Previsão de Fila Portuária - Versão Enriquecida

Este módulo fornece predição de tempo de espera usando modelos completos
ou light, com enriquecimento automático de features a partir de dados básicos
do scraping.

Não requer API AIS em tempo real - usa apenas:
- Dados do scraping (IMO, tipo, porto, ETA)
- API Open-Meteo (gratuita) para clima
- Tabelas pré-carregadas (safra, preços)
- Histórico de lineups (já coletado)
"""

import json
import pickle
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

# ============================================================================
# CORES PARA TERMINAL (User-Friendly)
# ============================================================================

class Colors:
    """Cores ANSI para terminal - User Friendly"""
    # Cores básicas
    GREEN = '\033[92m'      # Sucesso
    YELLOW = '\033[93m'     # Aviso
    RED = '\033[91m'        # Erro
    BLUE = '\033[94m'       # Informação
    CYAN = '\033[96m'       # Destaque
    MAGENTA = '\033[95m'    # Especial
    WHITE = '\033[97m'      # Normal
    BOLD = '\033[1m'        # Negrito
    RESET = '\033[0m'       # Reset

    @staticmethod
    def success(text):
        """Texto de sucesso (verde)"""
        return f"{Colors.GREEN}{text}{Colors.RESET}"

    @staticmethod
    def warning(text):
        """Texto de aviso (amarelo)"""
        return f"{Colors.YELLOW}{text}{Colors.RESET}"

    @staticmethod
    def error(text):
        """Texto de erro (vermelho)"""
        return f"{Colors.RED}{text}{Colors.RESET}"

    @staticmethod
    def info(text):
        """Texto informativo (azul)"""
        return f"{Colors.BLUE}{text}{Colors.RESET}"

    @staticmethod
    def highlight(text):
        """Texto destacado (ciano)"""
        return f"{Colors.CYAN}{text}{Colors.RESET}"

    @staticmethod
    def bold(text):
        """Texto em negrito"""
        return f"{Colors.BOLD}{text}{Colors.RESET}"

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

MODEL_DIR = Path("models")
DATA_DIR = Path("data")
LINEUP_HISTORY = Path("lineups_previstos/lineup_history.parquet")

# Informações dos portos
PORTOS = {
    "Santos": {"uf": "SP", "regiao": "SUDESTE", "capacidade": 100, "num_bercos": 20, "lat": -23.96, "lon": -46.32},
    "Paranaguá": {"uf": "PR", "regiao": "SUL", "capacidade": 60, "num_bercos": 12, "lat": -25.51, "lon": -48.51},
    "Rio Grande": {"uf": "RS", "regiao": "SUL", "capacidade": 50, "num_bercos": 10, "lat": -32.09, "lon": -52.10},
    "Itaqui": {"uf": "MA", "regiao": "NORDESTE", "capacidade": 70, "num_bercos": 8, "lat": -2.57, "lon": -44.37},
    "Vitória": {"uf": "ES", "regiao": "SUDESTE", "capacidade": 80, "num_bercos": 15, "lat": -20.32, "lon": -40.34},
    "Suape": {"uf": "PE", "regiao": "NORDESTE", "capacidade": 55, "num_bercos": 9, "lat": -8.37, "lon": -34.95},
    "Salvador": {"uf": "BA", "regiao": "NORDESTE", "capacidade": 45, "num_bercos": 8, "lat": -12.97, "lon": -38.52},
    "Itajaí": {"uf": "SC", "regiao": "SUL", "capacidade": 40, "num_bercos": 7, "lat": -26.91, "lon": -48.66},
}

# Dados agrícolas históricos (médias mensais)
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

# Categorias de tempo de espera
CATEGORIAS = {
    0: "0-2 dias (Rápido)",
    1: "2-7 dias (Normal)",
    2: "7-14 dias (Longo)",
    3: "14+ dias (Muito Longo)",
}


# ============================================================================
# CLASSE PRINCIPAL
# ============================================================================


class EnrichedPredictor:
    """
    Preditor enriquecido que usa modelos completos (quando aplicável) ou light.

    Enriquece automaticamente os dados do scraping com features calculadas:
    - Clima (API Open-Meteo gratuita)
    - Safra e preços (tabelas pré-carregadas)
    - Fila histórica (lineup_history.parquet)
    - Features AIS estimadas (médias)
    """

    def __init__(self):
        """Inicializa o preditor carregando modelos e dados históricos."""
        self.models = self._load_models()
        self.lineup_history = self._load_lineup_history()
        self.porto_stats = self._calculate_porto_stats()

        print(Colors.success("[OK] EnrichedPredictor inicializado com sucesso"))
        print(Colors.info(f"   Modelos carregados: {list(self.models.keys())}"))
        print(Colors.info(f"   Historico de lineups: {len(self.lineup_history)} registros"))

    def _load_models(self) -> Dict:
        """Carrega modelos completos e light para cada perfil."""
        models = {}

        for profile in ["vegetal", "mineral", "fertilizante"]:
            profile_models = {}

            # Metadata
            meta_path = MODEL_DIR / f"{profile}_metadata.json"
            light_meta_path = MODEL_DIR / f"{profile}_light_metadata.json"

            with meta_path.open("r") as f:
                profile_models["complete_meta"] = json.load(f)

            with light_meta_path.open("r") as f:
                profile_models["light_meta"] = json.load(f)

            # Modelos completos (se existirem versões REAL)
            xgb_path = MODEL_DIR / f"{profile}_xgb_reg_REAL.pkl"
            lgb_clf_path = MODEL_DIR / f"{profile}_lgb_clf_REAL.pkl"

            if xgb_path.exists():
                with xgb_path.open("rb") as f:
                    profile_models["complete_reg"] = pickle.load(f)
                with lgb_clf_path.open("rb") as f:
                    profile_models["complete_clf"] = pickle.load(f)
                profile_models["has_complete"] = True
            else:
                profile_models["has_complete"] = False

            # Modelos light
            light_reg_path = MODEL_DIR / f"{profile}_light_lgb_reg.pkl"
            light_clf_path = MODEL_DIR / f"{profile}_light_lgb_clf.pkl"

            with light_reg_path.open("rb") as f:
                profile_models["light_reg"] = pickle.load(f)
            with light_clf_path.open("rb") as f:
                profile_models["light_clf"] = pickle.load(f)

            models[profile.upper()] = profile_models

        return models

    def _load_lineup_history(self) -> pd.DataFrame:
        """Carrega histórico de lineups (se existir)."""
        if LINEUP_HISTORY.exists():
            try:
                df = pd.read_parquet(LINEUP_HISTORY)
                if 'prev_chegada' in df.columns:
                    # Tentar converter para datetime, ignorar erros
                    df['prev_chegada'] = pd.to_datetime(df['prev_chegada'], errors='coerce')
                # Renomear 'porto' para 'nome_porto' se necessário
                if 'porto' in df.columns and 'nome_porto' not in df.columns:
                    df['nome_porto'] = df['porto']
                return df
            except Exception as e:
                print(Colors.warning(f"[AVISO] Erro ao carregar lineup_history.parquet: {e}"))
                return pd.DataFrame()
        else:
            # Retornar DataFrame vazio se não existir
            return pd.DataFrame()

    def _calculate_porto_stats(self) -> Dict:
        """Calcula estatísticas históricas por porto."""
        stats = {}

        try:
            if len(self.lineup_history) > 0 and 'nome_porto' in self.lineup_history.columns:
                for porto in PORTOS.keys():
                    porto_data = self.lineup_history[
                        self.lineup_history['nome_porto'] == porto
                    ]

                    if len(porto_data) > 0 and 'tempo_espera_horas' in porto_data.columns:
                        tempo_medio = porto_data["tempo_espera_horas"].mean()
                        stats[porto] = {
                            "tempo_medio": tempo_medio if not pd.isna(tempo_medio) else 48.0,
                            "count": len(porto_data),
                        }
                    else:
                        stats[porto] = {"tempo_medio": 48.0, "count": 0}
            else:
                # Valores default
                for porto in PORTOS.keys():
                    stats[porto] = {"tempo_medio": 48.0, "count": 0}
        except Exception as e:
            print(Colors.warning(f"[AVISO] Erro ao calcular estatisticas de portos: {e}"))
            # Valores default em caso de erro
            for porto in PORTOS.keys():
                stats[porto] = {"tempo_medio": 48.0, "count": 0}

        return stats

    def get_clima_forecast(self, porto: str, data: datetime) -> Dict:
        """
        Obtém previsão de clima via API Open-Meteo (gratuita).

        Args:
            porto: Nome do porto
            data: Data da previsão

        Returns:
            Dict com temperatura, precipitação e vento
        """
        coords = PORTOS[porto]

        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "daily": "temperature_2m_mean,precipitation_sum,windspeed_10m_max,relativehumidity_2m_mean",
                "start_date": data.strftime("%Y-%m-%d"),
                "end_date": data.strftime("%Y-%m-%d"),
                "timezone": "America/Sao_Paulo",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            forecast = response.json()

            return {
                "temp": forecast["daily"]["temperature_2m_mean"][0],
                "precip": forecast["daily"]["precipitation_sum"][0] or 0,
                "vento": forecast["daily"]["windspeed_10m_max"][0],
                "umidade": forecast["daily"]["relativehumidity_2m_mean"][0],
            }

        except Exception as e:
            print(Colors.warning(f"[AVISO] Erro ao buscar clima: {e}. Usando valores medios."))
            # Fallback: usar médias regionais
            regiao = coords["regiao"]
            mes = data.month

            # Médias regionais (valores aproximados)
            clima_medio = {
                "SUDESTE": {1: {"temp": 26.5, "precip": 250, "vento": 15, "umidade": 78}},
                "SUL": {1: {"temp": 24.5, "precip": 140, "vento": 18, "umidade": 75}},
                "NORDESTE": {1: {"temp": 28.5, "precip": 80, "vento": 20, "umidade": 72}},
            }

            # Usar valores do mês (ou janeiro como fallback)
            clima = clima_medio.get(regiao, clima_medio["SUDESTE"]).get(mes, clima_medio["SUDESTE"][1])

            return {
                "temp": clima["temp"],
                "precip": clima["precip"],
                "vento": clima["vento"],
                "umidade": clima["umidade"],
            }

    def estimate_fila_historica(self, porto: str, data: datetime) -> int:
        """
        Estima número de navios na fila baseado em histórico.

        Args:
            porto: Nome do porto
            data: Data da estimativa

        Returns:
            Número estimado de navios na fila (últimos 7 dias)
        """
        try:
            if len(self.lineup_history) == 0 or 'nome_porto' not in self.lineup_history.columns:
                # Default: 3 navios
                return 3

            # Filtrar lineups do mesmo porto e mês
            porto_data = self.lineup_history[
                (self.lineup_history['nome_porto'] == porto) &
                (self.lineup_history['prev_chegada'].notna()) &
                (self.lineup_history['prev_chegada'].dt.month == data.month)
            ]

            if len(porto_data) == 0:
                return 3

            # Contar navios por dia e calcular média
            navios_por_dia = porto_data.groupby(
                porto_data['prev_chegada'].dt.date
            ).size()

            media_diaria = navios_por_dia.mean()

            # Estimar fila de 7 dias
            fila_7d = int(media_diaria * 7) if not pd.isna(media_diaria) else 3

            return max(1, min(fila_7d, 20))  # Entre 1 e 20 navios

        except Exception as e:
            print(Colors.warning(f"[AVISO] Erro ao estimar fila historica: {e}"))
            return 3  # Fallback

    def inferir_perfil(self, tipo_navio: str, natureza_carga: str, porto: str) -> str:
        """
        Infere o perfil de carga baseado no tipo de navio, carga e porto.

        Args:
            tipo_navio: Tipo do navio (Bulk Carrier, Tanker, etc)
            natureza_carga: Natureza da carga (Soja, Ureia, Minério, etc)
            porto: Nome do porto

        Returns:
            "VEGETAL", "MINERAL" ou "FERTILIZANTE"
        """
        tipo_lower = tipo_navio.lower() if tipo_navio else ""
        carga_lower = natureza_carga.lower() if natureza_carga else ""

        # Tankers geralmente são fertilizantes/químicos
        if "tanker" in tipo_lower or "chemical" in tipo_lower:
            return "FERTILIZANTE"

        # Verificar pela carga
        if any(x in carga_lower for x in ["soja", "milho", "farelo", "acucar", "trigo", "cevada"]):
            return "VEGETAL"

        if any(x in carga_lower for x in ["minerio", "bauxita", "manganes", "ferro", "cimento"]):
            return "MINERAL"

        if any(x in carga_lower for x in ["ureia", "kcl", "npk", "fosfato", "fertil"]):
            return "FERTILIZANTE"

        # Inferir pelo porto + tipo
        if "bulk" in tipo_lower or "cargo" in tipo_lower:
            # Portos de grãos
            if porto in ["Santos", "Paranaguá", "Rio Grande"]:
                return "VEGETAL"
            # Portos de minério
            elif porto in ["Itaqui", "Vitória"]:
                return "MINERAL"
            else:
                return "VEGETAL"  # Default

        return "VEGETAL"  # Fallback

    def enrich_features(
        self,
        navio_data: Dict,
        use_complete_model: bool = False
    ) -> Tuple[Dict, List[str]]:
        """
        Enriquece dados básicos do navio com todas as features necessárias.

        Args:
            navio_data: Dict com dados básicos (porto, tipo, carga, eta, dwt, calado)
            use_complete_model: Se True, gera features para modelo completo (35-51)

        Returns:
            (features_dict, feature_names)
        """
        features = {}

        # Dados básicos
        porto = navio_data["porto"]
        eta = pd.to_datetime(navio_data["eta"])
        tipo_navio = navio_data.get("tipo", "Bulk Carrier")
        natureza_carga = navio_data.get("carga", "Soja em Graos")
        dwt = navio_data.get("dwt", 75000)
        calado = navio_data.get("calado", 12.5)
        toneladas = navio_data.get("toneladas", 50000)

        # Inferir perfil
        perfil = self.inferir_perfil(tipo_navio, natureza_carga, porto)

        # ===== FEATURES BÁSICAS =====
        features["nome_porto"] = porto
        features["nome_terminal"] = f"{porto} - Terminal 1"
        features["tipo_navegacao"] = "Longo Curso"
        features["tipo_carga"] = "Granel"
        features["natureza_carga"] = natureza_carga
        features["cdmercadoria"] = "1201"  # Mock
        features["stsh4"] = "1201"
        features["movimentacao_total_toneladas"] = toneladas

        # ===== FEATURES TEMPORAIS =====
        features["mes"] = eta.month
        features["dia_semana"] = eta.dayofweek
        features["dia_do_ano"] = eta.day_of_year

        # Período de safra
        if eta.month in [2, 3, 4]:  # Safra soja
            features["periodo_safra"] = 1
        elif eta.month in [7, 8, 9]:  # Safrinha milho
            features["periodo_safra"] = 2
        else:
            features["periodo_safra"] = 0

        # ===== FEATURES HISTÓRICAS =====
        features["navios_na_fila_7d"] = self.estimate_fila_historica(porto, eta)
        features["navios_no_fundeio_na_chegada"] = features["navios_na_fila_7d"]
        features["porto_tempo_medio_historico"] = self.porto_stats[porto]["tempo_medio"]
        features["tempo_espera_ma5"] = features["porto_tempo_medio_historico"]  # Proxy

        # ===== FEATURES CLIMÁTICAS =====
        clima = self.get_clima_forecast(porto, eta)

        features["temp_media_dia"] = clima["temp"]
        features["temperatura_media"] = clima["temp"]  # Alias para modelo light
        features["precipitacao_dia"] = clima["precip"]
        features["vento_rajada_max_dia"] = clima["vento"] * 1.5
        features["vento_velocidade_media"] = clima["vento"]
        features["umidade_media_dia"] = clima["umidade"]
        features["amplitude_termica"] = 8.0
        features["restricao_vento"] = 1 if clima["vento"] > 25 else 0
        features["restricao_chuva"] = 1 if clima["precip"] > 50 else 0

        if use_complete_model:
            # Features climáticas extras para modelo completo
            features["chuva_acumulada_ultimos_3dias"] = clima["precip"] * 3
            features["frente_fria"] = 0
            features["pressao_anomalia"] = 0.0
            features["ressaca"] = 0

        # ===== FEATURES DE MARÉ (apenas VEGETAL completo) =====
        if use_complete_model and perfil == "VEGETAL":
            features["wave_height_max"] = 1.5
            features["wave_height_media"] = 1.0
            features["mare_astronomica"] = 2.0
            features["mare_subindo"] = 1
            features["mare_horas_ate_extremo"] = 3.0
            features["tem_mare_astronomica"] = 1

        # ===== FEATURES AGRÍCOLAS =====
        agro = AGRO_HISTORICO[eta.month]

        features["flag_celulose"] = 0
        features["flag_algodao"] = 0
        features["flag_soja"] = 1 if "soja" in natureza_carga.lower() else 0
        features["flag_milho"] = 1 if "milho" in natureza_carga.lower() else 0
        features["producao_soja"] = agro["prod_soja"]
        features["producao_milho"] = agro["prod_milho"]
        features["producao_algodao"] = agro["prod_algodao"]
        features["preco_soja_mensal"] = agro["preco_soja"]
        features["preco_milho_mensal"] = agro["preco_milho"]
        features["preco_algodao_mensal"] = agro["preco_algodao"]
        features["indice_pressao_soja"] = (agro["preco_soja"] * agro["prod_soja"]) / 100
        features["indice_pressao_milho"] = (agro["preco_milho"] * agro["prod_milho"]) / 100

        # ===== FEATURES AIS (ESTIMADAS) =====
        features["ais_navios_no_raio"] = features["navios_na_fila_7d"]
        features["ais_fila_ao_largo"] = features["navios_na_fila_7d"]
        features["ais_velocidade_media_kn"] = 10.0
        features["ais_dist_media_km"] = 100.0
        features["ais_eta_media_horas"] = 10.0

        # ===== FEATURES ESPECÍFICAS POR PERFIL =====
        features["flag_quimico"] = 1 if perfil == "FERTILIZANTE" else 0

        # DWT e calado normalizados
        features["dwt_normalizado"] = dwt / 100000
        features["calado_normalizado"] = calado / 20

        # Tipo de navio encoded (mock)
        features["tipo_navio_encoded"] = 1

        # Capacidade e berços do porto
        features["capacidade_porto"] = PORTOS[porto]["capacidade"]
        features["num_bercos"] = PORTOS[porto]["num_bercos"]

        # Nome porto encoded (será feito depois com LabelEncoder real)
        features["nome_porto_encoded"] = 0
        features["natureza_carga_encoded"] = 0

        return features, perfil

    def prepare_feature_array(
        self,
        features: Dict,
        perfil: str,
        use_complete: bool
    ) -> np.ndarray:
        """
        Prepara array de features na ordem correta para o modelo.

        Args:
            features: Dict com todas as features
            perfil: "VEGETAL", "MINERAL" ou "FERTILIZANTE"
            use_complete: Se True, usa features do modelo completo

        Returns:
            Array numpy com features na ordem correta
        """
        # Obter lista de features necessárias
        if use_complete:
            feature_names = self.models[perfil]["complete_meta"]["features"]
        else:
            feature_names = self.models[perfil]["light_meta"]["features"]

        # Criar array na ordem correta
        X = []
        for feat in feature_names:
            if feat in features:
                value = features[feat]

                # Codificar features categóricas simples
                if isinstance(value, str):
                    # Hash simples para strings
                    value = hash(value) % 100

                X.append(float(value))
            else:
                # Feature faltando - usar 0
                X.append(0.0)

        return np.array([X])

    def predict(
        self,
        navio_data: Dict,
        quality_score: float = 1.0,
        force_model: Optional[str] = None
    ) -> Dict:
        """
        Faz previsão de tempo de espera para um navio.

        Args:
            navio_data: Dict com dados do navio
                - porto: str (obrigatório)
                - tipo: str (opcional)
                - carga: str (opcional)
                - eta: str ou datetime (obrigatório)
                - dwt: float (opcional)
                - calado: float (opcional)
                - toneladas: float (opcional)
            quality_score: Score de qualidade dos dados (0-1)
            force_model: "complete" ou "light" para forçar uso de modelo específico

        Returns:
            Dict com resultado da previsão:
                - tempo_espera_previsto_horas: float
                - categoria_fila: str
                - categoria_index: int
                - confianca: float
                - perfil: str
                - modelo_usado: str
                - features_calculadas: int
        """
        # 1. Enriquecer features e inferir perfil
        features, perfil = self.enrich_features(navio_data, use_complete_model=False)

        # 2. Decidir qual modelo usar
        use_complete = False
        modelo_usado = "light"

        # Regra: modelo completo apenas para VEGETAL com qualidade >= 80%
        if force_model == "complete":
            use_complete = True
            modelo_usado = "complete"
        elif force_model == "light":
            use_complete = False
            modelo_usado = "light"
        else:
            # Lógica automática
            if (
                perfil == "VEGETAL"
                and quality_score >= 0.80
                and self.models[perfil]["has_complete"]
            ):
                use_complete = True
                modelo_usado = "complete"
                # Re-enriquecer com features completas
                features, _ = self.enrich_features(navio_data, use_complete_model=True)

        # 3. Preparar array de features
        X = self.prepare_feature_array(features, perfil, use_complete)

        # 4. Fazer previsão
        if use_complete and self.models[perfil]["has_complete"]:
            # Modelo completo
            reg_model = self.models[perfil]["complete_reg"]
            clf_model = self.models[perfil]["complete_clf"]
        else:
            # Modelo light
            reg_model = self.models[perfil]["light_reg"]
            clf_model = self.models[perfil]["light_clf"]

        # Regressão (tempo em horas)
        tempo_previsto = float(reg_model.predict(X)[0])

        # Classificação (categoria)
        categoria_idx = int(clf_model.predict(X)[0])
        categoria = CATEGORIAS.get(categoria_idx, "Desconhecido")

        # Confiança (baseada em probabilidade do classificador)
        try:
            proba = clf_model.predict_proba(X)[0]
            confianca = float(proba[categoria_idx])
        except:
            confianca = 0.8

        # 5. Retornar resultado
        return {
            "tempo_espera_previsto_horas": round(tempo_previsto, 1),
            "tempo_espera_previsto_dias": round(tempo_previsto / 24, 1),
            "categoria_fila": categoria,
            "categoria_index": categoria_idx,
            "confianca": round(confianca, 3),
            "perfil": perfil,
            "modelo_usado": modelo_usado,
            "features_calculadas": len(features),
            "porto": navio_data["porto"],
            "eta": pd.to_datetime(navio_data["eta"]).strftime("%Y-%m-%d"),
        }


# ============================================================================
# FUNÇÕES AUXILIARES PARA EXIBIÇÃO AMIGÁVEL
# ============================================================================

def get_categoria_color(categoria_index: int) -> str:
    """Retorna a cor apropriada para cada categoria de fila."""
    colors = {
        0: Colors.success,  # 0-2 dias (Rápido)
        1: Colors.info,     # 2-7 dias (Normal)
        2: Colors.warning,  # 7-14 dias (Longo)
        3: Colors.error,    # 14+ dias (Muito Longo)
    }
    return colors.get(categoria_index, Colors.info)


def get_categoria_explicacao(categoria: str) -> str:
    """Retorna explicação amigável sobre a categoria de fila."""
    explicacoes = {
        "0-2 dias (Rápido)": "Fila curta. Atracacao rapida esperada. Situacao favoravel.",
        "2-7 dias (Normal)": "Tempo de espera dentro da media. Planejamento normal.",
        "7-14 dias (Longo)": "Fila mais longa que o usual. Recomenda-se planejamento cuidadoso.",
        "14+ dias (Muito Longo)": "Fila critica. Considere alternativas ou aguarde reducao.",
    }
    return explicacoes.get(categoria, "Categoria desconhecida")


def format_resultado(resultado: Dict, show_details: bool = True) -> str:
    """
    Formata o resultado da previsão de forma amigável ao usuário.

    Args:
        resultado: Dict retornado pela função predict()
        show_details: Se True, mostra detalhes técnicos adicionais

    Returns:
        String formatada com cores e informações explicativas
    """
    output = []

    # Cabeçalho
    output.append("\n" + "=" * 70)
    output.append(Colors.bold(f"PREVISAO DE FILA PORTUARIA - {resultado['porto'].upper()}"))
    output.append("=" * 70)

    # Informações do navio
    output.append(f"\n{Colors.bold('Porto:')} {resultado['porto']}")
    output.append(f"{Colors.bold('ETA previsto:')} {resultado['eta']}")

    # Resultado principal
    output.append(f"\n{Colors.bold('TEMPO DE ESPERA PREVISTO:')}")
    tempo_dias = resultado['tempo_espera_previsto_dias']
    tempo_horas = resultado['tempo_espera_previsto_horas']

    # Cor baseada na categoria
    color_func = get_categoria_color(resultado['categoria_index'])
    output.append(color_func(f"  {tempo_dias:.1f} dias ({tempo_horas:.1f} horas)"))

    # Categoria e explicação
    categoria = resultado['categoria_fila']
    output.append(f"\n{Colors.bold('Categoria:')} {color_func(categoria)}")
    output.append(f"{Colors.bold('Explicacao:')} {get_categoria_explicacao(categoria)}")

    # Confiança
    confianca = resultado['confianca'] * 100
    if confianca >= 80:
        conf_color = Colors.success
    elif confianca >= 60:
        conf_color = Colors.info
    else:
        conf_color = Colors.warning
    output.append(f"\n{Colors.bold('Confianca da previsao:')} {conf_color(f'{confianca:.1f}%')}")

    # Detalhes técnicos (opcional)
    if show_details:
        output.append(f"\n{Colors.bold('DETALHES TECNICOS:')}")
        output.append(f"  Perfil de carga: {resultado['perfil']}")
        output.append(f"  Modelo usado: {resultado['modelo_usado']}")
        if 'features_calculadas' in resultado:
            output.append(f"  Features calculadas: {resultado['features_calculadas']}")

    output.append("\n" + "=" * 70)

    return "\n".join(output)


def print_legenda_categorias():
    """Imprime legenda explicativa sobre as categorias de fila."""
    print("\n" + Colors.bold("LEGENDA DE CATEGORIAS DE FILA:"))
    print(Colors.success("  0-2 dias (Rapido):") + " Fila curta, atracacao rapida esperada")
    print(Colors.info("  2-7 dias (Normal):") + " Tempo de espera dentro da media")
    print(Colors.warning("  7-14 dias (Longo):") + " Fila mais longa, planejamento necessario")
    print(Colors.error("  14+ dias (Muito Longo):") + " Fila critica, considerar alternativas")
    print()


# ============================================================================
# EXEMPLO DE USO
# ============================================================================


if __name__ == "__main__":
    # Inicializar preditor
    predictor = EnrichedPredictor()

    print("\n" + "=" * 70)
    print(Colors.bold("TESTE DE PREVISAO COM ENRIQUECIMENTO AUTOMATICO"))
    print("=" * 70 + "\n")

    # Exemplo 1: Navio de grãos em Santos
    navio1 = {
        "porto": "Santos",
        "tipo": "Bulk Carrier",
        "carga": "Soja em Graos",
        "eta": "2026-02-15",
        "dwt": 75000,
        "calado": 12.5,
        "toneladas": 60000,
    }

    print(Colors.highlight("Navio 1: Bulk Carrier com Soja em Santos"))
    print("-" * 70)

    # Testar com modelo light
    resultado_light = predictor.predict(navio1, quality_score=0.5, force_model="light")

    # Demonstrar formatação amigável
    print(format_resultado(resultado_light, show_details=True))

    print("\n" + Colors.info("COMPARACAO: Testando modelo completo para o mesmo navio..."))

    # Testar com modelo completo
    resultado_complete = predictor.predict(navio1, quality_score=1.0, force_model="complete")
    print(format_resultado(resultado_complete, show_details=True))

    # Exemplo 2: Tanker de fertilizante em Suape
    navio2 = {
        "porto": "Suape",
        "tipo": "Chemical Tanker",
        "carga": "Ureia",
        "eta": "2026-03-01",
        "dwt": 45000,
    }

    print("\n" + Colors.highlight("Navio 2: Chemical Tanker com Ureia em Suape"))
    print("-" * 70)
    print(Colors.info("Previsao com selecao automatica de modelo (quality_score=0.9)"))

    resultado2 = predictor.predict(navio2, quality_score=0.9)
    print(format_resultado(resultado2, show_details=True))

    print("=" * 70)
    print(Colors.success("[OK] Testes concluidos com sucesso!"))
    print("=" * 70)

    # Adicionar legenda explicativa sobre categorias
    print_legenda_categorias()
