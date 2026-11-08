"""T08: cliente del servicio de modelos detrás de ``ProveedorEmbeddings`` y ``Reordenador``."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.configuracion import cargar_ajustes
from app.inferencia.interfaces import ProveedorEmbeddings, Reordenador
from app.inferencia.servicio_modelos import (
    ClienteServicioModelos,
    ErrorServicioModelos,
    cliente_desde_ajustes,
)
from pruebas.conftest import variables_base

REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def _vector(valor: float) -> list[float]:
    return [valor] + [0.0] * 1023


def _cliente(
    manejador: Callable[[httpx.Request], httpx.Response], max_textos: int = 64
) -> tuple[ClienteServicioModelos, list[dict[str, Any]]]:
    recibidos: list[dict[str, Any]] = []

    def registrar(peticion: httpx.Request) -> httpx.Response:
        recibidos.append({"ruta": peticion.url.path, **json.loads(peticion.content)})
        return manejador(peticion)

    http = httpx.AsyncClient(
        transport=httpx.MockTransport(registrar), base_url="http://modelos.test"
    )
    return ClienteServicioModelos("http://modelos.test", cliente=http, max_textos=max_textos), (
        recibidos
    )


def _servicio_correcto(peticion: httpx.Request) -> httpx.Response:
    cuerpo = json.loads(peticion.content)
    if peticion.url.path == "/embeber":
        return httpx.Response(
            200,
            json={
                "modelo": "BAAI/bge-m3",
                "revision": REVISION,
                "dimension": 1024,
                "vectores": [_vector(float(len(t))) for t in cuerpo["textos"]],
            },
        )
    return httpx.Response(
        200,
        json={
            "modelo": "BAAI/bge-reranker-v2-m3",
            "revision": "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e",
            "puntajes": [min(len(t) / 10, 1.0) for t in cuerpo["textos"]],
        },
    )


def test_el_cliente_cumple_ambas_interfaces() -> None:
    cliente, _ = _cliente(_servicio_correcto)
    proveedor: ProveedorEmbeddings = cliente
    reordenador: Reordenador = cliente
    assert proveedor is reordenador


async def test_embeber_divide_en_partes_y_conserva_el_orden() -> None:
    cliente, recibidos = _cliente(_servicio_correcto, max_textos=2)
    resultado = await cliente.embeber(["a", "bb", "ccc", "dddd", "eeeee"])
    assert [r["textos"] for r in recibidos] == [["a", "bb"], ["ccc", "dddd"], ["eeeee"]]
    assert [v[0] for v in resultado.vectores] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert (resultado.identidad.modelo, resultado.identidad.revision) == ("BAAI/bge-m3", REVISION)


async def test_reordenar_devuelve_puntajes_e_identidad() -> None:
    cliente, recibidos = _cliente(_servicio_correcto, max_textos=2)
    resultado = await cliente.reordenar("consulta", ["uno", "dos tres", "cuatro"])
    assert resultado.puntajes == [0.3, 0.8, 0.6]
    assert resultado.identidad.modelo == "BAAI/bge-reranker-v2-m3"
    assert {r["consulta"] for r in recibidos} == {"consulta"}


@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(503, json={"codigo": "servicio_ocupado"}),
        httpx.Response(500, text="error"),
        httpx.Response(200, text="no es json"),
        httpx.Response(
            200, json={"modelo": "m", "revision": "r", "dimension": 768, "vectores": []}
        ),
        httpx.Response(
            200, json={"modelo": "m", "revision": "r", "dimension": 1024, "vectores": [[0.1] * 10]}
        ),
        httpx.Response(
            200,
            json={"modelo": "m", "revision": "r", "dimension": 1024, "vectores": [_vector(1)] * 2},
        ),  # dos vectores para un texto
    ],
)
async def test_respuestas_fuera_de_contrato_son_error_503(respuesta: httpx.Response) -> None:
    cliente, _ = _cliente(lambda _: respuesta)
    with pytest.raises(ErrorServicioModelos) as error:
        await cliente.embeber(["texto"])
    assert error.value.estado_http == 503
    assert error.value.codigo == "servicio_modelos_no_disponible"


async def test_puntaje_fuera_de_rango_es_error() -> None:
    cliente, _ = _cliente(
        lambda _: httpx.Response(200, json={"modelo": "m", "revision": "r", "puntajes": [1.5]})
    )
    with pytest.raises(ErrorServicioModelos):
        await cliente.reordenar("q", ["t"])


async def test_texto_rechazado_por_el_servicio_es_422_sin_devolver_el_texto() -> None:
    cliente, _ = _cliente(
        lambda _: httpx.Response(
            422, json={"codigo": "texto_demasiado_largo", "mensaje": "x", "incidencia_id": "i"}
        )
    )
    with pytest.raises(ErrorServicioModelos) as error:
        await cliente.embeber(["texto confidencial del estudiante"])
    assert error.value.estado_http == 422
    assert error.value.detalle == {"codigo": "texto_demasiado_largo"}
    assert "confidencial" not in repr(error.value.__dict__)


async def test_revision_distinta_entre_partes_es_error() -> None:
    revisiones = iter(["r1", "r2"])

    def manejador(peticion: httpx.Request) -> httpx.Response:
        textos = json.loads(peticion.content)["textos"]
        return httpx.Response(
            200,
            json={
                "modelo": "BAAI/bge-m3",
                "revision": next(revisiones),
                "dimension": 1024,
                "vectores": [_vector(1)] * len(textos),
            },
        )

    cliente, _ = _cliente(manejador, max_textos=1)
    with pytest.raises(ErrorServicioModelos) as error:
        await cliente.embeber(["a", "b"])
    assert "cambió" in error.value.motivo


async def test_servicio_caido_es_error_503() -> None:
    def caido(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin conexión", request=peticion)

    cliente, _ = _cliente(caido)
    with pytest.raises(ErrorServicioModelos) as error:
        await cliente.embeber(["a"])
    assert error.value.motivo == "sin respuesta (ConnectError)"


async def test_lista_vacia_no_llama_al_servicio() -> None:
    cliente, recibidos = _cliente(_servicio_correcto)
    with pytest.raises(ValueError):
        await cliente.embeber([])
    assert recibidos == []


def test_registro_no_guarda_textos(capsys: pytest.CaptureFixture[str]) -> None:
    import asyncio

    cliente, _ = _cliente(_servicio_correcto)
    asyncio.run(cliente.embeber(["frase-privada-del-borrador"]))
    salida = capsys.readouterr().out
    assert "servicio de modelos" in salida
    assert "frase-privada-del-borrador" not in salida


def test_url_del_servicio_desde_el_entorno() -> None:
    ajustes = cargar_ajustes(variables_base() | {"URL_SERVICIO_MODELOS": "http://modelos:8000"})
    assert isinstance(cliente_desde_ajustes(ajustes), ClienteServicioModelos)
    with pytest.raises(ErrorServicioModelos):
        cliente_desde_ajustes(cargar_ajustes(variables_base()))
    with pytest.raises(Exception, match="URL_SERVICIO_MODELOS"):
        cargar_ajustes(variables_base() | {"URL_SERVICIO_MODELOS": "modelos:8000"})
