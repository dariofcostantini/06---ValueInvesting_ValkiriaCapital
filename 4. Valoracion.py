"""
╔══════════════════════════════════════════════════════════════════╗
║         VALKIRIA CAPITAL — Análisis Fundamental                  ║
║         4. Valoración                                            ║
╚══════════════════════════════════════════════════════════════════╝

DESCRIPCIÓN:
  Calcula métricas de valoración histórica, múltiplos y FCF Yield.
  Con la estructura de la cuarta página del Excel de valoración.

CÓMO USAR:
  1. Cambiá TICKER por el símbolo que querés analizar
  2. Ejecutá:  python "4. Valoracion.py"
"""

TICKER = "NVO"
YEARS  = [2022, 2023, 2024, 2025]
ESCALA = "AUTO"

import sys
import warnings
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import pandas as pd
    import datetime
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError as e:
    print(f"\nERROR: Falta instalar dependencias.")
    sys.exit(1)

DIV  = "─" * 62
DIV2 = "═" * 62

def fmt_val(valor, escala="M"):
    if valor is None or pd.isna(valor):
        return Fore.WHITE + Style.DIM + "  N/D"
    divisor = 1_000_000 if escala == "M" else 1_000_000_000
    sufijo  = "M" if escala == "M" else "B"
    num = valor / divisor
    color = Fore.GREEN if num >= 0 else Fore.RED
    return f"{color}{num:>10.1f} {sufijo}"

def fmt_pct(valor):
    if valor is None or pd.isna(valor):
        return Fore.WHITE + Style.DIM + "   N/D %"
    color = Fore.GREEN if valor >= 0 else Fore.RED
    return f"{color}{valor:>8.1f}%"

def header(titulo):
    print(f"\n{Fore.CYAN}{DIV2}")
    print(f"  {titulo}")
    print(f"{DIV2}{Style.RESET_ALL}")

def subheader(titulo):
    print(f"\n{Fore.YELLOW}  {titulo}")
    print(f"  {DIV}{Style.RESET_ALL}")

def descargar_datos(ticker: str):
    print(f"\n{Fore.CYAN}  Descargando datos de {ticker}...{Style.RESET_ALL}", end=" ")
    t = yf.Ticker(ticker)
    info       = t.info or {}
    financials = t.financials
    balance    = t.balance_sheet
    cashflow   = t.cashflow
    hist       = t.history(period="5y")
    if financials is None or financials.empty:
        print(Fore.RED + "ERROR")
        sys.exit(1)
    print(Fore.GREEN + "OK")
    return info, financials, balance, cashflow, hist

def obtener_fila(df: pd.DataFrame, posibles_nombres: list):
    for nombre in posibles_nombres:
        if nombre in df.index:
            return df.loc[nombre]
    return pd.Series([None] * len(df.columns), index=df.columns)

