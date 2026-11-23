"""Formateador de referencias con estilos CSL locales (T18-01, apartado 5; RN-17).

Arma la referencia de un documento a partir de sus metadatos guardados, sin red y sin
modelo de lenguaje, con ``citeproc-py`` y los estilos oficiales de cada norma de D-12.
Se usa cuando el documento no tiene DOI o cuando doi.org no responde.

Los estilos vienen del repositorio oficial de estilos CSL (paquete ``citeproc-py-styles``
0.2.0), con licencia CC BY-SA 3.0, en ``estilos/``. Su huella se comprueba al cargarlos:
un estilo modificado no se usa.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
    formatter,
)
from citeproc.source.json import CiteProcJSON
from pydantic import BaseModel, ConfigDict

DIRECTORIO_ESTILOS = Path(__file__).parent / "estilos"
LOCALE = "es-ES"


class EstiloCsl(BaseModel):
    model_config = ConfigDict(frozen=True)

    archivo: str
    huella: str
    titulo: str


# Normas de la lista cerrada de D-12 y su estilo CSL oficial.
ESTILOS: dict[str, EstiloCsl] = {
    "apa7": EstiloCsl(
        archivo="apa.csl",
        huella="17bc430cf931767d551a894129b3a705e1feee91090295c09674e370ccdef5d9",
        titulo="APA Style 7th edition",
    ),
    "ieee": EstiloCsl(
        archivo="ieee.csl",
        huella="6dee2b87ce90a7ab86f232d78a9216f47adc6193f13b6307b4a83c65594e721a",
        titulo="IEEE Reference Guide version 11.29.2023",
    ),
    "vancouver": EstiloCsl(
        archivo="nlm-citation-sequence.csl",
        huella="42759650b00306c02aa5786db843c8ed67128a86b2ec0a1825a1f4e6387d51cc",
        titulo="NLM/Vancouver: Citing Medicine 2nd edition (citation-sequence)",
    ),
}

# IEEE y Vancouver numeran la lista: una referencia suelta no lleva número (T18-01).
_NUMERO_DE_LISTA = re.compile(r"^\s*(\[\d+\]|\d+\.)\s*")


class NormaNoAdmitida(ValueError):
    pass


class EstiloAlterado(RuntimeError):
    pass


def quitar_numero(texto: str) -> str:
    return _NUMERO_DE_LISTA.sub("", " ".join(texto.split()))


def huella_estilo(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@lru_cache(maxsize=4)
def _estilo(norma: str) -> CitationStylesStyle:
    definicion = ESTILOS.get(norma)
    if definicion is None:
        raise NormaNoAdmitida(f"norma sin estilo CSL: {norma}")
    ruta = DIRECTORIO_ESTILOS / definicion.archivo
    if huella_estilo(ruta) != definicion.huella:
        raise EstiloAlterado(f"el estilo {definicion.archivo} no coincide con su huella")
    return CitationStylesStyle(str(ruta), locale=LOCALE, validate=False)


def item_csl(identificador: str, metadatos: dict[str, Any]) -> dict[str, Any]:
    """Elemento CSL-JSON desde los metadatos guardados de un documento.

    ``metadatos``: ``titulo``, ``autores`` (``[{nombres, apellidos}]``), ``anio``,
    ``revista_editorial``, ``isbn``, ``doi``, ``idioma`` y ``url``.
    """
    es_libro = bool(metadatos.get("isbn"))
    item: dict[str, Any] = {
        "id": identificador,
        "type": "book" if es_libro else "article-journal",
        "title": metadatos.get("titulo") or "Sin título",
        "author": [
            {"family": a["apellidos"], **({"given": a["nombres"]} if a.get("nombres") else {})}
            for a in metadatos.get("autores") or []
            if isinstance(a, dict) and a.get("apellidos")
        ],
    }
    if metadatos.get("anio"):
        item["issued"] = {"date-parts": [[int(metadatos["anio"])]]}
    if metadatos.get("revista_editorial"):
        item["publisher" if es_libro else "container-title"] = metadatos["revista_editorial"]
    for clave, campo in (("doi", "DOI"), ("isbn", "ISBN"), ("url", "URL"), ("idioma", "language")):
        if metadatos.get(clave):
            item[campo] = metadatos[clave]
    return item


def formatear(norma: str, metadatos: dict[str, Any]) -> str:
    """La referencia en la norma, en texto plano y sin número de lista."""
    estilo = _estilo(norma)
    fuente = CiteProcJSON([item_csl("ref", metadatos)])
    bibliografia = CitationStylesBibliography(estilo, fuente, formatter.plain)
    bibliografia.register(Citation([CitationItem("ref")]))
    (entrada,) = bibliografia.bibliography()
    return quitar_numero(str(entrada))
