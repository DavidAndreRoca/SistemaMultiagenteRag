"""Párrafos del borrador con identificador estable (T11, actividad 4; decisión T11-01, 5).

Se recorre el cuerpo en orden de lectura, con los párrafos y las celdas de las tablas
(también las anidadas y sin repetir las celdas combinadas). El texto de un párrafo es la
suma de sus ``w:t``: entran hipervínculos, controles de contenido, inserciones del control
de cambios y el resultado visible de los campos (las citas de Zotero o Mendeley tal como
se ven). No entran el texto eliminado (``w:delText``), el código de los campos
(``w:instrText``) ni los cuadros de texto. El archivo debe estar ya validado.
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
ESPACIOS = {f"{W}tab", f"{W}br", f"{W}cr"}
# Subárboles que no son texto del párrafo: cuadros de texto y su versión alternativa.
OMITIDOS = {f"{W}txbxContent", f"{MC}Fallback"}
_BLANCOS = re.compile(r"\s+")

Origen = Literal["cuerpo", "tabla"]


class ParrafoBorrador(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str  # p1, p2... dentro de la versión
    texto: str
    estilo: str | None
    origen: Origen


class TextoBorrador(BaseModel):
    model_config = ConfigDict(frozen=True)

    parrafos: list[ParrafoBorrador]
    palabras: int


def extraer_parrafos(ruta: Path) -> TextoBorrador:
    parrafos: list[ParrafoBorrador] = []
    for parrafo, origen in _recorrer(Document(str(ruta)), "cuerpo"):
        texto = texto_de_parrafo(parrafo._p)
        if texto:
            estilo = parrafo.style.name if parrafo.style is not None else None
            parrafos.append(
                ParrafoBorrador(
                    id=f"p{len(parrafos) + 1}", texto=texto, estilo=estilo, origen=origen
                )
            )
    return TextoBorrador(parrafos=parrafos, palabras=sum(len(p.texto.split()) for p in parrafos))


def _recorrer(contenedor: Any, origen: Origen) -> Iterator[tuple[Paragraph, Origen]]:
    for bloque in contenedor.iter_inner_content():
        if isinstance(bloque, Paragraph):
            yield bloque, origen
        elif isinstance(bloque, Table):
            # Una celda combinada aparece varias veces. El conjunto guarda los elementos (no
            # su id(), que lxml recicla): mientras viven, lxml devuelve el mismo objeto.
            vistas: set[Any] = set()
            for fila in bloque.rows:
                for celda in fila.cells:
                    if celda._tc in vistas:
                        continue
                    vistas.add(celda._tc)
                    yield from _recorrer(celda, "tabla")


def texto_de_parrafo(elemento: Any) -> str:
    partes: list[str] = []
    _juntar(elemento, partes)
    return _BLANCOS.sub(" ", "".join(partes)).strip()


def _juntar(elemento: Any, partes: list[str]) -> None:
    for hijo in elemento:
        etiqueta = hijo.tag
        if etiqueta in OMITIDOS:
            continue
        if etiqueta == TEXTO:
            partes.append(hijo.text or "")
        elif etiqueta in ESPACIOS:
            partes.append(" ")
        else:
            _juntar(hijo, partes)
