"""Extracción con Docling: texto, títulos, orden de lectura y páginas (T09, actividad 1).

Configuración (decisión T09-01, apartado 2):

* Solo PDF, con el modelo de diseño de página fijado en ``recursos.py`` y sin red.
* Sin OCR: un PDF escaneado se excluye del corpus científico (18.3); las guías
  escaneadas, si hicieran falta, son de T22.
* Sin estructura de tablas ni enriquecimientos (imágenes, fórmulas, código, gráficos).
* Docling se importa al crear el extractor: es una dependencia opcional (``corpus``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.corpus.bloques import Bloque, DocumentoExtraido, TipoBloque
from app.corpus.recursos import DISENO_DE_PAGINA, exigir

# Etiquetas de Docling (DocItemLabel) a tipos de bloque.
TIPOS_POR_ETIQUETA = {
    "title": TipoBloque.TITULO_DOCUMENTO,
    "section_header": TipoBloque.TITULO_SECCION,
    "text": TipoBloque.PARRAFO,
    "paragraph": TipoBloque.PARRAFO,
    "list_item": TipoBloque.ELEMENTO_LISTA,
    "caption": TipoBloque.LEYENDA,
    "footnote": TipoBloque.NOTA,
    "page_header": TipoBloque.ENCABEZADO_PAGINA,
    "page_footer": TipoBloque.PIE_PAGINA,
    "table": TipoBloque.TABLA,
    "formula": TipoBloque.FORMULA,
    "reference": TipoBloque.REFERENCIA,
}


class ErrorExtraccion(RuntimeError):
    """Docling no pudo convertir el PDF."""


@dataclass(frozen=True)
class OpcionesDocling:
    """Rendimiento y memoria de Docling (decisión T10-02). No cambian qué se extrae.

    * ``motor``: lector del PDF (``docling_parse`` o ``pypdfium2``).
    * ``hilos``: hilos de PyTorch para el modelo de diseño de página.
    * ``lote_paginas``: páginas por pasada del modelo de diseño de página.
    * ``cola_paginas``: páginas en espera entre etapas de Docling (acota la memoria).
    """

    # Medido con 3 PDF reales (89 páginas): mismo texto extraído que con los valores de
    # Docling (lote 4, cola 100), 5 % menos de tiempo y pico de 2,6 GB en lugar de 3,6 GB.
    # pypdfium2 se descartó: duplicaba texto (14 298 palabras de un PDF que tiene 9 712).
    motor: str = "docling_parse"
    hilos: int = 4
    lote_paginas: int = 1
    cola_paginas: int = 4

    def firma(self) -> str:
        return f"motor={self.motor}"


MOTORES = ("docling_parse", "pypdfium2")


class ExtractorDocling:
    def __init__(self, recursos: Path, opciones: OpcionesDocling | None = None) -> None:
        exigir(recursos)
        self.opciones = opciones = opciones or OpcionesDocling()
        if opciones.motor not in MOTORES:
            raise ValueError(f"motor de Docling desconocido: {opciones.motor}")
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        if opciones.motor == "pypdfium2":
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend as Motor
        else:
            from docling.backend.docling_parse_v4_backend import (
                DoclingParseV4DocumentBackend as Motor,
            )
        hilos = opciones.hilos
        tuberia = PdfPipelineOptions(
            artifacts_path=recursos,
            do_ocr=False,
            do_table_structure=False,
            do_picture_classification=False,
            do_picture_description=False,
            do_code_enrichment=False,
            do_formula_enrichment=False,
            generate_page_images=False,
            generate_picture_images=False,
            enable_remote_services=False,
            allow_external_plugins=False,
            accelerator_options=AcceleratorOptions(num_threads=hilos, device=AcceleratorDevice.CPU),
            layout_batch_size=opciones.lote_paginas,
            queue_max_size=opciones.cola_paginas,
        )
        self._convertidor = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=tuberia, backend=Motor)
            },
        )

    @property
    def firma(self) -> str:
        """Lo que determina el resultado de la extracción (para la caché): versión de
        Docling, revisión del modelo de diseño de página y motor de lectura del PDF."""
        from importlib.metadata import version

        return (
            f"docling={version('docling-slim')};layout={DISENO_DE_PAGINA.revision};"
            f"{self.opciones.firma()};bloques=1"
        )

    def extraer(self, ruta: Path) -> DocumentoExtraido:
        from docling.datamodel.base_models import ConversionStatus
        from docling_core.types.doc import ContentLayer, DocItem

        resultado = self._convertidor.convert(ruta, raises_on_error=False)
        if resultado.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
            raise ErrorExtraccion(f"Docling terminó con estado {resultado.status.value}")
        documento = resultado.document
        bloques: list[Bloque] = []
        capas = {ContentLayer.BODY, ContentLayer.FURNITURE}
        for item, _ in documento.iterate_items(with_groups=False, included_content_layers=capas):
            if isinstance(item, DocItem):
                bloque = _bloque(item, item.content_layer is ContentLayer.FURNITURE)
                if bloque is not None:
                    bloques.append(bloque)
        return DocumentoExtraido(num_paginas=documento.num_pages(), bloques=bloques)


def _bloque(item: Any, es_mobiliario: bool) -> Bloque | None:
    paginas = [p.page_no for p in item.prov]
    if not paginas:
        return None
    tipo = TIPOS_POR_ETIQUETA.get(str(item.label.value), TipoBloque.OTRO)
    if es_mobiliario and tipo is not TipoBloque.PIE_PAGINA:
        tipo = TipoBloque.ENCABEZADO_PAGINA
    return Bloque(
        tipo=tipo,
        texto=str(getattr(item, "text", "") or ""),
        pagina_inicio=min(paginas),
        pagina_fin=max(paginas),
    )
