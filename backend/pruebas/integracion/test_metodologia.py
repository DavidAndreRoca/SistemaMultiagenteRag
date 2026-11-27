"""Diagnóstico metodológico con la base real y el modelo simulado (T26; CP-08, datos
inventados, diseño no identificable, aislamiento)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.agentes.metodologia import AgenteMetodologia, AtencionMetodologia
from app.bd.enumeraciones import TipoSolicitud
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.dobles_rag import ReordenadorFicticio
from pruebas.integracion.conftest import Entorno, consultar, esperar_orquestador
from pruebas.integracion.test_estructura import _caso, _guias

pytestmark = pytest.mark.integracion


@dataclass
class Modelo:
    entradas: list[EntradaModelo] = field(default_factory=list)
    recomendacion: str = "Justifique por qué 84 estudiantes bastan y cómo se seleccionaron."

    def revision(self, entrada: EntradaModelo) -> dict[str, Any]:
        self.entradas.append(entrada)
        hallazgo = {
            "ubicacion": "sección",
            "descripcion": "No se informan los criterios de selección de la muestra (GEN-2).",
            "recomendacion": self.recomendacion,
            "citas": ["F1"],
        }
        return {
            "hallazgos": [
                {**hallazgo, "indicador": "precision_del_analisis_de_datos", "severidad": "baja"},
                {**hallazgo, "indicador": "justificacion_del_diseno", "severidad": "alta"},
            ],
            "preguntas_al_estudiante": ["¿Qué diseño de investigación siguió el estudio?"],
            "notas_para_el_estudiante": ["Para la redacción, pida una propuesta de redacción."],
        }

    def cadena(self) -> CadenaModelos:
        async def sin_espera(_: float) -> None:
            return None

        simulado = ProveedorSimulado(
            respuestas={
                "JuicioSuficiencia": lambda _: {"suficiente": True, "motivo": "Lista pertinente."},
                "RevisionMetodologica": self.revision,
            }
        )
        return CadenaModelos(
            [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
            dormir=sin_espera,
        )


@dataclass
class Metodologia:
    entorno: Entorno
    cliente: httpx.AsyncClient
    modelo: Modelo
    atencion: AtencionMetodologia

    async def secciones(self) -> list[dict[str, Any]]:
        respuesta = await self.cliente.get("/caso/metodologia/secciones")
        assert respuesta.status_code == 200, respuesta.text
        datos: list[dict[str, Any]] = respuesta.json()
        return datos

    async def id_de(self, titulo: str) -> str:
        return next(s["id"] for s in await self.secciones() if s["titulo"] == titulo)

    async def pedir(self, seccion_id: str) -> dict[str, Any]:
        respuesta = await self.cliente.post("/caso/metodologia", json={"seccion_id": seccion_id})
        assert respuesta.status_code == 202, respuesta.text
        await esperar_orquestador(self.entorno)
        vista = await self.cliente.get(f"/caso/metodologia/{respuesta.json()['id']}")
        assert vista.status_code == 200, vista.text
        datos: dict[str, Any] = vista.json()
        return datos


def _atencion(entorno: Entorno, modelo: Modelo) -> AtencionMetodologia:
    cadena = modelo.cadena()
    servicio = ServicioEvidencia(
        Recuperador(EmbeddingsFicticios(), ReordenadorFicticio()),
        cadena,
        lambda: datetime(2026, 11, 26, 12, tzinfo=UTC),
    )
    agente = AgenteMetodologia(
        servicio, cadena, versiones=lambda: {"suficiencia": "v1", "metodologia": "v1"}
    )
    atencion = AtencionMetodologia(
        TipoSolicitud.REVISION_METODOLOGICA,
        agente,
        entorno.reloj,
    )
    entorno.aplicacion.state.atencion_metodologia = atencion
    return atencion


@pytest.fixture
async def metodologia(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> AsyncIterator[Metodologia]:
    consultar(
        entorno.url_bd,
        "UPDATE configuracion SET parametros = jsonb_set(parametros, '{suficiencia_tau}',"
        " '0.01') WHERE vigente RETURNING id",
    )
    await _guias(entorno)
    cliente = await _caso(entorno, investigador, "CASO-A")
    modelo = Modelo()
    yield Metodologia(entorno, cliente, modelo, _atencion(entorno, modelo))
    await cliente.aclose()


async def test_lista_las_secciones_con_el_diseno_que_nombran(metodologia: Metodologia) -> None:
    secciones = {s["titulo"]: s["diseno"] for s in await metodologia.secciones()}
    assert secciones["Resumen"] == "cuasiexperimental"
    assert secciones["2. Método"] is None
    assert "Referencias" not in secciones


async def test_sin_diseno_declarado_pregunta_y_revisa_los_elementos_comunes(
    metodologia: Metodologia,
) -> None:
    vista = await metodologia.pedir(await metodologia.id_de("2. Método"))
    assert vista["estado"] == "entregada" and vista["etiqueta"] == "verificada", vista[
        "advertencias"
    ]
    assert vista["diseno"] is None and vista["seccion_titulo"] == "2. Método"
    assert [h["severidad"] for h in vista["hallazgos"]] == ["alta", "baja"]
    assert vista["hallazgos"][0]["indicador_nombre"] == "Justificación del diseño"
    assert vista["preguntas_al_estudiante"] == ["¿Qué diseño de investigación siguió el estudio?"]
    assert {c["nombre"]: c["superada"] for c in vista["comprobaciones"]} == {
        "esquema": True,
        "no_reescritura": True,
        "sin_datos_inventados": True,  # 84 está en el texto del estudiante
        "citas": True,
    }
    (entrada,) = metodologia.modelo.entradas
    assert "no lo supongas" in entrada.tarea
    # La lista de comprobación (elementos comunes) llega como fragmentos citables.
    assert any("GEN-1." in b.contenido for b in entrada.datos[1:])
    assert entrada.datos[0].etiqueta == "alcance" and "## 2. Método" in entrada.datos[0].contenido


async def test_con_diseno_declarado_usa_su_lista_de_comprobacion(
    metodologia: Metodologia,
) -> None:
    vista = await metodologia.pedir(await metodologia.id_de("Resumen"))
    assert vista["diseno"] == "cuasiexperimental"
    (entrada,) = metodologia.modelo.entradas
    assert "diseño cuasiexperimental" in entrada.tarea
    assert any("CUA-1." in b.contenido for b in entrada.datos[1:])


async def test_un_valor_estadistico_inventado_va_con_advertencias(
    metodologia: Metodologia,
) -> None:
    metodologia.modelo.recomendacion = "Informe que la correlación fue r = 0,62 con p < 0,05."
    vista = await metodologia.pedir(await metodologia.id_de("2. Método"))
    assert vista["etiqueta"] == "con_advertencias"
    assert any("dato posiblemente inventado" in a for a in vista["advertencias"])


async def test_aislamiento_entre_casos(
    metodologia: Metodologia, investigador: httpx.AsyncClient
) -> None:
    ajena = await metodologia.cliente.post("/caso/metodologia", json={"seccion_id": "s999"})
    assert ajena.status_code == 422 and ajena.json()["codigo"] == "seccion_inexistente"
    vista = await metodologia.pedir(await metodologia.id_de("2. Método"))
    otro = await _caso(metodologia.entorno, investigador, "CASO-C")
    assert (await otro.get(f"/caso/metodologia/{vista['id']}")).status_code == 404
    propias = (await metodologia.cliente.get("/caso/solicitudes")).json()
    assert [s["tipo"] for s in propias] == ["revision_metodologica"]
