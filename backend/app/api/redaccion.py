"""Rutas del caso para la propuesta de redacción de un párrafo (T27; RF-07, CU-06, CP-09,
CP-10).

* ``GET /caso/redaccion/parrafos``: párrafos del cuerpo de la versión vigente, con su
  sección, sus palabras y si están dentro del límite.
* ``POST /caso/redaccion``: pide la propuesta de un párrafo; un párrafo fuera de los límites
  se rechaza con su motivo y no crea la solicitud (CP-09). Responde 202 y el trabajo sigue
  en segundo plano.
* ``GET /caso/redaccion/{id}``: avance y resultado, con el original, la propuesta y cada
  cambio con su razón y la pauta desplegable de la guía.

Una solicitud de otro caso responde 404, igual que una inexistente (4.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.agentes.redaccion import (
    TIPO,
    AgenteRedaccion,
    AtencionRedaccion,
    parrafos_redactables,
)
from app.api.estructura import CitaGuia
from app.api.evidencia import ComprobacionVista, SolicitudInexistente
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta
from app.borradores.alcance import contar_palabras
from app.configuracion import Ajustes
from app.corpus.fabrica import CorpusNoConfigurado
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.rag.modelos import AVISO_SIN_EVIDENCIA
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoCaso, Reloj, RelojDep, Unidad, obtener_reloj

router = APIRouter(prefix="/caso/redaccion", tags=["redaccion"])
INDICADORES = {
    "registro_formal": "Registro formal",
    "fluidez_y_precision_lexica": "Fluidez y precisión léxica",
    "correccion_gramatical_y_claridad": "Corrección gramatical y claridad",
}


class ParrafoRedactable(BaseModel):
    id: str
    seccion: str
    texto: str
    palabras: int
    dentro_del_limite: bool


class ParrafosRedactables(BaseModel):
    limite_palabras: int
    parrafos: list[ParrafoRedactable]


class PedidoRedaccion(BaseModel):
    parrafo_id: str = Field(min_length=1, max_length=40)


class SolicitudRedaccion(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    creada_en: datetime


class CambioVista(BaseModel):
    tipo: str
    tipo_nombre: str
    antes: str
    despues: str
    razon: str
    citas: list[CitaGuia]


class VistaRedaccion(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    entregada_en: datetime | None
    parrafo_id: str | None
    abstencion: bool
    aviso: str | None
    etiqueta: Etiqueta | None
    original: str | None
    propuesta: str | None
    palabras_original: int
    palabras_propuesta: int
    limite_palabras_propuesta: int
    cambios: list[CambioVista]
    notas_para_el_estudiante: list[str]
    advertencias: list[str]
    comprobaciones: list[ComprobacionVista]


async def obtener_atencion(peticion: Request, unidad: Unidad) -> AtencionRedaccion:
    """Una por proceso; usa el servicio de modelos y el adaptador."""
    estado = peticion.app.state
    actual: AtencionRedaccion | None = getattr(estado, "atencion_redaccion", None)
    if actual is not None:
        return actual
    ajustes: Ajustes = estado.ajustes
    if not ajustes.url_servicio_modelos:
        raise CorpusNoConfigurado(["URL_SERVICIO_MODELOS"])
    _, parametros = await unidad.configuracion.vigente()
    reloj: Reloj = obtener_reloj(peticion)
    abrir = fabrica_de_unidades(estado.fabrica_sesiones)
    modelos = cliente_desde_ajustes(ajustes)
    cadena = crear_cadena(ajustes, parametros, registrador_en_base(abrir))
    evidencia = ServicioEvidencia(Recuperador(modelos, modelos), cadena, reloj)
    actual = AtencionRedaccion(TIPO, AgenteRedaccion(evidencia, cadena), abrir, reloj)
    estado.atencion_redaccion = actual
    return actual


AtencionDep = Annotated[AtencionRedaccion, Depends(obtener_atencion)]


@router.get(
    "/parrafos",
    response_model=ParrafosRedactables,
    summary="Párrafos de la versión vigente que admiten una propuesta de redacción",
)
async def parrafos(contexto: ContextoCaso, unidad: Unidad) -> ParrafosRedactables:
    _, parametros = await unidad.configuracion.vigente()
    limite = parametros.limite_palabras_d3
    version = await unidad.versiones.vigente_mas_reciente(contexto)
    if version is None:
        return ParrafosRedactables(limite_palabras=limite, parrafos=[])
    completa = await unidad.versiones.con_parrafos(contexto, version.id)
    assert completa is not None
    return ParrafosRedactables(
        limite_palabras=limite,
        parrafos=[
            ParrafoRedactable(id=i, seccion=s, texto=t, palabras=p, dentro_del_limite=p <= limite)
            for i, s, t, p in parrafos_redactables(completa)
        ],
    )


@router.post(
    "",
    response_model=SolicitudRedaccion,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}, 503: {}},
    summary="Pedir la propuesta de redacción de un párrafo",
)
async def pedir_redaccion(
    pedido: PedidoRedaccion, contexto: ContextoCaso, unidad: Unidad, atencion: AtencionDep
) -> SolicitudRedaccion:
    solicitud = await atencion.iniciar(unidad, contexto, pedido.parrafo_id)
    atencion.lanzar(solicitud, contexto)
    return SolicitudRedaccion(
        id=solicitud.id, estado=solicitud.estado, creada_en=solicitud.creada_en
    )


@router.get(
    "/{solicitud_id}",
    response_model=VistaRedaccion,
    summary="Avance y resultado de una propuesta de redacción",
)
async def ver_redaccion(
    solicitud_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> VistaRedaccion:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None or solicitud.tipo is not TIPO:
        raise SolicitudInexistente()
    atencion: AtencionRedaccion | None = getattr(peticion.app.state, "atencion_redaccion", None)
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
    abstencion = bool(resultado and resultado.abstencion)
    detalle = {
        r.identificador_visible: (f, d)
        for r, f, d in await unidad.fragmentos_recuperados.detalle(contexto, solicitud_id)
    }
    _, parametros = await unidad.configuracion.vigente()
    original = salida.get("original")
    propuesta = salida.get("propuesta")
    palabras_original = contar_palabras(original) if isinstance(original, str) else 0

    def citas(identificadores: list[str]) -> list[CitaGuia]:
        return [
            CitaGuia(
                identificador=i,
                texto=detalle[i][0].texto,
                guia=detalle[i][1].titulo,
                apartado=detalle[i][0].seccion_original,
            )
            for i in identificadores
            if i in detalle
        ]

    return VistaRedaccion(
        id=solicitud.id,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        creada_en=solicitud.creada_en,
        entregada_en=solicitud.entregada_en,
        parrafo_id=solicitud.alcance_ref,
        abstencion=abstencion,
        aviso=AVISO_SIN_EVIDENCIA if abstencion else None,
        etiqueta=resultado.etiqueta if resultado else None,
        original=original if isinstance(original, str) else None,
        propuesta=propuesta if isinstance(propuesta, str) else None,
        palabras_original=palabras_original,
        palabras_propuesta=contar_palabras(propuesta) if isinstance(propuesta, str) else 0,
        limite_palabras_propuesta=int(palabras_original * parametros.factor_extension_d3),
        cambios=[
            CambioVista(
                tipo=c["tipo"],
                tipo_nombre=INDICADORES.get(c["tipo"], c["tipo"]),
                antes=c["antes"],
                despues=c["despues"],
                razon=c["razon"],
                citas=citas(c.get("citas", [])),
            )
            for c in salida.get("cambios", [])
            if isinstance(c, dict)
        ],
        notas_para_el_estudiante=[str(n) for n in salida.get("notas_para_el_estudiante", [])],
        advertencias=[str(a) for a in (resultado.advertencias if resultado else [])],
        comprobaciones=[ComprobacionVista(**c) for c in salida.get("comprobaciones", [])],
    )
