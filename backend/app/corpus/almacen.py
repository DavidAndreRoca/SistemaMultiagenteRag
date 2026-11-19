"""Almacén de los PDF del corpus (T10; Fase 1, 18.2 y 18.10).

* Cada archivo se guarda con un nombre aleatorio en ``DIRECTORIO_ARCHIVOS/corpus/``,
  fuera de toda carpeta pública. La base guarda solo la ruta relativa.
* Los PDF no se redistribuyen: ninguna ruta de la API los sirve. Se conservan para
  volver a segmentar si cambia la ventana (T34) sin pedir otra vez los archivos.
"""

from __future__ import annotations

from pathlib import Path

from app.comun.almacen import AlmacenPrivado

SUBCARPETA = "corpus"


class AlmacenArchivos(AlmacenPrivado):
    def __init__(self, base: Path) -> None:
        super().__init__(base, SUBCARPETA, ".pdf")
