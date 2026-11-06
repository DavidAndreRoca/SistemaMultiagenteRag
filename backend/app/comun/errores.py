"""Formato único de error de la API y manejadores globales (hoja de ruta, 4.4).

Cuerpo de toda respuesta de error: ``{codigo, mensaje, detalle?, incidencia_id}``.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.comun.contexto import obtener_incidencia_id
from app.comun.registro import obtener_registrador

MENSAJE_ERROR_INTERNO = "Ocurrió un error inesperado. Indique el identificador de incidencia."

_CODIGOS_HTTP = {
    401: ("no_autenticado", "Debe iniciar sesión para continuar."),
    403: ("sin_permiso", "No tiene permiso para realizar esta operación."),
    404: ("no_existe", "El recurso solicitado no existe."),
    405: ("metodo_no_permitido", "El método no está permitido en esta ruta."),
    422: ("entrada_invalida", "Los datos enviados no son válidos."),
    429: ("demasiadas_solicitudes", "Demasiadas solicitudes. Intente de nuevo más tarde."),
}


class RespuestaError(BaseModel):
    """Esquema OpenAPI del error común."""

    codigo: str = Field(examples=["entrada_invalida"])
    mensaje: str
    detalle: Any | None = None
    incidencia_id: str | None = None


class ErrorAplicacion(Exception):
    """Error previsto por la aplicación, con código HTTP y mensaje para el usuario."""

    def __init__(
        self,
        codigo: str,
        mensaje: str,
        *,
        estado_http: int = 400,
        detalle: Any | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.estado_http = estado_http
        self.detalle = detalle


def respuesta_error(
    estado_http: int, codigo: str, mensaje: str, detalle: Any | None = None
) -> JSONResponse:
    cuerpo: dict[str, Any] = {"codigo": codigo, "mensaje": mensaje}
    if detalle is not None:
        cuerpo["detalle"] = detalle
    cuerpo["incidencia_id"] = obtener_incidencia_id()
    return JSONResponse(status_code=estado_http, content=cuerpo)


def _detalle_validacion(error: RequestValidationError) -> list[dict[str, str]]:
    # No se devuelve ``input``: puede contener datos del usuario (RNF-02, 4.6).
    return [
        {"campo": ".".join(str(p) for p in e["loc"]), "problema": str(e["msg"])}
        for e in error.errors()
    ]


async def _manejar_error_aplicacion(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, ErrorAplicacion)
    return respuesta_error(error.estado_http, error.codigo, error.mensaje, error.detalle)


async def _manejar_validacion(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    obtener_registrador("validacion").info(
        "entrada invalida", extra={"tipo_evento": "validacion", "errores": len(error.errors())}
    )
    return respuesta_error(
        422, "entrada_invalida", _CODIGOS_HTTP[422][1], _detalle_validacion(error)
    )


async def _manejar_http(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, StarletteHTTPException)
    codigo, mensaje = _CODIGOS_HTTP.get(error.status_code, ("error_http", "No se pudo atender."))
    if error.status_code in (401, 403, 404):
        obtener_registrador("seguridad").warning(
            "acceso rechazado",
            extra={"tipo_evento": "seguridad", "estado_http": error.status_code},
        )
    return respuesta_error(error.status_code, codigo, mensaje)


async def manejar_inesperado(_: Request, error: Exception) -> JSONResponse:
    obtener_registrador("errores").error(
        "error interno",
        exc_info=(type(error), error, error.__traceback__),
        extra={"tipo_evento": "error_interno"},
    )
    return respuesta_error(500, "error_interno", MENSAJE_ERROR_INTERNO)


def registrar_manejadores(aplicacion: FastAPI) -> None:
    aplicacion.add_exception_handler(ErrorAplicacion, _manejar_error_aplicacion)
    aplicacion.add_exception_handler(RequestValidationError, _manejar_validacion)
    aplicacion.add_exception_handler(StarletteHTTPException, _manejar_http)
    aplicacion.add_exception_handler(Exception, manejar_inesperado)
