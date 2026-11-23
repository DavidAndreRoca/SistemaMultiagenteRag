"""Dobles de la recuperación (T16): reordenador determinista por coincidencia de palabras.

``ReordenadorFicticio`` puntúa cada texto con la fracción de palabras de la consulta que
contiene (sin palabras vacías), de 0 a 1: los textos del mismo asunto quedan arriba y los
de otro asunto, cerca de 0, como haría un reordenador real. Cuenta sus llamadas.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence

from app.inferencia.interfaces import IdentidadModelo, Puntajes
from app.repositorios.recuperacion import PALABRAS_VACIAS

IDENTIDAD = IdentidadModelo(modelo="ficticio/reordenador-palabras", revision="rev-1")


def _palabras(texto: str) -> set[str]:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    )
    limpio = "".join(c if c.isalnum() else " " for c in sin_tildes)
    return {p for p in limpio.split() if len(p) > 2 and p not in PALABRAS_VACIAS}


class ReordenadorFicticio:
    def __init__(self) -> None:
        self.llamadas: list[int] = []  # cuántos textos recibió en cada llamada

    async def reordenar(self, consulta: str, textos: Sequence[str]) -> Puntajes:
        self.llamadas.append(len(textos))
        buscadas = _palabras(consulta) or {""}
        return Puntajes(
            identidad=IDENTIDAD,
            puntajes=[len(buscadas & _palabras(t)) / len(buscadas) for t in textos],
        )
