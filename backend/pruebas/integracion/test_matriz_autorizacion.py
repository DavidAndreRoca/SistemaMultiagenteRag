"""Recorre la matriz de autorización con todas las combinaciones de sesión (T05, T06).

* Sin sesión: 401 en toda ruta que no sea pública.
* A1 en rutas de A2 y A2 en rutas de A1: 403.
* Sesión del caso B en rutas de datos de caso: nunca ve datos del caso A.

Las rutas con archivo (T11) se piden como formulario con un .docx de muestra, y
``{VERSION_A}`` es una versión real del caso A, que el caso B no debe ver.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from pruebas.integracion.conftest import (
    Entorno,
    crear_caso,
    crear_tema,
    entrar_y_cambiar,
    primera_credencial,
)
from pruebas.matriz_autorizacion import MATRIZ, Entrada, Politica

pytestmark = pytest.mark.integracion

DOCX = Path(__file__).parents[1] / "datos" / "docx"
VALORES: dict[str, str] = {"{CASO_A}": "CASO-A"}


def _ruta(ruta: str, entrada: Entrada) -> str:
    concreta = entrada.ejemplo or ruta
    for marca, valor in VALORES.items():
        concreta = concreta.replace(marca, valor)
    return concreta


async def _pedir(
    cliente: httpx.AsyncClient, metodo: str, ruta: str, entrada: Entrada
) -> httpx.Response:
    if entrada.archivo is not None:
        archivos = {"archivo": (entrada.archivo, (DOCX / entrada.archivo).read_bytes())}
        return await cliente.request(
            metodo, _ruta(ruta, entrada), data=entrada.formulario, files=archivos
        )
    cuerpo = entrada.cuerpo if metodo in {"POST", "PUT", "PATCH"} else None
    return await cliente.request(metodo, _ruta(ruta, entrada), json=cuerpo)


async def test_matriz_de_autorizacion(entorno: Entorno, investigador: httpx.AsyncClient) -> None:
    await crear_tema(investigador, "TEMA-A")
    await crear_tema(investigador, "TEMA-B")
    caso_a = await crear_caso(investigador, "CASO-A", "TEMA-A")
    caso_b = await crear_caso(investigador, "CASO-B", "TEMA-B")

    async with (
        entorno.cliente() as anonimo,
        entorno.cliente() as estudiante_a,
        entorno.cliente() as estudiante_b,
    ):
        await entrar_y_cambiar(estudiante_a, *primera_credencial(caso_a))
        await entrar_y_cambiar(estudiante_b, *primera_credencial(caso_b))
        version_a = await estudiante_a.post(
            "/caso/versiones",
            data={"hito": "avance_1"},
            files={"archivo": ("a.docx", (DOCX / "valido.docx").read_bytes())},
        )
        assert version_a.status_code == 201, version_a.text
        VALORES["{VERSION_A}"] = version_a.json()["version"]["id"]

        fallos: list[str] = []
        for (metodo, ruta), entrada in MATRIZ.items():
            if metodo == "DELETE" and ruta == "/sesion":
                continue  # cerraría la sesión de prueba; se cubre en test_sesion
            if ruta == "/sesion/contrasena":
                continue  # cambia la contraseña; se cubre en test_sesion

            sin_sesion = await _pedir(anonimo, metodo, ruta, entrada)
            if entrada.politica is not Politica.PUBLICA and sin_sesion.status_code != 401:
                fallos.append(f"{metodo} {ruta} sin sesión -> {sin_sesion.status_code}")

            if entrada.politica is Politica.INVESTIGADOR:
                r = await _pedir(estudiante_a, metodo, ruta, entrada)
                if r.status_code != 403:
                    fallos.append(f"{metodo} {ruta} con A1 -> {r.status_code}")
            if entrada.politica is Politica.CASO:
                r = await _pedir(investigador, metodo, ruta, entrada)
                if r.status_code != 403:
                    fallos.append(f"{metodo} {ruta} con A2 -> {r.status_code}")
                propio = await _pedir(estudiante_a, metodo, ruta, entrada)
                if propio.status_code >= 400:
                    fallos.append(f"{metodo} {ruta} con su caso -> {propio.status_code}")
            if entrada.datos_de_caso:
                ajeno = await _pedir(estudiante_b, metodo, ruta, entrada)
                datos_de_a = ("CASO-A", "TEMA-A", VALORES["{VERSION_A}"])
                if any(dato in ajeno.text for dato in datos_de_a):
                    fallos.append(f"{metodo} {ruta}: el caso B ve datos del caso A")
        assert fallos == []
