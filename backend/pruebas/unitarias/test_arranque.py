"""Sin una variable obligatoria la aplicación no arranca y lo informa."""

from __future__ import annotations

import pytest

from app import __main__ as arranque
from app.configuracion import ErrorConfiguracion
from app.main import crear_aplicacion


def test_crear_aplicacion_sin_variables_lanza_error_de_configuracion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for nombre in ("ENTORNO", "URL_BD", "SECRETO_SESION"):
        monkeypatch.delenv(nombre, raising=False)
    with pytest.raises(ErrorConfiguracion, match="URL_BD"):
        crear_aplicacion()


def test_comando_de_arranque_sale_con_1_y_nombra_la_variable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ENTORNO", "pruebas")
    monkeypatch.delenv("URL_BD", raising=False)
    monkeypatch.delenv("SECRETO_SESION", raising=False)
    assert arranque.principal() == 1
    error = capsys.readouterr().err
    assert "URL_BD" in error
    assert "SECRETO_SESION" in error
