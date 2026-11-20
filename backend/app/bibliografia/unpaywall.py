"""Cliente de Unpaywall: estado de acceso abierto y mejor ubicación por DOI (RN-14, RNF-08).

Exige el correo del proyecto en ``email``; sin él, el resultado es ``no_comprobable``
(``no_configurado``). Uso pedido: hasta 100 000 consultas por día.
"""

from __future__ import annotations

from typing import Any

from app.bibliografia.base import ClienteBase, doi_en_ruta, texto
from app.bibliografia.cache import Cache
from app.bibliografia.http import ClienteHttp, FallaDeServicio, json_de
from app.bibliografia.modelos import (
    AccesoAbierto,
    Autor,
    Estado,
    MetadatosBibliograficos,
    Motivo,
    ResultadoBibliografico,
    Servicio,
)
from app.bibliografia.normalizacion import normalizar_doi

URL_BASE = "https://api.unpaywall.org/v2"


def acceso_unpaywall(datos: dict[str, Any]) -> AccesoAbierto:
    mejor = datos.get("best_oa_location")
    mejor = mejor if isinstance(mejor, dict) else {}
    return AccesoAbierto(
        es_abierto=bool(datos.get("is_oa")),
        estado=texto(datos.get("oa_status")),
        url=texto(mejor.get("url")),
        url_pdf=texto(mejor.get("url_for_pdf")),
        licencia=texto(mejor.get("license")),
        version=texto(mejor.get("version")),
    )


def metadatos_unpaywall(datos: dict[str, Any]) -> MetadatosBibliograficos:
    autores = [
        Autor(apellidos=texto(a.get("family")), nombres=texto(a.get("given")))
        for a in datos.get("z_authors") or []
        if isinstance(a, dict) and a.get("family")
    ]
    anio = datos.get("year")
    return MetadatosBibliograficos(
        doi=normalizar_doi(texto(datos.get("doi"))),
        titulo=texto(datos.get("title")),
        autores=autores,
        anio=anio if isinstance(anio, int) else None,
        revista=texto(datos.get("journal_name")),
        editorial=texto(datos.get("publisher")),
        tipo=texto(datos.get("genre")),
    )


class ClienteUnpaywall(ClienteBase):
    servicio = Servicio.UNPAYWALL

    def __init__(self, http: ClienteHttp, correo: str | None, cache: Cache | None = None) -> None:
        super().__init__(http, cache)
        self._correo = correo

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        normal = self._doi_valido(doi)
        if normal is None:
            return self._doi_invalido()
        if not self._correo:
            return ResultadoBibliografico.no_comprobable(self.servicio, Motivo.NO_CONFIGURADO)
        correo = self._correo

        async def obtener() -> ResultadoBibliografico:
            respuesta = await self._http.get(
                f"{URL_BASE}/{doi_en_ruta(normal)}", params={"email": correo}
            )
            if respuesta.status_code == 404:
                return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.NO_EXISTE)
            if respuesta.status_code != 200:
                raise FallaDeServicio(Motivo.ERROR_DEL_SERVICIO)
            datos = self._diccionario(json_de(respuesta))
            return ResultadoBibliografico(
                servicio=self.servicio,
                estado=Estado.ENCONTRADO,
                metadatos=metadatos_unpaywall(datos),
                acceso_abierto=acceso_unpaywall(datos),
            )

        return await self._con_cache(normal, obtener)
