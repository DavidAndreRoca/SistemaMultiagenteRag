"""Aporte de fuentes sin base (T32): resumen de los registros, datos declarados, existencia,
segmentación del resumen y coherencia sin modelo."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.aportes.coherencia import evaluar_coherencia
from app.aportes.existencia import DatosAporte, comprobar_existencia, resumen_de
from app.aportes.servicio import PALABRAS_POR_FRAGMENTO, texto_del_resumen, trozos_del_resumen
from app.bd.enumeraciones import CoherenciaFuente, ExistenciaFuente, MetodoExistencia
from app.bibliografia.crossref import metadatos_crossref
from app.bibliografia.openalex import metadatos_openalex
from pruebas.dobles_aportes import (
    OBRA_MONETARIA,
    OBRA_SIN_DOI,
    RESUMEN_MONETARIA,
    RESUMEN_SIN_DOI,
    bibliografia_ficticia,
)


def test_el_resumen_jats_de_crossref_queda_en_texto_plano() -> None:
    item = {
        "abstract": "<jats:p>La tutor&#237;a <jats:italic>reduce</jats:italic>\n"
        " la ansiedad.</jats:p>"
    }
    assert metadatos_crossref(item).resumen == "La tutoría reduce la ansiedad."


def test_el_resumen_de_openalex_se_arma_desde_el_indice_invertido() -> None:
    obra = {
        "abstract_inverted_index": {
            "reduce": [2],
            "La": [0],
            "tutoría": [1],
            "ansiedad.": [4],
            "la": [3],
        }
    }
    assert metadatos_openalex(obra).resumen == "La tutoría reduce la ansiedad."
    assert metadatos_openalex({}).resumen is None


def test_los_datos_declarados_se_validan_y_normalizan() -> None:
    datos = DatosAporte(
        titulo=" Un título ",
        autores=["Pérez, Ana", "", "  García Márquez "],
        anio=2024,
        doi="https://doi.org/10.5555/ABC.1",
    )
    assert datos.autores == ["Pérez", "García Márquez"] and datos.doi == "10.5555/abc.1"
    assert DatosAporte(titulo="Otro título", autores=["X"], anio=2020, doi="  ").doi is None
    with pytest.raises(ValidationError):
        DatosAporte(titulo="Título", autores=[",", " "], anio=2024)
    with pytest.raises(ValidationError):
        DatosAporte(titulo="Título", autores=["X"], anio=2024, doi="no es un doi")


async def test_existencia_por_doi_por_metadatos_y_sin_confirmar() -> None:
    crossref, openalex = bibliografia_ficticia()
    servicios = [crossref, openalex]
    por_doi = await comprobar_existencia(
        DatosAporte(titulo="x" * 5, autores=["Z"], anio=2000, doi=OBRA_MONETARIA.doi), servicios
    )
    assert (por_doi.estado, por_doi.metodo) == (ExistenciaFuente.CONFIRMADA, MetodoExistencia.DOI)
    por_metadatos = await comprobar_existencia(
        DatosAporte(titulo=OBRA_SIN_DOI.titulo or "", autores=["Prueba"], anio=2023), servicios
    )
    assert por_metadatos.metodo is MetodoExistencia.METADATOS
    assert await resumen_de(por_metadatos.metadatos, servicios) == RESUMEN_SIN_DOI  # type: ignore[arg-type]
    # El año o el autor que no coinciden no confirman la obra (CP-15).
    otro_autor = await comprobar_existencia(
        DatosAporte(titulo=OBRA_SIN_DOI.titulo or "", autores=["Distinto"], anio=2023), servicios
    )
    assert otro_autor.estado is ExistenciaFuente.NO_LOCALIZADA
    # Con un servicio caído y nada confirmado: no comprobable (RN-18).
    openalex.caido = True
    caida = await comprobar_existencia(
        DatosAporte(titulo="T" * 5, autores=["Z"], anio=2000, doi="10.5555/otra"), servicios
    )
    assert caida.estado is ExistenciaFuente.NO_COMPROBABLE


def test_el_resumen_se_segmenta_por_oraciones() -> None:
    trozos = trozos_del_resumen(RESUMEN_MONETARIA)
    assert len(trozos) >= 2 and " ".join(trozos) == " ".join(RESUMEN_MONETARIA.split())
    assert all(t.endswith(".") for t in trozos)
    assert all(len(t.split()) <= PALABRAS_POR_FRAGMENTO for t in trozos)
    texto = texto_del_resumen(RESUMEN_MONETARIA)
    assert texto.huella == texto_del_resumen("  " + RESUMEN_MONETARIA.upper()).huella
    assert not texto.desde_pdf and all(t > 0 for t in texto.tokens)


async def test_sin_modelo_ni_texto_la_coherencia_no_se_evalua() -> None:
    versiones = dict
    assert (
        await evaluar_coherencia(None, versiones, "a", ["b"])
    ).valor is CoherenciaFuente.NO_EVALUADA
    assert (
        await evaluar_coherencia(None, versiones, "a", [])
    ).valor is CoherenciaFuente.NO_EVALUADA
