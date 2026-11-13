"""T10: comandos de consola de ingesta y reindexación de punta a punta con la base real.

El canal y el servicio de modelos se sustituyen por dobles; la configuración se lee del
entorno como en el servidor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.configuracion import cargar_ajustes
from app.corpus import fabrica, ingesta, reindexar
from app.corpus.almacen import AlmacenArchivos
from app.corpus.indexacion import Indexador
from pruebas.conftest import SECRETO_PRUEBAS
from pruebas.dobles_corpus import CanalFicticio, EmbeddingsFicticios, contenido
from pruebas.integracion.conftest import consultar

pytestmark = pytest.mark.integracion


@pytest.fixture
def servidor(bd_limpia: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Entorno de un servidor con una cuenta A2 y un tema; devuelve una carpeta con PDF."""
    for variable in ("URL_GROBID", "URL_SERVICIO_MODELOS", "DIRECTORIO_RECURSOS_CORPUS"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("ENTORNO", "pruebas")
    monkeypatch.setenv("URL_BD", bd_limpia)
    monkeypatch.setenv("SECRETO_SESION", SECRETO_PRUEBAS)
    consultar(
        bd_limpia,
        "INSERT INTO cuenta (codigo, hash_contrasena, rol)"
        " VALUES ('INV-01', 'x', 'A2') RETURNING 1",
    )
    consultar(
        bd_limpia, "INSERT INTO coleccion (tipo, tema) VALUES ('cientifica', 'TEMA-A') RETURNING 1"
    )
    carpeta = tmp_path / "entrada"
    carpeta.mkdir()
    (carpeta / "uno.pdf").write_bytes(contenido("TUTORIA"))
    (carpeta / "dos.pdf").write_bytes(contenido("SUENO"))
    return carpeta


def test_ingesta_y_reindexacion_por_consola(
    servidor: Path,
    bd_limpia: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    embeddings = EmbeddingsFicticios()
    monkeypatch.setattr(
        ingesta,
        "crear_indexador",
        lambda _ajustes: Indexador(CanalFicticio(), embeddings, AlmacenArchivos(tmp_path / "a")),
    )
    argumentos = [str(servidor), "--tema", "tema-a", "--investigador", "inv-01"]
    assert ingesta.principal(argumentos) == 0
    salida = capsys.readouterr().out
    assert "Resumen (2 archivos): indexado: 2" in salida
    assert "ansiedad" not in salida  # nunca texto de los documentos
    assert ingesta.principal(argumentos) == 0
    assert "ya_registrado: 2" in capsys.readouterr().out
    assert consultar(
        bd_limpia,
        "SELECT count(*) FROM documento d JOIN cuenta c ON c.id = d.indexado_por_id"
        " WHERE c.codigo = 'INV-01'",
    ) == [(2,)]

    monkeypatch.setattr(
        reindexar,
        "crear_reindexador",
        lambda _ajustes: Indexador(None, EmbeddingsFicticios("rev-2"), None),
    )
    assert reindexar.principal(["--investigador", "INV-01"]) == 0
    assert "Documentos reindexados: 2" in capsys.readouterr().out
    assert reindexar.principal(["--investigador", "INV-01"]) == 0
    assert "Documentos reindexados: 0" in capsys.readouterr().out


def test_errores_de_los_comandos(
    servidor: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Sin GROBID, servicio de modelos ni recursos configurados: mensaje y código 1.
    assert ingesta.principal([str(servidor), "--tema", "TEMA-A", "--investigador", "INV-01"]) == 1
    assert "no está configurada" in capsys.readouterr().err
    assert reindexar.principal(["--investigador", "INV-01"]) == 1
    assert "URL_SERVICIO_MODELOS" in capsys.readouterr().err
    assert (
        ingesta.principal([str(servidor / "no-existe"), "--tema", "T", "--investigador", "I"]) == 2
    )

    monkeypatch.setattr(
        ingesta,
        "crear_indexador",
        lambda _a: Indexador(CanalFicticio(), EmbeddingsFicticios(), AlmacenArchivos(servidor)),
    )
    assert ingesta.principal([str(servidor), "--tema", "TEMA-A", "--investigador", "NADIE"]) == 1
    assert "no es una cuenta de investigador" in capsys.readouterr().err
    assert ingesta.principal([str(servidor), "--tema", "TEMA-Z", "--investigador", "INV-01"]) == 1
    assert "TEMA-Z" in capsys.readouterr().err


def test_la_fabrica_exige_la_configuracion_del_corpus(servidor: Path) -> None:
    ajustes = cargar_ajustes()
    with pytest.raises(fabrica.CorpusNoConfigurado) as error:
        fabrica.crear_indexador(ajustes)
    assert error.value.detalle == {
        "variables": [
            "DIRECTORIO_RECURSOS_CORPUS",
            "URL_GROBID",
            "URL_SERVICIO_MODELOS",
            "DIRECTORIO_ARCHIVOS",
        ]
    }
    con_modelos = ajustes.model_copy(update={"url_servicio_modelos": "http://modelos:8000"})
    assert isinstance(fabrica.crear_reindexador(con_modelos), Indexador)
