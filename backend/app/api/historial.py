"""Historial del caso y resumen descargable (T33; RF-14, CU-13, HU-12, CP-20).

* ``GET /caso/historial``: versiones, solicitudes, resultados con su etiqueta, decisiones y
  fuentes aportadas, en orden cronológico; filtros por hito y por periodo (fechas de Lima,
  ``desde`` y ``hasta`` inclusive).
* ``GET /caso/historial/resumen``: el mismo historial como texto plano para la declaración
  de herramientas, con los mismos filtros.

Todo se lee con el caso del contexto (4.5): el historial de un caso no muestra nada de otro.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.casos.servicio import CasoInexistente
from app.comun.errores import ErrorAplicacion
from app.registro.historial import (
    EventoHistorial,
    Filtro,
    armar_historial,
    modelos_usados,
    resumen_para_declaracion,
)
from app.repositorios.contexto import ContextoAcceso
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad

router = APIRouter(prefix="/caso/historial", tags=["historial"])

HitoQuery = Annotated[str | None, Query(max_length=40, description="Código del hito.")]
FechaQuery = Annotated[date | None, Query(description="Fecha de Lima, AAAA-MM-DD.")]


class PeriodoInvalido(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "periodo_invalido",
            "La fecha inicial del periodo es posterior a la final.",
            estado_http=422,
        )


class Historial(BaseModel):
    eventos: list[EventoHistorial]


def _filtro(hito: str | None, desde: date | None, hasta: date | None) -> Filtro:
    if desde is not None and hasta is not None and desde > hasta:
        raise PeriodoInvalido()
    return Filtro(hito=hito or None, desde=desde, hasta=hasta)


async def _eventos(
    unidad: Unidad, contexto: ContextoAcceso, filtro: Filtro
) -> tuple[list[EventoHistorial], list[str]]:
    _, parametros = await unidad.configuracion.vigente()
    resultados = await unidad.resultados.listar(contexto)
    eventos = armar_historial(
        versiones=await unidad.versiones.recientes(contexto),
        solicitudes=await unidad.solicitudes.listar(contexto),
        resultados=resultados,
        decisiones=await unidad.decisiones.listar(contexto),
        aportes=await unidad.fuentes_aportadas.listar(contexto),
        nombres_hito={h.codigo: h.nombre for h in parametros.hitos},
        filtro=filtro,
    )
    solicitudes = {e.solicitud_id for e in eventos if e.solicitud_id is not None}
    return eventos, modelos_usados(r for r in resultados if r.solicitud_id in solicitudes)


@router.get("", response_model=Historial, summary="Historial cronológico del caso")
async def historial(
    contexto: ContextoCaso,
    unidad: Unidad,
    hito: HitoQuery = None,
    desde: FechaQuery = None,
    hasta: FechaQuery = None,
) -> Historial:
    eventos, _ = await _eventos(unidad, contexto, _filtro(hito, desde, hasta))
    return Historial(eventos=eventos)


@router.get(
    "/resumen",
    response_class=PlainTextResponse,
    summary="Resumen del historial para la declaración de herramientas",
    responses={200: {"content": {"text/plain": {}}}},
)
async def resumen(
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
    hito: HitoQuery = None,
    desde: FechaQuery = None,
    hasta: FechaQuery = None,
) -> PlainTextResponse:
    filtro = _filtro(hito, desde, hasta)
    encontrado = await unidad.caso_propio.obtener(contexto)
    if encontrado is None:
        raise CasoInexistente()
    caso, coleccion = encontrado
    eventos, modelos = await _eventos(unidad, contexto, filtro)
    texto = resumen_para_declaracion(
        codigo=caso.codigo,
        tema=coleccion.tema or "",
        eventos=eventos,
        modelos=modelos,
        filtro=filtro,
        generado_en=reloj(),
    )
    return PlainTextResponse(
        texto,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="resumen-de-uso-{caso.codigo}.txt"',
            "Cache-Control": "no-store",
        },
    )
