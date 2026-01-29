"""
Interface Streamlit para Sistema de Previsão de Fila Portuária

Sistema completo que usa predictor_enriched.py para fazer previsões
sem necessidade de API AIS em tempo real.

Funcionalidades:
- Entrada manual de dados do navio
- Upload de CSV com múltiplos navios
- Seleção automática de modelo (complete vs light)
- Visualização de resultados e features calculadas
- Comparação de múltiplos navios
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# Importar o preditor enriquecido
try:
    from predictor_enriched import EnrichedPredictor, PORTOS, CATEGORIAS
except ImportError:
    st.error("❌ Erro ao importar predictor_enriched.py")
    st.stop()


# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Previsão de Fila Portuária",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

st.markdown(
    """
    <style>
    .big-metric {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# CACHE DO PREDITOR
# ============================================================================


@st.cache_resource
def load_predictor():
    """Carrega o preditor uma única vez."""
    with st.spinner("Carregando modelos..."):
        predictor = EnrichedPredictor()
    return predictor


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def format_hours_to_days(horas):
    """Formata horas para dias e horas."""
    dias = int(horas // 24)
    horas_rest = int(horas % 24)

    if dias == 0:
        return f"{horas:.1f}h"
    elif horas_rest == 0:
        return f"{dias}d"
    else:
        return f"{dias}d {horas_rest}h"


def get_categoria_color(categoria_index):
    """Retorna cor baseada na categoria."""
    colors = {
        0: "#28a745",  # Verde (0-2 dias)
        1: "#ffc107",  # Amarelo (2-7 dias)
        2: "#fd7e14",  # Laranja (7-14 dias)
        3: "#dc3545",  # Vermelho (14+ dias)
    }
    return colors.get(categoria_index, "#6c757d")


def show_prediction_card(resultado):
    """Mostra card com resultado da previsão."""
    st.markdown("### 📊 Resultado da Previsão")

    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-label">Tempo de Espera</div>
            <div class="big-metric">{format_hours_to_days(resultado['tempo_espera_previsto_horas'])}</div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        color = get_categoria_color(resultado['categoria_index'])
        st.markdown(
            f"""
            <div class="metric-label">Categoria</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: {color};">
                {resultado['categoria_fila']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        confianca_pct = resultado['confianca'] * 100
        st.markdown(
            f"""
            <div class="metric-label">Confiança</div>
            <div style="font-size: 1.5rem; font-weight: bold;">
                {confianca_pct:.1f}%
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-label">Perfil</div>
            <div style="font-size: 1.5rem; font-weight: bold;">
                {resultado['perfil']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Informações adicionais
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Porto", resultado['porto'])

    with col2:
        st.metric("ETA", resultado['eta'])

    with col3:
        modelo_icon = "🎯" if resultado['modelo_usado'] == "complete" else "⚡"
        modelo_label = "Completo (51 features)" if resultado['modelo_usado'] == "complete" else "Light (15 features)"
        st.metric(f"{modelo_icon} Modelo", modelo_label)


# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================


def main():
    """Interface principal do Streamlit."""

    # Título
    st.title("🚢 Previsão de Fila Portuária")
    st.markdown("Sistema de previsão de tempo de espera usando modelos treinados com dados AIS reais")

    # Carregar preditor
    try:
        predictor = load_predictor()

        # Mostrar estatísticas do sistema
        with st.expander("ℹ️ Informações do Sistema", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Modelos Disponíveis**")
                st.markdown("- ✅ VEGETAL (Grãos)")
                st.markdown("- ✅ MINERAL (Minério)")
                st.markdown("- ✅ FERTILIZANTE (Químicos)")

            with col2:
                st.markdown("**Performance (MAE)**")
                st.markdown("- VEGETAL: **8.7h** (completo)")
                st.markdown("- MINERAL: **16.4h** (light)")
                st.markdown("- FERTILIZANTE: **60.3h** (light)")

            with col3:
                st.markdown("**Dados Utilizados**")
                st.markdown(f"- Lineups históricos: {len(predictor.lineup_history)}")
                st.markdown(f"- Portos cobertos: {len(PORTOS)}")
                st.markdown(f"- Features calculadas: 15-51")

    except Exception as e:
        st.error(f"❌ Erro ao carregar preditor: {e}")
        st.stop()

    # Sidebar - Modo de entrada
    st.sidebar.header("⚙️ Configurações")

    modo_entrada = st.sidebar.radio(
        "Modo de Entrada",
        ["📝 Entrada Manual", "📤 Upload CSV"],
        index=0,
    )

    # Configurações avançadas
    with st.sidebar.expander("🔧 Configurações Avançadas", expanded=False):
        force_model = st.selectbox(
            "Forçar Modelo",
            ["Automático", "Completo (51 features)", "Light (15 features)"],
            index=0,
        )

        quality_score = st.slider(
            "Quality Score",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.1,
            help="Score de qualidade dos dados (0-1). Valores >= 0.8 ativam modelo completo para VEGETAL.",
        )

        show_features = st.checkbox("Mostrar Features Calculadas", value=False)

    # Converter seleção de modelo
    force_model_param = None
    if force_model == "Completo (51 features)":
        force_model_param = "complete"
    elif force_model == "Light (15 features)":
        force_model_param = "light"

    # ========================================================================
    # MODO 1: ENTRADA MANUAL
    # ========================================================================

    if modo_entrada == "📝 Entrada Manual":
        st.markdown("## Dados do Navio")

        col1, col2 = st.columns(2)

        with col1:
            porto = st.selectbox(
                "Porto de Destino *",
                options=list(PORTOS.keys()),
                index=0,
            )

            tipo_navio = st.selectbox(
                "Tipo de Navio",
                options=[
                    "Bulk Carrier",
                    "Tanker",
                    "Chemical Tanker",
                    "Ore Carrier",
                    "General Cargo",
                    "Container Ship",
                ],
                index=0,
            )

            natureza_carga = st.selectbox(
                "Natureza da Carga",
                options=[
                    "Soja em Graos",
                    "Milho",
                    "Farelo de Soja",
                    "Acucar",
                    "Trigo",
                    "Minerio de Ferro",
                    "Bauxita",
                    "Manganes",
                    "Ureia",
                    "KCL",
                    "NPK",
                    "Fosfato",
                ],
                index=0,
            )

        with col2:
            eta = st.date_input(
                "ETA (Estimated Time of Arrival) *",
                value=datetime.now() + timedelta(days=7),
                min_value=datetime.now().date(),
                max_value=datetime.now().date() + timedelta(days=365),
            )

            dwt = st.number_input(
                "DWT (Deadweight Tonnage)",
                min_value=1000,
                max_value=400000,
                value=75000,
                step=1000,
                help="Capacidade de carga do navio em toneladas",
            )

            calado = st.number_input(
                "Calado (metros)",
                min_value=1.0,
                max_value=25.0,
                value=12.5,
                step=0.5,
                help="Profundidade do navio submerso",
            )

        toneladas = st.number_input(
            "Movimentação Total (toneladas)",
            min_value=1000,
            max_value=400000,
            value=50000,
            step=1000,
            help="Quantidade total de carga a ser movimentada",
        )

        # Botão de previsão
        st.markdown("---")

        if st.button("🔮 Fazer Previsão", type="primary", use_container_width=True):
            # Preparar dados
            navio_data = {
                "porto": porto,
                "tipo": tipo_navio,
                "carga": natureza_carga,
                "eta": eta.strftime("%Y-%m-%d"),
                "dwt": dwt,
                "calado": calado,
                "toneladas": toneladas,
            }

            # Fazer previsão
            with st.spinner("Calculando previsão..."):
                try:
                    resultado = predictor.predict(
                        navio_data,
                        quality_score=quality_score,
                        force_model=force_model_param,
                    )

                    # Mostrar resultado
                    st.success("✅ Previsão concluída com sucesso!")
                    show_prediction_card(resultado)

                    # Mostrar features calculadas
                    if show_features:
                        st.markdown("---")
                        st.markdown("### 🔍 Features Calculadas")

                        # Enriquecer features para visualização
                        features, perfil = predictor.enrich_features(
                            navio_data,
                            use_complete_model=(resultado['modelo_usado'] == 'complete')
                        )

                        # Agrupar features por categoria
                        feature_groups = {
                            "Básicas": [k for k in features.keys() if any(x in k for x in ['nome_', 'tipo_', 'natureza', 'movimentacao'])],
                            "Temporais": [k for k in features.keys() if any(x in k for x in ['mes', 'dia_', 'periodo'])],
                            "Climáticas": [k for k in features.keys() if any(x in k for x in ['temp', 'precip', 'vento', 'umidade'])],
                            "Históricas": [k for k in features.keys() if any(x in k for x in ['navios_', 'tempo_espera', 'porto_tempo'])],
                            "AIS": [k for k in features.keys() if 'ais_' in k],
                        }

                        for group_name, group_features in feature_groups.items():
                            if group_features:
                                with st.expander(f"📋 {group_name} ({len(group_features)} features)"):
                                    df_features = pd.DataFrame([
                                        {"Feature": k, "Valor": features.get(k, 0)}
                                        for k in group_features
                                    ])
                                    st.dataframe(df_features, use_container_width=True)

                except Exception as e:
                    st.error(f"❌ Erro ao fazer previsão: {e}")
                    st.exception(e)

    # ========================================================================
    # MODO 2: UPLOAD CSV
    # ========================================================================

    elif modo_entrada == "📤 Upload CSV":
        st.markdown("## Upload de Navios em Lote")

        st.markdown(
            """
            <div class="info-box">
            <strong>ℹ️ Formato do CSV:</strong><br>
            O arquivo deve conter as seguintes colunas:<br>
            - <code>porto</code> (obrigatório): Nome do porto<br>
            - <code>tipo</code>: Tipo de navio<br>
            - <code>carga</code>: Natureza da carga<br>
            - <code>eta</code> (obrigatório): Data de chegada (YYYY-MM-DD)<br>
            - <code>dwt</code>: Deadweight tonnage<br>
            - <code>calado</code>: Calado em metros<br>
            - <code>toneladas</code>: Movimentação total<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Template CSV
        col1, col2 = st.columns([3, 1])

        with col2:
            template_df = pd.DataFrame({
                "porto": ["Santos", "Paranaguá"],
                "tipo": ["Bulk Carrier", "Tanker"],
                "carga": ["Soja em Graos", "Ureia"],
                "eta": ["2026-02-15", "2026-03-01"],
                "dwt": [75000, 45000],
                "calado": [12.5, 10.0],
                "toneladas": [60000, 35000],
            })

            csv_template = template_df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download Template",
                data=csv_template,
                file_name="template_navios.csv",
                mime="text/csv",
            )

        with col1:
            uploaded_file = st.file_uploader(
                "Selecione o arquivo CSV",
                type=["csv"],
                help="Upload de arquivo CSV com dados dos navios",
            )

        if uploaded_file is not None:
            try:
                # Ler CSV
                df = pd.read_csv(uploaded_file)

                st.success(f"✅ Arquivo carregado: {len(df)} navios encontrados")

                # Validar colunas obrigatórias
                required_cols = ["porto", "eta"]
                missing_cols = [col for col in required_cols if col not in df.columns]

                if missing_cols:
                    st.error(f"❌ Colunas obrigatórias faltando: {missing_cols}")
                    st.stop()

                # Mostrar preview
                with st.expander("👀 Preview dos Dados", expanded=True):
                    st.dataframe(df, use_container_width=True)

                # Botão de processar
                if st.button("🚀 Processar Todos", type="primary", use_container_width=True):
                    resultados = []

                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for idx, row in df.iterrows():
                        # Atualizar progresso
                        progress = (idx + 1) / len(df)
                        progress_bar.progress(progress)
                        status_text.text(f"Processando navio {idx + 1}/{len(df)}...")

                        # Preparar dados
                        navio_data = {
                            "porto": row["porto"],
                            "tipo": row.get("tipo", "Bulk Carrier"),
                            "carga": row.get("carga", "Soja em Graos"),
                            "eta": row["eta"],
                            "dwt": row.get("dwt", 75000),
                            "calado": row.get("calado", 12.5),
                            "toneladas": row.get("toneladas", 50000),
                        }

                        # Fazer previsão
                        try:
                            resultado = predictor.predict(
                                navio_data,
                                quality_score=quality_score,
                                force_model=force_model_param,
                            )
                            resultados.append(resultado)
                        except Exception as e:
                            st.warning(f"⚠️ Erro no navio {idx + 1}: {e}")
                            resultados.append({
                                "erro": str(e),
                                "porto": navio_data["porto"],
                                "eta": navio_data["eta"],
                            })

                    # Limpar progresso
                    progress_bar.empty()
                    status_text.empty()

                    # Mostrar resultados
                    st.success(f"✅ Processamento concluído: {len(resultados)} previsões")

                    # Criar DataFrame de resultados
                    df_results = pd.DataFrame(resultados)

                    # Estatísticas
                    st.markdown("### 📈 Estatísticas")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric(
                            "Tempo Médio",
                            format_hours_to_days(df_results["tempo_espera_previsto_horas"].mean())
                        )

                    with col2:
                        st.metric(
                            "Tempo Máximo",
                            format_hours_to_days(df_results["tempo_espera_previsto_horas"].max())
                        )

                    with col3:
                        st.metric(
                            "Confiança Média",
                            f"{df_results['confianca'].mean() * 100:.1f}%"
                        )

                    with col4:
                        perfil_mais_comum = df_results["perfil"].mode()[0] if len(df_results) > 0 else "N/A"
                        st.metric("Perfil Mais Comum", perfil_mais_comum)

                    # Tabela de resultados
                    st.markdown("### 📊 Resultados Detalhados")

                    # Adicionar formatação
                    df_display = df_results.copy()
                    df_display["tempo_espera_previsto_horas"] = df_display["tempo_espera_previsto_horas"].apply(
                        lambda x: format_hours_to_days(x)
                    )
                    df_display["confianca"] = df_display["confianca"].apply(
                        lambda x: f"{x*100:.1f}%"
                    )

                    st.dataframe(
                        df_display[[
                            "porto", "eta", "perfil", "tempo_espera_previsto_horas",
                            "categoria_fila", "confianca", "modelo_usado"
                        ]],
                        use_container_width=True
                    )

                    # Download dos resultados
                    csv_results = df_results.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download Resultados (CSV)",
                        data=csv_results,
                        file_name=f"previsoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )

            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {e}")
                st.exception(e)

    # ========================================================================
    # FOOTER
    # ========================================================================

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 0.9rem;">
        🚢 Sistema de Previsão de Fila Portuária |
        Modelos treinados com dados AIS reais (308 eventos) |
        Sem necessidade de API real-time (economia de €500+/mês)
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
