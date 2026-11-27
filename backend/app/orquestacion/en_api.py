"""Lo que la API necesita de la orquestación (T28).

* ``ejecutor_de``: el ejecutor del tipo, para validar y crear la solicitud (``iniciar``). Uno
  por proceso y tipo, desde la ``FabricaEjecutores``; las pruebas lo sustituyen en
  ``app.state``.
* ``encolar``: la solicitud ya quedó "recibida" en la cola; la atiende el trabajador. Solo
  con ``EJECUCION_EN_PROCESO`` (pruebas) la API la atiende ella misma con el mismo grafo.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from langgraph.checkpoint.memory import InMemorySaver

from app.agentes.ejecucion import Ejecutor
from app.bd.enumeraciones import TipoSolicitud
from app.bd.modelos import Solicitud
from app.configuracion import Ajustes
from app.orquestacion.fabrica import ATRIBUTOS, FabricaEjecutores
from app.orquestacion.grafo import Orquestador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo, fabrica_de_unidades
from app.seguridad.dependencias import obtener_reloj


async def ejecutor_de(peticion: Request, unidad: UnidadDeTrabajo, tipo: TipoSolicitud) -> Any:
    estado = peticion.app.state
    actual: Ejecutor | None = getattr(estado, ATRIBUTOS[tipo], None)
    if actual is not None:
        return actual
    fabrica: FabricaEjecutores | None = getattr(estado, "fabrica_ejecutores", None)
    if fabrica is None:
        _, parametros = await unidad.configuracion.vigente()
        fabrica = FabricaEjecutores(
            estado.ajustes,
            parametros,
            fabrica_de_unidades(estado.fabrica_sesiones),
            obtener_reloj(peticion),
        )
        estado.fabrica_ejecutores = fabrica
    actual = fabrica(tipo)  # CorpusNoConfigurado (503) si falta un servicio
    setattr(estado, ATRIBUTOS[tipo], actual)
    return actual


def orquestador_en_proceso(aplicacion: FastAPI, peticion: Request) -> Orquestador:
    estado = aplicacion.state
    actual: Orquestador | None = getattr(estado, "orquestador", None)
    if actual is None:

        def ejecutores(tipo: TipoSolicitud) -> Ejecutor:
            ejecutor: Ejecutor = getattr(estado, ATRIBUTOS[tipo])
            return ejecutor

        actual = Orquestador(
            ejecutores,
            fabrica_de_unidades(estado.fabrica_sesiones),
            obtener_reloj(peticion),
            InMemorySaver(),
        )
        estado.orquestador = actual
    return actual


def encolar(peticion: Request, solicitud: Solicitud, contexto: ContextoAcceso) -> None:
    ajustes: Ajustes = peticion.app.state.ajustes
    if ajustes.ejecucion_en_proceso:
        orquestador_en_proceso(peticion.app, peticion).lanzar(solicitud.id, contexto)
