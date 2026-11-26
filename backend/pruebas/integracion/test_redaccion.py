"""Propuesta de redacción de un párrafo con la base real y el modelo simulado (T27; CP-09,
CP-10, RN-07, RN-17, aislamiento)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.agentes.redaccion import AgenteRedaccion, AtencionRedaccion
from app.bd.enumeraciones import TipoSolicitud
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from app.repositorios.unidad import fabrica_de_unidades
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.dobles_rag import ReordenadorFicticio
from pruebas.integracion.conftest import Entorno, consultar
from pruebas.integracion.test_estructura import _caso, _guias

pytestmark = pytest.mark.integracion

PARRAFO = (
    "La ansiedad ante la estadística reduce el rendimiento. ¿La tutoría entre pares"
    " reduce esa ansiedad en estudiantes de primer año?"
)
PROPUESTA = (
    "La ansiedad ante la estadística disminuye el rendimiento académico. ¿La tutoría entre"
    " pares reduce esa ansiedad en estudiantes de primer año?"
)


@dataclass
class Modelo:
    entradas: list[EntradaModelo] = field(default_factory=list)
    propuesta: str = PROPUESTA

    def redaccion(self, entrada: EntradaModelo) -> dict[str, Any]:
        self.entradas.append(entrada)
        return {
            "original": "Un original que el modelo copió mal.",  # el sistema lo reemplaza
            "propuesta": self.propuesta,
            "cambios": [
                {
                    "tipo": "fluidez_y_precision_lexica",
                    "antes": "reduce el rendimiento",
                    "despues": "disminuye el rendimiento académico",
                    "razon": "Se evita repetir el verbo de la pregunta.",
                    "citas": ["F1"],
                }
            ],
            "notas_para_el_estudiante": ["Para la estructura, pida la revisión de estructura."],
        }

    def cadena(self) -> CadenaModelos:
        async def sin_espera(_: float) -> None:
            return None

        simulado = ProveedorSimulado(
            respuestas={
                "JuicioSuficiencia": lambda _: {"suficiente": True, "motivo": "Pautas pertinentes."},
                "PropuestaRedaccion": self.redaccion,
            }
        )
        return CadenaModelos(
            [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
            dormir=sin_espera,
        )


@dataclass
class Redaccion:
    entorno: Entorno
    cliente: httpx.AsyncClient
    modelo: Modelo
    atencion: AtencionRedaccion

    async def parrafos(self) -> dict[str, Any]:
        respuesta = await self.cliente.get("/caso/redaccion/parrafos")
        assert respuesta.status_code == 200, respuesta.text
        datos: dict[str, Any] = respuesta.json()
        return datos

    async def id_de(self, inicio: str) -> str:
        return next(
            p["id"] for p in (await self.parrafos())["parrafos"] if p["texto"].startswith(inicio)
        )

    async def pedir(self, parrafo_id: str) -> httpx.Response:
        respuesta = await self.cliente.post("/caso/redaccion", json={"parrafo_id": parrafo_id})
        await self.atencion.esperar()
        return respuesta

    async def ver(self, solicitud_id: str) -> dict[str, Any]:
        respuesta = await self.cliente.get(f"/caso/redaccion/{solicitud_id}")
        assert respuesta.status_code == 200, respuesta.text
        datos: dict[str, Any] = respuesta.json()
        return datos


def _atencion(entorno: Entorno, modelo: Modelo) -> AtencionRedaccion:
    cadena = modelo.cadena()
    servicio = ServicioEvidencia(
        Recuperador(EmbeddingsFicticios(), ReordenadorFicticio()),
        cadena,
        lambda: datetime(2026, 11, 26, 12, tzinfo=UTC),
    )
    agente = AgenteRedaccion(
        servicio, cadena, versiones=lambda: {"suficiencia": "v1", "redaccion": "v1"}
    )
    atencion = AtencionRedaccion(
        TipoSolicitud.PROPUESTA_REDACCION,
        agente,
        fabrica_de_unidades(entorno.aplicacion.state.fabrica_sesiones),
        entorno.reloj,
    )
    entorno.aplicacion.state.atencion_redaccion = atencion
    return atencion


@pytest.fixture
async def redaccion(entorno: Entorno, investigador: httpx.AsyncClient) -> AsyncIterator[Redaccion]:
    consultar(
        entorno.url_bd,
        "UPDATE configuracion SET parametros = jsonb_set(parametros, '{suficiencia_tau}',"
        " '0.01') WHERE vigente RETURNING id",
    )
    await _guias(entorno)
    cliente = await _caso(entorno, investigador, "CASO-A")
    modelo = Modelo()
    yield Redaccion(entorno, cliente, modelo, _atencion(entorno, modelo))
    await cliente.aclose()


async def test_lista_los_parrafos_del_cuerpo_sin_titulos_ni_referencias(
    redaccion: Redaccion,
) -> None:
    datos = await redaccion.parrafos()
    assert datos["limite_palabras"] == 250
    textos = [p["texto"] for p in datos["parrafos"]]
    assert PARRAFO in textos
    assert "1. Introducción" not in textos and not any(t.startswith("Quispe") for t in textos)
    primero = next(p for p in datos["parrafos"] if p["texto"] == PARRAFO)
    assert primero["seccion"] == "1. Introducción" and primero["dentro_del_limite"] is True
    assert primero["palabras"] == len(PARRAFO.split())


async def test_cp10_propone_dentro_del_limite_con_cambios_justificados(
    redaccion: Redaccion,
) -> None:
    parrafo = await redaccion.id_de("La ansiedad ante")
    respuesta = await redaccion.pedir(parrafo)
    assert respuesta.status_code == 202, respuesta.text
    vista = await redaccion.ver(respuesta.json()["id"])
    assert vista["estado"] == "entregada" and vista["etiqueta"] is None, vista["advertencias"]
    assert vista["parrafo_id"] == parrafo
    assert vista["original"] == PARRAFO  # el guardado, no el que devolvió el modelo
    assert vista["propuesta"] == PROPUESTA
    assert vista["palabras_original"] == len(PARRAFO.split())
    assert vista["limite_palabras_propuesta"] == int(len(PARRAFO.split()) * 1.2)
    (cambio,) = vista["cambios"]
    assert cambio["tipo_nombre"] == "Fluidez y precisión léxica"
    assert cambio["citas"][0]["identificador"] == "F1" and cambio["citas"][0]["guia"]
    assert {c["nombre"]: c["superada"] for c in vista["comprobaciones"]} == {
        "esquema": True,
        "limites_propuesta": True,
        "citas": True,
    }
    # Al modelo van solo el párrafo y las pautas de las guías (RNF-10).
    (entrada,) = redaccion.modelo.entradas
    assert entrada.datos[0].etiqueta == "alcance" and entrada.datos[0].contenido == PARRAFO
    assert all(b.etiqueta.startswith("F") for b in entrada.datos[1:])
    propias = (await redaccion.cliente.get("/caso/solicitudes")).json()
    assert [s["tipo"] for s in propias] == ["propuesta_redaccion"]


async def test_cp10_una_propuesta_demasiado_larga_va_con_advertencias(
    redaccion: Redaccion,
) -> None:
    redaccion.modelo.propuesta = PROPUESTA + " " + " ".join(["Esto se agrega."] * 6)
    respuesta = await redaccion.pedir(await redaccion.id_de("La ansiedad ante"))
    vista = await redaccion.ver(respuesta.json()["id"])
    assert vista["etiqueta"] == "con_advertencias"
    assert any("el límite es" in a for a in vista["advertencias"])


async def test_una_propuesta_con_una_cita_nueva_va_con_advertencias(redaccion: Redaccion) -> None:
    redaccion.modelo.propuesta = PROPUESTA.replace("año?", "año [9]?")
    respuesta = await redaccion.pedir(await redaccion.id_de("La ansiedad ante"))
    vista = await redaccion.ver(respuesta.json()["id"])
    assert vista["etiqueta"] == "con_advertencias"
    assert any("citas que no están en el original" in a for a in vista["advertencias"])


async def test_cp09_rechaza_sin_crear_la_solicitud(redaccion: Redaccion) -> None:
    parrafo = await redaccion.id_de("La ansiedad ante")
    siguiente = f"p{int(parrafo[1:]) + 1}"
    varios = await redaccion.cliente.post(
        "/caso/redaccion", json={"parrafo_id": f"{parrafo}-{siguiente}"}
    )
    assert varios.status_code == 422 and varios.json()["codigo"] == "fragmento_de_varios_parrafos"
    referencias = await redaccion.cliente.post(
        "/caso/redaccion", json={"parrafo_id": await _id_por_texto(redaccion, "Quispe")}
    )
    assert referencias.status_code == 422
    assert referencias.json()["codigo"] == "parrafo_no_admitido"
    consultar(
        redaccion.entorno.url_bd,
        "UPDATE configuracion SET parametros = jsonb_set(parametros, '{limite_palabras_d3}',"
        " '10') WHERE vigente RETURNING id",
    )
    largo = await redaccion.cliente.post("/caso/redaccion", json={"parrafo_id": parrafo})
    assert largo.status_code == 422 and largo.json()["codigo"] == "alcance_demasiado_largo"
    assert "Seleccione un fragmento más corto" in largo.json()["mensaje"]
    listado = await redaccion.parrafos()
    assert listado["limite_palabras"] == 10
    assert next(p for p in listado["parrafos"] if p["id"] == parrafo)["dentro_del_limite"] is False
    assert (await redaccion.cliente.get("/caso/solicitudes")).json() == []
    assert redaccion.modelo.entradas == []


async def _id_por_texto(redaccion: Redaccion, inicio: str) -> str:
    """Id de un párrafo que la lista no ofrece (título o referencia), desde la versión."""
    version = (await redaccion.cliente.get("/caso/versiones")).json()[0]["id"]
    vista = (await redaccion.cliente.get(f"/caso/versiones/{version}/secciones")).json()
    return next(p["id"] for p in vista["parrafos"] if p["texto"].startswith(inicio))


async def test_aislamiento_entre_casos(redaccion: Redaccion, investigador: httpx.AsyncClient) -> None:
    respuesta = await redaccion.pedir(await redaccion.id_de("La ansiedad ante"))
    otro = await _caso(redaccion.entorno, investigador, "CASO-C")
    assert (await otro.get(f"/caso/redaccion/{respuesta.json()['id']}")).status_code == 404
    assert (await otro.get("/caso/solicitudes")).json() == []
