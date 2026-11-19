"""Párrafos del borrador con identificador estable (T11, actividad 4; T12-01, apartado 2).

Se recorre el cuerpo en orden de lectura, con los párrafos y las celdas de las tablas
(también las anidadas y sin repetir las celdas combinadas) y el contenido de los controles
de contenido de bloque (``w:sdt``), donde Mendeley y Word ponen la bibliografía.

El texto de un párrafo es la suma de sus ``w:t``: entran hipervínculos, controles de
contenido, inserciones del control de cambios y el resultado visible de los campos (las
citas de Zotero o Mendeley tal como se ven). No entran el texto eliminado
(``w:delText``), el código de los campos (``w:instrText``) ni los cuadros de texto. Los
saltos de línea se conservan como ``\\n``. Cada párrafo guarda además su nivel de título
(T12-01, apartado 3). El archivo debe estar ya validado.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pydantic import BaseModel, ConfigDict

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
TEXTO = f"{W}t"
TABULACION = f"{W}tab"
SALTOS = {f"{W}br", f"{W}cr"}
# Subárboles que no son texto del párrafo: cuadros de texto y su versión alternativa.
OMITIDOS = {f"{W}txbxContent", f"{MC}Fallback"}
# Contenedores de bloque cuyo contenido es parte del cuerpo.
CONTENEDORES = {f"{W}sdt": f"{W}sdtContent", f"{W}customXml": None}
_BLANCOS_EN_LINEA = re.compile(r"[^\S\n]+")

# Nivel por el nombre del estilo (Word guarda en inglés los de sus estilos integrados).
_NIVEL_POR_NOMBRE = re.compile(r"^(?:heading|t[ií]tulo|encabezado)\s*([1-9])$", re.IGNORECASE)
_TITULO_DEL_DOCUMENTO = {"title", "título", "titulo"}
NIVEL_TEXTO = 9  # w:outlineLvl 9: texto, no título

Origen = Literal["cuerpo", "tabla"]


class ParrafoBorrador(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str  # p1, p2... dentro de la versión
    texto: str
    estilo: str | None
    origen: Origen
    nivel: int | None = None  # 0: título del documento; 1 a 9: título; None: texto


class TextoBorrador(BaseModel):
    model_config = ConfigDict(frozen=True)

    parrafos: list[ParrafoBorrador]
    palabras: int


def extraer_parrafos(ruta: Path) -> TextoBorrador:
    documento = Document(str(ruta))
    parrafos: list[ParrafoBorrador] = []
    for parrafo, origen in _recorrer(documento._body._body, documento._body, "cuerpo"):
        texto = texto_de_parrafo(parrafo._p)
        if texto:
            estilo = parrafo.style.name if parrafo.style is not None else None
            parrafos.append(
                ParrafoBorrador(
                    id=f"p{len(parrafos) + 1}",
                    texto=texto,
                    estilo=estilo,
                    origen=origen,
                    nivel=nivel_de_titulo(parrafo) if origen == "cuerpo" else None,
                )
            )
    return TextoBorrador(parrafos=parrafos, palabras=sum(len(p.texto.split()) for p in parrafos))


def _recorrer(elemento: Any, padre: Any, origen: Origen) -> Iterator[tuple[Paragraph, Origen]]:
    """Párrafos de un contenedor (cuerpo, celda o control de contenido) en orden."""
    for hijo in elemento.iterchildren():
        etiqueta = hijo.tag
        if etiqueta == f"{W}p":
            yield Paragraph(hijo, padre), origen
        elif etiqueta == f"{W}tbl":
            # Una celda combinada aparece varias veces. El conjunto guarda los elementos (no
            # su id(), que lxml recicla): mientras viven, lxml devuelve el mismo objeto.
            vistas: set[Any] = set()
            for fila in Table(hijo, padre).rows:
                for celda in fila.cells:
                    if celda._tc in vistas:
                        continue
                    vistas.add(celda._tc)
                    yield from _recorrer(celda._tc, celda, "tabla")
        elif etiqueta in CONTENEDORES:
            interior = CONTENEDORES[etiqueta]
            contenido = hijo if interior is None else hijo.find(interior)
            if contenido is not None:
                yield from _recorrer(contenido, padre, origen)


def texto_de_parrafo(elemento: Any) -> str:
    partes: list[str] = []
    _juntar(elemento, partes)
    lineas = (_BLANCOS_EN_LINEA.sub(" ", linea).strip() for linea in "".join(partes).split("\n"))
    return "\n".join(linea for linea in lineas if linea)


def _juntar(elemento: Any, partes: list[str]) -> None:
    for hijo in elemento:
        etiqueta = hijo.tag
        if etiqueta in OMITIDOS:
            continue
        if etiqueta == TEXTO:
            partes.append(hijo.text or "")
        elif etiqueta == TABULACION:
            partes.append(" ")
        elif etiqueta in SALTOS:
            partes.append("\n")
        else:
            _juntar(hijo, partes)


def _nivel_de_esquema(propiedades: Any) -> int | None:
    """``w:outlineLvl`` de unas propiedades de párrafo (0 a 9), si lo tienen."""
    if propiedades is None:
        return None
    nodo = propiedades.find(f"{W}outlineLvl")
    valor = nodo.get(f"{W}val") if nodo is not None else None
    return int(valor) if valor is not None and valor.isdigit() else None


def nivel_de_titulo(parrafo: Paragraph) -> int | None:
    """0 para el título del documento, 1 a 9 para un título y None para el texto."""
    propio = _nivel_de_esquema(parrafo._p.pPr)
    if propio is not None:
        return None if propio >= NIVEL_TEXTO else propio + 1
    estilo: Any = parrafo.style
    vistos = 0
    while estilo is not None and vistos < 20:  # cadena de estilos base, sin ciclos
        nombre = (estilo.name or "").strip().lower()
        if nombre in _TITULO_DEL_DOCUMENTO:
            return 0
        coincidencia = _NIVEL_POR_NOMBRE.match(nombre)
        if coincidencia:
            return int(coincidencia.group(1))
        del_estilo = _nivel_de_esquema(estilo.element.pPr)
        if del_estilo is not None:
            return None if del_estilo >= NIVEL_TEXTO else del_estilo + 1
        estilo = estilo.base_style
        vistos += 1
    return None
