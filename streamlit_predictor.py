#!/usr/bin/env python3
"""
Interface Streamlit para Previsão de Fila Portuária com Enriquecimento Automático

Sistema completo de previsão que:
- Usa modelos completos (VEGETAL com qualidade >= 80%) ou light
- Enriquece automaticamente dados do scraping
- Não depende de lineups históricos (opcional)
- API de clima gratuita (Open-Meteo)
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Importar o predictor enriquecido
from predictor_enriched import EnrichedPredictor, PORTOS, CATEGORIAS

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Previsão de Fila Portuária",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INICIALIZAR PREDICTOR (CACHE)
# ============================================================================

@st.cache_resource
def load_predictor():
    """Carrega e cacheia o predictor."""
    return EnrichedPredictor()

predictor = load_predictor()

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="main-header">🚢 Previsão de Fila Portuária</div>', unsafe_allow_html=True)

st.markdown("""
<div class="info-box">
    <strong>ℹ️ Sistema de Previsão Enriquecido</strong><br>
    Este sistema usa modelos treinados com dados AIS reais e enriquece automaticamente suas previsões com:
    <ul>
        <li>🌤️ Clima em tempo real (Open-Meteo API)</li>
        <li>📊 Histórico de fila do porto</li>
        <li>🌾 Dados de safra e preços agrícolas</li>
        <li>🚢 Features AIS estimadas</li>
    </ul>
    <strong>Não é necessário API AIS em tempo real!</strong>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - CONFIGURAÇÕES
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configurações")

    # Modo avançado
    modo_avancado = st.checkbox("Modo Avançado", value=False)

    if modo_avancado:
        force_model = st.radio(
            "Forçar modelo:",
            ["Automático", "Complete", "Light"],
            help="Automático: usa complete para VEGETAL com qualidade >= 80%"
        )

        quality_score = st.slider(
            "Score de qualidade dos dados",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.1,
            help="Qualidade dos dados de entrada (0-1)"
        )
    else:
        force_model = "Automático"
        quality_score = 1.0

    st.markdown("---")

    # Info do sistema
    st.markdown("### 📊 Status do Sistema")
    st.success(f"✅ Predictor carregado")
    st.info(f"📦 Modelos: {len(predictor.models)}")
    st.info(f"📜 Histórico: {len(predictor.lineup_history)} lineups")

# ============================================================================
# TABS PRINCIPAIS
# ============================================================================

tab1, tab2, tab3 = st.tabs(["🔮 Nova Previsão", "📋 Previsão em Lote", "📊 Análise"])

# ============================================================================
# TAB 1: NOVA PREVISÃO
# ============================================================================

