from __future__ import annotations

import httpx
import pytest

from app import diagnostico
from app.configuracion import cargar_ajustes
from pruebas.conftest import variables_base

CLAVE_GROQ = "gsk_clave_de_prueba_no_real"
CLAVE_OPENALEX = "oa_clave_de_prueba_no_real"


def cliente_simulado(estado_groq: int, estado_openalex: int) -> httpx.Client:
    def manejador(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.host == "api.groq.com":
            assert peticion.headers["Authorization"] == f"Bearer {CLAVE_GROQ}"
            return httpx.Response(estado_groq, json={})
        if peticion.url.host == "api.openalex.org":
            assert peticion.url.params["api_key"] == CLAVE_OPENALEX
            return httpx.Response(estado_openalex, json={})
        raise AssertionError(f"host inesperado {peticion.url.host}")

    return httpx.Client(transport=httpx.MockTransport(manejador))


def ajustes_con_claves() -> object:
    return cargar_ajustes(
        variables_base(
            CLAVE_GROQ=CLAVE_GROQ, CLAVE_OPENALEX=CLAVE_OPENALEX, CORREO_POLITE="p@example.org"
        )
    )


def test_ambas_claves_validas() -> None:
    ajustes = cargar_ajustes(
        variables_base(
            CLAVE_GROQ=CLAVE_GROQ, CLAVE_OPENALEX=CLAVE_OPENALEX, CORREO_POLITE="p@example.org"
        )
    )
    resultados = diagnostico.ejecutar_diagnostico(ajustes, cliente_simulado(200, 200))
    assert [r.ok for r in resultados] == [True, True]


def test_clave_rechazada_se_informa_sin_imprimir_la_clave() -> None:
    ajustes = cargar_ajustes(variables_base(CLAVE_GROQ=CLAVE_GROQ, CLAVE_OPENALEX=CLAVE_OPENALEX))
    resultados = diagnostico.ejecutar_diagnostico(ajustes, cliente_simulado(401, 403))
    assert [r.ok for r in resultados] == [False, False]
    assert "401" in resultados[0].detalle
    assert all(CLAVE_GROQ not in r.detalle and CLAVE_OPENALEX not in r.detalle for r in resultados)


def test_claves_ausentes() -> None:
    ajustes = cargar_ajustes(variables_base())
    cliente = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
    resultados = diagnostico.ejecutar_diagnostico(ajustes, cliente)
    assert [r.ok for r in resultados] == [False, False]
    assert "CLAVE_GROQ" in resultados[0].detalle
    assert "CLAVE_OPENALEX" in resultados[1].detalle


def test_error_de_red_no_se_confunde_con_clave_invalida() -> None:
    def falla(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    ajustes = cargar_ajustes(variables_base(CLAVE_GROQ=CLAVE_GROQ, CLAVE_OPENALEX=CLAVE_OPENALEX))
    resultados = diagnostico.ejecutar_diagnostico(
        ajustes, httpx.Client(transport=httpx.MockTransport(falla))
    )
    assert all("sin conexión" in r.detalle for r in resultados)


def test_comando_sale_con_error_si_falta_configuracion(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for nombre in ("ENTORNO", "URL_BD", "SECRETO_SESION"):
        monkeypatch.delenv(nombre, raising=False)
    assert diagnostico.principal([]) == 1
    assert "ERROR" in capsys.readouterr().err
