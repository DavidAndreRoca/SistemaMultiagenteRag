"""Fixtures de integración: base PostgreSQL propia y migrada, aplicación y clientes.

Cada ejecución crea una base ``sma_prueba_<aleatorio>`` en el servidor de
``URL_BD_PRUEBAS``, aplica las migraciones y la borra al final: nunca toca la base de
desarrollo. Entre pruebas se vacían las tablas y se restaura la configuración semilla.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy.engine import make_url

from app.configuracion import cargar_ajustes
from app.main import crear_aplicacion
from app.repositorios.unidad import UnidadDeTrabajo
from app.seguridad.crear_investigador import crear_cuenta_investigador
from pruebas.conftest import variables_base

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
CONTRASENA_NUEVA = "contrasena-ficticia-de-pruebas-01"
TABLAS_CONSERVADAS = {"alembic_version", "configuracion"}
# Parámetros de la versión 1 tal como los deja la migración, para restaurarlos entre pruebas.
_PARAMETROS_SEMILLA: dict[str, str] = {}


def _conninfo(url: str) -> str:
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def configuracion_alembic(url: str) -> Config:
    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "migraciones"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    cfg.attributes["configurar_registro"] = False
    return cfg


@pytest.fixture(scope="session")
def servidor_pruebas() -> str:
    url = os.environ.get("URL_BD_PRUEBAS")
    if url:
        return url
    if os.environ.get("CI") == "true":
        pytest.fail("URL_BD_PRUEBAS no está definida en la integración continua")
    pytest.skip("URL_BD_PRUEBAS no definida: levante la base con docker compose (ver README)")


@pytest.fixture(scope="session")
def base_temporal(servidor_pruebas: str) -> Iterator[str]:
    """Crea una base vacía y devuelve su URL. Se borra al terminar la sesión de pruebas."""
    nombre = f"sma_prueba_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(_conninfo(servidor_pruebas), autocommit=True) as conexion:
        conexion.execute(f'CREATE DATABASE "{nombre}"')
    url = make_url(servidor_pruebas).set(database=nombre).render_as_string(hide_password=False)
    try:
        yield url
    finally:
        with psycopg.connect(_conninfo(servidor_pruebas), autocommit=True) as conexion:
            conexion.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')


@pytest.fixture(scope="session")
def url_bd_migrada(base_temporal: str) -> str:
    command.upgrade(configuracion_alembic(base_temporal), "head")
    with psycopg.connect(_conninfo(base_temporal)) as conexion:
        fila = conexion.execute(
            "SELECT parametros::text FROM configuracion WHERE numero_version = 1"
        ).fetchone()
    assert fila is not None
    _PARAMETROS_SEMILLA[base_temporal] = fila[0]
    return base_temporal


@pytest.fixture
def bd_limpia(url_bd_migrada: str) -> str:
    """Vacía las tablas y restaura la configuración semilla antes de cada prueba."""
    with psycopg.connect(_conninfo(url_bd_migrada), autocommit=True) as conexion:
        tablas = [
            fila[0]
            for fila in conexion.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()
            if fila[0] not in TABLAS_CONSERVADAS
        ]
        if tablas:
            conexion.execute("TRUNCATE " + ", ".join(f'"{t}"' for t in tablas) + " CASCADE")
        conexion.execute("DELETE FROM configuracion WHERE numero_version <> 1")
        conexion.execute(
            "UPDATE configuracion SET vigente = true, congelada = false,"
            " parametros = CAST(%s AS jsonb)",
            (_PARAMETROS_SEMILLA[url_bd_migrada],),
        )
    return url_bd_migrada


def consultar(url: str, sql: str, *parametros: object) -> list[tuple[object, ...]]:
    """Lectura directa para comprobar el estado de la base desde las pruebas."""
    with psycopg.connect(_conninfo(url)) as conexion:
        return list(conexion.execute(sql, parametros).fetchall())  # type: ignore[arg-type]


@dataclass
class RelojFicticio:
    ahora: datetime = field(default_factory=lambda: datetime(2026, 11, 6, 12, 0, tzinfo=UTC))

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta: float) -> None:
        self.ahora += timedelta(**delta)


@dataclass
class Entorno:
    aplicacion: FastAPI
    reloj: RelojFicticio
    url_bd: str

    def cliente(self) -> httpx.AsyncClient:
        transporte = httpx.ASGITransport(app=self.aplicacion, raise_app_exceptions=False)
        return httpx.AsyncClient(transport=transporte, base_url="https://sma.test")

    async def crear_investigador(self, codigo: str = "INV-01") -> str:
        async with self.aplicacion.state.fabrica_sesiones() as sesion:
            contrasena = await crear_cuenta_investigador(UnidadDeTrabajo(sesion), codigo)
        assert contrasena is not None
        return contrasena


@pytest.fixture
async def entorno(bd_limpia: str, tmp_path: Path) -> AsyncIterator[Entorno]:
    # DIRECTORIO_ARCHIVOS: la carga de borradores (T11) guarda allí cada versión.
    variables = variables_base(URL_BD=bd_limpia, DIRECTORIO_ARCHIVOS=str(tmp_path / "archivos"))
    aplicacion = crear_aplicacion(cargar_ajustes(variables))
    reloj = RelojFicticio()
    aplicacion.state.reloj = reloj
    async with aplicacion.router.lifespan_context(aplicacion):
        yield Entorno(aplicacion=aplicacion, reloj=reloj, url_bd=bd_limpia)


async def iniciar_sesion(
    cliente: httpx.AsyncClient, codigo: str, contrasena: str
) -> httpx.Response:
    """Inicia sesión y deja la cabecera CSRF lista en el cliente."""
    respuesta = await cliente.post("/sesion", json={"codigo": codigo, "contrasena": contrasena})
    if respuesta.status_code == 200:
        cliente.headers["X-CSRF-Token"] = respuesta.json()["csrf"]
    return respuesta


async def entrar_y_cambiar(
    cliente: httpx.AsyncClient, codigo: str, contrasena_inicial: str
) -> httpx.AsyncClient:
    respuesta = await iniciar_sesion(cliente, codigo, contrasena_inicial)
    assert respuesta.status_code == 200, respuesta.text
    cambio = await cliente.post(
        "/sesion/contrasena",
        json={"contrasena_actual": contrasena_inicial, "contrasena_nueva": CONTRASENA_NUEVA},
    )
    assert cambio.status_code == 204, cambio.text
    return cliente


@pytest.fixture
async def investigador(entorno: Entorno) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente con sesión de investigador (A2) y contraseña ya cambiada."""
    contrasena = await entorno.crear_investigador()
    async with entorno.cliente() as cliente:
        yield await entrar_y_cambiar(cliente, "INV-01", contrasena)