with tab1:
    st.header("Dados do Navio")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informações Básicas")

        porto = st.selectbox(
            "Porto de Destino *",
            options=list(PORTOS.keys()),
            index=0,
            help="Porto onde o navio irá atracar"
        )

        tipo_navio = st.selectbox(
            "Tipo de Navio",
            options=[
                "Bulk Carrier",
                "Tanker",
                "Chemical Tanker",
                "LPG Tanker",
                "General Cargo",
                "Container Ship",
                "Ore Carrier"
            ],
            index=0,
            help="Tipo do navio (opcional, mas melhora a previsão)"
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
                "Fosfato"
            ],
            index=0,
            help="Tipo de carga (ajuda a identificar o perfil)"
        )

    with col2:
        st.subheader("Características Técnicas")

        eta = st.date_input(
            "ETA (Estimated Time of Arrival) *",
            value=datetime.now() + timedelta(days=7),
            min_value=datetime.now(),
            max_value=datetime.now() + timedelta(days=90),
            help="Data estimada de chegada"
        )

        dwt = st.number_input(
            "DWT (Deadweight Tonnage)",
            min_value=1000.0,
            max_value=400000.0,
            value=75000.0,
            step=1000.0,
            help="Porte bruto do navio em toneladas"
        )

        calado = st.number_input(
            "Calado (metros)",
            min_value=1.0,
            max_value=30.0,
            value=12.5,
            step=0.5,
            help="Calado do navio em metros"
        )

        toneladas = st.number_input(
            "Toneladas de Carga",
            min_value=1000.0,
            max_value=300000.0,
            value=50000.0,
            step=1000.0,
            help="Quantidade de carga em toneladas"
        )

    st.markdown("---")

    # Botão de previsão
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        prever_button = st.button("🔮 Fazer Previsão", use_container_width=True, type="primary")

    if prever_button:
        with st.spinner("🔄 Enriquecendo dados e fazendo previsão..."):
            # Preparar dados do navio
            navio_data = {
                "porto": porto,
                "tipo": tipo_navio,
                "carga": natureza_carga,
                "eta": eta.strftime("%Y-%m-%d"),
                "dwt": dwt,
                "calado": calado,
                "toneladas": toneladas,
            }

            # Converter força de modelo
            force_param = None
            if force_model == "Complete":
                force_param = "complete"
            elif force_model == "Light":
                force_param = "light"

            # Fazer previsão
            try:
                resultado = predictor.predict(
                    navio_data,
                    quality_score=quality_score,
                    force_model=force_param
                )

                st.markdown("---")
                st.header("📊 Resultado da Previsão")

                # Exibir resultado principal
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "⏱️ Tempo de Espera",
                        f"{resultado['tempo_espera_previsto_horas']:.1f}h",
                        delta=f"{resultado['tempo_espera_previsto_dias']:.1f} dias"
                    )

                with col2:
                    st.metric(
                        "📋 Categoria",
                        resultado['categoria_fila'].split('(')[0].strip()
                    )

                with col3:
                    st.metric(
                        "🎯 Confiança",
                        f"{resultado['confianca']*100:.1f}%"
                    )

                with col4:
                    st.metric(
                        "📦 Perfil",
                        resultado['perfil']
                    )

                # Detalhes da previsão
                st.markdown("---")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🔧 Detalhes Técnicos")

                    details_html = f"""
                    <div class="metric-card">
                        <strong>Modelo Usado:</strong> {resultado['modelo_usado'].upper()}<br>
                        <strong>Features Calculadas:</strong> {resultado['features_calculadas']}<br>
                        <strong>Porto:</strong> {resultado['porto']}<br>
                        <strong>ETA:</strong> {resultado['eta']}<br>
                    </div>
                    """
                    st.markdown(details_html, unsafe_allow_html=True)

                with col2:
                    st.markdown("### 📈 Interpretação")

                    # Interpretação baseada no tempo
                    tempo_horas = resultado['tempo_espera_previsto_horas']

                    if tempo_horas < 48:
                        msg = "🟢 **Fila Rápida**: Tempo de espera abaixo de 2 dias. Condições favoráveis."
                        st.markdown(f'<div class="success-box">{msg}</div>', unsafe_allow_html=True)
                    elif tempo_horas < 168:
                        msg = "🟡 **Fila Normal**: Tempo de espera entre 2-7 dias. Dentro do esperado."
                        st.markdown(f'<div class="warning-box">{msg}</div>', unsafe_allow_html=True)
                    else:
                        msg = "🔴 **Fila Longa**: Tempo de espera acima de 7 dias. Porto congestionado."
                        st.markdown(f'<div class="warning-box">{msg}</div>', unsafe_allow_html=True)

                # Mostrar features calculadas em modo avançado
                if modo_avancado:
                    with st.expander("🔍 Ver Features Calculadas"):
                        # Obter features enriquecidas
                        features, perfil = predictor.enrich_features(
                            navio_data,
                            use_complete_model=(resultado['modelo_usado'] == 'complete')
                        )

                        # Mostrar em formato tabela
                        df_features = pd.DataFrame([
                            {"Feature": k, "Valor": v}
                            for k, v in list(features.items())[:20]  # Primeiras 20
                        ])

                        st.dataframe(df_features, use_container_width=True)

                        st.info(f"Total de {len(features)} features calculadas automaticamente")

            except Exception as e:
                st.error(f"❌ Erro ao fazer previsão: {e}")
                st.exception(e)

# ============================================================================
# TAB 2: PREVISÃO EM LOTE
# ============================================================================

with tab2:
    st.header("📋 Previsão em Lote")

    st.info("Faça upload de um arquivo CSV/Excel com múltiplos navios para previsão em lote.")

    # Template
    st.markdown("### 📄 Formato do Arquivo")

    template_df = pd.DataFrame({
        "porto": ["Santos", "Paranaguá"],
        "tipo": ["Bulk Carrier", "Tanker"],
        "carga": ["Soja em Graos", "Ureia"],
        "eta": ["2026-02-15", "2026-03-01"],
        "dwt": [75000, 45000],
        "calado": [12.5, 10.0],
        "toneladas": [60000, 35000],
    })

    st.dataframe(template_df, use_container_width=True)

    # Download template
    csv = template_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Template CSV",
        data=csv,
        file_name="template_previsao_lote.csv",
        mime="text/csv"
    )

    st.markdown("---")

    # Upload de arquivo
    uploaded_file = st.file_uploader(
        "Fazer upload do arquivo",
        type=["csv", "xlsx"],
        help="Arquivo CSV ou Excel com os dados dos navios"
    )

    if uploaded_file is not None:
        try:
            # Ler arquivo
            if uploaded_file.name.endswith('.csv'):
                df_navios = pd.read_csv(uploaded_file)
            else:
                df_navios = pd.read_excel(uploaded_file)

            st.success(f"✅ Arquivo carregado: {len(df_navios)} navios encontrados")

            # Mostrar preview
            with st.expander("👁️ Preview dos dados"):
                st.dataframe(df_navios.head(10), use_container_width=True)

            # Botão de processar
            if st.button("🚀 Processar Lote", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                resultados = []

                for idx, row in df_navios.iterrows():
                    # Atualizar progresso
                    progress = (idx + 1) / len(df_navios)
                    progress_bar.progress(progress)
                    status_text.text(f"Processando navio {idx+1}/{len(df_navios)}...")

                    # Preparar dados
                    navio_data = {
                        "porto": row.get("porto", "Santos"),
                        "tipo": row.get("tipo", "Bulk Carrier"),
                        "carga": row.get("carga", "Soja em Graos"),
                        "eta": str(row.get("eta", datetime.now().strftime("%Y-%m-%d"))),
                        "dwt": float(row.get("dwt", 75000)),
                        "calado": float(row.get("calado", 12.5)),
                        "toneladas": float(row.get("toneladas", 50000)),
                    }

                    # Fazer previsão
                    try:
                        resultado = predictor.predict(navio_data)
                        resultados.append({
                            "Porto": resultado['porto'],
                            "ETA": resultado['eta'],
                            "Perfil": resultado['perfil'],
                            "Tempo_Espera_Horas": resultado['tempo_espera_previsto_horas'],
                            "Tempo_Espera_Dias": resultado['tempo_espera_previsto_dias'],
                            "Categoria": resultado['categoria_fila'],
                            "Confianca": resultado['confianca'],
                            "Modelo": resultado['modelo_usado'],
                        })
                    except Exception as e:
                        st.warning(f"⚠️ Erro no navio {idx+1}: {e}")

                progress_bar.empty()
                status_text.empty()

                # Mostrar resultados
                if resultados:
                    st.success(f"✅ {len(resultados)} previsões concluídas!")

                    df_resultados = pd.DataFrame(resultados)

                    st.dataframe(df_resultados, use_container_width=True)

                    # Download resultados
                    csv_result = df_resultados.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar Resultados",
                        data=csv_result,
                        file_name=f"previsoes_lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {e}")
            st.exception(e)

