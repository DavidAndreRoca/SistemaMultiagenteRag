"""T14: limitador, comparador, contrato con respuestas grabadas y fallas simuladas.

Criterios de aceptación:
* con el servicio simulado caído, el resultado es ``no_comprobable`` y nunca
  ``no_encontrado`` (base de CP-13);
* una segunda consulta del mismo DOI se resuelve desde la caché;
* el limitador impide superar la tasa configurada en una ráfaga de prueba.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.bibliografia.cache import CacheBibliografica, CacheEnMemoria
from app.bibliografia.comparador import (
    algun_autor_coincide,
    comparar,
    mejor_coincidencia,
    similitud_titulo,
)
from app.bibliografia.doi import estilo_csl
from app.bibliografia.fabrica import crear_servicios
from app.bibliografia.interfaces import (
    BuscadorBibliografico,
    FormateadorDeCitas,
    ServicioBibliografico,
)
from app.bibliografia.limitador import CubetaDeFichas
from app.bibliografia.modelos import (
    Autor,
    ConsultaBibliografica,
    Estado,
    MetadatosBibliograficos,
    Motivo,
    ResultadoBibliografico,
)
from app.bibliografia.normalizacion import normalizar_doi
from app.configuracion import cargar_ajustes
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.conftest import variables_base
from pruebas.dobles_bibliografia import (
    CLAVE_FICTICIA,
    CORREO_FICTICIO,
    Clientes,
    RelojFalso,
    Transporte,
    clientes,
    hay_grabacion,
    json_respuesta,
    por_url,
)

DOI = "10.3390/educsci13090856"
INEXISTENTE = "10.9999/sma-no-existe-2026"
GRABACIONES = {
    f"api.crossref.org/works/{DOI}": "crossref_doi_existente",
    f"api.crossref.org/works/{INEXISTENTE}": "crossref_doi_inexistente",
    "api.crossref.org/works?": "crossref_busqueda",
    f"doi.org/{INEXISTENTE}": "doi_csl_inexistente",
    f"api.unpaywall.org/v2/{DOI}": "unpaywall_existente",
    f"api.unpaywall.org/v2/{INEXISTENTE}": "unpaywall_inexistente",
    f"api.openalex.org/works/doi:{DOI}": "openalex_doi_existente",
    f"api.openalex.org/works/doi:{INEXISTENTE}": "openalex_doi_inexistente",
    "api.openalex.org/works?": "openalex_busqueda",
}


def _grabado(peticion: httpx.Request) -> httpx.Response:
    if peticion.url.host == "doi.org" and DOI in str(peticion.url):
        nombre = (
            "doi_cita_apa"
            if "x-bibliography" in peticion.headers["accept"]
            else "doi_csl_existente"
        )
        return por_url({DOI: nombre})(peticion)
    return por_url(GRABACIONES)(peticion)


def _con_grabaciones(**opciones: object) -> tuple[Clientes, Transporte]:
    transporte = Transporte(_grabado)
    return clientes(transporte(), **opciones), transporte  # type: ignore[arg-type]


# ----------------------------------------------------------------------------- limitador


def test_el_limitador_no_supera_la_tasa_en_una_rafaga() -> None:
    reloj = RelojFalso()
    cubeta = CubetaDeFichas(3, capacidad=3, reloj=reloj, dormir=reloj.dormir)
    momentos: list[float] = []

    async def rafaga() -> None:
        for _ in range(30):
            await cubeta.adquirir()
            momentos.append(reloj.t)

    asyncio.run(rafaga())
    # La ráfaga inicial (3) sale enseguida; después, nunca más de 3 por segundo.
    assert momentos[:3] == [0.0, 0.0, 0.0]
    for i, inicio in enumerate(momentos):
        for j in range(i, len(momentos)):
            transcurrido = momentos[j] - inicio
            assert j - i + 1 <= 3 + 3 * transcurrido + 1e-9
    assert momentos[-1] == pytest.approx((30 - 3) / 3)


def test_el_limitador_admite_consultas_concurrentes_en_orden() -> None:
    reloj = RelojFalso()
    cubeta = CubetaDeFichas(10, reloj=reloj, dormir=reloj.dormir)

    async def concurrentes() -> None:
        await asyncio.gather(*(cubeta.adquirir() for _ in range(25)))

    asyncio.run(concurrentes())
    assert reloj.t == pytest.approx((25 - 10) / 10)


def test_el_limitador_rechaza_una_tasa_no_positiva() -> None:
    with pytest.raises(ValueError):
        CubetaDeFichas(0)


# ----------------------------------------------------------------------------- comparador

CANDIDATO = MetadatosBibliograficos(
    titulo="Challenges and Opportunities of Generative AI for Higher Education as Explained"
    " by ChatGPT",
    autores=[Autor(apellidos="Michel-Villarreal", nombres="Rosario")],
    anio=2023,
)


def test_el_titulo_se_compara_normalizado_y_sin_subtitulo() -> None:
    assert similitud_titulo("Educación   SUPERIOR: un estudio", "educacion superior") == 1.0
    assert similitud_titulo("Ansiedad y estadística", "Tutoría entre pares") < 0.5
    assert similitud_titulo(None, "algo") == 0.0


@pytest.mark.parametrize(
    ("apellidos", "autores", "coincide"),
    [
        (["Michel-Villarreal"], [Autor(apellidos="Michel-Villarreal")], True),
        (["Villarreal"], [Autor(apellidos="Michel-Villarreal")], True),  # compuesto
        (["Pérez"], [Autor(apellidos="Perez")], True),  # sin tildes
        (["García"], [Autor(nombre_completo="Ana María García López")], True),  # OpenAlex
        (["de"], [Autor(apellidos="de la Cruz")], False),  # menos de 3 letras
        (["Torres"], [Autor(apellidos="Quispe")], False),
    ],
)
def test_coincidencia_de_apellidos(
    apellidos: list[str], autores: list[Autor], coincide: bool
) -> None:
    assert algun_autor_coincide(apellidos, autores) is coincide


@pytest.mark.parametrize(
    ("titulo", "apellidos", "anio", "motivo"),
    [
        (CANDIDATO.titulo, ["Michel-Villarreal"], 2023, None),
        (CANDIDATO.titulo, ["Michel-Villarreal"], 2024, None),  # un año de diferencia
        (CANDIDATO.titulo, ["Michel-Villarreal"], 2021, "anio"),
        ("Otro artículo sobre inteligencia artificial", ["Michel-Villarreal"], 2023, "titulo"),
        (CANDIDATO.titulo, ["Quispe"], 2023, "autor"),
        (CANDIDATO.titulo, [], 2023, "datos_insuficientes"),
        (CANDIDATO.titulo, ["Michel-Villarreal"], None, "datos_insuficientes"),
        (None, ["Michel-Villarreal"], 2023, "datos_insuficientes"),
    ],
)
def test_comparar_exige_titulo_autor_y_anio(
    titulo: str | None, apellidos: list[str], anio: int | None, motivo: str | None
) -> None:
    resultado = comparar(titulo, apellidos, anio, CANDIDATO)
    assert (resultado.confirmada, resultado.motivo) == (motivo is None, motivo)


def test_normalizar_doi() -> None:
    assert normalizar_doi("https://doi.org/10.3390/EDUCSCI13090856.") == DOI
    assert normalizar_doi("doi:10.3390/educsci13090856") == DOI
    assert normalizar_doi("no es un doi") is None


# ------------------------------------------------------------------ contrato (grabado)


def test_crossref_por_doi_con_respuesta_real() -> None:
    cs, _ = _con_grabaciones()
    resultado = asyncio.run(cs.crossref.por_doi(f"https://doi.org/{DOI.upper()}"))
    assert resultado.estado is Estado.ENCONTRADO and resultado.metadatos is not None
    datos = resultado.metadatos
    assert datos.doi == DOI and datos.anio == 2023
    assert datos.titulo is not None and datos.titulo.startswith("Challenges and Opportunities")
    assert (
        datos.autores[0].apellidos == "Michel-Villarreal" and datos.revista == "Education Sciences"
    )
    assert (datos.volumen, datos.numero, datos.paginas) == ("13", "9", "856")


def test_crossref_doi_inexistente_es_no_encontrado() -> None:
    cs, _ = _con_grabaciones()
    resultado = asyncio.run(cs.crossref.por_doi(INEXISTENTE))
    assert (resultado.estado, resultado.motivo) == (Estado.NO_ENCONTRADO, Motivo.NO_EXISTE)


def test_crossref_busqueda_y_comparador_confirman_la_obra() -> None:
    cs, transporte = _con_grabaciones()
    consulta = ConsultaBibliografica(
        titulo=CANDIDATO.titulo or "", autores=["Michel-Villarreal"], anio=2023
    )
    resultado = asyncio.run(cs.crossref.buscar(consulta))
    assert resultado.estado is Estado.ENCONTRADO and len(resultado.candidatos) == 5
    mejor = mejor_coincidencia(
        consulta.titulo, consulta.autores, consulta.anio, resultado.candidatos
    )
    assert mejor is not None and mejor[0].doi == DOI
    # Las otras obras no se confirman con estos datos.
    otros = [c for c in resultado.candidatos if c.doi != DOI]
    assert not any(comparar(consulta.titulo, consulta.autores, 2023, c).confirmada for c in otros)
    params = transporte.peticiones[0].url.params
    assert params["mailto"] == CORREO_FICTICIO and "query.bibliographic" in params


def test_doi_org_metadatos_y_cita_con_respuesta_real() -> None:
    cs, transporte = _con_grabaciones()
    metadatos = asyncio.run(cs.doi.por_doi(DOI))
    assert metadatos.estado is Estado.ENCONTRADO and metadatos.metadatos is not None
    assert metadatos.metadatos.anio == 2023 and metadatos.metadatos.autores[0].apellidos == (
        "Michel-Villarreal"
    )
    estilo = estilo_csl("apa7")
    assert estilo == "apa"
    cita = asyncio.run(cs.doi.cita(DOI, estilo))
    assert cita.estado is Estado.ENCONTRADO and cita.cita is not None
    assert cita.cita.startswith("Michel-Villarreal, R.") and "(2023)" in cita.cita
    assert "style=apa" in transporte.peticiones[-1].headers["accept"]
    inexistente = asyncio.run(cs.doi.por_doi(INEXISTENTE))
    assert inexistente.estado is Estado.NO_ENCONTRADO


def test_unpaywall_acceso_abierto_con_respuesta_real() -> None:
    cs, transporte = _con_grabaciones()
    resultado = asyncio.run(cs.unpaywall.por_doi(DOI))
    acceso = resultado.acceso_abierto
    assert resultado.estado is Estado.ENCONTRADO and acceso is not None
    assert (acceso.es_abierto, acceso.estado, acceso.licencia, acceso.version) == (
        True,
        "gold",
        "cc-by",
        "publishedVersion",
    )
    assert acceso.url is not None
    assert transporte.peticiones[0].url.params["email"] == CORREO_FICTICIO
    assert asyncio.run(cs.unpaywall.por_doi(INEXISTENTE)).estado is Estado.NO_ENCONTRADO


@pytest.mark.skipif(
    not hay_grabacion("openalex_doi_existente"),
    reason="Falta grabar OpenAlex: requiere CLAVE_OPENALEX (python -m pruebas.contrato.grabar)",
)
def test_openalex_con_respuesta_real() -> None:
    cs, transporte = _con_grabaciones()
    resultado = asyncio.run(cs.openalex.por_doi(DOI))
    assert resultado.estado is Estado.ENCONTRADO and resultado.metadatos is not None
    assert resultado.metadatos.anio == 2023 and resultado.acceso_abierto is not None
    assert algun_autor_coincide(["Michel-Villarreal"], resultado.metadatos.autores)
    assert transporte.peticiones[0].url.params["api_key"] == CLAVE_FICTICIA
    assert asyncio.run(cs.openalex.por_doi(INEXISTENTE)).estado is Estado.NO_ENCONTRADO
    busqueda = asyncio.run(
        cs.openalex.buscar(
            ConsultaBibliografica(
                titulo=CANDIDATO.titulo or "", autores=["Michel-Villarreal"], anio=2023
            )
        )
    )
    assert busqueda.estado is Estado.ENCONTRADO and busqueda.candidatos


def test_openalex_mapea_su_formato() -> None:
    """Formato documentado de OpenAlex (simulado hasta tener la grabación real)."""
    obra = {
        "doi": f"https://doi.org/{DOI}",
        "title": CANDIDATO.titulo,
        "publication_year": 2023,
        "type": "article",
        "authorships": [{"author": {"display_name": "Rosario Michel-Villarreal"}}],
        "biblio": {"volume": "13", "issue": "9", "first_page": "856", "last_page": "856"},
        "primary_location": {"source": {"display_name": "Education Sciences"}},
        "open_access": {"is_oa": True, "oa_status": "gold", "oa_url": "https://www.mdpi.com/x"},
        "best_oa_location": {"pdf_url": "https://www.mdpi.com/x/pdf", "license": "cc-by"},
    }
    cs = clientes(httpx.MockTransport(lambda _: json_respuesta(obra)))
    resultado = asyncio.run(cs.openalex.por_doi(DOI))
    assert resultado.metadatos is not None and resultado.acceso_abierto is not None
    assert (resultado.metadatos.doi, resultado.metadatos.paginas) == (DOI, "856")
    assert algun_autor_coincide(["Michel-Villarreal"], resultado.metadatos.autores)
    assert resultado.acceso_abierto.url_pdf == "https://www.mdpi.com/x/pdf"


# --------------------------------------------------------------- fallas simuladas (RN-18)


def _caido(_: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("sin conexión simulada")


def _lento(_: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("respuesta lenta simulada")


def _consultas(cs: Clientes) -> list[Callable[[], Coroutine[Any, Any, ResultadoBibliografico]]]:
    consulta = ConsultaBibliografica(titulo="Un título", autores=["Quispe"], anio=2020)
    return [
        lambda: cs.crossref.por_doi(DOI),
        lambda: cs.crossref.buscar(consulta),
        lambda: cs.doi.por_doi(DOI),
        lambda: cs.doi.cita(DOI, "apa"),
        lambda: cs.unpaywall.por_doi(DOI),
        lambda: cs.openalex.por_doi(DOI),
        lambda: cs.openalex.buscar(consulta),
    ]


@pytest.mark.parametrize(
    ("manejador", "motivo", "peticiones_por_consulta"),
    [
        (_caido, Motivo.SIN_CONEXION, 3),
        (_lento, Motivo.TIEMPO_AGOTADO, 3),
        (lambda _: httpx.Response(503), Motivo.ERROR_DEL_SERVICIO, 3),
        (lambda _: httpx.Response(429), Motivo.LIMITE_DE_TASA, 3),
        (
            lambda _: httpx.Response(
                200, content=b"<html>portal</html>", headers={"content-type": "text/html"}
            ),
            Motivo.RESPUESTA_INVALIDA,
            1,
        ),
        (lambda _: httpx.Response(403), Motivo.ERROR_DEL_SERVICIO, 1),  # sin reintento
    ],
)
def test_un_servicio_caido_da_no_comprobable_y_nunca_no_encontrado(
    manejador: Callable[[httpx.Request], httpx.Response],
    motivo: Motivo,
    peticiones_por_consulta: int,
) -> None:
    """Base de CP-13 (RN-18), en los cuatro clientes y en sus búsquedas."""
    transporte = Transporte(manejador)
    cs = clientes(transporte())
    for consulta in _consultas(cs):
        resultado = asyncio.run(consulta())
        # Nunca no_encontrado: una caída no es una inexistencia (RN-18).
        assert resultado.estado is Estado.NO_COMPROBABLE, resultado
        assert resultado.motivo is motivo
    # Lo transitorio se reintenta (3 intentos); un 403 o un cuerpo ilegible, no.
    assert len(transporte.peticiones) == peticiones_por_consulta * len(_consultas(cs))


def test_los_errores_transitorios_se_reintentan_con_espera_exponencial() -> None:
    estados = iter([503, 502, 200])

    def manejador(peticion: httpx.Request) -> httpx.Response:
        estado = next(estados)
        if estado == 200:
            return por_url(GRABACIONES)(peticion)
        return httpx.Response(estado)

    transporte = Transporte(manejador)
    cs = clientes(transporte())
    resultado = asyncio.run(cs.crossref.por_doi(DOI))
    assert resultado.estado is Estado.ENCONTRADO
    assert len(transporte.peticiones) == 3
    assert cs.reloj.esperas == [0.5, 1.0]  # 0,5 s y 1 s (sin el componente aleatorio)


def test_retry_after_de_un_429_se_respeta() -> None:
    respuestas = iter([httpx.Response(429, headers={"Retry-After": "7"})])

    def manejador(peticion: httpx.Request) -> httpx.Response:
        return next(respuestas, None) or por_url(GRABACIONES)(peticion)

    cs = clientes(Transporte(manejador)())
    assert asyncio.run(cs.crossref.por_doi(DOI)).estado is Estado.ENCONTRADO
    assert cs.reloj.esperas == [7.0]


def test_un_404_no_se_reintenta() -> None:
    transporte = Transporte(por_url(GRABACIONES))
    cs = clientes(transporte())
    asyncio.run(cs.crossref.por_doi(INEXISTENTE))
    assert len(transporte.peticiones) == 1 and cs.reloj.esperas == []


def test_sin_correo_o_sin_clave_el_servicio_no_es_comprobable() -> None:
    transporte = Transporte(_caido)
    cs = clientes(transporte(), correo=None, clave=None)
    for resultado in (
        asyncio.run(cs.unpaywall.por_doi(DOI)),
        asyncio.run(cs.openalex.por_doi(DOI)),
    ):
        assert (resultado.estado, resultado.motivo) == (
            Estado.NO_COMPROBABLE,
            Motivo.NO_CONFIGURADO,
        )
    assert transporte.peticiones == []  # ni siquiera se consulta


def test_un_doi_invalido_no_se_consulta() -> None:
    transporte = Transporte(_caido)
    cs = clientes(transporte())
    resultado = asyncio.run(cs.crossref.por_doi("no-es-un-doi"))
    assert (resultado.estado, resultado.motivo) == (Estado.NO_COMPROBABLE, Motivo.DOI_INVALIDO)
    assert transporte.peticiones == []


# ------------------------------------------------------------------------------ caché


def test_la_segunda_consulta_del_mismo_doi_sale_de_la_cache() -> None:
    transporte = Transporte(_grabado)
    cs = clientes(transporte(), cache=CacheEnMemoria())
    primera = asyncio.run(cs.crossref.por_doi(DOI))
    segunda = asyncio.run(cs.crossref.por_doi(f"https://doi.org/{DOI}"))  # mismo DOI normalizado
    assert (primera.desde_cache, segunda.desde_cache) == (False, True)
    assert segunda.metadatos == primera.metadatos
    assert len(transporte.peticiones) == 1


def test_un_no_comprobable_no_se_guarda_en_la_cache() -> None:
    cache = CacheEnMemoria()
    caido = Transporte(_caido)
    cs = clientes(caido(), cache=cache)
    assert asyncio.run(cs.crossref.por_doi(DOI)).estado is Estado.NO_COMPROBABLE
    assert cache.entradas == {}
    vuelto = Transporte(_grabado)
    cs = clientes(vuelto(), cache=cache)
    assert asyncio.run(cs.crossref.por_doi(DOI)).estado is Estado.ENCONTRADO


def test_el_registro_no_lleva_el_correo_ni_la_clave(caplog: pytest.LogCaptureFixture) -> None:
    cs = clientes(Transporte(_caido)())
    with caplog.at_level(logging.WARNING):
        asyncio.run(cs.openalex.por_doi(DOI))
        asyncio.run(cs.unpaywall.por_doi(DOI))
    registro = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert "servicio bibliografico no disponible" in registro
    assert CORREO_FICTICIO not in registro and CLAVE_FICTICIA not in registro


def test_si_la_base_falla_la_cache_se_omite_y_se_consulta_igual() -> None:
    @asynccontextmanager
    async def abrir_roto() -> AsyncIterator[UnidadDeTrabajo]:
        raise OperationalError("SELECT 1", None, ConnectionError("base caída simulada"))
        yield  # pragma: no cover

    cache = CacheBibliografica(abrir_roto, timedelta(days=30), timedelta(hours=24))
    transporte = Transporte(_grabado)
    cs = clientes(transporte(), cache=cache)
    resultado = asyncio.run(cs.crossref.por_doi(DOI))
    assert resultado.estado is Estado.ENCONTRADO and not resultado.desde_cache
    assert len(transporte.peticiones) == 1


def test_la_fabrica_arma_los_cuatro_clientes_con_su_configuracion() -> None:
    ajustes = cargar_ajustes(
        variables_base(
            CORREO_POLITE=CORREO_FICTICIO, CLAVE_OPENALEX=CLAVE_FICTICIA, TASA_CROSSREF="7"
        )
    )
    transporte = Transporte(_grabado)
    servicios = crear_servicios(ajustes, cache=CacheEnMemoria(), transporte=transporte())

    async def usar() -> None:
        try:
            assert (await servicios.crossref.por_doi(DOI)).estado is Estado.ENCONTRADO
            assert (await servicios.unpaywall.por_doi(DOI)).estado is Estado.ENCONTRADO
        finally:
            await servicios.cerrar()

    asyncio.run(usar())
    agente = transporte.peticiones[0].headers["user-agent"]
    assert agente == f"SistemaMultiagenteRag/0.1 (mailto:{CORREO_FICTICIO})"
    assert servicios.crossref._http._limitador.tasa == 7
    assert isinstance(servicios.crossref, BuscadorBibliografico)
    assert isinstance(servicios.openalex, BuscadorBibliografico)
    assert isinstance(servicios.doi, FormateadorDeCitas)
    assert isinstance(servicios.unpaywall, ServicioBibliografico)
    assert not isinstance(servicios.unpaywall, BuscadorBibliografico)


def test_sin_correo_no_hay_mailto_en_el_agente() -> None:
    servicios = crear_servicios(cargar_ajustes(variables_base()))
    try:
        assert servicios._cliente.headers["user-agent"] == "SistemaMultiagenteRag/0.1"
    finally:
        asyncio.run(servicios.cerrar())
