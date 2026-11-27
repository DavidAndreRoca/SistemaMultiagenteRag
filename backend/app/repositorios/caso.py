"""Repositorios de datos de caso (A1). Comparten solo la base con filtro por caso."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.bd.enumeraciones import EstadoSolicitud, TipoColeccion, TipoSolicitud
from app.bd.modelos import (
    Caso,
    Coleccion,
    Decision,
    Documento,
    Fragmento,
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

    async def vigente_mas_reciente(self, contexto: ContextoAcceso) -> VersionBorrador | None:
        """La versión vigente cargada más recientemente, de cualquier hito (T19)."""
        resultado = await self._sesion.execute(
            self._consulta(contexto)
            .where(VersionBorrador.vigente)
            .order_by(VersionBorrador.cargada_en.desc())
            .limit(1)
        )
        version: VersionBorrador | None = resultado.scalar_one_or_none()
        return version

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

    async def hay_de_version(self, contexto: ContextoAcceso, version_id: uuid.UUID) -> bool:
        """Alguna solicitud del caso usa la versión (sus ids de sección y párrafo)."""
        resultado = await self._sesion.execute(
            self._consulta(contexto).where(Solicitud.version_id == version_id).limit(1)
        )
        return resultado.first() is not None

    async def recientes(
        self, contexto: ContextoAcceso, tipos: Sequence[TipoSolicitud], limite: int = 30
    ) -> Sequence[Solicitud]:
        """Las solicitudes del caso de esos tipos, de la más reciente a la más antigua, sin las
        rechazadas por la validación previa (no tienen resultado)."""
        resultado = await self._sesion.scalars(
            self._consulta(contexto)
            .where(Solicitud.tipo.in_(list(tipos)), Solicitud.estado != EstadoSolicitud.RECHAZADA)
            .order_by(Solicitud.creada_en.desc(), Solicitud.id)
            .limit(limite)
        )
        return resultado.all()


class RepositorioFragmentosRecuperados(RepositorioDeCaso[FragmentoRecuperado]):
    modelo = FragmentoRecuperado

    async def borrar_de_solicitud(self, contexto: ContextoAcceso, solicitud_id: uuid.UUID) -> None:
        """Antes de reintentar una solicitud cortada (T28): lo que dejó el intento anterior."""
        await self._sesion.execute(
            delete(FragmentoRecuperado).where(
                FragmentoRecuperado.caso_id == contexto.caso_exigido(),
                FragmentoRecuperado.solicitud_id == solicitud_id,
            )
        )

    async def identificadores(self, contexto: ContextoAcceso, solicitud_id: uuid.UUID) -> set[str]:
        """``F1`` a ``Fn`` recuperados para una solicitud del caso (comprobación 3, T18)."""
        resultado = await self._sesion.execute(
            select(FragmentoRecuperado.identificador_visible).where(
                FragmentoRecuperado.caso_id == contexto.caso_exigido(),
                FragmentoRecuperado.solicitud_id == solicitud_id,
            )
        )
        return set(resultado.scalars().all())

    async def documentos_citados(
        self, contexto: ContextoAcceso, solicitud_id: uuid.UUID, identificadores: Sequence[str]
    ) -> list[tuple[str, Documento]]:
        """El documento de cada identificador citado, en el orden pedido (T18)."""
        if not identificadores:
            return []
        resultado = await self._sesion.execute(
            select(FragmentoRecuperado.identificador_visible, Documento)
            .join(Fragmento, Fragmento.id == FragmentoRecuperado.fragmento_id)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                FragmentoRecuperado.caso_id == contexto.caso_exigido(),
                FragmentoRecuperado.solicitud_id == solicitud_id,
                FragmentoRecuperado.identificador_visible.in_(list(identificadores)),
            )
        )
        por_identificador = {i: d for i, d in resultado.all()}
        return [(i, por_identificador[i]) for i in identificadores if i in por_identificador]

    async def detalle(
        self, contexto: ContextoAcceso, solicitud_id: uuid.UUID
    ) -> list[tuple[FragmentoRecuperado, Fragmento, Documento]]:
        """Los fragmentos recuperados de la solicitud con su documento, en orden (T19)."""
        resultado = await self._sesion.execute(
            select(FragmentoRecuperado, Fragmento, Documento)
            .join(Fragmento, Fragmento.id == FragmentoRecuperado.fragmento_id)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                FragmentoRecuperado.caso_id == contexto.caso_exigido(),
                FragmentoRecuperado.solicitud_id == solicitud_id,
            )
            .order_by(FragmentoRecuperado.posicion)
        )
        return [(r, f, d) for r, f, d in resultado.all()]


class RepositorioResultados(RepositorioDeCaso[Resultado]):
    modelo = Resultado

    async def borrar_de_solicitud(self, contexto: ContextoAcceso, solicitud_id: uuid.UUID) -> None:
        """Antes de reintentar una solicitud cortada (T28): lo que dejó el intento anterior."""
        await self._sesion.execute(
            delete(Resultado).where(
                Resultado.caso_id == contexto.caso_exigido(), Resultado.solicitud_id == solicitud_id
            )
        )

    async def de_solicitud(
        self, contexto: ContextoAcceso, solicitud_id: uuid.UUID
    ) -> Resultado | None:
        """El último intento de la solicitud del caso (T19)."""
        resultado = await self._sesion.execute(
            self._consulta(contexto)
            .where(Resultado.solicitud_id == solicitud_id)
            .order_by(Resultado.intento.desc())
            .limit(1)
        )
        encontrado: Resultado | None = resultado.scalar_one_or_none()
        return encontrado


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
