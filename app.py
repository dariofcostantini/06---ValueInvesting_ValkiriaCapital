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
    return t.info, t.financials, t.cashflow, t.balance_sheet

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
        
    fin = financials.reindex(columns=cols) if financials is not None and not financials.empty else pd.DataFrame(columns=cols)
    cf = cashflow.reindex(columns=cols) if cashflow is not None and not cashflow.empty else pd.DataFrame(columns=cols)

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
        "Sales Value of Production (Revenue)": revenue / 1_000,
        "Y/Y Growth %": crec_revenue,
        "COGS": cogs / 1_000,
        "Gross Profit": gross_profit / 1_000,
        "Gross margin %": margen_bruto,
        "EBITDA": ebitda / 1_000,
        "EBITDA margin %": margen_ebitda,
        "Depreciation & Amortization Expense": depreciation / 1_000,
        "EBIT": ebit / 1_000,
        "EBIT margin %": margen_ebit,
        "Interest expense / Income": interest_exp / 1_000,
        "Pretax Income": pretax / 1_000,
        "Income Taxes": tax / 1_000,
        "tax rate %": tax_rate,
        "Consolidated Net Income": consolidated_net_income / 1_000,
        "Minority Interest": minority / 1_000,
        "Net Income": net_income / 1_000,
        "Margen beneficio neto %": margen_neto,
        "Net income per share ( EPS )": eps,
        "Fully diluted shares (millions)": diluted_shares / 1_000_000
    }).T # Transponemos para que las métricas sean las filas y los años las columnas

    # Formateamos las columnas para mostrar solo el año
    df_mostrar.columns = [str(c)[:4] for c in df_mostrar.columns]
    
    return df_mostrar

def calcular_flujos_caja(financials, cashflow, years):
    todas_cols = sorted(cashflow.columns)
    cols = todas_cols[-years:] if years else todas_cols
    
    if not cols:
        return pd.DataFrame()
        
    fin = financials.reindex(columns=cols) if financials is not None and not financials.empty else pd.DataFrame(columns=cols)
    cf = cashflow.reindex(columns=cols) if cashflow is not None and not cashflow.empty else pd.DataFrame(columns=cols)


    # Extracción de métricas
    revenue = obtener_fila(fin, ["Total Revenue", "Operating Revenue", "Revenue"])
    ebitda = obtener_fila(fin, ["EBITDA", "Ebitda", "Normalized EBITDA"])
    
    capex_raw = obtener_fila(cf, ["Capital Expenditure", "Capital Expenditures", "Purchase Of Property Plant And Equipment"])
    capex = capex_raw.copy()
    for c in cols:
        if pd.notna(capex.get(c)):
            capex[c] = abs(capex[c])
            
    interest_exp = obtener_fila(fin, ["Net Non Operating Interest Income Expense", "Interest Expense", "Interest Expense Non Operating"])
    intereses = interest_exp.copy()
    for c in cols:
        if pd.notna(intereses.get(c)):
            intereses[c] = abs(intereses[c])

    tax = obtener_fila(fin, ["Tax Provision", "Income Tax Expense"])
    tasas = tax.copy()
    for c in cols:
        if pd.notna(tasas.get(c)):
            tasas[c] = abs(tasas[c])

    wc = obtener_fila(cf, ["Change In Working Capital"])
    sbc = obtener_fila(cf, ["Stock Based Compensation", "Share Based Compensation"])

    op_cf = obtener_fila(cf, ["Operating Cash Flow", "Cash From Operations", "Net Cash Provided By Operating Activities", "Total Cash From Operating Activities"])
    fcf = pd.Series(index=cols)
    for c in cols:
        if pd.notna(op_cf.get(c)) and pd.notna(capex.get(c)):
            fcf[c] = op_cf[c] - capex[c]
        else:
            fcf[c] = None

    diluted_shares = obtener_fila(fin, ["Diluted Average Shares", "Basic Average Shares"])
    
    fcf_per_share = pd.Series(index=cols)
    conversion_fcf_ebitda = pd.Series(index=cols)
    capex_sale = pd.Series(index=cols)

    for c in cols:
        if pd.notna(fcf.get(c)) and pd.notna(diluted_shares.get(c)) and diluted_shares[c] != 0:
            fcf_per_share[c] = fcf[c] / diluted_shares[c]
        else:
            fcf_per_share[c] = None
            
        if pd.notna(fcf.get(c)) and pd.notna(ebitda.get(c)) and ebitda[c] != 0:
            conversion_fcf_ebitda[c] = (fcf[c] / ebitda[c]) * 100
        else:
            conversion_fcf_ebitda[c] = None

        if pd.notna(capex.get(c)) and pd.notna(revenue.get(c)) and revenue[c] != 0:
            capex_sale[c] = (capex[c] / revenue[c]) * 100
        else:
            capex_sale[c] = None

    # Construcción del DataFrame para mostrar
    df_mostrar = pd.DataFrame({
        "EBITDA": ebitda / 1_000,
        "Capex (introducir manual)": capex / 1_000,
        "Intereses": intereses / 1_000,
        "Tasas": tasas / 1_000,
        "WC": wc / 1_000,
        "Stock options/minoritarios": sbc / 1_000,
        "Flujo de caja libre": fcf / 1_000,
        "Flujo de caja libre por accion": fcf_per_share,
        "Conversion FCF/Ebitda %": conversion_fcf_ebitda,
        "Capex /Sale %": capex_sale,
    }).T

    df_mostrar.columns = [str(c)[:4] for c in df_mostrar.columns]
    
    return df_mostrar

