"""Arranque: ``python -m app``. Valida la configuración antes de levantar el servidor."""

from __future__ import annotations

import os
import sys

import uvicorn

from app.configuracion import ErrorConfiguracion, cargar_ajustes


def principal() -> int:
    try:
        cargar_ajustes()
    except ErrorConfiguracion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    uvicorn.run(
        "app.main:crear_aplicacion",
        factory=True,
        host=os.environ.get("HOST_API", "0.0.0.0"),
        port=int(os.environ.get("PUERTO_INTERNO_API", "8000")),
        log_config=None,
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
