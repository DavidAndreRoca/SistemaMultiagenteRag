"""Crea el subconjunto de desarrollo del corpus: 3 PDF por tema para las pruebas diarias.

El corpus provisional completo (``datos/corpus-provisional/``, unas 2 500 páginas) se
ingiere solo en ejecuciones programadas (``scripts/ingesta-programada.ps1``). Para el día
a día basta con un subconjunto pequeño, que se ingiere en minutos.

Regla de selección, fija para que el subconjunto sea reproducible: por tema, los PDF de
10 a 16 páginas que la ingesta completa indexó sin problemas (según
``datos/corpus-provisional/ingesta-*.log`` si existe), de menos a más páginas y, a igual
número, por nombre. Se copian a ``datos/corpus-desarrollo/<tema>/`` y la lista queda en
``datos/corpus-desarrollo/seleccion.json``.

Uso, desde la raíz del repositorio::

    python scripts/crear_subconjunto_desarrollo.py [--por-tema 3]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "datos" / "corpus-provisional"
DESTINO = RAIZ / "datos" / "corpus-desarrollo"
PAGINAS = range(10, 17)


def no_indexados() -> set[str]:
    """Archivos que una ingesta completa anterior no indexó (excluidos, incompletos...)."""
    vistos: set[str] = set()
    for registro in ORIGEN.glob("ingesta-*.log"):
        for linea in registro.read_text(encoding="utf-8", errors="replace").splitlines():
            coincidencia = re.search(r"\b(excluido|incompleto|duplicado|error)\s+(\S+\.pdf)", linea)
            if coincidencia:
                vistos.add(coincidencia.group(2))
    return vistos


def paginas(pdf: Path) -> int:
    try:
        return len(PdfReader(pdf).pages)
    except (PyPdfError, OSError, ValueError):  # un PDF ilegible no entra al subconjunto
        return -1


def principal() -> int:
    lector = argparse.ArgumentParser(description="Crea el subconjunto de desarrollo.")
    lector.add_argument("--por-tema", type=int, default=3)
    args = lector.parse_args()
    descartados = no_indexados()
    seleccion: dict[str, list[dict[str, object]]] = {}
    for tema in sorted(p for p in ORIGEN.iterdir() if p.is_dir()):
        candidatos = sorted(
            (n, pdf.name)
            for pdf in tema.glob("*.pdf")
            if pdf.name not in descartados and (n := paginas(pdf)) in PAGINAS
        )[: args.por_tema]
        destino = DESTINO / tema.name
        if destino.exists():
            shutil.rmtree(destino)
        destino.mkdir(parents=True)
        for _, nombre in candidatos:
            shutil.copy2(tema / nombre, destino / nombre)
        seleccion[tema.name] = [{"archivo": nombre, "paginas": n} for n, nombre in candidatos]
        print(f"{tema.name}: " + ", ".join(f"{nombre} ({n} p.)" for n, nombre in candidatos))
    (DESTINO / "seleccion.json").write_text(
        json.dumps(seleccion, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
