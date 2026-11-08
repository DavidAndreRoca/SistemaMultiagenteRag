"""T09: reglas del canal ``procesar_pdf`` con extractor y GROBID simulados.

La validación usa los PDF de muestra reales; Docling se sustituye por bloques fijos.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.administracion.parametros import VentanaTokens, parametros_iniciales
from app.bd.enumeraciones import SeccionNormalizada as S
from app.corpus.bloques import Bloque, DocumentoExtraido, TipoBloque
from app.corpus.esquemas import (
    DocumentoProcesado,
    EstadoProcesamiento,
    MetadatosCabecera,
    MotivoExclusion,
    MotivoIncompleto,
)
from app.corpus.extraccion import CanalPdf, ParametrosCanal, huella_de_texto
from app.corpus.extractor_docling import ErrorExtraccion
from app.corpus.validacion import LimitesPdf

PDF = Path(__file__).resolve().parents[1] / "datos" / "pdf"
T = TipoBloque
SECRETO = "Frase confidencial del cuerpo"


class PorPalabras:
    def contar(self, texto: str) -> int:
        return len(texto.split())


class ExtractorFijo:
    def __init__(self, bloques: list[Bloque] | Exception, num_paginas: int = 3) -> None:
        self.bloques = bloques
        self.num_paginas = num_paginas
        self.llamadas = 0

    def extraer(self, ruta: Path) -> DocumentoExtraido:
        self.llamadas += 1
        if isinstance(self.bloques, Exception):
            raise self.bloques
        return DocumentoExtraido(num_paginas=self.num_paginas, bloques=self.bloques)


class CabeceraFija:
    def __init__(self) -> None:
        self.llamadas = 0

    def cabecera(self, ruta: Path) -> MetadatosCabecera:
        self.llamadas += 1
        return MetadatosCabecera(titulo="Título ficticio", doi="10.5555/x.1")


PARAMETROS = ParametrosCanal(
    limites=LimitesPdf(25, 60),
    ventana=VentanaTokens(minimo=60, maximo=90, objetivo=80),
    solapamiento_oraciones=1,
    palabras_minimas=100,
)


def b(tipo: TipoBloque, texto: str, pagina: int = 1) -> Bloque:
    return Bloque(tipo=tipo, texto=texto, pagina_inicio=pagina, pagina_fin=pagina)


def frases(n: int, base: str = "Una frase ficticia de prueba") -> str:
    return " ".join(f"{base} número {i}." for i in range(n))


def articulo() -> list[Bloque]:
    return [
        b(T.TITULO_DOCUMENTO, "Título"),
        b(T.TITULO_SECCION, "Introducción"),
        b(T.PARRAFO, f"{SECRETO}. " + frases(9)),
        b(T.TITULO_SECCION, "Método", 2),
        b(T.PARRAFO, frases(9), 2),
        b(T.TITULO_SECCION, "Referencias", 3),
        b(T.PARRAFO, "Autor, A. (2020). Obra ficticia que no debe aparecer.", 3),
    ]


def canal(extractor: ExtractorFijo, cabecera: CabeceraFija | None = None) -> CanalPdf:
    return CanalPdf(extractor, cabecera or CabeceraFija(), PorPalabras(), PARAMETROS)


def test_un_articulo_completo_se_procesa_con_fragmentos_y_metadatos(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        documento = canal(ExtractorFijo(articulo())).procesar_pdf(PDF / "articulo_es.pdf")
    assert documento.estado is EstadoProcesamiento.PROCESADO
    assert documento.secciones == [S.INTRODUCCION, S.METODOS]
    assert documento.metadatos is not None and documento.metadatos.doi == "10.5555/x.1"
    assert [f.seccion_normalizada for f in documento.fragmentos] == [S.INTRODUCCION, S.METODOS]
    assert all(f.seccion_original and f.pagina_inicio >= 1 for f in documento.fragmentos)
    assert not any("Obra ficticia" in f.texto for f in documento.fragmentos)
    assert documento.palabras > 100 and documento.num_paginas == 3
    cuerpo = "\n".join((f"{SECRETO}. " + frases(9), frases(9)))
    assert documento.huella_texto == huella_de_texto(cuerpo)
    # RN-23 y 4.6: el registro guarda cantidades y estados, nunca texto del documento.
    registro = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert SECRETO not in registro and "procesado" in registro


def test_texto_insuficiente_queda_incompleto_con_motivo_y_fragmentos() -> None:
    bloques = [b(T.TITULO_SECCION, "Introducción"), b(T.PARRAFO, frases(2))]
    documento = canal(ExtractorFijo(bloques)).procesar_pdf(PDF / "documento_corto.pdf")
    assert documento.estado is EstadoProcesamiento.INCOMPLETO
    assert documento.motivos_incompleto == [MotivoIncompleto.TEXTO_INSUFICIENTE]
    assert documento.fragmentos  # se indexan solo si el investigador confirma (T10)
    assert documento.mensajes == ["Se extrajo menos texto del esperado para un artículo."]


def test_sin_secciones_imrad_queda_incompleto() -> None:
    bloques = [b(T.TITULO_SECCION, "Primera parte"), b(T.PARRAFO, frases(30))]
    documento = canal(ExtractorFijo(bloques)).procesar_pdf(PDF / "articulo_es.pdf")
    assert documento.estado is EstadoProcesamiento.INCOMPLETO
    assert documento.motivos_incompleto == [MotivoIncompleto.SIN_SECCIONES_IMRAD]
    assert {f.seccion_normalizada for f in documento.fragmentos} == {S.OTRA}


def test_los_dos_motivos_a_la_vez() -> None:
    documento = canal(ExtractorFijo([b(T.PARRAFO, "Poco texto.")])).procesar_pdf(
        PDF / "documento_corto.pdf"
    )
    assert documento.motivos_incompleto == [
        MotivoIncompleto.TEXTO_INSUFICIENTE,
        MotivoIncompleto.SIN_SECCIONES_IMRAD,
    ]


@pytest.mark.parametrize(
    ("nombre", "motivo"),
    [
        ("escaneado.pdf", MotivoExclusion.SIN_CAPA_DE_TEXTO),
        ("cifrado.pdf", MotivoExclusion.PDF_CIFRADO),
    ],
)
def test_un_pdf_invalido_se_excluye_sin_extraer_ni_llamar_a_grobid(
    nombre: str, motivo: MotivoExclusion
) -> None:
    extractor, cabecera = ExtractorFijo(articulo()), CabeceraFija()
    documento = canal(extractor, cabecera).procesar_pdf(PDF / nombre)
    assert (documento.estado, documento.motivo_exclusion) == (EstadoProcesamiento.EXCLUIDO, motivo)
    assert documento.fragmentos == [] and documento.metadatos is None
    assert extractor.llamadas == cabecera.llamadas == 0
    assert documento.mensajes


def test_si_docling_no_extrae_texto_se_excluye_sin_capa_de_texto() -> None:
    documento = canal(ExtractorFijo([b(T.ENCABEZADO_PAGINA, "Revista")])).procesar_pdf(
        PDF / "articulo_es.pdf"
    )
    assert documento.motivo_exclusion is MotivoExclusion.SIN_CAPA_DE_TEXTO


def test_si_docling_falla_se_excluye_como_ilegible() -> None:
    documento = canal(ExtractorFijo(ErrorExtraccion("fallo"))).procesar_pdf(PDF / "articulo_es.pdf")
    assert documento.motivo_exclusion is MotivoExclusion.PDF_ILEGIBLE


def test_los_parametros_salen_de_la_configuracion_versionada() -> None:
    parametros = ParametrosCanal.desde(parametros_iniciales())
    assert parametros.limites == LimitesPdf(25, 60)
    assert (parametros.ventana.minimo, parametros.ventana.maximo) == (300, 450)
    assert (parametros.solapamiento_oraciones, parametros.palabras_minimas) == (1, 1500)


def test_la_huella_de_texto_ignora_mayusculas_y_espacios() -> None:
    assert huella_de_texto("Hola   Mundo\n") == huella_de_texto("hola mundo")


@pytest.mark.parametrize(
    "datos",
    [
        {"estado": "excluido"},  # sin motivo
        {
            "estado": "excluido",
            "motivo_exclusion": "no_es_pdf",
            "motivos_incompleto": ["texto_insuficiente"],
        },
        {"estado": "procesado", "motivo_exclusion": "no_es_pdf"},
        {"estado": "incompleto"},  # sin motivo
        {"estado": "procesado"},  # sin fragmentos
        {"estado": "procesado", "motivos_incompleto": ["texto_insuficiente"]},
    ],
)
def test_el_documento_procesado_exige_estado_coherente(datos: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DocumentoProcesado.model_validate({"huella_archivo": "a" * 64, **datos})


def test_los_fragmentos_se_numeran_sin_huecos() -> None:
    fragmento = {
        "texto": "x",
        "seccion_normalizada": "otra",
        "seccion_original": None,
        "pagina_inicio": 1,
        "pagina_fin": 1,
        "tokens": 1,
    }
    with pytest.raises(ValidationError, match="numeran"):
        DocumentoProcesado.model_validate(
            {
                "estado": "procesado",
                "huella_archivo": "a" * 64,
                "fragmentos": [fragmento | {"orden": 1}],
            }
        )
    with pytest.raises(ValidationError, match="pagina_inicio"):
        DocumentoProcesado.model_validate(
            {
                "estado": "procesado",
                "huella_archivo": "a" * 64,
                "fragmentos": [fragmento | {"orden": 0, "pagina_inicio": 2}],
            }
        )
