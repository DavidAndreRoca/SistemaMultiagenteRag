"""T10: indexación y gestión del corpus con la base real (RF-15, CU-14, CP-21).

El canal de extracción y el servicio de modelos se sustituyen por dobles
(``pruebas/dobles_corpus.py``); el canal real con los PDF de muestra se prueba en
``test_corpus_real.py``.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from app.bd.enumeraciones import Rol
from app.corpus.almacen import AlmacenArchivos
from app.corpus.indexacion import Indexador, Resultado
from app.corpus.ingesta import ingerir_carpeta
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.corpus import Encontrado
from app.repositorios.unidad import UnidadDeTrabajo, fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador
from pruebas.dobles_corpus import CanalFicticio, EmbeddingsFicticios, contenido, vector_de
from pruebas.integracion.conftest import Entorno, consultar, crear_tema

pytestmark = pytest.mark.integracion


@dataclass
class Corpus:
    entorno: Entorno
    cliente: httpx.AsyncClient
    canal: CanalFicticio
    embeddings: EmbeddingsFicticios
    archivos: Path
    contexto: ContextoAcceso

    async def subir(
        self, coleccion_id: str, datos: bytes, nombre: str = "articulo.pdf"
    ) -> httpx.Response:
        return await self.cliente.post(
            f"/investigador/colecciones/{coleccion_id}/documentos",
            files={"archivo": (nombre, datos, "application/pdf")},
        )

    async def coleccion(self, tema: str) -> str:
        await crear_tema(self.cliente, tema)
        colecciones = (await self.cliente.get("/investigador/colecciones")).json()
        return str(next(c["id"] for c in colecciones if c["tema"] == tema))

    async def contadores(self, coleccion_id: str) -> tuple[int, int]:
        colecciones = (await self.cliente.get("/investigador/colecciones")).json()
        fila = next(c for c in colecciones if c["id"] == coleccion_id)
        return fila["n_incluidas"], fila["n_excluidas"]


@pytest.fixture
async def corpus(entorno: Entorno, investigador: httpx.AsyncClient, tmp_path: Path) -> Corpus:
    canal, embeddings = CanalFicticio(), EmbeddingsFicticios()
    indexador = Indexador(canal, embeddings, AlmacenArchivos(tmp_path / "archivos"))
    entorno.aplicacion.state.indexador = indexador
    entorno.aplicacion.state.embebedor = indexador
    ((cuenta_id,),) = consultar(entorno.url_bd, "SELECT id FROM cuenta WHERE codigo = 'INV-01'")
    assert isinstance(cuenta_id, uuid.UUID)
    contexto = ContextoAcceso(cuenta_id=cuenta_id, rol=Rol.INVESTIGADOR, caso_id=None)
    return Corpus(entorno, investigador, canal, embeddings, tmp_path / "archivos", contexto)


async def test_subir_un_pdf_lo_indexa_con_vectores_y_trazabilidad(
    corpus: Corpus, caplog: pytest.LogCaptureFixture
) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    with caplog.at_level(logging.INFO):
        respuesta = await corpus.subir(coleccion, contenido("TUTORIA"), "Tutoría y ansiedad.pdf")
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert (datos["resultado"], datos["fragmentos"]) == ("indexado", 3)
    assert corpus.canal.parametros is not None and corpus.canal.parametros.palabras_minimas == 1500

    documentos = (
        await corpus.cliente.get(f"/investigador/colecciones/{coleccion}/documentos")
    ).json()
    assert len(documentos) == 1
    documento = documentos[0]
    assert documento["id"] == datos["documento_id"]
    assert (documento["estado"], documento["fragmentos"], documento["confirmado"]) == (
        "activo",
        3,
        False,
    )
    assert documento["archivo_original"] == "Tutoría y ansiedad.pdf"
    assert documento["autores"] == [{"nombres": "Ana", "apellidos": "Prueba Ficticia"}]
    assert await corpus.contadores(coleccion) == (1, 0)

    filas = consultar(
        corpus.entorno.url_bd,
        "SELECT d.modelo_embeddings, d.revision_embeddings, c.codigo, d.ruta_archivo,"
        " (SELECT count(*) FROM fragmento f WHERE f.documento_id = d.id"
        "  AND f.embedding IS NOT NULL AND f.coleccion_id = d.coleccion_id)"
        " FROM documento d JOIN cuenta c ON c.id = d.indexado_por_id",
    )
    modelo, revision, quien, ruta, con_vector = filas[0]
    assert (modelo, revision, quien, con_vector) == (
        "ficticio/bolsa-de-palabras",
        "rev-1",
        "INV-01",
        3,
    )
    assert isinstance(ruta, str) and (corpus.archivos / ruta).is_file()
    assert "Tutoría" not in ruta  # nombre aleatorio
    # El registro no lleva texto del documento (4.6).
    registro = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert "ansiedad ante la estadística" not in registro and "indexado" in registro


async def test_reingerir_el_mismo_pdf_no_duplica_documentos_ni_fragmentos(corpus: Corpus) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    assert (await corpus.subir(coleccion, contenido("TUTORIA"))).status_code == 201
    segunda = await corpus.subir(coleccion, contenido("TUTORIA"), "copia.pdf")
    assert segunda.status_code == 200
    assert segunda.json()["resultado"] == "ya_registrado"
    assert corpus.canal.procesados == 1  # el mismo archivo no se vuelve a procesar
    assert consultar(corpus.entorno.url_bd, "SELECT count(*) FROM documento") == [(1,)]
    assert consultar(corpus.entorno.url_bd, "SELECT count(*) FROM fragmento") == [(3,)]
    assert consultar(corpus.entorno.url_bd, "SELECT count(*) FROM exclusion_corpus") == [(0,)]


async def test_cp21_duplicado_por_texto_o_por_doi_se_rechaza_con_motivo(corpus: Corpus) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    original = (await corpus.subir(coleccion, contenido("TUTORIA", "DOI=10.5555/x.1"))).json()
    # Otro archivo con el mismo texto (por ejemplo, la versión de un repositorio).
    por_texto = await corpus.subir(coleccion, contenido("TUTORIA", "otra copia"), "repo.pdf")
    # Otro texto con el mismo DOI.
    por_doi = await corpus.subir(coleccion, contenido("SUENO", "DOI=10.5555/x.1"), "doi.pdf")
    for respuesta in (por_texto, por_doi):
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert (datos["resultado"], datos["motivos"]) == ("duplicado", ["duplicado"])
        assert datos["documento_id"] == original["documento_id"]
    exclusiones = (
        await corpus.cliente.get(f"/investigador/colecciones/{coleccion}/exclusiones")
    ).json()
    assert [(e["identificador"], e["motivo"]) for e in exclusiones] == [
        ("repo.pdf", "duplicado"),
        ("doi.pdf", "duplicado"),
    ]
    assert all(
        e["duplicado_de_id"] == original["documento_id"] and e["mensaje"] for e in exclusiones
    )
    assert await corpus.contadores(coleccion) == (1, 2)


async def test_cp21_escaneado_e_ilegible_se_rechazan_con_motivo_una_sola_vez(
    corpus: Corpus,
) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    escaneado = await corpus.subir(coleccion, contenido("ESCANEADO"), "escaneado.pdf")
    ilegible = await corpus.subir(coleccion, contenido("ILEGIBLE"), "danado.pdf")
    assert escaneado.status_code == ilegible.status_code == 200
    assert escaneado.json()["motivos"] == ["sin_capa_de_texto"]
    assert ilegible.json()["motivos"] == ["pdf_ilegible"]
    assert escaneado.json()["mensajes"] and escaneado.json()["fragmentos"] == 0
    otra_vez = await corpus.subir(coleccion, contenido("ESCANEADO"), "escaneado.pdf")
    assert otra_vez.json()["resultado"] == "ya_registrado"
    exclusiones = (
        await corpus.cliente.get(f"/investigador/colecciones/{coleccion}/exclusiones")
    ).json()
    assert [e["motivo"] for e in exclusiones] == ["sin_capa_de_texto", "pdf_ilegible"]
    assert consultar(corpus.entorno.url_bd, "SELECT count(*) FROM documento") == [(0,)]
    assert await corpus.contadores(coleccion) == (0, 2)


async def test_un_incompleto_se_indexa_solo_al_confirmarlo_y_conserva_la_marca(
    corpus: Corpus,
) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    respuesta = await corpus.subir(coleccion, contenido("INCOMPLETO"), "corto.pdf")
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert (datos["resultado"], datos["motivos"]) == ("incompleto", ["texto_insuficiente"])
    assert await corpus.contadores(coleccion) == (0, 0)
    assert consultar(
        corpus.entorno.url_bd, "SELECT count(*) FROM fragmento WHERE embedding IS NOT NULL"
    ) == [(0,)]
    assert await _densa(corpus, coleccion, "tutoría ansiedad") == []

    confirmado = await corpus.cliente.post(
        f"/investigador/documentos/{datos['documento_id']}/confirmar"
    )
    assert confirmado.status_code == 200, confirmado.text
    vista = confirmado.json()
    assert (vista["estado"], vista["confirmado"], vista["motivo_estado"]) == (
        "incompleto",
        True,
        "texto_insuficiente",
    )
    assert await corpus.contadores(coleccion) == (1, 0)
    assert len(await _densa(corpus, coleccion, "tutoría ansiedad")) == 1

    otra_vez = await corpus.cliente.post(
        f"/investigador/documentos/{datos['documento_id']}/confirmar"
    )
    assert (otra_vez.status_code, otra_vez.json()["codigo"]) == (409, "estado_no_permite")


async def test_retirar_deja_de_recuperarse_y_conserva_el_registro(corpus: Corpus) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    documento_id = (await corpus.subir(coleccion, contenido("TUTORIA"))).json()["documento_id"]
    assert len(await _lexica(corpus, coleccion, "ansiedad")) == 2

    retirado = await corpus.cliente.post(f"/investigador/documentos/{documento_id}/retirar")
    assert retirado.status_code == 200
    assert retirado.json()["estado"] == "retirado" and retirado.json()["retirado_en"]
    assert await corpus.contadores(coleccion) == (0, 0)
    assert await _lexica(corpus, coleccion, "ansiedad") == []
    assert await _densa(corpus, coleccion, "tutoría ansiedad") == []
    assert consultar(corpus.entorno.url_bd, "SELECT count(*) FROM fragmento") == [(3,)]

    otra_vez = await corpus.cliente.post(f"/investigador/documentos/{documento_id}/retirar")
    assert otra_vez.status_code == 409
    # Retirado sigue registrado: volver a subirlo no lo duplica.
    assert (await corpus.subir(coleccion, contenido("TUTORIA"))).json()["resultado"] == (
        "ya_registrado"
    )


async def test_consultas_densa_y_lexica_devuelven_fragmentos_de_la_coleccion_indicada(
    corpus: Corpus,
) -> None:
    tema_a, tema_b = await corpus.coleccion("TEMA-A"), await corpus.coleccion("TEMA-B")
    await corpus.subir(tema_a, contenido("TUTORIA"))
    await corpus.subir(tema_b, contenido("SUENO"))
    await corpus.subir(
        tema_b, contenido("TUTORIA", "copia en otro tema")
    )  # otro tema: no es duplicado

    densa = await _densa(corpus, tema_a, "la tutoría entre pares reduce la ansiedad")
    assert densa[0].fragmento.seccion_normalizada.value == "introduccion"
    assert (densa[0].fragmento.seccion_original, densa[0].fragmento.pagina_inicio) == (
        "1. Introducción",
        1,
    )
    assert {e.fragmento.coleccion_id for e in densa} == {uuid.UUID(tema_a)}
    assert densa[0].puntaje > densa[-1].puntaje

    lexica = await _lexica(corpus, tema_b, "sleep")
    assert lexica and {e.fragmento.coleccion_id for e in lexica} == {uuid.UUID(tema_b)}
    assert all(e.fragmento.pagina_inicio and e.fragmento.seccion_original for e in lexica)
    assert all("sleep" in e.fragmento.texto.lower() for e in lexica)
    assert await _lexica(corpus, tema_a, "sleep") == []


async def test_reindexar_vuelve_a_embeber_solo_lo_desactualizado(corpus: Corpus) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    await corpus.subir(coleccion, contenido("TUTORIA"))
    await corpus.subir(coleccion, contenido("SUENO"))
    indexador: Indexador = corpus.entorno.aplicacion.state.indexador
    async with corpus.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        assert await indexador.reindexar(unidad, corpus.contexto) == 0
        corpus.embeddings.revision = "rev-2"
        assert await indexador.reindexar(unidad, corpus.contexto) == 2
        assert await indexador.reindexar(unidad, corpus.contexto) == 0
        assert await indexador.reindexar(unidad, corpus.contexto, forzar=True) == 2
    assert consultar(
        corpus.entorno.url_bd, "SELECT DISTINCT revision_embeddings FROM documento"
    ) == [("rev-2",)]


async def test_solo_colecciones_cientificas_existentes(corpus: Corpus) -> None:
    inexistente = uuid.uuid4()
    for ruta in (
        f"/investigador/colecciones/{inexistente}/documentos",
        f"/investigador/colecciones/{inexistente}/exclusiones",
    ):
        assert (await corpus.cliente.get(ruta)).status_code == 404
    assert (await corpus.subir(str(inexistente), contenido("TUTORIA"))).status_code == 404
    assert (
        await corpus.cliente.post(f"/investigador/documentos/{inexistente}/retirar")
    ).status_code == 404
    # El corpus de guías se segmenta por apartado (T22): en T10 no se sube nada a él.
    ((guias,),) = consultar(
        corpus.entorno.url_bd, "INSERT INTO coleccion (tipo) VALUES ('guias') RETURNING id::text"
    )
    assert (await corpus.subir(str(guias), contenido("TUTORIA"))).status_code == 404


async def test_un_pdf_mas_grande_que_el_limite_se_rechaza_sin_procesarlo(corpus: Corpus) -> None:
    coleccion = await corpus.coleccion("TEMA-A")
    cambiar = (
        "UPDATE configuracion SET parametros ="
        " jsonb_set(parametros, '{tamano_max_pdf_mb}', %s::jsonb) RETURNING 1"
    )
    consultar(corpus.entorno.url_bd, cambiar, "1")
    try:
        grande = b"%PDF-1.4\n" + b"0" * (1024 * 1024)
        respuesta = await corpus.subir(coleccion, grande, "grande.pdf")
    finally:
        consultar(corpus.entorno.url_bd, cambiar, "25")  # la limpieza no restaura parámetros
    assert (respuesta.status_code, respuesta.json()["codigo"]) == (413, "archivo_demasiado_grande")
    assert corpus.canal.procesados == 0


async def test_sin_configuracion_del_corpus_la_subida_responde_503(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> None:
    await crear_tema(investigador, "TEMA-A")
    coleccion = (await investigador.get("/investigador/colecciones")).json()[0]["id"]
    respuesta = await investigador.post(
        f"/investigador/colecciones/{coleccion}/documentos",
        files={"archivo": ("a.pdf", contenido("TUTORIA"), "application/pdf")},
    )
    assert respuesta.status_code == 503
    datos = respuesta.json()
    assert datos["codigo"] == "corpus_no_configurado"
    assert "URL_GROBID" in datos["detalle"]["variables"]


async def test_comando_de_ingesta_es_idempotente(corpus: Corpus, tmp_path: Path) -> None:
    await corpus.coleccion("TEMA-A")
    carpeta = tmp_path / "entrada"
    carpeta.mkdir()
    for nombre, datos in {
        "a_tutoria.pdf": contenido("TUTORIA"),
        "b_sueno.pdf": contenido("SUENO"),
        "c_corto.pdf": contenido("INCOMPLETO"),
        "d_escaneado.pdf": contenido("ESCANEADO"),
        "e_repetido.pdf": contenido("TUTORIA", "otra copia"),
        "notas.txt": b"no es un pdf de la carpeta",
    }.items():
        (carpeta / nombre).write_bytes(datos)
    indexador: Indexador = corpus.entorno.aplicacion.state.indexador
    abrir = fabrica_de_unidades(corpus.entorno.aplicacion.state.fabrica_sesiones)
    lineas: list[str] = []

    primera = await ingerir_carpeta(
        abrir, indexador, corpus.contexto, "TEMA-A", carpeta, lineas.append
    )
    assert primera == Counter({"indexado": 2, "incompleto": 1, "excluido": 1, "duplicado": 1})
    assert len(lineas) == 5 and all("ansiedad" not in linea for linea in lineas)
    segunda = await ingerir_carpeta(
        abrir, indexador, corpus.contexto, "TEMA-A", carpeta, lineas.append
    )
    assert segunda == Counter({"ya_registrado": 5})
    assert consultar(corpus.entorno.url_bd, "SELECT count(*) FROM documento") == [(3,)]
    assert consultar(corpus.entorno.url_bd, "SELECT count(*) FROM exclusion_corpus") == [(2,)]


async def test_el_contexto_de_consola_exige_una_cuenta_de_investigador(corpus: Corpus) -> None:
    async with corpus.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        contexto = await contexto_de_investigador(unidad, "inv-01")
        assert contexto == corpus.contexto
        with pytest.raises(CuentaNoValida):
            await contexto_de_investigador(unidad, "NO-EXISTE")


async def _densa(corpus: Corpus, coleccion: str, consulta: str) -> list[Encontrado]:
    async with corpus.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        return await UnidadDeTrabajo(sesion).corpus.buscar_denso(
            corpus.contexto, uuid.UUID(coleccion), vector_de(consulta), 5
        )


async def _lexica(corpus: Corpus, coleccion: str, consulta: str) -> list[Encontrado]:
    async with corpus.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        return await UnidadDeTrabajo(sesion).corpus.buscar_lexico(
            corpus.contexto, uuid.UUID(coleccion), consulta, 5
        )


def test_los_resultados_de_la_ingesta_son_un_contrato_estable() -> None:
    assert [r.value for r in Resultado] == [
        "indexado",
        "incompleto",
        "excluido",
        "duplicado",
        "ya_registrado",
    ]
