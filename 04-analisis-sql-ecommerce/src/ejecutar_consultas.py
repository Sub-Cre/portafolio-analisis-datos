"""Ejecuta las consultas de sql/ sobre data/ecommerce.db y arma el dashboard.

Cada consulta se guarda como CSV en outputs/ con el mismo nombre del archivo .sql.
"""
import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from estilo import BLUES, GRAY, S1, S3, SURF, TXT, header, hbar_labels, kpi_row, money

BASE = Path(__file__).resolve().parents[1]
SQL, OUT = BASE / "sql", BASE / "outputs"
ORDEN_RFM = ["Campeones", "Leales", "Nuevos", "Necesitan atención", "En riesgo", "Perdidos"]


def ejecutar() -> dict:
    res = {}
    with sqlite3.connect(BASE / "data" / "ecommerce.db") as con:
        for f in sorted(SQL.glob("*.sql")):
            df = pd.read_sql_query(f.read_text(encoding="utf-8-sig"), con)
            df.to_csv(OUT / f"{f.stem}.csv", index=False)
            res[f.stem] = df
            print(f"{f.name}: {len(df)} filas")
    return res


def main():
    OUT.mkdir(exist_ok=True)
    r = ejecutar()
    kpis = r["01_kpis_mensuales"]
    coh = r["03_cohortes_retencion"]
    rfm = r["04_segmentacion_rfm"].set_index("segmento")
    canal = r["05_recompra_por_canal"].set_index("canal")

    k25 = kpis[kpis.mes.str.startswith("2025")]
    k24 = kpis[kpis.mes.str.startswith("2024")]
    crec = (k25.ingresos.sum() / k24.ingresos.sum() - 1) * 100

    # retención del mes 1 al 3, promedio de las cohortes con al menos 3 meses de historia
    piv = coh.pivot(index="cohorte", columns="meses_desde_inicio", values="retencion_pct")
    madura = piv[piv.index <= "2025-09"]
    ret_m1 = madura[1].mean()
    ret_m3 = madura[3].mean()
    valiosos = rfm.loc[["Campeones", "Leales"]]
    rfm["ingreso_por_cliente"] = (rfm.ingresos / rfm.clientes).round(2)

    m = {
        "ingresos_2025": round(float(k25.ingresos.sum()), 2),
        "crecimiento_vs_2024_pct": round(float(crec), 1),
        "pedidos_2025": int(k25.pedidos.sum()),
        "ticket_promedio_2025": round(float(k25.ingresos.sum() / k25.pedidos.sum()), 2),
        "retencion_mes1_pct": round(float(ret_m1), 1),
        "retencion_mes3_pct": round(float(ret_m3), 1),
        "valiosos_pct_clientes": round(float(valiosos.pct_clientes.sum()), 1),
        "valiosos_pct_ingresos": round(float(valiosos.pct_ingresos.sum()), 1),
        "ingreso_por_cliente_campeones": float(rfm.loc["Campeones", "ingreso_por_cliente"]),
        "ingreso_por_cliente_perdidos": float(rfm.loc["Perdidos", "ingreso_por_cliente"]),
        "en_riesgo_clientes": int(rfm.loc["En riesgo", "clientes"]),
        "canal_mayor_recompra": canal.recompra_pct.idxmax(),
        "canal_mayor_recompra_pct": float(canal.recompra_pct.max()),
        "canal_menor_recompra": canal.recompra_pct.idxmin(),
        "canal_menor_recompra_pct": float(canal.recompra_pct.min()),
        "rfm": rfm[["clientes", "pct_clientes", "pct_ingresos", "ingreso_por_cliente"]].reset_index().to_dict(orient="records"),
    }
    (OUT / "metricas.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")

    fig = plt.figure(figsize=(16, 10), dpi=110)
    header(fig, "E-commerce: Ventas, Retención y Segmentación de Clientes",
           "Base SQLite con 4 tablas. Todo el análisis se hace en SQL (CTEs, funciones de ventana, NTILE); Python solo grafica.")
    kpi_row(fig, [("Ingresos 2025", money(m["ingresos_2025"]), f"+{crec:.0f}% vs 2024"),
                  ("Pedidos 2025", f"{m['pedidos_2025']:,}".replace(",", "."), None),
                  ("Ticket promedio", f"${m['ticket_promedio_2025']:.0f}", None),
                  ("Recompra al mes 1", f"{ret_m1:.0f}%", "de cada cohorte")])

    ax = fig.add_axes([0.035, 0.42, 0.44, 0.29])
    ax.plot(range(len(kpis)), kpis.ingresos, color=S1, lw=2.2)
    ax.set_xticks(range(0, len(kpis), 3), kpis.mes.iloc[::3], fontsize=9.5)
    ax.yaxis.set_major_formatter(FuncFormatter(money))
    ax.set_title("Ingresos mensuales (pedidos completados)")

    ax = fig.add_axes([0.53, 0.42, 0.435, 0.29])
    sub = piv.loc["2025-01":"2025-06", 0:6]
    cmap = LinearSegmentedColormap.from_list("azules", BLUES)
    ax.imshow(sub.values, cmap=cmap, aspect="auto", vmin=0, vmax=40)
    for i in range(sub.shape[0]):
        for j in range(sub.shape[1]):
            v = sub.values[i, j]
            if not np.isnan(v) and j > 0:
                ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=10,
                        color="white" if v > 25 else TXT)
            elif j == 0:
                ax.text(j, i, "100%", ha="center", va="center", fontsize=10, color="white")
    ax.set_xticks(range(sub.shape[1]), [f"M{j}" for j in sub.columns])
    ax.set_yticks(range(sub.shape[0]), sub.index)
    ax.grid(False)
    ax.set_title("Retención por cohorte 2025 (% que vuelve a comprar)")

    ax = fig.add_axes([0.15, 0.06, 0.32, 0.28])
    seg = rfm.reindex(ORDEN_RFM[::-1]).dropna()
    y, h = np.arange(len(seg)), 0.38
    ax.barh(y + h / 2 + 0.01, seg.pct_ingresos, h, color=S1, label="% de ingresos")
    ax.barh(y - h / 2 - 0.01, seg.pct_clientes, h, color=GRAY, label="% de clientes")
    ax.set_yticks(y, seg.index)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="upper right", fontsize=10)
    ax.set_title(f"Segmentos RFM: Campeones + Leales = {m['valiosos_pct_clientes']:.0f}% de clientes "
                 f"y {m['valiosos_pct_ingresos']:.0f}% de ingresos", fontsize=12)

    ax = fig.add_axes([0.62, 0.06, 0.345, 0.28])
    c = canal.sort_values("recompra_pct")
    ax.barh(c.index, c.recompra_pct, color=[S3 if x == m["canal_mayor_recompra"] else GRAY for x in c.index], height=0.55)
    hbar_labels(ax, c.recompra_pct, lambda v: f"{v:.0f}%")
    ax.set_xlim(0, c.recompra_pct.max() * 1.3)
    ax.set_title("% de clientes que recompran, por canal")
    fig.savefig(OUT / "dashboard_ecommerce.png", facecolor=SURF)
    plt.close(fig)
    print(json.dumps({k: v for k, v in m.items() if k != "rfm"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
