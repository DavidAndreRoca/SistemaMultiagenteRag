"""Comando de diagnóstico de claves externas: ``python -m app.diagnostico``.

Prueba con una llamada mínima las claves de Groq y OpenAlex (T03). Nunca imprime
una clave: informa solo estado y código HTTP. Sale con código 1 si alguna falla.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from app.configuracion import Ajustes, ErrorConfiguracion, cargar_ajustes

URL_GROQ = "https://api.groq.com/openai/v1/models"
URL_OPENALEX = "https://api.openalex.org/works"
TIEMPO_MAXIMO_S = 15.0


@dataclass(frozen=True)
class Resultado:
    servicio: str
    ok: bool
    detalle: str


def probar_groq(cliente: httpx.Client, ajustes: Ajustes) -> Resultado:
    if ajustes.clave_groq is None or not ajustes.clave_groq.get_secret_value().strip():
        return Resultado("groq", False, "CLAVE_GROQ no está configurada")
    try:
        respuesta = cliente.get(
            URL_GROQ,
            headers={"Authorization": f"Bearer {ajustes.clave_groq.get_secret_value()}"},
        )
    except httpx.HTTPError as error:
        return Resultado("groq", False, f"sin conexión ({type(error).__name__})")
    if respuesta.status_code == 200:
        return Resultado("groq", True, "clave válida (HTTP 200)")
    if respuesta.status_code in (401, 403):
        return Resultado("groq", False, f"clave rechazada (HTTP {respuesta.status_code})")
    return Resultado("groq", False, f"respuesta inesperada (HTTP {respuesta.status_code})")


def probar_openalex(cliente: httpx.Client, ajustes: Ajustes) -> Resultado:
    if ajustes.clave_openalex is None or not ajustes.clave_openalex.get_secret_value().strip():
        return Resultado("openalex", False, "CLAVE_OPENALEX no está configurada")
    parametros = {"per-page": "1", "api_key": ajustes.clave_openalex.get_secret_value()}
    if ajustes.correo_polite:
        parametros["mailto"] = ajustes.correo_polite
    try:
        respuesta = cliente.get(URL_OPENALEX, params=parametros)
    except httpx.HTTPError as error:
        return Resultado("openalex", False, f"sin conexión ({type(error).__name__})")
    if respuesta.status_code == 200:
        return Resultado("openalex", True, "clave válida (HTTP 200)")
    if respuesta.status_code in (401, 403):
        return Resultado("openalex", False, f"clave rechazada (HTTP {respuesta.status_code})")
    return Resultado("openalex", False, f"respuesta inesperada (HTTP {respuesta.status_code})")


def ejecutar_diagnostico(ajustes: Ajustes, cliente: httpx.Client) -> list[Resultado]:
    return [probar_groq(cliente, ajustes), probar_openalex(cliente, ajustes)]


def principal(argumentos: Sequence[str] | None = None) -> int:
    argparse.ArgumentParser(description="Prueba las claves de Groq y OpenAlex.").parse_args(
        argumentos
    )
    try:
        ajustes = cargar_ajustes()
    except ErrorConfiguracion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    with httpx.Client(timeout=TIEMPO_MAXIMO_S) as cliente:
        resultados = ejecutar_diagnostico(ajustes, cliente)
    for r in resultados:
        print(f"[{'OK' if r.ok else 'FALLA'}] {r.servicio}: {r.detalle}")
    return 0 if all(r.ok for r in resultados) else 1


if __name__ == "__main__":
    raise SystemExit(principal())
