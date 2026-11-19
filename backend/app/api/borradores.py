"""Rutas del borrador del caso (A1): versiones (T11) y sus secciones (T12).

RF-01, CU-01 y F-05 (decisiones T11-01, apartado 6, y T12-01, apartado 8). Toda lectura
filtra por el caso de la sesión: la versión de otro caso responde 404, igual que una
inexistente. Ninguna ruta devuelve el archivo; el texto de los párrafos solo lo ve su
propio caso, para elegir el alcance.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, UploadFile, status
from pydantic import BaseModel, Field

from app.borradores.secciones import TituloMarcado
from app.borradores.servicio import (
    SUBCARPETA,
    BorradorDemasiadoGrande,
    ResultadoCarga,
    ServicioBorradores,
    VersionDetalle,
    VersionInexistente,
    VersionResumen,
    VistaSecciones,
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


class MarcadoSecciones(BaseModel):
    titulos: list[TituloMarcado] = Field(min_length=1, max_length=500)


class MarcadoReferencias(BaseModel):
    desde: str = Field(min_length=1, max_length=20)
    hasta: str | None = Field(default=None, min_length=1, max_length=20)


@router.get(
    "/versiones/{version_id}/secciones",
    response_model=VistaSecciones,
    summary="Secciones y párrafos de una versión",
    description="Árbol de secciones, párrafos con su texto y sección, y la lista de"
    " referencias. Sin estilos de título, pide marcar las secciones (F-05).",
)
async def ver_secciones(
    version_id: uuid.UUID, contexto: ContextoCaso, unidad: Unidad
) -> VistaSecciones:
    version = await unidad.versiones.con_parrafos(contexto, version_id)
    if version is None:
        raise VersionInexistente()
    return VistaSecciones.desde(version)


@router.put(
    "/versiones/{version_id}/secciones",
    response_model=VistaSecciones,
    responses={409: {}},
    summary="Marcar a mano las secciones de una versión",
    description="Indica qué párrafos son títulos y su nivel. Reemplaza la detección por"
    " estilos y vuelve a detectar la lista de referencias. 409 si la versión ya tiene"
    " solicitudes.",
)
async def marcar_secciones(
    version_id: uuid.UUID,
    cuerpo: MarcadoSecciones,
    contexto: ContextoCaso,
    unidad: Unidad,
    servicio: ServicioDep,
) -> VistaSecciones:
    return await servicio.marcar_secciones(unidad, contexto, version_id, cuerpo.titulos)


@router.put(
    "/versiones/{version_id}/referencias",
    response_model=VistaSecciones,
    responses={409: {}},
    summary="Indicar a mano la lista de referencias",
    description="Del párrafo `desde` al párrafo `hasta` (por defecto, el último). Cada línea"
    " no vacía es una entrada. 409 si la versión ya tiene solicitudes.",
)
async def marcar_referencias(
    version_id: uuid.UUID,
    cuerpo: MarcadoReferencias,
    contexto: ContextoCaso,
    unidad: Unidad,
    servicio: ServicioDep,
) -> VistaSecciones:
    return await servicio.marcar_referencias(
        unidad, contexto, version_id, cuerpo.desde, cuerpo.hasta
    )
