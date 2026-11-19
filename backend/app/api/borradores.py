"""Rutas del borrador del caso (A1): cargar una versión, listarlas y ver sus metadatos.

RF-01 y CU-01 (decisión T11-01, apartado 6). Toda lectura filtra por el caso de la
sesión: la versión de otro caso responde 404, igual que una inexistente. Ninguna ruta
devuelve el archivo ni su texto.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, UploadFile, status

from app.borradores.servicio import (
    SUBCARPETA,
    BorradorDemasiadoGrande,
    ResultadoCarga,
    ServicioBorradores,
    VersionDetalle,
    VersionResumen,
    evento_de_validacion,
)
from app.comun.almacen import AlmacenPrivado
from app.comun.errores import ErrorAplicacion
from app.configuracion import Ajustes
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad

router = APIRouter(prefix="/caso", tags=["borradores"])

BYTES_POR_MB = 1024 * 1024
PARTE = BYTES_POR_MB


class BorradoresNoConfigurado(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "borradores_no_configurado",
            "La carga de borradores no está configurada en este servidor.",
            estado_http=503,
            detalle={"variables": ["DIRECTORIO_ARCHIVOS"]},
        )


class VersionInexistente(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__("no_existe", "La versión solicitada no existe.", estado_http=404)


def obtener_servicio(peticion: Request) -> ServicioBorradores:
    estado = peticion.app.state
    servicio: ServicioBorradores | None = getattr(estado, "servicio_borradores", None)
    if servicio is None:
        ajustes: Ajustes = estado.ajustes
        if not ajustes.directorio_archivos:
            raise BorradoresNoConfigurado()
        almacen = AlmacenPrivado(Path(ajustes.directorio_archivos), SUBCARPETA, ".docx")
        servicio = ServicioBorradores(almacen)
        estado.servicio_borradores = servicio
    return servicio


ServicioDep = Annotated[ServicioBorradores, Depends(obtener_servicio)]


@router.post(
    "/versiones",
    response_model=ResultadoCarga,
    status_code=status.HTTP_201_CREATED,
    responses={413: {}, 503: {}},
    summary="Cargar una versión del borrador",
    description="Valida el .docx (RN-16) y crea una versión nueva, vigente en su hito, sin"
    " borrar las anteriores (RN-09). Un archivo inválido, con macros, cifrado o dañado se"
    " rechaza con su motivo y no crea versión (CP-02).",
)
async def cargar_version(
    hito: Annotated[str, Form(min_length=1, max_length=40)],
    archivo: UploadFile,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
    servicio: ServicioDep,
) -> ResultadoCarga:
    _, parametros = await unidad.configuracion.vigente()
    limite = parametros.tamano_max_docx_mb * BYTES_POR_MB
    with tempfile.TemporaryDirectory(prefix="sma-borrador-") as carpeta:
        ruta = Path(carpeta) / "subido.docx"
        escritos = 0
        with ruta.open("wb") as destino:
            while parte := await archivo.read(PARTE):
                escritos += len(parte)
                if escritos > limite:
                    evento_de_validacion(contexto, "archivo_demasiado_grande", escritos)
                    raise BorradorDemasiadoGrande(parametros.tamano_max_docx_mb)
                destino.write(parte)
        return await servicio.cargar(
            unidad,
            contexto,
            hito.strip(),
            ruta,
            archivo.filename,
            archivo.content_type,
            reloj(),
        )


@router.get(
    "/versiones",
    response_model=list[VersionResumen],
    summary="Versiones del borrador",
    description="De la más reciente a la más antigua; con `hito`, solo las de ese hito.",
)
async def listar_versiones(
    contexto: ContextoCaso, unidad: Unidad, hito: str | None = None
) -> list[VersionResumen]:
    _, parametros = await unidad.configuracion.vigente()
    return [
        VersionResumen.desde(v, parametros.hitos)
        for v in await unidad.versiones.recientes(contexto, hito)
    ]


@router.get(
    "/versiones/{version_id}",
    response_model=VersionDetalle,
    summary="Metadatos de una versión del borrador",
)
async def ver_version(
    version_id: uuid.UUID, contexto: ContextoCaso, unidad: Unidad
) -> VersionDetalle:
    version = await unidad.versiones.con_parrafos(contexto, version_id)
    if version is None:
        raise VersionInexistente()
    _, parametros = await unidad.configuracion.vigente()
    return VersionDetalle.con_detalle(version, parametros.hitos)
