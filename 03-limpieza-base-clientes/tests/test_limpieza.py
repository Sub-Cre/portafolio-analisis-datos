import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from limpieza import (deduplicar, normalizar_ciudad, normalizar_email, normalizar_nombre,  # noqa: E402
                      normalizar_telefono, parse_fecha, parse_monto)


@pytest.mark.parametrize("entrada,esperado", [
    ("+591 71234567", "+591 71234567"),
    ("71234567", "+591 71234567"),
    ("591-712-34567", "+591 71234567"),
    ("(591) 7123 4567", "+591 71234567"),
    ("7123-4567", "+591 71234567"),
    ("+59161234567", "+591 61234567"),
    ("1234567", None),
    ("", None),
    (None, None),
])
def test_telefono(entrada, esperado):
    assert normalizar_telefono(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    (" Ana.Lopez12@Gmail.com ", "ana.lopez12@gmail.com"),
    ("ana.lopez12gmail.com", None),
    ("ana.lopez12@gmail", None),
    ("", None),
])
def test_email(entrada, esperado):
    assert normalizar_email(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    ("  MARIA  gutierrez ", "Maria Gutierrez"),
    ("josé DE la cruz", "José de la Cruz"),
    (None, None),
])
def test_nombre(entrada, esperado):
    assert normalizar_nombre(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    ("SCZ", "Santa Cruz"), ("Sta. Cruz", "Santa Cruz"), ("santa cruz de la sierra", "Santa Cruz"),
    ("cbba", "Cochabamba"), ("Cbba.", "Cochabamba"), ("la paz ", "La Paz"), ("Lima", None),
])
def test_ciudad(entrada, esperado):
    assert normalizar_ciudad(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    ("2024-03-05", "2024-03-05"), ("05/03/2024", "2024-03-05"), ("05.03.2024", "2024-03-05"),
    ("pendiente", None), ("31/02/2024", None),
])
def test_fecha(entrada, esperado):
    assert parse_fecha(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    ("1250.50", 1250.5), ("1,250.50", 1250.5), ("1.250,50", 1250.5), ("Bs 1.250,50", 1250.5),
    ("1250,50", 1250.5), ("12.345.678,90", 12345678.9), ("850", 850.0), ("", None),
])
def test_monto(entrada, esperado):
    assert parse_monto(entrada) == esperado


def test_deduplicar_por_email_y_telefono_encadenados():
    df = pd.DataFrame({
        "id_origen": ["A", "B", "C", "D"],
        "nombre": ["Ana Lopez", "Ana Lopez", "Ana López", "Luis Rojas"],
        "email": ["ana@x.com", "ana@x.com", None, "luis@x.com"],
        "telefono": [None, "+591 71234567", "+591 71234567", "+591 79999999"],
        "ciudad": ["Sucre", "Sucre", "Sucre", "La Paz"],
        "fecha_registro": ["2024-01-01", None, None, "2024-02-01"],
        "monto_compras": [100.0, None, None, 50.0],
    })
    unicos, fusiones = deduplicar(df)
    assert len(unicos) == 2
    ana = unicos[unicos.email == "ana@x.com"].iloc[0]
    # Los vacíos del registro más completo se rellenan con los duplicados
    assert ana.telefono == "+591 71234567"
    assert ana.fecha_registro == "2024-01-01"
    assert fusiones.registros.tolist() == [3]
