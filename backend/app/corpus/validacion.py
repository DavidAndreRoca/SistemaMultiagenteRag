"""Validación del PDF antes de procesarlo (T09, tareas técnicas; RN-16).

Se comprueba, en este orden y sin ejecutar nada del documento (RN-23):

1. Tamaño (25 MB): se mira antes de leer el archivo.
2. Tipo real: la firma ``%PDF-`` en el primer kilobyte, no la extensión.
3. Que se pueda abrir y no exija contraseña de apertura. Un PDF que solo restringe
   permisos (imprimir, copiar) se abre con contraseña vacía y se admite (decisión
   T09-01, apartado 3).
4. Páginas (60).
5. Capa de texto: si menos de la mitad de las páginas tiene texto, el PDF se considera
   escaneado y se excluye del corpus científico (18.3, actividad 8).
"""

from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PageObject, PdfReader
from pypdf.errors import PyPdfError

from app.corpus.esquemas import MotivoExclusion

FIRMA_PDF = b"%PDF-"
BYTES_CABECERA = 1024
MIN_CARACTERES_PAGINA_CON_TEXTO = 40
FRACCION_MINIMA_PAGINAS_CON_TEXTO = 0.5
BYTES_POR_MB = 1024 * 1024

logging.getLogger("pypdf").setLevel(logging.ERROR)  # sus avisos citan texto del PDF


@dataclass(frozen=True)
class LimitesPdf:
    tamano_max_mb: int
    paginas_max: int


@dataclass(frozen=True)
class InformeValidacion:
    huella_archivo: str
    motivo: MotivoExclusion | None = None
    num_paginas: int | None = None
    paginas_con_texto: int | None = None

    @property
    def valido(self) -> bool:
        return self.motivo is None


def huella(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def validar_pdf(ruta: Path, limites: LimitesPdf) -> InformeValidacion:
    tamano = ruta.stat().st_size
    if tamano > limites.tamano_max_mb * BYTES_POR_MB:
        return InformeValidacion(_huella_por_partes(ruta), MotivoExclusion.EXCEDE_TAMANO)
    contenido = ruta.read_bytes()
    firma_archivo = huella(contenido)
    if FIRMA_PDF not in contenido[:BYTES_CABECERA]:
        return InformeValidacion(firma_archivo, MotivoExclusion.NO_ES_PDF)
    try:
        lector = PdfReader(io.BytesIO(contenido))
        if lector.is_encrypted and not lector.decrypt(""):
            return InformeValidacion(firma_archivo, MotivoExclusion.PDF_CIFRADO)
        paginas = len(lector.pages)
    except (PyPdfError, ValueError, KeyError, TypeError, OSError):
        return InformeValidacion(firma_archivo, MotivoExclusion.PDF_ILEGIBLE)
    if paginas == 0:
        return InformeValidacion(firma_archivo, MotivoExclusion.PDF_ILEGIBLE, 0)
    if paginas > limites.paginas_max:
        return InformeValidacion(firma_archivo, MotivoExclusion.EXCEDE_PAGINAS, paginas)
    con_texto = sum(1 for pagina in lector.pages if _tiene_texto(pagina))
    if con_texto < paginas * FRACCION_MINIMA_PAGINAS_CON_TEXTO:
        return InformeValidacion(
            firma_archivo, MotivoExclusion.SIN_CAPA_DE_TEXTO, paginas, con_texto
        )
    return InformeValidacion(firma_archivo, None, paginas, con_texto)


def _tiene_texto(pagina: PageObject) -> bool:
    try:
        texto = pagina.extract_text()
    except Exception:  # una página dañada cuenta como página sin texto
        return False
    return sum(1 for c in texto if not c.isspace()) >= MIN_CARACTERES_PAGINA_CON_TEXTO


def _huella_por_partes(ruta: Path) -> str:
    calculo = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for parte in iter(lambda: archivo.read(BYTES_POR_MB), b""):
            calculo.update(parte)
    return calculo.hexdigest()
