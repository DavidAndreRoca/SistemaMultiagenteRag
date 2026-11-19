"""Construcción del indexador real a partir de los ajustes (T10).

Necesita GROBID, el servicio de modelos, los recursos del canal y la carpeta de
archivos. Si falta alguno, la ingesta responde 503 con los nombres de las variables;
el resto de la API sigue funcionando.
"""

from __future__ import annotations

from pathlib import Path

from app.administracion.parametros import parametros_iniciales
from app.comun.errores import ErrorAplicacion
from app.configuracion import Ajustes
from app.corpus.almacen import AlmacenArchivos
from app.corpus.extraccion import ParametrosCanal, crear_canal
from app.corpus.extractor_docling import OpcionesDocling
from app.corpus.indexacion import Indexador
from app.inferencia.servicio_modelos import cliente_desde_ajustes

CARPETA_CACHE = "extraccion"  # caché de Docling, junto a los PDF (decisión T10-02)


class CorpusNoConfigurado(ErrorAplicacion):
    def __init__(self, faltan: list[str]) -> None:
        super().__init__(
            "corpus_no_configurado",
            "La ingesta de documentos no está configurada en este servidor.",
            estado_http=503,
            detalle={"variables": faltan},
        )


def _exigir(ajustes: Ajustes, nombres: dict[str, str | None]) -> None:
    faltan = [nombre for nombre, valor in nombres.items() if not valor]
    if faltan:
        raise CorpusNoConfigurado(faltan)


def crear_indexador(ajustes: Ajustes) -> Indexador:
    """Indexador con Docling, GROBID, el tokenizador, el servicio de modelos y el almacén.

    Los parámetros del canal se toman de la configuración vigente en cada ingesta; los de
    aquí solo sirven para crear el canal.
    """
    _exigir(
        ajustes,
        {
            "DIRECTORIO_RECURSOS_CORPUS": ajustes.directorio_recursos_corpus,
            "URL_GROBID": ajustes.url_grobid,
            "URL_SERVICIO_MODELOS": ajustes.url_servicio_modelos,
            "DIRECTORIO_ARCHIVOS": ajustes.directorio_archivos,
        },
    )
    assert ajustes.directorio_recursos_corpus and ajustes.url_grobid
    assert ajustes.directorio_archivos
    archivos = Path(ajustes.directorio_archivos)
    canal = crear_canal(
        Path(ajustes.directorio_recursos_corpus),
        ajustes.url_grobid,
        ParametrosCanal.desde(parametros_iniciales()),
        opciones=OpcionesDocling(hilos=ajustes.hilos_docling),
        cache=archivos / CARPETA_CACHE,
    )
    return Indexador(canal, cliente_desde_ajustes(ajustes), AlmacenArchivos(archivos))


def crear_reindexador(ajustes: Ajustes) -> Indexador:
    """Indexador solo para volver a embeber: no carga Docling ni usa GROBID."""
    _exigir(ajustes, {"URL_SERVICIO_MODELOS": ajustes.url_servicio_modelos})
    return Indexador(None, cliente_desde_ajustes(ajustes), None)
