"""Construye los cuatro clientes con un cliente HTTP compartido, sus limitadores y la caché."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import httpx

from app.bibliografia.cache import Cache, CacheBibliografica
from app.bibliografia.crossref import ClienteCrossref
from app.bibliografia.doi import ClienteDoi
from app.bibliografia.http import ClienteHttp, PoliticaReintentos
from app.bibliografia.limitador import CubetaDeFichas
from app.bibliografia.modelos import Servicio
from app.bibliografia.openalex import ClienteOpenAlex
from app.bibliografia.unpaywall import ClienteUnpaywall
from app.configuracion import Ajustes
from app.repositorios.unidad import FabricaUnidades

NOMBRE_CLIENTE = "SistemaMultiagenteRag/0.1"
RAFAGA_UNPAYWALL = 10  # la tasa media es baja (100 000 por día); se admite una ráfaga corta


@dataclass
class ServiciosBibliograficos:
    crossref: ClienteCrossref
    doi: ClienteDoi
    unpaywall: ClienteUnpaywall
    openalex: ClienteOpenAlex
    _cliente: httpx.AsyncClient

    async def cerrar(self) -> None:
        await self._cliente.aclose()


def crear_cliente_http(
    ajustes: Ajustes, transporte: httpx.AsyncBaseTransport | None = None
) -> httpx.AsyncClient:
    agente = NOMBRE_CLIENTE
    if ajustes.correo_polite:
        agente += f" (mailto:{ajustes.correo_polite})"  # pool cortés de Crossref
    return httpx.AsyncClient(
        timeout=httpx.Timeout(ajustes.tiempo_maximo_bibliografia_s, connect=5.0),
        headers={"User-Agent": agente},
        follow_redirects=True,  # doi.org redirige al registro del DOI
        transport=transporte,
    )


def crear_servicios(
    ajustes: Ajustes,
    abrir: FabricaUnidades | None = None,
    *,
    cache: Cache | None = None,
    transporte: httpx.AsyncBaseTransport | None = None,
) -> ServiciosBibliograficos:
    """Con ``abrir``, la caché va a ``cache_metadatos``; ``cache`` permite otra."""
    if cache is None and abrir is not None:
        cache = CacheBibliografica(
            abrir,
            vigencia=timedelta(days=ajustes.vigencia_cache_bibliografia_dias),
            vigencia_no_encontrado=timedelta(hours=ajustes.vigencia_no_encontrado_horas),
        )
    cliente = crear_cliente_http(ajustes, transporte)
    politica = PoliticaReintentos(intentos=ajustes.reintentos_bibliografia)

    def http(servicio: Servicio, limitador: CubetaDeFichas) -> ClienteHttp:
        return ClienteHttp(servicio, cliente, limitador, politica)

    clave = ajustes.clave_openalex.get_secret_value() if ajustes.clave_openalex else None
    correo = ajustes.correo_polite
    return ServiciosBibliograficos(
        crossref=ClienteCrossref(
            http(Servicio.CROSSREF, CubetaDeFichas(ajustes.tasa_crossref)),
            CubetaDeFichas(ajustes.tasa_crossref_busqueda),
            correo,
            cache,
        ),
        doi=ClienteDoi(http(Servicio.DOI, CubetaDeFichas(ajustes.tasa_doi)), cache),
        unpaywall=ClienteUnpaywall(
            http(Servicio.UNPAYWALL, CubetaDeFichas(ajustes.tasa_unpaywall, RAFAGA_UNPAYWALL)),
            correo,
            cache,
        ),
        openalex=ClienteOpenAlex(
            http(Servicio.OPENALEX, CubetaDeFichas(ajustes.tasa_openalex)), clave, correo, cache
        ),
        _cliente=cliente,
    )
