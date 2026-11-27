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
    AtencionPlan,
    hito_configurado,
    nombre_del_hito,
)
from app.api.estructura import CitaGuia
from app.api.evidencia import ComprobacionVista, SolicitudInexistente
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta
from app.orquestacion.en_api import ejecutor_de, encolar
from app.rag.modelos import AVISO_SIN_EVIDENCIA
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad

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
    """El ejecutor del tipo, uno por proceso (``app/orquestacion/en_api.py``)."""
    ejecutor: AtencionPlan = await ejecutor_de(peticion, unidad, TIPO)
    return ejecutor


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
    pedido: PedidoPlan,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    atencion: AtencionDep,
) -> SolicitudPlan:
    solicitud = await atencion.iniciar(unidad, contexto, pedido.hito)
    encolar(peticion, solicitud, contexto)
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
