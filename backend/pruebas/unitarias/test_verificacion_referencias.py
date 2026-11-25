"""Estado de cada referencia (T20, actividades 3 y 4; CP-12, CP-13, RN-18; decisión T20-01)."""

from __future__ import annotations

import pytest

from app.agentes.esquemas import EstadoReferencia
from app.agentes.verificacion_referencias import Verificador
from app.bibliografia.modelos import (
    Autor,
    ConsultaBibliografica,
    Estado,
    MetadatosBibliograficos,
    Motivo,
    ResultadoBibliografico,
    Servicio,
)
from app.corpus.grobid import ReferenciaGrobid

OBRA = MetadatosBibliograficos(
    doi="10.5555/ficticio.2021.001",
    titulo="Tutoría entre pares y ansiedad ante la estadística",
    autores=[Autor(apellidos="Quispe", nombres="Ana"), Autor(apellidos="Huamán", nombres="Luis")],
    anio=2021,
    revista="Revista Ficticia de Pedagogía",
)
OTRA = MetadatosBibliograficos(
    doi="10.5555/ficticio.2019.777",
    titulo="Costos logísticos en microempresas costeras",
    autores=[Autor(apellidos="Torres")],
    anio=2019,
)


class Servicio_:
    """Crossref u OpenAlex simulado: conoce unas obras, o no responde."""

    def __init__(
        self, servicio: Servicio, obras: list[MetadatosBibliograficos], caido: bool = False
    ) -> None:
        self.servicio = servicio
        self.obras = obras
        self.caido = caido
        self.llamadas: list[str] = []

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        self.llamadas.append(f"doi:{doi}")
        if self.caido:
            return ResultadoBibliografico.no_comprobable(self.servicio, Motivo.SIN_CONEXION)
        obra = next((o for o in self.obras if o.doi == doi), None)
        if obra is None:
            return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.SIN_COINCIDENCIAS)
        return ResultadoBibliografico(
            servicio=self.servicio, estado=Estado.ENCONTRADO, metadatos=obra
        )

    async def buscar(self, consulta: ConsultaBibliografica) -> ResultadoBibliografico:
        self.llamadas.append(f"buscar:{consulta.titulo}")
        if self.caido:
            return ResultadoBibliografico.no_comprobable(self.servicio, Motivo.SIN_CONEXION)
        if not self.obras:
            return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.SIN_COINCIDENCIAS)
        return ResultadoBibliografico(
            servicio=self.servicio, estado=Estado.ENCONTRADO, candidatos=self.obras
        )


def _verificador(
    obras: list[MetadatosBibliograficos] | None = None,
    *,
    crossref_caido: bool = False,
    openalex_caido: bool = False,
    en_openalex: list[MetadatosBibliograficos] | None = None,
) -> tuple[Verificador, Servicio_, Servicio_]:
    crossref = Servicio_(
        Servicio.CROSSREF, obras if obras is not None else [OBRA, OTRA], crossref_caido
    )
    openalex = Servicio_(Servicio.OPENALEX, en_openalex or [], openalex_caido)
    return Verificador(crossref, openalex), crossref, openalex


def _ref(**cambios: object) -> ReferenciaGrobid:
    base: dict[str, object] = {
        "texto": "Quispe, A., & Huamán, L. (2021). Tutoría entre pares y ansiedad ante la"
        " estadística. Revista Ficticia de Pedagogía.",
        "titulo": OBRA.titulo,
        "apellidos": ["Quispe", "Huamán"],
        "anio": 2021,
        "doi": OBRA.doi,
    }
    return ReferenciaGrobid.model_validate({**base, **cambios})


async def test_con_doi_y_datos_correctos_queda_verificada() -> None:
    verificador, _, openalex = _verificador()
    resultado = await verificador.verificar(1, _ref())
    assert resultado.estado is EstadoReferencia.VERIFICADA
    assert (resultado.metodo, resultado.doi_encontrado, resultado.discrepancias) == (
        "doi",
        OBRA.doi,
        [],
    )
    assert openalex.llamadas == []  # Crossref ya la encontró


