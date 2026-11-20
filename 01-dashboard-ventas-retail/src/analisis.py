"""Análisis de ventas y rentabilidad retail 2025.

Lee data/ventas_retail_2025.csv, calcula KPIs y cortes por mes, categoría y región,
y genera outputs/dashboard_ventas.png + outputs/metricas.json + tablas resumen en CSV.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from estilo import GRAY, MESES, S1, S2, SURF, header, hbar_labels, kpi_row, money, panel_texto

BASE = Path(__file__).resolve().parents[1]
DATA, OUT = BASE / "data", BASE / "outputs"


def cargar() -> pd.DataFrame:
    df = pd.read_csv(DATA / "ventas_retail_2025.csv", parse_dates=["fecha"])
    df["mes"] = df.fecha.dt.month
    return df


def resumen(df: pd.DataFrame) -> dict:
    mensual = df.groupby("mes")[["venta", "ganancia"]].sum()
    por_cat = df.groupby("categoria")[["venta", "ganancia"]].sum()
    por_cat["margen"] = por_cat.ganancia / por_cat.venta * 100
    por_reg = df.groupby("region")[["venta", "ganancia"]].sum()
    por_reg["margen"] = por_reg.ganancia / por_reg.venta * 100
    return {"mensual": mensual, "categoria": por_cat.sort_values("venta"), "region": por_reg.sort_values("margen")}


def main():
    OUT.mkdir(exist_ok=True)
    df = cargar()
    r = resumen(df)
    mensual, por_cat, por_reg = r["mensual"], r["categoria"], r["region"]
    total, gan, pedidos = df.venta.sum(), df.ganancia.sum(), len(df)

    top = por_cat.venta.idxmax()
    mg = por_cat.margen.idxmax()
    best, worst = mensual.venta.idxmax(), mensual.venta.idxmin()
    reg_baja = por_reg.margen.idxmin()
    brecha = por_reg.drop(reg_baja).margen.mean() - por_reg.margen.min()
    q4 = mensual.loc[[11, 12], "venta"].sum() / total * 100

    metricas = {
        "ventas_totales": round(total, 2),
        "ganancia_total": round(gan, 2),
        "margen_pct": round(gan / total * 100, 1),
        "transacciones": int(pedidos),
        "ticket_promedio": round(total / pedidos, 2),
        "categoria_top": top,
        "categoria_top_share_pct": round(por_cat.venta.max() / total * 100, 1),
        "categoria_mayor_margen": mg,
        "categoria_mayor_margen_pct": round(por_cat.margen.max(), 1),
        "region_margen_mas_bajo": reg_baja,
        "brecha_margen_pp": round(brecha, 1),
        "mejor_mes": MESES[best - 1],
        "peor_mes": MESES[worst - 1],
        "nov_dic_share_pct": round(q4, 1),
    }
    (OUT / "metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    por_cat.round(2).to_csv(OUT / "resumen_categoria.csv")
    por_reg.round(2).to_csv(OUT / "resumen_region.csv")
    mensual.round(2).to_csv(OUT / "resumen_mensual.csv")

    fig = plt.figure(figsize=(16, 10), dpi=110)
    header(fig, "Dashboard de Ventas y Rentabilidad 2025",
           "Tienda retail multicanal - 4 categorías, 4 regiones. Transacciones diarias procesadas con Python/Pandas.")
    kpi_row(fig, [("Ventas totales", money(total), None), ("Ganancia", money(gan), None),
                  ("Margen promedio", f"{gan / total * 100:.1f}%", None),
                  ("Ticket promedio", f"${total / pedidos:,.0f}", None)])

    ax = fig.add_axes([0.035, 0.40, 0.56, 0.31])
    ax.plot(MESES, mensual.venta.values, color=S1, lw=2.2, marker="o", ms=6, label="Ventas")
    ax.plot(MESES, mensual.ganancia.values, color=S2, lw=2.2, marker="o", ms=6, label="Ganancia")
    ax.yaxis.set_major_formatter(FuncFormatter(money))
    ax.set_title("Ventas y ganancia por mes")
    ax.legend(loc="upper left", frameon=False, ncol=2)

    ax = fig.add_axes([0.66, 0.40, 0.305, 0.31])
    ax.barh(por_cat.index, por_cat.venta, color=S1, height=0.55)
    hbar_labels(ax, por_cat.venta, money)
    ax.xaxis.set_major_formatter(FuncFormatter(money))
    ax.set_title("Ventas por categoría")
    ax.set_xlim(0, por_cat.venta.max() * 1.25)

    ax = fig.add_axes([0.085, 0.06, 0.39, 0.27])
    ax.barh(por_reg.index, por_reg.margen, height=0.55,
            color=[S2 if x == reg_baja else GRAY for x in por_reg.index])
    hbar_labels(ax, por_reg.margen, lambda v: f"{v:.1f}%")
    ax.set_title(f"Margen por región: {reg_baja} queda {brecha:.0f} pp por debajo")
    ax.set_xlim(0, por_reg.margen.max() * 1.2)

    ax = fig.add_axes([0.53, 0.06, 0.435, 0.27])
    panel_texto(ax, "Hallazgos y recomendaciones", (
        f"1. {top} concentra el {metricas['categoria_top_share_pct']:.0f}% de las ventas, pero {mg}\n"
        f"    tiene el mayor margen ({por_cat.margen.max():.0f}%): conviene impulsarla.\n\n"
        f"2. {reg_baja} vende parecido al resto pero con menor margen:\n"
        "    revisar descuentos y costos de envío de esa región.\n\n"
        f"3. Noviembre y diciembre suman el {q4:.0f}% del año: planificar\n"
        "    inventario y campañas desde septiembre."))
    fig.savefig(OUT / "dashboard_ventas.png", facecolor=SURF)
    plt.close(fig)
    print(json.dumps(metricas, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
