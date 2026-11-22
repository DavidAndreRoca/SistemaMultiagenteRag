"""Construcción del importador real a partir de los ajustes (T15).

Usa el indexador de T10 (Docling, GROBID, servicio de modelos y almacén), GROBID para
las referencias, los servicios de T14 y un cliente HTTP propio para las descargas.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import httpx

from app.bibliografia.fabrica import NOMBRE_CLIENTE, crear_servicios
from app.configuracion import Ajustes
from app.corpus.fabrica import CorpusNoConfigurado
from app.corpus.grobid import ClienteGrobid
from app.corpus.indexacion import Indexador
from app.importacion.descarga import Descargador
from app.importacion.resolucion import Localizador
from app.importacion.servicio import Importador
from app.repositorios.unidad import FabricaUnidades

TIEMPO_DESCARGA_S = 60.0


def crear_importador(
    ajustes: Ajustes,
    abrir: FabricaUnidades,
    indexador: Indexador,
    reloj: Callable[[], datetime],
) -> Importador:
    if not ajustes.url_grobid or not ajustes.directorio_archivos:
        faltan = [
            nombre
            for nombre, valor in (
                ("URL_GROBID", ajustes.url_grobid),
                ("DIRECTORIO_ARCHIVOS", ajustes.directorio_archivos),
            )
            if not valor
        ]
        raise CorpusNoConfigurado(faltan)
    servicios = crear_servicios(ajustes, abrir)
    descargas = httpx.AsyncClient(
        timeout=httpx.Timeout(TIEMPO_DESCARGA_S, connect=10.0),
        headers={"User-Agent": NOMBRE_CLIENTE},
        follow_redirects=True,
    )
    return Importador(
        extractor=ClienteGrobid(ajustes.url_grobid),
        localizador=Localizador(servicios.crossref, servicios.openalex),
        unpaywall=servicios.unpaywall,
        descargador=Descargador(descargas),
        indexador=indexador,
        abrir=abrir,
        directorio=Path(ajustes.directorio_archivos),
        reloj=reloj,
    )
