"""Rutas del investigador para importar las referencias del artículo O1 (T15; RF-20, CU-14).

* Iniciar una importación con el artículo (PDF o .docx) o con una lista de DOI: responde
  202 y el trabajo sigue en segundo plano.
* Consultar el avance, el informe del tema y las referencias (con la vista de pendientes).
* Subir el PDF de una referencia pendiente.

El artículo O1 se guarda solo en la carpeta privada de la importación y se borra en
cuanto se extraen sus referencias (RN-19). Ninguna ruta lo devuelve ni guarda su nombre.
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, UploadFile, status
from pydantic import BaseModel

from app.api.corpus import ArchivoDemasiadoGrande, obtener_indexador
from app.bd.enumeraciones import (
    EstadoImportacion,
    EstadoReferencia,
    OrigenImportacion,
    TipoColeccion,
)
from app.bd.modelos import Coleccion, ImportacionReferencias, ReferenciaImportada
from app.comun.errores import ErrorAplicacion
from app.configuracion import Ajustes
from app.corpus.indexacion import RecursoInexistente
from app.importacion.extraccion import origen_de
from app.importacion.fabrica import crear_importador
from app.importacion.servicio import Entrada, Importador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoInvestigador, Reloj, RelojDep, Unidad, obtener_reloj

router = APIRouter(prefix="/investigador", tags=["importacion"])

BYTES_POR_MB = 1024 * 1024
PARTE = BYTES_POR_MB
MAX_CARACTERES_DOIS = 100_000


class ArticuloDemasiadoGrande(ErrorAplicacion):
    def __init__(self, limite_mb: int) -> None:
        super().__init__(
            "archivo_demasiado_grande",
            f"El artículo supera el tamaño máximo de {limite_mb} MB.",
            estado_http=413,
            detalle={"limite_mb": limite_mb},
        )


class EntradaAmbigua(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "entrada_no_valida",
            "Suba el artículo (PDF o .docx) o pegue una lista de DOI, pero no ambos.",
            estado_http=422,
        )


class ImportacionVista(BaseModel):
    id: uuid.UUID
    coleccion_id: uuid.UUID
    origen: OrigenImportacion
    estado: EstadoImportacion
    total: int
    procesadas: int
    error: str | None
    creada_en: datetime
    iniciada_en: datetime | None
    terminada_en: datetime | None

    @classmethod
    def desde(cls, importacion: ImportacionReferencias) -> ImportacionVista:
        return cls(
            id=importacion.id,
            coleccion_id=importacion.coleccion_id,
            origen=importacion.origen,
            estado=importacion.estado,
            total=importacion.total,
            procesadas=importacion.procesadas,
            error=importacion.error,
            creada_en=importacion.creada_en,
            iniciada_en=importacion.iniciada_en,
            terminada_en=importacion.terminada_en,
        )


class ReferenciaVista(BaseModel):
    id: uuid.UUID
    texto: str
    doi: str | None
    titulo: str | None
    autores: list[str]
    anio: int | None
    estado: EstadoReferencia
    motivo: str | None
    estado_oa: str | None
    url_acceso_abierto: str | None
    url_pdf: str | None
    licencia: str | None
    documento_id: uuid.UUID | None
    actualizada_en: datetime

    @classmethod
    def desde(cls, referencia: ReferenciaImportada) -> ReferenciaVista:
        return cls(
            id=referencia.id,
            texto=referencia.texto,
            doi=referencia.doi,
            titulo=referencia.titulo,
            autores=[str(a) for a in referencia.autores or []],
            anio=referencia.anio,
            estado=referencia.estado,
            motivo=referencia.motivo,
            estado_oa=referencia.estado_oa,
            url_acceso_abierto=referencia.url_acceso_abierto,
            url_pdf=referencia.url_pdf,
            licencia=referencia.licencia,
            documento_id=referencia.documento_id,
            actualizada_en=referencia.actualizada_en,
        )


class InformeTema(BaseModel):
    """Informe del corpus de un tema (RF-15, RF-20)."""

    coleccion_id: uuid.UUID
    tema: str | None
    referencias: int
    de_acceso_abierto: int
    incluidas: int
    pendientes_pdf: int
    no_comprobables: int
    excluidas: int
    excluidas_por_motivo: dict[str, int]
    documentos_recuperables: int
    exclusiones_del_corpus: int


async def obtener_importador(peticion: Request) -> Importador:
    """Uno por proceso; usa el indexador de T10 (carga Docling al primer uso)."""
    estado = peticion.app.state
    actual: Importador | None = getattr(estado, "importador", None)
    if actual is not None:
        return actual
    indexador = await obtener_indexador(peticion)
    async with estado.candado_corpus:
        actual = getattr(estado, "importador", None)
        if actual is None:
            ajustes: Ajustes = estado.ajustes
            reloj: Reloj = obtener_reloj(peticion)
            abrir = fabrica_de_unidades(estado.fabrica_sesiones)
            actual = crear_importador(ajustes, abrir, indexador, reloj)
            estado.importador = actual
        return actual


ImportadorDep = Annotated[Importador, Depends(obtener_importador)]


async def _cientifica(
    unidad: Unidad, contexto: ContextoAcceso, coleccion_id: uuid.UUID
) -> Coleccion:
    coleccion = await unidad.corpus.coleccion(contexto, coleccion_id)
    if coleccion is None or coleccion.tipo is not TipoColeccion.CIENTIFICA:
        raise RecursoInexistente()
    return coleccion


async def _interrumpidas(
    peticion: Request, unidad: Unidad, contexto: ContextoAcceso, ahora: datetime
) -> None:
    """Una importación en curso que este proceso no atiende quedó cortada por un reinicio."""
    importador: Importador | None = getattr(peticion.app.state, "importador", None)
    activas = importador.activas if importador is not None else frozenset()
    if await unidad.importacion.marcar_interrumpidas(contexto, activas, ahora):
        await unidad.confirmar()


@router.post(
    "/colecciones/{coleccion_id}/importaciones",
    response_model=ImportacionVista,
    status_code=status.HTTP_202_ACCEPTED,
    responses={413: {}, 503: {}},
    summary="Importar las referencias de un artículo O1 o de una lista de DOI",
    description="Responde 202 en cuanto recibe el archivo; el avance se consulta en"
    " /investigador/importaciones/{id}. El artículo se borra al extraer sus referencias.",
)
async def iniciar_importacion(
    coleccion_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoInvestigador,
    unidad: Unidad,
    reloj: RelojDep,
    importador: ImportadorDep,
    archivo: UploadFile | None = None,
    dois: Annotated[str | None, Form(max_length=MAX_CARACTERES_DOIS)] = None,
) -> ImportacionVista:
    coleccion = await _cientifica(unidad, contexto, coleccion_id)
    await _interrumpidas(peticion, unidad, contexto, reloj())
    hay_dois = bool(dois and dois.strip())
    if (archivo is None) == (not hay_dois):
        raise EntradaAmbigua()
    origen = origen_de(archivo.filename) if archivo is not None else OrigenImportacion.DOI
    importacion = await unidad.importacion.agregar(
        contexto,
        ImportacionReferencias(coleccion_id=coleccion.id, origen=origen, creada_en=reloj()),
    )
    if archivo is None:
        entrada = Entrada(origen=origen, dois=dois)
    else:
        ruta = await _guardar_articulo(unidad, importador, importacion.id, archivo, origen)
        entrada = Entrada(
            origen=origen, ruta=ruta, nombre=archivo.filename, tipo=archivo.content_type
        )
    await unidad.confirmar()
    importador.lanzar(importacion.id, contexto, entrada)
    return ImportacionVista.desde(importacion)


async def _guardar_articulo(
    unidad: Unidad,
    importador: Importador,
    importacion_id: uuid.UUID,
    archivo: UploadFile,
    origen: OrigenImportacion,
) -> Path:
    _, parametros = await unidad.configuracion.vigente()
    limite_mb = (
        parametros.tamano_max_pdf_mb
        if origen is OrigenImportacion.PDF
        else parametros.tamano_max_docx_mb
    )
    carpeta = importador.carpeta(importacion_id)
    ruta = carpeta / f"articulo.{origen.value}"
    escritos = 0
    try:
        with ruta.open("wb") as destino:
            while parte := await archivo.read(PARTE):
                escritos += len(parte)
                if escritos > limite_mb * BYTES_POR_MB:
                    raise ArticuloDemasiadoGrande(limite_mb)
                destino.write(parte)
    except BaseException:
        shutil.rmtree(carpeta, ignore_errors=True)  # RN-19
        raise
    return ruta


@router.get(
    "/importaciones/{importacion_id}",
    response_model=ImportacionVista,
    summary="Avance de una importación de referencias",
)
async def ver_importacion(
    importacion_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoInvestigador,
    unidad: Unidad,
    reloj: RelojDep,
) -> ImportacionVista:
    await _interrumpidas(peticion, unidad, contexto, reloj())
    importacion = await unidad.importacion.obtener(contexto, importacion_id)
    if importacion is None:
        raise RecursoInexistente()
    return ImportacionVista.desde(importacion)


@router.get(
    "/colecciones/{coleccion_id}/informe",
    response_model=InformeTema,
    summary="Informe del corpus de un tema: referencias por estado y motivo",
)
async def informe_tema(
    coleccion_id: uuid.UUID, contexto: ContextoInvestigador, unidad: Unidad
) -> InformeTema:
    coleccion = await _cientifica(unidad, contexto, coleccion_id)
    por_estado = dict.fromkeys(EstadoReferencia, 0)
    por_motivo: dict[str, int] = {}
    abiertas = 0
    for estado, motivo, abierta, cantidad in await unidad.importacion.conteos(
        contexto, coleccion.id
    ):
        por_estado[estado] += cantidad
        abiertas += cantidad if abierta else 0
        if estado is EstadoReferencia.EXCLUIDA and motivo:
            por_motivo[motivo] = por_motivo.get(motivo, 0) + cantidad
    return InformeTema(
        coleccion_id=coleccion.id,
        tema=coleccion.tema,
        referencias=sum(por_estado.values()),
        de_acceso_abierto=abiertas,
        incluidas=por_estado[EstadoReferencia.INCLUIDA],
        pendientes_pdf=por_estado[EstadoReferencia.PENDIENTE_PDF],
        no_comprobables=por_estado[EstadoReferencia.NO_COMPROBABLE],
        excluidas=por_estado[EstadoReferencia.EXCLUIDA],
        excluidas_por_motivo=dict(sorted(por_motivo.items())),
        documentos_recuperables=coleccion.n_incluidas,
        exclusiones_del_corpus=coleccion.n_excluidas,
    )


@router.get(
    "/colecciones/{coleccion_id}/referencias",
    response_model=list[ReferenciaVista],
    summary="Referencias importadas de un tema; con estado=pendiente_pdf, los pendientes",
)
async def listar_referencias(
    coleccion_id: uuid.UUID,
    contexto: ContextoInvestigador,
    unidad: Unidad,
    estado: EstadoReferencia | None = None,
) -> list[ReferenciaVista]:
    coleccion = await _cientifica(unidad, contexto, coleccion_id)
    return [
        ReferenciaVista.desde(r)
        for r in await unidad.importacion.referencias(contexto, coleccion.id, estado)
    ]


@router.post(
    "/referencias/{referencia_id}/pdf",
    response_model=ReferenciaVista,
    responses={413: {}, 503: {}},
    summary="Subir el PDF de una referencia pendiente",
    description="Se indexa con el canal de T09 y T10: la referencia queda incluida, o"
    " excluida con el motivo del canal.",
)
async def subir_pdf_referencia(
    referencia_id: uuid.UUID,
    archivo: UploadFile,
    contexto: ContextoInvestigador,
    unidad: Unidad,
    importador: ImportadorDep,
) -> ReferenciaVista:
    if await unidad.importacion.referencia(contexto, referencia_id) is None:
        raise RecursoInexistente()
    _, parametros = await unidad.configuracion.vigente()
    limite = parametros.tamano_max_pdf_mb * BYTES_POR_MB
    with tempfile.TemporaryDirectory(prefix="sma-referencia-") as carpeta:
        ruta = Path(carpeta) / "subido.pdf"
        escritos = 0
        with ruta.open("wb") as destino:
            while parte := await archivo.read(PARTE):
                escritos += len(parte)
                if escritos > limite:
                    raise ArchivoDemasiadoGrande(parametros.tamano_max_pdf_mb)
                destino.write(parte)
        referencia = await importador.subir_pdf(unidad, contexto, referencia_id, ruta)
    return ReferenciaVista.desde(referencia)
