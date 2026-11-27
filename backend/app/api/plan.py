"""Rutas del caso para el plan de tarea del hito (T24; RF-05, CU-04).

* ``GET /caso/plan/hitos``: los hitos del programa, con la fecha de la versión vigente de
  cada uno, si la hay.
* ``POST /caso/plan``: pide el plan del hito de una versión vigente; responde 202 y el
  trabajo sigue en segundo plano.
* ``GET /caso/plan/{id}``: avance y resultado, con las tareas en orden, su criterio de
  logro y la instrucción del programa desplegable. Si el corpus no tiene instrucciones del
  hito, la solicitud se entrega como abstención, con su motivo.

El plan no modifica el borrador. Una solicitud de otro caso responde 404 (4.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.agentes.plan import (
    TIPO,
    AgentePlan,
    AtencionPlan,
    hito_configurado,
    nombre_del_hito,
)
from app.api.estructura import CitaGuia
from app.api.evidencia import ComprobacionVista, SolicitudInexistente
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta
from app.configuracion import Ajustes
from app.corpus.fabrica import CorpusNoConfigurado
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.rag.modelos import AVISO_SIN_EVIDENCIA
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoCaso, Reloj, RelojDep, Unidad, obtener_reloj

router = APIRouter(prefix="/caso/plan", tags=["plan"])


class HitoDelPlan(BaseModel):
    codigo: str
    nombre: str
    version_cargada_en: datetime | None


class PedidoPlan(BaseModel):
    hito: str = Field(min_length=1, max_length=40)


class SolicitudPlan(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    creada_en: datetime


class TareaVista(BaseModel):
    orden: int
    tarea: str
    criterio_de_logro: str
    citas: list[CitaGuia]


class VistaPlan(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    entregada_en: datetime | None
    hito: str | None
    abstencion: bool
    aviso: str | None
    motivo_abstencion: str | None
    etiqueta: Etiqueta | None
    tareas: list[TareaVista]
    notas_para_el_estudiante: list[str]
    advertencias: list[str]
    comprobaciones: list[ComprobacionVista]


async def obtener_atencion(peticion: Request, unidad: Unidad) -> AtencionPlan:
    """Una por proceso; usa el servicio de modelos y el adaptador."""
    estado = peticion.app.state
    actual: AtencionPlan | None = getattr(estado, "atencion_plan", None)
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
    actual = AtencionPlan(TIPO, AgentePlan(evidencia, cadena), abrir, reloj)
    estado.atencion_plan = actual
    return actual


AtencionDep = Annotated[AtencionPlan, Depends(obtener_atencion)]


@router.get(
    "/hitos",
    response_model=list[HitoDelPlan],
    summary="Hitos del programa, con la versión vigente de cada uno si la hay",
)
async def hitos(contexto: ContextoCaso, unidad: Unidad) -> list[HitoDelPlan]:
    _, parametros = await unidad.configuracion.vigente()
    resultado = []
    for hito in sorted(parametros.hitos, key=lambda h: h.orden):
        version = await unidad.versiones.vigente_del_hito(contexto, hito.codigo)
        resultado.append(
            HitoDelPlan(
                codigo=hito.codigo,
                nombre=nombre_del_hito(hito),
                version_cargada_en=version.cargada_en if version else None,
            )
        )
    return resultado


@router.post(
    "",
    response_model=SolicitudPlan,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}, 503: {}},
    summary="Pedir el plan de tarea del hito de una versión vigente",
)
async def pedir_plan(
    pedido: PedidoPlan, contexto: ContextoCaso, unidad: Unidad, atencion: AtencionDep
) -> SolicitudPlan:
    solicitud = await atencion.iniciar(unidad, contexto, pedido.hito)
    atencion.lanzar(solicitud, contexto)
    return SolicitudPlan(id=solicitud.id, estado=solicitud.estado, creada_en=solicitud.creada_en)


@router.get(
    "/{solicitud_id}",
    response_model=VistaPlan,
    summary="Avance y resultado de un plan de tarea",
)
async def ver_plan(
    solicitud_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> VistaPlan:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None or solicitud.tipo is not TIPO:
        raise SolicitudInexistente()
    atencion: AtencionPlan | None = getattr(peticion.app.state, "atencion_plan", None)
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
    _, parametros = await unidad.configuracion.vigente()
    version = await unidad.versiones.con_parrafos(contexto, solicitud.version_id)
    hito = hito_configurado(parametros, version.hito) if version else None
    resultado = await unidad.resultados.de_solicitud(contexto, solicitud_id)
    salida: dict[str, Any] = (resultado.salida or {}) if resultado else {}
    abstencion = bool(resultado and resultado.abstencion)
    detalle = {
        r.identificador_visible: (f, d)
        for r, f, d in await unidad.fragmentos_recuperados.detalle(contexto, solicitud_id)
    }

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

    return VistaPlan(
        id=solicitud.id,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        creada_en=solicitud.creada_en,
        entregada_en=solicitud.entregada_en,
        hito=str(salida.get("hito") or (nombre_del_hito(hito) if hito else "")) or None,
        abstencion=abstencion,
        aviso=AVISO_SIN_EVIDENCIA if abstencion else None,
        motivo_abstencion=str(salida.get("motivo"))
        if abstencion and salida.get("motivo")
        else None,
        etiqueta=resultado.etiqueta if resultado else None,
        tareas=[
            TareaVista(
                orden=int(t.get("orden", i)),
                tarea=str(t.get("tarea", "")),
                criterio_de_logro=str(t.get("criterio_de_logro", "")),
                citas=citas(t.get("citas", [])),
            )
            for i, t in enumerate(salida.get("tareas", []), 1)
            if isinstance(t, dict)
        ],
        notas_para_el_estudiante=[str(n) for n in salida.get("notas_para_el_estudiante", [])],
        advertencias=[str(a) for a in (resultado.advertencias if resultado else [])],
        comprobaciones=[ComprobacionVista(**c) for c in salida.get("comprobaciones", [])],
    )
