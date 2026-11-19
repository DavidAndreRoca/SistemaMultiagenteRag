"""T10: ingesta con el canal real (Docling y tokenizador) y la base real: CP-21.

Marca ``corpus`` (extra ``corpus`` y recursos en ``DIRECTORIO_RECURSOS_CORPUS``) y
necesita ``URL_BD_PRUEBAS``. GROBID se sustituye por sus cabeceras grabadas y el
servicio de modelos por los embeddings de bolsa de palabras.

Los siete PDF ficticios de muestra cubren los casos de CP-21: dos artículos indexados,
dos incompletos, un escaneado y un cifrado rechazados con motivo, y un duplicado (el PDF
con solo restricción de permisos tiene el mismo texto que el documento corto).
"""

from __future__ import annotations

import importlib.util
import os
import uuid
from collections import Counter
from pathlib import Path

import httpx
import pytest

from app.administracion.parametros import parametros_iniciales
from app.bd.enumeraciones import Rol
from app.corpus.almacen import AlmacenArchivos
from app.corpus.extraccion import CanalPdf, ParametrosCanal
from app.corpus.indexacion import Indexador
from app.corpus.ingesta import ingerir_carpeta
from app.corpus.recursos import problemas
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo, fabrica_de_unidades
from pruebas.datos import textos_muestra as t
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.integracion.conftest import Entorno, consultar, crear_tema
from pruebas.integracion.test_canal_pdf import GrobidGrabado

pytestmark = [pytest.mark.corpus, pytest.mark.integracion]

PDF = Path(__file__).resolve().parents[1] / "datos" / "pdf"
RECURSOS = os.environ.get("DIRECTORIO_RECURSOS_CORPUS", "")


@pytest.fixture
def canal_real() -> CanalPdf:
    if importlib.util.find_spec("docling") is None:
        pytest.skip("falta el extra corpus (Docling)")
    if not RECURSOS or problemas(Path(RECURSOS)):
        pytest.skip("DIRECTORIO_RECURSOS_CORPUS sin recursos verificados")
    from app.corpus.extractor_docling import ExtractorDocling
    from app.corpus.tokenizador import ContadorTokensBgeM3

    recursos = Path(RECURSOS)
    return CanalPdf(
        ExtractorDocling(recursos),
        GrobidGrabado(),
        ContadorTokensBgeM3(recursos),
        ParametrosCanal.desde(parametros_iniciales()),
    )


async def test_cp21_ingesta_de_los_pdf_de_muestra(
    entorno: Entorno, investigador: httpx.AsyncClient, canal_real: CanalPdf, tmp_path: Path
) -> None:
    await crear_tema(investigador, "TEMA-MUESTRA")
    ((cuenta_id,),) = consultar(entorno.url_bd, "SELECT id FROM cuenta WHERE codigo = 'INV-01'")
    assert isinstance(cuenta_id, uuid.UUID)
    contexto = ContextoAcceso(cuenta_id=cuenta_id, rol=Rol.INVESTIGADOR, caso_id=None)
    indexador = Indexador(canal_real, EmbeddingsFicticios(), AlmacenArchivos(tmp_path))
    abrir = fabrica_de_unidades(entorno.aplicacion.state.fabrica_sesiones)
    lineas: list[str] = []

    primera = await ingerir_carpeta(abrir, indexador, contexto, "TEMA-MUESTRA", PDF, lineas.append)
    assert primera == Counter({"indexado": 2, "incompleto": 2, "excluido": 2, "duplicado": 1}), (
        lineas
    )
    # Cada línea: "[i/n % | transcurrido | restante] resultado archivo | ...".
    por_archivo = {
        linea.split("] ", 1)[1].split()[1]: linea.split("] ", 1)[1].split()[0]
        for linea in lineas
        if linea.startswith("[")
    }
    assert por_archivo == {
        "articulo_en.pdf": "indexado",
        "articulo_es.pdf": "indexado",
        "cifrado.pdf": "excluido",
        "documento_corto.pdf": "incompleto",
        "escaneado.pdf": "excluido",
        "sin_secciones_imrad.pdf": "incompleto",
        "solo_permisos.pdf": "duplicado",
    }

    # Reingerir la carpeta no duplica nada.
    segunda = await ingerir_carpeta(abrir, indexador, contexto, "TEMA-MUESTRA", PDF, lineas.append)
    assert segunda == Counter({"ya_registrado": 7})
    assert consultar(entorno.url_bd, "SELECT count(*) FROM documento") == [(4,)]
    assert consultar(
        entorno.url_bd, "SELECT motivo, identificador FROM exclusion_corpus ORDER BY identificador"
    ) == [
        ("pdf_cifrado", "cifrado.pdf"),
        ("sin_capa_de_texto", "escaneado.pdf"),
        ("duplicado", "solo_permisos.pdf"),
    ]

    # Consultas de prueba sobre el corpus real: sección y páginas de la colección indicada.
    coleccion = (await investigador.get("/investigador/colecciones")).json()[0]
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        lexica = await unidad.corpus.buscar_lexico(
            contexto, uuid.UUID(coleccion["id"]), "tutoría ansiedad", 5
        )
    assert lexica
    assert {e.documento.doi for e in lexica} == {"10.5555/rfes.2026.0042"}
    assert all(e.fragmento.seccion_original and e.fragmento.pagina_inicio >= 1 for e in lexica)
    textos = " ".join(e.fragmento.texto for e in lexica)
    assert t.SOLO_EN_REFERENCIAS_ES not in textos
    assert (coleccion["n_incluidas"], coleccion["n_excluidas"]) == (2, 3)
