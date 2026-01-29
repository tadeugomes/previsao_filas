#!/usr/bin/env python3
"""
Script para preprocessar dados históricos e gerar features de treino.

Este script converte lineup_history.parquet (dados brutos) em features_history.parquet
(dados processados com todas as features necessárias para treino).

IMPORTANTE: Este script precisa calcular o TARGET (tempo_espera_horas) real.
Para isso, precisamos de dados de atracação efetiva para calcular o tempo real de espera.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import sys

# Adiciona o diretório raiz ao path para importar módulos do streamlit
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_raw_history():
    """Carrega dados históricos brutos."""
    parquet_file = Path("lineups_previstos/lineup_history.parquet")

    if not parquet_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {parquet_file}")

    df = pd.read_parquet(parquet_file)
    print(f"✅ Dados brutos carregados: {len(df):,} registros")
    print(f"   Colunas disponíveis: {list(df.columns)}")

    return df


def calculate_target_variable(df):
    """
    Calcula a variável target: tempo_espera_horas.

    PROBLEMA CRÍTICO: O arquivo atual NÃO TEM dados de atracação efetiva!

    Opções:
    1. Se tiver coluna 'data_atracacao': tempo = data_atracacao - prev_chegada
    2. Se não tiver: IMPOSSÍVEL treinar (não sabemos o tempo real de espera)

    Para treinar modelos reais, você precisa:
    - Dados históricos COM data/hora de chegada prevista E atracação efetiva
    - Ou um arquivo separado linkando eventos a suas conclusões
    """
    print("\n⚠️  VERIFICANDO POSSIBILIDADE DE CALCULAR TARGET...")

    # Verifica se temos as colunas necessárias
    required_cols = ['prev_chegada']
    actual_cols = ['data_atracacao', 'hora_atracacao', 'atracacao_efetiva',
                   'data_inicio_operacao', 'timestamp_atracacao']

    missing = [col for col in required_cols if col not in df.columns]
    available_actual = [col for col in actual_cols if col in df.columns]

    if missing:
        print(f"❌ Coluna 'prev_chegada' não encontrada")
        return None

    if not available_actual:
        print(f"❌ IMPOSSÍVEL CALCULAR TARGET!")
        print(f"   Colunas disponíveis: {list(df.columns)}")
        print(f"\n   Nenhuma coluna de atracação efetiva encontrada.")
        print(f"   Procurei por: {actual_cols}")
        print(f"\n💡 SOLUÇÃO:")
        print(f"   1. Obter dados históricos completos (chegada + atracação)")
        print(f"   2. Ou linkar eventos históricos com dados de operação portuária")
        print(f"   3. Ou usar sistema em produção para coletar dados reais")
        return None

    print(f"✅ Colunas de atracação encontradas: {available_actual}")

    # Tenta calcular target
    # TODO: Implementar lógica específica baseada nas colunas disponíveis

    return df


def extract_basic_features(df):
    """Extrai features básicas dos dados brutos."""
    print("\n📊 Extraindo features básicas...")

    features = pd.DataFrame()

    # 1. Porto e Terminal
    if 'porto' in df.columns:
        features['nome_porto'] = df['porto']
    if 'berco' in df.columns:
        features['nome_terminal'] = df['berco']

    # 2. Natureza da carga
    if 'operacao' in df.columns:
        features['natureza_carga'] = df['operacao'].map({
            'EMBARQUE': 'EXPORTACAO',
            'DESEMBARQUE': 'IMPORTACAO',
            'DESCARGA': 'IMPORTACAO',
            'CARREGAMENTO': 'EXPORTACAO'
        }).fillna('EXPORTACAO')

    # 3. Movimentação de carga (toneladas)
    if 'qtdcarga' in df.columns:
        # Tenta converter para número
        features['movimentacao_total_toneladas'] = pd.to_numeric(
            df['qtdcarga'].astype(str).str.replace(',', '.').str.replace('[^0-9.]', '', regex=True),
            errors='coerce'
        )

    # 4. Flags de produto
    if 'produto' in df.columns or 'carga' in df.columns:
        cargo_col = 'produto' if 'produto' in df.columns else 'carga'
        cargo_lower = df[cargo_col].astype(str).str.lower()

        features['flag_soja'] = cargo_lower.str.contains('soja', na=False).astype(int)
        features['flag_milho'] = cargo_lower.str.contains('milho', na=False).astype(int)

    # 5. Features temporais
    if 'prev_chegada' in df.columns:
        dates = pd.to_datetime(df['prev_chegada'], errors='coerce')
        features['mes'] = dates.dt.month
        features['dia_semana'] = dates.dt.dayofweek
        features['dia_do_ano'] = dates.dt.dayofyear

        # Período de safra (soja: mar-mai e set-nov, milho: fev-jul)
        is_soja_1 = (dates.dt.month >= 3) & (dates.dt.month <= 5)
        is_soja_2 = (dates.dt.month >= 9) & (dates.dt.month <= 11)
        is_milho = (dates.dt.month >= 2) & (dates.dt.month <= 7)

        features['periodo_safra'] = 0
        features.loc[is_soja_1 | is_soja_2, 'periodo_safra'] = 1  # Safra soja
        features.loc[is_milho, 'periodo_safra'] = 2  # Safra milho

    print(f"✅ Features básicas extraídas: {len(features.columns)} colunas")
    print(f"   Colunas: {list(features.columns)}")

    return features


def calculate_queue_metrics(df):
    """
    Calcula métricas de fila.

    PROBLEMA: Precisamos de dados de múltiplos navios no MESMO momento histórico.
    O arquivo atual parece ser um snapshot único, não uma série temporal completa.
    """
    print("\n⚠️  TENTANDO CALCULAR MÉTRICAS DE FILA...")

    if 'prev_chegada' not in df.columns or 'porto' not in df.columns:
        print("❌ Colunas necessárias não disponíveis")
        return None

    # Para cada navio, contar quantos outros navios estavam aguardando
    # no mesmo porto na mesma data
    df_sorted = df.copy()
    df_sorted['prev_chegada_dt'] = pd.to_datetime(df_sorted['prev_chegada'], errors='coerce')

    # Agrupa por porto e data para contar fila
    queue_metrics = []

    for idx, row in df_sorted.iterrows():
        porto = row['porto']
        data_chegada = row['prev_chegada_dt']

        if pd.isna(data_chegada):
            queue_metrics.append(0)
            continue

        # Conta navios no mesmo porto que chegaram na mesma janela temporal
        same_port = df_sorted['porto'] == porto
        same_timeframe = (
            (df_sorted['prev_chegada_dt'] >= data_chegada - timedelta(days=1)) &
            (df_sorted['prev_chegada_dt'] <= data_chegada + timedelta(days=1))
        )

        queue_count = (same_port & same_timeframe).sum() - 1  # Exclui o próprio navio
        queue_metrics.append(max(0, queue_count))

    print(f"✅ Métricas de fila calculadas (aproximadas)")
    print(f"   Fila média: {np.mean(queue_metrics):.1f} navios")

    return pd.Series(queue_metrics, index=df.index, name='navios_no_fundeio_na_chegada')


def calculate_historical_baselines(df):
    """
    Calcula baselines históricos (tempo médio, moving averages).

    PROBLEMA: Precisamos da variável TARGET para calcular médias históricas!
    Sem tempo_espera_horas, não podemos calcular porto_tempo_medio_historico.
    """
    print("\n⚠️  IMPOSSÍVEL CALCULAR BASELINES SEM TARGET")
    print("   - porto_tempo_medio_historico requer tempo_espera_horas")
    print("   - tempo_espera_ma5 requer tempo_espera_horas")
    print("   - navios_na_fila_7d requer série temporal completa")

    return None


def main():
    """Função principal."""
    print("="*70)
    print("PREPROCESSAMENTO DE DADOS HISTÓRICOS")
    print("="*70)

    # 1. Carrega dados brutos
    try:
        df_raw = load_raw_history()
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return 1

    # 2. Verifica se é possível calcular target
    df_with_target = calculate_target_variable(df_raw)

    if df_with_target is None:
        print("\n" + "="*70)
        print("❌ IMPOSSÍVEL PROSSEGUIR COM TREINO")
        print("="*70)
        print("\n🔍 DIAGNÓSTICO:")
        print("   O arquivo lineup_history.parquet contém apenas:")
        print("   - Dados de previsão de chegada (prev_chegada)")
        print("   - Informações do navio e carga")
        print("   - MAS NÃO contém dados de atracação efetiva")
        print("\n   Sem saber QUANDO o navio efetivamente atracou,")
        print("   é IMPOSSÍVEL calcular o tempo real de espera (target).")
        print("\n💡 SOLUÇÕES POSSÍVEIS:")
        print("\n   1. USAR DADOS HISTÓRICOS COMPLETOS:")
        print("      - Obter arquivo com prev_chegada + data_atracacao")
        print("      - Formato: CSV/Parquet com ambas as colunas")
        print("      - Fonte: Sistema portuário, APIs, banco de dados")
        print("\n   2. COLETAR DADOS EM PRODUÇÃO:")
        print("      - Rodar sistema Streamlit por 2-3 meses")
        print("      - Salvar previsões + acompanhar atracações reais")
        print("      - Acumular dataset de treino gradualmente")
        print("\n   3. USAR DADOS EXTERNOS:")
        print("      - AIS data com timestamps de chegada/atracação")
        print("      - Relatórios de autoridade portuária")
        print("      - Planilhas manuais de operação")
        print("\n   4. MANTER MODELOS MOCK:")
        print("      - Usar modelos simplificados atuais")
        print("      - Ajustar heurísticas com conhecimento do domínio")
        print("      - Validar com dados reais quando disponíveis")
        print("\n📋 ARQUIVO NECESSÁRIO (exemplo):")
        print("   Colunas mínimas:")
        print("   - navio")
        print("   - porto")
        print("   - prev_chegada (datetime)")
        print("   - data_atracacao (datetime)")
        print("   - carga")
        print("   - operacao")
        print("\n   Com isso, podemos calcular:")
        print("   tempo_espera_horas = data_atracacao - prev_chegada")
        print("\n" + "="*70)
        return 1

    # 3. Extrai features básicas
    features_basic = extract_basic_features(df_raw)

    # 4. Calcula métricas de fila
    queue_metrics = calculate_queue_metrics(df_raw)
    if queue_metrics is not None:
        features_basic['navios_no_fundeio_na_chegada'] = queue_metrics

    # 5. Calcula baselines históricos
    # (impossível sem target)

    # 6. Features de clima
    # (requer integração com APIs - não disponível em batch histórico)
    print("\n⚠️  Features de clima (precipitacao_dia, vento_rajada_max_dia):")
    print("   Requer integração com Open-Meteo ou similar")
    print("   Não implementado neste script de preprocessing")

    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    print(f"\n📊 Features extraídas: {len(features_basic.columns)}")
    print(f"   Disponíveis: {list(features_basic.columns)}")
    print(f"\n❌ Features faltando (~10):")
    print("   - porto_tempo_medio_historico (requer target)")
    print("   - tempo_espera_ma5 (requer target)")
    print("   - navios_na_fila_7d (requer série temporal)")
    print("   - precipitacao_dia (requer API clima)")
    print("   - vento_rajada_max_dia (requer API clima)")
    print("   - tipo_navegacao (não disponível)")
    print("   - ais_fila_ao_largo (requer API AIS)")
    print("   - temp_media_dia (requer API clima)")

    print("\n❌ Mais importante: TARGET ausente!")
    print("   - tempo_espera_horas: DESCONHECIDO")

    print("\n💡 RECOMENDAÇÃO FINAL:")
    print("   Não é possível treinar modelos reais com os dados atuais.")
    print("   Mantenha os modelos MOCK até obter dados históricos completos.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
