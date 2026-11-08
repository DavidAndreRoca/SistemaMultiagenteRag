"""Lotes sin relleno: cada lote agrupa solo textos de igual longitud."""

from __future__ import annotations

import pytest

from servicio.lotes import lotes_sin_relleno


def test_agrupa_por_longitud_igual_y_respeta_el_tamano() -> None:
    longitudes = [5, 3, 5, 5, 3, 9]
    assert lotes_sin_relleno(longitudes, 2) == [[1, 4], [0, 2], [3], [5]]


@pytest.mark.parametrize("tamano", [1, 2, 16])
def test_cubre_cada_indice_una_vez_y_sin_mezclar_longitudes(tamano: int) -> None:
    longitudes = [(i * 7) % 5 for i in range(23)]
    lotes = lotes_sin_relleno(longitudes, tamano)
    assert sorted(i for lote in lotes for i in lote) == list(range(23))
    for lote in lotes:
        assert len(lote) <= tamano
        assert len({longitudes[i] for i in lote}) == 1


def test_tamano_invalido() -> None:
    with pytest.raises(ValueError):
        lotes_sin_relleno([1], 0)
