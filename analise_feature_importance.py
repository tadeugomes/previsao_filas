#!/usr/bin/env python3
"""
Análise de Importância de Features - Fase 4
============================================

Script para analisar a importância de features nos modelos de previsão
de tempo de espera de navios. Usa feature_importances_ dos modelos
tree-based e SHAP values para identificar as features mais relevantes.

Objetivo: Identificar top 15-20 features para possível modelo simplificado.
"""

import pickle
from pathlib import Path
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

SHAP_AVAILABLE = False  # Desabilitado para versão standalone


class FeatureImportanceAnalyzer:
    """Analisa importância de features em modelos de previsão."""

    def __init__(self, models_dir: Path = Path("models")):
        self.models_dir = models_dir
        self.results = {}

    def load_model(self, profile: str) -> Dict:
        """Carrega modelo e metadados para um perfil específico."""
        # Tenta diferentes nomes de arquivo
        possible_paths = [
            self.models_dir / f"{profile.lower()}_ensemble_model.pkl",
            self.models_dir / f"{profile.lower()}_ensemble_reg.pkl",
        ]

        model_path = None
        for path in possible_paths:
            if path.exists():
                model_path = path
                break

        if not model_path:
            print(f"❌ Modelo não encontrado para perfil {profile}")
            return None

        metadata_path = self.models_dir / f"{profile.lower()}_model_metadata.json"

        try:
            with open(model_path, 'rb') as f:
                models = pickle.load(f)

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            return {
                'models': models,
                'metadata': metadata,
                'profile': profile
            }
        except Exception as e:
            print(f"❌ Erro ao carregar modelo {profile}: {e}")
            return None

    def extract_tree_importance(self, model, feature_names: List[str]) -> List[Dict]:
        """Extrai importância de features de modelos tree-based."""
        importance_dict = {}

        # LightGBM
        if hasattr(model, 'lgb_model') and model.lgb_model is not None:
            lgb_importance = model.lgb_model.feature_importances_
            importance_dict['lgb'] = dict(zip(feature_names, lgb_importance))

        # XGBoost
        if hasattr(model, 'xgb_model') and model.xgb_model is not None:
            try:
                xgb_importance = model.xgb_model.feature_importances_
                # XGBoost pode ter features diferentes, precisamos mapear
                if len(xgb_importance) == len(feature_names):
                    importance_dict['xgb'] = dict(zip(feature_names, xgb_importance))
            except Exception as e:
                print(f"⚠️  Não foi possível extrair importância do XGBoost: {e}")

        # Modelo único (fallback)
        if not importance_dict and hasattr(model, 'feature_importances_'):
            importance_dict['model'] = dict(zip(feature_names, model.feature_importances_))

        # Converte para lista de dicts
        if not importance_dict:
            return []

        # Calcula média de importância
        result = []
        for feature in feature_names:
            importances = [importance_dict[model_name].get(feature, 0)
                          for model_name in importance_dict.keys()]
            mean_imp = sum(importances) / len(importances) if importances else 0

            result.append({
                'feature': feature,
                'mean_importance': float(mean_imp),
                'combined_importance': float(mean_imp),
                **{f'{model_name}_importance': importance_dict[model_name].get(feature, 0)
                   for model_name in importance_dict.keys()}
            })

        # Ordena por importância
        result.sort(key=lambda x: x['combined_importance'], reverse=True)

        return result

    def calculate_shap_importance(self, model, X_sample, max_samples: int = 100):
        """SHAP desabilitado nesta versão standalone."""
        return []

    def analyze_profile(self, profile: str) -> Dict:
        """Analisa importância de features para um perfil específico."""
        print(f"\n{'='*60}")
        print(f"Analisando perfil: {profile}")
        print(f"{'='*60}")

        # Carrega modelo
        model_data = self.load_model(profile)
        if not model_data:
            return None

        models = model_data['models']
        metadata = model_data['metadata']
        feature_names = metadata.get('features', [])

        print(f"✓ Modelo carregado: {len(feature_names)} features")

        # Extrai importância tree-based
        model_obj = models.get('model_ensemble') or models.get('model_reg')
        if model_obj is None:
            print("❌ Nenhum modelo encontrado")
            return None

        tree_importance = self.extract_tree_importance(model_obj, feature_names)

        if not tree_importance:
            print("❌ Não foi possível extrair importância de features")
            return None

        print(f"✓ Importância tree-based calculada")

        # Adiciona categorias
        for item in tree_importance:
            item['categoria'] = self.categorize_feature(item['feature'])

        self.results[profile] = {
            'importance': tree_importance,
            'total_features': len(feature_names),
            'metadata': metadata
        }

        return self.results[profile]

    def categorize_feature(self, feature_name: str) -> str:
        """Categoriza feature por tipo de dado."""
        feature_lower = feature_name.lower()

        if any(x in feature_lower for x in ['temp', 'precipitacao', 'vento', 'umidade',
                                              'chuva', 'clima', 'wave', 'pressao', 'ressaca']):
            return 'Clima'
        elif any(x in feature_lower for x in ['ais', 'navio', 'fila', 'fundeio']):
            return 'AIS/Fila'
        elif any(x in feature_lower for x in ['mare', 'astronomica']):
            return 'Maré'
        elif any(x in feature_lower for x in ['producao', 'preco', 'soja', 'milho',
                                                'algodao', 'economia', 'pressao']):
            return 'Economia'
        elif any(x in feature_lower for x in ['porto', 'terminal', 'berco']):
            return 'Porto'
        elif any(x in feature_lower for x in ['mes', 'dia', 'semana', 'ano', 'safra', 'periodo']):
            return 'Temporal'
        elif any(x in feature_lower for x in ['carga', 'mercadoria', 'flag', 'natureza',
                                                'movimentacao', 'dwt', 'tonelada']):
            return 'Carga'
        elif any(x in feature_lower for x in ['tempo_espera', 'historico', 'media']):
            return 'Histórico'
        else:
            return 'Outros'

    def print_top_features(self, profile: str, top_n: int = 20):
        """Imprime top N features mais importantes."""
        if profile not in self.results:
            print(f"❌ Perfil {profile} não foi analisado")
            return

        result = self.results[profile]
        importance = result['importance']

        print(f"\n{'='*80}")
        print(f"TOP {top_n} FEATURES MAIS IMPORTANTES - {profile}")
        print(f"{'='*80}")
        print(f"{'Rank':<5} {'Feature':<40} {'Categoria':<15} {'Importância':<12}")
        print(f"{'-'*80}")

        for i, item in enumerate(importance[:top_n], 1):
            print(f"{i:<5} {item['feature']:<40} {item['categoria']:<15} "
                  f"{item['combined_importance']:.6f}")

        # Resumo por categoria
        print(f"\n{'='*80}")
        print("RESUMO POR CATEGORIA (Top 20)")
        print(f"{'='*80}")

        top_20 = importance[:top_n]
        categoria_counts = {}
        for item in top_20:
            cat = item['categoria']
            categoria_counts[cat] = categoria_counts.get(cat, 0) + 1

        for cat, count in sorted(categoria_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / top_n) * 100
            print(f"{cat:<20} {count:>3} features ({pct:>5.1f}%)")

    def generate_report(self, output_file: str = "FASE4_ANALISE_FEATURES.md"):
        """Gera relatório markdown com os resultados."""
        report = []
        report.append("# Análise de Importância de Features - Fase 4")
        report.append("")
        report.append("**Data:** 2026-01-28")
        report.append("**Objetivo:** Identificar top 15-20 features para possível modelo simplificado")
        report.append("")
        report.append("---")
        report.append("")

        for profile in self.results:
            result = self.results[profile]
            importance = result['importance']

            report.append(f"## {profile}")
            report.append("")
            report.append(f"**Total de features:** {result['total_features']}")
            report.append("")

            # Top 20 features
            report.append("### Top 20 Features Mais Importantes")
            report.append("")
            report.append("| Rank | Feature | Categoria | Importância |")
            report.append("|------|---------|-----------|-------------|")

            for i, item in enumerate(importance[:20], 1):
                report.append(
                    f"| {i} | `{item['feature']}` | {item['categoria']} | "
                    f"{item['combined_importance']:.6f} |"
                )

            report.append("")

            # Resumo por categoria
            report.append("### Distribuição por Categoria (Top 20)")
            report.append("")

            top_20 = importance[:20]
            categoria_counts = {}
            for item in top_20:
                cat = item['categoria']
                categoria_counts[cat] = categoria_counts.get(cat, 0) + 1

            report.append("| Categoria | Quantidade | Porcentagem |")
            report.append("|-----------|------------|-------------|")

            for cat, count in sorted(categoria_counts.items(), key=lambda x: x[1], reverse=True):
                pct = (count / 20) * 100
                report.append(f"| {cat} | {count} | {pct:.1f}% |")

            report.append("")

            # Análise de cobertura
            report.append("### Análise de Cobertura")
            report.append("")

            total_importance = sum(item['combined_importance'] for item in importance)
            top_10_importance = sum(item['combined_importance'] for item in importance[:10])
            top_20_importance = sum(item['combined_importance'] for item in importance[:20])

            pct_10 = (top_10_importance / total_importance) * 100 if total_importance > 0 else 0
            pct_20 = (top_20_importance / total_importance) * 100 if total_importance > 0 else 0

            report.append(f"- Top 10 features cobrem **{pct_10:.1f}%** da importância total")
            report.append(f"- Top 20 features cobrem **{pct_20:.1f}%** da importância total")
            report.append("")

            # Recomendações
            report.append("### Features Recomendadas para Modelo Simplificado")
            report.append("")
            report.append("```python")
            report.append(f"FEATURES_SIMPLIFICADAS_{profile.upper()} = [")
            for item in importance[:15]:
                report.append(f'    "{item["feature"]}",  # {item["categoria"]}')
            report.append("]")
            report.append("```")
            report.append("")
            report.append("---")
            report.append("")

        # Análise comparativa
        report.append("## Análise Comparativa Entre Perfis")
        report.append("")

        # Features comuns no top 10
        if len(self.results) > 1:
            profiles_list = list(self.results.keys())
            common_features = set(
                item['feature'] for item in self.results[profiles_list[0]]['importance'][:10]
            )

            for profile in profiles_list[1:]:
                profile_top_10 = set(
                    item['feature'] for item in self.results[profile]['importance'][:10]
                )
                common_features &= profile_top_10

            report.append("### Features Comuns no Top 10 de Todos os Perfis")
            report.append("")

            if common_features:
                report.append("```python")
                report.append("FEATURES_CRITICAS_COMUNS = [")
                for feat in sorted(common_features):
                    report.append(f'    "{feat}",')
                report.append("]")
                report.append("```")
            else:
                report.append("⚠️ Não há features comuns no top 10 de todos os perfis.")

            report.append("")

        # Recomendações finais
        report.append("## Recomendações")
        report.append("")
        report.append("### 1. Modelo Simplificado Universal (15-20 features)")
        report.append("")
        report.append("Baseado na análise, recomenda-se treinar um modelo simplificado com:")
        report.append("")
        report.append("- **5-7 features de lineup/carga** (nome_porto, terminal, carga, DWT, mês)")
        report.append("- **3-4 features de fila** (navios_no_fundeio, tempo_medio_historico)")
        report.append("- **3-4 features de clima** (temp, precipitação, vento)")
        report.append("- **2-3 features temporais** (dia_semana, periodo_safra)")
        report.append("- **2-3 features de contexto** (AIS se disponível, flags de produto)")
        report.append("")

        report.append("### 2. Próximos Passos")
        report.append("")
        report.append("1. **Validar viabilidade:** Verificar se todas as features do top 20 são "
                     "obtíveis de forma confiável")
        report.append("2. **Re-treinar modelos:** Criar versões 'light' usando apenas top 15-20 features")
        report.append("3. **Comparar performance:** MAE/RMSE modelo completo vs simplificado")
        report.append("4. **Critério de sucesso:** Degradação < 10% de performance é aceitável")
        report.append("5. **Deployment:** Se bem-sucedido, substituir modelos em produção")
        report.append("")

        report.append("### 3. Impacto Esperado")
        report.append("")
        report.append("✅ **Vantagens:**")
        report.append("- Menos dependência de APIs externas")
        report.append("- Inferência mais rápida (menos features)")
        report.append("- Maior confiabilidade (features mais confiáveis)")
        report.append("- Mais explicável para usuários")
        report.append("")
        report.append("⚠️ **Riscos:**")
        report.append("- Possível perda de precisão (precisa validar)")
        report.append("- Perda de contexto detalhado (economia, maré oceânica, etc.)")
        report.append("")

        report.append("---")
        report.append("")
        report.append("**Fim da Análise**")

        # Salva relatório
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

        print(f"\n✓ Relatório salvo em: {output_file}")


def main():
    """Função principal."""
    print("="*60)
    print("ANÁLISE DE IMPORTÂNCIA DE FEATURES - FASE 4")
    print("="*60)

    analyzer = FeatureImportanceAnalyzer()

    # Perfis para analisar
    profiles = ['VEGETAL', 'MINERAL', 'FERTILIZANTE', 'PONTA_DA_MADEIRA']

    for profile in profiles:
        result = analyzer.analyze_profile(profile)

        if result:
            analyzer.print_top_features(profile, top_n=20)

    # Gera relatório final
    print("\n" + "="*60)
    print("Gerando relatório final...")
    print("="*60)

    analyzer.generate_report()

    print("\n✓ Análise concluída com sucesso!")
    print("\nResumo:")
    print(f"- {len(analyzer.results)} perfis analisados")
    print(f"- Relatório: FASE4_ANALISE_FEATURES.md")
    print(f"- SHAP: {'✓ Disponível' if SHAP_AVAILABLE else '✗ Não disponível'}")


if __name__ == "__main__":
    main()
