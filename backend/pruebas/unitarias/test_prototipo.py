"""Ajustes del prototipo navegable: títulos dudosos del corpus y entidades de doi.org."""

from __future__ import annotations

import pytest

from app.bibliografia.csl import quitar_numero
from app.corpus.titulos import dudoso


@pytest.mark.parametrize(
    ("titulo", "esperado"),
    [
        (None, True),
        ("", True),
        ("EDUCARE COMUNICARE ET", True),
        ("PREDICTORES DEL DESEMPEÑO ACADÉMICO MEDIANTE EL USO DEL CHATGPT", True),
        ("Corto", True),
        ("Percepción de estudiantes universitarios sobre el uso de ChatGPT", False),
    ],
)
def test_titulo_dudoso(titulo: str | None, esperado: bool) -> None:
    assert dudoso(titulo) is esperado


def test_la_cita_de_doi_org_sin_entidades_html() -> None:
    texto = "[1] A. Díaz, «Título», European Public &amp; Social Innovation Review, 2025."
    assert (
        quitar_numero(texto)
        == "A. Díaz, «Título», European Public & Social Innovation Review, 2025."
    )
