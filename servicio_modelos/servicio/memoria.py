"""Memoria del proceso (T08: registro de memoria usada). Solo Linux; en otro sistema, nulo."""

from __future__ import annotations

from pathlib import Path

from servicio.esquemas import Memoria

_ESTADO = Path("/proc/self/status")


def _leer_kb(contenido: str, campo: str) -> float | None:
    for linea in contenido.splitlines():
        if linea.startswith(f"{campo}:"):
            return round(int(linea.split()[1]) / 1024, 1)
    return None


def memoria_actual(ruta: Path = _ESTADO) -> Memoria:
    try:
        contenido = ruta.read_text(encoding="ascii")
    except OSError:
        return Memoria()
    return Memoria(residente_mb=_leer_kb(contenido, "VmRSS"), pico_mb=_leer_kb(contenido, "VmHWM"))
