"""Rutas del caso para verificar las referencias de su borrador (T20; RF-09, CU-08, CP-12,
CP-13).

* ``POST /caso/referencias``: verifica la lista de referencias de la versión vigente más
  reciente. Responde 202 y el trabajo sigue en segundo plano. Sin versión, 409; si no se
  detectó la lista, 422 con qué hacer (RF-09, A).
* ``GET /caso/referencias/{id}``: avance (referencias hechas de un total) y el informe:
  estado de cada referencia con sus discrepancias, citas sin entrada y entradas no citadas.

Una solicitud de otro caso responde 404, igual que una inexistente (4.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from app.agentes.esquemas import EstadoReferencia
from app.agentes.referencias import AtencionReferencias
from app.agentes.verificacion_referencias import Verificador
from app.api.evidencia import SolicitudInexistente
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoSolicitud
from app.bibliografia.fabrica import crear_servicios
from app.configuracion import Ajustes
from app.corpus.fabrica import CorpusNoConfigurado
from app.corpus.grobid import ClienteGrobid
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoCaso, Reloj, RelojDep, Unidad, obtener_reloj

router = APIRouter(prefix="/caso", tags=["referencias"])

CAMPOS = {"titulo": "Título", "autores": "Autores", "anio": "Año", "doi": "DOI"}
NORMAS = {"ieee": "IEEE", "apa7": "APA 7", "vancouver": "Vancouver"}


class SolicitudVerificacion(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    creada_en: datetime


class DiscrepanciaVista(BaseModel):
    campo: str
    etiqueta: str
    valor_borrador: str | None
    valor_fuente: str | None


class ReferenciaVerificadaVista(BaseModel):
    indice: int
    texto_original: str
    estado: EstadoReferencia
    metodo: str | None
    discrepancias: list[DiscrepanciaVista]
    doi_encontrado: str | None
    url_doi: str | None
    explicacion: str | None
    citada: bool


class EntradaNoCitadaVista(BaseModel):
    indice: int
    texto: str


class ProgresoVista(BaseModel):
    hechas: int
    total: int


class ComprobacionVista(BaseModel):
    numero: int
    nombre: str
    superada: bool
    motivos: list[str]


class VistaVerificacion(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    entregada_en: datetime | None
    norma: str | None
    norma_nombre: str | None
    progreso: ProgresoVista | None
    resumen: dict[str, int]
    referencias: list[ReferenciaVerificadaVista]
    citas_sin_entrada: list[str]
    entradas_no_citadas: list[EntradaNoCitadaVista]
    avisos: list[str]
    etiqueta: Etiqueta | None
    advertencias: list[str]
    comprobaciones: list[ComprobacionVista]


async def obtener_atencion(peticion: Request, unidad: Unidad) -> AtencionReferencias:
    """Una por proceso; usa GROBID, Crossref, OpenAlex y, si se configura, el adaptador."""
    estado = peticion.app.state
    actual: AtencionReferencias | None = getattr(estado, "atencion_referencias", None)
    if actual is not None:
        return actual
    ajustes: Ajustes = estado.ajustes
    if not ajustes.url_grobid:
        raise CorpusNoConfigurado(["URL_GROBID"])
    _, parametros = await unidad.configuracion.vigente()
    reloj: Reloj = obtener_reloj(peticion)
    abrir = fabrica_de_unidades(estado.fabrica_sesiones)
    servicios = crear_servicios(ajustes, abrir)
    actual = AtencionReferencias(
        ClienteGrobid(ajustes.url_grobid),
        Verificador(servicios.crossref, servicios.openalex),
        crear_cadena(ajustes, parametros, registrador_en_base(abrir)),
        abrir,
        reloj,
    )
    estado.atencion_referencias = actual
    return actual


AtencionDep = Annotated[AtencionReferencias, Depends(obtener_atencion)]


@router.post(
    "/referencias",
    response_model=SolicitudVerificacion,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}, 503: {}},
    summary="Verificar las referencias de la versión vigente",
    description="202 y el trabajo sigue en segundo plano. 409 sin versión; 422 si no se"
    " detectó la lista de referencias (hay que indicarla a mano).",
)
async def verificar_referencias(
    contexto: ContextoCaso, unidad: Unidad, atencion: AtencionDep
) -> SolicitudVerificacion:
    solicitud = await atencion.iniciar(unidad, contexto)
    atencion.lanzar(solicitud, contexto)
    return SolicitudVerificacion(
        id=solicitud.id, estado=solicitud.estado, creada_en=solicitud.creada_en
    )


def _url_doi(doi: str | None) -> str | None:
    return f"https://doi.org/{doi}" if doi else None


@router.get(
    "/referencias/{solicitud_id}",
    response_model=VistaVerificacion,
    summary="Avance e informe de una verificación de referencias",
)
async def ver_verificacion(
    solicitud_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> VistaVerificacion:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None or solicitud.tipo is not TipoSolicitud.VERIFICACION_REFERENCIAS:
        raise SolicitudInexistente()
    atencion: AtencionReferencias | None = getattr(peticion.app.state, "atencion_referencias", None)
    if atencion is not None:
        await atencion.marcar_interrumpida(unidad, contexto, solicitud)
    elif solicitud.estado in {
        EstadoSolicitud.RECIBIDA,
        EstadoSolicitud.RECUPERANDO,
        EstadoSolicitud.GENERANDO,
    }:
        solicitud.estado, solicitud.motivo = EstadoSolicitud.NO_ATENDIDA, "interrumpida"
        solicitud.actualizada_en = reloj()
        await unidad.confirmar()
    resultado = await unidad.resultados.de_solicitud(contexto, solicitud_id)
    salida: dict[str, Any] = (resultado.salida or {}) if resultado else {}
    progreso = atencion.progreso(solicitud_id) if atencion is not None else None
    no_citadas = set(salida.get("entradas_no_citadas", []))
    textos = {r["indice"]: r["texto_original"] for r in salida.get("referencias", [])}
    norma = salida.get("norma")
    return VistaVerificacion(
        id=solicitud.id,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        creada_en=solicitud.creada_en,
        entregada_en=solicitud.entregada_en,
        norma=norma,
        norma_nombre=NORMAS.get(norma) if norma else None,
        progreso=ProgresoVista(hechas=progreso[0], total=progreso[1]) if progreso else None,
        resumen={e.value: int(salida.get("resumen", {}).get(e.value, 0)) for e in EstadoReferencia},
        referencias=[
            ReferenciaVerificadaVista(
                indice=r["indice"],
                texto_original=r["texto_original"],
                estado=EstadoReferencia(r["estado"]),
                metodo=r.get("metodo"),
                discrepancias=[
                    DiscrepanciaVista(
                        campo=d["campo"],
                        etiqueta=CAMPOS.get(d["campo"], d["campo"]),
                        valor_borrador=d.get("valor_borrador"),
                        valor_fuente=d.get("valor_fuente"),
                    )
                    for d in r.get("discrepancias", [])
                ],
                doi_encontrado=r.get("doi_encontrado"),
                url_doi=_url_doi(r.get("doi_encontrado")),
                explicacion=r.get("explicacion"),
                citada=r["indice"] not in no_citadas,
            )
            for r in salida.get("referencias", [])
        ],
        citas_sin_entrada=[str(c) for c in salida.get("citas_sin_entrada", [])],
        entradas_no_citadas=[
            EntradaNoCitadaVista(indice=i, texto=textos.get(i, ""))
            for i in salida.get("entradas_no_citadas", [])
        ],
        avisos=[str(a) for a in salida.get("avisos", [])],
        etiqueta=resultado.etiqueta if resultado else None,
        advertencias=[str(a) for a in (resultado.advertencias if resultado else [])],
        comprobaciones=[ComprobacionVista(**c) for c in salida.get("comprobaciones", [])],
    )
