import streamlit as st
import yfinance as yf
import pandas as pd

# Configuración inicial de la página
st.set_page_config(page_title="Valkiria Capital - Valoración", layout="wide")

st.title("📊 Valkiria Capital — Análisis Fundamental")

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("Configuración")
ticker_input = st.sidebar.text_input("Ticker (Ej: NVO, AAPL)", value="NVO").upper()
years_input = st.sidebar.slider("Años de historia a analizar", min_value=2, max_value=10, value=4)

# --- FUNCIONES DE OBTENCIÓN Y CÁLCULO ---
@st.cache_data # Guardamos en caché para no descargar todo el tiempo
def descargar_datos(ticker):
    t = yf.Ticker(ticker)
    return t.info, t.financials, t.cashflow

def obtener_fila(df, posibles_nombres):
    for nombre in posibles_nombres:
        if nombre in df.index:
            return df.loc[nombre]
    return pd.Series([None] * len(df.columns), index=df.columns)

def calcular_income_statement(financials, cashflow, years):
    todas_cols = sorted(financials.columns)
    cols = todas_cols[-years:] if years else todas_cols
    
    if not cols:
        return pd.DataFrame()
        
    fin = financials[cols]
    cf = cashflow[cols] if cashflow is not None and not cashflow.empty else pd.DataFrame(columns=cols)

    # Extracción de métricas
    revenue = obtener_fila(fin, ["Total Revenue", "Operating Revenue", "Revenue"])
    cogs = obtener_fila(fin, ["Cost Of Revenue", "Cost of Revenue", "Cost Of Goods Sold"])
    gross_profit = obtener_fila(fin, ["Gross Profit"])
    ebitda = obtener_fila(fin, ["EBITDA", "Ebitda", "Normalized EBITDA"])
    depreciation = obtener_fila(cf, ["Depreciation And Amortization", "Depreciation Amortization Depletion", "Reconciled Depreciation"])
    ebit = obtener_fila(fin, ["Operating Income", "EBIT", "Ebit"])
    interest_exp = obtener_fila(fin, ["Net Non Operating Interest Income Expense", "Interest Expense", "Interest Expense Non Operating"])
    pretax = obtener_fila(fin, ["Pretax Income"])
    tax = obtener_fila(fin, ["Tax Provision", "Income Tax Expense"])
    consolidated_net_income = obtener_fila(fin, ["Net Income Including Noncontrolling Interests"])
    net_income = obtener_fila(fin, ["Net Income", "Net Income Common Stockholders"])
    eps = obtener_fila(fin, ["Diluted EPS", "Basic EPS"])
    diluted_shares = obtener_fila(fin, ["Diluted Average Shares", "Basic Average Shares"])

    # Cálculos adicionales
    margen_bruto = (gross_profit / revenue) * 100
    margen_ebitda = (ebitda / revenue) * 100
    margen_ebit = (ebit / revenue) * 100
    margen_neto = (net_income / revenue) * 100
    minority = consolidated_net_income - net_income
    tax_rate = (tax / pretax) * 100
    
    crec_revenue = pd.Series(index=cols)
    for i, c in enumerate(cols):
        if i == 0:
            crec_revenue[c] = None
        else:
            ant = revenue.get(cols[i-1])
            act = revenue.get(c)
            if pd.notna(ant) and pd.notna(act) and ant != 0:
                crec_revenue[c] = ((act - ant) / abs(ant)) * 100

    # Construcción del DataFrame para mostrar en Streamlit
    df_mostrar = pd.DataFrame({
        "Sales Value of Production (Revenue)": revenue,
        "Y/Y Growth %": crec_revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "Gross margin %": margen_bruto,
        "EBITDA": ebitda,
        "EBITDA margin %": margen_ebitda,
        "Depreciation & Amortization Expense": depreciation,
        "EBIT": ebit,
        "EBIT margin %": margen_ebit,
        "Interest expense / Income": interest_exp,
        "Pretax Income": pretax,
        "Income Taxes": tax,
        "tax rate %": tax_rate,
        "Consolidated Net Income": consolidated_net_income,
        "Minority Interest": minority,
        "Net Income": net_income,
        "Margen beneficio neto %": margen_neto,
        "Net income per share ( EPS )": eps,
        "Fully diluted shares (millions)": diluted_shares / 1_000_000
    }).T # Transponemos para que las métricas sean las filas y los años las columnas

    # Formateamos las columnas para mostrar solo el año
    df_mostrar.columns = [str(c)[:4] for c in df_mostrar.columns]
    
    return df_mostrar

# --- INTERFAZ PRINCIPAL ---
if ticker_input:
    try:
        with st.spinner(f"Descargando datos para {ticker_input}..."):
            info, financials, cashflow = descargar_datos(ticker_input)
            
        if financials.empty:
            st.error(f"No se encontraron datos financieros para {ticker_input}.")
        else:
            st.subheader(f"{info.get('longName', ticker_input)} ({ticker_input})")
            
            # --- TABS PARA NAVEGAR POR LAS FASES ---
            tab1, tab2, tab3, tab4 = st.tabs(["1. Income Statement", "2. Flujos de Caja", "3. Retornos Capital", "4. Valoración"])
            
            with tab1:
                st.markdown("### 1. Income Statement")
                df_is = calcular_income_statement(financials, cashflow, years_input)
                
                # Mostramos la tabla en Streamlit (con un estilo visual agradable)
                st.dataframe(df_is.style.format(precision=2), use_container_width=True)
                
            with tab2:
                st.info("Próximamente: Aquí integraremos la Fase 2 (Flujos de caja).")
            with tab3:
                st.info("Próximamente: Aquí integraremos la Fase 3 (Retornos de capital).")
            with tab4:
                st.info("Próximamente: Aquí integraremos la Fase 4 (Valoración).")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el ticker: {e}")
