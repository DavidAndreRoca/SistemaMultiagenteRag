"""Ruta de salud: conexión a la base, extensión vectorial y versión de la aplicación."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import __version__
from app.comun.registro import obtener_registrador
from app.seguridad.dependencias import Unidad

router = APIRouter(tags=["salud"])


class EstadoSalud(BaseModel):
    estado: Literal["ok", "degradado"]
    version: str
    base_de_datos: bool
    extension_vector: str | None
    """Versión de la extensión ``vector`` si está instalada; ``None`` si no lo está."""


@router.get(
    "/salud",
    response_model=EstadoSalud,
    responses={503: {"model": EstadoSalud, "description": "Base o extensión no disponible"}},
    summary="Estado de la aplicación y de sus dependencias básicas",
)
async def salud(unidad: Unidad) -> JSONResponse:
    base_conectada = False
    version_vector: str | None = None
    try:
        version_vector = await unidad.salud.version_extension_vector()
        base_conectada = True
    except Exception as error:
        # Solo el tipo de error: el mensaje puede contener la URL de conexión.
        obtener_registrador("salud").warning(
            "comprobacion de salud fallida",
            extra={"tipo_evento": "error_externo", "excepcion": type(error).__name__},
        )

    sano = base_conectada and version_vector is not None
    cuerpo = EstadoSalud(
        estado="ok" if sano else "degradado",
        version=__version__,
        base_de_datos=base_conectada,
        extension_vector=version_vector,
    )
    return JSONResponse(status_code=200 if sano else 503, content=cuerpo.model_dump())
