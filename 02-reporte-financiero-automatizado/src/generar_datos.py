"""Genera transacciones contables simuladas de una pyme de servicios (2025, semilla 42).

Salida: data/transacciones_2025.csv  (fecha, tipo, cuenta, monto)
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

INGRESOS = {"Ventas de servicios": 52000, "Ventas de productos": 31000, "Otros ingresos": 3500}
GASTOS = {"Sueldos": 34000, "Alquiler": 6500, "Marketing": 7800, "Software y servicios": 3900,
          "Logistica": 5200, "Impuestos": 6100, "Otros gastos": 2400}


def generar(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for m in range(1, 13):
        crecimiento = 1 + 0.025 * m
        for c, base in INGRESOS.items():
            for _ in range(int(rng.integers(18, 30))):
                monto = base * crecimiento / 24 * rng.uniform(0.6, 1.4)
                rows.append((pd.Timestamp(2025, m, int(rng.integers(1, 28))), "Ingreso", c, round(monto, 2)))
        for c, base in GASTOS.items():
            n = 2 if c in ("Sueldos", "Alquiler", "Impuestos") else int(rng.integers(5, 12))
            campana = 1.35 if (c == "Marketing" and m in (3, 9)) else 1  # campañas de marzo y septiembre
            for _ in range(n):
                monto = base * campana / n * rng.uniform(0.85, 1.15)
                rows.append((pd.Timestamp(2025, m, int(rng.integers(1, 28))), "Gasto", c, round(monto, 2)))
    df = pd.DataFrame(rows, columns=["fecha", "tipo", "cuenta", "monto"]).sort_values("fecha")
    df["fecha"] = df.fecha.dt.date
    return df


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    df = generar()
    df.to_csv(DATA / "transacciones_2025.csv", index=False)
    print(f"{len(df):,} transacciones -> data/transacciones_2025.csv")
