#!/usr/bin/env python3
"""
Script de teste para validar as correções da Fase 2.
Testa o sistema de validação e rastreamento de qualidade de features.
"""

import sys
from pathlib import Path

# Adiciona o diretório atual ao path para importar streamlit_app
sys.path.insert(0, str(Path(__file__).parent))

# Importa as classes e funções que precisamos testar
from streamlit_app import (
    FeatureQuality,
    FeatureReport,
    avaliar_qualidade_features,
)

def test_feature_quality_enum():
    """Testa se o enum FeatureQuality está correto"""
    print("\n" + "="*70)
    print("TESTE 1: Enum FeatureQuality")
    print("="*70)

    expected_qualities = [
        "REAL", "API_OK", "API_FALLBACK", "CALCULATED",
        "DEFAULT", "CRITICAL_DEFAULT"
    ]

    for quality_name in expected_qualities:
        quality = getattr(FeatureQuality, quality_name, None)
        assert quality is not None, f"FeatureQuality.{quality_name} não encontrado"
        print(f"  ✓ FeatureQuality.{quality_name:20s} = {quality.value}")

    print("\n  ✅ TESTE 1 PASSOU - Enum definido corretamente")
    return True


def test_feature_report_dataclass():
    """Testa se a dataclass FeatureReport funciona"""
    print("\n" + "="*70)
    print("TESTE 2: Dataclass FeatureReport")
    print("="*70)

    # Cria um report de teste
    report = FeatureReport(
        total_features=54,
        quality_breakdown={
            FeatureQuality.REAL: 5,
            FeatureQuality.API_OK: 10,
            FeatureQuality.CALCULATED: 3,
            FeatureQuality.DEFAULT: 36,
            FeatureQuality.API_FALLBACK: 0,
            FeatureQuality.CRITICAL_DEFAULT: 0,
        },
        critical_issues=[],
        warnings=["Teste warning"],
        confidence_score=65.5
    )

    print(f"  Total features: {report.total_features}")
    print(f"  Confidence score: {report.confidence_score}")
    print(f"  Warnings: {len(report.warnings)}")

    # Testa to_dict
    report_dict = report.to_dict()
    assert "total_features" in report_dict
    assert "confidence" in report_dict
    assert report_dict["confidence"] == 65.5
    print(f"  ✓ to_dict() funciona corretamente")

    print("\n  ✅ TESTE 2 PASSOU - Dataclass funciona corretamente")
    return True


def test_avaliar_qualidade_cenario_perfeito():
    """Testa avaliação com todas as APIs disponíveis (cenário perfeito)"""
    print("\n" + "="*70)
    print("TESTE 3: Avaliação com todas APIs disponíveis")
    print("="*70)

    metadata = {
        "features": [
            # Lineup (5 features)
            "nome_porto", "nome_terminal", "natureza_carga",
            "movimentacao_total_toneladas", "mes",
            # Clima (3 features)
            "temp_media_dia", "precipitacao_dia", "vento_rajada_max_dia",
            # AIS (3 features)
            "ais_navios_no_raio", "ais_fila_ao_largo", "ais_velocidade_media_kn",
            # Fila calculada (2 features)
            "navios_no_fundeio_na_chegada", "navios_na_fila_7d",
            # Histórico (1 feature)
            "porto_tempo_medio_historico",
        ]
    }

    api_status = {
        "clima_ok": True,
        "ais_ok": True,
        "mare_ok": True,
        "economia_ok": True,
        "historico_ok": True,
    }

    report = avaliar_qualidade_features(metadata, api_status)

    print(f"  Total features: {report.total_features}")
    print(f"  Confidence score: {report.confidence_score:.1f}%")
    print(f"  Critical issues: {len(report.critical_issues)}")
    print(f"  Warnings: {len(report.warnings)}")

    print(f"\n  Quality breakdown:")
    for quality, count in report.quality_breakdown.items():
        if count > 0:
            pct = (count / report.total_features) * 100
            print(f"    - {quality.value:20s}: {count:2d} features ({pct:5.1f}%)")

    # Validações
    assert report.total_features == 14, f"Esperado 14 features, obteve {report.total_features}"
    assert report.confidence_score >= 85, f"Score deve ser ≥85% com todas APIs, obteve {report.confidence_score:.1f}%"
    assert len(report.critical_issues) == 0, "Não deve haver issues críticos com todas APIs"

    print("\n  ✅ TESTE 3 PASSOU - Cenário perfeito avaliado corretamente")
    return True


