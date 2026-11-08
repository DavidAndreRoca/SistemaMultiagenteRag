"""T09: metadatos de cabecera con GROBID, contra respuestas grabadas de GROBID 0.9.1."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
import pytest

from app.corpus.esquemas import Autor, MetadatosCabecera
from app.corpus.grobid import ClienteGrobid, ErrorGrobid, metadatos_desde_tei, normalizar_doi

CONTRATO = Path(__file__).resolve().parents[1] / "contrato" / "grobid"
PDF = Path(__file__).resolve().parents[1] / "datos" / "pdf" / "articulo_es.pdf"


def tei(nombre: str) -> str:
    return (CONTRATO / nombre).read_text(encoding="utf-8")


def test_lee_la_cabecera_grabada_del_articulo_en_espanol() -> None:
    metadatos = metadatos_desde_tei(tei("cabecera_articulo_es.tei.xml"))
    assert metadatos.titulo == (
        "Tutoría entre pares y ansiedad ante la estadística en estudiantes de Psicología"
        " de una universidad privada de Ica"
    )
    assert metadatos.autores == [
        Autor(nombres="Lucía", apellidos="Mendoza Vargas"),
        Autor(nombres="Rafael Quispe", apellidos="Huamán"),  # GROBID con dos apellidos
    ]
    assert metadatos.doi == "10.5555/rfes.2026.0042"
    assert (metadatos.anio, metadatos.revista, metadatos.idioma) == (None, None, "es")


def test_lee_la_cabecera_grabada_del_articulo_en_ingles() -> None:
    metadatos = metadatos_desde_tei(tei("cabecera_articulo_en.tei.xml"))
    assert metadatos.titulo is not None and metadatos.titulo.startswith("Sleep duration")
    assert [a.apellidos for a in metadatos.autores] == ["Torres Medina", "Rojas"]
    assert (metadatos.doi, metadatos.idioma) == ("10.5555/fjsh.2026.0007", "en")


def test_lee_fecha_publicada_revista_y_doi_normalizado() -> None:
    metadatos = metadatos_desde_tei(tei("cabecera_completa.tei.xml"))
    assert metadatos == MetadatosCabecera(
        titulo="Título ficticio en dos líneas",
        autores=[
            Autor(nombres="María José", apellidos="Paredes Lima"),
            Autor(nombres=None, apellidos="Sin Nombre"),
        ],
        anio=2021,
        doi="10.5555/rfes.2021.0099",
        revista="Revista Ficticia de Educación Superior",
        idioma="es",
    )


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("10.5555/ABC.1", "10.5555/abc.1"),
        ("https://doi.org/10.5555/x.y", "10.5555/x.y"),
        ("doi:10.5555/x.y.", "10.5555/x.y"),
        ("no es un doi", None),
        ("", None),
        (None, None),
    ],
)
def test_normaliza_doi(valor: str | None, esperado: str | None) -> None:
    assert normalizar_doi(valor) == esperado


def test_una_respuesta_sin_cabecera_tei_es_invalida() -> None:
    with pytest.raises(ValueError):
        metadatos_desde_tei("<TEI xmlns='http://www.tei-c.org/ns/1.0'/>")


def cliente(manejador: httpx.MockTransport) -> ClienteGrobid:
    return ClienteGrobid(
        "http://grobid", cliente=httpx.Client(base_url="http://grobid", transport=manejador)
    )


def test_el_cliente_envia_el_pdf_sin_consolidar_y_lee_la_respuesta(
    caplog: pytest.LogCaptureFixture,
) -> None:
    vistos: list[httpx.Request] = []

    def responder(solicitud: httpx.Request) -> httpx.Response:
        vistos.append(solicitud)
        return httpx.Response(200, text=tei("cabecera_articulo_es.tei.xml"))

    with caplog.at_level(logging.INFO):
        metadatos = cliente(httpx.MockTransport(responder)).cabecera(PDF)
    assert metadatos.doi == "10.5555/rfes.2026.0042"
    (solicitud,) = vistos
    assert solicitud.url.path == "/api/processHeaderDocument"
    cuerpo = solicitud.content
    assert b'name="consolidateHeader"\r\n\r\n0' in cuerpo
    assert PDF.read_bytes() in cuerpo
    registro = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert "Tutoría" not in registro and "rfes" not in registro  # nada del contenido


def test_sin_cabecera_detectada_devuelve_metadatos_vacios() -> None:
    respuesta = cliente(httpx.MockTransport(lambda _: httpx.Response(204))).cabecera(PDF)
    assert respuesta == MetadatosCabecera()


@pytest.mark.parametrize(
    "respuesta",
    [httpx.Response(503), httpx.Response(500), httpx.Response(200, text="no es xml")],
)
def test_errores_de_grobid_son_503(respuesta: httpx.Response) -> None:
    with pytest.raises(ErrorGrobid) as error:
        cliente(httpx.MockTransport(lambda _: respuesta)).cabecera(PDF)
    assert (error.value.estado_http, error.value.codigo) == (503, "grobid_no_disponible")


def test_grobid_sin_respuesta_es_503() -> None:
    def caido(solicitud: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin conexión", request=solicitud)

    with pytest.raises(ErrorGrobid, match="servicio de extracción"):
        cliente(httpx.MockTransport(caido)).cabecera(PDF)
