"""Rutas del caso (A1). Toda lectura usa el contexto de la sesión."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.bd.enumeraciones import TipoAutoria
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
