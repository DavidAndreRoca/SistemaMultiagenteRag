"""Almacén privado de archivos subidos (T10 para el corpus, T11 para los borradores).

Cada archivo se guarda con un nombre aleatorio en ``DIRECTORIO_ARCHIVOS/<subcarpeta>/``,
fuera de toda carpeta pública, y la base guarda solo la ruta relativa. Ninguna ruta de la
API sirve estos archivos.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path


class AlmacenPrivado:
    def __init__(self, base: Path, subcarpeta: str, extension: str) -> None:
        self._base = base
        self._subcarpeta = subcarpeta
        self._extension = extension

    def guardar(self, origen: Path) -> str:
        """Copia el archivo con un nombre aleatorio y devuelve su ruta relativa."""
        relativa = f"{self._subcarpeta}/{uuid.uuid4().hex}{self._extension}"
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
