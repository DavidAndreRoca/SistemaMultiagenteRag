"""Armado de lotes sin relleno (decisión T08-01, determinismo).

Un texto procesado en un lote con relleno da un vector que difiere en torno a 1e-7 del
que da procesado solo, porque el relleno cambia la forma de las operaciones. Si cada
lote solo agrupa textos con la misma cantidad de tokens, no hay relleno y el resultado
de cada texto es idéntico bit a bit sin importar con qué otros textos llegó (medido en
T08). En CPU, agrupar casi no acelera, así que no se pierde rendimiento.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence


def lotes_sin_relleno(longitudes: Sequence[int], tamano: int) -> list[list[int]]:
    """Índices agrupados por longitud igual, en lotes de hasta ``tamano``.

    Cubre todos los índices una sola vez; el orden es por longitud y, a igual longitud,
    por posición.
    """
    if tamano < 1:
        raise ValueError("el tamaño de lote debe ser al menos 1")
    grupos: dict[int, list[int]] = defaultdict(list)
    for indice, longitud in enumerate(longitudes):
        grupos[longitud].append(indice)
    lotes: list[list[int]] = []
    for longitud in sorted(grupos):
        indices = grupos[longitud]
        lotes.extend(indices[i : i + tamano] for i in range(0, len(indices), tamano))
    return lotes
