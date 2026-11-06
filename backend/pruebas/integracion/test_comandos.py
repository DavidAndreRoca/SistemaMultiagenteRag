"""Comandos de línea: alta del investigador y semillas ficticias (con base real)."""

from __future__ import annotations

import pytest

from app.bd import semillas
from app.seguridad import crear_investigador
from pruebas.conftest import SECRETO_PRUEBAS
from pruebas.integracion.conftest import consultar

pytestmark = pytest.mark.integracion


@pytest.fixture
def entorno_cli(bd_limpia: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("ENTORNO", "pruebas")
    monkeypatch.setenv("URL_BD", bd_limpia)
    monkeypatch.setenv("SECRETO_SESION", SECRETO_PRUEBAS)
    return bd_limpia


def test_crear_investigador_imprime_la_contrasena_una_vez(
    entorno_cli: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert crear_investigador.principal(["inv-07"]) == 0
    salida = capsys.readouterr().out
    assert "INV-07" in salida and "Contraseña inicial" in salida
    contrasena = salida.rsplit(": ", 1)[1].strip()
    assert contrasena not in str(consultar(entorno_cli, "SELECT * FROM cuenta"))
    assert crear_investigador.principal(["INV-07"]) == 1  # repetido
    assert "ya existe" in capsys.readouterr().err
    assert crear_investigador.principal(["con espacios"]) == 1


def test_crear_investigador_sin_configuracion(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for nombre in ("ENTORNO", "URL_BD", "SECRETO_SESION"):
        monkeypatch.delenv(nombre, raising=False)
    assert crear_investigador.principal(["INV-01"]) == 1
    assert "ERROR" in capsys.readouterr().err


def test_semillas_por_linea_de_comandos(
    entorno_cli: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert semillas.principal() == 0
    assert "CASO-DEV-02-2" in capsys.readouterr().out
    assert semillas.principal() == 0
    assert "ya existían" in capsys.readouterr().out


def test_semillas_se_niegan_en_produccion(
    entorno_cli: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ENTORNO", "produccion")
    monkeypatch.setenv("SECRETO_SESION", "p" * 40)
    monkeypatch.setenv("CORREO_POLITE", "proyecto@example.org")
    monkeypatch.setenv("CLAVE_OPENALEX", "k")
    assert semillas.principal() == 1
    assert "producción" in capsys.readouterr().err
    assert consultar(entorno_cli, "SELECT count(*) FROM caso") == [(0,)]
