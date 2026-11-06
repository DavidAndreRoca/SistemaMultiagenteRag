"""Repositorio de autenticación: cuentas y sesiones antes de que exista un contexto.

Es la frontera que produce el ``ContextoAcceso``; no lee datos de caso.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import EstadoCaso
from app.bd.modelos import Caso, Cuenta, Sesion


class RepositorioAutenticacion:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def cuenta_por_codigo(self, codigo: str) -> Cuenta | None:
        resultado = await self._sesion.execute(select(Cuenta).where(Cuenta.codigo == codigo))
        return resultado.scalar_one_or_none()

    async def cuenta_por_id(self, cuenta_id: uuid.UUID) -> Cuenta | None:
        return await self._sesion.get(Cuenta, cuenta_id)

    async def caso_habilitado(self, caso_id: uuid.UUID) -> bool:
        resultado = await self._sesion.execute(select(Caso.estado).where(Caso.id == caso_id))
        return resultado.scalar_one_or_none() is EstadoCaso.HABILITADO

    async def agregar_cuenta(self, cuenta: Cuenta) -> Cuenta:
        """Solo para el alta inicial del investigador (comando de línea)."""
        self._sesion.add(cuenta)
        await self._sesion.flush()
        return cuenta

    async def sesion_por_huella(self, huella: str) -> Sesion | None:
        resultado = await self._sesion.execute(select(Sesion).where(Sesion.huella_token == huella))
        return resultado.scalar_one_or_none()

    async def sesiones_abiertas(self, cuenta_id: uuid.UUID) -> Sequence[Sesion]:
        resultado = await self._sesion.execute(
            select(Sesion)
            .where(Sesion.cuenta_id == cuenta_id, Sesion.cerrada_en.is_(None))
            .order_by(Sesion.creada_en, Sesion.id)
        )
        return resultado.scalars().all()

    async def agregar_sesion(self, sesion: Sesion) -> Sesion:
        self._sesion.add(sesion)
        await self._sesion.flush()
        return sesion

    async def cerrar_otras_sesiones(
        self, cuenta_id: uuid.UUID, conservar: uuid.UUID, ahora: datetime, motivo: str
    ) -> None:
        await self._sesion.execute(
            update(Sesion)
            .where(
                Sesion.cuenta_id == cuenta_id,
                Sesion.cerrada_en.is_(None),
                Sesion.id != conservar,
            )
            .values(cerrada_en=ahora, motivo_cierre=motivo)
        )
