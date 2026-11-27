"""Corpus de guías (T22): lectura, segmentación por apartado y exclusión de la rúbrica."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.corpus.guias import (
    RubricaNoIndexable,
    archivos,
    exigir_no_rubrica,
    huellas_bloqueadas,
    leer_guia,
    segmentar,
)

PROVISIONALES = Path(__file__).parents[2] / "guias" / "provisionales"
GUIA = """---
titulo: Guía ficticia
tipo: guia_investigacion
procedencia: Prueba
licencia: Uso interno
---

## Primer apartado

Párrafo uno del primer apartado.

Párrafo dos del primer apartado.

## Segundo apartado

Texto del segundo apartado.
"""


def _guia(tmp_path: Path, nombre: str = "guia.md", texto: str = GUIA) -> Path:
    ruta = tmp_path / nombre
    ruta.write_bytes(texto.encode("utf-8"))
    return ruta


def test_lee_la_cabecera_y_los_apartados(tmp_path: Path) -> None:
    guia = leer_guia(_guia(tmp_path))
    assert (guia.titulo, guia.tipo, guia.procedencia, guia.licencia) == (
        "Guía ficticia",
        "guia_investigacion",
        "Prueba",
        "Uso interno",
    )
    assert [a.titulo for a in guia.apartados] == ["Primer apartado", "Segundo apartado"]


def test_segmenta_por_apartado_y_divide_los_largos(tmp_path: Path) -> None:
    guia = leer_guia(_guia(tmp_path))
    assert [apartado for apartado, _, _ in segmentar(guia)] == [
        "Primer apartado",
        "Segundo apartado",
    ]
    partidos = segmentar(guia, maximo=8)
    assert [apartado for apartado, _, _ in partidos] == [
        "Primer apartado",
        "Primer apartado",
        "Segundo apartado",
    ]


@pytest.mark.parametrize(
    ("nombre", "texto"),
    [
        ("rubrica-del-programa.md", GUIA),
        (
            "guia.md",
            GUIA.replace("titulo: Guía ficticia", "titulo: Rúbrica de evaluación del artículo"),
        ),
    ],
)
def test_la_rubrica_se_rechaza_por_nombre(tmp_path: Path, nombre: str, texto: str) -> None:
    with pytest.raises(RubricaNoIndexable):
        exigir_no_rubrica(leer_guia(_guia(tmp_path, nombre, texto)), frozenset())


def test_la_rubrica_se_rechaza_por_huella_registrada(tmp_path: Path) -> None:
    ruta = _guia(tmp_path, "criterios.md")
    huella = hashlib.sha256(ruta.read_bytes()).hexdigest()
    registro = tmp_path / "bloqueadas.txt"
    registro.write_text(f"# comentario\n{huella}  # rúbrica 2026\n", encoding="utf-8")
    with pytest.raises(RubricaNoIndexable):
        exigir_no_rubrica(leer_guia(ruta), huellas_bloqueadas(registro))


def test_las_guias_provisionales_se_leen_y_ninguna_es_la_rubrica() -> None:
    guias = [leer_guia(ruta) for ruta in archivos(PROVISIONALES)]
    assert len(guias) == 6 and all(g.apartados for g in guias)
    for guia in guias:
        exigir_no_rubrica(guia, huellas_bloqueadas())
        assert "provisional" in guia.procedencia
