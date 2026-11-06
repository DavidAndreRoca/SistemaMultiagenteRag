"""Fixtures comunes. Ninguna prueba automática llama a un modelo real (apartado 4.7)."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from fastapi import FastAPI

from app.configuracion import Ajustes, cargar_ajustes
from app.main import crear_aplicacion

if sys.platform == "win32":  # psycopg asíncrono no soporta el bucle Proactor de Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

SECRETO_PRUEBAS = "secreto-solo-para-pruebas-automaticas-0123456789"
URL_BD_INALCANZABLE = "postgresql+psycopg://sma:sma@127.0.0.1:1/sma?connect_timeout=2"


def variables_base(**cambios: str) -> dict[str, str]:
    variables = {
        "ENTORNO": "pruebas",
        "URL_BD": URL_BD_INALCANZABLE,
        "SECRETO_SESION": SECRETO_PRUEBAS,
    }
    variables.update(cambios)
    return variables


@pytest.fixture
def ajustes() -> Ajustes:
    return cargar_ajustes(variables_base())


@pytest.fixture
def fabrica_cliente() -> Callable[[FastAPI], httpx.AsyncClient]:
    def _crear(aplicacion: FastAPI) -> httpx.AsyncClient:
        transporte = httpx.ASGITransport(app=aplicacion, raise_app_exceptions=False)
        return httpx.AsyncClient(transport=transporte, base_url="http://prueba")

    return _crear


@pytest.fixture
async def cliente_sin_bd(
    ajustes: Ajustes, fabrica_cliente: Callable[[FastAPI], httpx.AsyncClient]
) -> AsyncIterator[httpx.AsyncClient]:
    """Aplicación con una base inalcanzable a propósito (el motor es perezoso)."""
    aplicacion = crear_aplicacion(ajustes)
    async with aplicacion.router.lifespan_context(aplicacion), fabrica_cliente(aplicacion) as c:
        yield c


@pytest.fixture
def url_bd_real() -> str:
    """URL de PostgreSQL real con pgvector, para pruebas de integración.

    En la integración continua (``CI=true``) su ausencia es un fallo, no un salto.
    """
    url = os.environ.get("URL_BD_PRUEBAS")
    if url:
        return url
    if os.environ.get("CI") == "true":
        pytest.fail("URL_BD_PRUEBAS no está definida en la integración continua")
    pytest.skip("URL_BD_PRUEBAS no definida: levante la base con docker compose (ver README)")
