"""Genera una base de clientes "sucia" como las que llegan de un CRM o de formularios web.

Problemas introducidos a propósito (reproducibles, semilla 7):
  - Nombres con mayúsculas/minúsculas mezcladas, espacios dobles y sin tildes
  - Correos en mayúsculas, con espacios o inválidos; algunos vacíos
  - Teléfonos en 6 formatos distintos
  - Ciudades escritas de 3 a 5 maneras
  - Fechas en 3 formatos y textos como "pendiente"
  - Montos con separadores latinos y anglosajones, con o sin "Bs"
  - ~12% de registros duplicados con variaciones

Salida: data/clientes_crudo.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

NOMBRES = ["María", "José", "Juan", "Ana", "Luis", "Carla", "Jorge", "Lucía", "Diego", "Sofía", "Andrés",
           "Valeria", "Miguel", "Camila", "Fernando", "Gabriela", "Ricardo", "Daniela", "Óscar", "Paola",
           "Sebastián", "Natalia", "Héctor", "Mónica", "Raúl", "Verónica", "Iván", "Claudia", "Rubén", "Elena"]
APELLIDOS = ["Gutiérrez", "Fernández", "Rodríguez", "López", "Martínez", "Pérez", "Gómez", "Sánchez",
             "Ramírez", "Torres", "Flores", "Rivera", "Vargas", "Rojas", "Castro", "Mendoza", "Quispe",
             "Mamani", "Choque", "Ortiz", "Suárez", "Molina", "Arce", "Paredes", "Salazar", "Núñez"]
CIUDADES = {
    "Santa Cruz": ["Santa Cruz", "santa cruz", "Sta. Cruz", "SCZ", "Santa Cruz de la Sierra"],
    "La Paz": ["La Paz", "LA PAZ", "LPZ", "la paz "],
    "Cochabamba": ["Cochabamba", "cbba", "Cbba.", "COCHABAMBA"],
    "Sucre": ["Sucre", "sucre", "SUC"],
    "El Alto": ["El Alto", "el alto", "EL ALTO"],
    "Tarija": ["Tarija", "TJA", "tarija"],
}
PESOS_CIUDAD = [0.30, 0.24, 0.20, 0.10, 0.10, 0.06]
DOMINIOS = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "empresa.com.bo"]
SIN_TILDE = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")


def _ensuciar_nombre(nombre, rng):
    r = rng.random()
    if r < 0.25:
        nombre = nombre.upper()
    elif r < 0.45:
        nombre = nombre.lower()
    if rng.random() < 0.30:
        nombre = nombre.translate(SIN_TILDE)
    if rng.random() < 0.25:
        nombre = nombre.replace(" ", "  ", 1)
    if rng.random() < 0.20:
        nombre = f" {nombre} "
    return nombre


def _ensuciar_email(email, rng):
    r = rng.random()
    if r < 0.06:
        return ""
    if r < 0.10:
        return email.replace("@", "", 1)  # sin arroba -> inválido
    if r < 0.13:
        return email.rsplit(".", 1)[0]  # sin dominio de nivel superior -> inválido
    if r < 0.30:
        return email.upper()
    if r < 0.40:
        return f" {email} "
    return email


def _formatear_tel(num, rng):
    a, b = num[:4], num[4:]
    formatos = [f"+591 {num}", num, f"591-{num[:3]}-{num[3:]}", f"(591) {a} {b}", f"{a}-{b}", f"+591{num}"]
    if rng.random() < 0.05:
        return ""
    return formatos[int(rng.integers(0, len(formatos)))]


def _formatear_fecha(fecha, rng):
    r = rng.random()
    if r < 0.03:
        return "pendiente"
    if r < 0.45:
        return fecha.strftime("%Y-%m-%d")
    if r < 0.80:
        return fecha.strftime("%d/%m/%Y")
    return fecha.strftime("%d.%m.%Y")


def _formatear_monto(monto, rng):
    entero, dec = f"{monto:.2f}".split(".")
    miles = f"{int(entero):,}"
    r = rng.random()
    if r < 0.30:
        return f"{entero}.{dec}"
    if r < 0.55:
        return f"{miles}.{dec}"  # 1,250.50
    if r < 0.80:
        return f"{miles.replace(',', '.')},{dec}"  # 1.250,50
    return f"Bs {miles.replace(',', '.')},{dec}"


def generar(n_clientes: int = 1800, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = []
    usados = set()
    for i in range(n_clientes):
        while True:
            nom = f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}"
            if nom not in usados:
                usados.add(nom)
                break
        partes = nom.translate(SIN_TILDE).lower().split()
        email = f"{partes[0]}.{partes[1]}{int(rng.integers(1, 99))}@{rng.choice(DOMINIOS)}"
        tel = f"{rng.choice(['6', '7'])}{int(rng.integers(0, 10**7)):07d}"
        ciudad = rng.choice(list(CIUDADES), p=PESOS_CIUDAD)
        fecha = pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(rng.integers(0, 1400)))
        monto = float(np.round(rng.lognormal(6.6, 0.8), 2))
        base.append((nom, email, tel, ciudad, fecha, monto))

    def fila(rec):
        nom, email, tel, ciudad, fecha, monto = rec
        return {
            "nombre": _ensuciar_nombre(nom, rng),
            "email": _ensuciar_email(email, rng),
            "telefono": _formatear_tel(tel, rng),
            "ciudad": rng.choice(CIUDADES[ciudad]),
            "fecha_registro": _formatear_fecha(fecha, rng),
            "monto_compras": _formatear_monto(monto, rng),
        }

    rows = [fila(r) for r in base]
    # duplicados: el mismo cliente cargado otra vez con otro formato
    for idx in rng.choice(n_clientes, size=int(n_clientes * 0.12), replace=False):
        rows.append(fila(base[idx]))
    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    df.insert(0, "id_origen", [f"C{10000 + i}" for i in range(len(df))])
    return df


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    df = generar()
    df.to_csv(DATA / "clientes_crudo.csv", index=False)
    print(f"{len(df):,} registros -> data/clientes_crudo.csv")