# --- INTERFAZ PRINCIPAL ---
def calcular_retornos_capital(financials, balance, years):
    todas_cols = sorted(balance.columns)
    cols = todas_cols[-years:] if years else todas_cols
    
    if not cols:
        return pd.DataFrame()
        
    fin = financials.reindex(columns=cols) if financials is not None and not financials.empty else pd.DataFrame(columns=cols)
    bal = balance.reindex(columns=cols) if balance is not None and not balance.empty else pd.DataFrame(columns=cols)

    # P&L
    ebit = obtener_fila(fin, ["Operating Income", "EBIT", "Ebit"])
    interest = obtener_fila(fin, ["Net Non Operating Interest Income Expense", "Interest Expense", "Interest Expense Non Operating"])
    tax = obtener_fila(fin, ["Tax Provision", "Income Tax Expense"])
    net_income = obtener_fila(fin, ["Net Income", "Net Income Common Stockholders"])
    pretax = obtener_fila(fin, ["Pretax Income"])

    # Balance
    cash = obtener_fila(bal, ["Cash And Cash Equivalents", "Cash", "Cash And Equivalents"])
    debt = obtener_fila(bal, ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Short Long Term Debt Total"])
    leases = obtener_fila(bal, ["Capital Lease Obligations", "Long Term Capital Lease Obligation"])
    goodwill = obtener_fila(bal, ["Goodwill"])
    equity = obtener_fila(bal, ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"])
    marketable = obtener_fila(bal, ["Other Short Term Investments", "Short Term Investments"])

    # Rellenar nulos con 0 para sumas (ej: leases)
    def fill_zero(s):
        s_copy = s.copy()
        for c in cols:
            if pd.isna(s_copy.get(c)):
                s_copy[c] = 0
        return s_copy

    leases = fill_zero(leases)
    goodwill = fill_zero(goodwill)
    marketable = fill_zero(marketable)
    cash = fill_zero(cash)
    debt = fill_zero(debt)
    equity = fill_zero(equity)

    # Capital empleado
    cap_con_gw = pd.Series(index=cols)
    cap_sin_gw = pd.Series(index=cols)
    for c in cols:
        cap_con_gw[c] = equity[c] + debt[c] + leases[c]
        cap_sin_gw[c] = cap_con_gw[c] - goodwill[c]

    # ROE y ROCE
    roe = pd.Series(index=cols)
    roce_con_gw = pd.Series(index=cols)
    roce_sin_gw = pd.Series(index=cols)
    for c in cols:
        roe[c] = (net_income[c] / equity[c]) * 100 if pd.notna(net_income.get(c)) and equity[c] != 0 else None
        
        if pd.notna(ebit.get(c)):
            roce_con_gw[c] = (ebit[c] / cap_con_gw[c]) * 100 if cap_con_gw[c] != 0 else None
            roce_sin_gw[c] = (ebit[c] / cap_sin_gw[c]) * 100 if cap_sin_gw[c] != 0 else None

    # ROIC = NOPAT / (Deuda + Equity + Leases - Cash - Marketable)
    nopat = pd.Series(index=cols)
    roic = pd.Series(index=cols)
    for c in cols:
        t = tax.get(c)
        p = pretax.get(c)
        tax_rate = (t / p) if (pd.notna(t) and pd.notna(p) and p != 0) else 0.20
        e = ebit.get(c)
        nopat[c] = e * (1 - tax_rate) if pd.notna(e) else None
            
        invested_cap = debt[c] + equity[c] + leases[c] - cash[c] - marketable[c]
        roic[c] = (nopat[c] / invested_cap) * 100 if pd.notna(nopat.get(c)) and invested_cap != 0 else None

    # Construcción de la tabla
    df_mostrar = pd.DataFrame({
        "EBIT": ebit / 1_000,
        "Interest": interest / 1_000,
        "Tasas": tax / 1_000,
        "Net income": net_income / 1_000,
        "(+) Cash and cash equivalents": cash / 1_000,
        "(-) Marketable Securities": marketable / 1_000,
        "(+) Deuda total": debt / 1_000,
        "(+) Operating Leases": leases / 1_000,
        "(+) Goodwill": goodwill / 1_000,
        "(+) Equity": equity / 1_000,
        "Capital empleado con goodwill": cap_con_gw / 1_000,
        "Capital empleado sin goodwill": cap_sin_gw / 1_000,
        "ROE (net income/equity) %": roe,
        "ROCE sin goodwill %": roce_sin_gw,
        "ROCE con goodwill %": roce_con_gw,
        "EBIT x (1-t) NOPAT": nopat / 1_000,
        "ROIC %": roic
    }).T

    df_mostrar.columns = [str(c)[:4] for c in df_mostrar.columns]
    return df_mostrar

if ticker_input:
    try:
        with st.spinner(f"Descargando datos para {ticker_input}..."):
            info, financials, cashflow, balance = descargar_datos(ticker_input)
            
        if financials.empty:
            st.error(f"No se encontraron datos financieros para {ticker_input}.")
        else:
            st.subheader(f"{info.get('longName', ticker_input)} ({ticker_input})")
            
            # --- TABS PARA NAVEGAR POR LAS FASES ---
            tab1, tab2, tab3, tab4 = st.tabs(["1. Income Statement", "2. Flujos de Caja", "3. Retornos Capital", "4. Valoración"])
            
            with tab1:
                st.markdown("### 1. Income Statement (All numbers in thousands)")
                df_is = calcular_income_statement(financials, cashflow, years_input)
                
                # Mostramos la tabla en Streamlit (con un estilo visual agradable)
                st.dataframe(df_is.style.format("{:,.2f}"), use_container_width=True)
                
            with tab2:
                st.markdown("### 2. Flujos de Caja (All numbers in thousands)")
                df_fc = calcular_flujos_caja(financials, cashflow, years_input)
                st.dataframe(df_fc.style.format("{:,.2f}"), use_container_width=True)
            with tab3:
                st.markdown("### 3. Retornos de Capital (All numbers in thousands)")
                df_rc = calcular_retornos_capital(financials, balance, years_input)
                st.dataframe(df_rc.style.format("{:,.2f}"), use_container_width=True)
            with tab4:
                st.info("Próximamente: Aquí integraremos la Fase 4 (Valoración).")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el ticker: {e}")
