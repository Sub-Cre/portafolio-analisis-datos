"""Crea la base SQLite simulada de una tienda online (2024-2025, semilla 21).

Tablas:
  clientes(id_cliente, fecha_alta, ciudad, canal)
  productos(id_producto, nombre, categoria, precio)
  pedidos(id_pedido, id_cliente, fecha, estado)
  detalle_pedido(id_pedido, id_producto, cantidad, precio_unitario)

Salida: data/ecommerce.db
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
FIN = pd.Timestamp("2025-12-31")

CATEGORIAS = {
    "Electrónica": (["Audífonos", "Parlante", "Cargador", "Smartwatch", "Teclado", "Mouse", "Webcam", "Power bank", "Cable USB-C", "Hub USB"], (15, 180)),
    "Hogar": (["Lámpara", "Organizador", "Juego de sábanas", "Cortina", "Set de cocina", "Toallas", "Almohada", "Reloj de pared", "Espejo", "Alfombra"], (10, 90)),
    "Moda": (["Polera", "Jean", "Chaqueta", "Zapatillas", "Gorra", "Mochila", "Cinturón", "Bufanda", "Vestido", "Camisa"], (12, 85)),
    "Belleza": (["Crema facial", "Perfume", "Shampoo", "Protector solar", "Labial", "Sérum", "Acondicionador", "Mascarilla", "Desodorante", "Kit de uñas"], (6, 70)),
    "Deportes": (["Pelota", "Mat de yoga", "Botella", "Pesas", "Cuerda", "Banda elástica", "Guantes", "Short deportivo", "Rodilleras", "Bolso deportivo"], (8, 95)),
    "Mascotas": (["Alimento 3 kg", "Cama", "Juguete", "Correa", "Arena", "Plato", "Snack", "Shampoo para mascotas", "Transportadora", "Rascador"], (5, 60)),
}
# canal: (peso en altas, probabilidad de volver a comprar después de cada pedido)
CANALES = {"Orgánico": (0.30, 0.55), "Redes sociales": (0.30, 0.42), "Google Ads": (0.25, 0.38), "Referidos": (0.15, 0.62)}
CIUDADES = (["Santa Cruz", "La Paz", "Cochabamba", "Sucre", "Tarija", "El Alto"], [0.32, 0.24, 0.2, 0.09, 0.07, 0.08])


def generar(n_clientes: int = 4000, seed: int = 21):
    rng = np.random.default_rng(seed)
    productos = []
    for cat, (items, (lo, hi)) in CATEGORIAS.items():
        for it in items:
            productos.append((len(productos) + 1, it, cat, round(float(rng.uniform(lo, hi)), 2)))
    productos = pd.DataFrame(productos, columns=["id_producto", "nombre", "categoria", "precio"])
    # popularidad desigual: pocos productos venden mucho
    pop = rng.pareto(1.6, len(productos)) + 0.2
    pop /= pop.sum()

    canales = list(CANALES)
    clientes, pedidos, detalle = [], [], []
    dias = (FIN - pd.Timestamp("2024-01-01")).days
    for cid in range(1, n_clientes + 1):
        # más altas a medida que crece el negocio
        alta = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(dias * rng.beta(1.6, 1.0)))
        canal = rng.choice(canales, p=[CANALES[c][0] for c in canales])
        clientes.append((cid, alta.date().isoformat(), rng.choice(CIUDADES[0], p=CIUDADES[1]), canal))
        fecha = alta
        while fecha <= FIN:
            pid = len(pedidos) + 1
            estado = rng.choice(["completado", "cancelado", "devuelto"], p=[0.92, 0.05, 0.03])
            pedidos.append((pid, cid, fecha.date().isoformat(), estado))
            for prod in rng.choice(productos.id_producto, size=int(rng.integers(1, 5)), replace=False, p=pop):
                precio = productos.precio.iloc[prod - 1] * rng.choice([1, 1, 1, 0.9, 0.85])  # descuentos ocasionales
                detalle.append((pid, int(prod), int(rng.integers(1, 4)), round(float(precio), 2)))
            if rng.random() > CANALES[canal][1]:
                break
            fecha = fecha + pd.Timedelta(days=int(rng.exponential(55)) + 7)

    clientes = pd.DataFrame(clientes, columns=["id_cliente", "fecha_alta", "ciudad", "canal"])
    pedidos = pd.DataFrame(pedidos, columns=["id_pedido", "id_cliente", "fecha", "estado"])
    detalle = pd.DataFrame(detalle, columns=["id_pedido", "id_producto", "cantidad", "precio_unitario"])
    return clientes, productos, pedidos, detalle


SCHEMA = """
CREATE TABLE clientes (id_cliente INTEGER PRIMARY KEY, fecha_alta TEXT NOT NULL, ciudad TEXT, canal TEXT);
CREATE TABLE productos (id_producto INTEGER PRIMARY KEY, nombre TEXT, categoria TEXT, precio REAL);
CREATE TABLE pedidos (id_pedido INTEGER PRIMARY KEY, id_cliente INTEGER REFERENCES clientes(id_cliente),
                      fecha TEXT NOT NULL, estado TEXT CHECK (estado IN ('completado','cancelado','devuelto')));
CREATE TABLE detalle_pedido (id_pedido INTEGER REFERENCES pedidos(id_pedido),
                             id_producto INTEGER REFERENCES productos(id_producto),
                             cantidad INTEGER, precio_unitario REAL);
CREATE INDEX ix_pedidos_cliente ON pedidos(id_cliente);
CREATE INDEX ix_detalle_pedido ON detalle_pedido(id_pedido);
"""

if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    db = DATA / "ecommerce.db"
    db.unlink(missing_ok=True)
    tablas = dict(zip(["clientes", "productos", "pedidos", "detalle_pedido"], generar()))
    with sqlite3.connect(db) as con:
        con.executescript(SCHEMA)
        for nombre, df in tablas.items():
            df.to_sql(nombre, con, if_exists="append", index=False)
    print({k: len(v) for k, v in tablas.items()}, "-> data/ecommerce.db")
