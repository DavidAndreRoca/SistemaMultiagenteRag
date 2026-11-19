"""T12: secciones del borrador con la base real (F-05; decisión T12-01).

Criterio de aceptación: un .docx con estilos produce sus secciones; uno sin estilos pide
selección manual y la guarda. El validador de alcance y CP-09 se prueban en
``unitarias/test_secciones_borrador.py``; aquí se comprueba además que funciona sobre los
párrafos y secciones guardados en la base.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app.administracion.parametros import parametros_iniciales
from app.bd.enumeraciones import Rol, TipoAlcance, TipoSolicitud
from app.borradores.alcance import AlcanceInvalido, validar_alcance
from app.borradores.servicio import MENSAJE_SIN_ESTILOS, parrafos_de, secciones_de
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.integracion.conftest import (
    Entorno,
    consultar,
    crear_caso,
    crear_tema,
    entrar_y_cambiar,
    primera_credencial,
)

pytestmark = pytest.mark.integracion

DOCX = Path(__file__).parents[1] / "datos" / "docx"


async def _caso(
    entorno: Entorno, investigador: httpx.AsyncClient, codigo: str
) -> httpx.AsyncClient:
    await crear_tema(investigador, f"TEMA-{codigo}")
    caso = await crear_caso(investigador, codigo, f"TEMA-{codigo}")
    return await entrar_y_cambiar(entorno.cliente(), *primera_credencial(caso))


@pytest.fixture
async def caso_a(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> AsyncIterator[httpx.AsyncClient]:
    cliente = await _caso(entorno, investigador, "CASO-A")
    yield cliente
    await cliente.aclose()


async def _cargar(cliente: httpx.AsyncClient, archivo: str) -> dict[str, object]:
    respuesta = await cliente.post(
        "/caso/versiones",
        data={"hito": "avance_1"},
        files={"archivo": (archivo, (DOCX / archivo).read_bytes())},
    )
    assert respuesta.status_code == 201, respuesta.text
    datos: dict[str, object] = respuesta.json()
    return datos


def _id(carga: dict[str, object]) -> str:
    version = carga["version"]
    assert isinstance(version, dict)
    return str(version["id"])


async def test_un_docx_con_estilos_produce_sus_secciones(caso_a: httpx.AsyncClient) -> None:
    carga = await _cargar(caso_a, "estructura.docx")
    version = carga["version"]
    assert isinstance(version, dict)
    assert (version["metodo_deteccion"], version["secciones"], version["referencias"]) == (
        "estilos",
        11,
        3,
    )
    assert carga["mensajes"] == ["Es la primera versión del hito Avance 1."]
    vista = (await caso_a.get(f"/caso/versiones/{_id(carga)}/secciones")).json()
    assert vista["metodo_deteccion"] == "estilos" and vista["mensajes"] == []
    assert vista["titulo_documento"] == "Tutoría entre pares y ansiedad ante la estadística"
    assert [s["titulo"] for s in vista["secciones"]][:3] == [
        "Resumen",
        "1. Introducción",
        "1.1. Planteamiento del problema",
    ]
    parrafos = {p["id"]: p for p in vista["parrafos"]}
    assert parrafos["p5"]["es_titulo"] and parrafos["p5"]["seccion"] == "s2"
    assert parrafos["p6"]["seccion"] == "s2" and not parrafos["p6"]["es_titulo"]
    assert parrafos["p2"]["seccion"] is None  # preliminar
    assert vista["referencias"]["seccion"] == "s11" and len(vista["referencias"]["entradas"]) == 3


async def test_un_docx_sin_estilos_pide_seleccion_manual_y_la_guarda(
    entorno: Entorno, caso_a: httpx.AsyncClient
) -> None:
    carga = await _cargar(caso_a, "sin_estilos.docx")
    assert carga["mensajes"] == ["Es la primera versión del hito Avance 1.", MENSAJE_SIN_ESTILOS]
    version_id = _id(carga)
    ruta = f"/caso/versiones/{version_id}/secciones"
    antes = (await caso_a.get(ruta)).json()
    assert antes["metodo_deteccion"] is None and antes["secciones"] == []
    assert antes["mensajes"] == [MENSAJE_SIN_ESTILOS]

    titulos = [{"parrafo": pid, "nivel": 1} for pid in ("p1", "p3", "p5", "p7")]
    marcada = await caso_a.put(ruta, json={"titulos": titulos})
    assert marcada.status_code == 200, marcada.text
    assert marcada.json()["metodo_deteccion"] == "manual" and marcada.json()["mensajes"] == []
    guardada = (await caso_a.get(ruta)).json()
    assert guardada == marcada.json()
    assert [s["clase"] for s in guardada["secciones"]] == [
        "introduccion",
        "metodos",
        "resultados",
        "referencias",
    ]
    assert consultar(
        entorno.url_bd, "SELECT metodo_deteccion::text, secciones IS NOT NULL FROM version_borrador"
    ) == [("manual", True)]
    detalle = (await caso_a.get(f"/caso/versiones/{version_id}")).json()
    assert (detalle["metodo_deteccion"], detalle["secciones"], detalle["referencias"]) == (
        "manual",
        4,
        1,
    )


async def test_la_lista_de_referencias_se_indica_a_mano(caso_a: httpx.AsyncClient) -> None:
    version_id = _id(await _cargar(caso_a, "zotero.docx"))
    ruta = f"/caso/versiones/{version_id}/referencias"
    assert (await caso_a.get(f"/caso/versiones/{version_id}/secciones")).json()[
        "referencias"
    ] is None
    respuesta = await caso_a.put(ruta, json={"desde": "p6"})
    assert respuesta.status_code == 200, respuesta.text
    referencias = respuesta.json()["referencias"]
    assert (referencias["metodo"], referencias["desde"], referencias["hasta"]) == (
        "manual",
        "p6",
        "p6",
    )
    assert len(referencias["entradas"]) == 2
    assert respuesta.json()["metodo_deteccion"] == "estilos"  # las secciones no cambian


@pytest.mark.parametrize(
    ("ruta", "cuerpo", "codigo"),
    [
        ("secciones", {"titulos": [{"parrafo": "p99", "nivel": 1}]}, "secciones_invalidas"),
        ("secciones", {"titulos": []}, "entrada_invalida"),
        ("secciones", {"titulos": [{"parrafo": "p1", "nivel": 12}]}, "secciones_invalidas"),
        ("referencias", {"desde": "p5", "hasta": "p1"}, "secciones_invalidas"),
        ("referencias", {"desde": ""}, "entrada_invalida"),
    ],
)
async def test_las_marcas_manuales_se_validan(
    caso_a: httpx.AsyncClient, ruta: str, cuerpo: dict[str, object], codigo: str
) -> None:
    version_id = _id(await _cargar(caso_a, "sin_estilos.docx"))
    respuesta = await caso_a.put(f"/caso/versiones/{version_id}/{ruta}", json=cuerpo)
    assert (respuesta.status_code, respuesta.json()["codigo"]) == (422, codigo)


async def test_una_version_con_solicitudes_no_cambia_sus_secciones(
    entorno: Entorno, caso_a: httpx.AsyncClient
) -> None:
    version_id = _id(await _cargar(caso_a, "sin_estilos.docx"))
    consultar(
        entorno.url_bd,
        "INSERT INTO solicitud (caso_id, version_id, tipo, alcance_tipo, configuracion_id)"
        " SELECT v.caso_id, v.id, 'plan_tarea', 'hito', c.id FROM version_borrador v,"
        " configuracion c WHERE c.vigente RETURNING 1",
    )
    for ruta, cuerpo in (
        ("secciones", {"titulos": [{"parrafo": "p1", "nivel": 1}]}),
        ("referencias", {"desde": "p8"}),
    ):
        respuesta = await caso_a.put(f"/caso/versiones/{version_id}/{ruta}", json=cuerpo)
        assert (respuesta.status_code, respuesta.json()["codigo"]) == (409, "version_en_uso")
    assert consultar(entorno.url_bd, "SELECT metodo_deteccion FROM version_borrador") == [(None,)]


async def test_un_caso_no_ve_ni_marca_las_secciones_de_otro(
    entorno: Entorno, investigador: httpx.AsyncClient, caso_a: httpx.AsyncClient
) -> None:
    version_id = _id(await _cargar(caso_a, "estructura.docx"))
    caso_b = await _caso(entorno, investigador, "CASO-B")
    try:
        ruta = f"/caso/versiones/{version_id}"
        assert (await caso_b.get(f"{ruta}/secciones")).status_code == 404
        marcar = await caso_b.put(
            f"{ruta}/secciones", json={"titulos": [{"parrafo": "p2", "nivel": 1}]}
        )
        assert marcar.status_code == 404
        assert (await caso_b.put(f"{ruta}/referencias", json={"desde": "p2"})).status_code == 404
    finally:
        await caso_b.aclose()
    assert consultar(entorno.url_bd, "SELECT metodo_deteccion::text FROM version_borrador") == [
        ("estilos",)
    ]


async def test_el_alcance_se_valida_sobre_la_version_guardada(
    entorno: Entorno, caso_a: httpx.AsyncClient
) -> None:
    await _cargar(caso_a, "estructura.docx")
    ((version_id, caso_id, cuenta_id),) = consultar(
        entorno.url_bd,
        "SELECT v.id, v.caso_id, c.id FROM version_borrador v"
        " JOIN cuenta c ON c.caso_id = v.caso_id",
    )
    assert isinstance(version_id, uuid.UUID) and isinstance(caso_id, uuid.UUID)
    assert isinstance(cuenta_id, uuid.UUID)
    contexto = ContextoAcceso(cuenta_id=cuenta_id, rol=Rol.CASO, caso_id=caso_id)
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        version = await UnidadDeTrabajo(sesion).versiones.con_parrafos(contexto, version_id)
    assert version is not None
    parrafos, secciones = parrafos_de(version), secciones_de(version)
    parametros = parametros_iniciales()
    resuelto = validar_alcance(
        TipoSolicitud.REVISION_METODOLOGICA,
        TipoAlcance.SECCION,
        "s5",
        parrafos,
        secciones,
        parametros,
    )
    assert resuelto.texto.startswith("2. Método") and "Participaron 84" in resuelto.texto
    corta = parametros.model_copy(update={"limite_palabras_d3": 5})
    with pytest.raises(AlcanceInvalido) as error:  # CP-09 con un límite reducido
        validar_alcance(
            TipoSolicitud.PROPUESTA_REDACCION,
            TipoAlcance.FRAGMENTO,
            "p7",
            parrafos,
            secciones,
            corta,
        )
    assert error.value.motivo == "alcance_demasiado_largo"
