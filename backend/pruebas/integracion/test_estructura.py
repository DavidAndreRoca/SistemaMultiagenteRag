"""Diagnóstico de estructura y coherencia con la base real y el modelo simulado (T23; CP-08,
CP-05, aislamiento)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.agentes.estructura import AgenteEstructura
from app.agentes.seccion import AtencionSeccion
from app.bd.enumeraciones import Rol, TipoSolicitud
from app.corpus.guias import archivos, coleccion_guias, indexar_guia, leer_guia
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
from pruebas.integracion.conftest import (
    Entorno,
    consultar,
    crear_caso,
    crear_tema,
    entrar_y_cambiar,
    esperar_orquestador,
    primera_credencial,
)

pytestmark = pytest.mark.integracion

DOCX = Path(__file__).parents[1] / "datos" / "docx"
PROVISIONALES = Path(__file__).parents[2] / "guias" / "provisionales"
REESCRITURA = " ".join(["La sección debería decir exactamente esto"] * 12)  # 72 palabras


@dataclass
class Modelo:
    entradas: list[EntradaModelo] = field(default_factory=list)
    recomendacion: str = "Revise que el objetivo nombre las mismas variables que el problema."

    def revision(self, entrada: EntradaModelo) -> dict[str, Any]:
        self.entradas.append(entrada)
        hallazgo = {
            "ubicacion": "p5",
            "descripcion": "El objetivo no retoma la variable del problema.",
            "recomendacion": self.recomendacion,
            "citas": ["F1"],
        }
        return {
            "hallazgos": [
                {**hallazgo, "indicador": "cohesion_entre_apartados", "severidad": "baja"},
                {
                    **hallazgo,
                    "indicador": "alineacion_problema_objetivos_hipotesis",
                    "severidad": "alta",
                },
            ],
            "fortalezas": ["El problema se apoya en antecedentes."],
            "notas_para_el_estudiante": ["Para el diseño, pida la revisión metodológica."],
        }

    def cadena(self) -> CadenaModelos:
        async def sin_espera(_: float) -> None:
            return None

        simulado = ProveedorSimulado(
            respuestas={
                "JuicioSuficiencia": lambda _: {"suficiente": True, "motivo": "Guías pertinentes."},
                "RevisionEstructura": self.revision,
            }
        )
        return CadenaModelos(
            [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
            dormir=sin_espera,
        )


@dataclass
class Estructura:
    entorno: Entorno
    cliente: httpx.AsyncClient
    modelo: Modelo
    atencion: AtencionSeccion

    async def pedir(self, seccion_id: str) -> httpx.Response:
        respuesta = await self.cliente.post("/caso/estructura", json={"seccion_id": seccion_id})
        await esperar_orquestador(self.entorno)
        return respuesta

    async def ver(self, solicitud_id: str) -> dict[str, Any]:
        respuesta = await self.cliente.get(f"/caso/estructura/{solicitud_id}")
        assert respuesta.status_code == 200, respuesta.text
        datos: dict[str, Any] = respuesta.json()
        return datos

    async def introduccion(self) -> str:
        secciones = (await self.cliente.get("/caso/estructura/secciones")).json()
        return next(s["id"] for s in secciones if "Introducción" in s["titulo"])


async def _caso(
    entorno: Entorno, investigador: httpx.AsyncClient, codigo: str
) -> httpx.AsyncClient:
    tema = f"TEMA-{codigo}"
    await crear_tema(investigador, tema)
    caso = await crear_caso(investigador, codigo, tema)
    cliente = await entrar_y_cambiar(entorno.cliente(), *primera_credencial(caso))
    carga = await cliente.post(
        "/caso/versiones",
        data={"hito": "avance_1"},
        files={"archivo": ("borrador.docx", (DOCX / "estructura.docx").read_bytes())},
    )
    assert carga.status_code == 201, carga.text
    return cliente


async def _guias(entorno: Entorno) -> None:
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        cuenta = await unidad.autenticacion.cuenta_por_codigo("INV-01")
        assert cuenta is not None
        contexto = ContextoAcceso(cuenta.id, Rol.INVESTIGADOR, None)
        coleccion = await coleccion_guias(unidad, contexto)
        for ruta in archivos(PROVISIONALES):
            await indexar_guia(unidad, contexto, coleccion, leer_guia(ruta), EmbeddingsFicticios())
        await unidad.confirmar()


def _atencion(entorno: Entorno, modelo: Modelo) -> AtencionSeccion:
    cadena = modelo.cadena()
    servicio = ServicioEvidencia(
        Recuperador(EmbeddingsFicticios(), ReordenadorFicticio()),
        cadena,
        lambda: datetime(2026, 11, 26, 12, tzinfo=UTC),
    )
    agente = AgenteEstructura(
        servicio, cadena, versiones=lambda: {"suficiencia": "v1", "estructura": "v1"}
    )
    atencion = AtencionSeccion(
        TipoSolicitud.REVISION_ESTRUCTURA,
        agente,
        entorno.reloj,
    )
    entorno.aplicacion.state.atencion_estructura = atencion
    return atencion


@pytest.fixture
async def estructura(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> AsyncIterator[Estructura]:
    # Umbral de suficiencia bajo: el reordenador ficticio puntúa por palabras en común.
    consultar(
        entorno.url_bd,
        "UPDATE configuracion SET parametros = jsonb_set(parametros, '{suficiencia_tau}',"
        " '0.01') WHERE vigente RETURNING id",
    )
    await _guias(entorno)
    cliente = await _caso(entorno, investigador, "CASO-A")
    modelo = Modelo()
    yield Estructura(entorno, cliente, modelo, _atencion(entorno, modelo))
    await cliente.aclose()


async def test_lista_las_secciones_revisables_sin_las_referencias(estructura: Estructura) -> None:
    secciones = (await estructura.cliente.get("/caso/estructura/secciones")).json()
    titulos = [s["titulo"] for s in secciones]
    assert "1. Introducción" in titulos and "Referencias" not in titulos
    assert all(s["palabras"] > 0 for s in secciones)


async def test_cp08_diagnostica_sin_reescribir_y_ordena_por_severidad(
    estructura: Estructura,
) -> None:
    seccion = await estructura.introduccion()
    respuesta = await estructura.pedir(seccion)
    assert respuesta.status_code == 202
    vista = await estructura.ver(respuesta.json()["id"])
    assert vista["estado"] == "entregada" and vista["etiqueta"] is None
    assert vista["seccion_titulo"] == "1. Introducción"
    assert [h["severidad"] for h in vista["hallazgos"]] == ["alta", "baja"]
    hallazgo = vista["hallazgos"][0]
    assert hallazgo["indicador_nombre"] == "Alineación entre problema, objetivos e hipótesis"
    cita = hallazgo["citas"][0]
    assert cita["identificador"] == "F1" and cita["guia"] and cita["apartado"] and cita["texto"]
    assert {c["nombre"]: c["superada"] for c in vista["comprobaciones"]} == {
        "esquema": True,
        "no_reescritura": True,
        "citas": True,
    }
    # Al modelo van la sección (con sus párrafos identificados) y las guías, nada más.
    (entrada,) = estructura.modelo.entradas
    alcance = entrada.datos[0]
    assert alcance.etiqueta == "alcance" and "## 1. Introducción" in alcance.contenido
    assert "[p" in alcance.contenido and "El grupo con tutoría redujo" not in alcance.contenido
    assert all(b.etiqueta.startswith("F") for b in entrada.datos[1:])


async def test_una_recomendacion_que_reescribe_va_con_advertencias(estructura: Estructura) -> None:
    estructura.modelo.recomendacion = REESCRITURA
    respuesta = await estructura.pedir(await estructura.introduccion())
    vista = await estructura.ver(respuesta.json()["id"])
    assert vista["etiqueta"] == "con_advertencias"
    assert any("posible reescritura" in a for a in vista["advertencias"])


async def test_sin_guias_se_abstiene_sin_llamar_al_modelo(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> None:
    cliente = await _caso(entorno, investigador, "CASO-B")
    modelo = Modelo()
    _atencion(entorno, modelo)
    seccion = next(
        s["id"]
        for s in (await cliente.get("/caso/estructura/secciones")).json()
        if "Introducción" in s["titulo"]
    )
    respuesta = await cliente.post("/caso/estructura", json={"seccion_id": seccion})
    await esperar_orquestador(entorno)
    vista = (await cliente.get(f"/caso/estructura/{respuesta.json()['id']}")).json()
    assert vista["abstencion"] is True and vista["aviso"] == "Sin evidencia suficiente"
    assert modelo.entradas == []


async def test_seccion_inexistente_y_aislamiento(
    estructura: Estructura, investigador: httpx.AsyncClient
) -> None:
    ajena = await estructura.cliente.post("/caso/estructura", json={"seccion_id": "s999"})
    assert ajena.status_code == 422 and ajena.json()["codigo"] == "seccion_inexistente"
    respuesta = await estructura.pedir(await estructura.introduccion())
    otro = await _caso(estructura.entorno, investigador, "CASO-C")
    assert (await otro.get(f"/caso/estructura/{respuesta.json()['id']}")).status_code == 404
    propias = (await estructura.cliente.get("/caso/solicitudes")).json()
    assert [s["tipo"] for s in propias] == ["revision_estructura"]
