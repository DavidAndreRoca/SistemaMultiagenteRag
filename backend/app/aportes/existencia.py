"""Existencia de una fuente aportada (T32; RF-13, CP-14 a CP-16, RN-18). Sin modelo.

* **Con DOI:** Crossref y, si no lo conoce, OpenAlex. Si ningún servicio resuelve el DOI y
  todos respondieron, la existencia no se confirma (CP-16): no se busca por metadatos una
  obra cuyo DOI declarado no existe.
* **Sin DOI:** búsqueda por metadatos en Crossref y luego en OpenAlex; se confirma si un
  candidato coincide en título, al menos un autor y año (comparador de T14, CP-15).
* Si un servicio no respondió y nada la confirmó, queda ``no_comprobable`` (RN-18): nunca
  se declara inexistente por una caída.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.bd.enumeraciones import ExistenciaFuente, MetodoExistencia
from app.bibliografia.comparador import mejor_coincidencia
from app.bibliografia.interfaces import BuscadorBibliografico
from app.bibliografia.modelos import ConsultaBibliografica, Estado, MetadatosBibliograficos
from app.bibliografia.normalizacion import normalizar_doi

MAX_AUTORES = 20


class DatosAporte(BaseModel):
    """Datos bibliográficos que declara el caso (título, autores y año; DOI opcional)."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    titulo: Annotated[str, Field(min_length=3, max_length=500)]
    autores: Annotated[list[str], Field(min_length=1, max_length=MAX_AUTORES)]
    anio: Annotated[int, Field(ge=1500, le=2100)]
    doi: str | None = None

    @field_validator("autores")
    @classmethod
    def _apellidos(cls, autores: list[str]) -> list[str]:
        """Cada autor como apellidos: "Pérez, Ana" da "Pérez"; las líneas vacías se omiten."""
        limpios = [x for x in (a.split(",")[0].strip()[:120] for a in autores) if x]
        if not limpios:
            raise ValueError("Escriba al menos un autor.")
        return limpios

    @field_validator("doi")
    @classmethod
    def _doi(cls, doi: str | None) -> str | None:
        if doi is None or not doi.strip():
            return None
        normal = normalizar_doi(doi)
        if normal is None:
            raise ValueError("El DOI no tiene la forma 10.xxxx/...")
        return normal


@dataclass(frozen=True)
class Existencia:
    estado: ExistenciaFuente
    metodo: MetodoExistencia | None = None
    metadatos: MetadatosBibliograficos | None = None  # del registro, si se confirmó


async def comprobar_existencia(
    datos: DatosAporte, servicios: Sequence[BuscadorBibliografico]
) -> Existencia:
    fallas = False
    if datos.doi:
        for servicio in servicios:
            resultado = await servicio.por_doi(datos.doi)
            if resultado.estado is Estado.ENCONTRADO and resultado.metadatos is not None:
                metadatos = resultado.metadatos
                if metadatos.doi is None:
                    metadatos = metadatos.model_copy(update={"doi": datos.doi})
                return Existencia(ExistenciaFuente.CONFIRMADA, MetodoExistencia.DOI, metadatos)
            fallas = fallas or resultado.estado is Estado.NO_COMPROBABLE
        return Existencia(
            ExistenciaFuente.NO_COMPROBABLE if fallas else ExistenciaFuente.NO_LOCALIZADA
        )
    consulta = ConsultaBibliografica(titulo=datos.titulo, autores=datos.autores, anio=datos.anio)
    for servicio in servicios:
        busqueda = await servicio.buscar(consulta)
        if busqueda.estado is Estado.NO_COMPROBABLE:
            fallas = True
            continue
        hallada = mejor_coincidencia(datos.titulo, datos.autores, datos.anio, busqueda.candidatos)
        if hallada is not None:
            return Existencia(ExistenciaFuente.CONFIRMADA, MetodoExistencia.METADATOS, hallada[0])
    return Existencia(ExistenciaFuente.NO_COMPROBABLE if fallas else ExistenciaFuente.NO_LOCALIZADA)


async def resumen_de(
    metadatos: MetadatosBibliograficos, servicios: Sequence[BuscadorBibliografico]
) -> str | None:
    """El resumen del registro; si no lo trae (por ejemplo, una búsqueda de Crossref), se
    pide la obra por DOI a cada servicio. Una falla deja la fuente sin resumen."""
    if metadatos.resumen:
        return metadatos.resumen
    if not metadatos.doi:
        return None
    for servicio in servicios:
        resultado = await servicio.por_doi(metadatos.doi)
        if resultado.metadatos is not None and resultado.metadatos.resumen:
            return resultado.metadatos.resumen
    return None
