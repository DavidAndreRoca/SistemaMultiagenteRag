"""Ingesta del corpus de guías con la base real (T22): indexación, duplicados, rúbrica y
recuperación por tipo de solicitud."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.bd.enumeraciones import Rol, TipoAutoria, TipoSolicitud
from app.casos import servicio as casos
from app.corpus.guias import RubricaNoIndexable, coleccion_guias, indexar_guia, leer_guia
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.integracion.conftest import Entorno, consultar

pytestmark = pytest.mark.integracion

PROVISIONALES = Path(__file__).parents[2] / "guias" / "provisionales"


async def _contextos(unidad: UnidadDeTrabajo) -> tuple[ContextoAcceso, ContextoAcceso]:
    inv = await unidad.autenticacion.cuenta_por_codigo("INV-01")
    assert inv is not None
    investigador = ContextoAcceso(inv.id, Rol.INVESTIGADOR, None)
    await casos.crear_coleccion_cientifica(unidad, investigador, "TEMA-A")
    creado = await casos.crear_caso(
        unidad, investigador, "CASO-A", TipoAutoria.INDIVIDUAL, "TEMA-A"
    )
    await unidad.confirmar()
    cuenta = await unidad.autenticacion.cuenta_por_codigo(creado.credenciales[0].codigo)
    assert cuenta is not None
    return investigador, ContextoAcceso(cuenta.id, Rol.CASO, creado.caso.id)


async def test_las_guias_se_indexan_una_vez_y_se_recuperan_para_d1(entorno: Entorno) -> None:
    await entorno.crear_investigador()
    embeddings = EmbeddingsFicticios()
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        investigador, caso = await _contextos(unidad)
        coleccion = await coleccion_guias(unidad, investigador)
        guia = leer_guia(PROVISIONALES / "guia-estructura-imrad.md")
        estado, documento_id = await indexar_guia(unidad, investigador, coleccion, guia, embeddings)
        await unidad.confirmar()
        assert estado == "indexada" and documento_id is not None
        # La misma guía no se duplica, y la colección de guías es una sola.
        assert (await indexar_guia(unidad, investigador, coleccion, guia, embeddings))[
            0
        ] == "duplicada"
        assert (await coleccion_guias(unidad, investigador)).id == coleccion.id
        # D1 recupera de las guías; la búsqueda de evidencia, no (solo científica y personal).
        vector = (await embeddings.embeber(["alineación problema objetivos hipótesis"])).vectores[0]
        para_d1 = await unidad.recuperacion.buscar_denso(
            caso, TipoSolicitud.REVISION_ESTRUCTURA, vector, 5
        )
        para_d4 = await unidad.recuperacion.buscar_denso(
            caso, TipoSolicitud.BUSQUEDA_EVIDENCIA, vector, 5
        )
        assert len(para_d1) == 5 and para_d4 == []
    apartados = consultar(
        entorno.url_bd,
        "SELECT DISTINCT seccion_original FROM fragmento WHERE documento_id = %s",
        documento_id,
    )
    assert ("Alineación entre problema, objetivos e hipótesis",) in apartados


async def test_intentar_indexar_la_rubrica_falla(entorno: Entorno, tmp_path: Path) -> None:
    await entorno.crear_investigador()
    rubrica = tmp_path / "rubrica-articulo.md"
    rubrica.write_bytes(b"---\ntitulo: Criterios\n---\n\n## Puntajes\n\nCriterio 1: 4 puntos.\n")
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        investigador, _ = await _contextos(unidad)
        coleccion = await coleccion_guias(unidad, investigador)
        with pytest.raises(RubricaNoIndexable):
            await indexar_guia(
                unidad, investigador, coleccion, leer_guia(rubrica), EmbeddingsFicticios()
            )
    assert consultar(entorno.url_bd, "SELECT count(*) FROM documento") == [(0,)]
