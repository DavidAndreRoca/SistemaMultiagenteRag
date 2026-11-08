"""Interfaces de los motores de inferencia. La aplicación HTTP solo depende de estas."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from servicio.catalogo import ModeloFijado


class MotorEmbeddings(Protocol):
    @property
    def modelo(self) -> ModeloFijado: ...

    def contar_tokens(self, textos: Sequence[str]) -> list[int]:
        """Tokens de cada texto, con los especiales."""
        ...

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        """Vectores normalizados (norma 1) de ``DIMENSION_EMBEDDINGS``, en el orden recibido."""
        ...


class MotorReordenador(Protocol):
    @property
    def modelo(self) -> ModeloFijado: ...

    def contar_tokens(self, consulta: str, textos: Sequence[str]) -> list[int]:
        """Tokens de cada par (consulta, texto), con los especiales."""
        ...

    def reordenar(self, consulta: str, textos: Sequence[str]) -> list[float]:
        """Puntaje de pertinencia de cada texto, normalizado entre 0 y 1 (sigmoide)."""
        ...
