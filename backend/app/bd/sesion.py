"""Motor y sesiones asíncronas de SQLAlchemy 2 con psycopg 3.

El motor se crea al arrancar la aplicación (``lifespan``) y se cierra al apagarla.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.configuracion import Ajustes


def crear_motor(ajustes: Ajustes) -> AsyncEngine:
    return create_async_engine(
        ajustes.url_bd.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


def crear_fabrica_sesiones(motor: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(motor, expire_on_commit=False)
