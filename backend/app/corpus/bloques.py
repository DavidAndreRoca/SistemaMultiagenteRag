"""Bloques de texto que entrega el extractor (Docling) a la limpieza y la segmentación.

Es la frontera entre la biblioteca de extracción y el resto del canal: solo texto,
tipo, páginas y si el bloque es mobiliario de página (encabezado o pie).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TipoBloque(StrEnum):
    TITULO_DOCUMENTO = "titulo_documento"
    TITULO_SECCION = "titulo_seccion"
    PARRAFO = "parrafo"
    ELEMENTO_LISTA = "elemento_lista"
    LEYENDA = "leyenda"
    NOTA = "nota"
    TABLA = "tabla"
    FORMULA = "formula"
    REFERENCIA = "referencia"  # entrada de bibliografía; nunca se segmenta (18.3)
    ENCABEZADO_PAGINA = "encabezado_pagina"
    PIE_PAGINA = "pie_pagina"
    OTRO = "otro"


# Bloques cuyo texto forma parte del cuerpo que se segmenta.
TIPOS_DE_TEXTO = frozenset(
    {TipoBloque.PARRAFO, TipoBloque.ELEMENTO_LISTA, TipoBloque.LEYENDA, TipoBloque.NOTA}
)
TIPOS_MOBILIARIO = frozenset({TipoBloque.ENCABEZADO_PAGINA, TipoBloque.PIE_PAGINA})


class Bloque(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tipo: TipoBloque
    texto: str
    pagina_inicio: int = Field(ge=1)
    pagina_fin: int = Field(ge=1)

    @model_validator(mode="after")
    def _paginas_ordenadas(self) -> Self:
        if self.pagina_inicio > self.pagina_fin:
            raise ValueError("pagina_inicio no puede ser mayor que pagina_fin")
        return self


class DocumentoExtraido(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    num_paginas: int = Field(ge=0)
    bloques: list[Bloque]
