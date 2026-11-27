"""Contrato de los ejecutores que llama el orquestador (T28 y T30).

Cada tipo de solicitud tiene un ejecutor, cuyos pasos el grafo de la orquestación recorre
como nodos distintos:

* ``ejecutar``: recupera, decide la suficiencia y, si alcanza, genera (contrato de T18). Si
  se abstiene, la abstención ya quedó registrada (T16) y no hay más pasos.
* ``verificar``: las comprobaciones del tipo sobre la salida ajustada, incluidas la 4
  (existencia de fuentes) y la 6 (fidelidad, con el evaluador) donde aplican (T30).
* ``reintentar``: un único reintento con los motivos de falla, los mismos fragmentos y sin
  repetir la recuperación (T30).
* ``registrar``: guarda el resultado del intento con su etiqueta y sus advertencias, y lo
  devuelve para enlazarle la verificación.

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
from app.bd.modelos import Resultado, Solicitud
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import Comprobacion


@dataclass
class Ejecucion:
    """Lo que produjo un intento. ``datos`` guarda lo que necesitan los pasos siguientes
    (alcance, fragmentos, evidencia, modelo); nunca entra al estado del grafo."""

    abstencion: bool
    salida: dict[str, Any] | None = None
    datos: dict[str, Any] = field(default_factory=dict)
    intento: int = 1


class Ejecutor(Protocol):
    tipo: TipoSolicitud

    async def ejecutar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> Ejecucion: ...

    async def reintentar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        anterior: Ejecucion,
        motivos: Sequence[str],
    ) -> Ejecucion: ...

    async def verificar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
    ) -> list[Comprobacion]: ...

    async def registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
        comprobaciones: Sequence[Comprobacion],
        etiqueta: Etiqueta,
    ) -> Resultado: ...


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
