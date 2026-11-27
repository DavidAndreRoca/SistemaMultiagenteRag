"""Entorno de Alembic. Migraciones síncronas con psycopg 3 sobre la misma URL de la API."""

from __future__ import annotations

import os
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import create_engine, pool

import app.bd.modelos  # noqa: F401  (registra las tablas)
from app.bd.base import Base

configuracion = context.config
if configuracion.config_file_name is not None and configuracion.attributes.get(
    "configurar_registro", True
):
    fileConfig(configuracion.config_file_name)

objetivo = Base.metadata

# Tablas del checkpointer de LangGraph (T28): las crea la migración 0021 con la ``setup()`` de
# la biblioteca y no son modelos de SQLAlchemy. La comparación de ``alembic check`` las omite.
TABLAS_DEL_CHECKPOINTER = frozenset(
    {"checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"}
)


def incluir(objeto: Any, nombre: str | None, tipo: str, reflejado: bool, comparado: Any) -> bool:
    tabla = objeto.table.name if tipo in ("index", "column", "unique_constraint") else nombre
    return tabla not in TABLAS_DEL_CHECKPOINTER


def _url() -> str:
    url = configuracion.get_main_option("sqlalchemy.url") or os.environ.get("URL_BD")
    if not url:
        raise RuntimeError("Defina URL_BD para ejecutar las migraciones")
    return url


def ejecutar_sin_conexion() -> None:
    context.configure(
        url=_url(), target_metadata=objetivo, literal_binds=True, include_object=incluir
    )
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_con_conexion() -> None:
    motor = create_engine(_url(), poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=objetivo,
            compare_type=True,
            include_object=incluir,
        )
        with context.begin_transaction():
            context.run_migrations()
    motor.dispose()


if context.is_offline_mode():
    ejecutar_sin_conexion()
else:
    ejecutar_con_conexion()
