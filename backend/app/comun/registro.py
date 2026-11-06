"""Registro estructurado en JSON (hoja de ruta, apartado 4.6).

Reglas:

* Una línea JSON por evento, con ``incidencia_id`` cuando existe una petición en curso.
* Nunca se registra texto de borradores, de propuestas ni contraseñas. Quien llama
  pasa solo metadatos (etapa, duración, resultado); este módulo además elimina del
  registro cualquier campo cuyo nombre sugiera un secreto o contenido del usuario.
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from typing import Any

from app.comun.contexto import obtener_incidencia_id

NOMBRE_REGISTRADOR = "sma"

# Campos que nunca se escriben en el registro técnico.
FRAGMENTOS_PROHIBIDOS = ("contrasena", "password", "clave", "secreto", "cookie", "authorization")
NOMBRES_PROHIBIDOS = frozenset({"token", "texto", "contenido", "borrador", "propuesta", "cuerpo"})

_ATRIBUTOS_ESTANDAR = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


def _es_prohibido(nombre: str) -> bool:
    minuscula = nombre.lower()
    return minuscula in NOMBRES_PROHIBIDOS or any(f in minuscula for f in FRAGMENTOS_PROHIBIDOS)


class FormateadorJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        evento: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "registrador": record.name,
            "evento": record.getMessage(),
            "incidencia_id": obtener_incidencia_id(),
        }
        for nombre, valor in record.__dict__.items():
            if nombre in _ATRIBUTOS_ESTANDAR or nombre.startswith("_") or _es_prohibido(nombre):
                continue
            evento[nombre] = valor
        if record.exc_info:
            # La traza contiene nombres de archivo y líneas; el mensaje de la excepción
            # puede incluir datos, por eso solo se escribe el tipo y la pila.
            tipo = record.exc_info[0]
            evento["excepcion"] = tipo.__name__ if tipo else None
            # Solo archivo, línea y función: sin el código fuente de cada línea.
            evento["traza"] = [
                f"{marco.filename}:{marco.lineno}:{marco.name}"
                for marco in traceback.extract_tb(record.exc_info[2])
            ]
        return json.dumps(evento, ensure_ascii=False, default=str)


class _ManejadorSalidaEstandar(logging.StreamHandler):  # type: ignore[type-arg]
    """Escribe en el ``sys.stdout`` vigente al emitir (no en el de la configuración)."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property
    def stream(self) -> Any:
        return sys.stdout

    @stream.setter
    def stream(self, _valor: Any) -> None:
        pass


def configurar_registro(nivel: str = "INFO") -> logging.Logger:
    """Configura el registrador raíz de la aplicación para emitir JSON por stdout."""
    registrador = logging.getLogger(NOMBRE_REGISTRADOR)
    registrador.setLevel(nivel)
    registrador.handlers.clear()
    manejador = _ManejadorSalidaEstandar()
    manejador.setFormatter(FormateadorJson())
    registrador.addHandler(manejador)
    registrador.propagate = False
    return registrador


def obtener_registrador(nombre: str = "") -> logging.Logger:
    return logging.getLogger(f"{NOMBRE_REGISTRADOR}.{nombre}" if nombre else NOMBRE_REGISTRADOR)
