"""Genera la base simulada de clientes de un servicio por suscripción (internet/TV), semilla 5.

La probabilidad de abandono (churn) depende de variables con efectos conocidos, para poder
verificar que el modelo recupera los factores correctos.

Salida: data/clientes_suscripcion.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def generar(n: int = 7000, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    contrato = rng.choice(["Mensual", "Anual", "Bianual"], n, p=[0.55, 0.30, 0.15])
    plan = rng.choice(["Básico", "Estándar", "Premium"], n, p=[0.40, 0.40, 0.20])
    base_cargo = {"Básico": 35, "Estándar": 60, "Premium": 95}
    cargo = np.array([base_cargo[p] for p in plan]) * rng.uniform(0.85, 1.2, n)
    antig = np.where(contrato == "Mensual", rng.integers(1, 40, n), rng.integers(6, 73, n))
    pago = rng.choice(["Débito automático", "Transferencia", "Efectivo"], n, p=[0.40, 0.35, 0.25])
    tickets = rng.poisson(np.where(plan == "Premium", 0.8, 1.2))
    atrasos = rng.poisson(np.where(pago == "Efectivo", 1.1, 0.4))
    usa_app = rng.random(n) < 0.55
    region = rng.choice(["Santa Cruz", "La Paz", "Cochabamba", "Sucre", "Tarija"], n, p=[0.32, 0.28, 0.22, 0.10, 0.08])

    logit = (-1.0
             + 1.5 * (contrato == "Mensual") - 0.8 * (contrato == "Bianual")
             - 0.035 * antig
             + 0.012 * (cargo - 60)
             + 0.38 * tickets
             + 0.45 * atrasos
             - 0.65 * usa_app
             + 0.40 * (pago == "Efectivo") - 0.30 * (pago == "Débito automático")
             + rng.normal(0, 0.6, n))
    churn = rng.random(n) < 1 / (1 + np.exp(-logit))

    return pd.DataFrame({
        "id_cliente": [f"S{50000 + i}" for i in range(n)],
        "region": region,
        "tipo_contrato": contrato,
        "plan": plan,
        "antiguedad_meses": antig,
        "cargo_mensual": cargo.round(2),
        "metodo_pago": pago,
        "tickets_soporte_90d": tickets,
        "pagos_atrasados_12m": atrasos,
        "usa_app": usa_app.astype(int),
        "abandono": churn.astype(int),
    })


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    df = generar()
    df.to_csv(DATA / "clientes_suscripcion.csv", index=False)
    print(f"{len(df):,} clientes, tasa de abandono {df.abandono.mean():.1%} -> data/clientes_suscripcion.csv")
