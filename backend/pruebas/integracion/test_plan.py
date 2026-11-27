"""Plan de tarea del hito con la base real y el modelo simulado (T24; RF-05, abstención sin
instrucciones del hito, aislamiento)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.agentes.plan import AgentePlan, AtencionPlan
from app.bd.enumeraciones import Rol, TipoSolicitud
from app.corpus.guias import coleccion_guias, indexar_guia, leer_guia
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.dobles_rag import ReordenadorFicticio
from pruebas.integracion.conftest import Entorno, consultar, esperar_orquestador
from pruebas.integracion.test_estructura import PROVISIONALES, _caso, _guias

pytestmark = pytest.mark.integracion


@dataclass
class Modelo:
    entradas: list[EntradaModelo] = field(default_factory=list)
    juicios: int = 0

    def plan(self, entrada: EntradaModelo) -> dict[str, Any]:
        self.entradas.append(entrada)
        tarea = {"criterio_de_logro": "Nombra las mismas variables.", "citas": ["F1"]}
        return {
            "hito": "Un hito que el modelo escribió mal",
            "tareas": [
                {**tarea, "orden": 3, "tarea": "Revisar que el título nombre las variables."},
                {**tarea, "orden": 1, "tarea": "Redactar la justificación del estudio."},
            ],
            "notas_para_el_estudiante": ["Para el método, pida la revisión metodológica."],
        }

    def juicio(self, _: EntradaModelo) -> dict[str, Any]:
        self.juicios += 1
        return {"suficiente": True, "motivo": "Instrucciones del hito."}

    def cadena(self) -> CadenaModelos:
        async def sin_espera(_: float) -> None:
            return None

        simulado = ProveedorSimulado(
            respuestas={"JuicioSuficiencia": self.juicio, "PlanTarea": self.plan}
        )
        return CadenaModelos(
            [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
            dormir=sin_espera,
        )


@dataclass
class Plan:
    entorno: Entorno
    cliente: httpx.AsyncClient
    modelo: Modelo
    atencion: AtencionPlan

    async def pedir(self, hito: str) -> dict[str, Any]:
        respuesta = await self.cliente.post("/caso/plan", json={"hito": hito})
        assert respuesta.status_code == 202, respuesta.text
        await esperar_orquestador(self.entorno)
        vista = await self.cliente.get(f"/caso/plan/{respuesta.json()['id']}")
        assert vista.status_code == 200, vista.text
        datos: dict[str, Any] = vista.json()
        return datos


def _atencion(entorno: Entorno, modelo: Modelo) -> AtencionPlan:
    cadena = modelo.cadena()
    servicio = ServicioEvidencia(
        Recuperador(EmbeddingsFicticios(), ReordenadorFicticio()),
        cadena,
        lambda: datetime(2026, 11, 26, 12, tzinfo=UTC),
    )
    agente = AgentePlan(servicio, cadena, versiones=lambda: {"suficiencia": "v1", "plan": "v1"})
    atencion = AtencionPlan(
        TipoSolicitud.PLAN_TAREA,
        agente,
        entorno.reloj,
    )
    entorno.aplicacion.state.atencion_plan = atencion
    return atencion


def _umbral_bajo(entorno: Entorno) -> None:
    consultar(
        entorno.url_bd,
        "UPDATE configuracion SET parametros = jsonb_set(parametros, '{suficiencia_tau}',"
        " '0.01') WHERE vigente RETURNING id",
    )


@pytest.fixture
async def plan(entorno: Entorno, investigador: httpx.AsyncClient) -> AsyncIterator[Plan]:
    _umbral_bajo(entorno)
    await _guias(entorno)
    cliente = await _caso(entorno, investigador, "CASO-A")
    modelo = Modelo()
    yield Plan(entorno, cliente, modelo, _atencion(entorno, modelo))
    await cliente.aclose()


async def test_lista_los_hitos_con_su_version_vigente(plan: Plan) -> None:
    hitos = (await plan.cliente.get("/caso/plan/hitos")).json()
    assert hitos[0]["codigo"] == "avance_1" and hitos[0]["nombre"] == "Avance 1: Planteamiento"
    assert hitos[0]["version_cargada_en"] is not None
    assert all(h["version_cargada_en"] is None for h in hitos[1:])


async def test_arma_el_plan_con_las_instrucciones_del_hito_y_el_estado_del_borrador(
    plan: Plan,
) -> None:
    vista = await plan.pedir("avance_1")
    assert vista["estado"] == "entregada" and vista["etiqueta"] == "verificada", vista[
        "advertencias"
    ]
    assert vista["hito"] == "Avance 1: Planteamiento"  # lo pone el sistema
    assert [(t["orden"], t["tarea"][:9]) for t in vista["tareas"]] == [
        (1, "Redactar "),
        (2, "Revisar q"),
    ]
    assert vista["tareas"][0]["citas"][0]["identificador"] == "F1"
    assert {c["nombre"]: c["superada"] for c in vista["comprobaciones"]} == {
        "esquema": True,
        "no_reescritura": True,
        "citas": True,
    }
    (entrada,) = plan.modelo.entradas
    alcance = entrada.datos[0].contenido
    # Al modelo va el estado del borrador (títulos y palabras), no su texto (RNF-10).
    assert alcance.startswith("Hito de la versión: Avance 1: Planteamiento")
    assert "- 1. Introducción (" in alcance and "Lista de referencias: sí" in alcance
    assert "El grupo con tutoría redujo" not in alcance
    assert any("título provisional" in b.contenido for b in entrada.datos[1:])
    propias = (await plan.cliente.get("/caso/solicitudes")).json()
    assert [s["tipo"] for s in propias] == ["plan_tarea"]


async def test_sin_instrucciones_del_hito_se_abstiene_sin_recuperar_ni_generar(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> None:
    _umbral_bajo(entorno)
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:  # solo la guía IMRaD
        unidad = UnidadDeTrabajo(sesion)
        cuenta = await unidad.autenticacion.cuenta_por_codigo("INV-01")
        assert cuenta is not None
        contexto = ContextoAcceso(cuenta.id, Rol.INVESTIGADOR, None)
        coleccion = await coleccion_guias(unidad, contexto)
        guia = leer_guia(PROVISIONALES / "guia-estructura-imrad.md")
        await indexar_guia(unidad, contexto, coleccion, guia, EmbeddingsFicticios())
        await unidad.confirmar()
    cliente = await _caso(entorno, investigador, "CASO-B")
    modelo = Modelo()
    sin_instrucciones = Plan(entorno, cliente, modelo, _atencion(entorno, modelo))
    vista = await sin_instrucciones.pedir("avance_1")
    assert vista["estado"] == "entregada" and vista["abstencion"] is True
    assert vista["aviso"] == "Sin evidencia suficiente"
    assert vista["motivo_abstencion"] == (
        "El corpus de guías no tiene instrucciones del hito Avance 1: Planteamiento."
    )
    assert vista["tareas"] == [] and modelo.entradas == [] and modelo.juicios == 0
    recuperados = consultar(
        entorno.url_bd,
        "SELECT count(*) FROM fragmento_recuperado WHERE solicitud_id = %s",
        vista["id"],
    )
    assert recuperados == [(0,)]


async def test_hito_sin_version_o_inexistente_no_crea_la_solicitud(plan: Plan) -> None:
    sin_version = await plan.cliente.post("/caso/plan", json={"hito": "avance_3"})
    assert sin_version.status_code == 409
    assert sin_version.json()["codigo"] == "sin_version_del_hito"
    inexistente = await plan.cliente.post("/caso/plan", json={"hito": "avance_99"})
    assert inexistente.status_code == 422 and inexistente.json()["codigo"] == "hito_inexistente"
    assert (await plan.cliente.get("/caso/solicitudes")).json() == []


async def test_aislamiento_entre_casos(plan: Plan, investigador: httpx.AsyncClient) -> None:
    vista = await plan.pedir("avance_1")
    otro = await _caso(plan.entorno, investigador, "CASO-C")
    assert (await otro.get(f"/caso/plan/{vista['id']}")).status_code == 404
