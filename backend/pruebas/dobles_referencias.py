"""Dobles de la verificación de referencias (T20): GROBID, Crossref y OpenAlex, sin red.

* GROBID: la respuesta real grabada para la lista de cada borrador de muestra
  (``pruebas/contrato/grobid/referencias_t20_<norma>.tei.xml``).
* Crossref y OpenAlex: ``httpx.MockTransport`` que responde a partir de
  ``pruebas/datos/referencias_t20.py``. La obra ``CAIDA`` responde 503; con ``caidos``,
  todos los servicios responden 503 (CP-13).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx

from app.agentes.referencias import AtencionReferencias
from app.agentes.verificacion_referencias import Verificador
from app.bibliografia.normalizacion import normalizar
from app.corpus.grobid import ClienteGrobid
from app.llm.interfaces import ModeloLenguaje
from app.repositorios.unidad import FabricaUnidades
from pruebas.datos.referencias_t20 import OBRAS, Escenario, Obra
from pruebas.dobles_bibliografia import clientes, json_respuesta

GROBID = Path(__file__).parent / "contrato" / "grobid"
E = Escenario
REGISTRADAS = [o for o in OBRAS if o.existe]


def _item(obra: Obra) -> dict[str, Any]:
    fuente = obra.fuente
    autores: Any = fuente["autores"]
    item: dict[str, Any] = {
        "title": [fuente["titulo"]],
        "author": [{"family": apellido, "given": inicial} for apellido, inicial in autores],
        "issued": {"date-parts": [[fuente["anio"]]]},
        "type": "book" if obra.revista is None else "journal-article",
    }
    if obra.revista:
        item["container-title"] = [obra.revista]
    if obra.editorial:
        item["publisher"] = obra.editorial
    if fuente["doi"]:
        item["DOI"] = fuente["doi"]
    return item


def _por_doi(doi: str) -> Obra | None:
    return next((o for o in REGISTRADAS if o.fuente["doi"] == doi), None)


def _por_titulo(consulta: str) -> Obra | None:
    texto = normalizar(consulta)
    return next((o for o in REGISTRADAS if normalizar(str(o.fuente["titulo"])) in texto), None)


def _crossref(peticion: httpx.Request) -> httpx.Response:
    ruta = unquote(peticion.url.path)
    if ruta.startswith("/works/"):
        obra = _por_doi(ruta.removeprefix("/works/").lower())
        if obra is None:
            return httpx.Response(404)
        if obra.escenario is E.CAIDA:
            return httpx.Response(503)
        return json_respuesta({"status": "ok", "message": _item(obra)})
    obra = _por_titulo(peticion.url.params.get("query.bibliographic", ""))
    if obra is not None and obra.escenario is E.CAIDA:
        return httpx.Response(503)
    items = [_item(obra)] if obra is not None else []
    return json_respuesta({"status": "ok", "message": {"items": items}})


def _openalex(peticion: httpx.Request) -> httpx.Response:
    """OpenAlex no conoce ninguna (Crossref las confirma); con la caída también responde 503."""
    ruta = unquote(peticion.url.path)
    if ruta.startswith("/works/doi:"):
        obra = _por_doi(ruta.removeprefix("/works/doi:").lower())
        if obra is not None and obra.escenario is E.CAIDA:
            return httpx.Response(503)
        return json_respuesta({"error": "no existe"}, 404)
    obra = _por_titulo(peticion.url.params.get("search", "") or str(peticion.url))
    if obra is not None and obra.escenario is E.CAIDA:
        return httpx.Response(503)
    return json_respuesta({"results": []})


def servicios(caidos: bool = False) -> Callable[[httpx.Request], httpx.Response]:
    def manejar(peticion: httpx.Request) -> httpx.Response:
        if caidos:
            return httpx.Response(503)
        if peticion.url.host == "api.crossref.org":
            return _crossref(peticion)
        if peticion.url.host == "api.openalex.org":
            return _openalex(peticion)
        raise AssertionError(f"servicio inesperado: {peticion.url.host}")

    return manejar


def grobid(caido: bool = False) -> Callable[[httpx.Request], httpx.Response]:
    def manejar(peticion: httpx.Request) -> httpx.Response:
        if caido or peticion.url.path != "/api/processCitationList":
            return httpx.Response(500)
        norma = "ieee" if b"%5B1%5D" in peticion.content else "apa7"  # "[1]" al inicio en IEEE
        return httpx.Response(
            200,
            content=(GROBID / f"referencias_t20_{norma}.tei.xml").read_bytes(),
            headers={"content-type": "application/xml"},
        )

    return manejar


def crear_atencion(
    abrir: FabricaUnidades,
    reloj: Callable[[], datetime],
    *,
    caidos: bool = False,
    grobid_caido: bool = False,
    modelo: ModeloLenguaje | None = None,
) -> AtencionReferencias:
    simulados = clientes(httpx.MockTransport(servicios(caidos)), intentos=1)
    extractor = ClienteGrobid(
        "http://grobid.prueba",
        cliente=httpx.Client(
            base_url="http://grobid.prueba", transport=httpx.MockTransport(grobid(grobid_caido))
        ),
    )
    return AtencionReferencias(
        extractor, Verificador(simulados.crossref, simulados.openalex), modelo, reloj
    )
