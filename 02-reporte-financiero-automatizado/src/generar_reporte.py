"""Automatiza el reporte financiero mensual: CSV de transacciones -> Excel listo para gerencia.

Uso:
    python src/generar_reporte.py                                  # usa data/transacciones_2025.csv
    python src/generar_reporte.py --entrada mis_datos.csv --salida reporte.xlsx

El Excel generado tiene 3 hojas con formato, encabezados fijos y 2 gráficos nativos:
  - Resumen mensual: ingresos, gastos, resultado y margen por mes
  - Estado de resultados: cuentas x meses con total anual
  - Transacciones: detalle original
Además genera outputs/dashboard_financiero.png y outputs/metricas.json.
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from openpyxl import load_workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from estilo import MESES, S1, S2, S3, SURF, TXT2, header, hbar_labels, kpi_row, money, panel_texto

BASE = Path(__file__).resolve().parents[1]
COLUMNAS = {"fecha", "tipo", "cuenta", "monto"}


def cargar(ruta: Path) -> pd.DataFrame:
    tx = pd.read_csv(ruta, parse_dates=["fecha"])
    faltan = COLUMNAS - set(tx.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el archivo de entrada: {sorted(faltan)}")
    tipos = set(tx.tipo.unique()) - {"Ingreso", "Gasto"}
    if tipos:
        raise ValueError(f"Valores de 'tipo' no reconocidos: {sorted(tipos)}")
    tx["mes"] = tx.fecha.dt.month
    return tx


def calcular(tx: pd.DataFrame):
    meses = sorted(tx.mes.unique())
    etiquetas = [MESES[m - 1] for m in meses]
    pyg = tx.pivot_table(index=["tipo", "cuenta"], columns="mes", values="monto", aggfunc="sum", fill_value=0).round(2)
    pyg.columns = etiquetas
    pyg["Total"] = pyg.sum(axis=1)
    res = tx.pivot_table(index="mes", columns="tipo", values="monto", aggfunc="sum", fill_value=0)
    res["Resultado"] = res.Ingreso - res.Gasto
    res["Margen %"] = (res.Resultado / res.Ingreso * 100).round(1)
    res.index = etiquetas
    return res, pyg


def escribir_excel(tx, res, pyg, salida: Path):
    with pd.ExcelWriter(salida, engine="openpyxl") as w:
        res.round(2).to_excel(w, sheet_name="Resumen mensual", index_label="Mes")
        pyg.to_excel(w, sheet_name="Estado de resultados")
        tx.drop(columns="mes").to_excel(w, sheet_name="Transacciones", index=False)

    wb = load_workbook(salida)
    head = PatternFill("solid", fgColor="1F3A5F")
    thin = Side(style="thin", color="D9D9D9")
    for ws in wb.worksheets:
        for c in ws[1]:
            c.fill, c.font = head, Font(color="FFFFFF", bold=True)
            c.alignment = Alignment(horizontal="center")
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 16
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.border = Border(bottom=thin)
                if isinstance(c.value, float):
                    c.number_format = "#,##0.00"
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions

    ws = wb["Resumen mensual"]
    n = ws.max_row
    ch = BarChart()
    ch.type, ch.title, ch.height, ch.width = "col", "Ingresos y gastos por mes", 8, 18
    ch.add_data(Reference(ws, min_col=2, max_col=3, min_row=1, max_row=n), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n))
    ws.add_chart(ch, "H2")
    lc = LineChart()
    lc.title, lc.height, lc.width = "Resultado neto mensual", 8, 18
    lc.add_data(Reference(ws, min_col=4, max_col=4, min_row=1, max_row=n), titles_from_data=True)
    lc.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n))
    ws.add_chart(lc, "H20")
    wb.save(salida)


def dashboard(tx, res, salida: Path) -> dict:
    ing, gas = res.Ingreso.sum(), res.Gasto.sum()
    gcat = tx[tx.tipo == "Gasto"].groupby("cuenta").monto.sum().sort_values()
    lo, hi = res["Margen %"].idxmin(), res["Margen %"].idxmax()

    fig = plt.figure(figsize=(16, 10), dpi=110)
    header(fig, "Reporte Financiero Mensual Automatizado",
           "Python lee las transacciones, arma el estado de resultados y genera el Excel con formato y gráficos en segundos.")
    kpi_row(fig, [("Ingresos del año", money(ing), None), ("Gastos del año", money(gas), None),
                  ("Resultado neto", money(ing - gas), None), ("Margen neto", f"{(ing - gas) / ing * 100:.1f}%", None)])

    ax = fig.add_axes([0.035, 0.40, 0.56, 0.31])
    x, wbar = np.arange(len(res)), 0.38
    ax.bar(x - wbar / 2 - 0.01, res.Ingreso, wbar, color=S1, label="Ingresos")
    ax.bar(x + wbar / 2 + 0.01, res.Gasto, wbar, color=S2, label="Gastos")
    ax.set_xticks(x, res.index)
    ax.yaxis.set_major_formatter(FuncFormatter(money))
    ax.legend(frameon=False, loc="upper left", ncol=2)
    ax.set_title("Ingresos vs gastos por mes")
    ax.set_ylim(0, res.Ingreso.max() * 1.18)

    ax = fig.add_axes([0.69, 0.40, 0.275, 0.31])
    ax.barh(gcat.index, gcat.values, color=S2, height=0.6)
    hbar_labels(ax, gcat.values, lambda v: f"{v / gas * 100:.0f}%")
    ax.xaxis.set_major_formatter(FuncFormatter(money))
    ax.set_title("Estructura de gastos del año")
    ax.set_xlim(0, gcat.max() * 1.22)

    ax = fig.add_axes([0.035, 0.06, 0.56, 0.27])
    ax.plot(res.index, res["Margen %"], color=S3, lw=2.2, marker="o", ms=6)
    ilo, ihi = list(res.index).index(lo), list(res.index).index(hi)
    ax.annotate(f"  Mínimo: {res.loc[lo, 'Margen %']:.0f}%", xy=(ilo, res.loc[lo, "Margen %"]), fontsize=10.5, color=TXT2, va="center")
    ax.annotate(f"Máximo: {res.loc[hi, 'Margen %']:.0f}%", xy=(ihi, res.loc[hi, "Margen %"]), xytext=(0, 9),
                textcoords="offset points", fontsize=10.5, color=TXT2, ha="center")
    ax.set_title("Margen neto mensual (%)")
    ax.set_ylim(res["Margen %"].min() - 7, res["Margen %"].max() + 4)

    ax = fig.add_axes([0.62, 0.06, 0.345, 0.27])
    panel_texto(ax, "Cómo funciona la automatización", (
        "1. Lee el CSV de transacciones del sistema\n    contable y valida columnas (Pandas).\n"
        "2. Calcula el estado de resultados por mes.\n"
        "3. Genera el Excel con formato, filtros y gráficos\n    nativos (openpyxl), listo para gerencia.\n"
        "4. Se ejecuta con un comando o programado cada mes."))
    fig.savefig(salida, facecolor=SURF)
    plt.close(fig)

    return {
        "ingresos": round(ing, 2), "gastos": round(gas, 2), "resultado": round(ing - gas, 2),
        "margen_pct": round((ing - gas) / ing * 100, 1),
        "mes_margen_min": lo, "margen_min_pct": float(res.loc[lo, "Margen %"]),
        "mes_margen_max": hi, "margen_max_pct": float(res.loc[hi, "Margen %"]),
        "gasto_principal": gcat.idxmax(), "gasto_principal_pct": round(gcat.max() / gas * 100, 1),
        "transacciones": int(len(tx)),
    }


def main():
    p = argparse.ArgumentParser(description="Genera el reporte financiero mensual en Excel.")
    p.add_argument("--entrada", type=Path, default=BASE / "data" / "transacciones_2025.csv")
    p.add_argument("--salida", type=Path, default=BASE / "outputs" / "reporte_financiero_2025.xlsx")
    a = p.parse_args()
    a.salida.parent.mkdir(parents=True, exist_ok=True)

    tx = cargar(a.entrada)
    res, pyg = calcular(tx)
    escribir_excel(tx, res, pyg, a.salida)
    out = BASE / "outputs"
    out.mkdir(exist_ok=True)
    m = dashboard(tx, res, out / "dashboard_financiero.png")
    (out / "metricas.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Reporte generado: {a.salida}")
    print(json.dumps(m, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
