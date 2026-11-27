"""Contrato de los ejecutores que llama el orquestador (T28).

Cada tipo de solicitud tiene un ejecutor con tres pasos, que el grafo de la orquestación
recorre como nodos distintos:

* ``ejecutar``: recupera, decide la suficiencia y, si alcanza, genera (contrato de T18). Si
  se abstiene, la abstención ya quedó registrada (T16) y no hay más pasos.
* ``verificar``: las comprobaciones deterministas del tipo, sobre la salida ajustada. T30
  agrega aquí el evaluador y el reintento con los motivos de falla.
* ``registrar``: guarda el resultado con su etiqueta y sus advertencias.

Los cambios de estado de la solicitud los hace el orquestador, salvo ``recuperando`` y
``generando``, que marca el ejecutor cuando empieza cada etapa.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoSolicitud
from app.bd.modelos import Solicitud
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import Comprobacion


@dataclass
class Ejecucion:
    """Lo que produjo el paso ``ejecutar``. ``datos`` guarda lo que necesitan los pasos
    siguientes (alcance, fragmentos, modelo); nunca entra al estado del grafo."""

    abstencion: bool
    salida: dict[str, Any] | None = None
    datos: dict[str, Any] = field(default_factory=dict)


class Ejecutor(Protocol):
    tipo: TipoSolicitud

    async def ejecutar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> Ejecucion: ...

    def verificar(self, ejecucion: Ejecucion) -> list[Comprobacion]: ...

    async def registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
        comprobaciones: Sequence[Comprobacion],
        etiqueta: Etiqueta | None,
    ) -> None: ...


def etiqueta_de(comprobaciones: Sequence[Comprobacion]) -> Etiqueta | None:
    """Con alguna comprobación fallida, "Con advertencias" (el reintento es de T30)."""
    return Etiqueta.CON_ADVERTENCIAS if any(not c.superada for c in comprobaciones) else None


def advertencias_de(comprobaciones: Sequence[Comprobacion]) -> list[str]:
    return [m for c in comprobaciones if not c.superada for m in c.motivos]


async def cambiar_estado(
    unidad: UnidadDeTrabajo,
    contexto: ContextoAcceso,
    solicitud_id: uuid.UUID,
    estado: EstadoSolicitud,
    reloj: Callable[[], datetime],
    motivo: str | None = None,
) -> None:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None:
        return
    ahora = reloj()
    solicitud.estado = estado
    solicitud.actualizada_en = ahora
    if motivo is not None:
        solicitud.motivo = motivo[:200]
    if estado is EstadoSolicitud.ENTREGADA:
        solicitud.entregada_en = ahora
    await unidad.confirmar()
