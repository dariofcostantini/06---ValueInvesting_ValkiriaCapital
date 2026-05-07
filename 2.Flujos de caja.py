"""
╔══════════════════════════════════════════════════════════════════╗
║         VALKIRIA CAPITAL — Análisis Fundamental                  ║
║         2. Flujos de caja                                        ║
╚══════════════════════════════════════════════════════════════════╝

DESCRIPCIÓN:
  Descarga y analiza el estado de flujos de caja de cualquier empresa.
  Calcula FCF, ratios de conversión y otras métricas,
  con la estructura de la segunda página del Excel de valoración.

CÓMO USAR:
  1. Cambiá TICKER por el símbolo que querés analizar
  2. Ejecutá:  python "2.Flujos de caja.py"
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
    if financials is None or financials.empty or cashflow is None or cashflow.empty:
        print(Fore.RED + "ERROR")
        sys.exit(1)
    print(Fore.GREEN + "OK")
    return info, financials, cashflow

def obtener_fila(df: pd.DataFrame, posibles_nombres: list):
    for nombre in posibles_nombres:
        if nombre in df.index:
            return df.loc[nombre]
    return pd.Series([None] * len(df.columns), index=df.columns)

def calcular_flujos(financials: pd.DataFrame, cashflow: pd.DataFrame, years):
    todas_cols = sorted(cashflow.columns)
    if isinstance(years, list):
        cols = [c for c in todas_cols if int(str(c)[:4]) in years]
    else:
        cols = todas_cols[-years:]
        
    if not cols:
        print(f"\n\033[91m  ATENCIÓN: yfinance no devolvió datos para esos años.\033[0m")
        sys.exit(1)
        
    fin = financials[cols] if financials is not None and not financials.empty else pd.DataFrame(columns=cols)
    cf  = cashflow[cols]

    # Revenue para el ratio Capex / Sale
    revenue = obtener_fila(fin, ["Total Revenue", "Operating Revenue", "Revenue"])
    
    # EBITDA de financials
    ebitda = obtener_fila(fin, ["EBITDA", "Ebitda", "Normalized EBITDA"])
    
    # Capex de cashflow (normalmente negativo)
    capex_raw = obtener_fila(cf, ["Capital Expenditure", "Capital Expenditures", "Purchase Of Property Plant And Equipment"])
    capex = capex_raw.copy()
    for c in cols:
        if pd.notna(capex[c]):
            capex[c] = abs(capex[c]) # Convertimos a positivo para mostrarlo como en Excel
            
    # Intereses y Tasas desde financials
    interest_exp = obtener_fila(fin, ["Net Non Operating Interest Income Expense", "Interest Expense", "Interest Expense Non Operating"])
    intereses = interest_exp.copy()
    for c in cols:
        if pd.notna(intereses[c]):
            intereses[c] = abs(intereses[c]) # Positivo en Excel

    tax = obtener_fila(fin, ["Tax Provision", "Income Tax Expense"])
    tasas = tax.copy()
    for c in cols:
        if pd.notna(tasas[c]):
            tasas[c] = abs(tasas[c])

    # Working Capital
    wc = obtener_fila(cf, ["Change In Working Capital"])

    # Stock options / minoritarios
    sbc = obtener_fila(cf, ["Stock Based Compensation", "Share Based Compensation"])

    # Free Cash Flow (Flujo de caja libre) = Operating Cash Flow - abs(Capex)
    op_cf = obtener_fila(cf, ["Operating Cash Flow", "Cash From Operations", "Net Cash Provided By Operating Activities", "Total Cash From Operating Activities"])
    fcf = pd.Series(index=cols)
    for c in cols:
        if pd.notna(op_cf.get(c)) and pd.notna(capex.get(c)):
            fcf[c] = op_cf[c] - capex[c]
        else:
            fcf[c] = None

    # Shares para per share
    diluted_shares = obtener_fila(fin, ["Diluted Average Shares", "Basic Average Shares"])
    
    # Ratios
    fcf_per_share = pd.Series(index=cols)
    conversion_fcf_ebitda = pd.Series(index=cols)
    capex_sale = pd.Series(index=cols)

    for c in cols:
        # FCF per share
        if pd.notna(fcf.get(c)) and pd.notna(diluted_shares.get(c)) and diluted_shares[c] != 0:
            fcf_per_share[c] = fcf[c] / diluted_shares[c]
        else:
            fcf_per_share[c] = None
            
        # Conversion FCF/EBITDA
        if pd.notna(fcf.get(c)) and pd.notna(ebitda.get(c)) and ebitda[c] != 0:
            conversion_fcf_ebitda[c] = (fcf[c] / ebitda[c]) * 100
        else:
            conversion_fcf_ebitda[c] = None

        # Capex / Sale
        if pd.notna(capex.get(c)) and pd.notna(revenue.get(c)) and revenue[c] != 0:
            capex_sale[c] = (capex[c] / revenue[c]) * 100
        else:
            capex_sale[c] = None

    return {
        "cols": cols,
        "revenue": revenue,
        "ebitda": ebitda,
        "capex": capex,
        "intereses": intereses,
        "tasas": tasas,
        "wc": wc,
        "sbc": sbc,
        "fcf": fcf,
        "fcf_per_share": fcf_per_share,
        "conversion_fcf_ebitda": conversion_fcf_ebitda,
        "capex_sale": capex_sale,
        "diluted_shares": diluted_shares
    }

def mostrar_encabezado(info: dict, ticker: str):
    nombre = info.get("longName") or info.get("shortName") or ticker
    print(f"\n{Fore.CYAN}{DIV2}")
    print(f"  VALKIRIA CAPITAL — Análisis Fundamental")
    print(f"  2. Flujos de caja")
    print(f"{DIV2}{Style.RESET_ALL}")
    print(f"\n  {Fore.WHITE}{Style.BRIGHT}{nombre}{Style.RESET_ALL}  {Fore.YELLOW}[{ticker}]{Style.RESET_ALL}")

def mostrar_flujos(datos: dict, escala: str):
    cols = datos["cols"]
    años = [str(c)[:4] for c in cols]

    subheader("2. Flujos de caja")
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
            # Para valores sin escala (per share)
            vals = ""
            for c in cols:
                v = serie.get(c)
                if pd.notna(v):
                    color = Fore.GREEN if v >= 0 else Fore.RED
                    vals += f"{color}{v:>12.2f} "
                else:
                    vals += Fore.WHITE + Style.DIM + "         N/D "
        print(f"  {label:<40}{vals}")

    fila("EBITDA",                                  datos["ebitda"])
    fila("Capex (introducir manual)",               datos["capex"])
    fila("Intereses",                               datos["intereses"])
    fila("Tasas",                                   datos["tasas"])
    fila("WC",                                      datos["wc"])
    fila("Stock options/minoritarios (si procede)", datos["sbc"])
    print(f"  {'─'*40}" + "─"*13*len(años))
    fila("Flujo de caja libre",                     datos["fcf"])
    fila("Flujo de caja libre por accion",          datos["fcf_per_share"], usa_escala=False)
    print()
    fila("Conversion FCF/Ebitda",                   datos["conversion_fcf_ebitda"], es_pct=True)
    print()
    fila("Capex /Sale",                             datos["capex_sale"], es_pct=True)
    print()

def main():
    info, financials, cashflow = descargar_datos(TICKER)
    datos = calcular_flujos(financials, cashflow, YEARS)
    
    escala_usar = ESCALA
    if escala_usar == "AUTO":
        revs = [v for v in datos["revenue"].values if pd.notna(v)]
        ultimo_rev = revs[-1] if revs else 0
        escala_usar = "B" if ultimo_rev >= 100_000_000_000 else "M"
        
    mostrar_encabezado(info, TICKER)
    mostrar_flujos(datos, escala_usar)

if __name__ == "__main__":
    main()
