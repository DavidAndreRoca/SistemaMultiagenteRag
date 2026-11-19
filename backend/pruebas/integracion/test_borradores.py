"""T11: carga y versiones del borrador con la base real (RF-01, CU-01, CP-01, CP-02, RN-09).

Casos de prueba de la tesis (Tabla 20, ``docs/especificacion-fase1/casos-de-prueba-tesis.md``):

* CP-01 (CU-01): un .docx de un caso registrado registra una versión nueva con fecha y hora,
  y las versiones anteriores se conservan.
* CP-02 (CU-01, E1): un archivo de formato distinto de .docx o dañado se rechaza, se informa
  el motivo y no se registra ninguna versión.

Las macros, el cifrado y el contenido anómalo no son parte de CP-02: los rechaza RN-16 y se
prueban aparte, con las mismas garantías.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import zipfile
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app.configuracion import cargar_ajustes
from app.main import crear_aplicacion
from pruebas.conftest import variables_base
from pruebas.integracion.conftest import (
    Entorno,
    RelojFicticio,
    consultar,
    crear_caso,
    crear_tema,
    entrar_y_cambiar,
    primera_credencial,
)

pytestmark = pytest.mark.integracion

DOCX = Path(__file__).parents[1] / "datos" / "docx"
VALIDO = (DOCX / "valido.docx").read_bytes()
TEXTO_DEL_BORRADOR = "ansiedad ante la estadística afecta el rendimiento"


async def _caso(
    entorno: Entorno, investigador: httpx.AsyncClient, codigo: str
) -> httpx.AsyncClient:
    tema = f"TEMA-{codigo}"
    await crear_tema(investigador, tema)
    caso = await crear_caso(investigador, codigo, tema)
    return await entrar_y_cambiar(entorno.cliente(), *primera_credencial(caso))


async def _cargar(
    cliente: httpx.AsyncClient,
    datos: bytes = VALIDO,
    hito: str = "avance_1",
    nombre: str = "Borrador de Ana Prueba Ficticia.docx",
) -> httpx.Response:
    return await cliente.post(
        "/caso/versiones", data={"hito": hito}, files={"archivo": (nombre, datos)}
    )


def _archivos(entorno: Entorno) -> list[Path]:
    carpeta = Path(entorno.aplicacion.state.ajustes.directorio_archivos) / "borradores"
    return sorted(carpeta.glob("*")) if carpeta.exists() else []


@pytest.fixture
async def caso_a(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> AsyncIterator[httpx.AsyncClient]:
    cliente = await _caso(entorno, investigador, "CASO-A")
    yield cliente
    await cliente.aclose()


async def test_cp01_carga_valida_registra_la_version_y_conserva_las_anteriores(
    entorno: Entorno, caso_a: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        respuesta = await _cargar(caso_a)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    version = cuerpo["version"]
    assert cuerpo["primera_del_hito"] is True
    assert cuerpo["mensajes"] == ["Es la primera versión del hito Avance 1."]
    assert (version["hito"], version["nombre_hito"], version["vigente"]) == (
        "avance_1",
        "Avance 1",
        True,
    )
    assert version["cargada_en"].startswith("2026-11-06T12:00:00")  # reloj de la prueba
    assert version["huella_sha256"] == hashlib.sha256(VALIDO).hexdigest()
    assert version["tamano_bytes"] == len(VALIDO)
    assert version["parrafos"] > 10 and version["palabras"] > 50

    ((ruta, parrafos, palabras),) = consultar(
        entorno.url_bd, "SELECT ruta_archivo, parrafos, palabras FROM version_borrador"
    )
    assert isinstance(ruta, str) and ruta.startswith("borradores/") and ruta.endswith(".docx")
    assert "Ana" not in ruta  # nombre aleatorio: el nombre original no se guarda
    (guardado,) = _archivos(entorno)
    assert guardado.read_bytes() == VALIDO and guardado.name == ruta.split("/")[1]
    assert isinstance(parrafos, list) and parrafos[0]["id"] == "p1"
    assert palabras == version["palabras"]
    # El registro no lleva el texto ni el nombre del archivo (4.6).
    registro = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert TEXTO_DEL_BORRADOR not in registro and "Ana Prueba" not in registro
    assert "version de borrador registrada" in registro

    # Una segunda carga del mismo caso: versión nueva con su fecha y hora, y la anterior se
    # conserva entera (registro, párrafos y archivo).
    entorno.reloj.avanzar(minutes=5)
    segunda = (await _cargar(caso_a)).json()["version"]
    assert segunda["id"] != version["id"]
    assert segunda["cargada_en"].startswith("2026-11-06T12:05:00")
    anterior = (await caso_a.get(f"/caso/versiones/{version['id']}")).json()
    assert {k: v for k, v in anterior.items() if k != "vigente"} == {
        k: v for k, v in version.items() if k != "vigente"
    }
    assert consultar(entorno.url_bd, "SELECT count(*) FROM version_borrador") == [(2,)]
    assert guardado.exists() and len(_archivos(entorno)) == 2


async def test_cada_carga_crea_una_version_y_solo_una_vigente_por_hito(
    entorno: Entorno, caso_a: httpx.AsyncClient
) -> None:
    primera = (await _cargar(caso_a)).json()["version"]
    entorno.reloj.avanzar(minutes=1)  # sin pasar la inactividad de la sesión
    segunda = await _cargar(caso_a)  # el mismo archivo: igual es una versión nueva (RN-09)
    assert segunda.status_code == 201
    assert segunda.json()["primera_del_hito"] is False
    assert "reemplaza como vigente" in segunda.json()["mensajes"][0]
    entorno.reloj.avanzar(minutes=1)  # sin pasar la inactividad de la sesión
    otra = (await _cargar(caso_a, hito="avance_2")).json()
    assert otra["primera_del_hito"] is True

    lista = (await caso_a.get("/caso/versiones")).json()
    assert [v["hito"] for v in lista] == ["avance_2", "avance_1", "avance_1"]
    assert [v["vigente"] for v in lista] == [True, True, False]
    assert "parrafos" not in lista[0] and "huella_sha256" not in lista[0]  # sin el detalle
    del_hito = (await caso_a.get("/caso/versiones", params={"hito": "avance_1"})).json()
    assert [v["id"] for v in del_hito] == [segunda.json()["version"]["id"], primera["id"]]
    anterior = (await caso_a.get(f"/caso/versiones/{primera['id']}")).json()
    assert anterior["vigente"] is False and anterior["parrafos"] == primera["parrafos"]
    assert consultar(entorno.url_bd, "SELECT count(*) FROM version_borrador") == [(3,)]
    assert len(_archivos(entorno)) == 3


async def test_dos_cargas_simultaneas_dejan_una_sola_vigente(
    entorno: Entorno, caso_a: httpx.AsyncClient
) -> None:
    respuestas = await asyncio.gather(*(_cargar(caso_a) for _ in range(3)))
    assert [r.status_code for r in respuestas] == [201, 201, 201]
    assert consultar(
        entorno.url_bd, "SELECT count(*) FILTER (WHERE vigente), count(*) FROM version_borrador"
    ) == [(1, 3)]


async def _rechazo_sin_version(
    entorno: Entorno,
    caso: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
    datos: bytes,
    nombre: str,
    motivo: str,
) -> None:
    """La carga se rechaza, se informa el motivo y no queda versión ni archivo."""
    with caplog.at_level(logging.INFO):
        respuesta = await _cargar(caso, datos, nombre=nombre)
    assert respuesta.status_code == 422, respuesta.text
    error = respuesta.json()
    assert (error["codigo"], error["detalle"]) == (motivo, {"motivo": motivo})
    assert error["mensaje"] and error["incidencia_id"]  # el motivo se informa al caso
    assert consultar(entorno.url_bd, "SELECT count(*) FROM version_borrador") == [(0,)]
    assert _archivos(entorno) == []
    eventos = [r for r in caplog.records if getattr(r, "tipo_evento", "") == "validacion_borrador"]
    assert [getattr(r, "motivo", None) for r in eventos] == [motivo]
    assert nombre not in json.dumps([r.__dict__ for r in eventos], default=str)


PDF = b"%PDF-1.4\n% documento ficticio\n%%EOF\n"
ODT = b"PK\x03\x04" + b"mimetypeapplication/vnd.oasis.opendocument.text" + bytes(64)


@pytest.mark.parametrize(
    ("nombre", "datos", "motivo"),
    [
        # Formato distinto de .docx, con su propia extensión
        ("borrador.pdf", PDF, "formato_no_admitido"),
        ("borrador.doc", (DOCX / "doc_antiguo.docx").read_bytes(), "formato_no_admitido"),
        ("borrador.odt", ODT, "formato_no_admitido"),
        ("borrador.txt", b"Texto plano ficticio.", "formato_no_admitido"),
        ("Articulo de Ana Ficticia", VALIDO, "formato_no_admitido"),  # sin extensión
        # Formato distinto de .docx con la extensión cambiada
        ("pdf_renombrado.docx", PDF, "formato_no_admitido"),
        (
            "hoja_renombrada.docx",
            (DOCX / "hoja_renombrada.docx").read_bytes(),
            "formato_no_admitido",
        ),
        # Dañado
        ("truncado.docx", (DOCX / "truncado.docx").read_bytes(), "docx_danado"),
        ("crc_alterado.docx", (DOCX / "crc_alterado.docx").read_bytes(), "docx_danado"),
        ("sin_documento.docx", (DOCX / "sin_documento.docx").read_bytes(), "formato_no_admitido"),
    ],
)
async def test_cp02_formato_distinto_o_danado_se_rechaza_sin_registrar_version(
    entorno: Entorno,
    caso_a: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
    nombre: str,
    datos: bytes,
    motivo: str,
) -> None:
    await _rechazo_sin_version(entorno, caso_a, caplog, datos, nombre, motivo)


@pytest.mark.parametrize(
    ("archivo", "motivo"),
    [
        ("con_macros.docm", "docx_con_macros"),
        ("macros_renombrado.docx", "docx_con_macros"),
        ("cifrado.docx", "docx_cifrado"),
        ("bomba.docx", "contenido_anomalo"),
    ],
)
async def test_rn16_macros_cifrado_o_contenido_anomalo_se_rechazan_sin_version(
    entorno: Entorno,
    caso_a: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
    archivo: str,
    motivo: str,
) -> None:
    datos = (DOCX / archivo).read_bytes()
    await _rechazo_sin_version(entorno, caso_a, caplog, datos, archivo, motivo)


async def test_un_borrador_mas_grande_que_el_limite_se_rechaza(
    entorno: Entorno, caso_a: httpx.AsyncClient
) -> None:
    cambiar = (
        "UPDATE configuracion SET parametros ="
        " jsonb_set(parametros, '{tamano_max_docx_mb}', %s::jsonb) RETURNING 1"
    )
    grande = io.BytesIO(VALIDO)
    with zipfile.ZipFile(grande, "a") as paquete:
        paquete.writestr("word/media/foto.bin", os.urandom(1024 * 1024))  # no se comprime
    consultar(entorno.url_bd, cambiar, "1")
    try:
        respuesta = await _cargar(caso_a, grande.getvalue())
    finally:
        consultar(entorno.url_bd, cambiar, "15")
    assert respuesta.status_code == 413
    assert respuesta.json()["codigo"] == "archivo_demasiado_grande"
    assert respuesta.json()["detalle"] == {"limite_mb": 1}
    assert consultar(entorno.url_bd, "SELECT count(*) FROM version_borrador") == [(0,)]


async def test_el_hito_debe_estar_en_el_catalogo(caso_a: httpx.AsyncClient) -> None:
    respuesta = await _cargar(caso_a, hito="hito_inventado")
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "hito_desconocido"
    assert "avance_1" in respuesta.json()["detalle"]["hitos"]
    assert (await _cargar(caso_a, hito="")).status_code == 422


async def test_un_caso_no_ve_las_versiones_de_otro(
    entorno: Entorno, investigador: httpx.AsyncClient, caso_a: httpx.AsyncClient
) -> None:
    version = (await _cargar(caso_a)).json()["version"]
    caso_b = await _caso(entorno, investigador, "CASO-B")
    try:
        assert (await caso_b.get(f"/caso/versiones/{version['id']}")).status_code == 404
        assert (await caso_b.get("/caso/versiones")).json() == []
        await _cargar(caso_b)
        lista_b = (await caso_b.get("/caso/versiones")).json()
        assert len(lista_b) == 1 and lista_b[0]["id"] != version["id"]
    finally:
        await caso_b.aclose()
    assert [v["id"] for v in (await caso_a.get("/caso/versiones")).json()] == [version["id"]]
    assert (await investigador.get(f"/caso/versiones/{version['id']}")).status_code == 403
    inexistente = "00000000-0000-4000-8000-000000000000"
    respuesta = await caso_a.get(f"/caso/versiones/{inexistente}")
    assert (respuesta.status_code, respuesta.json()["codigo"]) == (404, "no_existe")


async def test_sin_directorio_de_archivos_la_carga_responde_503(bd_limpia: str) -> None:
    aplicacion = crear_aplicacion(cargar_ajustes(variables_base(URL_BD=bd_limpia)))
    entorno_sin = Entorno(aplicacion=aplicacion, reloj=RelojFicticio(), url_bd=bd_limpia)
    async with aplicacion.router.lifespan_context(aplicacion):
        contrasena = await entorno_sin.crear_investigador()
        async with entorno_sin.cliente() as investigador:
            await entrar_y_cambiar(investigador, "INV-01", contrasena)
            caso = await _caso(entorno_sin, investigador, "CASO-C")
            try:
                respuesta = await _cargar(caso)
            finally:
                await caso.aclose()
    assert respuesta.status_code == 503
    assert respuesta.json()["codigo"] == "borradores_no_configurado"
