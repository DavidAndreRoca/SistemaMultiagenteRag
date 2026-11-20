"""Graba respuestas reales de los servicios bibliográficos para las pruebas de contrato (T14).

``python -m pruebas.contrato.grabar`` (con CORREO_POLITE y CLAVE_OPENALEX cargadas; sin la
clave se omite OpenAlex). Hace
pocas consultas, respetando las tasas de cada servicio, y guarda cada respuesta en
``pruebas/contrato/respuestas/``. Antes de guardar:

* se quitan el correo del proyecto y la clave de OpenAlex (y se comprueba que no queden);
* se quitan campos voluminosos que los clientes no usan (la lista de referencias de
  Crossref y de doi.org, el índice del resumen y las obras relacionadas de OpenAlex).

Los DOI son de artículos publicados y de acceso abierto; no hay datos de participantes.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

CARPETA = Path(__file__).parent / "respuestas"
DOI_EXISTENTE = "10.3390/educsci13090856"  # MDPI, CC BY (del corpus provisional)
DOI_INEXISTENTE = "10.9999/sma-no-existe-2026"
CAMPOS_OPENALEX_SOBRANTES = (
    "abstract_inverted_index",
    "referenced_works",
    "related_works",
    "concepts",
    "topics",
    "keywords",
    "counts_by_year",
    "mesh",
    "sustainable_development_goals",
    "grants",
    "locations",
    "indexed_in",
    "corresponding_author_ids",
    "corresponding_institution_ids",
)


def _limpiar(cuerpo: Any, servicio: str) -> Any:
    if isinstance(cuerpo, dict):
        if servicio == "doi":
            cuerpo.pop("reference", None)
        if servicio == "crossref":
            mensaje = cuerpo.get("message")
            if isinstance(mensaje, dict):
                mensaje.pop("reference", None)
                for item in mensaje.get("items", []) or []:
                    if isinstance(item, dict):
                        item.pop("reference", None)
        if servicio == "openalex":
            obras = cuerpo.get("results") if "results" in cuerpo else [cuerpo]
            for obra in obras or []:
                if isinstance(obra, dict):
                    for campo in CAMPOS_OPENALEX_SOBRANTES:
                        obra.pop(campo, None)
                    for autoria in obra.get("authorships", []) or []:
                        if isinstance(autoria, dict):
                            autoria.pop("institutions", None)
                            autoria.pop("affiliations", None)
            cuerpo.pop("meta", None)
    return cuerpo


def _guardar(nombre: str, servicio: str, respuesta: httpx.Response, secretos: list[str]) -> None:
    tipo = respuesta.headers.get("content-type", "")
    cuerpo: Any = _limpiar(respuesta.json(), servicio) if "json" in tipo else respuesta.text
    registro = {
        "servicio": servicio,
        "estado": respuesta.status_code,
        "tipo": tipo.split(";")[0],
        "cuerpo": cuerpo,
    }
    texto = json.dumps(registro, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for secreto in secretos:
        if secreto and secreto in texto:
            raise SystemExit(f"{nombre}: la respuesta contiene un dato del proyecto; no se guarda")
    (CARPETA / f"{nombre}.json").write_text(texto, encoding="utf-8")
    print(f"{nombre}: HTTP {respuesta.status_code}, {len(texto)} caracteres")


async def principal() -> None:
    correo = os.environ.get("CORREO_POLITE", "")
    clave = os.environ.get("CLAVE_OPENALEX", "")
    if not correo:
        raise SystemExit("Falta CORREO_POLITE")
    secretos = [correo, clave]
    CARPETA.mkdir(exist_ok=True)
    agente = {"User-Agent": f"SistemaMultiagenteRag/0.1 (mailto:{correo})"}
    async with httpx.AsyncClient(headers=agente, timeout=30, follow_redirects=True) as http:

        async def pedir(url: str, **kwargs: Any) -> httpx.Response:
            await asyncio.sleep(1.0)  # muy por debajo de la tasa de cada servicio
            return await http.get(url, **kwargs)

        crossref = await pedir(
            f"https://api.crossref.org/works/{DOI_EXISTENTE}", params={"mailto": correo}
        )
        _guardar("crossref_doi_existente", "crossref", crossref, secretos)
        _guardar(
            "crossref_doi_inexistente",
            "crossref",
            await pedir(
                f"https://api.crossref.org/works/{DOI_INEXISTENTE}", params={"mailto": correo}
            ),
            secretos,
        )
        obra = crossref.json()["message"]
        titulo = obra["title"][0]
        apellido = obra["author"][0]["family"]
        anio = obra["issued"]["date-parts"][0][0]
        consulta = f"{titulo} {apellido} {anio}"
        _guardar(
            "crossref_busqueda",
            "crossref",
            await pedir(
                "https://api.crossref.org/works",
                params={"mailto": correo, "query.bibliographic": consulta, "rows": "5"},
            ),
            secretos,
        )
        csl = "application/vnd.citationstyles.csl+json"
        _guardar(
            "doi_csl_existente",
            "doi",
            await pedir(f"https://doi.org/{DOI_EXISTENTE}", headers={"Accept": csl}),
            secretos,
        )
        _guardar(
            "doi_csl_inexistente",
            "doi",
            await pedir(f"https://doi.org/{DOI_INEXISTENTE}", headers={"Accept": csl}),
            secretos,
        )
        _guardar(
            "doi_cita_apa",
            "doi",
            await pedir(
                f"https://doi.org/{DOI_EXISTENTE}",
                headers={"Accept": "text/x-bibliography; style=apa; locale=es-ES"},
            ),
            secretos,
        )
        _guardar(
            "unpaywall_existente",
            "unpaywall",
            await pedir(f"https://api.unpaywall.org/v2/{DOI_EXISTENTE}", params={"email": correo}),
            secretos,
        )
        _guardar(
            "unpaywall_inexistente",
            "unpaywall",
            await pedir(
                f"https://api.unpaywall.org/v2/{DOI_INEXISTENTE}", params={"email": correo}
            ),
            secretos,
        )
        if not clave:
            print("OpenAlex omitido: falta CLAVE_OPENALEX (sin ella, rechaza la consulta)")
            return
        parametros = {"api_key": clave, "mailto": correo}
        _guardar(
            "openalex_doi_existente",
            "openalex",
            await pedir(f"https://api.openalex.org/works/doi:{DOI_EXISTENTE}", params=parametros),
            secretos,
        )
        _guardar(
            "openalex_doi_inexistente",
            "openalex",
            await pedir(f"https://api.openalex.org/works/doi:{DOI_INEXISTENTE}", params=parametros),
            secretos,
        )
        _guardar(
            "openalex_busqueda",
            "openalex",
            await pedir(
                "https://api.openalex.org/works",
                params={**parametros, "search": consulta, "per-page": "5"},
            ),
            secretos,
        )


if __name__ == "__main__":
    asyncio.run(principal())
    sys.exit(0)
