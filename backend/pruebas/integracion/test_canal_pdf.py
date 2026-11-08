"""T09: canal completo con Docling y el tokenizador reales sobre los PDF de muestra.

Marca ``corpus``: necesita el extra ``corpus`` y los recursos verificados en
``DIRECTORIO_RECURSOS_CORPUS`` (``python -m app.corpus.recursos``). GROBID se sustituye
por sus respuestas grabadas (``pruebas/contrato/grobid``); la prueba contra el GROBID real
está en ``test_grobid.py``.
"""

from __future__ import annotations

import importlib.util
import os
import re
from functools import cache
from pathlib import Path

import pytest

from app.administracion.parametros import parametros_iniciales
from app.bd.enumeraciones import SeccionNormalizada as S
from app.corpus.esquemas import (
    DocumentoProcesado,
    EstadoProcesamiento,
    MetadatosCabecera,
    MotivoExclusion,
    MotivoIncompleto,
)
from app.corpus.extraccion import CanalPdf, ParametrosCanal
from app.corpus.grobid import metadatos_desde_tei
from app.corpus.recursos import problemas
from pruebas.datos import textos_muestra as t

pytestmark = pytest.mark.corpus

PRUEBAS = Path(__file__).resolve().parents[1]
PDF = PRUEBAS / "datos" / "pdf"
CONTRATO = PRUEBAS / "contrato" / "grobid"
RECURSOS = os.environ.get("DIRECTORIO_RECURSOS_CORPUS", "")
PARAMETROS = ParametrosCanal.desde(parametros_iniciales())


class GrobidGrabado:
    """Devuelve la cabecera que GROBID 0.9.1 produjo para cada PDF de muestra."""

    def cabecera(self, ruta: Path) -> MetadatosCabecera:
        grabada = CONTRATO / f"cabecera_{ruta.stem}.tei.xml"
        if not grabada.exists():
            return MetadatosCabecera()
        return metadatos_desde_tei(grabada.read_text(encoding="utf-8"))


@cache
def _canal() -> CanalPdf:
    from app.corpus.extractor_docling import ExtractorDocling
    from app.corpus.tokenizador import ContadorTokensBgeM3

    recursos = Path(RECURSOS)
    return CanalPdf(
        ExtractorDocling(recursos), GrobidGrabado(), ContadorTokensBgeM3(recursos), PARAMETROS
    )


@pytest.fixture(scope="module")
def canal() -> CanalPdf:
    if importlib.util.find_spec("docling") is None:
        pytest.skip("falta el extra corpus (Docling)")
    if not RECURSOS or problemas(Path(RECURSOS)):
        pytest.skip("DIRECTORIO_RECURSOS_CORPUS sin recursos verificados")
    return _canal()


@cache
def procesado(nombre: str) -> DocumentoProcesado:
    return _canal().procesar_pdf(PDF / nombre)


def textos(documento: DocumentoProcesado) -> str:
    return "\n".join(f.texto for f in documento.fragmentos)


def comprobar_fragmentos(documento: DocumentoProcesado) -> None:
    """Criterio de T09: cada fragmento lleva sección normalizada, título original y páginas."""
    assert documento.fragmentos
    for fragmento in documento.fragmentos:
        assert fragmento.seccion_normalizada in S
        assert fragmento.seccion_original
        assert 1 <= fragmento.pagina_inicio <= fragmento.pagina_fin <= (documento.num_paginas or 0)
        assert fragmento.tokens <= PARAMETROS.ventana.maximo
    assert [f.orden for f in documento.fragmentos] == list(range(len(documento.fragmentos)))


