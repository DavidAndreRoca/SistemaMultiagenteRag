"""Entorno de Alembic. Migraciones síncronas con psycopg 3 sobre la misma URL de la API."""

from __future__ import annotations

import os
from logging.config import fileConfig

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


def _url() -> str:
    url = configuracion.get_main_option("sqlalchemy.url") or os.environ.get("URL_BD")
    if not url:
        raise RuntimeError("Defina URL_BD para ejecutar las migraciones")
    return url


def ejecutar_sin_conexion() -> None:
    context.configure(url=_url(), target_metadata=objetivo, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_con_conexion() -> None:
    motor = create_engine(_url(), poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=objetivo, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    motor.dispose()


if context.is_offline_mode():
    ejecutar_sin_conexion()
else:
    ejecutar_con_conexion()
