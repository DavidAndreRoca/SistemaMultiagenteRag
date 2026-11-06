"""Atajo para declarar columnas con descripción e indicador alimentado."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import MappedColumn, mapped_column


def col(
    *args: Any, comentario: str, alimenta: str | None = None, **kwargs: Any
) -> MappedColumn[Any]:
    info = dict(kwargs.pop("info", {}))
    if alimenta:
        info["alimenta"] = alimenta
    return mapped_column(*args, comment=comentario, info=info, **kwargs)