def test_articulo_en_espanol(canal: CanalPdf) -> None:
    documento = procesado("articulo_es.pdf")
    assert documento.estado is EstadoProcesamiento.PROCESADO, documento.motivos_incompleto
    assert documento.secciones == [
        S.RESUMEN,
        S.INTRODUCCION,
        S.METODOS,
        S.RESULTADOS,
        S.DISCUSION,
        S.CONCLUSIONES,
    ]
    assert documento.palabras >= PARAMETROS.palabras_minimas
    comprobar_fragmentos(documento)
    texto = textos(documento)
    # Referencias, agradecimientos, encabezado, pie y preliminares no llegan a los fragmentos.
    for ausente in (
        t.SOLO_EN_REFERENCIAS_ES,
        t.SOLO_EN_AGRADECIMIENTOS_ES,
        "Revista Ficticia de Educación Superior, 4(2)",
        "Mendoza Vargas",
        "Facultad de Psicología",
    ):
        assert ausente not in texto, ausente
    assert not re.search(r"Página \d+ de \d+", texto)
    # El párrafo que Docling partió en tres piezas al pie de la página 1 queda unido.
    assert "antes y después de la intervención. La población estuvo formada" in texto
    assert "continuó con las clases regulares" in texto
    metodos = [f for f in documento.fragmentos if f.seccion_normalizada is S.METODOS]
    assert metodos[0].seccion_original == "2.1. Diseño y participantes"
    assert (metodos[0].pagina_inicio, metodos[-1].pagina_fin) == (1, 2)
    assert documento.metadatos is not None
    assert documento.metadatos.doi == "10.5555/rfes.2026.0042"


def test_articulo_en_ingles_a_dos_columnas(canal: CanalPdf) -> None:
    documento = procesado("articulo_en.pdf")
    assert documento.estado is EstadoProcesamiento.PROCESADO, documento.motivos_incompleto
    assert documento.secciones == [
        S.RESUMEN,
        S.INTRODUCCION,
        S.METODOS,
        S.RESULTADOS,
        S.DISCUSION,
        S.CONCLUSIONES,
    ]
    comprobar_fragmentos(documento)
    texto = textos(documento)
    for ausente in (
        t.SOLO_EN_REFERENCIAS_EN,
        t.SOLO_EN_AGRADECIMIENTOS_EN,
        "Fictitious Journal of Student Health, 2(1)",
        "Daniel Torres Medina",
    ):
        assert ausente not in texto, ausente
    assert not re.search(r"Page \d+ of \d+", texto)
    # La cola de párrafo que Docling tomó por título vuelve a su párrafo.
    assert "effective preparation rather than a competing activity." in texto
    # Orden de lectura en dos columnas: la introducción va antes que los métodos.
    introduccion = texto.index("The transition to university")
    assert (
        introduccion
        < texto.index("Understanding this association")
        < texto.index("The study used a cross-sectional design")
    )


def test_documento_corto_queda_incompleto_con_motivo(canal: CanalPdf) -> None:
    documento = procesado("documento_corto.pdf")
    assert documento.estado is EstadoProcesamiento.INCOMPLETO
    assert documento.motivos_incompleto == [MotivoIncompleto.TEXTO_INSUFICIENTE]
    assert documento.secciones == [S.INTRODUCCION]


def test_documento_sin_secciones_imrad_queda_incompleto(canal: CanalPdf) -> None:
    documento = procesado("sin_secciones_imrad.pdf")
    assert documento.estado is EstadoProcesamiento.INCOMPLETO
    assert documento.motivos_incompleto == [MotivoIncompleto.SIN_SECCIONES_IMRAD]
    assert {f.seccion_normalizada for f in documento.fragmentos} == {S.OTRA}


def test_pdf_que_solo_restringe_permisos_se_procesa(canal: CanalPdf) -> None:
    documento = procesado("solo_permisos.pdf")
    assert documento.estado is EstadoProcesamiento.INCOMPLETO
    assert documento.fragmentos


@pytest.mark.parametrize(
    ("nombre", "motivo"),
    [
        ("escaneado.pdf", MotivoExclusion.SIN_CAPA_DE_TEXTO),
        ("cifrado.pdf", MotivoExclusion.PDF_CIFRADO),
    ],
)
def test_pdf_escaneado_o_cifrado_produce_estado_y_motivo(
    canal: CanalPdf, nombre: str, motivo: MotivoExclusion
) -> None:
    documento = procesado(nombre)
    assert (documento.estado, documento.motivo_exclusion) == (EstadoProcesamiento.EXCLUIDO, motivo)
    assert documento.fragmentos == []


def test_el_canal_es_determinista(canal: CanalPdf) -> None:
    assert canal.procesar_pdf(PDF / "articulo_en.pdf") == procesado("articulo_en.pdf")
