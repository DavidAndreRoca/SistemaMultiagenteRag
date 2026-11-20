"""Repositorios sin datos de caso: configuración vigente, estado de la base y caché de
metadatos bibliográficos (públicos y compartidos por todo el sistema, T14-01)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.administracion.parametros import ParametrosFuncionales
from app.bd.modelos import CacheMetadatos, Configuracion


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


class RepositorioCacheMetadatos:
    """Resultados de los servicios bibliográficos por servicio y clave (DOI o consulta)."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def vigente(self, servicio: str, clave: str, ahora: datetime) -> dict[str, Any] | None:
        respuesta: dict[str, Any] | None = await self._sesion.scalar(
            select(CacheMetadatos.respuesta).where(
                CacheMetadatos.servicio == servicio,
                CacheMetadatos.clave == clave,
                CacheMetadatos.vigente_hasta > ahora,
            )
        )
        return respuesta

    async def guardar(
        self,
        servicio: str,
        clave: str,
        respuesta: dict[str, Any],
        obtenida_en: datetime,
        vigente_hasta: datetime,
    ) -> None:
        """Crea o reemplaza la entrada (una por servicio y clave)."""
        valores = {
            "respuesta": respuesta,
            "obtenida_en": obtenida_en,
            "vigente_hasta": vigente_hasta,
        }
        await self._sesion.execute(
            insert(CacheMetadatos)
            .values(servicio=servicio, clave=clave, **valores)
            .on_conflict_do_update(index_elements=["servicio", "clave"], set_=valores)
        )
