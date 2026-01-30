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

# Importar Path para manipulação de arquivos
LINEUP_HISTORY_PATH = Path("lineups_previstos/lineup_history.parquet")


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


def buscar_navio_por_imo(imo, predictor):
    """
    Busca informações do navio no lineup_history por IMO.

    Args:
        imo: Código IMO do navio (pode ser string ou número)
        predictor: Instância do EnrichedPredictor com lineup_history carregado

    Returns:
        Dict com informações do navio ou None se não encontrado
    """
    if not imo or predictor.lineup_history.empty:
        return None

    try:
        # Converter IMO para string e limpar
        imo_str = str(imo).strip()

        # Verificar se existe coluna IMO no lineup_history
        imo_cols = [col for col in predictor.lineup_history.columns if 'imo' in col.lower()]

        if not imo_cols:
            return None

        imo_col = imo_cols[0]

        # Buscar navio por IMO
        df = predictor.lineup_history.copy()
        df[imo_col] = df[imo_col].astype(str).str.strip()

        navio_rows = df[df[imo_col] == imo_str]

        if navio_rows.empty:
            return None

        # Pegar o registro mais recente
        if 'prev_chegada' in navio_rows.columns:
            navio_rows = navio_rows.sort_values('prev_chegada', ascending=False)

        navio = navio_rows.iloc[0]

        # Extrair informações relevantes
        resultado = {
            'imo': imo_str,
            'encontrado': True
        }

        # ETA do lineup
        if 'prev_chegada' in navio_rows.columns:
            eta_lineup = pd.to_datetime(navio['prev_chegada'], errors='coerce')
            if pd.notna(eta_lineup):
                resultado['eta_lineup'] = eta_lineup
                resultado['eta_lineup_str'] = eta_lineup.strftime('%Y-%m-%d %H:%M')

        # Nome do navio
        nome_cols = [col for col in navio_rows.columns if 'navio' in col.lower() or 'nome' in col.lower()]
        if nome_cols:
            resultado['nome_navio'] = str(navio[nome_cols[0]])

        # Porto
        if 'nome_porto' in navio_rows.columns:
            resultado['porto'] = str(navio['nome_porto'])
        elif 'porto' in navio_rows.columns:
            resultado['porto'] = str(navio['porto'])

        # DWT
        if 'dwt' in navio_rows.columns:
            resultado['dwt'] = float(navio['dwt']) if pd.notna(navio['dwt']) else None

        # Tipo de navio
        tipo_cols = [col for col in navio_rows.columns if 'tipo' in col.lower()]
        if tipo_cols:
            resultado['tipo_navio'] = str(navio[tipo_cols[0]])

        # Carga
        carga_cols = [col for col in navio_rows.columns if 'carga' in col.lower() or 'produto' in col.lower()]
        if carga_cols:
            resultado['carga'] = str(navio[carga_cols[0]])

        # Calado
        if 'calado' in navio_rows.columns:
            resultado['calado'] = float(navio['calado']) if pd.notna(navio['calado']) else None

        # Toneladas
        toneladas_cols = [col for col in navio_rows.columns if 'tonelada' in col.lower() or 'quantidade' in col.lower()]
        if toneladas_cols:
            resultado['toneladas'] = float(navio[toneladas_cols[0]]) if pd.notna(navio[toneladas_cols[0]]) else None

        return resultado

    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar navio por IMO: {e}")
        return None


