"""Contrato OpenAPI versionado de la API (T13; hoja de ruta, 4.2 y RNF-22).

``python -m app.contrato`` escribe ``docs/api/openapi.json``, del que la interfaz genera
su cliente tipado (``npm run generar:api`` en ``frontend/``). Una prueba de arquitectura
falla si el archivo no coincide con la aplicación: así el cliente nunca se escribe a mano
ni queda desfasado. Los ajustes son ficticios: el contrato no depende del entorno y no
se conecta a la base.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.configuracion import cargar_ajustes
from app.main import crear_aplicacion

RUTA_CONTRATO = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"
_AJUSTES_DEL_CONTRATO = {
    "ENTORNO": "pruebas",
    "URL_BD": "postgresql+psycopg://contrato:contrato@127.0.0.1:1/contrato",
    "SECRETO_SESION": "solo-para-generar-el-contrato-0123456789abcdef",
}


# FastAPI describe cada respuesta con el nombre del estado de ``http.HTTPStatus``, que
# cambió en Python 3.13 (RFC 9110). Se fijan los de la RFC para que el contrato sea el
# mismo con 3.12 (contenedor y CI) y con 3.13.
NOMBRES_DE_ESTADO = {"413": "Content Too Large", "422": "Unprocessable Content"}


def _normalizar(contrato: dict[str, Any]) -> dict[str, Any]:
    for operaciones in contrato.get("paths", {}).values():
        for operacion in operaciones.values():
            for codigo, respuesta in operacion.get("responses", {}).items():
                if codigo in NOMBRES_DE_ESTADO and isinstance(respuesta, dict):
                    respuesta["description"] = NOMBRES_DE_ESTADO[codigo]
    return contrato


def generar() -> str:
    aplicacion = crear_aplicacion(cargar_ajustes(_AJUSTES_DEL_CONTRATO))
    contrato = _normalizar(aplicacion.openapi())
    return json.dumps(contrato, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    RUTA_CONTRATO.parent.mkdir(parents=True, exist_ok=True)
    RUTA_CONTRATO.write_text(generar(), encoding="utf-8", newline="\n")
    print(f"Contrato escrito en {RUTA_CONTRATO}")
