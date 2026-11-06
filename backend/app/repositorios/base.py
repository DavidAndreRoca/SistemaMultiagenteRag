"""Repositorio genérico de datos de caso: toda consulta filtra por ``caso_id``.

No existe ningún método sin ``ContextoAcceso``: el caso se toma siempre del contexto,
nunca de un parámetro, de modo que un caso no puede leer ni escribir datos de otro.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.base import Base
from app.repositorios.contexto import ContextoAcceso


class RepositorioDeCaso[M: Base]:
    modelo: ClassVar[type[Any]]

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    def _consulta(self, contexto: ContextoAcceso) -> Select[Any]:
        caso_id = contexto.caso_exigido()
        return select(self.modelo).where(self.modelo.caso_id == caso_id)

    async def obtener(self, contexto: ContextoAcceso, id_: uuid.UUID) -> M | None:
        """Entidad del caso del contexto, o ``None`` si no existe o es de otro caso."""
        resultado = await self._sesion.execute(
            self._consulta(contexto).where(self.modelo.id == id_)
        )
        entidad: M | None = resultado.scalar_one_or_none()
        return entidad

    async def listar(self, contexto: ContextoAcceso) -> Sequence[M]:
        resultado = await self._sesion.execute(self._consulta(contexto))
        entidades: Sequence[M] = resultado.scalars().all()
        return entidades

    async def agregar(self, contexto: ContextoAcceso, entidad: M) -> M:
        """Guarda la entidad asignándole el caso del contexto (se ignora el que traiga)."""
        entidad.caso_id = contexto.caso_exigido()  # type: ignore[attr-defined]
        self._sesion.add(entidad)
        await self._sesion.flush()
        return entidad
