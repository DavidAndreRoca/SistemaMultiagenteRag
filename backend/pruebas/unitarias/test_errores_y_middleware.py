"""Formato único de error, incidencia_id, cabeceras de seguridad y registro sin contenido."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.comun.errores import ErrorAplicacion
from app.configuracion import Ajustes
from app.main import crear_aplicacion

CLAVES_ERROR = {"codigo", "mensaje", "incidencia_id"}


class Entrada(BaseModel):
    cantidad: int


def aplicacion_con_rutas_de_prueba(ajustes: Ajustes) -> FastAPI:
    aplicacion = crear_aplicacion(ajustes)

    @aplicacion.get("/_prueba/falla")
    async def falla() -> None:
        raise RuntimeError("contenido secreto del borrador: NO DEBE SALIR")

    @aplicacion.get("/_prueba/error-aplicacion")
    async def error_aplicacion() -> None:
        raise ErrorAplicacion("codigo_repetido", "El código ya existe.", estado_http=409)

    @aplicacion.get("/_prueba/prohibido")
    async def prohibido() -> None:
        raise HTTPException(status_code=403)

    @aplicacion.post("/_prueba/valida")
    async def valida(entrada: Entrada) -> Entrada:
        return entrada

    return aplicacion


@pytest.fixture
async def cliente(
    ajustes: Ajustes, fabrica_cliente: Callable[[FastAPI], httpx.AsyncClient]
) -> httpx.AsyncClient:
    return fabrica_cliente(aplicacion_con_rutas_de_prueba(ajustes))


async def test_ruta_que_falla_a_proposito_devuelve_500_con_formato_comun(
    cliente: httpx.AsyncClient,
) -> None:
    respuesta = await cliente.get("/_prueba/falla")
    cuerpo = respuesta.json()
    assert respuesta.status_code == 500
    assert set(cuerpo) == CLAVES_ERROR
    assert cuerpo["codigo"] == "error_interno"
    assert cuerpo["incidencia_id"] == respuesta.headers["X-Incidencia-Id"]
    assert "NO DEBE SALIR" not in respuesta.text


async def test_error_de_aplicacion_usa_su_codigo_http(cliente: httpx.AsyncClient) -> None:
    respuesta = await cliente.get("/_prueba/error-aplicacion")
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "codigo_repetido"
    assert set(respuesta.json()) == CLAVES_ERROR


async def test_ruta_inexistente_es_404_con_formato_comun(cliente: httpx.AsyncClient) -> None:
    respuesta = await cliente.get("/no-existe")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_existe"
    assert set(respuesta.json()) == CLAVES_ERROR


async def test_403_usa_formato_comun(cliente: httpx.AsyncClient) -> None:
    respuesta = await cliente.get("/_prueba/prohibido")
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"


async def test_entrada_invalida_es_422_sin_devolver_el_valor_enviado(
    cliente: httpx.AsyncClient,
) -> None:
    respuesta = await cliente.post("/_prueba/valida", json={"cantidad": "dato-privado-123"})
    cuerpo = respuesta.json()
    assert respuesta.status_code == 422
    assert cuerpo["codigo"] == "entrada_invalida"
    assert cuerpo["detalle"][0]["campo"] == "body.cantidad"
    assert "dato-privado-123" not in respuesta.text


async def test_cada_peticion_recibe_un_incidencia_id_distinto(cliente: httpx.AsyncClient) -> None:
    a = await cliente.get("/no-existe")
    b = await cliente.get("/no-existe")
    assert a.headers["X-Incidencia-Id"] != b.headers["X-Incidencia-Id"]


async def test_cabeceras_de_seguridad_basicas(cliente: httpx.AsyncClient) -> None:
    respuesta = await cliente.get("/no-existe")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "DENY"
    assert respuesta.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in respuesta.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in respuesta.headers


async def test_documentacion_openapi_disponible_fuera_de_produccion(
    cliente: httpx.AsyncClient,
) -> None:
    respuesta = await cliente.get("/openapi.json")
    assert respuesta.status_code == 200
    assert "/salud" in respuesta.json()["paths"]
    docs = await cliente.get("/docs")
    assert docs.status_code == 200
    assert "Content-Security-Policy" not in docs.headers


async def test_produccion_oculta_openapi_y_envia_hsts(
    fabrica_cliente: Callable[[FastAPI], httpx.AsyncClient],
) -> None:
    from app.configuracion import cargar_ajustes
    from pruebas.conftest import variables_base

    ajustes_prod = cargar_ajustes(
        variables_base(
            ENTORNO="produccion",
            SECRETO_SESION="p" * 40,
            CORREO_POLITE="proyecto@example.org",
            CLAVE_OPENALEX="k",
        )
    )
    cliente = fabrica_cliente(crear_aplicacion(ajustes_prod))
    assert (await cliente.get("/openapi.json")).status_code == 404
    respuesta = await cliente.get("/no-existe")
    assert "max-age" in respuesta.headers["Strict-Transport-Security"]


async def test_el_registro_es_json_con_incidencia_y_sin_contenido(
    ajustes: Ajustes,
    fabrica_cliente: Callable[[FastAPI], httpx.AsyncClient],
    capsys: pytest.CaptureFixture[str],
) -> None:
    cliente = fabrica_cliente(aplicacion_con_rutas_de_prueba(ajustes))
    respuesta = await cliente.get("/_prueba/falla")
    lineas = [json.loads(linea) for linea in capsys.readouterr().out.splitlines() if linea]
    eventos = {linea["evento"]: linea for linea in lineas}

    assert "error interno" in eventos
    assert eventos["error interno"]["incidencia_id"] == respuesta.headers["X-Incidencia-Id"]
    assert eventos["error interno"]["excepcion"] == "RuntimeError"
    acceso = eventos["peticion"]
    assert acceso["estado_http"] == 500
    assert acceso["ruta"] == "/_prueba/falla"
    assert "duracion_ms" in acceso
    # El mensaje de la excepción (puede contener datos del usuario) no se registra.
    assert "NO DEBE SALIR" not in json.dumps(lineas)


def test_el_formateador_descarta_campos_con_nombre_de_secreto_o_contenido(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from app.comun.registro import configurar_registro, obtener_registrador

    configurar_registro()
    obtener_registrador("t").info(
        "evento",
        extra={"contrasena": "x1", "borrador": "texto del borrador", "etapa": "recuperacion"},
    )
    salida = capsys.readouterr().out
    assert "recuperacion" in salida
    assert "x1" not in salida
    assert "texto del borrador" not in salida
