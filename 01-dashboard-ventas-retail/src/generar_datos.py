"""Genera el dataset simulado de ventas retail 2025 (reproducible, semilla 42).

Salida: data/ventas_retail_2025.csv
Columnas: fecha, categoria, region, unidades, venta, ganancia
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def generar(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # categoría: (precio medio, margen base)
    cats = {"Tecnologia": (420, 0.22), "Hogar": (160, 0.31), "Moda": (75, 0.45), "Deportes": (110, 0.28)}
    regiones = ["Norte", "Centro", "Sur", "Occidente"]
    rows = []
    for d in pd.date_range("2025-01-01", "2025-12-31", freq="D"):
        temporada = 1 + 0.25 * np.sin((d.month - 3) / 12 * 2 * np.pi) + (0.45 if d.month in (11, 12) else 0)
        for c, (precio, margen) in cats.items():
            for r in regiones:
                for _ in range(rng.poisson(3.2 * temporada * (1.3 if r == "Centro" else 1))):
                    p = precio * rng.uniform(0.6, 1.5)
                    q = int(rng.integers(1, 4))
                    # Occidente aplica más descuentos y envíos más caros -> menor margen
                    m = margen + rng.normal(0, 0.04) - (0.06 if r == "Occidente" else 0)
                    rows.append((d.date(), c, r, q, round(p * q, 2), round(p * q * m, 2)))
    return pd.DataFrame(rows, columns=["fecha", "categoria", "region", "unidades", "venta", "ganancia"])


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    df = generar()
    df.to_csv(DATA / "ventas_retail_2025.csv", index=False)
    print(f"{len(df):,} transacciones -> data/ventas_retail_2025.csv")
