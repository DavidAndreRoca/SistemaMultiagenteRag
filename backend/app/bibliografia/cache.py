"""Caché de resultados bibliográficos en ``cache_metadatos`` (T14-01, apartado 5).

* Solo se guardan ``encontrado`` (30 días) y ``no_encontrado`` (24 horas, porque un DOI
  recién registrado puede aparecer al día siguiente). Un ``no_comprobable`` nunca se
  guarda: una caída no se recuerda como un resultado.
* Un problema con la base no impide consultar: la caché se omite y se registra.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from app.bibliografia.modelos import Estado, ResultadoBibliografico, Servicio
from app.comun.registro import obtener_registrador
from app.repositorios.unidad import FabricaUnidades

_registro = obtener_registrador("bibliografia")


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class Cache(Protocol):
    async def leer(self, servicio: Servicio, clave: str) -> ResultadoBibliografico | None: ...

    async def guardar(self, clave: str, resultado: ResultadoBibliografico) -> None: ...


class CacheBibliografica:
    def __init__(
        self,
        abrir: FabricaUnidades,
        vigencia: timedelta,
        vigencia_no_encontrado: timedelta,
        reloj: Callable[[], datetime] = ahora_utc,
    ) -> None:
        self._abrir = abrir
        self._vigencia = {
            Estado.ENCONTRADO: vigencia,
            Estado.NO_ENCONTRADO: vigencia_no_encontrado,
        }
        self._reloj = reloj

    async def leer(self, servicio: Servicio, clave: str) -> ResultadoBibliografico | None:
        try:
            async with self._abrir() as unidad:
                guardado = await unidad.cache_metadatos.vigente(
                    servicio.value, clave, self._reloj()
                )
        except SQLAlchemyError:
            _registro.warning(
                "cache bibliografica no disponible", extra={"tipo_evento": "bibliografia"}
            )
            return None
        if guardado is None:
            return None
        resultado = ResultadoBibliografico.model_validate(guardado)
        return resultado.model_copy(update={"desde_cache": True})

    async def guardar(self, clave: str, resultado: ResultadoBibliografico) -> None:
        vigencia = self._vigencia.get(resultado.estado)
        if vigencia is None:  # no_comprobable
            return
        ahora = self._reloj()
        respuesta = resultado.model_copy(update={"desde_cache": False}).model_dump(mode="json")
        try:
            async with self._abrir() as unidad:
                await unidad.cache_metadatos.guardar(
                    resultado.servicio.value, clave, respuesta, ahora, ahora + vigencia
                )
                await unidad.confirmar()
        except SQLAlchemyError:
            _registro.warning(
                "cache bibliografica no disponible", extra={"tipo_evento": "bibliografia"}
            )


class CacheEnMemoria:
    """Misma interfaz, sin base: para pruebas y herramientas de consola."""

    def __init__(self) -> None:
        self.entradas: dict[tuple[str, str], ResultadoBibliografico] = {}

    async def leer(self, servicio: Servicio, clave: str) -> ResultadoBibliografico | None:
        guardado = self.entradas.get((servicio.value, clave))
        return guardado.model_copy(update={"desde_cache": True}) if guardado else None

    async def guardar(self, clave: str, resultado: ResultadoBibliografico) -> None:
        if resultado.estado is not Estado.NO_COMPROBABLE:
            self.entradas[(resultado.servicio.value, clave)] = resultado
