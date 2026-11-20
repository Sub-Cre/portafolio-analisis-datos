"""Pipeline de limpieza: data/clientes_crudo.csv -> base limpia + reporte de calidad.

Uso:
    python src/pipeline.py
    python src/pipeline.py --entrada otra_base.csv

Salidas en outputs/:
  - clientes_limpio.csv            base final, un registro por cliente
  - reporte_limpieza.xlsx          hojas: Resumen, Clientes limpios, Duplicados fusionados, A revisar
  - calidad_antes_despues.png      gráfico de calidad por campo
  - metricas.json
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from estilo import S1, S2, SURF, TXT, header, kpi_row, panel_texto
from limpieza import calidad, deduplicar, estandarizar

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entrada", type=Path, default=BASE / "data" / "clientes_crudo.csv")
    a = p.parse_args()
    OUT.mkdir(exist_ok=True)

    crudo = pd.read_csv(a.entrada, dtype=str)
    q_antes = calidad(crudo)

    std = estandarizar(crudo)
    limpio, fusiones = deduplicar(std)
    q_despues = calidad(limpio)

    revisar = limpio[limpio.email.isna() & limpio.telefono.isna() | limpio.fecha_registro.isna()].copy()
    revisar["motivo"] = np.where(limpio.loc[revisar.index, "fecha_registro"].isna(),
                                 "Fecha de registro ilegible", "Sin email ni teléfono válidos")
    limpio = limpio.sort_values("nombre").reset_index(drop=True)
    limpio.to_csv(OUT / "clientes_limpio.csv", index=False)

    resumen = pd.DataFrame({"Campo": list(q_antes), "% estándar antes": list(q_antes.values()),
                            "% estándar después": list(q_despues.values())})
    with pd.ExcelWriter(OUT / "reporte_limpieza.xlsx", engine="openpyxl") as w:
        resumen.to_excel(w, sheet_name="Resumen", index=False)
        limpio.to_excel(w, sheet_name="Clientes limpios", index=False)
        fusiones.to_excel(w, sheet_name="Duplicados fusionados", index=False)
        revisar.to_excel(w, sheet_name="A revisar", index=False)

    metricas = {
        "registros_entrada": int(len(crudo)),
        "clientes_unicos": int(len(limpio)),
        "duplicados_fusionados": int(len(crudo) - len(limpio)),
        "grupos_con_duplicados": int(len(fusiones)),
        "registros_a_revisar": int(len(revisar)),
        "calidad_antes_pct": round(float(np.mean(list(q_antes.values()))), 1),
        "calidad_despues_pct": round(float(np.mean(list(q_despues.values()))), 1),
        "calidad_por_campo": {k: {"antes": q_antes[k], "despues": q_despues[k]} for k in q_antes},
    }
    (OUT / "metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")

    fig = plt.figure(figsize=(16, 10), dpi=110)
    header(fig, "Limpieza y Estandarización de Base de Clientes",
           "Base exportada de un CRM con formatos mezclados y duplicados. Pipeline en Python/Pandas con pruebas automáticas.")
    kpi_row(fig, [("Registros de entrada", f"{len(crudo):,}".replace(",", "."), None),
                  ("Clientes únicos", f"{len(limpio):,}".replace(",", "."), None),
                  ("Duplicados fusionados", f"{metricas['duplicados_fusionados']}", None),
                  ("Calidad promedio", f"{metricas['calidad_despues_pct']:.0f}%", f"antes {metricas['calidad_antes_pct']:.0f}%")])

    ax = fig.add_axes([0.095, 0.08, 0.50, 0.62])
    campos = list(q_antes)[::-1]
    y, h = np.arange(len(campos)), 0.36
    a_ = [q_antes[c] for c in campos]
    d_ = [q_despues[c] for c in campos]
    ax.barh(y + h / 2 + 0.01, d_, h, color=S1, label="Después")
    ax.barh(y - h / 2 - 0.01, a_, h, color=S2, label="Antes")
    for i in range(len(campos)):
        ax.text(d_[i], y[i] + h / 2, f"  {d_[i]:.0f}%", va="center", fontsize=10.5, color=TXT)
        ax.text(a_[i], y[i] - h / 2, f"  {a_[i]:.0f}%", va="center", fontsize=10.5, color=TXT)
    ax.set_yticks(y, campos)
    ax.set_xlim(0, 115)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("% de registros con el campo en formato estándar, por campo")

    ax = fig.add_axes([0.62, 0.08, 0.345, 0.62])
    panel_texto(ax, "Qué hace el pipeline", (
        "1. Nombres: espacios y mayúsculas consistentes.\n\n"
        "2. Correos: minúsculas, sin espacios y validados;\n    los inválidos quedan vacíos, no se inventan.\n\n"
        "3. Teléfonos: 6 formatos distintos -> +591 7XXXXXXX.\n\n"
        "4. Ciudades: 'SCZ', 'Sta. Cruz', 'santa cruz'\n    -> Santa Cruz.\n\n"
        "5. Fechas y montos: formatos latinos y anglosajones\n    -> AAAA-MM-DD y número decimal.\n\n"
        "6. Duplicados: agrupa por email, teléfono o\n    nombre + ciudad y conserva el más completo.\n\n"
        f"7. {len(revisar)} registros sin forma de contacto o con\n    fecha ilegible van a una hoja 'A revisar'."), size=11.5)
    fig.savefig(OUT / "calidad_antes_despues.png", facecolor=SURF)
    plt.close(fig)
    print(json.dumps(metricas, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
