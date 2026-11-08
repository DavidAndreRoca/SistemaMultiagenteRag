"""Catálogo de modelos fijados: revisiones exactas y verificación de archivos."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from servicio.catalogo import (
    BGE_M3,
    BGE_RERANKER_V2_M3,
    CATALOGO,
    Archivo,
    ModeloFijado,
    TipoModelo,
    problemas,
)


@pytest.mark.parametrize("modelo", CATALOGO, ids=lambda m: m.repositorio)
def test_revision_fijada_es_un_commit_completo(modelo: ModeloFijado) -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", modelo.revision)
    pesos = [a for a in modelo.archivos if a.ruta.endswith((".bin", ".safetensors"))]
    assert len(pesos) == 1 and pesos[0].sha256 and pesos[0].tamano > 2_000_000_000


def test_catalogo_tiene_un_modelo_de_cada_tipo() -> None:
    assert [m.tipo for m in CATALOGO] == [TipoModelo.EMBEDDINGS, TipoModelo.REORDENADOR]
    assert (BGE_M3.licencia, BGE_RERANKER_V2_M3.licencia) == ("MIT", "Apache-2.0")


def test_problemas_detecta_faltantes_tamano_y_huella(tmp_path: Path) -> None:
    contenido = b"pesos ficticios"
    modelo = ModeloFijado(
        TipoModelo.EMBEDDINGS,
        "org/modelo",
        "a" * 40,
        "MIT",
        (
            Archivo("pesos.bin", len(contenido), hashlib.sha256(contenido).hexdigest()),
            Archivo("config.json", 2),
        ),
    )
    directorio = modelo.directorio(tmp_path)
    assert directorio == tmp_path / "org--modelo" / ("a" * 40)
    assert len(problemas(modelo, tmp_path)) == 2
    directorio.mkdir(parents=True)
    (directorio / "pesos.bin").write_bytes(contenido)
    (directorio / "config.json").write_text("{}")
    assert problemas(modelo, tmp_path, con_huella=True) == []
    (directorio / "pesos.bin").write_bytes(b"pesos alterados")  # mismo tamaño, otra huella
    assert problemas(modelo, tmp_path) == []
    assert problemas(modelo, tmp_path, con_huella=True) == [
        "org/modelo: huella distinta en pesos.bin"
    ]
    (directorio / "config.json").write_text("{ }")
    assert "tamaño distinto" in problemas(modelo, tmp_path)[0]
