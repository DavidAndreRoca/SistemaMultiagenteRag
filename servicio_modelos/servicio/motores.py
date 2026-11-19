"""Interfaces de los motores de inferencia. La aplicación HTTP solo depende de estas."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
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


class ReordenadorPerezoso:
    """Carga el reordenador al primer uso (decisión T10-02).

    Durante la ingesta del corpus solo se embebe: con el reordenador cargado desde el
    arranque, el servicio ocupa memoria que no usa. El modelo es el mismo; solo cambia
    cuándo se carga. La primera llamada a ``/reordenar`` tarda lo que tarda la carga.
    """

    def __init__(self, cargar: Callable[[], MotorReordenador], modelo: ModeloFijado) -> None:
        self._cargar = cargar
        self._modelo = modelo
        self._motor: MotorReordenador | None = None
        self._candado = threading.Lock()

    @property
    def modelo(self) -> ModeloFijado:
        return self._modelo

    @property
    def cargado(self) -> bool:
        return self._motor is not None

    def _real(self) -> MotorReordenador:
        with self._candado:
            if self._motor is None:
                self._motor = self._cargar()
            return self._motor

    def contar_tokens(self, consulta: str, textos: Sequence[str]) -> list[int]:
        return self._real().contar_tokens(consulta, textos)

    def reordenar(self, consulta: str, textos: Sequence[str]) -> list[float]:
        return self._real().reordenar(consulta, textos)
