"""CreaciÃ³n de la aplicaciÃ³n FastAPI."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import borradores, caso, corpus, investigador, salud, sesion
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.comun.errores import RespuestaError, registrar_manejadores
from app.comun.middleware import MiddlewareIncidencia
from app.comun.registro import configurar_registro, obtener_registrador
from app.configuracion import Ajustes, cargar_ajustes


def crear_aplicacion(ajustes: Ajustes | None = None) -> FastAPI:
    """FÃ¡brica de la aplicaciÃ³n.

    Si no se pasan ``ajustes`` se leen y validan del entorno; ante una variable
    obligatoria ausente lanza ``ErrorConfiguracion`` y la aplicaciÃ³n no arranca.
    """
    ajustes = ajustes or cargar_ajustes()
    configurar_registro()

    @asynccontextmanager
    async def ciclo_de_vida(aplicacion: FastAPI) -> AsyncIterator[None]:
        motor = crear_motor(ajustes)
        aplicacion.state.motor = motor
        aplicacion.state.fabrica_sesiones = crear_fabrica_sesiones(motor)
        obtener_registrador().info(
            "aplicacion iniciada",
            extra={"tipo_evento": "arranque", "entorno": ajustes.entorno.value},
        )
        try:
            yield
        finally:
            await motor.dispose()
            obtener_registrador().info("aplicacion detenida", extra={"tipo_evento": "apagado"})

    aplicacion = FastAPI(
        title="Sistema multiagente con RAG",
        version=__version__,
        lifespan=ciclo_de_vida,
        docs_url="/docs" if ajustes.documentacion_habilitada else None,
        redoc_url=None,
        openapi_url="/openapi.json" if ajustes.documentacion_habilitada else None,
        responses={
            401: {"model": RespuestaError},
            403: {"model": RespuestaError},
            404: {"model": RespuestaError},
            422: {"model": RespuestaError},
            500: {"model": RespuestaError},
        },
    )
    aplicacion.state.ajustes = ajustes
    # El indexador del corpus (Docling) se crea al primer uso; las pruebas lo sustituyen.
    aplicacion.state.indexador = None
    aplicacion.state.embebedor = None
    aplicacion.state.candado_corpus = asyncio.Lock()
    aplicacion.state.servicio_borradores = None  # se crea al primer uso (DIRECTORIO_ARCHIVOS)
    registrar_manejadores(aplicacion)
    aplicacion.add_middleware(MiddlewareIncidencia, es_produccion=ajustes.es_produccion)
    for modulo in (salud, sesion, caso, borradores, investigador, corpus):
        aplicacion.include_router(modulo.router)
    return aplicacion