# ============================================================================
# TAB 3: ANÁLISE
# ============================================================================

with tab3:
    st.header("📊 Análise dos Modelos")

    st.markdown("### 🎯 Performance dos Modelos")

    # Criar DataFrame com métricas
    metricas = []

    for perfil in ["VEGETAL", "MINERAL", "FERTILIZANTE"]:
        if perfil in predictor.models:
            # Light model
            light_meta = predictor.models[perfil]["light_meta"]
            metricas.append({
                "Perfil": perfil,
                "Modelo": "Light (15 features)",
                "MAE (horas)": f"{light_meta['metrics']['test_mae']:.1f}",
                "R²": f"{light_meta['metrics']['test_r2']:.3f}",
                "Accuracy": f"{light_meta['metrics']['test_acc']*100:.1f}%",
                "Amostras": light_meta.get('num_samples', 'N/A'),
            })

            # Complete model (se existir)
            if predictor.models[perfil]["has_complete"]:
                complete_meta = predictor.models[perfil]["complete_meta"]
                metricas.append({
                    "Perfil": perfil,
                    "Modelo": f"Complete ({len(complete_meta['features'])} features)",
                    "MAE (horas)": f"{complete_meta['metrics']['test_mae']:.1f}",
                    "R²": f"{complete_meta['metrics']['test_r2']:.3f}",
                    "Accuracy": f"{complete_meta['metrics']['test_acc']*100:.1f}%",
                    "Amostras": complete_meta.get('num_samples', 'N/A'),
                })

    df_metricas = pd.DataFrame(metricas)
    st.dataframe(df_metricas, use_container_width=True)

    st.markdown("---")

    st.markdown("### 📋 Perfis de Carga")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🌾 VEGETAL")
        st.markdown("""
        - Soja, Milho, Farelo
        - Açúcar, Trigo, Cevada
        - **MAE:** ~19h (light) / ~9h (complete)
        - **R²:** 0.982 (light) / 0.997 (complete)
        """)

    with col2:
        st.markdown("#### ⛏️ MINERAL")
        st.markdown("""
        - Minério de Ferro
        - Bauxita, Manganês
        - **MAE:** ~16h (light)
        - **R²:** 0.985 (light)
        """)

    with col3:
        st.markdown("#### 🧪 FERTILIZANTE")
        st.markdown("""
        - Ureia, KCL, NPK
        - Fosfatos, Químicos
        - **MAE:** ~60h (light)
        - **R²:** 0.838 (light)
        """)

    st.markdown("---")

    st.markdown("### ℹ️ Sobre o Sistema")

    st.info("""
    **Sistema de Previsão com Enriquecimento Automático**

    Este sistema usa modelos treinados com dados AIS reais (308 eventos, 8 portos) e enriquece
    automaticamente as previsões com features calculadas:

    - **Temporais:** mês, dia da semana, período de safra
    - **Climáticas:** temperatura, precipitação, vento (API Open-Meteo gratuita)
    - **Históricas:** fila do porto, tempo médio histórico
    - **Agrícolas:** produção, preços, safra (tabelas pré-carregadas)
    - **AIS:** estimativas de navios no raio, velocidade, distância

    **Modelo Completo vs Light:**
    - **VEGETAL com qualidade >= 80%:** usa modelo completo (51 features, MAE 9h)
    - **Outros casos:** usa modelo light (15 features, MAE 16-60h)

    **Custo:** €0-20/mês (apenas API de clima gratuita)
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.9em;">
    🚢 Sistema de Previsão de Fila Portuária v2.0<br>
    Desenvolvido com dados AIS reais | Modelos LightGBM + XGBoost
</div>
""", unsafe_allow_html=True)
