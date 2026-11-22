"""Esquema JSON estricto a partir de un modelo Pydantic y validación local (T17-01).

El modo estricto de Groq exige que todo objeto declare ``additionalProperties: false`` y
liste todas sus propiedades en ``required``. Un campo opcional se expresa como unión con
``null``. Se quitan las claves que no forman parte del subconjunto admitido
(``default``, ``title``, formatos). La validación local con Pydantic se hace siempre,
aunque el proveedor garantice el esquema.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from app.llm.modelos import Proveedor, SalidaInvalida

CLAVES_DESCARTADAS = frozenset({"default", "title", "examples", "format"})
NOMBRADOS = frozenset({"properties", "$defs"})


def esquema_estricto(modelo: type[BaseModel]) -> dict[str, Any]:
    ajustado: dict[str, Any] = _ajustar(modelo.model_json_schema())
    return ajustado


def _ajustar(nodo: Any) -> Any:
    if isinstance(nodo, list):
        return [_ajustar(n) for n in nodo]
    if not isinstance(nodo, dict):
        return nodo
    ajustado: dict[str, Any] = {}
    for clave, valor in nodo.items():
        if clave in NOMBRADOS and isinstance(valor, dict):
            # Nombres de propiedades o definiciones: se conservan aunque se llamen "title".
            ajustado[clave] = {nombre: _ajustar(sub) for nombre, sub in valor.items()}
        elif clave not in CLAVES_DESCARTADAS:
            ajustado[clave] = _ajustar(valor)
    if ajustado.get("type") == "object" and "properties" in ajustado:
        ajustado["required"] = list(ajustado["properties"])
        ajustado["additionalProperties"] = False
    return ajustado


def nombre_esquema(modelo: type[BaseModel]) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in modelo.__name__)[:64]


def validar[T: BaseModel](modelo: type[T], texto: str, proveedor: Proveedor) -> T:
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        raise SalidaInvalida(proveedor, ["la respuesta no es JSON"]) from None
    try:
        return modelo.model_validate(datos)
    except ValidationError as error:
        # Solo la ubicación y el tipo de cada error: nunca los valores (4.6).
        errores = [
            f"{'.'.join(str(p) for p in e['loc']) or '(raíz)'}: {e['type']}"
            for e in error.errors(include_input=False, include_url=False)
        ]
        raise SalidaInvalida(proveedor, errores[:10]) from None
