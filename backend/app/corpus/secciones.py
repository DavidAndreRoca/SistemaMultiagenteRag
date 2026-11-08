"""Normalización de secciones a IMRaD a partir de los títulos (T09, actividades 4 y 6).

Reglas (decisión T09-01, apartado 4):

* Un título reconocido abre su sección: resumen, introducción, métodos, resultados,
  discusión, conclusiones, otra, referencias o agradecimientos. Se reconoce en español
  y en inglés, sin numeración, tildes ni mayúsculas, por su comienzo.
* Un título no reconocido dentro del cuerpo (introducción a conclusiones) es una
  subsección y hereda la sección ("2.1. Participantes" sigue en métodos). Fuera del
  cuerpo abre una sección "otra". Un "Summary" dentro del cuerpo tampoco es el resumen.
* Los títulos que el extractor dejó dentro de un párrafo ("Resumen La ansiedad...",
  "...la universidad. 2.2. Instrumentos La escala...") los separa antes la limpieza.
* Lo anterior a la primera sección reconocida (título, autores, afiliaciones) son
  metadatos, que da GROBID, y no se segmenta.
* Las referencias y los agradecimientos se excluyen (18.3).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from app.bd.enumeraciones import SeccionNormalizada
from app.corpus.bloques import TIPOS_DE_TEXTO, Bloque, TipoBloque


class SeccionExcluida(StrEnum):
    REFERENCIAS = "referencias"
    AGRADECIMIENTOS = "agradecimientos"


ClaseSeccion = SeccionNormalizada | SeccionExcluida

S = SeccionNormalizada
CUERPO_IMRAD = frozenset({S.INTRODUCCION, S.METODOS, S.RESULTADOS, S.DISCUSION, S.CONCLUSIONES})
MAX_PALABRAS_TITULO = 12

# Comienzos reconocidos, ya sin tildes y en minúsculas. El orden importa: se prueba de
# arriba abajo ("analisis y discusion" antes que "analisis de datos").
COMIENZOS: tuple[tuple[ClaseSeccion, tuple[str, ...]], ...] = (
    (
        SeccionExcluida.REFERENCIAS,
        (
            "referencias",
            "referencia bibliografica",
            "bibliografia",
            "references",
            "reference list",
            "bibliography",
            "literatura citada",
            "literature cited",
            "works cited",
            "fuentes consultadas",
        ),
    ),
    (
        SeccionExcluida.AGRADECIMIENTOS,
        ("agradecimiento", "acknowledgment", "acknowledgement", "reconocimientos"),
    ),
    (
        S.OTRA,
        (
            "anexo",
            "apendice",
            "appendix",
            "appendices",
            "material suplementario",
            "material complementario",
            "supplementary",
            "conflicto de interes",
            "conflict of interest",
            "conflicts of interest",
            "declaracion",
            "declaration",
            "financiamiento",
            "financiacion",
            "fuentes de financiamiento",
            "funding",
            "contribucion de",
            "contribuciones de",
            "author contribution",
            "authors contribution",
            "disponibilidad de",
            "data availability",
            "abreviaturas",
            "abbreviations",
            "palabras clave",
            "keywords",
            "notas",
            "notes",
        ),
    ),
    (S.RESUMEN, ("resumen", "abstract", "summary", "resumo", "sumario")),
    (
        S.INTRODUCCION,
        (
            "introduccion",
            "introduction",
            "antecedentes",
            "background",
            "marco teorico",
            "marco conceptual",
            "marco referencial",
            "revision de la literatura",
            "revision de literatura",
            "estado del arte",
            "literature review",
            "review of the literature",
            "theoretical framework",
            "theoretical background",
            "related work",
            "planteamiento del problema",
            "problem statement",
        ),
    ),
    (
        S.DISCUSION,
        (
            "discusion",
            "discussion",
            "analisis y discusion",
            "limitaciones",
            "limitations",
            "implicaciones",
            "implications",
        ),
    ),
    (
        S.METODOS,
        (
            "metodo",
            "metodologia",
            "materiales y metodos",
            "material y metodos",
            "materials and methods",
            "method",
            "methodology",
            "diseno",
            "design",
            "participantes",
            "participants",
            "poblacion",
            "muestra",
            "sample",
            "instrumentos",
            "instruments",
            "measures",
            "procedimiento",
            "procedure",
            "analisis de datos",
            "analisis estadistico",
            "data analysis",
            "statistical analysis",
        ),
    ),
    (S.RESULTADOS, ("resultados", "results", "hallazgos", "findings")),
    (
        S.CONCLUSIONES,
        (
            "conclusion",
            "consideraciones finales",
            "concluding remarks",
            "reflexiones finales",
            "recomendaciones",
            "recommendations",
        ),
    ),
)

NUMERACION = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[IVXLCDM]+[.)]|[A-Z][.)])\s+")


def clave_de_titulo(titulo: str) -> str:
    """Título comparable: sin numeración, tildes, signos ni mayúsculas."""
    sin_numero = NUMERACION.sub("", titulo.strip())
    descompuesto = unicodedata.normalize("NFKD", sin_numero)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    solo_letras = re.sub(r"[^a-z\s]", " ", sin_tildes.lower())
    return re.sub(r"\s+", " ", solo_letras).strip()


def _coincide(palabras: Sequence[str], partes: Sequence[str]) -> bool:
    # Cada palabra coincide completa o con un plural o sufijo corto ("metodos",
    # "conclusiones", "acknowledgments", "intereses").
    return len(palabras) >= len(partes) and all(
        palabra.startswith(parte) and len(palabra) - len(parte) <= 3
        for palabra, parte in zip(palabras, partes, strict=False)
    )


def _clase_exacta(palabras: Sequence[str]) -> ClaseSeccion | None:
    for clase, comienzos in COMIENZOS:
        for comienzo in comienzos:
            partes = comienzo.split()
            if len(palabras) == len(partes) and _coincide(palabras, partes):
                return clase
    return None


def clasificar_titulo(titulo: str) -> ClaseSeccion | None:
    """Sección que abre un título, o ``None`` si no se reconoce."""
    clave = clave_de_titulo(titulo)
    if not clave or len(clave.split()) > MAX_PALABRAS_TITULO:
        return None
    palabras = clave.split()
    for clase, comienzos in COMIENZOS:
        for comienzo in comienzos:
            if _coincide(palabras, comienzo.split()):
                return clase
    return None


def titulo_completo(frase: str) -> ClaseSeccion | None:
    """Como ``clasificar_titulo``, pero la frase debe ser el título entero, sin palabras de
    más: "Análisis de datos" o "Resultados y discusión" sí; "Results showed a gain" no.
    Se usa para reconocer títulos dentro de un párrafo, donde el riesgo de confundir una
    oración con un título es mayor."""
    palabras = clave_de_titulo(frase).split()
    if not palabras:
        return None
    if (clase := _clase_exacta(palabras)) is not None:
        return clase
    for conector in ("y", "and"):
        if conector in palabras:
            corte = palabras.index(conector)
            primera, segunda = palabras[:corte], palabras[corte + 1 :]
            if primera and segunda and _clase_exacta(segunda) is not None:
                return _clase_exacta(primera)
    return None


@dataclass(frozen=True)
class Parrafo:
    texto: str
    pagina_inicio: int
    pagina_fin: int


@dataclass
class SeccionTexto:
    clase: SeccionNormalizada
    titulo: str | None
    parrafos: list[Parrafo] = field(default_factory=list)


@dataclass
class _Grupo:
    clase: ClaseSeccion | None
    titulo: str | None
    reconocido: bool
    parrafos: list[Parrafo] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentoSeccionado:
    secciones: list[SeccionTexto]
    detectadas: list[SeccionNormalizada]  # en orden, sin repetir y sin "otra"

    @property
    def tiene_imrad(self) -> bool:
        return any(s in CUERPO_IMRAD for s in self.detectadas)


def seccionar(bloques: Sequence[Bloque]) -> DocumentoSeccionado:
    """Agrupa los bloques limpios por sección y excluye referencias y agradecimientos."""
    grupos: list[_Grupo] = []
    actual: ClaseSeccion | None = None
    hubo_reconocida = False

    for bloque in bloques:
        if bloque.tipo is TipoBloque.TITULO_SECCION:
            clase = clasificar_titulo(bloque.texto)
            if clase is S.RESUMEN and actual in CUERPO_IMRAD:
                clase = None  # "Summary of findings" dentro del cuerpo no es el resumen
            reconocido = clase is not None
            if clase is None:
                clase = actual if actual in CUERPO_IMRAD else S.OTRA
            hubo_reconocida |= reconocido
            grupos.append(_Grupo(clase, bloque.texto, reconocido))
            actual = clase
            continue
        if bloque.tipo not in TIPOS_DE_TEXTO:
            continue
        if not grupos:
            grupos.append(_Grupo(None, None, False))
        grupos[-1].parrafos.append(Parrafo(bloque.texto, bloque.pagina_inicio, bloque.pagina_fin))

    if hubo_reconocida:
        primera = next(i for i, g in enumerate(grupos) if g.reconocido)
        grupos = grupos[primera:]

    secciones: list[SeccionTexto] = []
    for grupo in grupos:
        if isinstance(grupo.clase, SeccionExcluida) or not grupo.parrafos:
            continue
        clase = grupo.clase if isinstance(grupo.clase, SeccionNormalizada) else S.OTRA
        secciones.append(SeccionTexto(clase, grupo.titulo, grupo.parrafos))

    detectadas: list[SeccionNormalizada] = []
    for seccion in secciones:
        if seccion.clase is not S.OTRA and seccion.clase not in detectadas:
            detectadas.append(seccion.clase)
    return DocumentoSeccionado(secciones, detectadas)
