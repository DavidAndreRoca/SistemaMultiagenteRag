"""T17: contrato de cada proveedor con su respuesta real grabada.

Las grabaciones salen de ``python -m pruebas.contrato.grabar_modelos`` con la tarea
ficticia ``contrato/v1``. Sin grabación, la prueba de ese proveedor se omite y lo dice:
se graba cuando el equipo carga la clave (T17-01, apartado 7).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.instrucciones import cargador
from app.llm.esquema import validar
from app.llm.modelos import Proveedor
from pruebas.contrato.grabar_modelos import ENTRADA, MODELOS, Clasificacion, _proveedor

GRABACIONES = Path(__file__).parents[1] / "contrato" / "modelos"


def _grabacion(nombre: str) -> dict[str, Any]:
    ruta = GRABACIONES / f"{nombre}.json"
    if not ruta.is_file():
        pytest.skip(f"sin respuesta grabada de {nombre}: python -m pruebas.contrato.grabar_modelos")
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


@pytest.mark.parametrize("nombre", list(MODELOS))
async def test_la_respuesta_grabada_se_interpreta_y_cumple_el_esquema(nombre: str) -> None:
    grabada = _grabacion(nombre)
    assert grabada["estado"] == 200, f"la grabación de {nombre} no fue exitosa"
    assert grabada["modelo"] == MODELOS[nombre]
    cliente = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=grabada["cuerpo"]))
    )
    proveedor = _proveedor(nombre, "clave-ficticia", cliente)
    respuesta = await proveedor.completar(cargador.cargar("contrato", "v1"), ENTRADA, Clasificacion)
    datos = validar(Clasificacion, respuesta.texto, Proveedor(nombre))
    assert datos.seccion == "metodos" and datos.cita == "F1"
    assert respuesta.uso.tokens_entrada and respuesta.uso.tokens_salida
    assert respuesta.version_informada


def test_las_grabaciones_no_contienen_claves() -> None:
    for ruta in GRABACIONES.glob("*.json") if GRABACIONES.is_dir() else []:
        texto = ruta.read_text(encoding="utf-8")
        for prefijo in ("gsk_", "sk-", "AIza", "Bearer "):
            assert prefijo not in texto, ruta.name
