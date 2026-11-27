"""Enrutamiento determinista: cada tipo de solicitud va a un solo agente (RN-02, CP-03).

Tabla fija de la tesis (tabla 9; insumos de T04, tabla 3). El nodo de enrutamiento no llama
al modelo ni consume tokens (Fase 1, 6.1). Un tipo que no está en la tabla es un error de
validación: la solicitud no se ejecuta.
"""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType
from typing import Final

from app.bd.enumeraciones import TipoSolicitud


class AgenteSistema(StrEnum):
    ESTRUCTURAL = "D1"
    METODOLOGICO = "D2"
    ESTILISTICO = "D3"
    BIBLIOGRAFICO = "D4"


TABLA_DE_AGENTES: Final = MappingProxyType(
    {
        TipoSolicitud.REVISION_ESTRUCTURA: AgenteSistema.ESTRUCTURAL,
        TipoSolicitud.PLAN_TAREA: AgenteSistema.ESTRUCTURAL,
        TipoSolicitud.REVISION_METODOLOGICA: AgenteSistema.METODOLOGICO,
        TipoSolicitud.PROPUESTA_REDACCION: AgenteSistema.ESTILISTICO,
        TipoSolicitud.BUSQUEDA_EVIDENCIA: AgenteSistema.BIBLIOGRAFICO,
        TipoSolicitud.VERIFICACION_REFERENCIAS: AgenteSistema.BIBLIOGRAFICO,
    }
)


class TipoDesconocido(ValueError):
    """El tipo de la solicitud no está en la tabla fija."""


def enrutar(tipo: str | None) -> AgenteSistema:
    """El agente del tipo; ``TipoDesconocido`` si no es uno de los seis."""
    try:
        return TABLA_DE_AGENTES[TipoSolicitud(tipo or "")]
    except (ValueError, KeyError):
        raise TipoDesconocido(str(tipo)) from None
