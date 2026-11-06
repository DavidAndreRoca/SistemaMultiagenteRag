"""Recorre la matriz de autorización con todas las combinaciones de sesión (T05, T06).

* Sin sesión: 401 en toda ruta que no sea pública.
* A1 en rutas de A2 y A2 en rutas de A1: 403.
* Sesión del caso B en rutas de datos de caso: nunca ve datos del caso A.
"""

from __future__ import annotations

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


def _ruta(ruta: str, entrada: Entrada) -> str:
    return (entrada.ejemplo or ruta).replace("{CASO_A}", "CASO-A")


async def _pedir(
    cliente: httpx.AsyncClient, metodo: str, ruta: str, entrada: Entrada
) -> httpx.Response:
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
                if "CASO-A" in ajeno.text or "TEMA-A" in ajeno.text:
                    fallos.append(f"{metodo} {ruta}: el caso B ve datos del caso A")
        assert fallos == []
