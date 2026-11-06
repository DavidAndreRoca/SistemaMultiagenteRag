"""Contexto de la petición en curso (identificador de incidencia)."""

from __future__ import annotations

from contextvars import ContextVar

_incidencia_id: ContextVar[str | None] = ContextVar("incidencia_id", default=None)


def obtener_incidencia_id() -> str | None:
    return _incidencia_id.get()


def fijar_incidencia_id(valor: str | None) -> None:
    _incidencia_id.set(valor)
