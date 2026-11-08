"""Interfaces ``ProveedorEmbeddings`` y ``Reordenador`` (T08, RNF-20).

La indexación (T10) y la recuperación (T16) dependen solo de estas interfaces: cambiar
de modelo o de servicio no toca a quien las usa. Cada resultado trae el identificador y
la revisión exacta del modelo, que se guardan con los vectores (RNF-21).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class IdentidadModelo(BaseModel):
    model_config = ConfigDict(frozen=True)

    modelo: str = Field(min_length=1)
    revision: str = Field(min_length=1)


class Embeddings(BaseModel):
    model_config = ConfigDict(frozen=True)

    identidad: IdentidadModelo
    vectores: list[list[float]]


class Puntajes(BaseModel):
    model_config = ConfigDict(frozen=True)

    identidad: IdentidadModelo
    puntajes: list[float] = Field(description="Uno por texto, en el orden recibido; 0 a 1")


class ProveedorEmbeddings(Protocol):
    async def embeber(self, textos: Sequence[str]) -> Embeddings:
        """Vectores normalizados de 1 024 dimensiones, uno por texto y en el mismo orden."""
        ...


class Reordenador(Protocol):
    async def reordenar(self, consulta: str, textos: Sequence[str]) -> Puntajes:
        """Puntaje de pertinencia de cada texto para la consulta, entre 0 y 1."""
        ...
