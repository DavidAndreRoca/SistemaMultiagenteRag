"""Cliente de GROBID para los metadatos de cabecera (T09, actividad 2).

* Usa ``/api/processHeaderDocument`` con ``consolidateHeader=0``: GROBID no consulta
  servicios externos. La comprobación con Crossref y OpenAlex llega en T14 y T15.
* El PDF solo viaja al GROBID local del proyecto compartido, nunca a un tercero (RNF-10).
* Una caída de GROBID es un error transitorio (503), no un estado del documento: la
  ingesta lo informa y se reintenta (decisión T09-01, apartado 6).
* No registra el contenido: solo el estado HTTP y la duración (4.6).
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from app.bibliografia.normalizacion import normalizar_doi
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.corpus.esquemas import Autor, MetadatosCabecera

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
PATRON_DOI_EN_TEXTO = re.compile(r"10\.\d{4,9}/[^\s\"<>]+")
TIEMPO_MAXIMO_S = 180.0  # la primera solicitud carga los modelos de GROBID

_registro = obtener_registrador("corpus")


class ErrorGrobid(ErrorAplicacion):
    """GROBID no respondió o respondió algo fuera de contrato (503)."""

    def __init__(self, motivo: str) -> None:
        super().__init__(
            "grobid_no_disponible",
            "El servicio de extracción de metadatos no está disponible. Intente más tarde.",
            estado_http=503,
        )
        self.motivo = motivo


def _texto(elemento: ET.Element | None) -> str | None:
    if elemento is None:
        return None
    texto = " ".join("".join(elemento.itertext()).split())
    return texto or None


def _anio(biblio: ET.Element) -> int | None:
    fechas = biblio.findall(f"{TEI}monogr/{TEI}imprint/{TEI}date")
    publicadas = [f for f in fechas if f.get("type") == "published"] or fechas
    for fecha in publicadas:
        coincidencia = re.match(r"(\d{4})", fecha.get("when") or _texto(fecha) or "")
        if coincidencia and 1500 <= int(coincidencia.group(1)) <= 2100:
            return int(coincidencia.group(1))
    return None


def metadatos_desde_tei(tei: str) -> MetadatosCabecera:
    """Lee título, autores, año, DOI, revista e idioma de la cabecera TEI de GROBID."""
    raiz = ET.fromstring(tei)
    cabecera = raiz.find(f"{TEI}teiHeader")
    if cabecera is None:
        raise ValueError("la respuesta no tiene teiHeader")
    biblio = cabecera.find(f"{TEI}fileDesc/{TEI}sourceDesc/{TEI}biblStruct")
    titulo = _texto(cabecera.find(f"{TEI}fileDesc/{TEI}titleStmt/{TEI}title"))
    if biblio is None:
        return MetadatosCabecera(titulo=titulo, idioma=cabecera.get(XML_LANG))

    autores: list[Autor] = []
    for persona in biblio.iterfind(f"{TEI}analytic/{TEI}author/{TEI}persName"):
        apellidos = _texto(persona.find(f"{TEI}surname"))
        nombres = " ".join(t for t in (_texto(n) for n in persona.findall(f"{TEI}forename")) if t)
        if apellidos:
            autores.append(Autor(nombres=nombres or None, apellidos=apellidos))

    doi = next(
        (
            normalizar_doi(_texto(i))
            for i in biblio.iter(f"{TEI}idno")
            if (i.get("type") or "").upper() == "DOI" and normalizar_doi(_texto(i))
        ),
        None,
    )
    revista = next(
        (_texto(t) for t in biblio.findall(f"{TEI}monogr/{TEI}title") if t.get("level") == "j"),
        None,
    )
    idioma = cabecera.get(XML_LANG)
    return MetadatosCabecera(
        titulo=titulo,
        autores=autores,
        anio=_anio(biblio),
        doi=doi,
        revista=revista,
        idioma=idioma[:8] if idioma else None,
    )


class ReferenciaGrobid(BaseModel):
    """Una entrada de la lista de referencias, analizada por GROBID (T15)."""

    model_config = ConfigDict(frozen=True)

    texto: str  # la entrada tal como aparece en el artículo
    titulo: str | None = None
    apellidos: list[str] = []
    anio: int | None = None
    doi: str | None = None


def referencias_desde_tei(tei: str) -> list[ReferenciaGrobid]:
    """Cada ``biblStruct`` del TEI de ``processReferences`` o ``processCitationList``."""
    raiz = ET.fromstring(tei)
    referencias = []
    for biblio in raiz.iter(f"{TEI}biblStruct"):
        crudo = next(
            (_texto(n) for n in biblio.iter(f"{TEI}note") if n.get("type") == "raw_reference"),
            None,
        )
        titulo = _texto(biblio.find(f"{TEI}analytic/{TEI}title")) or _texto(
            biblio.find(f"{TEI}monogr/{TEI}title")
        )
        apellidos = [s for s in (_texto(x) for x in biblio.iter(f"{TEI}surname")) if s]
        doi = next(
            (
                normalizar_doi(_texto(i))
                for i in biblio.iter(f"{TEI}idno")
                if (i.get("type") or "").upper() == "DOI" and normalizar_doi(_texto(i))
            ),
            None,
        ) or _doi_en_texto(crudo)
        texto = crudo or titulo
        if not texto:
            continue  # sin texto ni título no hay referencia que resolver
        referencias.append(
            ReferenciaGrobid(
                texto=texto,
                titulo=titulo,
                apellidos=apellidos,
                anio=_anio(biblio),
                doi=doi,
            )
        )
    return referencias


def _doi_en_texto(texto: str | None) -> str | None:
    if not texto:
        return None
    hallado = PATRON_DOI_EN_TEXTO.search(texto)
    return normalizar_doi(hallado.group(0)) if hallado else None


class ClienteGrobid:
    def __init__(
        self,
        url_base: str,
        *,
        cliente: httpx.Client | None = None,
        tiempo_maximo_s: float = TIEMPO_MAXIMO_S,
    ) -> None:
        self._cliente = cliente or httpx.Client(
            base_url=url_base, timeout=httpx.Timeout(tiempo_maximo_s, connect=5.0)
        )

    def cerrar(self) -> None:
        self._cliente.close()

    def cabecera(self, ruta: Path) -> MetadatosCabecera:
        inicio = time.perf_counter()
        try:
            with ruta.open("rb") as archivo:
                respuesta = self._cliente.post(
                    "/api/processHeaderDocument",
                    files={"input": ("documento.pdf", archivo, "application/pdf")},
                    data={"consolidateHeader": "0"},
                    headers={"Accept": "application/xml"},
                )
        except httpx.HTTPError as error:
            raise ErrorGrobid(f"sin respuesta ({type(error).__name__})") from error
        _registro.info(
            "grobid cabecera",
            extra={
                "tipo_evento": "extraccion",
                "estado_http": respuesta.status_code,
                "duracion_ms": round((time.perf_counter() - inicio) * 1000),
            },
        )
        if respuesta.status_code == 204:  # GROBID no encontró cabecera
            return MetadatosCabecera()
        if respuesta.status_code != 200:
            raise ErrorGrobid(f"estado HTTP {respuesta.status_code}")
        try:
            return metadatos_desde_tei(respuesta.text)
        except (ET.ParseError, ValueError) as error:
            raise ErrorGrobid("respuesta no válida") from error

    def referencias(self, ruta: Path) -> list[ReferenciaGrobid]:
        """Lista de referencias de un PDF (``processReferences``, sin consolidar)."""
        with ruta.open("rb") as archivo:
            respuesta = self._post(
                "/api/processReferences",
                files={"input": ("articulo.pdf", archivo, "application/pdf")},
                data={"consolidateCitations": "0", "includeRawCitations": "1"},
            )
        return self._referencias(respuesta)

    def referencias_de_texto(self, entradas: list[str]) -> list[ReferenciaGrobid]:
        """Análisis de entradas ya separadas, por ejemplo las de un .docx
        (``processCitationList``)."""
        if not entradas:
            return []
        respuesta = self._post(
            "/api/processCitationList",
            data={
                "citations": entradas,
                "consolidateCitations": "0",
                "includeRawCitations": "1",
            },
        )
        return self._referencias(respuesta)

    def _post(self, ruta: str, **kwargs: Any) -> httpx.Response:
        inicio = time.perf_counter()
        try:
            respuesta = self._cliente.post(ruta, headers={"Accept": "application/xml"}, **kwargs)
        except httpx.HTTPError as error:
            raise ErrorGrobid(f"sin respuesta ({type(error).__name__})") from error
        _registro.info(
            "grobid referencias",
            extra={
                "tipo_evento": "importacion",
                "estado_http": respuesta.status_code,
                "duracion_ms": round((time.perf_counter() - inicio) * 1000),
            },
        )
        return respuesta

    @staticmethod
    def _referencias(respuesta: httpx.Response) -> list[ReferenciaGrobid]:
        if respuesta.status_code == 204:  # GROBID no encontró referencias
            return []
        if respuesta.status_code != 200:
            raise ErrorGrobid(f"estado HTTP {respuesta.status_code}")
        try:
            return referencias_desde_tei(respuesta.text)
        except (ET.ParseError, ValueError) as error:
            raise ErrorGrobid("respuesta no válida") from error
