"""Dobles del importador de referencias (T15): GROBID, servicios bibliográficos y descargas.

Todo sale de ``pruebas/datos/articulo_o1.py``: cada referencia ficticia declara su
escenario y aquí se responde en consecuencia, sin red.

* GROBID: las respuestas reales grabadas en ``pruebas/contrato/grobid/``.
* Crossref, Unpaywall y OpenAlex: ``httpx.MockTransport`` con respuestas armadas.
* Descargas: PDF del canal ficticio de T10 (``pruebas/dobles_corpus.py``), un 403 o una
  página HTML, según el escenario.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx

from app.bibliografia.normalizacion import normalizar
from app.corpus.grobid import ClienteGrobid
from app.corpus.indexacion import Indexador
from app.importacion.descarga import Descargador
from app.importacion.resolucion import Localizador
from app.importacion.servicio import Importador
from app.repositorios.unidad import FabricaUnidades
from pruebas.datos.articulo_o1 import REFERENCIAS, Escenario, Referencia
from pruebas.dobles_bibliografia import clientes, json_respuesta
from pruebas.dobles_corpus import contenido

GROBID = Path(__file__).parent / "contrato" / "grobid"
DESCARGAS = "https://descargas.example"
PAGINAS = "https://repositorio.example"
E = Escenario

ABIERTAS_CON_PDF = {E.INCLUIDA, E.DESCARGA_403, E.DESCARGA_HTML, E.POR_METADATOS, E.ESCANEADA}
CON_REGISTRO = ABIERTAS_CON_PDF | {E.SIN_ENLACE_DIRECTO, E.CERRADA, E.SIN_UNPAYWALL}


def doi_de(referencia: Referencia) -> str | None:
    return referencia.doi or referencia.doi_real


def _por_doi(doi: str) -> Referencia | None:
    return next((r for r in REFERENCIAS if doi_de(r) == doi), None)


def _por_titulo(texto: str) -> Referencia | None:
    consulta = normalizar(texto)
    return next((r for r in REFERENCIAS if normalizar(r.titulo) in consulta), None)


def _item_crossref(referencia: Referencia) -> dict[str, Any]:
    item: dict[str, Any] = {
        "title": [referencia.titulo],
        "author": [{"family": referencia.apellido, "given": referencia.inicial}],
        "issued": {"date-parts": [[referencia.anio]]},
        "container-title": [referencia.revista],
        "type": "journal-article",
    }
    if doi_de(referencia):
        item["DOI"] = doi_de(referencia)
    return item


def _crossref(peticion: httpx.Request) -> httpx.Response:
    ruta = unquote(peticion.url.path)
    if ruta.startswith("/works/"):
        referencia = _por_doi(ruta.removeprefix("/works/").lower())
        if referencia is None or referencia.escenario is E.CAIDA:
            return httpx.Response(503 if referencia else 404)
        return json_respuesta({"status": "ok", "message": _item_crossref(referencia)})
    referencia = _por_titulo(peticion.url.params.get("query.bibliographic", ""))
    if referencia is not None and referencia.escenario is E.CAIDA:
        return httpx.Response(503)
    items = (
        [_item_crossref(referencia)]
        if referencia is not None and referencia.escenario in (E.POR_METADATOS, E.SIN_DOI)
        else []
    )
    return json_respuesta({"status": "ok", "message": {"items": items}})


def _unpaywall(peticion: httpx.Request) -> httpx.Response:
    doi = unquote(peticion.url.path).removeprefix("/v2/").lower()
    referencia = _por_doi(doi)
    if referencia is None or referencia.escenario not in CON_REGISTRO - {E.SIN_UNPAYWALL}:
        return json_respuesta({"HTTP_status_code": 404, "error": True}, 404)
    abierta = referencia.escenario is not E.CERRADA
    pdf = f"{DESCARGAS}/{doi}.pdf" if referencia.escenario in ABIERTAS_CON_PDF else None
    return json_respuesta(
        {
            "doi": doi,
            "title": referencia.titulo,
            "is_oa": abierta,
            "oa_status": "gold" if abierta else "closed",
            "best_oa_location": {
                "url": f"{PAGINAS}/{doi}",
                "url_for_pdf": pdf,
                "license": "cc-by",
                "version": "publishedVersion",
            }
            if abierta
            else None,
        }
    )


DOI_DATACITE = "10.48550/arxiv.0000.00001"  # solo lo conoce OpenAlex (lista de DOI)


def _openalex(peticion: httpx.Request) -> httpx.Response:
    ruta = unquote(peticion.url.path)
    if ruta.startswith("/works/doi:"):
        if ruta.removeprefix("/works/doi:").lower() != DOI_DATACITE:
            return json_respuesta({"error": "no existe"}, 404)
        return json_respuesta(
            {
                "doi": f"https://doi.org/{DOI_DATACITE}",
                "title": "Preimpresión ficticia en un repositorio de DataCite",
                "publication_year": 2024,
                "authorships": [{"author": {"display_name": "Ana Ficticia"}}],
                "open_access": {"is_oa": True, "oa_status": "green"},
                "best_oa_location": {
                    "landing_page_url": f"{PAGINAS}/{DOI_DATACITE}",
                    "pdf_url": None,
                    "license": "cc-by",
                },
            }
        )
    return json_respuesta({"results": []})  # las búsquedas solo las confirma Crossref


def servicios(peticion: httpx.Request) -> httpx.Response:
    host = peticion.url.host
    if host == "api.crossref.org":
        return _crossref(peticion)
    if host == "api.unpaywall.org":
        return _unpaywall(peticion)
    if host == "api.openalex.org":
        return _openalex(peticion)
    raise AssertionError(f"servicio inesperado: {host}")


def descargas(peticion: httpx.Request) -> httpx.Response:
    doi = unquote(peticion.url.path).removeprefix("/").removesuffix(".pdf")
    referencia = _por_doi(doi)
    if referencia is None:
        return httpx.Response(404)
    if referencia.escenario is E.DESCARGA_403:
        return httpx.Response(403)
    if referencia.escenario is E.DESCARGA_HTML:
        return httpx.Response(200, content=b"<!doctype html><title>Acceso</title>")
    marca = "ESCANEADO" if referencia.escenario is E.ESCANEADA else "TUTORIA"
    variante = re.sub(r"\W", "-", doi)
    return httpx.Response(200, content=contenido(marca, f"DOI={doi} VARIANTE={variante}"))


def grobid(peticion: httpx.Request) -> httpx.Response:
    nombre = {
        "/api/processReferences": "referencias_pdf.tei.xml",
        "/api/processCitationList": "referencias_docx.tei.xml",
    }.get(peticion.url.path)
    if nombre is None:
        return httpx.Response(404)
    return httpx.Response(
        200,
        content=(GROBID / nombre).read_bytes(),
        headers={"content-type": "application/xml"},
    )


class Contador:
    """Cuenta las peticiones de un transporte simulado."""

    def __init__(self, manejador: Callable[[httpx.Request], httpx.Response]) -> None:
        self.peticiones: list[httpx.Request] = []
        self._manejador = manejador

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)
        return self._manejador(peticion)


def crear_importador(
    abrir: FabricaUnidades,
    indexador: Indexador,
    directorio: Path,
    reloj: Callable[[], datetime],
    *,
    antes_de_localizar: Callable[[], None] | None = None,
) -> tuple[Importador, Contador, Contador]:
    """Importador con todos los servicios simulados. Devuelve también los contadores de
    peticiones a los servicios bibliográficos y a las descargas."""
    a_servicios, a_descargas = Contador(servicios), Contador(descargas)
    simulados = clientes(httpx.MockTransport(a_servicios), intentos=1)
    localizador = Localizador(simulados.crossref, simulados.openalex)
    if antes_de_localizar is not None:
        localizar = localizador.localizar

        async def espiar(referencia: Any) -> Any:
            antes_de_localizar()
            return await localizar(referencia)

        localizador.localizar = espiar  # type: ignore[method-assign]
    importador = Importador(
        extractor=ClienteGrobid(
            "http://grobid.prueba",
            cliente=httpx.Client(
                base_url="http://grobid.prueba", transport=httpx.MockTransport(grobid)
            ),
        ),
        localizador=localizador,
        unpaywall=simulados.unpaywall,
        descargador=Descargador(httpx.AsyncClient(transport=httpx.MockTransport(a_descargas))),
        indexador=indexador,
        abrir=abrir,
        directorio=directorio,
        reloj=reloj,
    )
    return importador, a_servicios, a_descargas
