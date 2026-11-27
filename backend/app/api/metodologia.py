"""Rutas del caso para el diagnóstico metodológico de una sección (T26; RF-06, CU-05, CP-08).

* ``GET /caso/metodologia/secciones``: secciones revisables de la versión vigente, con el
  diseño que nombra cada una (si lo nombra).
* ``POST /caso/metodologia``: pide el diagnóstico de una sección; responde 202 y el trabajo
  sigue en segundo plano.
* ``GET /caso/metodologia/{id}``: avance y resultado, con los hallazgos de mayor a menor
  severidad, las preguntas al estudiante y cada criterio desplegable a su guía.

Una solicitud de otro caso responde 404, igual que una inexistente (4.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.agentes.metodologia import (
    TIPO,
    AtencionMetodologia,
    identificar_diseno,
)
from app.agentes.seccion import alcance_de_seccion, secciones_revisables
from app.api.estructura import CitaGuia, HallazgoVista
from app.api.evidencia import ComprobacionVista, SolicitudInexistente
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta
from app.orquestacion.en_api import ejecutor_de, encolar
from app.rag.modelos import AVISO_SIN_EVIDENCIA
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad

router = APIRouter(prefix="/caso/metodologia", tags=["metodologia"])
INDICADORES = {
    "justificacion_del_diseno": "Justificación del diseño",
    "validez_de_tecnicas_e_instrumentos": "Validez de técnicas e instrumentos",
    "precision_del_analisis_de_datos": "Precisión del análisis de datos",
}


class SeccionMetodologica(BaseModel):
    id: str
    titulo: str
    palabras: int
    diseno: str | None


class PedidoMetodologia(BaseModel):
    seccion_id: str = Field(min_length=1, max_length=40)


class SolicitudMetodologia(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    creada_en: datetime


class VistaMetodologia(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    entregada_en: datetime | None
    seccion_id: str | None
    seccion_titulo: str | None
    diseno: str | None
    abstencion: bool
    aviso: str | None
    etiqueta: Etiqueta | None
    hallazgos: list[HallazgoVista]
    preguntas_al_estudiante: list[str]
    notas_para_el_estudiante: list[str]
    advertencias: list[str]
    comprobaciones: list[ComprobacionVista]


async def obtener_atencion(peticion: Request, unidad: Unidad) -> AtencionMetodologia:
    """El ejecutor del tipo, uno por proceso (``app/orquestacion/en_api.py``)."""
    ejecutor: AtencionMetodologia = await ejecutor_de(peticion, unidad, TIPO)
    return ejecutor


AtencionDep = Annotated[AtencionMetodologia, Depends(obtener_atencion)]


@router.get(
    "/secciones",
    response_model=list[SeccionMetodologica],
    summary="Secciones de la versión vigente, con el diseño que nombra cada una",
)
async def secciones(contexto: ContextoCaso, unidad: Unidad) -> list[SeccionMetodologica]:
    version = await unidad.versiones.vigente_mas_reciente(contexto)
    if version is None:
        return []
    completa = await unidad.versiones.con_parrafos(contexto, version.id)
    assert completa is not None
    resultado = []
    for i, titulo, palabras in secciones_revisables(completa):
        diseno = identificar_diseno(alcance_de_seccion(completa, i)[1])
        resultado.append(
            SeccionMetodologica(
                id=i, titulo=titulo, palabras=palabras, diseno=diseno.value if diseno else None
            )
        )
    return resultado


@router.post(
    "",
    response_model=SolicitudMetodologia,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}, 503: {}},
    summary="Pedir el diagnóstico metodológico de una sección",
)
async def pedir_metodologia(
    pedido: PedidoMetodologia,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    atencion: AtencionDep,
) -> SolicitudMetodologia:
    solicitud = await atencion.iniciar(unidad, contexto, pedido.seccion_id)
    encolar(peticion, solicitud, contexto)
    return SolicitudMetodologia(
        id=solicitud.id, estado=solicitud.estado, creada_en=solicitud.creada_en
    )


@router.get(
    "/{solicitud_id}",
    response_model=VistaMetodologia,
    summary="Avance y resultado de un diagnóstico metodológico",
)
async def ver_metodologia(
    solicitud_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> VistaMetodologia:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None or solicitud.tipo is not TIPO:
        raise SolicitudInexistente()
    titulo: str | None = None
    diseno: str | None = None
    version = await unidad.versiones.con_parrafos(contexto, solicitud.version_id)
    if version is not None and solicitud.alcance_ref:
        try:
            titulo, texto = alcance_de_seccion(version, solicitud.alcance_ref)
            identificado = identificar_diseno(texto)
            diseno = identificado.value if identificado else None
        except Exception:  # la versión ya no tiene esa sección: se muestra sin título
            titulo = None
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

    return VistaMetodologia(
        id=solicitud.id,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        creada_en=solicitud.creada_en,
        entregada_en=solicitud.entregada_en,
        seccion_id=solicitud.alcance_ref,
        seccion_titulo=titulo,
        diseno=diseno,
        abstencion=abstencion,
        aviso=AVISO_SIN_EVIDENCIA if abstencion else None,
        etiqueta=resultado.etiqueta if resultado else None,
        hallazgos=[
            HallazgoVista(
                indicador=h["indicador"],
                indicador_nombre=INDICADORES.get(h["indicador"], h["indicador"]),
                ubicacion=h["ubicacion"],
                descripcion=h["descripcion"],
                severidad=h["severidad"],
                recomendacion=h["recomendacion"],
                citas=citas(h.get("citas", [])),
            )
            for h in salida.get("hallazgos", [])
            if isinstance(h, dict)
        ],
        preguntas_al_estudiante=[str(p) for p in salida.get("preguntas_al_estudiante", [])],
        notas_para_el_estudiante=[str(n) for n in salida.get("notas_para_el_estudiante", [])],
        advertencias=[str(a) for a in (resultado.advertencias if resultado else [])],
        comprobaciones=[ComprobacionVista(**c) for c in salida.get("comprobaciones", [])],
    )
