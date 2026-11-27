"""Rutas del caso (A1). Toda lectura usa el contexto de la sesión.

``GET /caso/solicitudes`` lista las búsquedas de evidencia y las verificaciones de
referencias del caso para volver a abrir su resultado (prototipo, 26-11-2026; versión
reducida del historial de T33).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.bd.enumeraciones import EstadoSolicitud, TipoAutoria, TipoSolicitud
from app.casos.servicio import CasoInexistente
from app.seguridad.dependencias import ContextoCaso, Unidad

router = APIRouter(prefix="/caso", tags=["caso"])


class HitoVista(BaseModel):
    orden: int
    codigo: str
    nombre: str
    contenido: str


class CasoPropio(BaseModel):
    codigo: str
    tipo_autoria: TipoAutoria
    tema: str
    norma_citacion: str
    # Catálogo de hitos de la configuración vigente: la interfaz los ofrece al cargar (T13).
    hitos: list[HitoVista]


@router.get("", response_model=CasoPropio, summary="Datos del propio caso")
async def caso_propio(contexto: ContextoCaso, unidad: Unidad) -> CasoPropio:
    encontrado = await unidad.caso_propio.obtener(contexto)
    if encontrado is None:
        raise CasoInexistente()
    caso, coleccion = encontrado
    _, parametros = await unidad.configuracion.vigente()
    return CasoPropio(
        codigo=caso.codigo,
        tipo_autoria=caso.tipo_autoria,
        tema=coleccion.tema or "",
        norma_citacion=caso.norma_citacion,
        hitos=[HitoVista.model_validate(h.model_dump()) for h in parametros.hitos],
    )


TIPOS_CON_PANTALLA = (
    TipoSolicitud.BUSQUEDA_EVIDENCIA,
    TipoSolicitud.VERIFICACION_REFERENCIAS,
    TipoSolicitud.REVISION_ESTRUCTURA,
    TipoSolicitud.PROPUESTA_REDACCION,
    TipoSolicitud.REVISION_METODOLOGICA,
    TipoSolicitud.PLAN_TAREA,
)


class SolicitudResumen(BaseModel):
    id: uuid.UUID
    tipo: TipoSolicitud
    estado: EstadoSolicitud
    consulta: str | None  # la del estudiante, en las búsquedas de evidencia
    creada_en: datetime
    entregada_en: datetime | None
    solicitud_origen_id: uuid.UUID | None  # si es el reenvío de una no atendida (T29)


@router.get(
    "/solicitudes",
    response_model=list[SolicitudResumen],
    summary="Búsquedas de evidencia y verificaciones de referencias del caso",
)
async def solicitudes_del_caso(contexto: ContextoCaso, unidad: Unidad) -> list[SolicitudResumen]:
    return [
        SolicitudResumen(
            id=s.id,
            tipo=s.tipo,
            estado=s.estado,
            consulta=s.alcance_ref if s.tipo is TipoSolicitud.BUSQUEDA_EVIDENCIA else None,
            creada_en=s.creada_en,
            entregada_en=s.entregada_en,
            solicitud_origen_id=s.solicitud_origen_id,
        )
        for s in await unidad.solicitudes.recientes(contexto, TIPOS_CON_PANTALLA)
    ]
