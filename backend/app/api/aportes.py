"""Aporte de una fuente tras una abstención (T32; RF-13, CU-12, CP-14 a CP-17).

* ``POST /caso/solicitudes/{id}/aporte``: formulario con los datos bibliográficos (título,
  autores y año; DOI opcional) y, si lo tiene, el PDF. Solo sobre una búsqueda de evidencia
  entregada como "Sin evidencia suficiente" del propio caso. Registra la decisión "aportar"
  (CU-11) y sigue CU-12 en la misma petición (``app/aportes/servicio.py``); si la fuente
  quedó en la colección personal, encola una nueva búsqueda con la misma consulta.
* ``GET /caso/solicitudes/{id}/aportes``: los aportes de esa solicitud, con su desenlace.

El nombre original del PDF no se guarda ni se registra. Otra solicitud responde 404.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, UploadFile, status
from pydantic import BaseModel, ValidationError

from app.api.corpus import (
    BYTES_POR_MB,
    PARTE,
    ArchivoDemasiadoGrande,
    obtener_embebedor,
    obtener_indexador,
)
from app.api.decisiones import en_orden
from app.api.evidencia import SolicitudInexistente
from app.aportes.existencia import DatosAporte
from app.aportes.servicio import DesenlaceAporte, ServicioAportes
from app.bd.enumeraciones import (
    CoherenciaFuente,
    EstadoSolicitud,
    ExistenciaFuente,
    IndexacionAporte,
    MetodoExistencia,
    OpcionDecision,
    TipoSolicitud,
)
from app.bd.modelos import Decision, FuenteAportada, Resultado, Solicitud
from app.bibliografia.fabrica import crear_servicios
from app.bibliografia.referencias import ConstructorReferencias
from app.comun.errores import ErrorAplicacion
from app.configuracion import Ajustes
from app.corpus.indexacion import Indexador
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.orquestacion.en_api import encolar
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad, obtener_reloj

router = APIRouter(prefix="/caso/solicitudes", tags=["aportes"])


class AporteNoAdmitido(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "aporte_no_admitido",
            "Solo se aporta una fuente a una búsqueda de evidencia que terminó como"
            ' "Sin evidencia suficiente".',
            estado_http=409,
        )


class DatosAporteInvalidos(ErrorAplicacion):
    def __init__(self, campos: list[str]) -> None:
        super().__init__(
            "datos_aporte_invalidos",
            "Revise los datos de la fuente: título, al menos un autor, año y, si lo tiene,"
            " un DOI con la forma 10.xxxx/...",
            estado_http=422,
            detalle={"campos": campos},
        )


class VistaAporte(BaseModel):
    id: uuid.UUID
    titulo: str
    anio: int | None
    doi: str | None
    con_pdf: bool
    existencia: ExistenciaFuente
    metodo_existencia: MetodoExistencia | None
    coherencia: CoherenciaFuente
    explicacion_coherencia: str | None  # solo en la respuesta del aporte (no se guarda)
    indexacion: IndexacionAporte
    motivo_indexacion: str | None
    texto_indexado: str | None  # "pdf" o "resumen", solo en la respuesta del aporte
    cita_propuesta: str | None
    nueva_solicitud_id: uuid.UUID | None
    aportada_en: datetime


def _vista(aporte: FuenteAportada, desenlace: DesenlaceAporte | None = None) -> VistaAporte:
    datos = aporte.datos_bibliograficos or {}
    return VistaAporte(
        id=aporte.id,
        titulo=str(datos.get("titulo", "")),
        anio=datos.get("anio") if isinstance(datos.get("anio"), int) else None,
        doi=aporte.doi,
        con_pdf=bool(datos.get("con_pdf")),
        existencia=aporte.existencia,
        metodo_existencia=aporte.metodo_existencia,
        coherencia=aporte.coherencia,
        explicacion_coherencia=desenlace.coherencia.explicacion if desenlace else None,
        indexacion=aporte.indexacion,
        motivo_indexacion=aporte.motivo_indexacion,
        texto_indexado=desenlace.texto_indexado if desenlace else None,
        cita_propuesta=aporte.cita_propuesta,
        nueva_solicitud_id=aporte.solicitud_recuperacion_id,
        aportada_en=aporte.aportada_en,
    )


def _crear_servicio(peticion: Request, ajustes: Ajustes) -> ServicioAportes:
    estado = peticion.app.state
    abrir = fabrica_de_unidades(estado.fabrica_sesiones)
    servicios = crear_servicios(ajustes, abrir)

    async def embebedor() -> Indexador:
        return await obtener_embebedor(peticion)

    async def canal_pdf() -> Indexador:
        return await obtener_indexador(peticion)

    return ServicioAportes(
        servicios=[servicios.crossref, servicios.openalex],
        citas=ConstructorReferencias(servicios.doi),
        modelo=None,  # se completa con la cadena al primer uso (necesita la configuración)
        embebedor=embebedor,
        canal_pdf=canal_pdf,
        reloj=obtener_reloj(peticion),
    )


async def obtener_servicio(peticion: Request, unidad: Unidad) -> ServicioAportes:
    """Uno por proceso; las pruebas lo sustituyen en ``app.state.servicio_aportes``."""
    estado = peticion.app.state
    actual: ServicioAportes | None = getattr(estado, "servicio_aportes", None)
    if actual is None:
        ajustes: Ajustes = estado.ajustes
        actual = _crear_servicio(peticion, ajustes)
        _, parametros = await unidad.configuracion.vigente()
        actual.usar_modelo(
            crear_cadena(
                ajustes,
                parametros,
                registrador_en_base(fabrica_de_unidades(estado.fabrica_sesiones)),
            )
        )
        estado.servicio_aportes = actual
    return actual


ServicioDep = Annotated[ServicioAportes, Depends(obtener_servicio)]


async def _abstencion_propia(
    unidad: Unidad, contexto: ContextoAcceso, solicitud_id: uuid.UUID
) -> tuple[Solicitud, Resultado]:
    solicitud = await unidad.solicitudes.bloquear(contexto, solicitud_id)
    if solicitud is None:
        raise SolicitudInexistente()
    if (
        solicitud.tipo is not TipoSolicitud.BUSQUEDA_EVIDENCIA
        or solicitud.estado is not EstadoSolicitud.ENTREGADA
    ):
        raise AporteNoAdmitido()
    resultado = await unidad.resultados.de_solicitud(contexto, solicitud_id)
    if resultado is None or not resultado.abstencion:
        raise AporteNoAdmitido()
    return solicitud, resultado


async def _decidir_aportar(
    unidad: Unidad, contexto: ContextoAcceso, resultado: Resultado, ahora: datetime
) -> None:
    """CU-12 extiende CU-11: aportar es la decisión sobre la abstención (se reemplaza la
    anterior, si era otra)."""
    cadena = en_orden(list(await unidad.decisiones.de_resultado(contexto, resultado.id)))
    vigente = cadena[-1] if cadena else None
    if vigente is not None and vigente.opcion is OpcionDecision.APORTAR:
        return
    await unidad.decisiones.agregar(
        contexto,
        Decision(
            resultado_id=resultado.id,
            opcion=OpcionDecision.APORTAR,
            decidida_en=ahora,
            decision_reemplazada_id=vigente.id if vigente else None,
        ),
    )


@router.post(
    "/{solicitud_id}/aporte",
    response_model=VistaAporte,
    status_code=status.HTTP_201_CREATED,
    responses={409: {}, 413: {}, 503: {}},
    summary="Aportar una fuente tras una búsqueda sin evidencia suficiente",
)
async def aportar(
    solicitud_id: uuid.UUID,
    titulo: Annotated[str, Form()],
    autores: Annotated[str, Form(description="Apellidos de los autores, uno por línea.")],
    anio: Annotated[int, Form()],
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    servicio: ServicioDep,
    reloj: RelojDep,
    doi: Annotated[str | None, Form()] = None,
    archivo: UploadFile | None = None,
) -> VistaAporte:
    try:
        datos = DatosAporte(
            titulo=titulo, autores=autores.splitlines() or [autores], anio=anio, doi=doi
        )
    except ValidationError as error:
        raise DatosAporteInvalidos(
            sorted({str(e["loc"][0]) for e in error.errors() if e["loc"]})
        ) from None
    solicitud, resultado = await _abstencion_propia(unidad, contexto, solicitud_id)
    caso = await unidad.caso_propio.obtener(contexto)
    assert caso is not None
    await _decidir_aportar(unidad, contexto, resultado, reloj())
    _, parametros = await unidad.configuracion.vigente()
    limite = parametros.tamano_max_pdf_mb * BYTES_POR_MB
    with tempfile.TemporaryDirectory(prefix="sma-aporte-") as carpeta:
        ruta: Path | None = None
        if archivo is not None:
            ruta = Path(carpeta) / "aporte.pdf"
            escritos = 0
            with ruta.open("wb") as destino:
                while parte := await archivo.read(PARTE):
                    escritos += len(parte)
                    if escritos > limite:
                        raise ArchivoDemasiadoGrande(parametros.tamano_max_pdf_mb)
                    destino.write(parte)
            if escritos == 0:
                ruta = None
        desenlace = await servicio.aportar(
            unidad, contexto, solicitud, datos, ruta, caso[0].norma_citacion
        )
    if desenlace.nueva_solicitud is not None:
        encolar(peticion, desenlace.nueva_solicitud, contexto)
    return _vista(desenlace.aporte, desenlace)


@router.get(
    "/{solicitud_id}/aportes",
    response_model=list[VistaAporte],
    summary="Fuentes aportadas tras una solicitud, con su desenlace",
)
async def ver_aportes(
    solicitud_id: uuid.UUID, contexto: ContextoCaso, unidad: Unidad
) -> list[VistaAporte]:
    if await unidad.solicitudes.obtener(contexto, solicitud_id) is None:
        raise SolicitudInexistente()
    return [_vista(a) for a in await unidad.fuentes_aportadas.de_solicitud(contexto, solicitud_id)]
