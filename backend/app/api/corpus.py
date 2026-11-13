"""Rutas del investigador para el corpus científico (T10; RF-15, CU-14, CP-21).

* Listar los documentos y las exclusiones de una colección científica.
* Subir un PDF: se valida, se extrae, se segmenta y se indexa en la misma petición
  (unos segundos por documento). Un PDF a la vez por proceso.
* Confirmar un documento incompleto y retirar un documento.

Los PDF no se descargan por ninguna ruta: el sistema muestra fragmentos breves con
enlace a la fuente y no redistribuye los archivos (Fase 1, 18.10 y n.° 13).
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, UploadFile, status
from pydantic import BaseModel

from app.bd.enumeraciones import (
    EstadoDocumento,
    MotivoExclusionCorpus,
    ObjetoExclusion,
    TipoColeccion,
)
from app.bd.modelos import Coleccion, Documento, ExclusionCorpus
from app.comun.errores import ErrorAplicacion
from app.configuracion import Ajustes
from app.corpus.fabrica import crear_indexador, crear_reindexador
from app.corpus.indexacion import (
    Indexador,
    RecursoInexistente,
    Resultado,
    ResultadoIngesta,
    mensaje_de_motivo,
)
from app.repositorios.contexto import ContextoAcceso
from app.seguridad.dependencias import ContextoInvestigador, RelojDep, Unidad

router = APIRouter(prefix="/investigador", tags=["corpus"])

BYTES_POR_MB = 1024 * 1024
PARTE = BYTES_POR_MB


class ArchivoDemasiadoGrande(ErrorAplicacion):
    def __init__(self, limite_mb: int) -> None:
        super().__init__(
            "archivo_demasiado_grande",
            f"El PDF supera el tamaño máximo de {limite_mb} MB.",
            estado_http=413,
            detalle={"limite_mb": limite_mb},
        )


class DocumentoVista(BaseModel):
    id: uuid.UUID
    titulo: str | None
    autores: list[dict[str, Any]]
    anio: int | None
    doi: str | None
    estado: EstadoDocumento
    motivo_estado: str | None
    confirmado: bool
    archivo_original: str | None
    num_paginas: int | None
    fragmentos: int
    creado_en: datetime
    retirado_en: datetime | None

    @classmethod
    def desde(cls, documento: Documento, fragmentos: int) -> DocumentoVista:
        return cls(
            id=documento.id,
            titulo=documento.titulo,
            autores=list(documento.autores),
            anio=documento.anio,
            doi=documento.doi,
            estado=documento.estado,
            motivo_estado=documento.motivo_estado,
            confirmado=documento.confirmado_en is not None,
            archivo_original=documento.archivo_original,
            num_paginas=documento.num_paginas,
            fragmentos=fragmentos,
            creado_en=documento.creado_en,
            retirado_en=documento.retirado_en,
        )


class ExclusionVista(BaseModel):
    id: uuid.UUID
    objeto: ObjetoExclusion
    identificador: str
    motivo: MotivoExclusionCorpus
    mensaje: str
    duplicado_de_id: uuid.UUID | None
    registrada_en: datetime

    @classmethod
    def desde(cls, exclusion: ExclusionCorpus) -> ExclusionVista:
        return cls(
            id=exclusion.id,
            objeto=exclusion.objeto,
            identificador=exclusion.identificador,
            motivo=exclusion.motivo,
            mensaje=mensaje_de_motivo(exclusion.motivo),
            duplicado_de_id=exclusion.duplicado_de_id,
            registrada_en=exclusion.registrada_en,
        )


async def _perezoso(
    peticion: Request, nombre: str, crear: Callable[[Ajustes], Indexador]
) -> Indexador:
    """Crea una sola vez por proceso el indexador (Docling tarda en cargar)."""
    estado = peticion.app.state
    actual: Indexador | None = getattr(estado, nombre, None)
    if actual is not None:
        return actual
    async with estado.candado_corpus:
        actual = getattr(estado, nombre, None)
        if actual is None:
            ajustes: Ajustes = estado.ajustes
            actual = await asyncio.to_thread(crear, ajustes)
            setattr(estado, nombre, actual)
        return actual


async def obtener_indexador(peticion: Request) -> Indexador:
    return await _perezoso(peticion, "indexador", crear_indexador)


async def obtener_embebedor(peticion: Request) -> Indexador:
    """Solo embeddings (confirmar un incompleto): no carga Docling."""
    return await _perezoso(peticion, "embebedor", crear_reindexador)


IndexadorDep = Annotated[Indexador, Depends(obtener_indexador)]
EmbebedorDep = Annotated[Indexador, Depends(obtener_embebedor)]


async def _cientifica(
    unidad: Unidad, contexto: ContextoAcceso, coleccion_id: uuid.UUID
) -> Coleccion:
    coleccion = await unidad.corpus.coleccion(contexto, coleccion_id)
    if coleccion is None or coleccion.tipo is not TipoColeccion.CIENTIFICA:
        raise RecursoInexistente()
    return coleccion


async def _vista(unidad: Unidad, contexto: ContextoAcceso, documento: Documento) -> DocumentoVista:
    fragmentos = await unidad.corpus.fragmentos(contexto, documento)
    return DocumentoVista.desde(documento, len(fragmentos))


@router.get(
    "/colecciones/{coleccion_id}/documentos",
    response_model=list[DocumentoVista],
    summary="Documentos de una colección científica",
)
async def listar_documentos(
    coleccion_id: uuid.UUID, contexto: ContextoInvestigador, unidad: Unidad
) -> list[DocumentoVista]:
    coleccion = await _cientifica(unidad, contexto, coleccion_id)
    return [
        DocumentoVista.desde(documento, fragmentos)
        for documento, fragmentos in await unidad.corpus.listar_documentos(contexto, coleccion.id)
    ]


@router.get(
    "/colecciones/{coleccion_id}/exclusiones",
    response_model=list[ExclusionVista],
    summary="Archivos y referencias excluidos de una colección, con su motivo",
)
async def listar_exclusiones(
    coleccion_id: uuid.UUID, contexto: ContextoInvestigador, unidad: Unidad
) -> list[ExclusionVista]:
    coleccion = await _cientifica(unidad, contexto, coleccion_id)
    return [
        ExclusionVista.desde(e)
        for e in await unidad.corpus.listar_exclusiones(contexto, coleccion.id)
    ]


@router.post(
    "/colecciones/{coleccion_id}/documentos",
    response_model=ResultadoIngesta,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": ResultadoIngesta}, 413: {}, 503: {}},
    summary="Subir un PDF a una colección científica",
    description="201 si se guardó (indexado o incompleto); 200 si se excluyó, era un"
    " duplicado o ya se había procesado. El motivo va en la respuesta.",
)
async def subir_documento(
    coleccion_id: uuid.UUID,
    archivo: UploadFile,
    contexto: ContextoInvestigador,
    unidad: Unidad,
    indexador: IndexadorDep,
    respuesta: Response,
) -> ResultadoIngesta:
    coleccion = await _cientifica(unidad, contexto, coleccion_id)
    _, parametros = await unidad.configuracion.vigente()
    limite = parametros.tamano_max_pdf_mb * BYTES_POR_MB
    with tempfile.TemporaryDirectory(prefix="sma-subida-") as carpeta:
        ruta = Path(carpeta) / "subido.pdf"
        escritos = 0
        with ruta.open("wb") as destino:
            while parte := await archivo.read(PARTE):
                escritos += len(parte)
                if escritos > limite:
                    raise ArchivoDemasiadoGrande(parametros.tamano_max_pdf_mb)
                destino.write(parte)
        resultado = await indexador.ingerir(unidad, contexto, coleccion, ruta, archivo.filename)
    if resultado.resultado not in (Resultado.INDEXADO, Resultado.INCOMPLETO):
        respuesta.status_code = status.HTTP_200_OK
    return resultado


@router.post(
    "/documentos/{documento_id}/confirmar",
    response_model=DocumentoVista,
    summary="Confirmar la indexación de un documento incompleto",
)
async def confirmar_documento(
    documento_id: uuid.UUID,
    contexto: ContextoInvestigador,
    unidad: Unidad,
    reloj: RelojDep,
    embebedor: EmbebedorDep,
) -> DocumentoVista:
    documento = await embebedor.confirmar(unidad, contexto, documento_id, reloj())
    return await _vista(unidad, contexto, documento)


@router.post(
    "/documentos/{documento_id}/retirar",
    response_model=DocumentoVista,
    summary="Retirar un documento: deja de recuperarse y se conserva su registro",
)
async def retirar_documento(
    documento_id: uuid.UUID, contexto: ContextoInvestigador, unidad: Unidad, reloj: RelojDep
) -> DocumentoVista:
    documento = await Indexador.retirar(unidad, contexto, documento_id, reloj())
    return await _vista(unidad, contexto, documento)
