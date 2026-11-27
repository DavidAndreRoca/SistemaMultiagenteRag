"""Decisiones del caso sobre sus resultados y contadores de uso (T31; RF-12, CU-11, HU-10,
CP-18, CP-19, RN-08).

* ``GET /caso/solicitudes/{id}/decision``: las opciones posibles, la decisión vigente y el
  historial del resultado final de la solicitud.
* ``POST /caso/solicitudes/{id}/decision``: registra una decisión sobre el resultado final
  de una solicitud entregada del propio caso. Sobre una propuesta: aceptar, modificar o
  rechazar; tras una abstención ("Sin evidencia suficiente"): continuar o aportar. Una
  decisión nunca se edita: cambiarla registra otra que reemplaza a la anterior, y las dos se
  conservan. La solicitud se bloquea mientras se decide, así dos decisiones simultáneas no
  quedan vigentes a la vez.
* ``GET /caso/contadores``: decisiones vigentes por tipo y opción, y solicitudes entregadas
  por hito frente al uso mínimo orientativo de la configuración (se informa, no bloquea).

Una solicitud de otro caso responde 404, igual que una inexistente (4.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.api.evidencia import SolicitudInexistente
from app.bd.enumeraciones import EstadoSolicitud, OpcionDecision, TipoSolicitud
from app.bd.modelos import Decision, Resultado, Solicitud
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.repositorios.contexto import ContextoAcceso
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad

router = APIRouter(prefix="/caso", tags=["decisiones"])
SOBRE_PROPUESTA = (OpcionDecision.ACEPTAR, OpcionDecision.MODIFICAR, OpcionDecision.RECHAZAR)
TRAS_ABSTENCION = (OpcionDecision.CONTINUAR, OpcionDecision.APORTAR)
_registro = obtener_registrador("decisiones")


class SinResultadoQueDecidir(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sin_resultado",
            "Solo se decide sobre un resultado ya entregado.",
            estado_http=409,
        )


class OpcionNoAdmitida(ErrorAplicacion):
    def __init__(self, admitidas: tuple[OpcionDecision, ...]) -> None:
        super().__init__(
            "opcion_no_admitida",
            "Esa opción no corresponde a este resultado.",
            estado_http=422,
            detalle={"admitidas": [o.value for o in admitidas]},
        )


class DecisionRepetida(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "decision_repetida", "Esa ya es su decisión sobre este resultado.", estado_http=409
        )


class DecisionVista(BaseModel):
    id: uuid.UUID
    opcion: OpcionDecision
    decidida_en: datetime
    reemplaza_a: uuid.UUID | None


class VistaDecision(BaseModel):
    solicitud_id: uuid.UUID
    opciones: list[OpcionDecision]  # vacía si todavía no hay resultado entregado
    vigente: DecisionVista | None
    historial: list[DecisionVista]  # de la más antigua a la más reciente


class PedidoDecision(BaseModel):
    opcion: OpcionDecision


class ContadorTipo(BaseModel):
    tipo: TipoSolicitud
    aceptar: int = 0
    modificar: int = 0
    rechazar: int = 0
    continuar: int = 0
    aportar: int = 0


class UsoHito(BaseModel):
    hito: str
    nombre: str
    solicitudes: int
    minimo: int
    cumple: bool


class Contadores(BaseModel):
    por_tipo: list[ContadorTipo]
    por_hito: list[UsoHito]


def _vista(decision: Decision) -> DecisionVista:
    return DecisionVista(
        id=decision.id,
        opcion=decision.opcion,
        decidida_en=decision.decidida_en,
        reemplaza_a=decision.decision_reemplazada_id,
    )


def opciones_para(resultado: Resultado) -> tuple[OpcionDecision, ...]:
    return TRAS_ABSTENCION if resultado.abstencion else SOBRE_PROPUESTA


async def _resultado_final(
    unidad: Unidad, contexto: ContextoAcceso, solicitud_id: uuid.UUID, bloquear: bool = False
) -> tuple[Solicitud, Resultado | None]:
    solicitud = (
        await unidad.solicitudes.bloquear(contexto, solicitud_id)
        if bloquear
        else await unidad.solicitudes.obtener(contexto, solicitud_id)
    )
    if solicitud is None:
        raise SolicitudInexistente()
    if solicitud.estado is not EstadoSolicitud.ENTREGADA:
        return solicitud, None
    return solicitud, await unidad.resultados.de_solicitud(contexto, solicitud_id)


def en_orden(decisiones: list[Decision]) -> list[Decision]:
    """La cadena de reemplazos, de la primera decisión a la vigente (no depende de la hora:
    dos decisiones pueden registrarse en el mismo instante)."""
    siguiente = {d.decision_reemplazada_id: d for d in decisiones}
    cadena: list[Decision] = []
    actual = siguiente.get(None)
    while actual is not None and len(cadena) < len(decisiones):
        cadena.append(actual)
        actual = siguiente.get(actual.id)
    return cadena


def _vigente(decisiones: list[Decision]) -> Decision | None:
    cadena = en_orden(decisiones)
    return cadena[-1] if cadena else None


@router.get(
    "/solicitudes/{solicitud_id}/decision",
    response_model=VistaDecision,
    summary="Decisión vigente e historial sobre el resultado de una solicitud",
)
async def ver_decision(
    solicitud_id: uuid.UUID, contexto: ContextoCaso, unidad: Unidad
) -> VistaDecision:
    _, resultado = await _resultado_final(unidad, contexto, solicitud_id)
    if resultado is None:
        return VistaDecision(solicitud_id=solicitud_id, opciones=[], vigente=None, historial=[])
    decisiones = en_orden(list(await unidad.decisiones.de_resultado(contexto, resultado.id)))
    vigente = decisiones[-1] if decisiones else None
    return VistaDecision(
        solicitud_id=solicitud_id,
        opciones=list(opciones_para(resultado)),
        vigente=_vista(vigente) if vigente else None,
        historial=[_vista(d) for d in decisiones],
    )


@router.post(
    "/solicitudes/{solicitud_id}/decision",
    response_model=DecisionVista,
    status_code=status.HTTP_201_CREATED,
    responses={409: {}},
    summary="Registrar o cambiar la decisión sobre el resultado de una solicitud",
)
async def decidir(
    solicitud_id: uuid.UUID,
    pedido: PedidoDecision,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> DecisionVista:
    solicitud, resultado = await _resultado_final(unidad, contexto, solicitud_id, bloquear=True)
    if resultado is None:
        raise SinResultadoQueDecidir()
    admitidas = opciones_para(resultado)
    if pedido.opcion not in admitidas:
        raise OpcionNoAdmitida(admitidas)
    vigente = _vigente(list(await unidad.decisiones.de_resultado(contexto, resultado.id)))
    if vigente is not None and vigente.opcion is pedido.opcion:
        raise DecisionRepetida()
    try:
        decision = await unidad.decisiones.agregar(
            contexto,
            Decision(
                resultado_id=resultado.id,
                opcion=pedido.opcion,
                decidida_en=reloj(),
                decision_reemplazada_id=vigente.id if vigente else None,
            ),
        )
        await unidad.confirmar()
    except IntegrityError:  # otra decisión reemplazó a la misma al mismo tiempo
        await unidad.revertir()
        raise DecisionRepetida() from None
    _registro.info(
        "decision registrada",
        extra={
            "tipo_evento": "decision",
            "solicitud_id": str(solicitud.id),
            "tipo": solicitud.tipo.value,
            "opcion": pedido.opcion.value,
            "reemplaza": vigente is not None,
        },
    )
    return _vista(decision)


@router.get("/contadores", response_model=Contadores, summary="Contadores de uso del caso")
async def contadores(contexto: ContextoCaso, unidad: Unidad) -> Contadores:
    por_tipo: dict[TipoSolicitud, ContadorTipo] = {}
    for tipo, opcion, cantidad in await unidad.decisiones.contadores(contexto):
        fila = por_tipo.setdefault(tipo, ContadorTipo(tipo=tipo))
        setattr(fila, opcion.value, cantidad)
    _, parametros = await unidad.configuracion.vigente()
    entregadas = await unidad.solicitudes.entregadas_por_hito(contexto)
    minimo = parametros.uso_minimo_por_hito
    return Contadores(
        por_tipo=[por_tipo[t] for t in TipoSolicitud if t in por_tipo],
        por_hito=[
            UsoHito(
                hito=h.codigo,
                nombre=f"{h.nombre}: {h.contenido}",
                solicitudes=entregadas.get(h.codigo, 0),
                minimo=minimo,
                cumple=entregadas.get(h.codigo, 0) >= minimo,
            )
            for h in sorted(parametros.hitos, key=lambda h: h.orden)
        ],
    )
