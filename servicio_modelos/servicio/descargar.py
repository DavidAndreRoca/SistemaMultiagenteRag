"""Descarga los modelos fijados al volumen persistente y verifica tamaño y huella.

Uso: ``python -m servicio.descargar`` (necesita red; el servicio en sí no la usa).
Es idempotente: lo que ya está verificado no se vuelve a descargar.
"""

from __future__ import annotations

import sys
from pathlib import Path

from servicio.ajustes import cargar_ajustes
from servicio.catalogo import CATALOGO, ModeloFijado, problemas


def descargar_modelo(modelo: ModeloFijado, base: Path) -> None:
    from huggingface_hub import hf_hub_download

    destino = modelo.directorio(base)
    destino.mkdir(parents=True, exist_ok=True)
    for archivo in modelo.archivos:
        ruta = destino / archivo.ruta
        if ruta.is_file() and ruta.stat().st_size == archivo.tamano:
            continue
        print(f"Descargando {modelo.repositorio}@{modelo.revision[:10]}: {archivo.ruta}")
        hf_hub_download(
            repo_id=modelo.repositorio,
            filename=archivo.ruta,
            revision=modelo.revision,
            local_dir=destino,
        )


def main() -> int:
    base = cargar_ajustes().directorio_modelos
    for modelo in CATALOGO:
        descargar_modelo(modelo, base)
    errores = [p for modelo in CATALOGO for p in problemas(modelo, base, con_huella=True)]
    if errores:
        print("ERROR: " + "; ".join(errores), file=sys.stderr)
        return 1
    for modelo in CATALOGO:
        print(f"Verificado {modelo.repositorio}@{modelo.revision} en {modelo.directorio(base)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
