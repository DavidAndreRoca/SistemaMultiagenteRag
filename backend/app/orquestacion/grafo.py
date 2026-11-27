"""Grafo de la orquestación con LangGraph (T28 y T30; RF-03, RF-11, CU-02, CU-10, CP-03,
CP-04, CP-06, CP-07, RN-01, RN-02, RN-05, RN-06).

Toda solicitud recorre el mismo camino, en el orden de la Fase 1 (6.1 y 6.7):

    validar → enrutar → ejecutar → verificar → etiquetar → registrar → entregar
                                 ↘ (abstención) entregar
                       verificar → (falla corregible, intento 1) reintentar → verificar
    cualquier falla técnica → no_atendida

* ``validar``: la solicitud existe para el caso del contexto, está en cola y es de un tipo
  conocido. Si viene de un intento cortado, borra lo que dejó (fragmentos y resultados).
* ``enrutar``: tabla fija tipo a agente (``enrutamiento.py``), sin modelo.
* ``ejecutar``: recuperar, decidir la suficiencia y abstenerse o generar, con el ejecutor
  del tipo (contrato de T18; ``app/agentes/ejecucion.py``).
* ``verificar``: las seis comprobaciones, las que aplican al tipo (T30): esquema, límites,
  citas, existencia de fuentes, acceso abierto y fidelidad con el evaluador.
* ``reintentar``: si alguna falla la puede corregir el agente y es el intento 1, registra el
  intento con su verificación y genera una sola vez más con los motivos, los mismos
  fragmentos y sin repetir la recuperación (RN-05).
* ``etiquetar`` y ``registrar``: "Verificada" o "Con advertencias" (la abstención ya es "Sin
  evidencia suficiente"), y el resultado final con su verificación (PI-04).
* ``no_atendida``: una caída del proveedor (``ErrorDisponibilidad``) vuelve a la cola hasta
  agotar ``MAX_INTENTOS_TECNICOS``; cualquier otra falla deja la solicitud "no atendida"
  con su motivo, recuperable con el reenvío (T29).

El estado del grafo, que el checkpointer guarda en PostgreSQL por solicitud, solo lleva
identificadores, tipo, agente, nombres de comprobaciones, etiqueta y motivo de falla: nunca
el texto del borrador ni la salida (4.6). Lo demás viaja en el contexto de la ejecución,
que no se guarda.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from app.agentes.ejecucion import Ejecucion, Ejecutor, cambiar_estado
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoSolicitud
from app.bd.modelos import EventoTecnico, Solicitud
from app.comun.registro import obtener_registrador
from app.llm.modelos import ErrorDisponibilidad, ErrorModelo
from app.orquestacion.enrutamiento import TipoDesconocido, enrutar
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import FabricaUnidades, UnidadDeTrabajo
from app.verificacion.comprobaciones import Comprobacion
from app.verificacion.registro import etiqueta_de, motivos_para_reintento, verificacion_de

MAX_INTENTOS_TECNICOS = 3  # la base lo limita con un CHECK (0 a 3)
EN_COLA = frozenset({EstadoSolicitud.RECIBIDA, EstadoSolicitud.ASIGNADA})
_registro = obtener_registrador("orquestacion")


class EstadoGrafo(TypedDict, total=False):
    solicitud_id: str
    tipo: str | None
    agente: str | None
    abstencion: bool
    comprobaciones: list[dict[str, Any]]
    etiqueta: str | None
    intento: int
    reintentar: bool
    motivos_reintento: int
    fallo: str | None
    reintentable: bool
    estado_final: str | None


@dataclass
class ContextoEjecucion:
    """Lo que los nodos necesitan y no entra al estado guardado."""

    unidad: UnidadDeTrabajo
    contexto: ContextoAcceso
    ejecutores: Callable[[TipoSolicitud], Ejecutor]
    reloj: Callable[[], datetime]
    solicitud: Solicitud | None = None
    ejecutor: Ejecutor | None = None
    ejecucion: Ejecucion | None = None
    comprobaciones: list[Comprobacion] = field(default_factory=list)


class Nodo(Protocol):
    __name__: str

    def __call__(
        self, estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]
    ) -> Awaitable[dict[str, Any]]: ...


def motivo_de(error: Exception) -> str:
    if isinstance(error, ErrorModelo):
        return f"modelo:{error.motivo.value}"
    if isinstance(error, TipoDesconocido):
        return "validacion:tipo_desconocido"
    return str(getattr(error, "codigo", type(error).__name__))


def _seguro(nodo: Nodo) -> Nodo:
    """Una excepción no rompe el grafo: lo lleva a ``no_atendida`` con su motivo."""

    async def envuelto(
        estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]
    ) -> dict[str, Any]:
        try:
            return await nodo(estado, runtime=runtime)
        except Exception as error:
            return {
                "fallo": motivo_de(error),
                "reintentable": isinstance(error, ErrorDisponibilidad),
            }

    envuelto.__name__ = nodo.__name__
    return envuelto


async def validar(estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]) -> dict[str, Any]:
    ctx = runtime.context
    solicitud = await ctx.unidad.solicitudes.obtener(
        ctx.contexto, uuid.UUID(estado["solicitud_id"])
    )
    if solicitud is None:
        return {"fallo": "validacion:inexistente"}
    ctx.solicitud = solicitud
    if solicitud.estado not in EN_COLA:
        return {"fallo": "validacion:estado", "tipo": solicitud.tipo.value}
    if solicitud.intentos_tecnicos or solicitud.motivo == "interrumpida":
        # Un intento anterior pudo dejar fragmentos o un resultado a medias.
        await ctx.unidad.fragmentos_recuperados.borrar_de_solicitud(ctx.contexto, solicitud.id)
        await ctx.unidad.resultados.borrar_de_solicitud(ctx.contexto, solicitud.id)
        await ctx.unidad.confirmar()
    return {"tipo": solicitud.tipo.value}


async def enrutar_solicitud(
    estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]
) -> dict[str, Any]:
    ctx = runtime.context
    agente = enrutar(estado.get("tipo"))  # sin modelo: tabla fija (RN-02)
    assert ctx.solicitud is not None
    ctx.ejecutor = ctx.ejecutores(ctx.solicitud.tipo)
    await cambiar_estado(
        ctx.unidad, ctx.contexto, ctx.solicitud.id, EstadoSolicitud.ASIGNADA, ctx.reloj
    )
    return {"agente": agente.value}


async def _etapa(ctx: ContextoEjecucion, nombre: str, inicio: datetime) -> None:
    """Duración de una etapa como evento técnico (T30: latencias por etapa, RNF-12)."""
    assert ctx.solicitud is not None
    duracion = round((ctx.reloj() - inicio).total_seconds() * 1000)
    await ctx.unidad.eventos_tecnicos.agregar(
        EventoTecnico(
            solicitud_id=ctx.solicitud.id, etapa=nombre, inicio=inicio, duracion_ms=max(duracion, 0)
        )
    )
    await ctx.unidad.confirmar()


async def ejecutar(estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]) -> dict[str, Any]:
    ctx = runtime.context
    assert ctx.ejecutor is not None and ctx.solicitud is not None
    inicio = ctx.reloj()
    ctx.ejecucion = await ctx.ejecutor.ejecutar(ctx.unidad, ctx.contexto, ctx.solicitud)
    await _etapa(ctx, "ejecucion", inicio)
    return {"abstencion": ctx.ejecucion.abstencion}


async def verificar(estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]) -> dict[str, Any]:
    ctx = runtime.context
    assert ctx.ejecutor is not None and ctx.ejecucion is not None and ctx.solicitud is not None
    await cambiar_estado(
        ctx.unidad, ctx.contexto, ctx.solicitud.id, EstadoSolicitud.VERIFICANDO, ctx.reloj
    )
    inicio = ctx.reloj()
    ctx.comprobaciones = await ctx.ejecutor.verificar(
        ctx.unidad, ctx.contexto, ctx.solicitud, ctx.ejecucion
    )
    await _etapa(ctx, "verificacion", inicio)
    intento = ctx.ejecucion.intento
    return {
        "intento": intento,
        "comprobaciones": [
            {"numero": c.numero, "nombre": c.nombre, "superada": c.superada}
            for c in ctx.comprobaciones
        ],
        # Un solo reintento, y solo si alguna falla la puede corregir el agente (RN-05).
        "reintentar": intento == 1 and bool(motivos_para_reintento(ctx.comprobaciones)),
    }


async def _registrar_intento(ctx: ContextoEjecucion, etiqueta: Etiqueta) -> None:
    """Resultado del intento y su verificación (PI-04: una verificación por intento)."""
    assert ctx.ejecutor is not None and ctx.ejecucion is not None and ctx.solicitud is not None
    resultado = await ctx.ejecutor.registrar(
        ctx.unidad, ctx.contexto, ctx.solicitud, ctx.ejecucion, ctx.comprobaciones, etiqueta
    )
    await ctx.unidad.verificaciones.agregar(
        ctx.contexto,
        verificacion_de(resultado.id, ctx.ejecucion.intento, ctx.comprobaciones, ctx.reloj()),
    )
    await ctx.unidad.confirmar()


async def reintentar(estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]) -> dict[str, Any]:
    """El intento 1 no superó la verificación: queda registrado y el agente genera de nuevo
    con los motivos, los mismos fragmentos y sin repetir la recuperación (Fase 1, 7.2)."""
    ctx = runtime.context
    assert ctx.ejecutor is not None and ctx.ejecucion is not None and ctx.solicitud is not None
    await cambiar_estado(
        ctx.unidad, ctx.contexto, ctx.solicitud.id, EstadoSolicitud.REINTENTANDO, ctx.reloj
    )
    motivos = motivos_para_reintento(ctx.comprobaciones)
    await _registrar_intento(ctx, Etiqueta.CON_ADVERTENCIAS)
    inicio = ctx.reloj()
    ctx.ejecucion = await ctx.ejecutor.reintentar(
        ctx.unidad, ctx.contexto, ctx.solicitud, ctx.ejecucion, motivos
    )
    await _etapa(ctx, "reintento", inicio)
    return {"intento": 2, "motivos_reintento": len(motivos)}


async def etiquetar(estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]) -> dict[str, Any]:
    return {"etiqueta": etiqueta_de(runtime.context.comprobaciones).value}


async def registrar(estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]) -> dict[str, Any]:
    await _registrar_intento(runtime.context, etiqueta_de(runtime.context.comprobaciones))
    return {}


async def entregar(estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]) -> dict[str, Any]:
    ctx = runtime.context
    assert ctx.solicitud is not None
    await cambiar_estado(
        ctx.unidad, ctx.contexto, ctx.solicitud.id, EstadoSolicitud.ENTREGADA, ctx.reloj
    )
    return {"estado_final": EstadoSolicitud.ENTREGADA.value}


async def no_atendida(
    estado: EstadoGrafo, *, runtime: Runtime[ContextoEjecucion]
) -> dict[str, Any]:
    """Caída del proveedor: vuelve a la cola mientras queden intentos técnicos. Otra falla, o
    sin intentos: "no atendida" con su motivo. Una solicitud que ya no estaba en cola (por
    ejemplo, entregada) no se toca."""
    ctx = runtime.context
    fallo = estado.get("fallo") or "desconocido"
    await ctx.unidad.revertir()  # la falla pudo dejar la sesión a medias
    solicitud = await ctx.unidad.solicitudes.obtener(
        ctx.contexto, uuid.UUID(estado["solicitud_id"])
    )
    if solicitud is None or fallo == "validacion:estado":
        return {"estado_final": solicitud.estado.value if solicitud else None}
    solicitud.motivo = fallo[:200]
    solicitud.actualizada_en = ctx.reloj()
    if estado.get("reintentable") and solicitud.intentos_tecnicos < MAX_INTENTOS_TECNICOS:
        solicitud.intentos_tecnicos += 1
        solicitud.estado = EstadoSolicitud.RECIBIDA
    else:
        solicitud.estado = EstadoSolicitud.NO_ATENDIDA
    await ctx.unidad.confirmar()
    return {"estado_final": solicitud.estado.value}


def _siguiente(normal: str) -> Callable[[EstadoGrafo], str]:
    def elegir(estado: EstadoGrafo) -> str:
        return "no_atendida" if estado.get("fallo") else normal

    return elegir


def _tras_verificar(estado: EstadoGrafo) -> str:
    if estado.get("fallo"):
        return "no_atendida"
    return "reintentar" if estado.get("reintentar") else "etiquetar"


def _tras_ejecutar(estado: EstadoGrafo) -> str:
    if estado.get("fallo"):
        return "no_atendida"
    return "entregar" if estado.get("abstencion") else "verificar"


def construir_grafo() -> StateGraph[EstadoGrafo, ContextoEjecucion, EstadoGrafo, EstadoGrafo]:
    grafo = StateGraph(EstadoGrafo, context_schema=ContextoEjecucion)
    for nombre, nodo in (
        ("validar", validar),
        ("enrutar", enrutar_solicitud),
        ("ejecutar", ejecutar),
        ("verificar", verificar),
        ("reintentar", reintentar),
        ("etiquetar", etiquetar),
        ("registrar", registrar),
        ("entregar", entregar),
    ):
        # Las sobrecargas tipadas de ``add_node`` no aceptan nodos con ``runtime`` bajo mypy
        # estricto (tampoco un ejemplo mínimo con TypedDict o Pydantic): el grafo se prueba.
        grafo.add_node(nombre, _seguro(nodo))  # type: ignore[call-overload]
    grafo.add_node("no_atendida", no_atendida)  # type: ignore[call-overload]
    grafo.add_edge(START, "validar")
    grafo.add_conditional_edges("validar", _siguiente("enrutar"), ["enrutar", "no_atendida"])
    grafo.add_conditional_edges("enrutar", _siguiente("ejecutar"), ["ejecutar", "no_atendida"])
    grafo.add_conditional_edges(
        "ejecutar", _tras_ejecutar, ["verificar", "entregar", "no_atendida"]
    )
    grafo.add_conditional_edges(
        "verificar", _tras_verificar, ["reintentar", "etiquetar", "no_atendida"]
    )
    grafo.add_conditional_edges("reintentar", _siguiente("verificar"), ["verificar", "no_atendida"])
    grafo.add_conditional_edges("etiquetar", _siguiente("registrar"), ["registrar", "no_atendida"])
    grafo.add_conditional_edges("registrar", _siguiente("entregar"), ["entregar", "no_atendida"])
    grafo.add_conditional_edges("entregar", _siguiente(END), [END, "no_atendida"])
    grafo.add_edge("no_atendida", END)
    return grafo


ESTADO_INICIAL: EstadoGrafo = {
    "tipo": None,
    "agente": None,
    "abstencion": False,
    "comprobaciones": [],
    "etiqueta": None,
    "intento": 1,
    "reintentar": False,
    "motivos_reintento": 0,
    "fallo": None,
    "reintentable": False,
    "estado_final": None,
}


class Orquestador:
    """Ejecuta el grafo para una solicitud. Lo usa el trabajador y, solo en pruebas
    (``EJECUCION_EN_PROCESO``), la API dentro de su propio proceso."""

    def __init__(
        self,
        ejecutores: Callable[[TipoSolicitud], Ejecutor],
        abrir: FabricaUnidades,
        reloj: Callable[[], datetime],
        checkpointer: BaseCheckpointSaver[Any] | None = None,
    ) -> None:
        self._ejecutores = ejecutores
        self._abrir = abrir
        self._reloj = reloj
        self._grafo = construir_grafo().compile(checkpointer=checkpointer)
        self._tareas: set[asyncio.Task[str | None]] = set()

    async def atender(self, solicitud_id: uuid.UUID, contexto: ContextoAcceso) -> str | None:
        """Recorre el grafo; devuelve el estado en que queda la solicitud."""
        inicio = self._reloj()
        async with self._abrir() as unidad:
            ejecucion = ContextoEjecucion(unidad, contexto, self._ejecutores, self._reloj)
            final = await self._grafo.ainvoke(
                {**ESTADO_INICIAL, "solicitud_id": str(solicitud_id)},
                {"configurable": {"thread_id": str(solicitud_id)}},
                context=ejecucion,
            )
            duracion = round((self._reloj() - inicio).total_seconds() * 1000)
            if ejecucion.solicitud is not None:
                await unidad.eventos_tecnicos.agregar(
                    EventoTecnico(
                        solicitud_id=solicitud_id,
                        etapa="orquestacion",
                        inicio=inicio,
                        duracion_ms=max(duracion, 0),
                    )
                )
                await unidad.confirmar()
        _registro.info(
            "solicitud orquestada",
            extra={
                "tipo_evento": "orquestacion",
                "solicitud_id": str(solicitud_id),
                "tipo": final.get("tipo"),
                "agente": final.get("agente"),
                "estado": final.get("estado_final"),
                "fallo": final.get("fallo"),
                "etiqueta": final.get("etiqueta"),
                "duracion_ms": duracion,
            },
        )
        estado_final: str | None = final.get("estado_final")
        return estado_final

    def lanzar(self, solicitud_id: uuid.UUID, contexto: ContextoAcceso) -> None:
        """Solo pruebas: atiende en segundo plano dentro del proceso de la API."""
        tarea = asyncio.create_task(self.atender(solicitud_id, contexto))
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)

    async def esperar(self) -> None:
        while self._tareas:
            await asyncio.gather(*list(self._tareas), return_exceptions=True)

    def cancelar(self) -> None:
        for tarea in list(self._tareas):
            tarea.cancel()
