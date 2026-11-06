"""Integración de /salud con PostgreSQL real y pgvector."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import __version__
from app.configuracion import cargar_ajustes
from app.main import crear_aplicacion
from pruebas.conftest import variables_base

pytestmark = pytest.mark.integracion


async def test_salud_con_base_conectada_y_extension_vector(
    url_bd_real: str, fabrica_cliente: Callable[[FastAPI], httpx.AsyncClient]
) -> None:
    aplicacion = crear_aplicacion(cargar_ajustes(variables_base(URL_BD=url_bd_real)))
    async with aplicacion.router.lifespan_context(aplicacion), fabrica_cliente(aplicacion) as c:
        respuesta = await c.get("/salud")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["base_de_datos"] is True
    assert cuerpo["version"] == __version__
    assert cuerpo["extension_vector"]


async def test_la_extension_vector_opera_con_1024_dimensiones(url_bd_real: str) -> None:
    """Base de T10: vector(1024) y distancia coseno funcionan en esta imagen."""
    motor = create_async_engine(url_bd_real)
    try:
        async with motor.connect() as conexion:
            valor = (
                await conexion.execute(
                    text(
                        "SELECT (array_fill(1, ARRAY[1024])::vector(1024)"
                        " <=> array_fill(1, ARRAY[1024])::vector(1024))::float"
                    )
                )
            ).scalar_one()
    finally:
        await motor.dispose()
    assert valor == pytest.approx(0.0, abs=1e-6)
