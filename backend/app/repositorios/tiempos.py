"""Datos que devuelve el monitoreo de latencias (T30): solo tipos y duraciones."""

from __future__ import annotations

from dataclasses import dataclass

from app.bd.enumeraciones import TipoSolicitud


@dataclass(frozen=True)
class TiemposSolicitud:
    tipo: TipoSolicitud
    total_ms: int  # de la creación a la entrega: lo que espera el estudiante
    etapas: dict[str, int]  # orquestacion, ejecucion, verificacion, reintento, recuperacion...
