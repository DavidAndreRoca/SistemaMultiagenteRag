"""Referencias del artículo O1 o de una lista de DOI (T15-01, apartado 2).

Sin acceso a la base. Quien llama borra el archivo del artículo en cuanto esta función
termina, haya extraído algo o no (RN-19).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path, PureWindowsPath
from typing import Protocol

from app.bd.enumeraciones import OrigenImportacion
from app.bibliografia.normalizacion import normalizar_doi
from app.borradores.extraccion import ParrafoBorrador, extraer_parrafos
from app.borradores.secciones import detectar_por_estilos
from app.borradores.validacion import BorradorRechazado, validar_docx
from app.comun.errores import ErrorAplicacion
from app.corpus.grobid import ReferenciaGrobid
from app.corpus.secciones import es_referencia_bibliografica
from app.corpus.validacion import LimitesPdf, validar_pdf

MAX_REFERENCIAS = 500
_SEPARADOR_DOI = re.compile(r"[\s,;]+")


class ExtractorReferencias(Protocol):
    """Lo que el importador necesita de GROBID (``app/corpus/grobid.py``)."""

    def referencias(self, ruta: Path) -> list[ReferenciaGrobid]: ...

    def referencias_de_texto(self, entradas: list[str]) -> list[ReferenciaGrobid]: ...


class ErrorImportacion(ErrorAplicacion):
    def __init__(self, codigo: str, mensaje: str, estado_http: int = 422) -> None:
        super().__init__(codigo, mensaje, estado_http=estado_http)


def origen_de(nombre: str | None) -> OrigenImportacion:
    extension = PureWindowsPath(nombre or "").suffix.lower()
    if extension == ".pdf":
        return OrigenImportacion.PDF
    if extension == ".docx":
        return OrigenImportacion.DOCX
    raise ErrorImportacion(
        "formato_no_admitido",
        "El artículo debe ser un PDF o un .docx. También puede pegar una lista de DOI.",
    )


def referencias_del_archivo(
    ruta: Path,
    origen: OrigenImportacion,
    nombre: str | None,
    tipo: str | None,
    extractor: ExtractorReferencias,
    limites: LimitesPdf,
) -> list[ReferenciaGrobid]:
    if origen is OrigenImportacion.PDF:
        informe = validar_pdf(ruta, limites)
        if not informe.valido:
            assert informe.motivo is not None
            raise ErrorImportacion(
                "articulo_no_valido",
                f"El PDF del artículo no se puede procesar ({informe.motivo.value}).",
            )
        referencias = extractor.referencias(ruta)
    else:
        try:
            validar_docx(ruta, nombre, tipo)
        except BorradorRechazado as rechazo:
            raise ErrorImportacion("articulo_no_valido", rechazo.mensaje) from None
        entradas = entradas_de_referencias(extraer_parrafos(ruta).parrafos)
        referencias = extractor.referencias_de_texto(entradas)
    if not referencias:
        raise ErrorImportacion(
            "sin_referencias",
            "No se encontró la lista de referencias del artículo. Revise que tenga una"
            " sección de referencias o pegue la lista de DOI.",
        )
    return referencias[:MAX_REFERENCIAS]


def entradas_de_referencias(parrafos: Sequence[ParrafoBorrador]) -> list[str]:
    """Entradas de la lista de referencias de un .docx: la sección que detecta T12 o, si no
    tiene un título reconocible, los párrafos con forma de entrada bibliográfica."""
    secciones = detectar_por_estilos(parrafos)
    if secciones is not None and secciones.referencias is not None:
        return secciones.referencias.entradas
    return [
        linea.strip()
        for p in parrafos
        if es_referencia_bibliografica(p.texto)
        for linea in p.texto.split("\n")
        if linea.strip()
    ]


def referencias_de_dois(texto: str) -> tuple[list[ReferenciaGrobid], list[str]]:
    """Cada DOI de la lista (uno por línea, o separados por comas o espacios) y los que no
    tienen forma de DOI."""
    validas: list[ReferenciaGrobid] = []
    invalidas: list[str] = []
    vistos: set[str] = set()
    for parte in _SEPARADOR_DOI.split(texto.strip()):
        if not parte:
            continue
        doi = normalizar_doi(parte)
        if doi is None:
            invalidas.append(parte[:200])
        elif doi not in vistos:
            vistos.add(doi)
            validas.append(ReferenciaGrobid(texto=f"https://doi.org/{doi}", doi=doi))
    return validas[:MAX_REFERENCIAS], invalidas
