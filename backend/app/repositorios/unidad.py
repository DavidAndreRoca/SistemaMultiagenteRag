"""Unidad de trabajo: agrupa los repositorios de una petición y confirma o revierte.

Los servicios reciben una ``UnidadDeTrabajo`` y nunca la sesión de base (4.2).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositorios.autenticacion import RepositorioAutenticacion
from app.repositorios.caso import (
    RepositorioCasoPropio,
    RepositorioDecisiones,
    RepositorioFragmentosRecuperados,
    RepositorioFuentesAportadas,
    RepositorioResultados,
    RepositorioSolicitudes,
    RepositorioVerificaciones,
    RepositorioVersiones,
)
from app.repositorios.colecciones import RepositorioColecciones
from app.repositorios.investigador import (
    RepositorioCasosInvestigador,
    RepositorioColeccionesInvestigador,
    RepositorioCuentasInvestigador,
)
from app.repositorios.sistema import RepositorioConfiguracion, RepositorioSalud


class UnidadDeTrabajo:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        # Autenticación y sistema
        self.autenticacion = RepositorioAutenticacion(sesion)
        self.configuracion = RepositorioConfiguracion(sesion)
        self.salud = RepositorioSalud(sesion)
        # Datos de caso (A1)
        self.caso_propio = RepositorioCasoPropio(sesion)
        self.versiones = RepositorioVersiones(sesion)
        self.solicitudes = RepositorioSolicitudes(sesion)
        self.fragmentos_recuperados = RepositorioFragmentosRecuperados(sesion)
        self.resultados = RepositorioResultados(sesion)
        self.verificaciones = RepositorioVerificaciones(sesion)
        self.decisiones = RepositorioDecisiones(sesion)
        self.fuentes_aportadas = RepositorioFuentesAportadas(sesion)
        self.colecciones = RepositorioColecciones(sesion)
        # Investigador (A2)
        self.casos_investigador = RepositorioCasosInvestigador(sesion)
        self.colecciones_investigador = RepositorioColeccionesInvestigador(sesion)
        self.cuentas_investigador = RepositorioCuentasInvestigador(sesion)

    async def confirmar(self) -> None:
        await self._sesion.commit()

    async def revertir(self) -> None:
        await self._sesion.rollback()


async def abrir_unidad(fabrica: async_sessionmaker[AsyncSession]) -> AsyncIterator[UnidadDeTrabajo]:
    async with fabrica() as sesion:
        yield UnidadDeTrabajo(sesion)


async def obtener_unidad(peticion: Request) -> AsyncIterator[UnidadDeTrabajo]:
    """Dependencia de FastAPI: una unidad de trabajo por petición."""
    fabrica: async_sessionmaker[AsyncSession] = peticion.app.state.fabrica_sesiones
    async with fabrica() as sesion:
        yield UnidadDeTrabajo(sesion)
