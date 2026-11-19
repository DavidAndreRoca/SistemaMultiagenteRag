"""Repositorios de datos de caso (A1). Comparten solo la base con filtro por caso."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.bd.enumeraciones import TipoColeccion
from app.bd.modelos import (
    Caso,
    Coleccion,
    Decision,
    FragmentoRecuperado,
    FuenteAportada,
    Resultado,
    Solicitud,
    Verificacion,
    VersionBorrador,
)
from app.repositorios.base import RepositorioDeCaso
from app.repositorios.contexto import ContextoAcceso


class RepositorioVersiones(RepositorioDeCaso[VersionBorrador]):
    modelo = VersionBorrador

    async def vigente_del_hito(self, contexto: ContextoAcceso, hito: str) -> VersionBorrador | None:
        resultado = await self._sesion.execute(
            self._consulta(contexto).where(VersionBorrador.hito == hito, VersionBorrador.vigente)
        )
        vigente: VersionBorrador | None = resultado.scalar_one_or_none()
        return vigente

    async def con_parrafos(
        self, contexto: ContextoAcceso, version_id: uuid.UUID
    ) -> VersionBorrador | None:
        """Versión del caso con sus párrafos (columna de carga diferida)."""
        resultado = await self._sesion.execute(
            self._consulta(contexto)
            .where(VersionBorrador.id == version_id)
            .options(undefer(VersionBorrador.parrafos))
        )
        version: VersionBorrador | None = resultado.scalar_one_or_none()
        return version

    async def recientes(
        self, contexto: ContextoAcceso, hito: str | None = None
    ) -> Sequence[VersionBorrador]:
        """Versiones del caso, de la más reciente a la más antigua (sin cargar el texto)."""
        consulta = self._consulta(contexto).order_by(
            VersionBorrador.cargada_en.desc(), VersionBorrador.id.desc()
        )
        if hito is not None:
            consulta = consulta.where(VersionBorrador.hito == hito)
        resultado = await self._sesion.execute(consulta)
        versiones: Sequence[VersionBorrador] = resultado.scalars().all()
        return versiones

    async def registrar_vigente(
        self, contexto: ContextoAcceso, nueva: VersionBorrador
    ) -> VersionBorrador | None:
        """Guarda la nueva versión como vigente de su hito y devuelve la que lo era.

        Bloquea la fila del caso: dos cargas simultáneas del mismo caso se ordenan en lugar
        de chocar con el índice único de la versión vigente (decisión T11-01, apartado 4).
        """
        caso_id = contexto.caso_exigido()
        await self._sesion.execute(select(Caso.id).where(Caso.id == caso_id).with_for_update())
        anterior = await self.vigente_del_hito(contexto, nueva.hito)
        if anterior is not None:
            await self._sesion.execute(
                update(VersionBorrador)
                .where(VersionBorrador.caso_id == caso_id, VersionBorrador.id == anterior.id)
                .values(vigente=False)
                .execution_options(synchronize_session="fetch")
            )
        nueva.vigente = True
        await self.agregar(contexto, nueva)
        return anterior


class RepositorioSolicitudes(RepositorioDeCaso[Solicitud]):
    modelo = Solicitud


class RepositorioFragmentosRecuperados(RepositorioDeCaso[FragmentoRecuperado]):
    modelo = FragmentoRecuperado


class RepositorioResultados(RepositorioDeCaso[Resultado]):
    modelo = Resultado


class RepositorioVerificaciones(RepositorioDeCaso[Verificacion]):
    modelo = Verificacion


class RepositorioDecisiones(RepositorioDeCaso[Decision]):
    modelo = Decision


class RepositorioFuentesAportadas(RepositorioDeCaso[FuenteAportada]):
    modelo = FuenteAportada


class RepositorioCasoPropio:
    """El propio caso del contexto: datos visibles para el caso."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener(self, contexto: ContextoAcceso) -> tuple[Caso, Coleccion] | None:
        """Caso del contexto con su colección científica."""
        caso_id = contexto.caso_exigido()
        resultado = await self._sesion.execute(
            select(Caso, Coleccion)
            .join(Coleccion, Coleccion.id == Caso.coleccion_cientifica_id)
            .where(Caso.id == caso_id)
        )
        fila = resultado.first()
        return (fila[0], fila[1]) if fila else None

    async def coleccion_personal(self, contexto: ContextoAcceso) -> Coleccion | None:
        caso_id = contexto.caso_exigido()
        resultado = await self._sesion.execute(
            select(Coleccion).where(
                Coleccion.tipo == TipoColeccion.PERSONAL, Coleccion.caso_id == caso_id
            )
        )
        return resultado.scalar_one_or_none()
