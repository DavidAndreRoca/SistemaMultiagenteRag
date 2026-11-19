"""Tiempo y memoria por etapa de la ingesta (optimización del flujo de desarrollo, T10).

``Etapas`` acumula, por nombre de etapa, los segundos y el pico de memoria residente del
proceso. En Linux el pico se reinicia al empezar cada etapa (``/proc/self/clear_refs``),
así que cada valor corresponde a esa etapa; en otros sistemas no se informa memoria.

La memoria del servicio de modelos y de GROBID es de otros procesos: se mide aparte.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ESTADO = Path("/proc/self/status")
REINICIO = Path("/proc/self/clear_refs")


def _reiniciar_pico() -> bool:
    try:
        REINICIO.write_text("5")
    except OSError:
        return False
    return True


def pico_mb() -> float | None:
    """Pico de memoria residente del proceso (VmHWM), en MB; ``None`` fuera de Linux."""
    try:
        for linea in ESTADO.read_text().splitlines():
            if linea.startswith("VmHWM:"):
                return round(int(linea.split()[1]) / 1024, 1)
    except OSError:
        return None
    return None


class Etapas:
    def __init__(self) -> None:
        self.segundos: dict[str, float] = {}
        self.memoria_mb: dict[str, float] = {}

    @contextmanager
    def medir(self, nombre: str) -> Iterator[None]:
        reiniciado = _reiniciar_pico()
        inicio = time.perf_counter()
        try:
            yield
        finally:
            self.segundos[nombre] = round(
                self.segundos.get(nombre, 0.0) + time.perf_counter() - inicio, 3
            )
            pico = pico_mb() if reiniciado else None
            if pico is not None:
                self.memoria_mb[nombre] = max(self.memoria_mb.get(nombre, 0.0), pico)

    @property
    def total(self) -> float:
        return round(sum(self.segundos.values()), 3)
