"""Almacén de los PDF del corpus (T10; Fase 1, 18.2 y 18.10).

* Cada archivo se guarda con un nombre aleatorio en ``DIRECTORIO_ARCHIVOS/corpus/``,
  fuera de toda carpeta pública. La base guarda solo la ruta relativa.
* Los PDF no se redistribuyen: ninguna ruta de la API los sirve. Se conservan para
  volver a segmentar si cambia la ventana (T34) sin pedir otra vez los archivos.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

SUBCARPETA = "corpus"


class AlmacenArchivos:
    def __init__(self, base: Path) -> None:
        self._base = base

    def guardar(self, origen: Path) -> str:
        """Copia el archivo con un nombre aleatorio y devuelve su ruta relativa."""
        relativa = f"{SUBCARPETA}/{uuid.uuid4().hex}.pdf"
        destino = self._base / relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origen, destino)
        return relativa

    def borrar(self, relativa: str) -> None:
        self.ruta(relativa).unlink(missing_ok=True)

    def ruta(self, relativa: str) -> Path:
        ruta = (self._base / relativa).resolve()
        if not ruta.is_relative_to(self._base.resolve()):
            raise ValueError("ruta fuera del almacén")
        return ruta
