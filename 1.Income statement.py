"""
╔══════════════════════════════════════════════════════════════════╗
║         VALKIRIA CAPITAL — Análisis Fundamental                  ║
║         1. Income statement                                      ║
╚══════════════════════════════════════════════════════════════════╝

DESCRIPCIÓN:
  Descarga y analiza el estado de resultados de cualquier empresa.
  Calcula márgenes, tendencias y señales de calidad del negocio,
  con la estructura de la primera página del Excel de valoración.

CÓMO USAR:
  1. Cambiá TICKER por el símbolo que querés analizar
  2. Ejecutá:  python "1.Income statement.py"
"""

# ════════════════════════════════════════════════════════════════════
#   ★  CONFIGURACIÓN — EDITÁ SOLO ESTA SECCIÓN  ★
# ════════════════════════════════════════════════════════════════════

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
    print(f"Ejecutá:  pip install yfinance pandas colorama")
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
    cashflow   = t.cashflow
    if financials is None or financials.empty:
        print(Fore.RED + "ERROR")
        sys.exit(1)
    print(Fore.GREEN + "OK")
    return info, financials, cashflow

def obtener_fila(df: pd.DataFrame, posibles_nombres: list):
    for nombre in posibles_nombres:
        if nombre in df.index:
            return df.loc[nombre]
    return pd.Series([None] * len(df.columns), index=df.columns)

def calcular_pyg(financials: pd.DataFrame, cashflow: pd.DataFrame, years):
    todas_cols = sorted(financials.columns)
    if isinstance(years, list):
        cols = [c for c in todas_cols if int(str(c)[:4]) in years]
    else:
        cols = todas_cols[-years:]
        
    if not cols:
        print(f"\n\033[91m  ATENCIÓN: yfinance no devolvió datos para esos años.\033[0m")
        sys.exit(1)
        
    fin = financials[cols]
    cf = cashflow[cols] if cashflow is not None and not cashflow.empty else pd.DataFrame(columns=cols)

    revenue      = obtener_fila(fin, ["Total Revenue", "Operating Revenue", "Revenue"])
    cogs         = obtener_fila(fin, ["Cost Of Revenue", "Cost of Revenue", "Cost Of Goods Sold"])
    gross_profit = obtener_fila(fin, ["Gross Profit"])
    ebitda       = obtener_fila(fin, ["EBITDA", "Ebitda", "Normalized EBITDA"])
    
    depreciation = obtener_fila(cf, ["Depreciation And Amortization", "Depreciation Amortization Depletion", "Reconciled Depreciation"])
    
    ebit         = obtener_fila(fin, ["Operating Income", "EBIT", "Ebit"])
    interest_exp = obtener_fila(fin, ["Net Non Operating Interest Income Expense", "Interest Expense", "Interest Expense Non Operating"])
    pretax       = obtener_fila(fin, ["Pretax Income"])
    tax          = obtener_fila(fin, ["Tax Provision", "Income Tax Expense"])
    consolidated_net_income = obtener_fila(fin, ["Net Income Including Noncontrolling Interests"])
    net_income   = obtener_fila(fin, ["Net Income", "Net Income Common Stockholders"])
    eps          = obtener_fila(fin, ["Diluted EPS", "Basic EPS"])
    diluted_shares = obtener_fila(fin, ["Diluted Average Shares", "Basic Average Shares"])

    def margen(n, d):
        r = {}
        for c in cols:
            nv = n.get(c)
            dv = d.get(c)
            if pd.notna(nv) and pd.notna(dv) and dv != 0:
                r[c] = (nv / dv) * 100
            else:
                r[c] = None
        return pd.Series(r)

    def crecimiento_yoy(serie):
        r = {}
        for i, c in enumerate(cols):
            if i == 0:
                r[c] = None
                continue
            ant = serie.get(cols[i-1])
            act = serie.get(c)
            if pd.notna(ant) and pd.notna(act) and ant != 0:
                r[c] = ((act - ant) / abs(ant)) * 100
            else:
                r[c] = None
        return pd.Series(r)

    minority = pd.Series(index=cols)
    for c in cols:
        cni = consolidated_net_income.get(c)
        ni = net_income.get(c)
        if pd.notna(cni) and pd.notna(ni):
            minority[c] = cni - ni
        else:
            minority[c] = None

    tax_rate = pd.Series(index=cols)
    for c in cols:
        t = tax.get(c)
        p = pretax.get(c)
        if pd.notna(t) and pd.notna(p) and p != 0:
            tax_rate[c] = (t / p) * 100
        else:
            tax_rate[c] = None

    return {
        "cols": cols,
        "revenue": revenue,
        "crec_revenue": crecimiento_yoy(revenue),
        "cogs": cogs,
        "gross_profit": gross_profit,
        "margen_bruto": margen(gross_profit, revenue),
        "ebitda": ebitda,
        "margen_ebitda": margen(ebitda, revenue),
        "depreciation": depreciation,
        "ebit": ebit,
        "margen_ebit": margen(ebit, revenue),
        "interest_exp": interest_exp,
        "pretax": pretax,
        "tax": tax,
        "tax_rate": tax_rate,
        "consolidated_net_income": consolidated_net_income,
        "minority": minority,
        "net_income": net_income,
        "margen_neto": margen(net_income, revenue),
        "eps": eps,
        "diluted_shares": diluted_shares
    }