async def crear_tema(investigador: httpx.AsyncClient, tema: str) -> None:
    respuesta = await investigador.post(
        "/investigador/colecciones/cientificas", json={"tema": tema}
    )
    assert respuesta.status_code == 201, respuesta.text


async def crear_caso(
    investigador: httpx.AsyncClient, codigo: str, tema: str, autoria: str = "individual"
) -> dict[str, object]:
    respuesta = await investigador.post(
        "/investigador/casos", json={"codigo": codigo, "tipo_autoria": autoria, "tema": tema}
    )
    assert respuesta.status_code == 201, respuesta.text
    datos: dict[str, object] = respuesta.json()
    return datos


def primera_credencial(caso: dict[str, object]) -> tuple[str, str]:
    credenciales = caso["credenciales"]
    assert isinstance(credenciales, list)
    return credenciales[0]["cuenta"], credenciales[0]["contrasena_inicial"]


# Escenario de recuperación compartido por T16 y T18 (al final: importa Entorno de aquí).
from pruebas.integracion.escenario_rag import escenario  # noqa: E402, F401


async def esperar_orquestador(entorno: Entorno) -> None:
    """Espera las solicitudes que la API lanzó en su proceso (T28, solo en pruebas)."""
    orquestador = entorno.aplicacion.state.orquestador
    if orquestador is not None:
        await orquestador.esperar()
