"""T14: caché de resultados bibliográficos en ``cache_metadatos`` con la base real.

Criterio: una segunda consulta del mismo DOI se resuelve desde la caché. Además: un
``no_comprobable`` no se guarda, la vigencia se respeta y una entrada vencida se renueva.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.bibliografia.cache import CacheBibliografica
from app.bibliografia.modelos import Estado, Motivo
from app.repositorios.unidad import fabrica_de_unidades
from pruebas.dobles_bibliografia import Transporte, clientes, por_url
from pruebas.integracion.conftest import Entorno, consultar

pytestmark = pytest.mark.integracion

DOI = "10.3390/educsci13090856"
INEXISTENTE = "10.9999/sma-no-existe-2026"
GRABACIONES = {
    f"api.crossref.org/works/{DOI}": "crossref_doi_existente",
    f"api.crossref.org/works/{INEXISTENTE}": "crossref_doi_inexistente",
}


class Reloj:
    def __init__(self) -> None:
        self.ahora = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.ahora


def _cache(entorno: Entorno, reloj: Reloj) -> CacheBibliografica:
    return CacheBibliografica(
        fabrica_de_unidades(entorno.aplicacion.state.fabrica_sesiones),
        vigencia=timedelta(days=30),
        vigencia_no_encontrado=timedelta(hours=24),
        reloj=reloj,
    )


async def test_la_segunda_consulta_del_mismo_doi_sale_de_la_cache(entorno: Entorno) -> None:
    reloj = Reloj()
    transporte = Transporte(por_url(GRABACIONES))
    crossref = clientes(transporte(), cache=_cache(entorno, reloj)).crossref

    primera = await crossref.por_doi(DOI)
    segunda = await crossref.por_doi(f"https://doi.org/{DOI.upper()}")
    assert primera.estado is Estado.ENCONTRADO and not primera.desde_cache
    assert segunda.desde_cache and segunda.metadatos == primera.metadatos
    assert len(transporte.peticiones) == 1

    ((servicio, clave, estado, dias),) = consultar(
        entorno.url_bd,
        "SELECT servicio, clave, respuesta->>'estado',"
        " extract(day from vigente_hasta - obtenida_en)::int FROM cache_metadatos",
    )
    assert (servicio, clave, estado, dias) == ("crossref", DOI, "encontrado", 30)

    # Vencida la vigencia, se vuelve a consultar y la entrada se reemplaza (no se duplica).
    reloj.ahora += timedelta(days=31)
    tercera = await crossref.por_doi(DOI)
    assert not tercera.desde_cache and len(transporte.peticiones) == 2
    assert consultar(entorno.url_bd, "SELECT count(*) FROM cache_metadatos") == [(1,)]


async def test_lo_no_encontrado_vence_antes(entorno: Entorno) -> None:
    reloj = Reloj()
    transporte = Transporte(por_url(GRABACIONES))
    crossref = clientes(transporte(), cache=_cache(entorno, reloj)).crossref
    assert (await crossref.por_doi(INEXISTENTE)).motivo is Motivo.NO_EXISTE
    reloj.ahora += timedelta(hours=23)
    assert (await crossref.por_doi(INEXISTENTE)).desde_cache
    reloj.ahora += timedelta(hours=2)
    assert not (await crossref.por_doi(INEXISTENTE)).desde_cache
    assert len(transporte.peticiones) == 2


async def test_un_no_comprobable_no_se_guarda(entorno: Entorno) -> None:
    def caido(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin conexión simulada")

    reloj = Reloj()
    crossref = clientes(Transporte(caido)(), cache=_cache(entorno, reloj)).crossref
    resultado = await crossref.por_doi(DOI)
    assert (resultado.estado, resultado.motivo) == (Estado.NO_COMPROBABLE, Motivo.SIN_CONEXION)
    assert consultar(entorno.url_bd, "SELECT count(*) FROM cache_metadatos") == [(0,)]
