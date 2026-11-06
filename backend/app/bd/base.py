"""Base declarativa, convenciones de nombres y tipos comunes del esquema.

Cada columna lleva ``comment`` (descripción, también guardada en PostgreSQL) y, si
corresponde, ``info={"alimenta": ...}`` con el indicador o la exportación que
alimenta. El diccionario de datos se genera desde aquí (``python -m app.bd.diccionario``).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


def enumeracion(tipo: type[enum.Enum], nombre: str) -> Enum:
    """Enumeración guardada como texto con restricción CHECK (migraciones simples)."""
    return Enum(
        tipo,
        name=nombre,
        native_enum=False,
        create_constraint=True,
        length=40,
        values_callable=lambda miembros: [m.value for m in miembros],
        validate_strings=True,
    )


def clave_primaria() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
        comment="Identificador interno (UUID).",
    )


def momento(
    comentario: str, *, nulo: bool = False, alimenta: str | None = None
) -> Mapped[datetime]:
    info: dict[str, Any] = {"alimenta": alimenta} if alimenta else {}
    return mapped_column(
        DateTime(timezone=True),
        nullable=nulo,
        server_default=None if nulo else func.now(),
        comment=comentario,
        info=info,
    )
