"""Dobles para probar los clientes bibliográficos sin red (T14).

* ``respuesta_grabada``: una respuesta real de ``pruebas/contrato/respuestas/``.
* ``Transporte``: ``httpx.MockTransport`` que responde según la URL y cuenta las llamadas.
* ``RelojFalso``: reloj y espera simulados para el limitador y los reintentos.
* ``clientes``: los cuatro clientes con un transporte dado y sin esperas reales.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.bibliografia.cache import Cache
from app.bibliografia.crossref import ClienteCrossref
from app.bibliografia.doi import ClienteDoi
from app.bibliografia.http import ClienteHttp, PoliticaReintentos
from app.bibliografia.limitador import CubetaDeFichas
from app.bibliografia.modelos import Servicio
from app.bibliografia.openalex import ClienteOpenAlex
from app.bibliografia.unpaywall import ClienteUnpaywall

RESPUESTAS = Path(__file__).parent / "contrato" / "respuestas"
CORREO_FICTICIO = "proyecto@example.org"
CLAVE_FICTICIA = "clave-ficticia-de-openalex"


def hay_grabacion(nombre: str) -> bool:
    return (RESPUESTAS / f"{nombre}.json").is_file()


def respuesta_grabada(nombre: str) -> httpx.Response:
    registro = json.loads((RESPUESTAS / f"{nombre}.json").read_text(encoding="utf-8"))
    cuerpo = registro["cuerpo"]
    contenido = (
        json.dumps(cuerpo).encode() if not isinstance(cuerpo, str) else cuerpo.encode("utf-8")
    )
    return httpx.Response(
        registro["estado"], content=contenido, headers={"content-type": registro["tipo"]}
    )


Manejador = Callable[[httpx.Request], httpx.Response]


@dataclass
class Transporte:
    """Responde con ``manejador`` y guarda cada petición."""

    manejador: Manejador
    peticiones: list[httpx.Request] = field(default_factory=list)

    def __call__(self) -> httpx.MockTransport:
        def responder(peticion: httpx.Request) -> httpx.Response:
            self.peticiones.append(peticion)
            return self.manejador(peticion)

        return httpx.MockTransport(responder)


def por_url(rutas: dict[str, str]) -> Manejador:
    """Responde con la grabación cuyo fragmento de URL aparece en la petición."""

    def manejador(peticion: httpx.Request) -> httpx.Response:
        url = str(peticion.url)
        for fragmento, nombre in rutas.items():
            if fragmento in url:
                return respuesta_grabada(nombre)
        raise AssertionError(f"petición sin grabación: {peticion.url.path}")

    return manejador


@dataclass
class RelojFalso:
    t: float = 0.0
    esperas: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.t

    async def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self.t += segundos


@dataclass
class Clientes:
    crossref: ClienteCrossref
    doi: ClienteDoi
    unpaywall: ClienteUnpaywall
    openalex: ClienteOpenAlex
    reloj: RelojFalso


def clientes(
    transporte: httpx.AsyncBaseTransport,
    *,
    cache: Cache | None = None,
    correo: str | None = CORREO_FICTICIO,
    clave: str | None = CLAVE_FICTICIA,
    intentos: int = 3,
) -> Clientes:
    reloj = RelojFalso()
    http_cliente = httpx.AsyncClient(transport=transporte, follow_redirects=True)
    politica = PoliticaReintentos(intentos=intentos)

    def cubeta(tasa: float) -> CubetaDeFichas:
        return CubetaDeFichas(tasa, reloj=reloj, dormir=reloj.dormir)

    def http(servicio: Servicio) -> ClienteHttp:
        return ClienteHttp(
            servicio, http_cliente, cubeta(100), politica, dormir=reloj.dormir, azar=lambda: 0.0
        )

    return Clientes(
        crossref=ClienteCrossref(http(Servicio.CROSSREF), cubeta(100), correo, cache),
        doi=ClienteDoi(http(Servicio.DOI), cache),
        unpaywall=ClienteUnpaywall(http(Servicio.UNPAYWALL), correo, cache),
        openalex=ClienteOpenAlex(http(Servicio.OPENALEX), clave, correo, cache),
        reloj=reloj,
    )


def json_respuesta(cuerpo: Any, estado: int = 200, **cabeceras: str) -> httpx.Response:
    return httpx.Response(estado, json=cuerpo, headers=cabeceras)
