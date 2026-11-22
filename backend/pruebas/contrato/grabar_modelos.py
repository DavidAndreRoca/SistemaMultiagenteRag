"""Graba una respuesta real de cada proveedor de modelos para las pruebas de contrato (T17).

``python -m pruebas.contrato.grabar_modelos [groq] [deepseek] [gemini]`` (por defecto,
todos los que tengan clave en el entorno). Usa la instrucción ``contrato/v1`` y un
fragmento ficticio, con el mismo cuerpo que arma el adaptador. Guarda en
``pruebas/contrato/modelos/<proveedor>.json`` el estado HTTP y el cuerpo de la respuesta.

* No guarda cabeceras ni la petición: así no queda ninguna clave. Antes de escribir,
  comprueba que la clave no aparece en lo grabado.
* Cada proveedor recibe una sola llamada (R-01).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from app.configuracion import cargar_ajustes
from app.instrucciones import cargador
from app.llm.modelos import BloqueDatos, EntradaModelo, Proveedor
from app.llm.proveedores import (
    URL_DEEPSEEK,
    URL_GROQ,
    ProveedorCompatibleOpenAI,
    ProveedorGemini,
    ProveedorModelo,
)

DESTINO = Path(__file__).parent / "modelos"
MODELOS = {
    "groq": "openai/gpt-oss-120b",
    "deepseek": "deepseek-flash",
    "gemini": "gemini-3.8-flash",
}
ENTRADA = EntradaModelo(
    tarea="Clasifica el fragmento F1.",
    datos=[
        BloqueDatos(
            etiqueta="F1",
            contenido=(
                "Participaron 84 estudiantes ficticios de primer año, asignados a un grupo con"
                " tutoría entre pares y a un grupo control, en un diseño cuasiexperimental."
            ),
        )
    ],
)


class Clasificacion(BaseModel):
    """El esquema de la tarea de contrato (``instrucciones/contrato/v1.md``)."""

    seccion: Literal["introduccion", "metodos", "resultados", "discusion"]
    idioma: str = Field(min_length=2, max_length=2)
    cita: str


class Grabadora(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.interno = httpx.AsyncHTTPTransport()
        self.respuestas: list[tuple[int, bytes]] = []

    async def handle_async_request(self, peticion: httpx.Request) -> httpx.Response:
        respuesta = await self.interno.handle_async_request(peticion)
        contenido = await respuesta.aread()
        self.respuestas.append((respuesta.status_code, contenido))
        return httpx.Response(respuesta.status_code, content=contenido, headers=respuesta.headers)


def _proveedor(nombre: str, clave: str, cliente: httpx.AsyncClient) -> ProveedorModelo:
    if nombre == "groq":
        return ProveedorCompatibleOpenAI(
            Proveedor.GROQ, MODELOS[nombre], clave, cliente, URL_GROQ, esquema_estricto=True
        )
    if nombre == "deepseek":
        return ProveedorCompatibleOpenAI(
            Proveedor.DEEPSEEK,
            MODELOS[nombre],
            clave,
            cliente,
            URL_DEEPSEEK,
            esquema_estricto=False,
        )
    return ProveedorGemini(MODELOS[nombre], clave, cliente)


async def grabar(nombre: str, clave: str) -> None:
    grabadora = Grabadora()
    instruccion = cargador.cargar("contrato", "v1")
    async with httpx.AsyncClient(transport=grabadora, timeout=120) as cliente:
        try:
            respuesta = await _proveedor(nombre, clave, cliente).completar(
                instruccion, ENTRADA, Clasificacion
            )
            resumen = f"{respuesta.version_informada}, {respuesta.uso}"
        except Exception as error:  # se graba igual: el estado HTTP queda registrado
            resumen = f"falló: {type(error).__name__}"
    estado, contenido = grabadora.respuestas[-1]
    if clave.encode() in contenido:
        raise SystemExit(f"{nombre}: la respuesta contiene la clave; no se graba")
    cuerpo = json.loads(contenido) if contenido else None
    DESTINO.mkdir(exist_ok=True)
    (DESTINO / f"{nombre}.json").write_text(
        json.dumps(
            {"proveedor": nombre, "modelo": MODELOS[nombre], "estado": estado, "cuerpo": cuerpo},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{nombre}: HTTP {estado}; {resumen}")


async def principal(nombres: list[str]) -> None:
    ajustes = cargar_ajustes()
    claves = {
        "groq": ajustes.clave_groq,
        "deepseek": ajustes.clave_deepseek,
        "gemini": ajustes.clave_gemini,
    }
    for nombre in nombres or list(MODELOS):
        secreto = claves[nombre]
        if secreto is None or not secreto.get_secret_value().strip():
            print(f"{nombre}: sin clave en el entorno; se omite")
            continue
        await grabar(nombre, secreto.get_secret_value().strip())


if __name__ == "__main__":
    asyncio.run(principal(sys.argv[1:]))
