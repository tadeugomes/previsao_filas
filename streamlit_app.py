import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "Previsao de Fila - Vegetal (MVP)"
LINEUP_PATH = Path("data_extraction/raw/lineup/lineup_appa_latest.csv")
META_PATH = Path("data_extraction/processed/production/dataset_metadata.json")


@st.cache_data
def load_real_data():
    if LINEUP_PATH.exists():
        df_lineup = pd.read_csv(LINEUP_PATH)
        keep_cols = [c for c in ['Navio', 'Mercadoria', 'Chegada', 'Posicao'] if c in df_lineup.columns]
        df_lineup = df_lineup[keep_cols].copy()
    else:
        df_lineup = pd.DataFrame(columns=['Navio', 'Mercadoria', 'Chegada', 'Posicao'])

    if META_PATH.exists():
        with META_PATH.open("r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {}

    return df_lineup, meta


def calcular_risco(chuva_mm_3d, fila_atual, fila_media):
    if chuva_mm_3d > 20 or fila_atual > 20:
        return "Alto", "vermelho", "Chuva intensa ou fila critica"
    if chuva_mm_3d > 10 or fila_atual > fila_media:
        return "Medio", "amarelo", "Chuva relevante ou fila acima da media"
    return "Baixo", "verde", "Clima favoravel e fila abaixo da media"


st.set_page_config(page_title=APP_TITLE, layout="wide")

st.title(APP_TITLE)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Entrada")
    chegada = st.date_input("Data Estimada de Chegada (ETA)", value=datetime.today())
    produto = st.selectbox(
        "Tipo de Carga",
        ["Soja em Graos", "Farelo", "Milho", "Acucar", "Trigo", "Cevada", "Malte"]
    )
    chuva_prevista = st.number_input(
        "Previsao Climática (Acumulado 72h)",
        min_value=0.0,
        value=0.0
    )
    fila_atual = st.number_input("Navios aguardando no Fundeio", min_value=0, value=0)

with col2:
    st.subheader("Saida (MVP)")
    df_lineup, meta = load_real_data()
    fila_media = max(int(df_lineup.shape[0] / 2), 10) if not df_lineup.empty else 10
    risco, cor, motivo = calcular_risco(chuva_prevista, fila_atual, fila_media)

    if risco == "Baixo":
        estimativa = "2 a 3 dias"
        tendencia = "Fluxo Normal"
        dias_min, dias_max = 2, 3
    elif risco == "Medio":
        estimativa = "3 a 5 dias"
        tendencia = "Congestionamento Moderado"
        dias_min, dias_max = 3, 5
    else:
        estimativa = "5 a 7 dias"
        tendencia = "Congestionamento Critico"
        dias_min, dias_max = 5, 7

    data_prevista = chegada + pd.Timedelta(days=dias_max)
    st.metric("Estimativa de espera", estimativa)
    st.metric("Atracacao prevista", data_prevista.strftime("%d/%m (%A)"))
    st.metric("Tendencia", tendencia)
    st.metric("Risco", f"{risco} ({motivo})")

    st.caption("Regras: chuva > 10mm ou fila acima da media elevam risco. Chuva > 20mm ou fila > 20 = critico.")

st.divider()

st.subheader("Line-up publico (se disponivel)")
if df_lineup.empty:
    st.info("🔄 Aguardando atualizacao do line-up oficial... (Use o simulador manual acima)")
else:
    st.dataframe(df_lineup, use_container_width=True)

if meta:
    ops = meta.get("total_registros") or meta.get("n_registros")
    acc = meta.get("auc_macro") or meta.get("acuracia_ref")
    if ops or acc:
        texto = "Modelo calibrado"
        if ops:
            texto += f" com {ops} operacoes reais"
        if acc:
            texto += f" (Acuracia ref: {acc})"
        st.caption(texto)
