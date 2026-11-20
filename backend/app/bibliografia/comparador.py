"""Comparación de metadatos para confirmar una referencia sin DOI (T14-01, apartado 7).

18.9 de la especificación (y CP-15): se confirma si coinciden el título (similitud
normalizada alta), al menos un apellido de autor y el año. Tolerancias:

* Título: similitud de 0,88 o más sobre el texto normalizado (minúsculas, sin tildes ni
  puntuación, espacios simples); también sin el subtítulo, y vale la mayor.
* Autor: al menos un apellido en común; con apellidos compuestos basta una palabra de 3
  letras o más.
* Año: igual o con un año de diferencia (en línea frente a impreso).

Sin título, autores o año en la referencia no se confirma: falta lo que se compara.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict

from app.bibliografia.modelos import Autor, MetadatosBibliograficos
from app.bibliografia.normalizacion import normalizar

UMBRAL_TITULO = 0.88
TOLERANCIA_ANIOS = 1
MIN_LETRAS_PALABRA_APELLIDO = 3


def _sin_subtitulo(titulo: str) -> str:
    return re.split(r"[:.?]\s", titulo, maxsplit=1)[0]


def similitud_titulo(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    variantes_a = {normalizar(a), normalizar(_sin_subtitulo(a))}
    variantes_b = {normalizar(b), normalizar(_sin_subtitulo(b))}
    return max(
        difflib.SequenceMatcher(None, x, y).ratio()
        for x in variantes_a
        for y in variantes_b
        if x and y
    )


def _palabras_de_apellido(apellido: str) -> set[str]:
    normal = normalizar(apellido)
    palabras = {p for p in normal.split() if len(p) >= MIN_LETRAS_PALABRA_APELLIDO}
    return palabras | ({normal} if normal else set())


def algun_autor_coincide(referencia: Iterable[str], candidato: Sequence[Autor]) -> bool:
    buscados: set[str] = set()
    for apellido in referencia:
        buscados |= _palabras_de_apellido(apellido)
    for autor in candidato:
        propio = autor.apellidos_para_comparar()
        if propio and buscados & _palabras_de_apellido(propio):
            return True
        # OpenAlex da el nombre completo: un apellido compuesto puede no ser la última palabra.
        if autor.nombre_completo and buscados & set(normalizar(autor.nombre_completo).split()):
            return True
    return False


class Coincidencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    confirmada: bool
    similitud_titulo: float
    autor_coincide: bool
    anio_coincide: bool
    motivo: str | None = None  # datos_insuficientes, titulo, autor o anio


def comparar(
    titulo: str | None,
    apellidos: Sequence[str],
    anio: int | None,
    candidato: MetadatosBibliograficos,
) -> Coincidencia:
    """¿El candidato es la obra de la referencia (título, apellidos y año)?"""
    similitud = similitud_titulo(titulo, candidato.titulo)
    autor = algun_autor_coincide(apellidos, candidato.autores)
    anio_ok = (
        anio is not None
        and candidato.anio is not None
        and abs(anio - candidato.anio) <= TOLERANCIA_ANIOS
    )
    if not titulo or not apellidos or anio is None:
        motivo: str | None = "datos_insuficientes"
    elif similitud < UMBRAL_TITULO:
        motivo = "titulo"
    elif not autor:
        motivo = "autor"
    elif not anio_ok:
        motivo = "anio"
    else:
        motivo = None
    return Coincidencia(
        confirmada=motivo is None,
        similitud_titulo=round(similitud, 4),
        autor_coincide=autor,
        anio_coincide=anio_ok,
        motivo=motivo,
    )


def mejor_coincidencia(
    titulo: str | None,
    apellidos: Sequence[str],
    anio: int | None,
    candidatos: Sequence[MetadatosBibliograficos],
) -> tuple[MetadatosBibliograficos, Coincidencia] | None:
    """El candidato confirmado con mayor similitud de título, si hay alguno."""
    confirmados = [
        (c, coincidencia)
        for c in candidatos
        if (coincidencia := comparar(titulo, apellidos, anio, c)).confirmada
    ]
    if not confirmados:
        return None
    return max(confirmados, key=lambda par: par[1].similitud_titulo)
