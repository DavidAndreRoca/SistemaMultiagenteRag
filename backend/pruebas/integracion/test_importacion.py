"""T15: importador de referencias del artículo O1 con la base real (RF-20, RN-18, RN-19).

GROBID responde con sus respuestas reales grabadas; Crossref, Unpaywall, OpenAlex, las
descargas y el canal de T10 se simulan (``pruebas/dobles_importacion.py``). El artículo
O1 y sus 24 referencias son ficticios (``pruebas/datos/articulo_o1.py``).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.corpus.almacen import AlmacenArchivos
from app.corpus.indexacion import Indexador
from app.importacion.servicio import CARPETA, Importador
from app.repositorios.unidad import fabrica_de_unidades
from pruebas.datos import articulo_o1 as o1
from pruebas.datos.articulo_o1 import REFERENCIAS, Escenario
from pruebas.dobles_corpus import CanalFicticio, EmbeddingsFicticios, contenido
from pruebas.dobles_importacion import DOI_DATACITE, Contador, crear_importador, doi_de
from pruebas.integracion.conftest import Entorno, consultar, crear_tema

pytestmark = pytest.mark.integracion

DATOS = Path(__file__).parents[1] / "datos"
TIPO_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
E = Escenario
ESPERADO = {
    E.INCLUIDA: ("incluida", None),
    E.POR_METADATOS: ("incluida", None),
    E.DESCARGA_403: ("pendiente_pdf", "descarga_fallida"),
    E.DESCARGA_HTML: ("pendiente_pdf", "descarga_fallida"),
    E.SIN_ENLACE_DIRECTO: ("pendiente_pdf", "sin_enlace_directo"),
    E.CERRADA: ("excluida", "sin_acceso_abierto"),
    E.SIN_UNPAYWALL: ("excluida", "sin_acceso_abierto"),
    E.NO_LOCALIZADA: ("excluida", "no_localizada"),
    E.SIN_DOI: ("excluida", "sin_doi"),
    E.ESCANEADA: ("excluida", "sin_capa_de_texto"),
    E.CAIDA: ("no_comprobable", "crossref_error_del_servicio"),
}
# Partes de texto que solo están en el cuerpo del artículo: no deben quedar en ningún lado.
SOLO_DEL_ARTICULO = ("nunca debe quedar guardada", "un artículo O1 ficticio")


@dataclass
class Importacion:
    entorno: Entorno
    cliente: httpx.AsyncClient
    importador: Importador
    canal: CanalFicticio
    servicios: Contador
    descargas: Contador
    archivos: Path
    carpetas_al_localizar: list[list[Path]]

    async def coleccion(self, tema: str = "TEMA-A") -> str:
        await crear_tema(self.cliente, tema)
        colecciones = (await self.cliente.get("/investigador/colecciones")).json()
        return str(next(c["id"] for c in colecciones if c["tema"] == tema))

    async def importar(
        self,
        coleccion: str,
        *,
        archivo: tuple[str, bytes, str] | None = None,
        dois: str | None = None,
    ) -> dict[str, Any]:
        respuesta = await self.cliente.post(
            f"/investigador/colecciones/{coleccion}/importaciones",
            files={"archivo": archivo} if archivo else None,
            data={"dois": dois} if dois else None,
        )
        assert respuesta.status_code == 202, respuesta.text
        assert respuesta.json()["estado"] == "en_cola"
        await self.importador.esperar()
        final = await self.cliente.get(f"/investigador/importaciones/{respuesta.json()['id']}")
        datos: dict[str, Any] = final.json()
        return datos

    async def importar_docx(self, coleccion: str) -> dict[str, Any]:
        datos = (DATOS / "o1" / "articulo_o1.docx").read_bytes()
        return await self.importar(coleccion, archivo=("Mi artículo.docx", datos, TIPO_DOCX))

    async def importar_pdf(self, coleccion: str) -> dict[str, Any]:
        datos = (DATOS / "o1" / "articulo_o1.pdf").read_bytes()
        return await self.importar(coleccion, archivo=("Mi artículo.pdf", datos, "application/pdf"))

    async def informe(self, coleccion: str) -> dict[str, Any]:
        datos: dict[str, Any] = (
            await self.cliente.get(f"/investigador/colecciones/{coleccion}/informe")
        ).json()
        return datos

    async def referencias(self, coleccion: str, estado: str | None = None) -> list[dict[str, Any]]:
        datos: list[dict[str, Any]] = (
            await self.cliente.get(
                f"/investigador/colecciones/{coleccion}/referencias",
                params={"estado": estado} if estado else None,
            )
        ).json()
        return datos


@pytest.fixture
async def importacion(
    entorno: Entorno, investigador: httpx.AsyncClient, tmp_path: Path
) -> Importacion:
    archivos = tmp_path / "archivos"
    canal = CanalFicticio()
    indexador = Indexador(canal, EmbeddingsFicticios(), AlmacenArchivos(archivos))
    carpetas: list[list[Path]] = []

    def antes_de_localizar() -> None:  # RN-19: el artículo ya no está al resolver
        base = archivos / CARPETA
        carpetas.append(sorted(base.rglob("*")) if base.exists() else [])

    importador, servicios, descargas = crear_importador(
        fabrica_de_unidades(entorno.aplicacion.state.fabrica_sesiones),
        indexador,
        archivos,
        entorno.reloj,
        antes_de_localizar=antes_de_localizar,
    )
    entorno.aplicacion.state.indexador = indexador
    entorno.aplicacion.state.importador = importador
    return Importacion(
        entorno, investigador, importador, canal, servicios, descargas, archivos, carpetas
    )


def _por_referencia(referencias: list[dict[str, Any]]) -> dict[E, Counter[tuple[str, Any]]]:
    """Agrupa las referencias guardadas por el escenario ficticio que les corresponde."""
    agrupadas: dict[E, Counter[tuple[str, Any]]] = {}
    for fila in referencias:
        ficticia = next(r for r in REFERENCIAS if r.titulo.lower() in fila["texto"].lower())
        agrupadas.setdefault(ficticia.escenario, Counter())[(fila["estado"], fila["motivo"])] += 1
    return agrupadas


async def test_importar_el_docx_arma_el_informe_con_cada_resultado(
    importacion: Importacion,
) -> None:
    coleccion = await importacion.coleccion()
    final = await importacion.importar_docx(coleccion)
    assert (final["estado"], final["origen"], final["total"], final["procesadas"]) == (
        "terminada",
        "docx",
        24,
        24,
    )

    referencias = await importacion.referencias(coleccion)
    assert len(referencias) == 24
    cantidades = Counter(r.escenario for r in REFERENCIAS)
    for escenario, resultado in _por_referencia(referencias).items():
        assert resultado == Counter({ESPERADO[escenario]: cantidades[escenario]}), escenario

    informe = await importacion.informe(coleccion)
    assert {k: v for k, v in informe.items() if k not in ("coleccion_id", "tema")} == {
        "referencias": 24,
        "de_acceso_abierto": 15,  # 9 incluidas, 5 pendientes y la escaneada
        "incluidas": 9,
        "pendientes_pdf": 5,
        "no_comprobables": 2,
        "excluidas": 8,
        "excluidas_por_motivo": {
            "no_localizada": 2,
            "sin_acceso_abierto": 4,
            "sin_capa_de_texto": 1,
            "sin_doi": 1,
        },
        "documentos_recuperables": 9,
        "exclusiones_del_corpus": 8,  # 7 referencias y el PDF escaneado
    }
    colecciones = (await importacion.cliente.get("/investigador/colecciones")).json()
    fila = next(c for c in colecciones if c["id"] == coleccion)
    assert (fila["n_incluidas"], fila["n_excluidas"], fila["n_pendientes"]) == (9, 8, 5)

    # Los documentos llevan los metadatos de Crossref y de Unpaywall.
    documentos = consultar(
        importacion.entorno.url_bd,
        "SELECT doi, origen, estado_oa, licencia, url_acceso_abierto, revista_editorial"
        " FROM documento ORDER BY doi",
    )
    esperados = sorted(
        doi_de(r) or "" for r in REFERENCIAS if r.escenario in (E.INCLUIDA, E.POR_METADATOS)
    )
    assert [d[0] for d in documentos] == esperados
    assert {d[1:4] for d in documentos} == {("importacion_o1", "gold", "cc-by")}
    assert all(str(d[4]).startswith("https://repositorio.example/") for d in documentos)
    assert {d[5] for d in documentos} >= {"Revista Ficticia de Pedagogía"}

    pendientes = await importacion.referencias(coleccion, "pendiente_pdf")
    assert len(pendientes) == 5
    assert all(p["url_acceso_abierto"] for p in pendientes)

    exclusiones = consultar(
        importacion.entorno.url_bd,
        "SELECT objeto, motivo, count(*) FROM exclusion_corpus GROUP BY objeto, motivo",
    )
    assert set(exclusiones) == {
        ("referencia", "sin_acceso_abierto", 4),
        ("referencia", "no_localizada", 2),
        ("referencia", "sin_doi", 1),
        ("archivo", "sin_capa_de_texto", 1),
    }


async def test_rn19_no_queda_copia_del_articulo_ni_en_disco_ni_en_la_base(
    importacion: Importacion, caplog: pytest.LogCaptureFixture
) -> None:
    coleccion = await importacion.coleccion()
    with caplog.at_level(logging.INFO):
        assert (await importacion.importar_docx(coleccion))["estado"] == "terminada"
        final_pdf = await importacion.importar_pdf(coleccion)
    assert (final_pdf["estado"], final_pdf["origen"]) == ("terminada", "pdf")

    # Al resolver la primera referencia, la carpeta del artículo ya estaba vacía.
    assert importacion.carpetas_al_localizar
    assert all(carpeta == [] for carpeta in importacion.carpetas_al_localizar)
    restos = [p for p in (importacion.archivos / CARPETA).rglob("*") if p.is_file()]
    assert restos == []
    # Solo quedan los PDF de las referencias indexadas, en el almacén del corpus.
    guardados = [p for p in importacion.archivos.rglob("*") if p.is_file()]
    assert len(guardados) == 9
    assert all(p.parent.name == "corpus" for p in guardados)
    assert all(o1.FRASE_DEL_CUERPO.encode() not in p.read_bytes() for p in guardados)

    # Ninguna fila de ninguna tabla tiene texto del cuerpo ni el título del artículo.
    url = importacion.entorno.url_bd
    tablas = [
        fila[0]
        for fila in consultar(url, "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    ]
    assert "referencia_importada" in tablas and "documento" in tablas
    for tabla in tablas:
        for parte in SOLO_DEL_ARTICULO:
            ((cantidad,),) = consultar(
                url, f'SELECT count(*) FROM "{tabla}" AS t WHERE t::text ILIKE %s', f"%{parte}%"
            )
            assert cantidad == 0, (tabla, parte)
    # Ni el nombre del archivo ni su huella se guardan; el artículo no es un documento.
    for tabla in tablas:
        ((cantidad,),) = consultar(
            url, f'SELECT count(*) FROM "{tabla}" AS t WHERE t::text ILIKE %s', "%Mi artículo%"
        )
        assert cantidad == 0, tabla
    assert consultar(url, "SELECT count(*) FROM documento WHERE origen <> 'importacion_o1'") == [
        (0,)
    ]
    # El registro no lleva texto del artículo (4.6).
    registro = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert all(parte not in registro for parte in SOLO_DEL_ARTICULO)
    assert "importacion de referencias" in registro


async def test_reimportar_no_duplica_y_solo_reintenta_lo_pendiente(
    importacion: Importacion,
) -> None:
    coleccion = await importacion.coleccion()
    await importacion.importar_docx(coleccion)
    procesados = importacion.canal.procesados
    descargas = len(importacion.descargas.peticiones)
    antes = await importacion.informe(coleccion)

    segunda = await importacion.importar_docx(coleccion)
    assert (segunda["estado"], segunda["total"], segunda["procesadas"]) == ("terminada", 24, 24)
    assert await importacion.informe(coleccion) == antes
    assert importacion.canal.procesados == procesados  # nada se volvió a indexar
    # Solo se reintentan las dos descargas fallidas (403 y HTML).
    assert len(importacion.descargas.peticiones) == descargas + 2
    assert consultar(importacion.entorno.url_bd, "SELECT count(*) FROM documento") == [(9,)]
    assert consultar(importacion.entorno.url_bd, "SELECT count(*) FROM exclusion_corpus") == [(8,)]


async def test_lista_de_dois(importacion: Importacion) -> None:
    coleccion = await importacion.coleccion()
    final = await importacion.importar(
        coleccion,
        dois="https://doi.org/10.5555/SMA.O1.01\n10.5555/sma.o1.13, no-es-un-doi\n"
        f"10.5555/sma.o1.01\n10.5555/sma.o1.17\n{DOI_DATACITE}",
    )
    assert (final["estado"], final["origen"], final["total"], final["procesadas"]) == (
        "terminada",
        "doi",
        5,
        5,
    )
    exclusiones = consultar(importacion.entorno.url_bd, "SELECT count(*) FROM exclusion_corpus")
    otra_vez = await importacion.importar(coleccion, dois="no-es-un-doi\n10.5555/sma.o1.13")
    assert (otra_vez["total"], otra_vez["procesadas"]) == (2, 2)
    assert (
        consultar(importacion.entorno.url_bd, "SELECT count(*) FROM exclusion_corpus")
        == exclusiones
    )
    estados = {
        (r["doi"], r["estado"], r["motivo"]) for r in await importacion.referencias(coleccion)
    }
    assert estados == {
        ("10.5555/sma.o1.01", "incluida", None),
        ("10.5555/sma.o1.17", "incluida", None),
        # DataCite: solo OpenAlex la conoce y da su acceso abierto (Unpaywall no la tiene).
        (DOI_DATACITE, "pendiente_pdf", "sin_enlace_directo"),
        ("10.5555/sma.o1.13", "excluida", "sin_acceso_abierto"),
        (None, "excluida", "doi_invalido"),
    }
    assert (await importacion.informe(coleccion))["excluidas_por_motivo"] == {
        "doi_invalido": 1,
        "sin_acceso_abierto": 1,
    }
    # Un DOI que ya tiene documento en la colección no se descarga otra vez: la referencia
    # sin DOI del .docx que la búsqueda resuelve a 10.5555/sma.o1.17 usa ese documento.
    antes = len(importacion.descargas.peticiones)
    await importacion.importar_docx(coleccion)
    assert not any("sma.o1.17" in str(p.url) for p in importacion.descargas.peticiones[antes:])
    documentos = {
        r["documento_id"]
        for r in await importacion.referencias(coleccion)
        if r["doi"] == "10.5555/sma.o1.17"
    }
    assert len(documentos) == 1 and None not in documentos


async def test_articulo_no_valido_falla_y_tambien_se_borra(importacion: Importacion) -> None:
    coleccion = await importacion.coleccion()
    final = await importacion.importar(
        coleccion, archivo=("articulo.pdf", b"esto no es un pdf", "application/pdf")
    )
    assert (final["estado"], final["error"], final["total"]) == ("fallida", "articulo_no_valido", 0)
    assert [p for p in (importacion.archivos / CARPETA).rglob("*") if p.is_file()] == []

    ruta = f"/investigador/colecciones/{coleccion}/importaciones"
    texto = await importacion.cliente.post(ruta, files={"archivo": ("a.txt", b"x", "text/plain")})
    assert (texto.status_code, texto.json()["codigo"]) == (422, "formato_no_admitido")
    vacia = await importacion.cliente.post(ruta, data={"dois": "  "})
    assert (vacia.status_code, vacia.json()["codigo"]) == (422, "entrada_no_valida")
    ambas = await importacion.cliente.post(
        ruta,
        files={"archivo": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        data={"dois": "10.5555/sma.o1.01"},
    )
    assert (ambas.status_code, ambas.json()["codigo"]) == (422, "entrada_no_valida")
    otra = await importacion.cliente.post(
        f"/investigador/colecciones/{uuid.uuid4()}/importaciones", data={"dois": "10.5555/x.1"}
    )
    assert otra.status_code == 404


async def test_subir_el_pdf_de_una_pendiente_la_incluye(importacion: Importacion) -> None:
    coleccion = await importacion.coleccion()
    await importacion.importar_docx(coleccion)
    pendiente = next(
        p
        for p in await importacion.referencias(coleccion, "pendiente_pdf")
        if p["motivo"] == "sin_enlace_directo"
    )
    pdf = contenido("TUTORIA", f"VARIANTE=manual DOI={pendiente['doi']}")
    respuesta = await importacion.cliente.post(
        f"/investigador/referencias/{pendiente['id']}/pdf",
        files={"archivo": ("bajado.pdf", pdf, "application/pdf")},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert (respuesta.json()["estado"], respuesta.json()["motivo"]) == ("incluida", None)
    informe = await importacion.informe(coleccion)
    assert (
        informe["incluidas"],
        informe["pendientes_pdf"],
        informe["documentos_recuperables"],
    ) == (
        10,
        4,
        10,
    )
    ((origen, doi),) = consultar(
        importacion.entorno.url_bd,
        "SELECT origen, doi FROM documento WHERE id = %s",
        uuid.UUID(respuesta.json()["documento_id"]),
    )
    assert (origen, doi) == ("importacion_o1", pendiente["doi"])

    # Una referencia que ya no está pendiente no recibe otro PDF.
    otra = await importacion.cliente.post(
        f"/investigador/referencias/{pendiente['id']}/pdf",
        files={"archivo": ("bajado.pdf", pdf, "application/pdf")},
    )
    assert (otra.status_code, otra.json()["codigo"]) == (409, "estado_no_permite")
    # Un escaneado queda excluido con el motivo de T10.
    siguiente = next(
        p
        for p in await importacion.referencias(coleccion, "pendiente_pdf")
        if p["motivo"] == "sin_enlace_directo"
    )
    escaneado = await importacion.cliente.post(
        f"/investigador/referencias/{siguiente['id']}/pdf",
        files={"archivo": ("bajado.pdf", contenido("ESCANEADO", "manual"), "application/pdf")},
    )
    assert (escaneado.json()["estado"], escaneado.json()["motivo"]) == (
        "excluida",
        "sin_capa_de_texto",
    )


async def test_una_importacion_cortada_se_marca_interrumpida(importacion: Importacion) -> None:
    coleccion = await importacion.coleccion()
    ((importacion_id,),) = consultar(
        importacion.entorno.url_bd,
        "INSERT INTO importacion_referencias (coleccion_id, origen, estado)"
        " VALUES (%s, 'pdf', 'en_proceso') RETURNING id",
        uuid.UUID(coleccion),
    )
    respuesta = await importacion.cliente.get(f"/investigador/importaciones/{importacion_id}")
    assert respuesta.json()["estado"] == "interrumpida"
    assert respuesta.json()["terminada_en"] is not None
