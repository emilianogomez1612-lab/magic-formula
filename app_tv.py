import pandas as pd
import plotly.express as px
import streamlit as st
from tradingview_screener import Column, Query

# ---------------------------------------------------------
# CONFIGURACIÓN DEL DASHBOARD
# ---------------------------------------------------------
st.set_page_config(
    page_title="Fórmula Mágica - TradingView", page_icon="🧙‍♂️", layout="wide"
)

st.title("🧙‍♂️ Fórmula Mágica de Joel Greenblatt (vía TradingView)")
st.caption(
    "100% Gratuito • Con filtros avanzados de ROA mínimo y exclusión de P/E bajo"
)

# ---------------------------------------------------------
# BARRA LATERAL (PARÁMETROS Y NUEVAS REGLAS)
# ---------------------------------------------------------
st.sidebar.header("⚙️ Filtros y Reglas del Algoritmo")

market_choice = st.sidebar.selectbox(
    "Mercado a Analizar",
    ["Ambos (EE. UU. / SIC + México)", "Solo EE. UU. (SIC)", "Solo México"],
)
min_mcap = st.sidebar.number_input(
    "Market Cap Mínimo (USD)",
    value=500_000_000,
    step=100_000_000,
    format="%d",
)

# Nuevos controles interactivos para tus reglas
min_roa = (
    st.sidebar.slider("ROA Mínimo (%)", min_value=0.0, max_value=50.0, value=25.0, step=1.0)
    / 100.0
)  # TradingView maneja el ROA en formato decimal o porcentaje según la columna, ajustamos
min_pe = st.sidebar.number_input("P/E Mínimo (Excluir menor o igual a)", value=5.0, step=1.0)

top_n = st.sidebar.slider("Top N Empresas en Salida", 5, 50, 20)
exclude_sectors = st.sidebar.checkbox(
    "Excluir Financieras y Utilities (Regla Greenblatt)", value=True
)

btn_run = st.sidebar.button("🚀 Calcular Ranking Mágico", type="primary")

# ---------------------------------------------------------
# LÓGICA DE EXTRACCIÓN Y RANKING
# ---------------------------------------------------------
if btn_run:
  with st.spinner(
      "Consultando motores de TradingView aplicando tus reglas estrictas..."
  ):
    markets_to_query = []
    if "EE. UU." in market_choice or "Ambos" in market_choice:
      markets_to_query.append("america")
    if "México" in market_choice or "Ambos" in market_choice:
      markets_to_query.append("mexico")

    dfs = []
    for mkt in markets_to_query:
      try:
        q = (
            Query()
            .set_markets(mkt)
            .select(
                "name",
                "description",
                "close",
                "market_cap_basic",
                "price_earnings_ttm",
                "return_on_assets",
                "sector",
                "exchange",
                "earnings_release_date",
            )
            .where(
                Column("market_cap_basic") >= min_mcap,
                Column("price_earnings_ttm") > min_pe,  # P/E mayor al mínimo indicado
                Column("return_on_assets") >= min_roa * 100,  # TradingView usa base 100 para ROA (%)
            )
        )
        _, df_mkt = q.get_scanner_data()
        if not df_mkt.empty:
          dfs.append(df_mkt)
      except Exception as e:
        st.warning(f"Aviso en mercado {mkt}: {e}")

    if dfs:
      df = pd.concat(dfs, ignore_index=True)
      df = df.drop_duplicates(subset=["name"])

      # Filtrar sectores prohibidos por Greenblatt
      if exclude_sectors and "sector" in df.columns:
        df = df[
            ~df["sector"].isin(
                ["Finance", "Financial Services", "Financial", "Utilities"]
            )
        ]

      if not df.empty:
        # Renombrar columnas para claridad
        df = df.rename(
            columns={
                "name": "Ticker",
                "description": "Company Name",
                "close": "Price",
                "market_cap_basic": "Market Cap",
                "price_earnings_ttm": "P/E",
                "return_on_assets": "ROA",
                "earnings_release_date": "MRQ Date",
            }
        )

        # ---------------------------------------------------------
        # ALGORITMO INTERMEDIO: RANKING MÁGICO
        # ---------------------------------------------------------
        df["Rank_ROA"] = df["ROA"].rank(ascending=False, method="min")
        df["Rank_PE"] = df["P/E"].rank(ascending=True, method="min")
        df["Magic_Score"] = df["Rank_ROA"] + df["Rank_PE"]
        df = df.sort_values(by="Magic_Score", ascending=True).reset_index(
            drop=True
        )
        df["Magic_Rank"] = df.index + 1

        df_final = df.head(top_n)

        st.success(
            f"¡Éxito! Se filtraron y rankearon las mejores {len(df_final)}"
            " empresas bajo tus criterios."
        )

        # ---------------------------------------------------------
        # SALIDA EN EL DASHBOARD
        # ---------------------------------------------------------
        col1, col2, col3 = st.columns(3)
        col1.metric("🥇 #1 del Ranking", df_final.iloc[0]["Ticker"])
        col2.metric("ROA Promedio (Top)", f"{df_final['ROA'].mean():.2f}%")
        col3.metric("P/E Promedio (Top)", f"{df_final['P/E'].mean():.2f}x")

        st.markdown("---")

        # Gráfico de Dispersión interactivo
        st.subheader("📊 Mapa de Oportunidades (ROA vs P/E)")
        fig = px.scatter(
            df_final,
            x="P/E",
            y="ROA",
            text="Ticker",
            size="Market Cap",
            color="Magic_Rank",
            hover_data=["Company Name", "Price", "sector", "MRQ Date"],
            title="Empresas filtradas con ROA >= 25% y P/E > 5",
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)

        # Tabla final detallada
        st.subheader("📋 Listado Oficial de la Fórmula Mágica (Filtrado)")
        df_display = df_final[
            [
                "Magic_Rank",
                "Ticker",
                "Company Name",
                "Market Cap",
                "Price",
                "ROA",
                "P/E",
                "MRQ Date",
                "sector",
                "exchange",
            ]
        ].copy()

        df_display["Market Cap"] = df_display["Market Cap"].apply(
            lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A"
        )
        df_display["Price"] = df_display["Price"].apply(
            lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A"
        )
        df_display["ROA"] = df_display["ROA"].apply(
            lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A"
        )
        df_display["P/E"] = df_display["P/E"].apply(
            lambda x: f"{x:.2f}x" if pd.notnull(x) else "N/A"
        )

        st.dataframe(df_display, use_container_width=True, hide_index=True)

      else:
        st.warning(
            "No quedaron acciones que cumplan con un ROA tan exigente (>= 25%) y"
            " un P/E > 5 simultáneamente. Intenta relajar ligeramente los"
            " filtros en la barra lateral si es necesario."
        )
    else:
      st.warning(
          "No se pudieron recuperar datos. Revisa tu conexión a internet."
      )

# cd "C:\Users\52556\Curso Python A2\Cuadernos de Trabajo"
# streamlit run app_tv.py
      