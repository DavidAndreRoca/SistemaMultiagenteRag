"""Base común de los clientes: DOI validado, caché y fallas convertidas en ``no_comprobable``."""

from __future__ import annotations

import html
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

from app.bibliografia.cache import Cache
from app.bibliografia.http import ClienteHttp, FallaDeServicio
from app.bibliografia.modelos import Autor, Motivo, ResultadoBibliografico, Servicio
from app.bibliografia.normalizacion import normalizar_doi


def doi_en_ruta(doi: str) -> str:
    """El DOI como segmento de URL (conserva la barra, escapa lo demás)."""
    return quote(doi, safe="/()._-;:")


def texto(valor: object) -> str | None:
    """Primer texto de un campo que puede venir como cadena o como lista de cadenas."""
    if isinstance(valor, list):
        valor = valor[0] if valor else None
    if valor is None:
        return None
    limpio = " ".join(str(valor).split())
    return limpio or None


def texto_plano(valor: object, maximo: int = 6000) -> str | None:
    """Texto sin marcas (el resumen JATS de Crossref trae etiquetas y entidades)."""
    if not isinstance(valor, str):
        return None
    sin_marcas = html.unescape(re.sub(r"<[^>]+>", " ", valor))
    limpio = " ".join(sin_marcas.split())
    return limpio[:maximo] or None


def anio_de_partes(fecha: object) -> int | None:
    """Año de un campo CSL ``{"date-parts": [[2024, 5, 1]]}``."""
    if not isinstance(fecha, dict):
        return None
    partes = fecha.get("date-parts")
    try:
        anio = partes[0][0] if partes else None
        return int(anio) if anio is not None else None
    except (TypeError, ValueError, IndexError):
        return None


def autores_csl(lista: object) -> list[Autor]:
    """Autores en el formato de Crossref y CSL (``family``, ``given``, ``name``/``literal``)."""
    if not isinstance(lista, list):
        return []
    autores = []
    for autor in lista:
        if not isinstance(autor, dict):
            continue
        apellidos = texto(autor.get("family"))
        nombres = texto(autor.get("given"))
        completo = texto(autor.get("name") or autor.get("literal"))
        if apellidos or completo:
            autores.append(Autor(apellidos=apellidos, nombres=nombres, nombre_completo=completo))
    return autores


class ClienteBase:
    servicio: Servicio

    def __init__(self, http: ClienteHttp, cache: Cache | None = None) -> None:
        self._http = http
        self._cache = cache

    async def _con_cache(
        self, clave: str, obtener: Callable[[], Awaitable[ResultadoBibliografico]]
    ) -> ResultadoBibliografico:
        if self._cache is not None:
            guardado = await self._cache.leer(self.servicio, clave)
            if guardado is not None:
                return guardado
        try:
            resultado = await obtener()
        except FallaDeServicio as falla:
            return ResultadoBibliografico.no_comprobable(self.servicio, falla.motivo)
        if self._cache is not None:
            await self._cache.guardar(clave, resultado)
        return resultado

    def _doi_valido(self, doi: str) -> str | None:
        return normalizar_doi(doi)

    def _doi_invalido(self) -> ResultadoBibliografico:
        return ResultadoBibliografico.no_comprobable(self.servicio, Motivo.DOI_INVALIDO)

    @staticmethod
    def _diccionario(valor: Any) -> dict[str, Any]:
        if not isinstance(valor, dict):
            raise FallaDeServicio(Motivo.RESPUESTA_INVALIDA)
        return valor
