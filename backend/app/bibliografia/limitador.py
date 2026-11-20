"""Limitador de tasa por servicio: cubeta de fichas (T14-01, apartado 4).

Cada consulta toma una ficha. La cubeta se llena a ``tasa`` fichas por segundo hasta
``capacidad`` (la ráfaga admitida). Si está vacía, ``adquirir`` espera lo justo para que
haya una. El reloj y la espera se inyectan para probarlo sin tiempo real.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

Reloj = Callable[[], float]
Dormir = Callable[[float], Awaitable[None]]


class CubetaDeFichas:
    def __init__(
        self,
        tasa: float,
        capacidad: float | None = None,
        *,
        reloj: Reloj = time.monotonic,
        dormir: Dormir = asyncio.sleep,
    ) -> None:
        if tasa <= 0:
            raise ValueError("la tasa debe ser positiva")
        self.tasa = tasa
        self.capacidad = max(capacidad if capacidad is not None else tasa, 1.0)
        self._fichas = self.capacidad
        self._reloj = reloj
        self._dormir = dormir
        self._ultima = reloj()
        self._candado = asyncio.Lock()

    def _rellenar(self) -> None:
        ahora = self._reloj()
        self._fichas = min(self.capacidad, self._fichas + (ahora - self._ultima) * self.tasa)
        self._ultima = ahora

    async def adquirir(self) -> None:
        """Espera hasta tener una ficha y la consume. Las esperas se atienden en orden."""
        async with self._candado:
            self._rellenar()
            if self._fichas < 1:
                await self._dormir((1 - self._fichas) / self.tasa)
                self._rellenar()
            self._fichas -= 1
