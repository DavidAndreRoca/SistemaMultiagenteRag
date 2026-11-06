"""Repositorios sin datos de caso: configuración vigente y estado de la base."""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.administracion.parametros import ParametrosFuncionales
from app.bd.modelos import Configuracion


class ErrorSinConfiguracion(RuntimeError):
    """No hay una versión de configuración vigente (falta aplicar las migraciones)."""


class RepositorioConfiguracion:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def vigente(self) -> tuple[Configuracion, ParametrosFuncionales]:
        """Versión vigente y sus parámetros validados."""
        resultado = await self._sesion.execute(
            select(Configuracion).where(Configuracion.vigente.is_(True))
        )
        configuracion = resultado.scalar_one_or_none()
        if configuracion is None:
            raise ErrorSinConfiguracion("no hay configuración vigente")
        return configuracion, ParametrosFuncionales.model_validate(configuracion.parametros)


class RepositorioSalud:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def version_extension_vector(self) -> str | None:
        """Ejecuta una consulta mínima y devuelve la versión de ``vector`` si está instalada."""
        await self._sesion.execute(text("SELECT 1"))
        resultado = await self._sesion.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        version: str | None = resultado.scalar_one_or_none()
        return version
