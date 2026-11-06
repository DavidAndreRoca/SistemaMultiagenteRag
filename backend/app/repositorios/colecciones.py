"""Colecciones que cada tipo de solicitud puede consultar (RN-03, Fase 1, tabla de colecciones).

* D1, D2 y D3 (revision_estructura, plan_tarea, revision_metodologica, propuesta_redaccion):
  ``guias``.
* busqueda_evidencia (D4): ``cientifica`` del tema del caso y ``personal`` del caso.
* verificacion_referencias (D4): ninguna colección.

La recuperación (T16) recibe el contexto y el tipo, nunca una colección.
"""

from __future__ import annotations

import uuid
from typing import Final

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import TipoColeccion, TipoSolicitud
from app.bd.modelos import Caso, Coleccion
from app.repositorios.contexto import ContextoAcceso

TIPOS_DE_COLECCION_POR_SOLICITUD: Final[dict[TipoSolicitud, frozenset[TipoColeccion]]] = {
    TipoSolicitud.REVISION_ESTRUCTURA: frozenset({TipoColeccion.GUIAS}),
    TipoSolicitud.PLAN_TAREA: frozenset({TipoColeccion.GUIAS}),
    TipoSolicitud.REVISION_METODOLOGICA: frozenset({TipoColeccion.GUIAS}),
    TipoSolicitud.PROPUESTA_REDACCION: frozenset({TipoColeccion.GUIAS}),
    TipoSolicitud.BUSQUEDA_EVIDENCIA: frozenset({TipoColeccion.CIENTIFICA, TipoColeccion.PERSONAL}),
    TipoSolicitud.VERIFICACION_REFERENCIAS: frozenset(),
}


async def colecciones_permitidas(
    sesion: AsyncSession, tipo: TipoSolicitud, contexto: ContextoAcceso
) -> list[uuid.UUID]:
    """Identificadores de las colecciones que el caso del contexto puede consultar para ``tipo``."""
    caso_id = contexto.caso_exigido()
    tipos = TIPOS_DE_COLECCION_POR_SOLICITUD[tipo]
    if not tipos:
        return []

    condiciones = []
    if TipoColeccion.GUIAS in tipos:
        condiciones.append(Coleccion.tipo == TipoColeccion.GUIAS)
    if TipoColeccion.CIENTIFICA in tipos:
        cientifica_del_caso = select(Caso.coleccion_cientifica_id).where(Caso.id == caso_id)
        condiciones.append(
            (Coleccion.tipo == TipoColeccion.CIENTIFICA)
            & Coleccion.id.in_(cientifica_del_caso.scalar_subquery())
        )
    if TipoColeccion.PERSONAL in tipos:
        condiciones.append(
            (Coleccion.tipo == TipoColeccion.PERSONAL) & (Coleccion.caso_id == caso_id)
        )

    resultado = await sesion.execute(
        select(Coleccion.id).where(or_(*condiciones)).order_by(Coleccion.tipo)
    )
    return list(resultado.scalars().all())


class RepositorioColecciones:
    """Acceso a ``colecciones_permitidas`` desde la unidad de trabajo."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def permitidas(self, tipo: TipoSolicitud, contexto: ContextoAcceso) -> list[uuid.UUID]:
        return await colecciones_permitidas(self._sesion, tipo, contexto)
