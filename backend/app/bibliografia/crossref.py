"""Cliente de Crossref: existencia y metadatos por DOI, y búsqueda por metadatos (T14).

Fuente principal de DOI. Pool cortés: correo del proyecto en ``mailto`` y en el
``User-Agent`` (la fábrica lo pone en el cliente HTTP), 10 consultas por segundo de
registro individual y 3 de búsqueda, cada una con su limitador.
"""

from __future__ import annotations

from typing import Any

from app.bibliografia.base import ClienteBase, anio_de_partes, autores_csl, doi_en_ruta, texto
from app.bibliografia.cache import Cache
from app.bibliografia.http import ClienteHttp, FallaDeServicio, json_de
from app.bibliografia.limitador import CubetaDeFichas
from app.bibliografia.modelos import (
    ConsultaBibliografica,
    Estado,
    MetadatosBibliograficos,
    Motivo,
    ResultadoBibliografico,
    Servicio,
)
from app.bibliografia.normalizacion import normalizar_doi

URL_BASE = "https://api.crossref.org"
CANDIDATOS = 5
CAMPOS_BUSQUEDA = (
    "DOI,title,author,issued,published-print,published-online,container-title,volume,"
    "issue,page,publisher,type"
)


def metadatos_crossref(item: dict[str, Any]) -> MetadatosBibliograficos:
    anio = (
        anio_de_partes(item.get("issued"))
        or anio_de_partes(item.get("published-print"))
        or anio_de_partes(item.get("published-online"))
    )
    return MetadatosBibliograficos(
        doi=normalizar_doi(texto(item.get("DOI"))),
        titulo=texto(item.get("title")),
        autores=autores_csl(item.get("author")),
        anio=anio,
        revista=texto(item.get("container-title")),
        volumen=texto(item.get("volume")),
        numero=texto(item.get("issue")),
        paginas=texto(item.get("page")),
        editorial=texto(item.get("publisher")),
        tipo=texto(item.get("type")),
    )


class ClienteCrossref(ClienteBase):
    servicio = Servicio.CROSSREF

    def __init__(
        self,
        http: ClienteHttp,
        limitador_busqueda: CubetaDeFichas,
        correo: str | None,
        cache: Cache | None = None,
    ) -> None:
        super().__init__(http, cache)
        self._limitador_busqueda = limitador_busqueda
        self._params = {"mailto": correo} if correo else {}

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        normal = self._doi_valido(doi)
        if normal is None:
            return self._doi_invalido()

        async def obtener() -> ResultadoBibliografico:
            respuesta = await self._http.get(
                f"{URL_BASE}/works/{doi_en_ruta(normal)}", params=self._params
            )
            if respuesta.status_code == 404:
                return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.NO_EXISTE)
            if respuesta.status_code != 200:
                raise FallaDeServicio(Motivo.ERROR_DEL_SERVICIO)
            cuerpo = self._diccionario(json_de(respuesta))
            mensaje = self._diccionario(cuerpo.get("message"))
            return ResultadoBibliografico(
                servicio=self.servicio,
                estado=Estado.ENCONTRADO,
                metadatos=metadatos_crossref(mensaje),
            )

        return await self._con_cache(normal, obtener)

    async def buscar(self, consulta: ConsultaBibliografica) -> ResultadoBibliografico:
        async def obtener() -> ResultadoBibliografico:
            respuesta = await self._http.get(
                f"{URL_BASE}/works",
                params={
                    **self._params,
                    "query.bibliographic": consulta.texto()[:500],
                    "rows": str(CANDIDATOS),
                    "select": CAMPOS_BUSQUEDA,
                },
                limitador=self._limitador_busqueda,
            )
            if respuesta.status_code != 200:
                raise FallaDeServicio(Motivo.ERROR_DEL_SERVICIO)
            mensaje = self._diccionario(self._diccionario(json_de(respuesta)).get("message"))
            items = mensaje.get("items")
            if not isinstance(items, list):
                raise FallaDeServicio(Motivo.RESPUESTA_INVALIDA)
            candidatos = [metadatos_crossref(i) for i in items if isinstance(i, dict)]
            if not candidatos:
                return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.SIN_COINCIDENCIAS)
            return ResultadoBibliografico(
                servicio=self.servicio, estado=Estado.ENCONTRADO, candidatos=candidatos
            )

        return await self._con_cache(consulta.clave(), obtener)
