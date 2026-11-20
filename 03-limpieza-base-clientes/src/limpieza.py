"""Funciones de limpieza y estandarización de una base de clientes.

Cada función es pura (entrada -> salida) para poder probarla con pytest.
Las que no pueden interpretar un valor devuelven None en lugar de inventarlo.
"""
import re
import unicodedata
from datetime import datetime

import pandas as pd

EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")
TEL_RE = re.compile(r"^\+591 [67]\d{7}$")

CIUDADES = {
    "santa cruz": "Santa Cruz", "sta cruz": "Santa Cruz", "scz": "Santa Cruz", "santa cruz de la sierra": "Santa Cruz",
    "la paz": "La Paz", "lpz": "La Paz",
    "cochabamba": "Cochabamba", "cbba": "Cochabamba",
    "sucre": "Sucre", "suc": "Sucre",
    "el alto": "El Alto",
    "tarija": "Tarija", "tja": "Tarija",
}
CIUDADES_VALIDAS = set(CIUDADES.values())
FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y")
# Palabras que van en minúscula dentro de un nombre propio
MINUSCULAS = {"de", "del", "la", "las", "los", "y"}


def _vacio(valor) -> bool:
    return valor is None or (isinstance(valor, float) and pd.isna(valor)) or str(valor).strip() == ""


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_nombre(valor):
    """'  MARIA  gutierrez ' -> 'Maria Gutierrez'. No agrega tildes que no estaban."""
    if _vacio(valor):
        return None
    palabras = str(valor).split()
    return " ".join(p.lower() if (i > 0 and p.lower() in MINUSCULAS) else p.capitalize() for i, p in enumerate(palabras))


def clave_nombre(valor):
    """Clave para comparar nombres sin importar tildes, mayúsculas ni espacios."""
    n = normalizar_nombre(valor)
    return sin_tildes(n).lower() if n else None


def normalizar_email(valor):
    """Devuelve el correo en minúsculas y sin espacios, o None si no es válido."""
    if _vacio(valor):
        return None
    e = str(valor).strip().lower()
    return e if EMAIL_RE.match(e) else None


def normalizar_telefono(valor):
    """Cualquier formato de celular boliviano -> '+591 7XXXXXXX'. None si no tiene 8 dígitos válidos."""
    if _vacio(valor):
        return None
    dig = re.sub(r"\D", "", str(valor))
    if len(dig) == 11 and dig.startswith("591"):
        dig = dig[3:]
    if len(dig) == 8 and dig[0] in "67":
        return f"+591 {dig}"
    return None


def normalizar_ciudad(valor):
    if _vacio(valor):
        return None
    clave = re.sub(r"[.\s]+", " ", sin_tildes(str(valor)).lower()).strip()
    return CIUDADES.get(clave)


def parse_fecha(valor):
    """Acepta ISO, dd/mm/aaaa, dd.mm.aaaa y dd-mm-aaaa. Devuelve 'AAAA-MM-DD' o None."""
    if _vacio(valor):
        return None
    s = str(valor).strip()
    for fmt in FORMATOS_FECHA:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_monto(valor):
    """'Bs 1.250,50' | '1,250.50' | '1250.50' | '1250,50' -> 1250.5

    Regla: el último separador seguido de exactamente 2 dígitos es el decimal;
    el resto de puntos y comas son separadores de miles.
    """
    if _vacio(valor):
        return None
    s = re.sub(r"[^\d.,-]", "", str(valor))
    m = re.match(r"^(-?[\d.,]*?)[.,](\d{2})$", s)
    if m:
        entero = re.sub(r"[.,]", "", m.group(1)) or "0"
        return float(f"{entero}.{m.group(2)}")
    entero = re.sub(r"[.,]", "", s)
    return float(entero) if entero.lstrip("-").isdigit() else None


def estandarizar(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"id_origen": df.id_origen})
    out["nombre"] = df.nombre.map(normalizar_nombre)
    out["email"] = df.email.map(normalizar_email)
    out["telefono"] = df.telefono.map(normalizar_telefono)
    out["ciudad"] = df.ciudad.map(normalizar_ciudad)
    out["fecha_registro"] = df.fecha_registro.map(parse_fecha)
    out["monto_compras"] = df.monto_compras.map(parse_monto)
    return out


def deduplicar(df: pd.DataFrame):
    """Agrupa registros que comparten email o teléfono (o el mismo nombre + ciudad cuando faltan ambos).

    Usa union-find: si A comparte email con B y B comparte teléfono con C, los tres son el mismo cliente.
    De cada grupo conserva el registro más completo y rellena sus vacíos con los otros.
    Devuelve (clientes_unicos, tabla_de_fusiones).
    """
    padre = list(range(len(df)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[rb] = ra

    df = df.reset_index(drop=True)
    claves = {
        "email": df.email,
        "telefono": df.telefono,
        "nombre_ciudad": pd.Series([f"{clave_nombre(n)}|{c}" if clave_nombre(n) and c else None
                                    for n, c in zip(df.nombre, df.ciudad)]),
    }
    for serie in claves.values():
        visto = {}
        for i, k in serie.items():
            if k is None or pd.isna(k):
                continue
            if k in visto:
                unir(visto[k], i)
            else:
                visto[k] = i

    df["grupo"] = [raiz(i) for i in range(len(df))]
    df["_completo"] = df.drop(columns=["id_origen", "grupo"]).notna().sum(axis=1)
    df = df.sort_values(["grupo", "_completo"], ascending=[True, False])
    unicos = df.groupby("grupo", sort=False).first().reset_index(drop=True)  # first() toma el primer no nulo por columna
    fusiones = (df.groupby("grupo").filter(lambda g: len(g) > 1)
                  .groupby("grupo").agg(registros=("id_origen", "size"), ids=("id_origen", ", ".join))
                  .reset_index(drop=True))
    return unicos.drop(columns="_completo"), fusiones


def calidad(df: pd.DataFrame) -> dict:
    """% de registros cuyo campo ya está en el formato estándar (sirve antes y después de limpiar)."""
    def pct(mask):
        return round(float(mask.mean()) * 100, 1)

    def es_estandar(serie, fn):
        return serie.map(lambda v: not _vacio(v) and fn(v) == v)

    return {
        "Nombre": pct(es_estandar(df.nombre, normalizar_nombre)),
        "Email": pct(es_estandar(df.email, normalizar_email)),
        "Teléfono": pct(df.telefono.map(lambda v: not _vacio(v) and bool(TEL_RE.match(str(v))))),
        "Ciudad": pct(df.ciudad.isin(CIUDADES_VALIDAS)),
        "Fecha": pct(df.fecha_registro.map(lambda v: not _vacio(v) and parse_fecha(v) == v)),
        "Monto": pct(df.monto_compras.map(
            lambda v: (isinstance(v, float) and not pd.isna(v)) or bool(re.match(r"^\d+\.\d{2}$", str(v))))),
    }