async def test_cp12_un_anio_distinto_aunque_sea_en_uno_da_discrepancia() -> None:
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(2, _ref(anio=2022))
    assert resultado.estado is EstadoReferencia.CON_DISCREPANCIAS
    (discrepancia,) = resultado.discrepancias
    assert (discrepancia.campo, discrepancia.valor_borrador, discrepancia.valor_fuente) == (
        "anio",
        "2022",
        "2021",
    )


async def test_titulo_y_autores_distintos_se_informan_con_ambos_valores() -> None:
    verificador, _, _ = _verificador()
    titulo = "Tutoría y ansiedad matemática en la escuela"
    resultado = await verificador.verificar(
        1, _ref(texto=f"Pérez, J. (2021). {titulo}.", titulo=titulo, apellidos=["Pérez"])
    )
    assert resultado.estado is EstadoReferencia.CON_DISCREPANCIAS
    campos = {d.campo: d for d in resultado.discrepancias}
    assert set(campos) == {"titulo", "autores"}
    assert campos["autores"].valor_borrador == "Pérez"
    assert campos["autores"].valor_fuente == "Quispe, Huamán"


async def test_un_primer_autor_cambiado_es_discrepancia_aunque_los_coautores_coincidan() -> None:
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(apellidos=["Mendívil", "Huamán"]))
    assert resultado.estado is EstadoReferencia.CON_DISCREPANCIAS
    (discrepancia,) = resultado.discrepancias
    assert (discrepancia.campo, discrepancia.valor_borrador) == ("autores", "Mendívil, Huamán")


async def test_el_orden_de_los_coautores_no_importa_si_el_primero_coincide() -> None:
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(apellidos=["Quispe"]))
    assert resultado.estado is EstadoReferencia.VERIFICADA


async def test_un_doi_que_lleva_a_otra_obra_nunca_queda_verificada() -> None:
    """Decisión T20-01 (a): referencia fabricada con un DOI real de otra obra."""
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(doi=OTRA.doi))
    assert resultado.estado is EstadoReferencia.CON_DISCREPANCIAS
    assert {d.campo for d in resultado.discrepancias} >= {"titulo", "autores"}


async def test_un_dato_que_falta_en_la_referencia_es_una_discrepancia() -> None:
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(anio=None))
    assert resultado.estado is EstadoReferencia.CON_DISCREPANCIAS
    assert resultado.discrepancias[0].model_dump() == {
        "campo": "anio",
        "valor_borrador": None,
        "valor_fuente": "2021",
    }


async def test_sin_doi_se_busca_por_metadatos_y_se_informa_el_doi_encontrado() -> None:
    verificador, crossref, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(doi=None))
    assert resultado.estado is EstadoReferencia.VERIFICADA
    assert (resultado.metodo, resultado.doi_encontrado) == ("metadatos", OBRA.doi)
    assert crossref.llamadas == [f"buscar:{OBRA.titulo}"]


async def test_sin_doi_un_libro_sin_doi_se_verifica_por_metadatos() -> None:
    libro = MetadatosBibliograficos(
        titulo="Metodología de la investigación educativa",
        autores=[Autor(apellidos="Ramos")],
        anio=2015,
        tipo="book",
    )
    verificador, _, _ = _verificador([libro])
    resultado = await verificador.verificar(
        1,
        ReferenciaGrobid(
            texto="Ramos (2015)...", titulo=libro.titulo, apellidos=["Ramos"], anio=2015
        ),
    )
    assert resultado.estado is EstadoReferencia.VERIFICADA
    assert (resultado.metodo, resultado.doi_encontrado) == ("metadatos", None)


async def test_si_crossref_no_la_tiene_se_busca_en_openalex() -> None:
    verificador, _, openalex = _verificador([], en_openalex=[OBRA])
    resultado = await verificador.verificar(1, _ref(doi=None))
    assert resultado.estado is EstadoReferencia.VERIFICADA
    assert openalex.llamadas == [f"buscar:{OBRA.titulo}"]


