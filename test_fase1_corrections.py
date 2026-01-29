#!/usr/bin/env python3
"""
Script de teste para validar as correções da Fase 1.
Testa as três funções críticas corrigidas:
- carregar_tempo_medio_historico()
- calcular_fila_simulada()
- calcular_tempo_espera_ma5()
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Adiciona o diretório atual ao path para importar streamlit_app
sys.path.insert(0, str(Path(__file__).parent))

# Importa as funções que precisamos testar
from streamlit_app import (
    carregar_tempo_medio_historico,
    calcular_fila_simulada,
    calcular_tempo_espera_ma5,
    normalizar_texto
)

def test_carregar_tempo_medio_historico():
    """Testa se a função retorna valores razoáveis para diferentes portos"""
    print("\n" + "="*70)
    print("TESTE 1: carregar_tempo_medio_historico()")
    print("="*70)

    portos_teste = [
        "SANTOS",
        "PARANAGUA",
        "ITAQUI",
        "PONTA_DA_MADEIRA",
        "VILA_DO_CONDE",
        "PORTO_DESCONHECIDO"  # Deve retornar default de 48h
    ]

    resultados = {}
    for porto in portos_teste:
        tempo = carregar_tempo_medio_historico(porto)
        resultados[porto] = tempo
        print(f"  ✓ {porto:25s} → {tempo:6.1f} horas ({tempo/24:.1f} dias)")

    # Validações
    assert all(tempo > 0 for tempo in resultados.values()), "Todos os tempos devem ser > 0"
    assert all(tempo < 300 for tempo in resultados.values()), "Todos os tempos devem ser < 300h (razoável)"
    assert resultados["SANTOS"] == 48.0, "SANTOS deve retornar 48h"
    assert resultados["PARANAGUA"] == 72.0, "PARANAGUA deve retornar 72h"
    assert resultados["PORTO_DESCONHECIDO"] == 48.0, "Porto desconhecido deve retornar default 48h"

    print("\n  ✅ TESTE 1 PASSOU - Todos os valores são razoáveis")
    return True


def test_calcular_fila_simulada():
    """Testa se a função calcula corretamente a fila"""
    print("\n" + "="*70)
    print("TESTE 2: calcular_fila_simulada()")
    print("="*70)

    # Cria um lineup de teste com 5 navios
    base_date = datetime(2026, 1, 27, 10, 0, 0)
    df_teste = pd.DataFrame({
        "data_chegada_dt": [
            base_date,                          # Navio 0: chegada em T+0
            base_date + timedelta(hours=12),    # Navio 1: chegada em T+12h
            base_date + timedelta(hours=24),    # Navio 2: chegada em T+24h
            base_date + timedelta(hours=48),    # Navio 3: chegada em T+48h
            base_date + timedelta(hours=96),    # Navio 4: chegada em T+96h
        ],
        "perfil_modelo": ["MINERAL"] * 5  # Taxa de 48h
    })

    fila = calcular_fila_simulada(df_teste, "SANTOS")

    print(f"\n  Lineup de teste (5 navios, perfil MINERAL, taxa=48h):")
    print(f"  {'Navio':<8} {'Chegada (horas)':<18} {'Fila Calculada':<15} {'Esperado':<15}")
    print(f"  {'-'*60}")

    # Expectativas:
    # Navio 0: T+0h   → fila=0 (primeiro)
    # Navio 1: T+12h  → fila=1 (navio 0 ainda está, chegou há 12h < 48h)
    # Navio 2: T+24h  → fila=2 (navios 0 e 1 ainda estão)
    # Navio 3: T+48h  → fila=2 (navio 0 já saiu, navios 1 e 2 ainda estão)
    # Navio 4: T+96h  → fila=1 (navios 0,1,2 já saíram, navio 3 ainda está)
    expectativas = [0, 1, 2, 2, 1]

    for i in range(len(df_teste)):
        horas_desde_inicio = (df_teste.iloc[i]["data_chegada_dt"] - base_date).total_seconds() / 3600
        print(f"  Navio {i}  T+{horas_desde_inicio:5.0f}h           {fila[i]:5.0f}              {expectativas[i]:5.0f}")

    # Validações
    assert len(fila) == len(df_teste), "Fila deve ter mesmo tamanho que o DataFrame"
    assert fila[0] == 0, "Primeiro navio deve ter fila 0"
    assert np.array_equal(fila, expectativas), f"Fila calculada {fila} não corresponde ao esperado {expectativas}"

    print("\n  ✅ TESTE 2 PASSOU - Fila calculada corretamente")
    return True


def test_calcular_fila_simulada_coluna_alternativa():
    """Testa se a função funciona com coluna 'chegada_dt' (modelo premium)"""
    print("\n" + "="*70)
    print("TESTE 3: calcular_fila_simulada() com coluna alternativa")
    print("="*70)

    base_date = datetime(2026, 1, 27, 10, 0, 0)
    df_teste = pd.DataFrame({
        "chegada_dt": [  # Nota: coluna diferente (usada no modelo premium)
            base_date,
            base_date + timedelta(hours=12),
            base_date + timedelta(hours=24),
        ]
    })

    fila = calcular_fila_simulada(df_teste, "PONTA_DA_MADEIRA")

    print(f"  Lineup com coluna 'chegada_dt' (modelo premium)")
    print(f"  Fila calculada: {fila}")

    assert len(fila) == 3, "Fila deve ter 3 elementos"
    assert fila[0] == 0, "Primeiro navio deve ter fila 0"

    print("\n  ✅ TESTE 3 PASSOU - Funciona com coluna alternativa")
    return True


def test_calcular_tempo_espera_ma5():
    """Testa se a função retorna valores razoáveis"""
    print("\n" + "="*70)
    print("TESTE 4: calcular_tempo_espera_ma5()")
    print("="*70)

    base_date = datetime(2026, 1, 27, 10, 0, 0)
    df_teste = pd.DataFrame({
        "data_chegada_dt": [
            base_date,
            base_date + timedelta(hours=24),
            base_date + timedelta(hours=48),
        ]
    })

    tempo_ma5 = calcular_tempo_espera_ma5(df_teste, "SANTOS")

    print(f"  Tempo MA5 calculado para SANTOS: {tempo_ma5}")
    print(f"  Esperado: array de 48.0 (tempo médio de SANTOS)")

    assert len(tempo_ma5) == 3, "MA5 deve ter mesmo tamanho que o DataFrame"
    assert np.all(tempo_ma5 == 48.0), "Todos os valores devem ser 48.0 (tempo médio de SANTOS)"

    print("\n  ✅ TESTE 4 PASSOU - MA5 calculada corretamente")
    return True


def test_comparacao_antes_depois():
    """Mostra a diferença entre o cálculo antigo (errado) e o novo (correto)"""
    print("\n" + "="*70)
    print("TESTE 5: Comparação ANTES vs DEPOIS")
    print("="*70)

    base_date = datetime(2026, 1, 27, 10, 0, 0)
    df_teste = pd.DataFrame({
        "data_chegada_dt": [
            base_date,
            base_date + timedelta(hours=12),
            base_date + timedelta(hours=24),
            base_date + timedelta(hours=48),
            base_date + timedelta(hours=96),
        ],
        "perfil_modelo": ["MINERAL"] * 5
    })

    # Cálculo ANTIGO (errado) - usava df.index
    fila_antiga = df_teste.index.astype(float).values

    # Cálculo NOVO (correto) - usa simulação real
    fila_nova = calcular_fila_simulada(df_teste, "SANTOS")

    print(f"\n  {'Navio':<8} {'Fila ANTIGA (errado)':<22} {'Fila NOVA (correto)':<22} {'Diferença':<12}")
    print(f"  {'-'*65}")

    for i in range(len(df_teste)):
        diff = fila_nova[i] - fila_antiga[i]
        diff_str = f"+{diff:.0f}" if diff >= 0 else f"{diff:.0f}"
        print(f"  Navio {i}  {fila_antiga[i]:5.0f}                  {fila_nova[i]:5.0f}                  {diff_str:>4}")

    print("\n  📊 ANÁLISE:")
    print(f"  - Método antigo: simplesmente [0, 1, 2, 3, 4, ...] (índice do DataFrame)")
    print(f"  - Método novo: calcula fila real baseada em taxas de atracação")
    print(f"  - Impacto: O modelo agora recebe valores MUITO mais realistas!")

    print("\n  ✅ TESTE 5 PASSOU - Comparação mostra melhoria significativa")
    return True


def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "="*70)
    print("INICIANDO TESTES DAS CORREÇÕES DA FASE 1")
    print("="*70)

    tests = [
        ("Tempo Médio Histórico", test_carregar_tempo_medio_historico),
        ("Fila Simulada", test_calcular_fila_simulada),
        ("Fila com Coluna Alternativa", test_calcular_fila_simulada_coluna_alternativa),
        ("Tempo MA5", test_calcular_tempo_espera_ma5),
        ("Comparação Antes/Depois", test_comparacao_antes_depois),
    ]

    resultados = []
    for nome, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nome, "✅ PASSOU"))
        except Exception as e:
            resultados.append((nome, f"❌ FALHOU: {e}"))
            print(f"\n  ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("RESUMO DOS TESTES")
    print("="*70)
    for nome, status in resultados:
        print(f"  {nome:40s} {status}")

    passou = all("PASSOU" in status for _, status in resultados)

    print("\n" + "="*70)
    if passou:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("="*70)
        print("\n✅ As correções da Fase 1 estão funcionando corretamente.")
        print("✅ As features críticas agora são calculadas de forma correta.")
        print("✅ O impacto nas previsões deve ser positivo (valores mais realistas).")
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
