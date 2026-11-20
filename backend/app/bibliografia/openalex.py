"""Cliente de OpenAlex: respaldo de metadatos y de estado de acceso abierto (T14).

Desde el 13 de febrero de 2026 exige una clave (``CLAVE_OPENALEX``); sin ella el resultado
es ``no_comprobable`` (``no_configurado``). La consulta por DOI no tiene costo; la
búsqueda, sí (alrededor de USD 1 por 1 000), por eso se usa solo como respaldo.
OpenAlex da el nombre completo de cada autor, sin separar el apellido.
"""

from __future__ import annotations

from typing import Any

from app.bibliografia.base import ClienteBase, doi_en_ruta, texto
from app.bibliografia.cache import Cache
from app.bibliografia.http import ClienteHttp, FallaDeServicio, json_de
from app.bibliografia.modelos import (
    AccesoAbierto,
    Autor,
    ConsultaBibliografica,
    Estado,
    MetadatosBibliograficos,
    Motivo,
    ResultadoBibliografico,
    Servicio,
)
from app.bibliografia.normalizacion import normalizar_doi

URL_BASE = "https://api.openalex.org"
CANDIDATOS = 5


def _dic(valor: object) -> dict[str, Any]:
    return valor if isinstance(valor, dict) else {}


def metadatos_openalex(obra: dict[str, Any]) -> MetadatosBibliograficos:
    autores = [
        Autor(nombre_completo=texto(_dic(a.get("author")).get("display_name")))
        for a in obra.get("authorships") or []
        if isinstance(a, dict) and _dic(a.get("author")).get("display_name")
    ]
    biblio = _dic(obra.get("biblio"))
    primera, ultima = texto(biblio.get("first_page")), texto(biblio.get("last_page"))
    paginas = f"{primera}-{ultima}" if primera and ultima and primera != ultima else primera
    fuente = _dic(_dic(obra.get("primary_location")).get("source"))
    anio = obra.get("publication_year")
    return MetadatosBibliograficos(
        doi=normalizar_doi(texto(obra.get("doi"))),
        titulo=texto(obra.get("title") or obra.get("display_name")),
        autores=autores,
        anio=anio if isinstance(anio, int) else None,
        revista=texto(fuente.get("display_name")),
        volumen=texto(biblio.get("volume")),
        numero=texto(biblio.get("issue")),
        paginas=paginas,
        tipo=texto(obra.get("type")),
    )


def acceso_openalex(obra: dict[str, Any]) -> AccesoAbierto:
    abierto = _dic(obra.get("open_access"))
    mejor = _dic(obra.get("best_oa_location"))
    return AccesoAbierto(
        es_abierto=bool(abierto.get("is_oa")),
        estado=texto(abierto.get("oa_status")),
        url=texto(mejor.get("landing_page_url") or abierto.get("oa_url")),
        url_pdf=texto(mejor.get("pdf_url")),
        licencia=texto(mejor.get("license")),
        version=texto(mejor.get("version")),
    )


class ClienteOpenAlex(ClienteBase):
    servicio = Servicio.OPENALEX

    def __init__(
        self,
        http: ClienteHttp,
        clave: str | None,
        correo: str | None,
        cache: Cache | None = None,
    ) -> None:
        super().__init__(http, cache)
        self._params = {"api_key": clave} if clave else {}
        if correo:
            self._params["mailto"] = correo

    def _sin_clave(self) -> ResultadoBibliografico | None:
        if "api_key" not in self._params:
            return ResultadoBibliografico.no_comprobable(self.servicio, Motivo.NO_CONFIGURADO)
        return None

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        normal = self._doi_valido(doi)
        if normal is None:
            return self._doi_invalido()
        if (sin_clave := self._sin_clave()) is not None:
            return sin_clave

        async def obtener() -> ResultadoBibliografico:
            respuesta = await self._http.get(
                f"{URL_BASE}/works/doi:{doi_en_ruta(normal)}", params=self._params
            )
            if respuesta.status_code == 404:
                return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.NO_EXISTE)
            if respuesta.status_code != 200:
                raise FallaDeServicio(Motivo.ERROR_DEL_SERVICIO)
            obra = self._diccionario(json_de(respuesta))
            return ResultadoBibliografico(
                servicio=self.servicio,
                estado=Estado.ENCONTRADO,
                metadatos=metadatos_openalex(obra),
                acceso_abierto=acceso_openalex(obra),
            )

        return await self._con_cache(normal, obtener)

    async def buscar(self, consulta: ConsultaBibliografica) -> ResultadoBibliografico:
        if (sin_clave := self._sin_clave()) is not None:
            return sin_clave

        async def obtener() -> ResultadoBibliografico:
            respuesta = await self._http.get(
                f"{URL_BASE}/works",
                params={
                    **self._params,
                    # Solo el título: con apellidos y año agregados, la búsqueda de OpenAlex
                    # dejó fuera la obra buscada (comprobado con la grabación real, T14-01).
                    # El comparador exige después título, autor y año.
                    "search": consulta.titulo[:500],
                    "per-page": str(CANDIDATOS),
                },
            )
            if respuesta.status_code != 200:
                raise FallaDeServicio(Motivo.ERROR_DEL_SERVICIO)
            resultados = self._diccionario(json_de(respuesta)).get("results")
            if not isinstance(resultados, list):
                raise FallaDeServicio(Motivo.RESPUESTA_INVALIDA)
            candidatos = [metadatos_openalex(o) for o in resultados if isinstance(o, dict)]
            if not candidatos:
                return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.SIN_COINCIDENCIAS)
            return ResultadoBibliografico(
                servicio=self.servicio, estado=Estado.ENCONTRADO, candidatos=candidatos
            )

        return await self._con_cache(consulta.clave(), obtener)
