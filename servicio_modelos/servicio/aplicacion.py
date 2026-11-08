"""Aplicación HTTP mínima: ``/embeber``, ``/reordenar`` y ``/salud`` (T08).

* Cola con límite de concurrencia: como mucho ``MAX_CONCURRENCIA`` inferencias a la vez;
  las demás esperan hasta ``ESPERA_MAXIMA_S`` y luego reciben 503 ``servicio_ocupado``.
* Límites de entrada: número de textos y tokens por texto. Nada se trunca en silencio.
* Cada respuesta lleva el identificador y la revisión exacta del modelo (RNF-21).
* El registro solo guarda metadatos (ruta, cantidad, duración), nunca los textos.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from servicio import __version__
from servicio.ajustes import AjustesServicio, cargar_ajustes
from servicio.catalogo import CATALOGO, DIMENSION_EMBEDDINGS, ModeloFijado, problemas
from servicio.esquemas import (
    ModeloCargado,
    RespuestaEmbeber,
    RespuestaError,
    RespuestaReordenar,
    RespuestaSalud,
    SolicitudEmbeber,
    SolicitudReordenar,
)
from servicio.memoria import memoria_actual
from servicio.motores import MotorEmbeddings, MotorReordenador
from servicio.registro import configurar_registro

T = TypeVar("T")
registro = configurar_registro()


class ErrorServicio(Exception):
    def __init__(self, estado_http: int, codigo: str, mensaje: str, detalle: Any = None) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle


@dataclass
class _Estado:
    ajustes: AjustesServicio
    embeddings: MotorEmbeddings
    reordenador: MotorReordenador
    turnos: asyncio.Semaphore


def _respuesta_error(estado_http: int, codigo: str, mensaje: str, detalle: Any = None) -> Any:
    cuerpo = RespuestaError(
        codigo=codigo, mensaje=mensaje, detalle=detalle, incidencia_id=uuid.uuid4().hex
    )
    return JSONResponse(status_code=estado_http, content=cuerpo.model_dump(exclude_none=True))


def _cargar_motores_reales(ajustes: AjustesServicio) -> tuple[MotorEmbeddings, MotorReordenador]:
    faltan = [p for modelo in CATALOGO for p in problemas(modelo, ajustes.directorio_modelos)]
    if faltan:
        raise RuntimeError(
            "Faltan los pesos de los modelos en "
            f"{ajustes.directorio_modelos} ({'; '.join(faltan)}). "
            "Descárguelos con: python -m servicio.descargar"
        )
    from servicio.motor_transformers import cargar_motores

    return cargar_motores(ajustes)


def crear_aplicacion(
    ajustes: AjustesServicio | None = None,
    motores: tuple[MotorEmbeddings, MotorReordenador] | None = None,
) -> FastAPI:
    """``motores`` permite inyectar motores en pruebas; por defecto se cargan los reales."""
    ajustes = ajustes or cargar_ajustes()

    @asynccontextmanager
    async def ciclo_de_vida(aplicacion: FastAPI) -> AsyncIterator[None]:
        inicio = time.perf_counter()
        embeddings, reordenador = motores or _cargar_motores_reales(ajustes)
        aplicacion.state.servicio = _Estado(
            ajustes, embeddings, reordenador, asyncio.Semaphore(ajustes.max_concurrencia)
        )
        registro.info(
            "modelos cargados",
            extra={"duracion_ms": round((time.perf_counter() - inicio) * 1000)},
        )
        yield

    aplicacion = FastAPI(
        title="Servicio de modelos",
        version=__version__,
        lifespan=ciclo_de_vida,
        responses={
            422: {"model": RespuestaError},
            503: {"model": RespuestaError},
        },
    )

    @aplicacion.exception_handler(ErrorServicio)
    async def _error_servicio(_: Request, error: Exception) -> Any:
        assert isinstance(error, ErrorServicio)
        registro.info(
            "solicitud rechazada", extra={"codigo": error.codigo, "estado_http": error.estado_http}
        )
        return _respuesta_error(error.estado_http, error.codigo, error.mensaje, error.detalle)

    @aplicacion.exception_handler(RequestValidationError)
    async def _error_validacion(_: Request, error: Exception) -> Any:
        assert isinstance(error, RequestValidationError)
        detalle = [  # sin ``input``: podría contener texto del corpus o del estudiante
            {"campo": ".".join(str(p) for p in e["loc"]), "problema": str(e["msg"])}
            for e in error.errors()
        ]
        return _respuesta_error(
            422, "entrada_invalida", "Los datos enviados no son válidos.", detalle
        )

    def _estado(peticion: Request) -> _Estado:
        estado: _Estado = peticion.app.state.servicio
        return estado

    def _validar_textos(estado: _Estado, textos: Sequence[str]) -> None:
        if len(textos) > estado.ajustes.max_textos:
            raise ErrorServicio(
                422,
                "demasiados_textos",
                f"Se admiten como máximo {estado.ajustes.max_textos} textos por solicitud.",
                {"max_textos": estado.ajustes.max_textos, "recibidos": len(textos)},
            )
        vacios = [i for i, t in enumerate(textos) if not t.strip()]
        if vacios:
            raise ErrorServicio(422, "texto_vacio", "Hay textos vacíos.", {"indices": vacios})
        largos = [i for i, t in enumerate(textos) if len(t) > estado.ajustes.max_caracteres]
        _rechazar_largos(estado, largos)

    def _rechazar_largos(estado: _Estado, indices: list[int]) -> None:
        if indices:
            raise ErrorServicio(
                422,
                "texto_demasiado_largo",
                f"Hay textos de más de {estado.ajustes.max_tokens} tokens; divídalos antes.",
                {"indices": indices, "max_tokens": estado.ajustes.max_tokens},
            )

    async def _en_turno(estado: _Estado, ruta: str, n: int, trabajo: Callable[[], T]) -> T:
        llegada = time.perf_counter()
        try:
            await asyncio.wait_for(estado.turnos.acquire(), timeout=estado.ajustes.espera_maxima_s)
        except TimeoutError:
            raise ErrorServicio(
                503,
                "servicio_ocupado",
                "El servicio de modelos está ocupado. Intente de nuevo en unos segundos.",
            ) from None
        inicio = time.perf_counter()
        try:
            resultado = await asyncio.to_thread(trabajo)
        finally:
            estado.turnos.release()
        registro.info(
            "inferencia",
            extra={
                "ruta": ruta,
                "n_textos": n,
                "espera_ms": round((inicio - llegada) * 1000),
                "duracion_ms": round((time.perf_counter() - inicio) * 1000),
            },
        )
        return resultado

    def _identidad(modelo: ModeloFijado) -> dict[str, str]:
        return {"modelo": modelo.repositorio, "revision": modelo.revision}

    @aplicacion.post("/embeber", response_model=RespuestaEmbeber, summary="Textos a vectores")
    async def embeber(datos: SolicitudEmbeber, peticion: Request) -> RespuestaEmbeber:
        estado = _estado(peticion)
        _validar_textos(estado, datos.textos)
        motor = estado.embeddings

        def trabajo() -> list[list[float]]:
            tokens = motor.contar_tokens(datos.textos)
            _rechazar_largos(
                estado, [i for i, n in enumerate(tokens) if n > estado.ajustes.max_tokens]
            )
            return motor.embeber(datos.textos)

        vectores = await _en_turno(estado, "/embeber", len(datos.textos), trabajo)
        return RespuestaEmbeber(
            **_identidad(motor.modelo), dimension=DIMENSION_EMBEDDINGS, vectores=vectores
        )

    @aplicacion.post(
        "/reordenar", response_model=RespuestaReordenar, summary="Consulta y textos a puntajes"
    )
    async def reordenar(datos: SolicitudReordenar, peticion: Request) -> RespuestaReordenar:
        estado = _estado(peticion)
        if not datos.consulta.strip():
            raise ErrorServicio(422, "consulta_vacia", "La consulta está vacía.")
        _validar_textos(estado, datos.textos)
        motor = estado.reordenador

        def trabajo() -> list[float]:
            tokens = motor.contar_tokens(datos.consulta, datos.textos)
            _rechazar_largos(
                estado, [i for i, n in enumerate(tokens) if n > estado.ajustes.max_tokens]
            )
            return motor.reordenar(datos.consulta, datos.textos)

        puntajes = await _en_turno(estado, "/reordenar", len(datos.textos), trabajo)
        return RespuestaReordenar(**_identidad(motor.modelo), puntajes=puntajes)

    @aplicacion.get("/salud", response_model=RespuestaSalud, summary="Estado, modelos y memoria")
    async def salud(peticion: Request) -> RespuestaSalud:
        estado = _estado(peticion)
        return RespuestaSalud(
            estado="ok",
            version=__version__,
            modelos=[
                ModeloCargado(
                    **_identidad(m.modelo), tipo=m.modelo.tipo.value, licencia=m.modelo.licencia
                )
                for m in (estado.embeddings, estado.reordenador)
            ],
            memoria=memoria_actual(),
            max_textos=estado.ajustes.max_textos,
            max_tokens=estado.ajustes.max_tokens,
            tamano_lote=estado.ajustes.tamano_lote,
            max_concurrencia=estado.ajustes.max_concurrencia,
        )

    return aplicacion
