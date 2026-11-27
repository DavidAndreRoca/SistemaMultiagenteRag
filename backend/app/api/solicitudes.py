"""Estado en tiempo real, reenvío y otra solicitud con el mismo alcance (T29; RF-02, RF-22,
F-06, F-16; Fase 1, 7.2).

* ``GET /caso/solicitudes/{id}/eventos``: eventos enviados por el servidor con el estado de
  la solicitud (recibida, asignada, recuperando, generando, verificando, reintentando,
  entregada, no atendida). Valida el ``ContextoAcceso`` antes de transmitir: una solicitud de
  otro caso responde 404, igual que una inexistente. Al conectarse envía el estado actual,
  así que una reconexión (``EventSource`` reconecta solo) parte de él; después envía cada
  cambio y termina en un estado final. Como el trabajador es otro proceso, el canal consulta
  la base cada ``INTERVALO_EVENTOS_S``; el canal se cierra a los ``DURACION_MAXIMA_S`` y el
  navegador vuelve a conectarse, con la sesión validada de nuevo.
* ``POST /caso/solicitudes/{id}/reenvio``: una solicitud "no atendida" se vuelve a pedir como
  solicitud nueva enlazada a la original (``solicitud_origen_id``), con la configuración
  vigente (RNF-21).
* ``POST /caso/solicitudes/{id}/mismo-alcance``: otra solicitud de un tipo distinto sobre el
  mismo alcance, para un pedido de varias dimensiones (por ejemplo, la metodología de la
  sección cuya estructura se revisó). Se valida como cualquier solicitud nueva del tipo.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agentes.seccion import AtencionPorAlcance
from app.api.evidencia import SolicitudInexistente
from app.bd.enumeraciones import ALCANCES_ADMITIDOS, EstadoSolicitud, TipoSolicitud
from app.bd.modelos import Solicitud
from app.comun.errores import ErrorAplicacion
from app.orquestacion.en_api import ejecutor_de, encolar
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad

router = APIRouter(prefix="/caso/solicitudes", tags=["solicitudes"])

FINALES = frozenset(
    {EstadoSolicitud.ENTREGADA, EstadoSolicitud.NO_ATENDIDA, EstadoSolicitud.RECHAZADA}
)
INTERVALO_EVENTOS_S = 1.0
LATIDO_S = 15.0
DURACION_MAXIMA_S = 300.0
REINTENTO_CLIENTE_MS = 3000


class SolicitudNoReenviable(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "no_reenviable",
            "Solo se puede volver a pedir una solicitud que no pudo atenderse.",
            estado_http=409,
        )


class MismoAlcanceNoAdmitido(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "mismo_alcance_no_admitido",
            "Ese tipo de solicitud no admite el alcance de esta solicitud.",
            estado_http=422,
        )


class EstadoEvento(BaseModel):
    estado: EstadoSolicitud
    motivo: str | None
    intentos_tecnicos: int


class SolicitudNueva(BaseModel):
    id: uuid.UUID
    tipo: TipoSolicitud
    estado: EstadoSolicitud
    creada_en: datetime
    solicitud_origen_id: uuid.UUID | None


class PedidoMismoAlcance(BaseModel):
    tipo: TipoSolicitud


def _nueva(solicitud: Solicitud) -> SolicitudNueva:
    return SolicitudNueva(
        id=solicitud.id,
        tipo=solicitud.tipo,
        estado=solicitud.estado,
        creada_en=solicitud.creada_en,
        solicitud_origen_id=solicitud.solicitud_origen_id,
    )


async def _propia(unidad: Unidad, contexto: ContextoAcceso, solicitud_id: uuid.UUID) -> Solicitud:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None:  # de otro caso o inexistente: lo mismo (4.4)
        raise SolicitudInexistente()
    return solicitud


def _evento(numero: int, estado: EstadoEvento) -> str:
    return f"id: {numero}\nevent: estado\ndata: {estado.model_dump_json()}\n\n"


@router.get(
    "/{solicitud_id}/eventos",
    summary="Estado de una solicitud en tiempo real (eventos enviados por el servidor)",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def eventos(
    solicitud_id: uuid.UUID, peticion: Request, contexto: ContextoCaso, unidad: Unidad
) -> StreamingResponse:
    await _propia(unidad, contexto, solicitud_id)  # el contexto se valida antes de transmitir
    abrir = fabrica_de_unidades(peticion.app.state.fabrica_sesiones)
    intervalo: float = getattr(peticion.app.state, "intervalo_eventos_s", INTERVALO_EVENTOS_S)

    async def flujo() -> AsyncIterator[str]:
        yield f"retry: {REINTENTO_CLIENTE_MS}\n\n"
        inicio = ultimo_envio = time.monotonic()
        anterior: EstadoEvento | None = None
        numero = 0
        while time.monotonic() - inicio < DURACION_MAXIMA_S:
            async with abrir() as propia:
                solicitud = await propia.solicitudes.obtener(contexto, solicitud_id)
            if solicitud is None:
                return
            actual = EstadoEvento(
                estado=solicitud.estado,
                motivo=solicitud.motivo,
                intentos_tecnicos=solicitud.intentos_tecnicos,
            )
            if actual != anterior:
                numero += 1
                yield _evento(numero, actual)
                anterior, ultimo_envio = actual, time.monotonic()
            if actual.estado in FINALES:
                return
            if time.monotonic() - ultimo_envio >= LATIDO_S:
                yield ": latido\n\n"
                ultimo_envio = time.monotonic()
            if await peticion.is_disconnected():
                return
            await asyncio.sleep(intervalo)

    return StreamingResponse(
        flujo(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/{solicitud_id}/reenvio",
    response_model=SolicitudNueva,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}},
    summary="Volver a pedir una solicitud no atendida, enlazada a la original",
)
async def reenviar(
    solicitud_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> SolicitudNueva:
    original = await _propia(unidad, contexto, solicitud_id)
    if original.estado is not EstadoSolicitud.NO_ATENDIDA:
        raise SolicitudNoReenviable()
    configuracion, _ = await unidad.configuracion.vigente()
    ahora = reloj()
    nueva = await unidad.solicitudes.agregar(
        contexto,
        Solicitud(
            version_id=original.version_id,
            tipo=original.tipo,
            alcance_tipo=original.alcance_tipo,
            alcance_ref=original.alcance_ref,
            configuracion_id=configuracion.id,
            estado=EstadoSolicitud.RECIBIDA,
            solicitud_origen_id=original.id,
            creada_en=ahora,
            actualizada_en=ahora,
        ),
    )
    await unidad.confirmar()
    encolar(peticion, nueva, contexto)
    return _nueva(nueva)


@router.post(
    "/{solicitud_id}/mismo-alcance",
    response_model=SolicitudNueva,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}, 503: {}},
    summary="Pedir otro tipo de revisión sobre el mismo alcance",
)
async def mismo_alcance(
    solicitud_id: uuid.UUID,
    pedido: PedidoMismoAlcance,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
) -> SolicitudNueva:
    original = await _propia(unidad, contexto, solicitud_id)
    if pedido.tipo is original.tipo or original.alcance_tipo not in ALCANCES_ADMITIDOS[pedido.tipo]:
        raise MismoAlcanceNoAdmitido()
    ejecutor = await ejecutor_de(peticion, unidad, pedido.tipo)
    if not isinstance(ejecutor, AtencionPorAlcance) or (
        ejecutor.alcance_tipo is not original.alcance_tipo
    ):
        raise MismoAlcanceNoAdmitido()
    # Se valida como cualquier solicitud nueva: la versión vigente debe tener ese alcance.
    nueva = await ejecutor.iniciar(unidad, contexto, original.alcance_ref or "")
    encolar(peticion, nueva, contexto)
    return _nueva(nueva)
