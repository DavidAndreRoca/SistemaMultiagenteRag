"""Localización de cada referencia con los servicios de T14 (T15-01, apartado 5).

1. Con DOI: Crossref por DOI y, si no lo conoce, OpenAlex por DOI (los DOI de DataCite,
   como arXiv o Zenodo, no están en Crossref). Si nadie lo encuentra (DOI mal escrito), se
   busca por metadatos.
2. Sin DOI: búsqueda en Crossref y, si no confirma, en OpenAlex. El comparador de T14
   exige título, autor y año.
3. RN-18: si algún servicio no respondió y nada confirmó la obra, el resultado es
   ``no_comprobable``, nunca ``no_localizada``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.bibliografia.comparador import mejor_coincidencia
from app.bibliografia.interfaces import BuscadorBibliografico
from app.bibliografia.modelos import (
    AccesoAbierto,
    ConsultaBibliografica,
    Estado,
    MetadatosBibliograficos,
    Motivo,
)
from app.corpus.grobid import ReferenciaGrobid


class Localizacion(StrEnum):
    LOCALIZADA = "localizada"
    NO_LOCALIZADA = "no_localizada"
    NO_COMPROBABLE = "no_comprobable"


class ResultadoLocalizacion(BaseModel):
    model_config = ConfigDict(frozen=True)

    localizacion: Localizacion
    metadatos: MetadatosBibliograficos | None = None
    # Acceso abierto según OpenAlex, si la localizó por DOI: respaldo cuando Unpaywall no
    # tiene el registro (DOI de DataCite).
    acceso_abierto: AccesoAbierto | None = None
    motivo: str | None = None  # servicio y motivo cuando no es comprobable


class Localizador:
    def __init__(self, crossref: BuscadorBibliografico, openalex: BuscadorBibliografico) -> None:
        self._crossref = crossref
        self._openalex = openalex

    async def localizar(self, referencia: ReferenciaGrobid) -> ResultadoLocalizacion:
        fallas: list[str] = []
        if referencia.doi:
            for servicio in (self._crossref, self._openalex):
                resultado = await servicio.por_doi(referencia.doi)
                if resultado.estado is Estado.ENCONTRADO and resultado.metadatos is not None:
                    metadatos = resultado.metadatos
                    if not metadatos.doi:
                        metadatos = metadatos.model_copy(update={"doi": referencia.doi})
                    return ResultadoLocalizacion(
                        localizacion=Localizacion.LOCALIZADA,
                        metadatos=metadatos,
                        acceso_abierto=resultado.acceso_abierto,
                    )
                if resultado.estado is Estado.NO_COMPROBABLE:
                    fallas.append(_falla(resultado.servicio.value, resultado.motivo))
        if referencia.titulo and referencia.apellidos and referencia.anio:
            consulta = ConsultaBibliografica(
                titulo=referencia.titulo, autores=referencia.apellidos, anio=referencia.anio
            )
            for buscador in (self._crossref, self._openalex):
                busqueda = await buscador.buscar(consulta)
                if busqueda.estado is Estado.NO_COMPROBABLE:
                    fallas.append(_falla(busqueda.servicio.value, busqueda.motivo))
                    continue
                mejor = mejor_coincidencia(
                    consulta.titulo, consulta.autores, consulta.anio, busqueda.candidatos
                )
                if mejor is not None:
                    return ResultadoLocalizacion(
                        localizacion=Localizacion.LOCALIZADA, metadatos=mejor[0]
                    )
        if fallas:
            return ResultadoLocalizacion(localizacion=Localizacion.NO_COMPROBABLE, motivo=fallas[0])
        return ResultadoLocalizacion(localizacion=Localizacion.NO_LOCALIZADA)


def _falla(servicio: str, motivo: Motivo | None) -> str:
    return f"{servicio}_{motivo.value if motivo else 'sin_respuesta'}"[:60]