def listar_navios_lineup(predictor):
    """
    Lista todos os navios disponíveis no lineup_history.

    Args:
        predictor: Instância do EnrichedPredictor com lineup_history carregado

    Returns:
        Dict mapeando "Nome (IMO: xxx)" para dados do navio
    """
    navios_dict = {}

    if predictor.lineup_history.empty:
        return navios_dict

    try:
        df = predictor.lineup_history.copy()

        # Verificar colunas necessárias
        imo_cols = [col for col in df.columns if 'imo' in col.lower()]
        nome_cols = [col for col in df.columns if 'navio' in col.lower() or 'nome' in col.lower()]

        if not imo_cols or not nome_cols:
            return navios_dict

        imo_col = imo_cols[0]
        nome_col = nome_cols[0]

        # Limpar e filtrar
        df = df[[imo_col, nome_col]].dropna()
        df[imo_col] = df[imo_col].astype(str).str.strip()
        df[nome_col] = df[nome_col].astype(str).str.strip()

        # Remover duplicatas (pegar registro mais recente por IMO)
        df = df.drop_duplicates(subset=[imo_col], keep='first')

        # Criar dicionário com formato amigável
        for _, row in df.iterrows():
            imo = row[imo_col]
            nome = row[nome_col]

            if imo and nome and imo != 'nan' and nome != 'nan':
                # Formato: "Nome do Navio (IMO: 9123456)"
                display_name = f"{nome} (IMO: {imo})"
                navios_dict[display_name] = imo

        return navios_dict

    except Exception as e:
        st.warning(f"⚠️ Erro ao listar navios: {e}")
        return navios_dict