def mostrar_encabezado(info: dict, ticker: str):
    nombre = info.get("longName") or info.get("shortName") or ticker
    print(f"\n{Fore.CYAN}{DIV2}")
    print(f"  VALKIRIA CAPITAL — Análisis Fundamental")
    print(f"  1. Income statement")
    print(f"{DIV2}{Style.RESET_ALL}")
    print(f"\n  {Fore.WHITE}{Style.BRIGHT}{nombre}{Style.RESET_ALL}  {Fore.YELLOW}[{ticker}]{Style.RESET_ALL}")

def mostrar_pyg(datos: dict, escala: str):
    cols = datos["cols"]
    años = [str(c)[:4] for c in cols]

    subheader("1. Income statement")
    sufijo = "en millones" if escala == "M" else "en billones"
    print(f"  {Fore.WHITE}({sufijo} de moneda local){Style.RESET_ALL}\n")

    col_header = f"  {'CONCEPTO':<40}" + "".join(f"{a:>13}" for a in años)
    print(Fore.CYAN + col_header + Style.RESET_ALL)
    print(f"  {'─'*40}" + "─"*13*len(años))

    def fila(label, serie, es_pct=False, usa_escala=True):
        if usa_escala and not es_pct:
            vals = "".join(fmt_val(serie.get(c), escala) for c in cols)
        elif es_pct:
            vals = "".join(fmt_pct(serie.get(c)) for c in cols)
        else:
            # Para EPS sin escala
            vals = ""
            for c in cols:
                v = serie.get(c)
                if pd.notna(v):
                    color = Fore.GREEN if v >= 0 else Fore.RED
                    vals += f"{color}{v:>12.2f} "
                else:
                    vals += Fore.WHITE + Style.DIM + "         N/D "
        print(f"  {label:<40}{vals}")

    fila("Sales Value of Production (Revenue)", datos["revenue"])
    fila("Y/Y Growth %",                        datos["crec_revenue"], es_pct=True)
    fila("COGS",                                datos["cogs"])
    fila("Gross Profit",                        datos["gross_profit"])
    fila("Gross margin %",                      datos["margen_bruto"], es_pct=True)
    print()
    fila("EBITDA",                              datos["ebitda"])
    fila("EBITDA margin %",                     datos["margen_ebitda"], es_pct=True)
    fila("Depreciation & Amortization Expense", datos["depreciation"])
    fila("EBIT",                                datos["ebit"])
    fila("EBIT margin %",                       datos["margen_ebit"], es_pct=True)
    print()
    fila("Interest expense / Income",           datos["interest_exp"])
    fila("Pretax Income",                       datos["pretax"])
    fila("Income Taxes",                        datos["tax"])
    fila("tax rate %",                          datos["tax_rate"], es_pct=True)
    print()
    fila("Consolidated Net Income",             datos["consolidated_net_income"])
    fila("Minority Interest",                   datos["minority"])
    fila("Net Income",                          datos["net_income"])
    fila("Margen beneficio neto %",             datos["margen_neto"], es_pct=True)
    print()
    
    def fila_shares():
        vals = ""
        for c in cols:
            v = datos["diluted_shares"].get(c)
            if pd.notna(v):
                v_m = v / 1_000_000
                vals += f"{Fore.GREEN}{v_m:>12.2f} "
            else:
                vals += Fore.WHITE + Style.DIM + "         N/D "
        print(f"  {'Fully diluted shares (millions)':<40}{vals}")

    fila("Net income per share ( EPS )",        datos["eps"], usa_escala=False)
    fila_shares()

def main():
    info, financials, cashflow = descargar_datos(TICKER)
    datos = calcular_pyg(financials, cashflow, YEARS)
    
    escala_usar = ESCALA
    if escala_usar == "AUTO":
        revs = [v for v in datos["revenue"].values if pd.notna(v)]
        ultimo_rev = revs[-1] if revs else 0
        escala_usar = "B" if ultimo_rev >= 100_000_000_000 else "M"
        
    mostrar_encabezado(info, TICKER)
    mostrar_pyg(datos, escala_usar)
    print("\n")

if __name__ == "__main__":
    main()
