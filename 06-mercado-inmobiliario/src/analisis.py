"""Análisis del mercado inmobiliario para inversionistas (datos simulados, semilla 42).

Genera data/inmuebles_2025.csv si no existe, y luego:
  - precio por m2 por zona y su evolución mensual
  - velocidad de venta (días publicados) por zona
  - relación precio vs superficie por tipo de inmueble
Salidas: outputs/dashboard_inmobiliario.png, outputs/resumen_zonas.csv, outputs/metricas.json
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from estilo import GRAY, MESES, S1, S2, S3, S4, SURF, TXT, header, hbar_labels, kpi_row, money, panel_texto

BASE = Path(__file__).resolve().parents[1]
DATA, OUT = BASE / "data", BASE / "outputs"
ZONAS = {"Zona Norte": 1450, "Centro": 1250, "Zona Sur": 1050, "Periferia": 780}


def generar(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for z, base in ZONAS.items():
        for m in range(1, 13):
            for _ in range(int(rng.integers(25, 45))):
                tipo = rng.choice(["Departamento", "Casa"], p=[0.62, 0.38])
                m2 = rng.normal(85 if tipo == "Departamento" else 160, 22)
                pm2 = base * (1 + 0.006 * m) * rng.normal(1, 0.09) * (1.08 if tipo == "Departamento" else 1)
                dias = max(8, rng.normal(38 if z in ("Zona Norte", "Centro") else 62, 15))
                rows.append((f"2025-{m:02d}-01", z, tipo, round(m2, 1), round(pm2, 0), round(m2 * pm2, -2), int(dias)))
    return pd.DataFrame(rows, columns=["mes", "zona", "tipo", "m2", "precio_m2", "precio", "dias_en_venta"])


def main():
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    ruta = DATA / "inmuebles_2025.csv"
    if not ruta.exists():
        generar().to_csv(ruta, index=False)
    df = pd.read_csv(ruta, parse_dates=["mes"])

    zonas = df.groupby("zona").agg(publicaciones=("precio", "size"), precio_m2_mediano=("precio_m2", "median"),
                                   precio_mediano=("precio", "median"), dias_promedio=("dias_en_venta", "mean"))
    zonas = zonas.reindex(list(ZONAS)).round(1)
    zonas.to_csv(OUT / "resumen_zonas.csv")

    ene = df[df.mes.dt.month == 1].precio_m2.median()
    dic = df[df.mes.dt.month == 12].precio_m2.median()
    tpm = df.groupby("tipo").precio_m2.median()
    desc = (1 - zonas.loc["Periferia", "precio_m2_mediano"] / zonas.drop("Periferia").precio_m2_mediano.mean()) * 100
    prem = (tpm["Departamento"] / tpm["Casa"] - 1) * 100
    rapidas = zonas[zonas.dias_promedio < 45].index.tolist()

    m = {
        "publicaciones": int(len(df)),
        "precio_m2_mediano": float(df.precio_m2.median()),
        "variacion_anual_pct": round((dic / ene - 1) * 100, 1),
        "ticket_mediano": float(df.precio.median()),
        "dias_promedio": round(float(df.dias_en_venta.mean()), 1),
        "descuento_periferia_pct": round(desc, 1),
        "prima_departamento_pct": round(prem, 1),
        "zonas_venta_rapida": rapidas,
        "dias_periferia": float(zonas.loc["Periferia", "dias_promedio"]),
    }
    (OUT / "metricas.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")

    fig = plt.figure(figsize=(16, 10), dpi=110)
    header(fig, "Análisis del Mercado Inmobiliario 2025",
           f"{len(df):,} propiedades publicadas en 4 zonas. Limpieza en Python y visualización para decisiones de inversión.".replace(",", "."))
    kpi_row(fig, [("Precio mediano por m²", f"${m['precio_m2_mediano']:,.0f}", f"+{m['variacion_anual_pct']:.1f}% en el año".replace(".", ",")),
                  ("Ticket mediano", money(m["ticket_mediano"]), None),
                  ("Días promedio en venta", f"{m['dias_promedio']:.0f}", None),
                  ("Propiedades analizadas", f"{len(df):,}".replace(",", "."), None)])

    ax = fig.add_axes([0.035, 0.40, 0.56, 0.31])
    trend = df.groupby([df.mes.dt.month, "zona"]).precio_m2.median().unstack()
    for z, col in zip(ZONAS, [S1, S2, S3, S4]):
        ax.plot(MESES, trend[z].values, color=col, lw=2.2, label=z)
        ax.text(11.15, trend[z].values[-1], z, color=TXT, va="center", fontsize=10.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_title("Precio mediano por m² y zona")
    ax.legend(frameon=False, ncol=4, loc="upper left")
    ax.set_xlim(-0.3, 13.2)
    ax.set_ylim(trend.min().min() * 0.85, trend.max().max() * 1.12)

    ax = fig.add_axes([0.66, 0.40, 0.305, 0.31])
    d = zonas.dias_promedio.iloc[::-1]
    ax.barh(d.index, d.values, color=[S3 if v < 45 else GRAY for v in d.values], height=0.55)
    hbar_labels(ax, d.values, lambda v: f"{v:.0f} días")
    ax.set_title("Velocidad de venta (días promedio)")
    ax.set_xlim(0, d.max() * 1.3)

    ax = fig.add_axes([0.035, 0.06, 0.44, 0.27])
    samp = df.sample(600, random_state=1)
    for t, col in (("Departamento", S1), ("Casa", S2)):
        s = samp[samp.tipo == t]
        ax.scatter(s.m2, s.precio, s=14, color=col, alpha=0.55, edgecolors="none", label=t)
    ax.yaxis.set_major_formatter(FuncFormatter(money))
    ax.set_xlabel("Superficie (m²)")
    ax.set_title("Precio vs superficie")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="both")

    ax = fig.add_axes([0.53, 0.06, 0.435, 0.27])
    panel_texto(ax, "Recomendaciones para el inversionista", (
        f"1. {' y '.join(rapidas)}: mayor precio por m² y se venden\n"
        "    en menos de 45 días. Menor riesgo de inventario.\n\n"
        f"2. Periferia: precio {desc:.0f}% menor, pero tarda {m['dias_periferia']:.0f} días\n"
        "    en venderse. Opción para comprar y alquilar.\n\n"
        f"3. Los departamentos valen {prem:.0f}% más por m² que las casas."))
    fig.savefig(OUT / "dashboard_inmobiliario.png", facecolor=SURF)
    plt.close(fig)
    print(json.dumps(m, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
