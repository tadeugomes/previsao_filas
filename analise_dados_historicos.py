#!/usr/bin/env python3
"""
Script para analisar o arquivo lineup_history.parquet e preparar dados para treino.
"""

import sys
from pathlib import Path

def analyze_parquet():
    """Analisa estrutura do arquivo parquet."""
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas não está instalado")
        print("Execute: pip install pandas pyarrow")
        return False

    parquet_file = Path("lineups_previstos/lineup_history.parquet")

    if not parquet_file.exists():
        print(f"❌ Arquivo não encontrado: {parquet_file}")
        return False

    print("="*60)
    print("ANÁLISE DO ARQUIVO DE HISTÓRICO")
    print("="*60)

    # Carrega dados
    df = pd.read_parquet(parquet_file)

    print(f"\n📊 Informações Básicas:")
    print(f"   Linhas: {len(df):,}")
    print(f"   Colunas: {len(df.columns)}")
    print(f"   Tamanho: {parquet_file.stat().st_size / 1024:.1f} KB")

    # Colunas
    print(f"\n📋 Colunas Disponíveis ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        dtype = df[col].dtype
        non_null = df[col].notna().sum()
        pct = (non_null / len(df)) * 100
        print(f"   {i:2}. {col:<40} {str(dtype):<15} {non_null:>6}/{len(df)} ({pct:>5.1f}%)")

    # Target
    if 'tempo_espera_horas' in df.columns:
        print(f"\n🎯 Target: tempo_espera_horas")
        print(f"   Min: {df['tempo_espera_horas'].min():.1f}h")
        print(f"   Max: {df['tempo_espera_horas'].max():.1f}h")
        print(f"   Média: {df['tempo_espera_horas'].mean():.1f}h")
        print(f"   Mediana: {df['tempo_espera_horas'].median():.1f}h")
        print(f"   Não-nulos: {df['tempo_espera_horas'].notna().sum()}")

    # Perfis
    if 'perfil_modelo' in df.columns:
        print(f"\n🏷️  Perfis de Modelo:")
        perfis = df['perfil_modelo'].value_counts()
        for perfil, count in perfis.items():
            pct = (count / len(df)) * 100
            print(f"   {perfil:<20} {count:>6} ({pct:>5.1f}%)")

    # Features necessárias para modelos light
    features_light_vegetal = [
        "navios_no_fundeio_na_chegada",
        "porto_tempo_medio_historico",
        "tempo_espera_ma5",
        "navios_na_fila_7d",
        "nome_porto",
        "nome_terminal",
        "natureza_carga",
        "movimentacao_total_toneladas",
        "mes",
        "periodo_safra",
        "dia_semana",
        "flag_soja",
        "flag_milho",
        "precipitacao_dia",
        "vento_rajada_max_dia",
    ]

    print(f"\n✅ Features Necessárias para Modelo Light (15):")
    disponivel = 0
    faltando = []

    for feat in features_light_vegetal:
        if feat in df.columns:
            disponivel += 1
            non_null = df[feat].notna().sum()
            pct = (non_null / len(df)) * 100
            status = "✅" if pct > 50 else "⚠️"
            print(f"   {status} {feat:<40} {non_null:>6}/{len(df)} ({pct:>5.1f}%)")
        else:
            faltando.append(feat)
            print(f"   ❌ {feat:<40} NÃO DISPONÍVEL")

    print(f"\n📈 Resumo de Disponibilidade:")
    print(f"   Disponíveis: {disponivel}/15 ({disponivel/15*100:.0f}%)")
    if faltando:
        print(f"   Faltando: {len(faltando)}")
        print(f"   Features faltando: {', '.join(faltando)}")

    # Recomendações
    print(f"\n💡 Recomendações:")

    if disponivel >= 10:
        print(f"   ✅ Dados suficientes para treinar modelo light ({disponivel}/15 features)")
        print(f"   → Pode treinar com as {disponivel} features disponíveis")
    elif disponivel >= 7:
        print(f"   ⚠️  Dados parciais ({disponivel}/15 features)")
        print(f"   → Treino possível mas com performance reduzida")
    else:
        print(f"   ❌ Dados insuficientes ({disponivel}/15 features)")
        print(f"   → Necessário coletar mais features ou usar modelos completos")

    if len(df) < 1000:
        print(f"   ⚠️  Poucas amostras ({len(df)}). Recomendado: >= 1000")
    elif len(df) < 5000:
        print(f"   ⚠️  Amostras limitadas ({len(df)}). Ideal: >= 5000")
    else:
        print(f"   ✅ Amostras suficientes ({len(df):,})")

    return True


if __name__ == "__main__":
    success = analyze_parquet()
    sys.exit(0 if success else 1)
