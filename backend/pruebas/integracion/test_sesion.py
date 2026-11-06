"""T06: inicio de sesión, cookies, bloqueo, expiración, límite de sesiones y contraseña."""

from __future__ import annotations

import json

import pytest

from app.seguridad.servicio import MENSAJE_CREDENCIALES
from pruebas.integracion.conftest import (
    CONTRASENA_NUEVA,
    Entorno,
    consultar,
    entrar_y_cambiar,
    iniciar_sesion,
)

pytestmark = pytest.mark.integracion


async def test_inicio_correcto_pone_cookies_seguras(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        respuesta = await iniciar_sesion(cliente, "inv-01", contrasena)  # admite minúsculas
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["rol"] == "A2"
    assert cuerpo["debe_cambiar_contrasena"] is True
    cookies = respuesta.headers.get_list("set-cookie")
    sesion = next(c for c in cookies if c.startswith("sma_sesion="))
    csrf = next(c for c in cookies if c.startswith("sma_csrf="))
    for atributo in ("HttpOnly", "Secure", "SameSite=lax"):
        assert atributo.lower() in sesion.lower()
    assert "secure" in csrf.lower() and "httponly" not in csrf.lower()


async def test_mensaje_identico_para_cuenta_inexistente_y_contrasena_erronea(
    entorno: Entorno,
) -> None:
    await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        inexistente = await iniciar_sesion(cliente, "NO-EXISTE", "x")
        erronea = await iniciar_sesion(cliente, "INV-01", "contrasena-incorrecta")
    assert inexistente.status_code == erronea.status_code == 401
    assert inexistente.json()["mensaje"] == erronea.json()["mensaje"] == MENSAJE_CREDENCIALES
    assert inexistente.json()["codigo"] == erronea.json()["codigo"]


async def test_la_contrasena_no_aparece_en_la_base_ni_en_el_registro(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        await iniciar_sesion(cliente, "INV-01", "otra-contrasena-erronea-123")
        await entrar_y_cambiar(cliente, "INV-01", contrasena)
    volcado = json.dumps(
        [list(map(str, f)) for f in consultar(entorno.url_bd, "SELECT * FROM cuenta")]
    )
    registro = capsys.readouterr().out
    for secreto in (contrasena, CONTRASENA_NUEVA, "otra-contrasena-erronea-123"):
        assert secreto not in volcado
        assert secreto not in registro
    assert "$argon2id$" in volcado


async def test_bloqueo_tras_cinco_fallos_en_quince_minutos(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        for _ in range(5):
            entorno.reloj.avanzar(minutes=2)
            assert (await iniciar_sesion(cliente, "INV-01", "erronea")).status_code == 401
        # Bloqueada: ni la contraseña correcta entra, con el mismo mensaje genérico.
        bloqueada = await iniciar_sesion(cliente, "INV-01", contrasena)
        assert bloqueada.status_code == 401
        assert bloqueada.json()["mensaje"] == MENSAJE_CREDENCIALES
        entorno.reloj.avanzar(minutes=14)
        assert (await iniciar_sesion(cliente, "INV-01", contrasena)).status_code == 401
        entorno.reloj.avanzar(minutes=2)  # pasó el bloqueo de 15 minutos
        assert (await iniciar_sesion(cliente, "INV-01", contrasena)).status_code == 200


async def test_fallos_fuera_de_la_ventana_no_bloquean(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        for _ in range(4):
            assert (await iniciar_sesion(cliente, "INV-01", "erronea")).status_code == 401
        entorno.reloj.avanzar(minutes=16)  # la ventana de 15 minutos se reinicia
        for _ in range(4):
            assert (await iniciar_sesion(cliente, "INV-01", "erronea")).status_code == 401
        assert (await iniciar_sesion(cliente, "INV-01", contrasena)).status_code == 200


async def test_sesion_inactiva_60_minutos_deja_de_valer(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        await iniciar_sesion(cliente, "INV-01", contrasena)
        entorno.reloj.avanzar(minutes=59)
        assert (await cliente.get("/sesion")).status_code == 200  # renueva la actividad
        entorno.reloj.avanzar(minutes=59)
        assert (await cliente.get("/sesion")).status_code == 200
        entorno.reloj.avanzar(minutes=60)
        vencida = await cliente.get("/sesion")
    assert vencida.status_code == 401
    assert vencida.json()["codigo"] == "sesion_invalida"


async def test_expiracion_absoluta_de_8_horas(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        await iniciar_sesion(cliente, "INV-01", contrasena)
        for _ in range(8):  # actividad constante cada 50 minutos
            entorno.reloj.avanzar(minutes=50)
            assert (await cliente.get("/sesion")).status_code == 200
        entorno.reloj.avanzar(minutes=81)  # 8 h 1 min desde el inicio
        assert (await cliente.get("/sesion")).status_code == 401


async def test_tercera_sesion_cierra_la_mas_antigua(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    clientes = [entorno.cliente() for _ in range(3)]
    try:
        for cliente in clientes:
            entorno.reloj.avanzar(seconds=1)
            assert (await iniciar_sesion(cliente, "INV-01", contrasena)).status_code == 200
        estados = [(await c.get("/sesion")).status_code for c in clientes]
    finally:
        for cliente in clientes:
            await cliente.aclose()
    assert estados == [401, 200, 200]
    abiertas = consultar(entorno.url_bd, "SELECT count(*) FROM sesion WHERE cerrada_en IS NULL")
    assert abiertas == [(2,)]


async def test_cambio_obligatorio_de_contrasena_inicial(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        await iniciar_sesion(cliente, "INV-01", contrasena)
        pendiente = await cliente.get("/investigador/casos")
        assert pendiente.status_code == 403
        assert pendiente.json()["codigo"] == "cambio_contrasena_requerido"
        corta = await cliente.post(
            "/sesion/contrasena",
            json={"contrasena_actual": contrasena, "contrasena_nueva": "corta"},
        )
        assert corta.status_code == 422
        mal_actual = await cliente.post(
            "/sesion/contrasena",
            json={"contrasena_actual": "no-es", "contrasena_nueva": CONTRASENA_NUEVA},
        )
        assert mal_actual.status_code == 422
        ok = await cliente.post(
            "/sesion/contrasena",
            json={"contrasena_actual": contrasena, "contrasena_nueva": CONTRASENA_NUEVA},
        )
        assert ok.status_code == 204
        assert (await cliente.get("/investigador/casos")).status_code == 200
        assert (await cliente.get("/sesion")).json()["debe_cambiar_contrasena"] is False
    async with entorno.cliente() as otro:
        assert (await iniciar_sesion(otro, "INV-01", contrasena)).status_code == 401
        assert (await iniciar_sesion(otro, "INV-01", CONTRASENA_NUEVA)).status_code == 200


async def test_cambio_de_contrasena_cierra_las_demas_sesiones(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as primero, entorno.cliente() as segundo:
        await iniciar_sesion(primero, "INV-01", contrasena)
        await entrar_y_cambiar(segundo, "INV-01", contrasena)
        assert (await primero.get("/sesion")).status_code == 401
        assert (await segundo.get("/sesion")).status_code == 200


async def test_operaciones_que_modifican_exigen_csrf(entorno: Entorno) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        await iniciar_sesion(cliente, "INV-01", contrasena)
        valido = cliente.headers.pop("X-CSRF-Token")
        sin_csrf = await cliente.delete("/sesion")
        assert sin_csrf.status_code == 403
        assert sin_csrf.json()["codigo"] == "csrf_invalido"
        falso = await cliente.delete("/sesion", headers={"X-CSRF-Token": "0" * 64})
        assert falso.status_code == 403
        assert (await cliente.get("/sesion")).status_code == 200  # la sesión sigue viva
        cierre = await cliente.delete("/sesion", headers={"X-CSRF-Token": valido})
        assert cierre.status_code == 204
        assert (await cliente.get("/sesion")).status_code == 401


async def test_sin_sesion_responde_401_con_formato_comun(entorno: Entorno) -> None:
    async with entorno.cliente() as cliente:
        respuesta = await cliente.get("/sesion")
        cliente.cookies.set("sma_sesion", "inventada", domain="sma.test")
        con_cookie_falsa = await cliente.get("/sesion")
    assert respuesta.status_code == 401
    assert set(respuesta.json()) == {"codigo", "mensaje", "incidencia_id"}
    assert con_cookie_falsa.status_code == 401


async def test_eventos_de_seguridad_registrados(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
) -> None:
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        await iniciar_sesion(cliente, "INV-01", "erronea")
        await iniciar_sesion(cliente, "INV-01", contrasena)
        await cliente.delete("/sesion")
    acciones = [
        json.loads(linea).get("accion")
        for linea in capsys.readouterr().out.splitlines()
        if '"tipo_evento": "seguridad"' in linea
    ]
    assert {"fallo", "inicio", "cierre"} <= set(acciones)
