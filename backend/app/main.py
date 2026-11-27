"""Creación de la aplicación FastAPI."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app import __version__
from app.api import (
    borradores,
    caso,
    corpus,
    decisiones,
    estructura,
    evidencia,
    importacion,
    investigador,
    metodologia,
    plan,
    redaccion,
    referencias,
    salud,
    sesion,
    solicitudes,
)
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.comun.errores import RespuestaError, registrar_manejadores
from app.comun.middleware import MiddlewareIncidencia
from app.comun.registro import configurar_registro, obtener_registrador
from app.configuracion import Ajustes, cargar_ajustes
from app.importacion.servicio import purgar
from app.orquestacion.fabrica import ATRIBUTOS


def crear_aplicacion(ajustes: Ajustes | None = None) -> FastAPI:
    """Fábrica de la aplicación.

    Si no se pasan ``ajustes`` se leen y validan del entorno; ante una variable
    obligatoria ausente lanza ``ErrorConfiguracion`` y la aplicación no arranca.
    """
    ajustes = ajustes or cargar_ajustes()
    configurar_registro()

    @asynccontextmanager
    async def ciclo_de_vida(aplicacion: FastAPI) -> AsyncIterator[None]:
        motor = crear_motor(ajustes)
        aplicacion.state.motor = motor
        aplicacion.state.fabrica_sesiones = crear_fabrica_sesiones(motor)
        if ajustes.directorio_archivos:
            # RN-19: ningún artículo O1 sobrevive a una caída a mitad de importación.
            restos = purgar(Path(ajustes.directorio_archivos))
            if restos:
                obtener_registrador().warning(
                    "restos de importacion borrados",
                    extra={"tipo_evento": "arranque", "cantidad": restos},
                )
        obtener_registrador().info(
            "aplicacion iniciada",
            extra={"tipo_evento": "arranque", "entorno": ajustes.entorno.value},
        )
        try:
            yield
        finally:
            importador = aplicacion.state.importador
            if importador is not None:
                importador.cancelar()
            if aplicacion.state.orquestador is not None:  # solo en pruebas (T28)
                aplicacion.state.orquestador.cancelar()
            if aplicacion.state.fabrica_ejecutores is not None:
                await aplicacion.state.fabrica_ejecutores.cerrar()
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
    aplicacion.state.importador = None  # T15: se crea al primer uso, con el indexador
    # T28: los ejecutores de cada tipo se crean al primer uso con una fábrica compartida
    # (``app/orquestacion/en_api.py``); las pruebas los sustituyen.
    for atributo in ATRIBUTOS.values():
        setattr(aplicacion.state, atributo, None)
    aplicacion.state.fabrica_ejecutores = None
    aplicacion.state.orquestador = None  # solo con EJECUCION_EN_PROCESO (pruebas)
    aplicacion.state.candado_corpus = asyncio.Lock()
    aplicacion.state.servicio_borradores = None  # se crea al primer uso (DIRECTORIO_ARCHIVOS)
    registrar_manejadores(aplicacion)
    aplicacion.add_middleware(MiddlewareIncidencia, es_produccion=ajustes.es_produccion)
    modulos = (salud, sesion, caso, borradores, investigador, corpus, importacion)
    for modulo in (
        *modulos,
        evidencia,
        referencias,
        estructura,
        redaccion,
        metodologia,
        plan,
        solicitudes,
        decisiones,
    ):
        aplicacion.include_router(modulo.router)
    return aplicacion