def test_avaliar_qualidade_cenario_ruim():
    """Testa avaliação sem APIs disponíveis (cenário ruim)"""
    print("\n" + "="*70)
    print("TESTE 4: Avaliação sem APIs disponíveis")
    print("="*70)

    metadata = {
        "features": [
            # Lineup (5 features)
            "nome_porto", "nome_terminal", "natureza_carga",
            "movimentacao_total_toneladas", "mes",
            # Clima (3 features)
            "temp_media_dia", "precipitacao_dia", "vento_rajada_max_dia",
            # AIS (3 features - CRÍTICO)
            "ais_navios_no_raio", "ais_fila_ao_largo", "ais_velocidade_media_kn",
            # Fila calculada (2 features)
            "navios_no_fundeio_na_chegada", "navios_na_fila_7d",
            # Histórico (1 feature)
            "porto_tempo_medio_historico",
        ]
    }

    api_status = {
        "clima_ok": False,  # ❌
        "ais_ok": False,    # ❌ CRÍTICO
        "mare_ok": True,
        "economia_ok": False,  # ❌
        "historico_ok": False,
    }

    report = avaliar_qualidade_features(metadata, api_status)

    print(f"  Total features: {report.total_features}")
    print(f"  Confidence score: {report.confidence_score:.1f}%")
    print(f"  Critical issues: {len(report.critical_issues)}")
    print(f"  Warnings: {len(report.warnings)}")

    print(f"\n  Quality breakdown:")
    for quality, count in report.quality_breakdown.items():
        if count > 0:
            pct = (count / report.total_features) * 100
            print(f"    - {quality.value:20s}: {count:2d} features ({pct:5.1f}%)")

    print(f"\n  Critical issues:")
    for issue in report.critical_issues:
        print(f"    - {issue}")

    print(f"\n  Warnings:")
    for warning in report.warnings:
        print(f"    - {warning}")

    # Validações
    assert report.total_features == 14
    assert report.confidence_score < 60, f"Score deve ser <60% sem APIs, obteve {report.confidence_score:.1f}%"
    assert len(report.critical_issues) > 0, "Deve haver issues críticos sem dados AIS"
    assert len(report.warnings) > 0, "Deve haver warnings sem clima/economia"

    print("\n  ✅ TESTE 4 PASSOU - Cenário ruim avaliado corretamente")
    return True


def test_avaliar_qualidade_cenario_medio():
    """Testa avaliação com algumas APIs disponíveis (cenário médio)"""
    print("\n" + "="*70)
    print("TESTE 5: Avaliação com algumas APIs disponíveis")
    print("="*70)

    metadata = {
        "features": [
            "nome_porto", "nome_terminal", "natureza_carga",
            "movimentacao_total_toneladas", "mes",
            "temp_media_dia", "precipitacao_dia", "vento_rajada_max_dia",
            "ais_navios_no_raio", "ais_fila_ao_largo", "ais_velocidade_media_kn",
            "navios_no_fundeio_na_chegada", "navios_na_fila_7d",
            "porto_tempo_medio_historico",
        ]
    }

    api_status = {
        "clima_ok": True,   # ✅
        "ais_ok": False,    # ❌ CRÍTICO
        "mare_ok": True,    # ✅
        "economia_ok": True, # ✅
        "historico_ok": False,
    }

    report = avaliar_qualidade_features(metadata, api_status)

    print(f"  Total features: {report.total_features}")
    print(f"  Confidence score: {report.confidence_score:.1f}%")
    print(f"  Critical issues: {len(report.critical_issues)}")
    print(f"  Warnings: {len(report.warnings)}")

    # Validações
    assert 60 <= report.confidence_score < 80, \
        f"Score deve estar entre 60-80% no cenário médio, obteve {report.confidence_score:.1f}%"
    assert len(report.critical_issues) > 0, "Deve haver issue crítico (AIS indisponível)"

    print("\n  ✅ TESTE 5 PASSOU - Cenário médio avaliado corretamente")
    return True


def test_confidence_score_ranges():
    """Testa se os scores de confiança estão nos ranges esperados"""
    print("\n" + "="*70)
    print("TESTE 6: Ranges de Score de Confiança")
    print("="*70)

    scenarios = [
        ("Todas APIs OK", {"clima_ok": True, "ais_ok": True, "mare_ok": True, "economia_ok": True}, 80, 100),
        ("Sem AIS (crítico)", {"clima_ok": True, "ais_ok": False, "mare_ok": True, "economia_ok": True}, 60, 80),
        ("Sem nenhuma API", {"clima_ok": False, "ais_ok": False, "mare_ok": False, "economia_ok": False}, 0, 60),
    ]

    metadata = {
        "features": [
            "nome_porto", "mes", "temp_media_dia", "precipitacao_dia",
            "ais_navios_no_raio", "ais_fila_ao_largo",
            "navios_no_fundeio_na_chegada", "porto_tempo_medio_historico",
        ]
    }

    for scenario_name, api_status, min_score, max_score in scenarios:
        report = avaliar_qualidade_features(metadata, api_status)
        score = report.confidence_score

        print(f"  {scenario_name:25s} → Score: {score:5.1f}% (esperado: {min_score}-{max_score}%)")

        assert min_score <= score <= max_score, \
            f"{scenario_name}: Score {score:.1f}% fora do range esperado [{min_score}-{max_score}%]"

    print("\n  ✅ TESTE 6 PASSOU - Ranges de confiança corretos")
    return True


def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "="*70)
    print("INICIANDO TESTES DA FASE 2 - SISTEMA DE VALIDAÇÃO")
    print("="*70)

    tests = [
        ("Enum FeatureQuality", test_feature_quality_enum),
        ("Dataclass FeatureReport", test_feature_report_dataclass),
        ("Cenário Perfeito", test_avaliar_qualidade_cenario_perfeito),
        ("Cenário Ruim", test_avaliar_qualidade_cenario_ruim),
        ("Cenário Médio", test_avaliar_qualidade_cenario_medio),
        ("Ranges de Confiança", test_confidence_score_ranges),
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
        print("\n✅ Sistema de validação da Fase 2 está funcionando corretamente.")
        print("✅ Rastreamento de qualidade de features implementado.")
        print("✅ Score de confiança sendo calculado corretamente.")
        print("✅ Avisos críticos e warnings sendo gerados adequadamente.")
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
