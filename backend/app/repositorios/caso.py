"""Repositorios de datos de caso (A1). Comparten solo la base con filtro por caso."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
