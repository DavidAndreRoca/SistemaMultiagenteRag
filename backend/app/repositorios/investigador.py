"""Repositorios del investigador (A2). No comparten métodos con los repositorios de caso.

Todo método exige un ``ContextoAcceso`` de rol A2.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import TipoColeccion
from app.bd.modelos import CambioNorma, Caso, Coleccion, Cuenta, Sesion
from app.repositorios.contexto import ContextoAcceso


class RepositorioColeccionesInvestigador:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def cientifica_por_tema(self, contexto: ContextoAcceso, tema: str) -> Coleccion | None:
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(
            select(Coleccion).where(
                Coleccion.tipo == TipoColeccion.CIENTIFICA, Coleccion.tema == tema
            )
        )
        return resultado.scalar_one_or_none()

    async def listar(self, contexto: ContextoAcceso) -> Sequence[Coleccion]:
        """Colecciones compartidas (guías y científicas); las personales se ven por caso."""
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(
            select(Coleccion)
            .where(Coleccion.tipo != TipoColeccion.PERSONAL)
            .order_by(Coleccion.tipo, Coleccion.tema)
        )
        return resultado.scalars().all()

    async def agregar(self, contexto: ContextoAcceso, coleccion: Coleccion) -> Coleccion:
        contexto.exigir_investigador()
        self._sesion.add(coleccion)
        await self._sesion.flush()
        return coleccion


class RepositorioCasosInvestigador:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def por_codigo(self, contexto: ContextoAcceso, codigo: str) -> Caso | None:
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(select(Caso).where(Caso.codigo == codigo))
        return resultado.scalar_one_or_none()

    async def listar(self, contexto: ContextoAcceso) -> Sequence[tuple[Caso, Coleccion]]:
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(
            select(Caso, Coleccion)
            .join(Coleccion, Coleccion.id == Caso.coleccion_cientifica_id)
            .order_by(Caso.codigo)
        )
        return [(fila[0], fila[1]) for fila in resultado.all()]

    async def coleccion_de(self, contexto: ContextoAcceso, coleccion_id: uuid.UUID) -> Coleccion:
        contexto.exigir_investigador()
        coleccion = await self._sesion.get(Coleccion, coleccion_id)
        assert coleccion is not None
        return coleccion

    async def agregar(self, contexto: ContextoAcceso, caso: Caso) -> Caso:
        contexto.exigir_investigador()
        self._sesion.add(caso)
        await self._sesion.flush()
        return caso

    async def registrar_cambio_norma(
        self, contexto: ContextoAcceso, caso: Caso, norma_anterior: str, norma_nueva: str
    ) -> CambioNorma:
        contexto.exigir_investigador()
        cambio = CambioNorma(
            caso_id=caso.id,
            norma_anterior=norma_anterior,
            norma_nueva=norma_nueva,
            cuenta_id=contexto.cuenta_id,
        )
        self._sesion.add(cambio)
        await self._sesion.flush()
        return cambio

    async def cambios_norma(self, contexto: ContextoAcceso, caso: Caso) -> Sequence[CambioNorma]:
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(
            select(CambioNorma)
            .where(CambioNorma.caso_id == caso.id)
            .order_by(CambioNorma.cambiado_en)
        )
        return resultado.scalars().all()


class RepositorioCuentasInvestigador:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def existe_codigo(self, contexto: ContextoAcceso, codigo: str) -> bool:
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(select(Cuenta.id).where(Cuenta.codigo == codigo))
        return resultado.first() is not None

    async def agregar(self, contexto: ContextoAcceso, cuenta: Cuenta) -> Cuenta:
        contexto.exigir_investigador()
        self._sesion.add(cuenta)
        await self._sesion.flush()
        return cuenta

    async def de_caso(self, contexto: ContextoAcceso, caso: Caso) -> Sequence[Cuenta]:
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(
            select(Cuenta).where(Cuenta.caso_id == caso.id).order_by(Cuenta.codigo)
        )
        return resultado.scalars().all()

    async def cerrar_sesiones_de_caso(
        self, contexto: ContextoAcceso, caso: Caso, motivo: str, ahora: datetime
    ) -> None:
        contexto.exigir_investigador()
        cuentas_del_caso = select(Cuenta.id).where(Cuenta.caso_id == caso.id)
        await self._sesion.execute(
            update(Sesion)
            .where(Sesion.cuenta_id.in_(cuentas_del_caso), Sesion.cerrada_en.is_(None))
            .values(cerrada_en=ahora, motivo_cierre=motivo)
        )
