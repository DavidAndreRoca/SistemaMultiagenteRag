"""Interfaces de los servicios bibliográficos (T14-01, apartado 2; RNF-20).

Quien verifica referencias (T15, T20) depende de estas interfaces, no de un servicio
concreto: cambiar o agregar un servicio no toca a los agentes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.bibliografia.modelos import ConsultaBibliografica, ResultadoBibliografico, Servicio


@runtime_checkable
class ServicioBibliografico(Protocol):
    servicio: Servicio

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        """Existencia y metadatos (o acceso abierto) de una obra por su DOI."""
        ...


@runtime_checkable
class BuscadorBibliografico(ServicioBibliografico, Protocol):
    async def buscar(self, consulta: ConsultaBibliografica) -> ResultadoBibliografico:
        """Candidatos para una referencia sin DOI. ``encontrado`` si hay candidatos; el
        comparador decide cuál corresponde."""
        ...


@runtime_checkable
class FormateadorDeCitas(ServicioBibliografico, Protocol):
    async def cita(self, doi: str, estilo: str, idioma: str = "es-ES") -> ResultadoBibliografico:
        """Cita formateada por el registro del DOI, sin modelo de lenguaje (RN-17)."""
        ...
