"""Registro JSON de una línea por evento. Nunca se registran textos ni consultas (4.6)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_PERMITIDOS = frozenset(
    {"ruta", "n_textos", "duracion_ms", "espera_ms", "estado_http", "codigo", "modelo", "revision"}
)


class _FormateadorJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        evento: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "registrador": record.name,
            "evento": record.getMessage(),
        }
        # Lista blanca: solo metadatos conocidos, nunca contenido.
        evento.update({k: v for k, v in record.__dict__.items() if k in _PERMITIDOS})
        if record.exc_info and record.exc_info[0] is not None:
            evento["excepcion"] = record.exc_info[0].__name__
        return json.dumps(evento, ensure_ascii=False, default=str)


class _ManejadorSalida(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stdout.write(self.format(record) + "\n")
            sys.stdout.flush()
        except Exception:  # pragma: no cover - el registro nunca debe tumbar el servicio
            self.handleError(record)


def configurar_registro() -> logging.Logger:
    registrador = logging.getLogger("servicio_modelos")
    if not registrador.handlers:
        manejador = _ManejadorSalida()
        manejador.setFormatter(_FormateadorJson())
        registrador.addHandler(manejador)
        registrador.setLevel(logging.INFO)
        registrador.propagate = False
    return registrador
