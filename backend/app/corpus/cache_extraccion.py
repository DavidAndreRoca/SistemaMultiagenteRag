"""Caché de la extracción de Docling por huella del PDF (decisión T10-02).

Docling es la etapa más cara de la ingesta. Su resultado (``DocumentoExtraido``: bloques
con tipo, texto y páginas) depende solo del PDF y de la configuración del extractor, así
que se guarda comprimido con una clave de dos partes:

* la huella SHA-256 del archivo;
* la firma del extractor (versión de Docling, revisión del modelo de diseño de página y
  motor de lectura). Si cambia cualquiera de ellas, la entrada anterior no se usa.

Con la caché, volver a segmentar (otra ventana, otras reglas de limpieza) o repetir una
ingesta no vuelve a leer los PDF con Docling. Un archivo de caché dañado se ignora y se
vuelve a extraer. Los errores de extracción no se guardan.

La caché contiene texto de los documentos: vive junto a los PDF, en la carpeta privada
``DIRECTORIO_ARCHIVOS/extraccion/``, y nunca se sirve.
"""

from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path

from pydantic import ValidationError

from app.comun.registro import obtener_registrador
from app.corpus.bloques import DocumentoExtraido
from app.corpus.extraccion import Extractor
from app.corpus.validacion import huella

_registro = obtener_registrador("corpus")


class ExtractorEnCache:
    def __init__(self, extractor: Extractor, carpeta: Path, firma: str) -> None:
        self._extractor = extractor
        self._carpeta = carpeta
        self.firma = firma
        self._clave = hashlib.sha256(firma.encode()).hexdigest()[:12]
        self.aciertos = 0
        self.fallos = 0

    def ruta_de(self, huella_archivo: str) -> Path:
        return self._carpeta / huella_archivo[:2] / f"{huella_archivo}.{self._clave}.json.gz"

    def leer(self, huella_archivo: str) -> DocumentoExtraido | None:
        ruta = self.ruta_de(huella_archivo)
        if not ruta.is_file():
            return None
        try:
            return DocumentoExtraido.model_validate_json(gzip.decompress(ruta.read_bytes()))
        except (OSError, EOFError, ValidationError, ValueError):
            _registro.warning("cache de extraccion dañada", extra={"tipo_evento": "corpus"})
            return None

    def extraer(self, ruta: Path) -> DocumentoExtraido:
        huella_archivo = huella(ruta.read_bytes())
        guardado = self.leer(huella_archivo)
        if guardado is not None:
            self.aciertos += 1
            return guardado
        self.fallos += 1
        extraido = self._extractor.extraer(ruta)
        self._guardar(huella_archivo, extraido)
        return extraido

    def _guardar(self, huella_archivo: str, extraido: DocumentoExtraido) -> None:
        destino = self.ruta_de(huella_archivo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = destino.with_suffix(f".{os.getpid()}.parcial")
        temporal.write_bytes(gzip.compress(extraido.model_dump_json().encode(), compresslevel=6))
        temporal.replace(destino)
