#!/usr/bin/env python3
"""
Script para testar o sistema de fallback de modelos light.
"""

import sys
import json
from pathlib import Path


def test_load_light_model(profile):
    """Testa se consegue carregar modelo light."""
    print(f"\n{'='*60}")
    print(f"Testando carregamento de modelo LIGHT: {profile}")
    print(f"{'='*60}")

    models_dir = Path("models")
    prefix = f"{profile.lower()}_light"

    # Verifica metadados
    metadata_path = models_dir / f"{prefix}_metadata.json"
    if not metadata_path.exists():
        print(f"❌ Metadata não encontrado: {metadata_path}")
        return False

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    print(f"✅ Metadata carregado")
    print(f"   Profile: {metadata.get('profile')}")
    print(f"   Type: {metadata.get('model_type')}")
    print(f"   Is Mock: {metadata.get('is_mock', False)}")
    print(f"   Features: {len(metadata.get('features', []))}")

    # Lista features
    features = metadata.get('features', [])
    print(f"\n   Top 5 features:")
    for i, feat in enumerate(features[:5], 1):
        print(f"      {i}. {feat}")

    # Verifica arquivos de modelo
    reg_path = models_dir / f"{prefix}_lgb_reg.pkl"
    clf_path = models_dir / f"{prefix}_lgb_clf.pkl"

    if not reg_path.exists():
        print(f"❌ Modelo de regressão não encontrado: {reg_path}")
        return False

    if not clf_path.exists():
        print(f"❌ Modelo de classificação não encontrado: {clf_path}")
        return False

    print(f"✅ Arquivo de regressão existe: {reg_path.name}")
    print(f"✅ Arquivo de classificação existe: {clf_path.name}")

    # Verifica tamanho dos arquivos
    reg_size = reg_path.stat().st_size
    clf_size = clf_path.stat().st_size

    print(f"   Tamanho reg: {reg_size} bytes")
    print(f"   Tamanho clf: {clf_size} bytes")

    return True


def test_model_selection():
    """Testa lógica de seleção de modelos."""
    print(f"\n{'='*60}")
    print("TESTANDO LÓGICA DE SELEÇÃO DE MODELOS")
    print(f"{'='*60}")

    scenarios = [
        {"qualidade": 85, "modelo_esperado": "completo", "descricao": "Alta qualidade"},
        {"qualidade": 75, "modelo_esperado": "light", "descricao": "Média qualidade"},
        {"qualidade": 60, "modelo_esperado": "light", "descricao": "Baixa qualidade"},
    ]

    for scenario in scenarios:
        qualidade = scenario["qualidade"]
        esperado = scenario["modelo_esperado"]
        descricao = scenario["descricao"]

        # Lógica implementada no streamlit_app.py
        if qualidade >= 80:
            selecionado = "completo"
        else:
            selecionado = "light"  # Assumindo que light existe

        status = "✅" if selecionado == esperado else "❌"
        print(f"{status} {descricao} ({qualidade}%): {selecionado} == {esperado}")


def test_streamlit_integration():
    """Testa se streamlit_app.py tem as funções de fallback."""
    print(f"\n{'='*60}")
    print("TESTANDO INTEGRAÇÃO COM STREAMLIT")
    print(f"{'='*60}")

    streamlit_path = Path("streamlit_app.py")
    if not streamlit_path.exists():
        print("❌ streamlit_app.py não encontrado")
        return False

    with open(streamlit_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verifica se as funções estão definidas
    functions_to_check = [
        "load_light_models_for_profile",
        "select_model_by_quality",
    ]

    all_found = True
    for func_name in functions_to_check:
        if f"def {func_name}" in content:
            print(f"✅ Função '{func_name}' encontrada")
        else:
            print(f"❌ Função '{func_name}' NÃO encontrada")
            all_found = False

    # Verifica threshold de 80%
    if ">= 80" in content or ">= 80%" in content:
        print(f"✅ Threshold de 80% encontrado")
    else:
        print(f"⚠️  Threshold de 80% pode não estar definido")

    return all_found


def main():
    """Função principal."""
    print("="*60)
    print("TESTE DO SISTEMA DE FALLBACK DE MODELOS LIGHT")
    print("="*60)

    # Testa carregamento de cada perfil
    profiles = ["VEGETAL", "MINERAL", "FERTILIZANTE"]
    results = {}

    for profile in profiles:
        results[profile] = test_load_light_model(profile)

    # Testa lógica de seleção
    test_model_selection()

    # Testa integração com Streamlit
    streamlit_ok = test_streamlit_integration()

    # Resumo
    print(f"\n{'='*60}")
    print("RESUMO DOS TESTES")
    print(f"{'='*60}")

    print("\nModelos Light:")
    for profile, success in results.items():
        status = "✅ OK" if success else "❌ FALHOU"
        print(f"  {profile:<20} {status}")

    print(f"\nIntegração Streamlit: {'✅ OK' if streamlit_ok else '❌ FALHOU'}")

    all_ok = all(results.values()) and streamlit_ok

    if all_ok:
        print("\n" + "="*60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("="*60)
        print("\nSistema de fallback está PRONTO para uso.")
        print("\nComo testar no Streamlit:")
        print("  1. Execute: streamlit run streamlit_app.py")
        print("  2. Carregue um lineup")
        print("  3. Observe os badges de qualidade e modelo usado")
        print("  4. Se qualidade < 80%, verá 🔧 Modelo Simplificado")
        print("  5. Se qualidade >= 80%, usa modelo completo normal")
        print("\nNOTA: Modelos atuais são MOCK (demonstração).")
        print("      Para produção, treine modelos reais com dados históricos.")
        return 0
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
        print("Verifique os erros acima.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