def show_prediction_card(resultado, lineup_info=None):
    """
    Mostra card com resultado da previsão.

    Args:
        resultado: Dict com resultado da previsão do modelo
        lineup_info: Dict com informações do lineup (opcional, obtido via IMO)
    """
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

    # Comparação com lineup (se disponível)
    if lineup_info and lineup_info.get('eta_lineup'):
        st.markdown("---")
        st.markdown("### 🔄 Comparação: Lineup vs Previsão do Modelo")

        # Calcular ETA previsto (ETA lineup + tempo de espera)
        eta_lineup = lineup_info['eta_lineup']
        tempo_espera_horas = resultado['tempo_espera_previsto_horas']
        eta_previsto = eta_lineup + pd.Timedelta(hours=tempo_espera_horas)

        # Calcular atraso/antecipação
        delta_horas = (eta_previsto - eta_lineup).total_seconds() / 3600
        delta_dias = delta_horas / 24

        # Determinar cor do delta
        if delta_horas < 24:  # Menos de 1 dia
            delta_color = "#28a745"  # Verde
            delta_icon = "✅"
            delta_msg = "Atracação rápida"
        elif delta_horas < 168:  # Menos de 7 dias
            delta_color = "#ffc107"  # Amarelo
            delta_icon = "⚠️"
            delta_msg = "Atraso moderado"
        else:
            delta_color = "#dc3545"  # Vermelho
            delta_icon = "🚨"
            delta_msg = "Atraso significativo"

        # Criar colunas para comparação
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f"""
                <div class="info-box" style="background-color: #e3f2fd; border-color: #2196f3;">
                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">
                        📋 <strong>ETA do Lineup</strong>
                    </div>
                    <div style="font-size: 1.3rem; font-weight: bold; color: #2196f3;">
                        {eta_lineup.strftime('%d/%m/%Y %H:%M')}
                    </div>
                    <div style="font-size: 0.8rem; color: #666; margin-top: 0.3rem;">
                        Plano original do porto
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
                <div class="warning-box" style="background-color: #fff3e0; border-color: {delta_color};">
                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">
                        🔮 <strong>ETA Previsto (com espera)</strong>
                    </div>
                    <div style="font-size: 1.3rem; font-weight: bold; color: {delta_color};">
                        {eta_previsto.strftime('%d/%m/%Y %H:%M')}
                    </div>
                    <div style="font-size: 0.8rem; color: #666; margin-top: 0.3rem;">
                        Previsão do modelo
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
                <div class="success-box" style="background-color: #f5f5f5; border-color: {delta_color};">
                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">
                        {delta_icon} <strong>Diferença</strong>
                    </div>
                    <div style="font-size: 1.3rem; font-weight: bold; color: {delta_color};">
                        +{format_hours_to_days(delta_horas)}
                    </div>
                    <div style="font-size: 0.8rem; color: #666; margin-top: 0.3rem;">
                        {delta_msg}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Explicação adicional
        st.markdown(
            f"""
            <div class="info-box">
                <strong>ℹ️ Interpretação:</strong><br>
                O navio está no lineup com ETA de <strong>{eta_lineup.strftime('%d/%m/%Y às %H:%M')}</strong>.
                Com base nas condições atuais, o modelo prevê que a atracação real ocorrerá em
                <strong>{eta_previsto.strftime('%d/%m/%Y às %H:%M')}</strong>,
                resultando em um atraso de <strong style="color: {delta_color};">
                {delta_dias:.1f} dias ({delta_horas:.0f} horas)</strong> em relação ao planejado.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Mostrar informações do navio do lineup (se disponível)
        if lineup_info.get('nome_navio'):
            with st.expander("ℹ️ Informações do Lineup", expanded=False):
                info_cols = st.columns(2)

                with info_cols[0]:
                    st.markdown(f"**Navio:** {lineup_info.get('nome_navio', 'N/A')}")
                    st.markdown(f"**IMO:** {lineup_info.get('imo', 'N/A')}")
                    st.markdown(f"**Porto:** {lineup_info.get('porto', 'N/A')}")

                with info_cols[1]:
                    st.markdown(f"**Tipo:** {lineup_info.get('tipo_navio', 'N/A')}")
                    st.markdown(f"**Carga:** {lineup_info.get('carga', 'N/A')}")
                    st.markdown(f"**DWT:** {lineup_info.get('dwt', 'N/A')}")


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

        # Opção de seleção ou entrada manual
        modo_selecao = st.radio(
            "Escolha o modo de entrada:",
            ["🔍 Selecionar do Lineup", "✍️ Entrada Manual / Busca por IMO"],
            horizontal=True,
        )

        lineup_info = None

        # ========================================================================
        # MODO: SELECIONAR DO LINEUP
        # ========================================================================
        if modo_selecao == "🔍 Selecionar do Lineup":
            # Listar navios disponíveis
            navios_disponiveis = listar_navios_lineup(predictor)

            if not navios_disponiveis:
                st.warning("⚠️ Nenhum navio encontrado no lineup histórico. Use a opção 'Entrada Manual'.")
            else:
                st.info(f"📋 {len(navios_disponiveis)} navios disponíveis no lineup")

                # Selectbox com os navios
                navio_selecionado = st.selectbox(
                    "Selecione o Navio",
                    options=["Selecione..."] + list(navios_disponiveis.keys()),
                    index=0,
                )

                if navio_selecionado != "Selecione...":
                    # Buscar IMO do navio selecionado
                    imo_selecionado = navios_disponiveis[navio_selecionado]

                    with st.spinner(f"Carregando dados do navio..."):
                        lineup_info = buscar_navio_por_imo(imo_selecionado, predictor)

                    if lineup_info:
                        st.success(f"✅ Navio carregado: {lineup_info.get('nome_navio', 'N/A')}")

                        # Mostrar informações do lineup em um card
                        with st.expander("📋 Informações do Lineup", expanded=True):
                            col_info1, col_info2 = st.columns(2)

                            with col_info1:
                                st.markdown(f"**Navio:** {lineup_info.get('nome_navio', 'N/A')}")
                                st.markdown(f"**IMO:** {lineup_info.get('imo', 'N/A')}")
                                st.markdown(f"**Porto:** {lineup_info.get('porto', 'N/A')}")
                                st.markdown(f"**ETA Lineup:** {lineup_info.get('eta_lineup_str', 'N/A')}")

                            with col_info2:
                                st.markdown(f"**Tipo:** {lineup_info.get('tipo_navio', 'N/A')}")
                                st.markdown(f"**Carga:** {lineup_info.get('carga', 'N/A')}")
                                st.markdown(f"**DWT:** {lineup_info.get('dwt', 'N/A')}")

                        # Usar valores do lineup como padrão
                        porto_default = lineup_info.get('porto', 'Santos')
                        tipo_default = lineup_info.get('tipo_navio', 'Bulk Carrier')
                        carga_default = lineup_info.get('carga', 'Soja em Graos')
                        dwt_default = lineup_info.get('dwt', 75000) if lineup_info.get('dwt') else 75000
                        calado_default = lineup_info.get('calado', 12.5) if lineup_info.get('calado') else 12.5
                        toneladas_default = lineup_info.get('toneladas', 50000) if lineup_info.get('toneladas') else 50000

                        # ETA do lineup como padrão
                        if lineup_info.get('eta_lineup'):
                            eta_default = lineup_info['eta_lineup'].date()
                        else:
                            eta_default = datetime.now() + timedelta(days=7)
                    else:
                        st.error("❌ Erro ao carregar dados do navio")
                        st.stop()
                else:
                    # Valores padrão se nenhum navio selecionado
                    porto_default = 'Santos'
                    tipo_default = 'Bulk Carrier'
                    carga_default = 'Soja em Graos'
                    dwt_default = 75000
                    calado_default = 12.5
                    toneladas_default = 50000
                    eta_default = datetime.now() + timedelta(days=7)

        # ========================================================================
        # MODO: ENTRADA MANUAL / BUSCA POR IMO
        # ========================================================================
        else:
            # Campo IMO (opcional)
            imo_input = st.text_input(
                "🔍 IMO do Navio (opcional - para comparação com lineup)",
                value="",
                max_chars=10,
                help="Código IMO do navio. Se preenchido, buscaremos o navio no lineup para comparar ETAs.",
                placeholder="Ex: 9123456"
            )

            # Buscar navio no lineup se IMO foi fornecido
            if imo_input:
                with st.spinner(f"Buscando navio IMO {imo_input} no lineup..."):
                    lineup_info = buscar_navio_por_imo(imo_input, predictor)

                if lineup_info:
                    st.success(f"✅ Navio encontrado no lineup: {lineup_info.get('nome_navio', 'N/A')}")

                    # Preencher campos automaticamente se disponível
                    if lineup_info.get('eta_lineup'):
                        st.info(f"📋 ETA do Lineup: {lineup_info['eta_lineup_str']}")
                else:
                    st.warning(f"⚠️ Navio IMO {imo_input} não encontrado no lineup histórico. Você pode continuar com entrada manual.")

            # Valores padrão para entrada manual
            porto_default = 'Santos'
            tipo_default = 'Bulk Carrier'
            carga_default = 'Soja em Graos'
            dwt_default = 75000
            calado_default = 12.5
            toneladas_default = 50000
            eta_default = datetime.now() + timedelta(days=7)

        st.markdown("---")

        col1, col2 = st.columns(2)

        # Determinar índices baseados nos valores padrão
        portos_list = list(PORTOS.keys())
        porto_index = portos_list.index(porto_default) if porto_default in portos_list else 0

        tipos_list = [
            "Bulk Carrier",
            "Tanker",
            "Chemical Tanker",
            "Ore Carrier",
            "General Cargo",
            "Container Ship",
        ]
        tipo_index = tipos_list.index(tipo_default) if tipo_default in tipos_list else 0

        cargas_list = [
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
        ]
        carga_index = cargas_list.index(carga_default) if carga_default in cargas_list else 0

        with col1:
            porto = st.selectbox(
                "Porto de Destino *",
                options=portos_list,
                index=porto_index,
            )

            tipo_navio = st.selectbox(
                "Tipo de Navio",
                options=tipos_list,
                index=tipo_index,
            )

            natureza_carga = st.selectbox(
                "Natureza da Carga",
                options=cargas_list,
                index=carga_index,
            )

        with col2:
            eta = st.date_input(
                "ETA (Estimated Time of Arrival) *",
                value=eta_default,
                min_value=datetime.now().date(),
                max_value=datetime.now().date() + timedelta(days=365),
            )

            dwt = st.number_input(
                "DWT (Deadweight Tonnage)",
                min_value=1000,
                max_value=400000,
                value=int(dwt_default),
                step=1000,
                help="Capacidade de carga do navio em toneladas",
            )

            calado = st.number_input(
                "Calado (metros)",
                min_value=1.0,
                max_value=25.0,
                value=float(calado_default),
                step=0.5,
                help="Profundidade do navio submerso",
            )

        toneladas = st.number_input(
            "Movimentação Total (toneladas)",
            min_value=1000,
            max_value=400000,
            value=int(toneladas_default),
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
                    show_prediction_card(resultado, lineup_info)

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
            - <code>imo</code> (opcional): Código IMO do navio para buscar no lineup<br>
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
                "imo": ["9123456", "9234567"],
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

                        # Buscar informações do lineup por IMO (se disponível)
                        lineup_info = None
                        if 'imo' in row and pd.notna(row['imo']) and row['imo']:
                            lineup_info = buscar_navio_por_imo(row['imo'], predictor)

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

                            # Adicionar informações do lineup ao resultado
                            if lineup_info and lineup_info.get('eta_lineup'):
                                resultado['imo'] = lineup_info.get('imo', row.get('imo', ''))
                                resultado['eta_lineup'] = lineup_info['eta_lineup_str']

                                # Calcular ETA previsto e delta
                                eta_lineup_dt = lineup_info['eta_lineup']
                                eta_previsto_dt = eta_lineup_dt + pd.Timedelta(hours=resultado['tempo_espera_previsto_horas'])
                                resultado['eta_previsto'] = eta_previsto_dt.strftime('%Y-%m-%d %H:%M')

                                delta_horas = (eta_previsto_dt - eta_lineup_dt).total_seconds() / 3600
                                resultado['delta_horas'] = round(delta_horas, 1)
                                resultado['delta_dias'] = round(delta_horas / 24, 1)
                            else:
                                resultado['imo'] = row.get('imo', '')
                                resultado['eta_lineup'] = ''
                                resultado['eta_previsto'] = ''
                                resultado['delta_horas'] = None
                                resultado['delta_dias'] = None

                            resultados.append(resultado)
                        except Exception as e:
                            st.warning(f"⚠️ Erro no navio {idx + 1}: {e}")
                            resultados.append({
                                "erro": str(e),
                                "porto": navio_data["porto"],
                                "eta": navio_data["eta"],
                                "imo": row.get('imo', ''),
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
                        lambda x: format_hours_to_days(x) if pd.notna(x) else "N/A"
                    )
                    df_display["confianca"] = df_display["confianca"].apply(
                        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
                    )

                    # Selecionar colunas para exibição
                    display_cols = ["porto", "eta", "perfil", "tempo_espera_previsto_horas",
                                    "categoria_fila", "confianca", "modelo_usado"]

                    # Adicionar colunas de comparação se disponíveis
                    if 'imo' in df_display.columns and df_display['imo'].notna().any():
                        display_cols.insert(0, "imo")

                    if 'eta_lineup' in df_display.columns and df_display['eta_lineup'].notna().any() and (df_display['eta_lineup'] != '').any():
                        display_cols.insert(2, "eta_lineup")
                        display_cols.insert(3, "eta_previsto")
                        display_cols.insert(4, "delta_dias")

                    # Filtrar apenas colunas que existem
                    display_cols = [col for col in display_cols if col in df_display.columns]

                    st.dataframe(
                        df_display[display_cols],
                        use_container_width=True,
                        column_config={
                            "imo": st.column_config.TextColumn("IMO", help="Código IMO do navio"),
                            "eta_lineup": st.column_config.TextColumn("ETA Lineup", help="ETA do lineup original"),
                            "eta_previsto": st.column_config.TextColumn("ETA Previsto", help="ETA previsto com espera"),
                            "delta_dias": st.column_config.NumberColumn("Atraso (dias)", help="Diferença em dias entre ETA previsto e lineup", format="%.1f"),
                        }
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
