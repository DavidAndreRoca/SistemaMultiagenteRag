"""Repositorio del evaluador de la recuperación (A2, T16).

``python -m app.rag.evaluar`` trabaja en una transacción que siempre se revierte: el caso
transitorio que crea aquí nunca llega a la base.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import TipoAutoria, TipoColeccion
from app.bd.modelos import Caso, Coleccion, Documento
from app.repositorios.contexto import ContextoAcceso


class RepositorioEvaluacion:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def coleccion_del_tema(self, contexto: ContextoAcceso, tema: str) -> Coleccion | None:
        contexto.exigir_investigador()
        return await self._sesion.scalar(
            select(Coleccion).where(
                Coleccion.tipo == TipoColeccion.CIENTIFICA, Coleccion.tema == tema
            )
        )

    async def caso_transitorio(self, contexto: ContextoAcceso, coleccion: Coleccion) -> Caso:
        """Un caso sin cuenta ni datos, solo para recuperar por el camino de un agente."""
        contexto.exigir_investigador()
        caso = Caso(
            codigo=f"EVAL-{uuid.uuid4().hex[:8].upper()}",
            tipo_autoria=TipoAutoria.INDIVIDUAL,
            coleccion_cientifica_id=coleccion.id,
        )
        self._sesion.add(caso)
        await self._sesion.flush()
        return caso

    async def dois(
        self, contexto: ContextoAcceso, ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, str | None]:
        contexto.exigir_investigador()
        if not ids:
            return {}
        filas = await self._sesion.execute(
            select(Documento.id, Documento.doi).where(Documento.id.in_(list(ids)))
        )
        return {i: d for i, d in filas.all()}

    async def revertir(self) -> None:
        await self._sesion.rollback()

    async def estados_oa(
        self, contexto: ContextoAcceso, ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        """Estado de acceso abierto de cada documento (evaluador de D4, T19)."""
        contexto.exigir_investigador()
        if not ids:
            return {}
        filas = await self._sesion.execute(
            select(Documento.id, Documento.estado_oa).where(Documento.id.in_(list(ids)))
        )
        return {i: e.value for i, e in filas.all()}
