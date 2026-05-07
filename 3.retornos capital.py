"""
╔══════════════════════════════════════════════════════════════════╗
║         VALKIRIA CAPITAL — Análisis Fundamental                  ║
║         3. Retornos de capital                                   ║
╚══════════════════════════════════════════════════════════════════╝

DESCRIPCIÓN:
  Calcula el retorno sobre el capital invertido y métricas de balance.
  Con la estructura de la tercera página del Excel de valoración.

CÓMO USAR:
  1. Cambiá TICKER por el símbolo que querés analizar
  2. Ejecutá:  python "3.retornos capital.py"
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
    if financials is None or financials.empty or balance is None or balance.empty:
        print(Fore.RED + "ERROR")
        sys.exit(1)
    print(Fore.GREEN + "OK")
    return info, financials, balance

def obtener_fila(df: pd.DataFrame, posibles_nombres: list):
    for nombre in posibles_nombres:
        if nombre in df.index:
            return df.loc[nombre]
    return pd.Series([None] * len(df.columns), index=df.columns)

def calcular_retornos(financials: pd.DataFrame, balance: pd.DataFrame, years):
    todas_cols = sorted(balance.columns)
    if isinstance(years, list):
        cols = [c for c in todas_cols if int(str(c)[:4]) in years]
    else:
        cols = todas_cols[-years:]
        
    fin = financials[cols] if financials is not None and not financials.empty else pd.DataFrame(columns=cols)
    bal = balance[cols]

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

    # Si yfinance trae nulos donde debería ser 0 (ej: leases), lo rellenamos
    def fill_zero(serie):
        s = serie.copy()
        for c in cols:
            if pd.isna(s.get(c)):
                s[c] = 0
        return s

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
        eq = equity[c]
        dt = debt[c]
        le = leases[c]
        gw = goodwill[c]
        cap_con_gw[c] = eq + dt + le
        cap_sin_gw[c] = cap_con_gw[c] - gw

    # ROE y ROCE
    roe = pd.Series(index=cols)
    roce_con_gw = pd.Series(index=cols)
    roce_sin_gw = pd.Series(index=cols)
    for c in cols:
        if pd.notna(net_income.get(c)) and equity[c] != 0:
            roe[c] = (net_income[c] / equity[c]) * 100
        else:
            roe[c] = None
            
        if pd.notna(ebit.get(c)):
            if cap_con_gw[c] != 0:
                roce_con_gw[c] = (ebit[c] / cap_con_gw[c]) * 100
            else:
                roce_con_gw[c] = None
            if cap_sin_gw[c] != 0:
                roce_sin_gw[c] = (ebit[c] / cap_sin_gw[c]) * 100
            else:
                roce_sin_gw[c] = None

    # ROIC = NOPAT / (Deuda + Equity + Leases - Cash - Marketable)
    nopat = pd.Series(index=cols)
    roic = pd.Series(index=cols)
    for c in cols:
        t = tax.get(c)
        p = pretax.get(c)
        tax_rate = (t / p) if (pd.notna(t) and pd.notna(p) and p != 0) else 0.20
        e = ebit.get(c)
        if pd.notna(e):
            nopat[c] = e * (1 - tax_rate)
        else:
            nopat[c] = None
            
        invested_cap = debt[c] + equity[c] + leases[c] - cash[c] - marketable[c]
        if pd.notna(nopat.get(c)) and invested_cap != 0:
            roic[c] = (nopat[c] / invested_cap) * 100
        else:
            roic[c] = None

    return {
        "cols": cols,
        "ebit": ebit,
        "interest": interest,
        "tax": tax,
        "net_income": net_income,
        "cash": cash,
        "debt": debt,
        "leases": leases,
        "goodwill": goodwill,
        "equity": equity,
        "cap_con_gw": cap_con_gw,
        "cap_sin_gw": cap_sin_gw,
        "roe": roe,
        "roce_con_gw": roce_con_gw,
        "roce_sin_gw": roce_sin_gw,
        "nopat": nopat,
        "marketable": marketable,
        "roic": roic
    }

def mostrar_encabezado(info: dict, ticker: str):
    nombre = info.get("longName") or info.get("shortName") or ticker
    print(f"\n{Fore.CYAN}{DIV2}")
    print(f"  VALKIRIA CAPITAL — Análisis Fundamental")
    print(f"  3. Retornos de capital")
    print(f"{DIV2}{Style.RESET_ALL}")
    print(f"\n  {Fore.WHITE}{Style.BRIGHT}{nombre}{Style.RESET_ALL}  {Fore.YELLOW}[{ticker}]{Style.RESET_ALL}")

def mostrar_retornos(datos: dict, escala: str):
    cols = datos["cols"]
    años = [str(c)[:4] for c in cols]

    subheader("3. Retornos capital")
    sufijo = "en millones" if escala == "M" else "en billones"
    print(f"  {Fore.WHITE}({sufijo} de moneda local){Style.RESET_ALL}\n")

    col_header = f"  {'CONCEPTO':<40}" + "".join(f"{a:>13}" for a in años)
    print(Fore.CYAN + col_header + Style.RESET_ALL)
    print(f"  {'─'*40}" + "─"*13*len(años))

    def fila(label, serie, es_pct=False):
        if not es_pct:
            vals = "".join(fmt_val(serie.get(c), escala) for c in cols)
        else:
            vals = "".join(fmt_pct(serie.get(c)) for c in cols)
        print(f"  {label:<40}{vals}")

    fila("EBIT",                                 datos["ebit"])
    fila("Interest",                             datos["interest"])
    fila("Tasas",                                datos["tax"])
    fila("Net income",                           datos["net_income"])
    fila("(+) Cash and cash equivalents",        datos["cash"])
    fila("(+) Deuda total",                      datos["debt"])
    fila("(+) Opreating Leases",                 datos["leases"])
    fila("(+) Goodwill",                         datos["goodwill"])
    fila("(+) Equity",                           datos["equity"])
    print(f"  {'─'*40}" + "─"*13*len(años))
    fila("Capital empleado con goodwill",        datos["cap_con_gw"])
    fila("Capital empleado sin goodwill",        datos["cap_sin_gw"])
    print()
    fila("ROE ( net income / equity )",          datos["roe"], es_pct=True)
    fila("ROCE sin goodwill(EBIT/Cap. emp)",     datos["roce_sin_gw"], es_pct=True)
    fila("ROCE con goodwill(EBIT/Cap. emp)",     datos["roce_con_gw"], es_pct=True)
    print()
    
    subheader("Profitability and Efficiency Ratios")
    print(Fore.CYAN + col_header + Style.RESET_ALL)
    print(f"  {'─'*40}" + "─"*13*len(años))
    
    fila("EBIT x (1-t) NOPAT",                   datos["nopat"])
    fila("Interest",                             datos["interest"])
    fila("Tasas",                                datos["tax"])
    fila("Net income",                           datos["net_income"])
    fila("(-) Cash and cash equivalents",        datos["cash"])
    fila("(-) Marketable Securities",            datos["marketable"])
    fila("(+) Deuda total",                      datos["debt"])
    print(f"  {'─'*40}" + "─"*13*len(años))
    fila("ROIC",                                 datos["roic"], es_pct=True)
    print()

def main():
    info, financials, balance = descargar_datos(TICKER)
    datos = calcular_retornos(financials, balance, YEARS)
    
    escala_usar = ESCALA
    if escala_usar == "AUTO":
        eqs = [v for v in datos["equity"].values if pd.notna(v)]
        ultimo_eq = eqs[-1] if eqs else 0
        escala_usar = "B" if ultimo_eq >= 100_000_000_000 else "M"
        
    mostrar_encabezado(info, TICKER)
    mostrar_retornos(datos, escala_usar)

if __name__ == "__main__":
    main()