async def test_cp12_una_fabricada_queda_no_localizada() -> None:
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(
        3,
        _ref(
            doi=None,
            titulo="Tutores neuronales en la sierra andina",
            apellidos=["Mamani"],
            anio=2020,
        ),
    )
    assert resultado.estado is EstadoReferencia.NO_LOCALIZADA
    assert (resultado.metodo, resultado.doi_encontrado) == ("metadatos", None)


async def test_un_doi_inexistente_y_un_titulo_inventado_quedan_no_localizados() -> None:
    verificador, crossref, openalex = _verificador()
    resultado = await verificador.verificar(
        1, _ref(doi="10.5555/no.existe", titulo="Una obra que nadie escribió", apellidos=["Nadie"])
    )
    assert resultado.estado is EstadoReferencia.NO_LOCALIZADA
    assert crossref.llamadas[0] == "doi:10.5555/no.existe"
    assert openalex.llamadas[0] == "doi:10.5555/no.existe"


async def test_un_doi_mal_escrito_de_una_obra_que_existe_da_discrepancia_de_doi() -> None:
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(doi="10.5555/ficticio.2021.00X"))
    assert resultado.estado is EstadoReferencia.CON_DISCREPANCIAS
    assert resultado.discrepancias[0].model_dump() == {
        "campo": "doi",
        "valor_borrador": "10.5555/ficticio.2021.00X",
        "valor_fuente": OBRA.doi,
    }
    assert (resultado.metodo, resultado.doi_encontrado) == ("metadatos", OBRA.doi)


@pytest.mark.parametrize("con_doi", [True, False])
async def test_cp13_con_los_servicios_caidos_queda_no_comprobable(con_doi: bool) -> None:
    verificador, _, _ = _verificador(crossref_caido=True, openalex_caido=True)
    referencia = _ref() if con_doi else _ref(doi=None)
    resultado = await verificador.verificar(1, referencia)
    assert resultado.estado is EstadoReferencia.NO_COMPROBABLE  # RN-18: nunca no localizada
    assert resultado.discrepancias == []


async def test_rn18_si_uno_cae_y_el_otro_no_la_encuentra_no_es_inexistente() -> None:
    verificador, _, _ = _verificador([], openalex_caido=True)
    resultado = await verificador.verificar(1, _ref(doi=None, titulo="Obra desconocida"))
    assert resultado.estado is EstadoReferencia.NO_COMPROBABLE


async def test_si_uno_cae_pero_el_otro_la_encuentra_queda_verificada() -> None:
    verificador, _, _ = _verificador([], crossref_caido=True, en_openalex=[OBRA])
    resultado = await verificador.verificar(1, _ref())
    assert resultado.estado is EstadoReferencia.VERIFICADA


async def test_sin_titulo_ni_doi_no_hay_con_que_buscar() -> None:
    verificador, crossref, _ = _verificador()
    resultado = await verificador.verificar(1, ReferenciaGrobid(texto="Texto ilegible 2020"))
    assert resultado.estado is EstadoReferencia.NO_LOCALIZADA
    assert resultado.discrepancias[0].campo == "titulo" and crossref.llamadas == []


async def test_el_texto_original_se_conserva_recortado() -> None:
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(texto="x" * 2500))
    assert len(resultado.texto_original) == 2000


async def test_un_titulo_mal_leido_por_grobid_no_es_discrepancia_si_esta_en_la_entrada() -> None:
    """Con un título que termina en un año, GROBID tomó la revista como título (T20-01)."""
    verificador, _, _ = _verificador()
    resultado = await verificador.verificar(1, _ref(titulo="Revista Ficticia de Pedagogía"))
    assert resultado.estado is EstadoReferencia.VERIFICADA


async def test_un_titulo_cambiado_sigue_siendo_discrepancia() -> None:
    verificador, _, _ = _verificador()
    texto = "Quispe, A. (2021). Otro título inventado. Revista Ficticia de Pedagogía."
    resultado = await verificador.verificar(1, _ref(texto=texto, titulo="Otro título inventado"))
    assert [d.campo for d in resultado.discrepancias] == ["titulo"]
