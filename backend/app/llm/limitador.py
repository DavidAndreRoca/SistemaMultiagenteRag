"""Limitador del lado del cliente por proveedor (T17-01, apartado 4; riesgo R-01).

Ventanas deslizantes de un minuto y de un día para solicitudes y tokens. Antes de cada
llamada se reserva una estimación; al terminar se corrige con el uso real. Si la ventana
del minuto no alcanza, se espera hasta ``espera_maxima_s``; si no alcanza la del día, o
la espera sería mayor, la llamada falla por disponibilidad y pasa al respaldo.

Es por proceso: la API y el trabajador de T28 tendrán cada uno el suyo (apartado 4).
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.llm.modelos import ErrorDisponibilidad, MotivoError, Proveedor

MINUTO = 60.0
DIA = 86_400.0


@dataclass(frozen=True)
class Limites:
    rpm: int | None = None
    rpd: int | None = None
    tpm: int | None = None
    tpd: int | None = None


@dataclass
class _Registro:
    momento: float
    tokens: int


@dataclass
class Reserva:
    registro: _Registro
    limitador: LimitadorProveedor

    def ajustar(self, tokens_reales: int | None) -> None:
        if tokens_reales is not None:
            self.registro.tokens = tokens_reales


@dataclass
class LimitadorProveedor:
    proveedor: Proveedor
    limites: Limites
    espera_maxima_s: float = 30.0
    reloj: Callable[[], float] = time.monotonic
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep
    _registros: deque[_Registro] = field(default_factory=deque)
    _candado: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def reservar(self, tokens_estimados: int) -> Reserva:
        async with self._candado:
            ahora = self.reloj()
            self._purgar(ahora)
            if self._excede(ahora, DIA, tokens_estimados, self.limites.rpd, self.limites.tpd):
                raise ErrorDisponibilidad(MotivoError.LIMITE_DIARIO, self.proveedor)
            espera = self._espera_minuto(ahora, tokens_estimados)
            if espera > self.espera_maxima_s:
                raise ErrorDisponibilidad(
                    MotivoError.LIMITE_DE_TASA, self.proveedor, "espera del limitador", espera
                )
            if espera > 0:
                await self.dormir(espera)
            registro = _Registro(self.reloj(), tokens_estimados)
            self._registros.append(registro)
            return Reserva(registro, self)

    def _purgar(self, ahora: float) -> None:
        while self._registros and ahora - self._registros[0].momento >= DIA:
            self._registros.popleft()

    def _excede(
        self, ahora: float, ventana: float, tokens: int, max_sol: int | None, max_tok: int | None
    ) -> bool:
        dentro = [r for r in self._registros if ahora - r.momento < ventana]
        if max_sol is not None and len(dentro) + 1 > max_sol:
            return True
        return max_tok is not None and sum(r.tokens for r in dentro) + tokens > max_tok

    def _espera_minuto(self, ahora: float, tokens: int) -> float:
        """Segundos hasta que la ventana del minuto admita esta llamada."""
        rpm, tpm = self.limites.rpm, self.limites.tpm
        if tpm is not None and tokens > tpm:
            return float("inf")  # nunca cabe en un minuto
        dentro = [r for r in self._registros if ahora - r.momento < MINUTO]
        espera = 0.0
        if rpm is not None and len(dentro) + 1 > rpm:
            espera = max(espera, MINUTO - (ahora - dentro[len(dentro) - rpm].momento))
        if tpm is not None:
            usados = sum(r.tokens for r in dentro)
            for registro in dentro:  # se liberan en orden de antigüedad
                if usados + tokens <= tpm:
                    break
                usados -= registro.tokens
                espera = max(espera, MINUTO - (ahora - registro.momento))
        return espera