def calcular_valoracion(financials: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame, hist: pd.DataFrame, years, ticker_info):
    todas_cols = sorted(financials.columns)
    if isinstance(years, list):
        cols = [c for c in todas_cols if int(str(c)[:4]) in years]
    else:
        cols = todas_cols[-years:]
        
    fin = financials[cols]
    bal = balance[cols] if balance is not None and not balance.empty else pd.DataFrame(columns=cols)
    cf  = cashflow[cols] if cashflow is not None and not cashflow.empty else pd.DataFrame(columns=cols)

    # Métricas Base
    revenue = obtener_fila(fin, ["Total Revenue", "Operating Revenue", "Revenue"])
    ebitda = obtener_fila(fin, ["EBITDA", "Ebitda", "Normalized EBITDA"])
    ebit = obtener_fila(fin, ["Operating Income", "EBIT", "Ebit"])
    net_income = obtener_fila(fin, ["Net Income", "Net Income Common Stockholders"])
    diluted_shares = obtener_fila(fin, ["Diluted Average Shares", "Basic Average Shares"])
    eps = obtener_fila(fin, ["Diluted EPS", "Basic EPS"])

    # FCF
    op_cf = obtener_fila(cf, ["Operating Cash Flow", "Cash From Operations", "Net Cash Provided By Operating Activities"])
    capex_raw = obtener_fila(cf, ["Capital Expenditure", "Capital Expenditures"])
    fcf = pd.Series(index=cols)
    for c in cols:
        ocf = op_cf.get(c)
        cap = capex_raw.get(c)
        if pd.notna(ocf) and pd.notna(cap):
            fcf[c] = ocf - abs(cap)
        else:
            fcf[c] = None

    # Net Debt
    cash = obtener_fila(bal, ["Cash And Cash Equivalents", "Cash", "Cash And Equivalents"])
    debt = obtener_fila(bal, ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Short Long Term Debt Total"])
    net_debt = pd.Series(index=cols)
    for c in cols:
        ch = cash.get(c, 0)
        dt = debt.get(c, 0)
        if pd.isna(ch): ch = 0
        if pd.isna(dt): dt = 0
        net_debt[c] = dt - ch

    # Market Cap (Histórico aproximado multiplicando Diluted Shares * Precio a final de año)
    market_cap = pd.Series(index=cols)
    for c in cols:
        # Extraemos el año del timestamp
        year = c.year if hasattr(c, "year") else int(str(c)[:4])
        # Buscamos el precio en history para diciembre de ese año, o lo más cercano
        # Filtrar df hist por año
        df_year = hist[hist.index.year == year]
        if not df_year.empty:
            price = df_year.iloc[-1]["Close"]
        else:
            # Si no hay histórico, usamos el precio actual y rezamos o None
            price = ticker_info.get("currentPrice", 0)
        
        shares = diluted_shares.get(c)
        if pd.notna(shares) and shares != 0 and price != 0:
            market_cap[c] = shares * price
        else:
            market_cap[c] = None

    # Deuda Neta / EBITDA
    deuda_neta_ebitda = pd.Series(index=cols)
    for c in cols:
        nd = net_debt.get(c)
        eb = ebitda.get(c)
        if pd.notna(nd) and pd.notna(eb) and eb != 0:
            deuda_neta_ebitda[c] = nd / eb
        else:
            deuda_neta_ebitda[c] = None

    # Enterprise Value
    ev = pd.Series(index=cols)
    for c in cols:
        mc = market_cap.get(c)
        nd = net_debt.get(c)
        if pd.notna(mc) and pd.notna(nd):
            ev[c] = mc + nd
        else:
            ev[c] = None

    # Múltiplos
    ev_sale = pd.Series(index=cols)
    ev_ebitda = pd.Series(index=cols)
    ev_ebit = pd.Series(index=cols)
    ev_fcf = pd.Series(index=cols)
    p_fcf = pd.Series(index=cols)
    fcf_yield = pd.Series(index=cols)
    pe = pd.Series(index=cols)

    for c in cols:
        # EV/Sale
        if pd.notna(ev.get(c)) and pd.notna(revenue.get(c)) and revenue[c] != 0:
            ev_sale[c] = ev[c] / revenue[c]
        # EV/EBITDA
        if pd.notna(ev.get(c)) and pd.notna(ebitda.get(c)) and ebitda[c] != 0:
            ev_ebitda[c] = ev[c] / ebitda[c]
        # EV/EBIT
        if pd.notna(ev.get(c)) and pd.notna(ebit.get(c)) and ebit[c] != 0:
            ev_ebit[c] = ev[c] / ebit[c]
        # EV/FCF
        if pd.notna(ev.get(c)) and pd.notna(fcf.get(c)) and fcf[c] != 0:
            ev_fcf[c] = ev[c] / fcf[c]
        # P/FCF
        if pd.notna(market_cap.get(c)) and pd.notna(fcf.get(c)) and fcf[c] != 0:
            p_fcf[c] = market_cap[c] / fcf[c]
        # FCF Yield
        if pd.notna(market_cap.get(c)) and pd.notna(fcf.get(c)) and market_cap[c] != 0:
            fcf_yield[c] = (fcf[c] / market_cap[c]) * 100
        # PE
        if pd.notna(market_cap.get(c)) and pd.notna(net_income.get(c)) and net_income[c] != 0:
            pe[c] = market_cap[c] / net_income[c]

    return {
        "cols": cols,
        "market_cap": market_cap,
        "net_debt": net_debt,
        "deuda_neta_ebitda": deuda_neta_ebitda,
        "ev": ev,
        "ebitda": ebitda,
        "ebit": ebit,
        "net_income": net_income,
        "fcf": fcf,
        "ev_sale": ev_sale,
        "ev_ebitda": ev_ebitda,
        "ev_ebit": ev_ebit,
        "ev_fcf": ev_fcf,
        "p_fcf": p_fcf,
        "fcf_yield": fcf_yield,
        "pe": pe
    }

def mostrar_encabezado(info: dict, ticker: str):
    nombre = info.get("longName") or info.get("shortName") or ticker
    print(f"\n{Fore.CYAN}{DIV2}")
    print(f"  VALKIRIA CAPITAL — Análisis Fundamental")
    print(f"  4. Valoración")
    print(f"{DIV2}{Style.RESET_ALL}")
    print(f"\n  {Fore.WHITE}{Style.BRIGHT}{nombre}{Style.RESET_ALL}  {Fore.YELLOW}[{ticker}]{Style.RESET_ALL}")

def mostrar_valoracion(datos: dict, escala: str):
    cols = datos["cols"]
    años = [str(c)[:4] for c in cols]

    subheader("Valuation")
    sufijo = "en millones" if escala == "M" else "en billones"
    print(f"  {Fore.WHITE}({sufijo} de moneda local){Style.RESET_ALL}\n")

    col_header = f"  {'CONCEPTO':<40}" + "".join(f"{a:>13}" for a in años)
    print(Fore.CYAN + col_header + Style.RESET_ALL)
    print(f"  {'─'*40}" + "─"*13*len(años))

    def fila(label, serie, es_pct=False, usa_escala=True, is_ratio=False):
        if usa_escala and not es_pct and not is_ratio:
            vals = "".join(fmt_val(serie.get(c), escala) for c in cols)
        elif es_pct:
            vals = "".join(fmt_pct(serie.get(c)) for c in cols)
        else:
            # Para ratios (Ev/Ebitda, PE, etc)
            vals = ""
            for c in cols:
                v = serie.get(c)
                if pd.notna(v):
                    color = Fore.GREEN if v >= 0 else Fore.RED
                    vals += f"{color}{v:>12.2f}x"
                else:
                    vals += Fore.WHITE + Style.DIM + "         N/D "
        print(f"  {label:<40}{vals}")

    fila("Market cap",                              datos["market_cap"])
    fila("Net DEBT  (-) si es caja neta",           datos["net_debt"])
    fila("Deuda neta /EBITDA",                      datos["deuda_neta_ebitda"], is_ratio=True)
    fila("Enterprise Value ( EV )",                 datos["ev"])
    print(f"  {'─'*40}" + "─"*13*len(años))
    fila("EBITDA",                                  datos["ebitda"])
    fila("EBIT",                                    datos["ebit"])
    fila("Net income",                              datos["net_income"])
    fila("FCF",                                     datos["fcf"])
    print()
    
    subheader("Múltiplos Históricos")
    print(Fore.CYAN + col_header + Style.RESET_ALL)
    print(f"  {'─'*40}" + "─"*13*len(años))
    fila("Ev/Sale",                                 datos["ev_sale"], is_ratio=True)
    fila("Ev/Ebitda",                               datos["ev_ebitda"], is_ratio=True)
    fila("Ev/Ebit",                                 datos["ev_ebit"], is_ratio=True)
    fila("Ev/FCF",                                  datos["ev_fcf"], is_ratio=True)
    fila("P/FCF",                                   datos["p_fcf"], is_ratio=True)
    fila("FCF Yield",                               datos["fcf_yield"], es_pct=True)
    fila("PE",                                      datos["pe"], is_ratio=True)
    print()

def main():
    info, financials, balance, cashflow, hist = descargar_datos(TICKER)
    datos = calcular_valoracion(financials, balance, cashflow, hist, YEARS, info)
    
    escala_usar = ESCALA
    if escala_usar == "AUTO":
        mcs = [v for v in datos["market_cap"].values if pd.notna(v)]
        ultimo_mc = mcs[-1] if mcs else 0
        escala_usar = "B" if ultimo_mc >= 100_000_000_000 else "M"
        
    mostrar_encabezado(info, TICKER)
    mostrar_valoracion(datos, escala_usar)

if __name__ == "__main__":
    main()
