"""Repositorios del investigador (A2). No comparten métodos con los repositorios de caso.

Todo método exige un ``ContextoAcceso`` de rol A2.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import EstadoSolicitud, TipoColeccion
from app.bd.modelos import (
    CambioNorma,
    Caso,
    Coleccion,
    Cuenta,
    EventoTecnico,
    Sesion,
    Solicitud,
)
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.tiempos import TiemposSolicitud


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

    async def guias(self, contexto: ContextoAcceso) -> Coleccion | None:
        """La colección de guías, única y compartida (T22)."""
        contexto.exigir_investigador()
        resultado = await self._sesion.execute(
            select(Coleccion).where(Coleccion.tipo == TipoColeccion.GUIAS).limit(1)
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


class RepositorioMonitoreo:
    """Latencias de las solicitudes entregadas (T30; RNF-12). Solo duraciones y tipos: ningún
    contenido de los casos. A2."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def tiempos(
        self, contexto: ContextoAcceso, desde: datetime | None = None
    ) -> list[TiemposSolicitud]:
        contexto.exigir_investigador()
        consulta = (
            select(
                Solicitud.id,
                Solicitud.tipo,
                Solicitud.creada_en,
                Solicitud.entregada_en,
                EventoTecnico.etapa,
                EventoTecnico.duracion_ms,
            )
            .join(EventoTecnico, EventoTecnico.solicitud_id == Solicitud.id)
            .where(
                Solicitud.estado == EstadoSolicitud.ENTREGADA,
                Solicitud.entregada_en.is_not(None),
            )
        )
        if desde is not None:
            consulta = consulta.where(Solicitud.creada_en >= desde)
        por_solicitud: dict[uuid.UUID, TiemposSolicitud] = {}
        for fila in (await self._sesion.execute(consulta)).all():
            actual = por_solicitud.get(fila.id)
            if actual is None:
                total = round((fila.entregada_en - fila.creada_en).total_seconds() * 1000)
                actual = TiemposSolicitud(fila.tipo, max(total, 0), {})
                por_solicitud[fila.id] = actual
            actual.etapas[fila.etapa] = actual.etapas.get(fila.etapa, 0) + fila.duracion_ms
        return list(por_solicitud.values())
