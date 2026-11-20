"""Cliente de doi.org por negociación de contenido: metadatos CSL-JSON y cita formateada.

La cita la da el registro del DOI (Crossref, DataCite o mEDRA) en un estilo CSL: es
determinista y no interviene ningún modelo de lenguaje (RN-17).
"""

from __future__ import annotations

from typing import Any

from app.bibliografia.base import ClienteBase, anio_de_partes, autores_csl, doi_en_ruta, texto
from app.bibliografia.http import FallaDeServicio, json_de
from app.bibliografia.modelos import (
    Estado,
    MetadatosBibliograficos,
    Motivo,
    ResultadoBibliografico,
    Servicio,
)
from app.bibliografia.normalizacion import normalizar_doi

URL_BASE = "https://doi.org"
CSL_JSON = "application/vnd.citationstyles.csl+json"
TIPOS_DE_CITA = frozenset({"text/x-bibliography", "text/plain"})
# Normas de citación de la configuración (D-12) y su estilo CSL en citation.crosscite.org.
ESTILOS_CSL = {"apa7": "apa", "ieee": "ieee", "vancouver": "vancouver"}


def estilo_csl(norma: str) -> str | None:
    return ESTILOS_CSL.get(norma.strip().lower())


def metadatos_csl(datos: dict[str, Any]) -> MetadatosBibliograficos:
    return MetadatosBibliograficos(
        doi=normalizar_doi(texto(datos.get("DOI"))),
        titulo=texto(datos.get("title")),
        autores=autores_csl(datos.get("author")),
        anio=anio_de_partes(datos.get("issued"))
        or anio_de_partes(datos.get("published-print"))
        or anio_de_partes(datos.get("published-online")),
        revista=texto(datos.get("container-title")),
        volumen=texto(datos.get("volume")),
        numero=texto(datos.get("issue")),
        paginas=texto(datos.get("page")),
        editorial=texto(datos.get("publisher")),
        tipo=texto(datos.get("type")),
    )


class ClienteDoi(ClienteBase):
    servicio = Servicio.DOI

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        normal = self._doi_valido(doi)
        if normal is None:
            return self._doi_invalido()

        async def obtener() -> ResultadoBibliografico:
            respuesta = await self._http.get(
                f"{URL_BASE}/{doi_en_ruta(normal)}", headers={"Accept": CSL_JSON}
            )
            if respuesta.status_code == 404:
                return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.NO_EXISTE)
            if respuesta.status_code != 200:
                raise FallaDeServicio(Motivo.ERROR_DEL_SERVICIO)
            return ResultadoBibliografico(
                servicio=self.servicio,
                estado=Estado.ENCONTRADO,
                metadatos=metadatos_csl(self._diccionario(json_de(respuesta))),
            )

        return await self._con_cache(normal, obtener)

    async def cita(self, doi: str, estilo: str, idioma: str = "es-ES") -> ResultadoBibliografico:
        normal = self._doi_valido(doi)
        if normal is None:
            return self._doi_invalido()

        async def obtener() -> ResultadoBibliografico:
            respuesta = await self._http.get(
                f"{URL_BASE}/{doi_en_ruta(normal)}",
                headers={"Accept": f"text/x-bibliography; style={estilo}; locale={idioma}"},
            )
            if respuesta.status_code == 404:
                return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.NO_EXISTE)
            if respuesta.status_code != 200:
                raise FallaDeServicio(Motivo.ERROR_DEL_SERVICIO)
            # Solo una bibliografía en texto es una cita: una página HTML (un portal o un
            # error del proxy) no lo es, aunque llegue con 200.
            tipo = respuesta.headers.get("content-type", "").split(";")[0].strip().lower()
            if tipo not in TIPOS_DE_CITA:
                raise FallaDeServicio(Motivo.RESPUESTA_INVALIDA)
            cita = " ".join(respuesta.text.split())
            if not cita:
                raise FallaDeServicio(Motivo.RESPUESTA_INVALIDA)
            return ResultadoBibliografico(
                servicio=self.servicio, estado=Estado.ENCONTRADO, cita=cita
            )

        return await self._con_cache(f"{normal}|{estilo}|{idioma}", obtener)
