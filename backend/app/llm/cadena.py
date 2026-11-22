"""Cadena de respaldo, reintentos, límites, validación y registro (T17-01, apartados 3 a 5).

``CadenaModelos`` implementa ``ModeloLenguaje``. Por cada proveedor, en orden:

1. Reserva cupo en su limitador (R-01).
2. Llama al proveedor y valida la salida con Pydantic.
3. Ante un error de disponibilidad reintenta hasta 2 veces con espera exponencial (4.4)
   y después pasa al siguiente proveedor. Un error de la solicitud o una salida que no
   cumple el esquema se reportan sin pasar al respaldo.

Cada intento deja un evento técnico (proveedor, modelo, tokens, duración, costo y tipo de
error), sin contenido.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.comun.registro import obtener_registrador
from app.llm import mensajes
from app.llm.esquema import validar
from app.llm.limitador import LimitadorProveedor
from app.llm.modelos import (
    EntradaModelo,
    ErrorDisponibilidad,
    ErrorModelo,
    Instruccion,
    MotivoError,
    Proveedor,
    ResultadoEstructurado,
)
from app.llm.proveedores import ProveedorModelo

REINTENTOS = 2
ESPERA_BASE_S = 1.0
ESPERA_MAXIMA_REINTENTO_S = 20.0
MILLON = Decimal(1_000_000)

_registro = obtener_registrador("llm")


@dataclass(frozen=True)
class Precio:
    entrada_usd_millon: Decimal | None = None
    salida_usd_millon: Decimal | None = None

    def costo(self, entrada: int | None, salida: int | None) -> Decimal | None:
        if self.entrada_usd_millon is None or self.salida_usd_millon is None:
            return None
        if entrada is None and salida is None:
            return None
        total = (Decimal(entrada or 0) * self.entrada_usd_millon) + (
            Decimal(salida or 0) * self.salida_usd_millon
        )
        return (total / MILLON).quantize(Decimal("0.000001"))


@dataclass
class Eslabon:
    proveedor: ProveedorModelo
    limitador: LimitadorProveedor
    precio: Precio
    max_tokens_salida: int


@dataclass(frozen=True)
class EventoLlamada:
    """Lo que se registra de cada intento (``evento_tecnico``), sin contenido."""

    etapa: str
    inicio: datetime
    duracion_ms: int
    proveedor: str
    modelo: str
    tokens_entrada: int | None
    tokens_salida: int | None
    costo_estimado: Decimal | None
    error: str | None


Registrar = Callable[[EventoLlamada], Awaitable[None]]


async def _sin_registro(_: EventoLlamada) -> None:
    return None


class CadenaModelos:
    def __init__(
        self,
        eslabones: Sequence[Eslabon],
        registrar: Registrar = _sin_registro,
        *,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        reloj: Callable[[], float] = time.monotonic,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._eslabones = list(eslabones)
        self._registrar = registrar
        self._dormir = dormir
        self._reloj = reloj
        self._ahora = ahora

    @property
    def proveedores(self) -> list[Proveedor]:
        return [e.proveedor.proveedor for e in self._eslabones]

    async def generar[T: BaseModel](
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[T]
    ) -> ResultadoEstructurado[T]:
        if not self._eslabones:
            raise ErrorDisponibilidad(MotivoError.SIN_PROVEEDORES)
        estimados = mensajes.estimar_tokens(instruccion.texto, mensajes.usuario(entrada))
        intentos = 0
        ultimo: ErrorDisponibilidad | None = None
        for posicion, eslabon in enumerate(self._eslabones):
            for reintento in range(REINTENTOS + 1):
                intentos += 1
                try:
                    return await self._intentar(
                        eslabon, instruccion, entrada, esquema, estimados, intentos, posicion > 0
                    )
                except ErrorDisponibilidad as error:
                    ultimo = error
                    if error.motivo is MotivoError.LIMITE_DIARIO or reintento == REINTENTOS:
                        break
                    espera = error.espera_s or ESPERA_BASE_S * 2**reintento
                    if espera > ESPERA_MAXIMA_REINTENTO_S:
                        break
                    await self._dormir(espera)
            _registro.warning(
                "proveedor no disponible, se pasa al siguiente",
                extra={
                    "tipo_evento": "modelo",
                    "agente": instruccion.agente,
                    "proveedor": eslabon.proveedor.proveedor.value,
                    "motivo": ultimo.motivo.value if ultimo else None,
                },
            )
        assert ultimo is not None
        raise ultimo

    async def _intentar[T: BaseModel](
        self,
        eslabon: Eslabon,
        instruccion: Instruccion,
        entrada: EntradaModelo,
        esquema: type[T],
        estimados: int,
        intentos: int,
        respaldo: bool,
    ) -> ResultadoEstructurado[T]:
        proveedor = eslabon.proveedor
        inicio, comienzo = self._ahora(), self._reloj()
        uso_entrada = uso_salida = None
        error: ErrorModelo | None = None
        version: str | None = None
        try:
            reserva = await eslabon.limitador.reservar(estimados + eslabon.max_tokens_salida)
            respuesta = await proveedor.completar(instruccion, entrada, esquema)
            uso_entrada, uso_salida = respuesta.uso.tokens_entrada, respuesta.uso.tokens_salida
            version = respuesta.version_informada
            if uso_entrada is not None or uso_salida is not None:
                reserva.ajustar((uso_entrada or 0) + (uso_salida or 0))
            datos = validar(esquema, respuesta.texto, proveedor.proveedor)
        except ErrorModelo as fallo:
            error = fallo
            raise
        finally:
            duracion = round((self._reloj() - comienzo) * 1000)
            await self._registrar(
                EventoLlamada(
                    etapa=f"modelo:{instruccion.agente}"[:60],
                    inicio=inicio,
                    duracion_ms=duracion,
                    proveedor=proveedor.proveedor.value,
                    modelo=proveedor.modelo,
                    tokens_entrada=uso_entrada,
                    tokens_salida=uso_salida,
                    costo_estimado=eslabon.precio.costo(uso_entrada, uso_salida),
                    error=f"{type(error).__name__}:{error.motivo.value}" if error else None,
                )
            )
        _registro.info(
            "llamada al modelo",
            extra={
                "tipo_evento": "modelo",
                "agente": instruccion.agente,
                "instruccion": instruccion.identificador,
                "proveedor": proveedor.proveedor.value,
                "modelo": proveedor.modelo,
                "version_informada": version,
                "tokens_entrada": uso_entrada,
                "tokens_salida": uso_salida,
                "duracion_ms": duracion,
                "intentos": intentos,
            },
        )
        return ResultadoEstructurado[esquema](  # type: ignore[valid-type]
            datos=datos,
            proveedor=proveedor.proveedor,
            modelo=proveedor.modelo,
            version_informada=version,
            instruccion=instruccion.identificador,
            huella_instruccion=instruccion.huella,
            tokens_entrada=uso_entrada,
            tokens_salida=uso_salida,
            duracion_ms=duracion,
            costo_estimado=eslabon.precio.costo(uso_entrada, uso_salida),
            intentos=intentos,
            respaldo=respaldo,
        )
