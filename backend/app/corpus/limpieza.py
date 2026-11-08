"""Limpieza del texto extraído (T09, actividad 3; Fase 1, 18.3).

Funciones puras sobre bloques:

* Normalización Unicode (NFC), ligaduras, espacios especiales y caracteres invisibles.
* Encabezados y pies de página: los que el extractor marca y los textos que se repiten
  en varias páginas (con los números reemplazados), aunque el extractor los haya
  etiquetado como otra cosa o pegado dentro de un párrafo.
* Números de página sueltos y bloques sin letras (celdas numéricas de tablas).
* Títulos de sección que el extractor dejó dentro de un párrafo.
* Palabras cortadas con guion al final de línea y párrafos partidos por un salto de
  página o de columna.

El contenido es dato (RN-23): aquí solo se transforma texto, nunca se interpreta.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence

from app.corpus.bloques import TIPOS_DE_TEXTO, TIPOS_MOBILIARIO, Bloque, TipoBloque
from app.corpus.secciones import titulo_completo

# Un texto que se repite en al menos esta fracción de las páginas (y en 3 o más) es
# mobiliario de página aunque el extractor no lo haya marcado.
FRACCION_REPETICION = 0.5
MIN_PAGINAS_REPETICION = 3
LARGO_MAXIMO_MOBILIARIO = 160
LARGO_MINIMO_INCRUSTADO = 12  # "Página 2 de 4" sí; "12" o "Notas" no

# Títulos dentro de un párrafo
SE_BUSCAN_TITULOS = frozenset({TipoBloque.PARRAFO, TipoBloque.ELEMENTO_LISTA})
MAX_PALABRAS_TITULO_EN_LINEA = 4
FIN_PREVIO = re.compile(r"[.!?:;…»”\")\]]$")
NUMERO_DE_TITULO = re.compile(r"(?:\d+(?:\.\d+)*\.?|[IVX]+\.)")
ABRE_ORACION = '¿¡(«“"['
PALABRAS_FUNCIONALES = frozenset(
    {
        "de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "en", "a", "al", "con",
        "por", "para", "the", "of", "and", "or", "in", "on", "for", "to", "an", "with",
    }
)  # fmt: skip

LIGADURAS = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}
GUIONES = {"\u2010": "-", "\u2011": "-"}
INVISIBLES = re.compile("[\u00ad\u200b\u200c\u200d\u2060\ufeff]")
ESPACIOS = re.compile("[\\s\u00a0\u2000-\u200a\u202f\u205f\u3000]+")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

NUMERO_DE_PAGINA = re.compile(
    r"^(?:(?:p[áa]g(?:ina)?|page|p)\.?\s*)?(?:\d{1,4}|[ivxlcdm]{1,7})"
    r"(?:\s*(?:de|of|/)\s*\d{1,4})?$",
    re.IGNORECASE,
)
# "investi- gación" (corte de línea que el extractor dejó con un espacio): se une si la
# segunda parte empieza en minúscula y no es una conjunción ("pre- y postest").
CORTE_CON_GUION = re.compile(r"(?<=[^\W\d_]{2})-\s+(?=([^\W\d_]+))")
CONJUNCIONES = frozenset({"y", "e", "o", "u", "ni", "and", "or", "nor", "to"})
FIN_DE_ORACION = re.compile(r"[.!?:;…)\]\"”»]$")
# Tablas y fórmulas no se extraen como texto en T09; las entradas de bibliografía nunca.
DESCARTADOS = frozenset(
    {TipoBloque.TABLA, TipoBloque.FORMULA, TipoBloque.REFERENCIA, TipoBloque.OTRO}
)


def normalizar_texto(texto: str) -> str:
    """NFC, ligaduras, guiones Unicode, espacios y caracteres de control o invisibles."""
    texto = unicodedata.normalize("NFC", texto)
    for origen, destino in (LIGADURAS | GUIONES).items():
        texto = texto.replace(origen, destino)
    texto = INVISIBLES.sub("", texto)
    texto = CONTROL.sub(" ", texto)
    return ESPACIOS.sub(" ", texto).strip()


def unir_cortes_de_linea(texto: str) -> str:
    def reemplazar(coincidencia: re.Match[str]) -> str:
        siguiente = coincidencia.group(1)
        if siguiente[0].islower() and siguiente.lower() not in CONJUNCIONES:
            return ""
        return coincidencia.group(0)

    return CORTE_CON_GUION.sub(reemplazar, texto)


def es_numero_de_pagina(texto: str) -> bool:
    return NUMERO_DE_PAGINA.fullmatch(texto.strip()) is not None


def firma(texto: str) -> str:
    """Forma comparable de un texto repetido: minúsculas, sin números ni espacios extra."""
    return ESPACIOS.sub(" ", re.sub(r"\d+", "#", texto.lower())).strip()


def _mobiliario(
    bloques: Sequence[Bloque], num_paginas: int
) -> tuple[set[str], list[re.Pattern[str]]]:
    """Firmas del mobiliario de página y patrones para quitarlo de dentro de un párrafo.

    El extractor a veces pega el encabezado de la página siguiente al final de un párrafo
    que continúa en ella; el patrón lo encuentra con cualquier número de página.
    """
    marcadas: set[str] = set()
    ejemplo: dict[str, str] = {}
    paginas_por_firma: dict[str, set[int]] = defaultdict(set)
    for bloque in bloques:
        if not bloque.texto:
            continue
        clave = firma(bloque.texto)
        ejemplo.setdefault(clave, bloque.texto)
        if bloque.tipo in TIPOS_MOBILIARIO:
            marcadas.add(clave)
        if len(bloque.texto) <= LARGO_MAXIMO_MOBILIARIO:
            paginas_por_firma[clave].add(bloque.pagina_inicio)
    minimo = max(MIN_PAGINAS_REPETICION, math.ceil(num_paginas * FRACCION_REPETICION))
    firmas = marcadas | {f for f, paginas in paginas_por_firma.items() if len(paginas) >= minimo}
    patrones = [
        re.compile(r"\s+".join(re.sub(r"\d+", r"\\d+", re.escape(p)) for p in ejemplo[f].split()))
        for f in sorted(firmas)
        if len(ejemplo[f]) >= LARGO_MINIMO_INCRUSTADO and len(ejemplo[f].split()) >= 2
    ]
    return firmas, patrones


def _quitar_incrustado(texto: str, patrones: Sequence[re.Pattern[str]]) -> str:
    for patron in patrones:
        texto = patron.sub(" ", texto)
    return ESPACIOS.sub(" ", texto).strip()


def _titulo_desde(palabras: Sequence[re.Match[str]], inicio: int) -> int | None:
    """Si en ``inicio`` empieza un título de sección reconocible, devuelve dónde termina.

    Hasta 4 palabras: la primera con mayúscula, las demás en minúscula, sin terminar en
    una palabra funcional ("Resultados de la" no lo es) y seguidas de una mayúscula o del
    final del bloque. Se prueba de la más larga a la más corta.
    """
    for largo in range(min(MAX_PALABRAS_TITULO_EN_LINEA, len(palabras) - inicio), 0, -1):
        frase = [p.group() for p in palabras[inicio : inicio + largo]]
        ultima = frase[-1].rstrip(":.")
        siguiente = palabras[inicio + largo].group() if inicio + largo < len(palabras) else ""
        if not frase[0][0].isupper() or not ultima or ultima.lower() in PALABRAS_FUNCIONALES:
            continue
        if any(not p[0].islower() for p in frase[1:]):
            continue
        if any(re.search(r"[^\w-]", p) for p in [*frase[:-1], ultima]):
            continue
        if siguiente and not (siguiente[0].isupper() or siguiente[0] in ABRE_ORACION):
            continue
        if titulo_completo(" ".join([*frase[:-1], ultima])) is not None:
            return inicio + largo
    return None


def separar_titulos_en_linea(bloque: Bloque) -> list[Bloque]:
    """Separa los títulos de sección que el extractor dejó dentro de un párrafo.

    Casos reales: "Resumen La ansiedad..." y una página entera en un solo bloque con
    "...la universidad. 2.2. Instrumentos La ansiedad...". Un título solo se busca al
    comienzo del bloque o después de un fin de oración, con numeración opcional.
    """
    texto = bloque.texto
    palabras = list(re.finditer(r"\S+", texto))
    piezas: list[Bloque] = []
    desde = 0  # carácter donde empieza el texto pendiente
    i = 0
    while i < len(palabras):
        if i == 0 or FIN_PREVIO.search(palabras[i - 1].group()):
            j = i + 1 if NUMERO_DE_TITULO.fullmatch(palabras[i].group()) else i
            fin = _titulo_desde(palabras, j) if j < len(palabras) else None
            if fin is not None:
                antes = texto[desde : palabras[i].start()].strip()
                if antes:
                    piezas.append(bloque.model_copy(update={"texto": antes}))
                titulo = texto[palabras[i].start() : palabras[fin - 1].end()].rstrip(":")
                piezas.append(
                    bloque.model_copy(update={"texto": titulo, "tipo": TipoBloque.TITULO_SECCION})
                )
                desde = palabras[fin - 1].end()
                i = fin
                continue
        i += 1
    resto = texto[desde:].strip()
    if resto:
        piezas.append(bloque.model_copy(update={"texto": resto}))
    return piezas


def _empieza_en_minuscula(texto: str) -> bool:
    primera = next((c for c in texto if c.isalpha()), "")
    return primera.islower()


def _continua(anterior: Bloque, siguiente: Bloque) -> bool:
    """El siguiente bloque continúa la oración del anterior (salto de página o columna)."""
    if anterior.tipo not in TIPOS_DE_TEXTO or siguiente.tipo not in TIPOS_DE_TEXTO:
        return False
    if anterior.tipo is not siguiente.tipo:
        return False
    return not FIN_DE_ORACION.search(anterior.texto) and _empieza_en_minuscula(siguiente.texto)


def _unir(anterior: Bloque, siguiente: Bloque) -> Bloque:
    if re.search(r"[^\W\d_]-$", anterior.texto):
        texto = anterior.texto[:-1] + siguiente.texto
    else:
        texto = f"{anterior.texto} {siguiente.texto}"
    return anterior.model_copy(
        update={
            "texto": texto,
            "pagina_inicio": min(anterior.pagina_inicio, siguiente.pagina_inicio),
            "pagina_fin": max(anterior.pagina_fin, siguiente.pagina_fin),
        }
    )


def limpiar(bloques: Sequence[Bloque], num_paginas: int) -> list[Bloque]:
    """Devuelve los bloques de contenido limpios, en orden de lectura.

    Quita el mobiliario de página, las tablas, las fórmulas y los bloques vacíos o sin
    letras. Un "título" que empieza en minúscula es la cola de un párrafo que el
    extractor confundió con un título, y se trata como texto.
    """
    normalizados = [b.model_copy(update={"texto": normalizar_texto(b.texto)}) for b in bloques]
    firmas, incrustados = _mobiliario(normalizados, num_paginas)

    contenido: list[Bloque] = []
    for bloque in normalizados:
        if bloque.tipo in TIPOS_MOBILIARIO or bloque.tipo in DESCARTADOS:
            continue
        if firma(bloque.texto) in firmas or es_numero_de_pagina(bloque.texto):
            continue
        if bloque.tipo in TIPOS_DE_TEXTO:
            bloque = bloque.model_copy(
                update={"texto": _quitar_incrustado(bloque.texto, incrustados)}
            )
        if not any(c.isalpha() for c in bloque.texto):
            continue
        if bloque.tipo is TipoBloque.TITULO_SECCION and _empieza_en_minuscula(bloque.texto):
            bloque = bloque.model_copy(update={"tipo": TipoBloque.PARRAFO})
        piezas = separar_titulos_en_linea(bloque) if bloque.tipo in SE_BUSCAN_TITULOS else [bloque]
        for pieza in piezas:
            if contenido and _continua(contenido[-1], pieza):
                contenido[-1] = _unir(contenido[-1], pieza)
            else:
                contenido.append(pieza)

    return [b.model_copy(update={"texto": unir_cortes_de_linea(b.texto)}) for b in contenido]


def contar_palabras(texto: str) -> int:
    return len(re.findall(r"\w+", texto))
