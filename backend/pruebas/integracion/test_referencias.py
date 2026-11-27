"""Verificación de referencias con la base real y los servicios simulados (T20; CP-12, CP-13,
RN-18, RF-09; decisión T20-01)."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.agentes.referencias import (
    AVISO_NO_COMPROBABLES,
    AVISO_SIN_EXPLICACIONES,
    AtencionReferencias,
)
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, ErrorDisponibilidad, MotivoError, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.repositorios.unidad import fabrica_de_unidades
from pruebas.datos import referencias_t20 as t20
from pruebas.dobles_referencias import crear_atencion
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


@dataclass
class Verificacion:
    entorno: Entorno
    investigador: httpx.AsyncClient

    async def caso(
        self, codigo: str, norma: str = "ieee", archivo: str | None = None
    ) -> httpx.AsyncClient:
        tema = f"TEMA-{codigo}"
        await crear_tema(self.investigador, tema)
        caso = await crear_caso(self.investigador, codigo, tema)
        if norma != "ieee":
            cambio = await self.investigador.put(
                f"/investigador/casos/{codigo}/norma", json={"norma": norma}
            )
            assert cambio.status_code == 200, cambio.text
        cliente = await entrar_y_cambiar(self.entorno.cliente(), *primera_credencial(caso))
        nombre = archivo or f"referencias_{norma}.docx"
        carga = await cliente.post(
            "/caso/versiones",
            data={"hito": "avance_1"},
            files={"archivo": ("borrador.docx", (DOCX / nombre).read_bytes())},
        )
        assert carga.status_code == 201, carga.text
        return cliente

    def atencion(self, **opciones: Any) -> AtencionReferencias:
        atencion = crear_atencion(
            fabrica_de_unidades(self.entorno.aplicacion.state.fabrica_sesiones),
            self.entorno.reloj,
            **opciones,
        )
        self.entorno.aplicacion.state.atencion_referencias = atencion
        return atencion

    async def verificar(
        self, cliente: httpx.AsyncClient, atencion: AtencionReferencias
    ) -> dict[str, Any]:
        respuesta = await cliente.post("/caso/referencias")
        assert respuesta.status_code == 202, respuesta.text
        await esperar_orquestador(self.entorno)
        vista = await cliente.get(f"/caso/referencias/{respuesta.json()['id']}")
        assert vista.status_code == 200, vista.text
        datos: dict[str, Any] = vista.json()
        return datos


@pytest.fixture
async def verificacion(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> AsyncIterator[Verificacion]:
    yield Verificacion(entorno, investigador)


def _comprobar_clave(vista: dict[str, Any], norma: str) -> None:
    clave = t20.esperado(norma)
    assert vista["estado"] == "entregada" and vista["norma"] == norma
    estados = {r["indice"]: r["estado"] for r in vista["referencias"]}
    assert estados == clave["estados"]
    campos = {r["indice"]: {d["campo"] for d in r["discrepancias"]} for r in vista["referencias"]}
    for indice, esperados in clave["campos"].items():  # type: ignore[attr-defined]
        assert campos[indice] == esperados, (norma, indice, campos[indice])
    # Ninguna fabricada queda como verificada (criterio de aceptación de T20).
    assert all(estados[i] != "verificada" for i in clave["fabricadas"])  # type: ignore[attr-defined]
    assert vista["citas_sin_entrada"] == clave["citas_sin_entrada"]
    assert [e["indice"] for e in vista["entradas_no_citadas"]] == clave["entradas_no_citadas"]
    assert vista["resumen"] == {
        "verificada": 4,
        "con_discrepancias": 4,
        "no_localizada": 2,
        "no_comprobable": 1,
    }
    assert vista["avisos"] == [AVISO_NO_COMPROBABLES.format(n=1)]
    assert vista["etiqueta"] is None and vista["comprobaciones"][0]["superada"] is True


async def test_cp12_informe_completo_en_ieee(verificacion: Verificacion) -> None:
    cliente = await verificacion.caso("CASO-A")
    vista = await verificacion.verificar(cliente, verificacion.atencion())
    _comprobar_clave(vista, "ieee")
    por_indice = {r["indice"]: r for r in vista["referencias"]}
    anio = por_indice[3]["discrepancias"][0]
    assert (anio["etiqueta"], anio["valor_borrador"], anio["valor_fuente"]) == (
        "Año",
        "2022",
        "2021",
    )
    assert por_indice[2]["metodo"] == "metadatos"
    assert por_indice[2]["url_doi"] == "https://doi.org/10.5555/t20.mamani.2019"
    assert por_indice[11]["citada"] is False and por_indice[1]["citada"] is True


async def test_cp12_informe_completo_en_apa7(verificacion: Verificacion) -> None:
    cliente = await verificacion.caso("CASO-A", norma="apa7")
    vista = await verificacion.verificar(cliente, verificacion.atencion())
    _comprobar_clave(vista, "apa7")
    assert vista["norma_nombre"] == "APA 7"


async def test_cp13_con_los_servicios_caidos_nada_queda_inexistente(
    verificacion: Verificacion,
) -> None:
    cliente = await verificacion.caso("CASO-A")
    vista = await verificacion.verificar(cliente, verificacion.atencion(caidos=True))
    assert vista["estado"] == "entregada"
    assert {r["estado"] for r in vista["referencias"]} == {"no_comprobable"}
    assert vista["avisos"][0] == AVISO_NO_COMPROBABLES.format(n=11)
    # El cruce de citas no depende de los servicios.
    assert vista["citas_sin_entrada"] == ["[12]"]


async def test_el_resultado_queda_registrado_en_la_base(
    verificacion: Verificacion, entorno: Entorno
) -> None:
    cliente = await verificacion.caso("CASO-A")
    vista = await verificacion.verificar(cliente, verificacion.atencion())
    ((tipo, estado, salida),) = consultar(
        entorno.url_bd,
        "SELECT s.tipo, s.estado, r.salida FROM solicitud s"
        " JOIN resultado r ON r.solicitud_id = s.id"
        " WHERE s.id = %s",
        uuid.UUID(vista["id"]),
    )
    assert (tipo, estado) == ("verificacion_referencias", "entregada")
    assert isinstance(salida, dict) and len(salida["referencias"]) == 11
    assert salida["citas"][0]["texto"] == "[1]"


async def test_sin_version_responde_409(verificacion: Verificacion, entorno: Entorno) -> None:
    tema = "TEMA-SIN"
    await crear_tema(verificacion.investigador, tema)
    caso = await crear_caso(verificacion.investigador, "CASO-SIN", tema)
    cliente = await entrar_y_cambiar(entorno.cliente(), *primera_credencial(caso))
    verificacion.atencion()
    respuesta = await cliente.post("/caso/referencias")
    assert respuesta.status_code == 409 and respuesta.json()["codigo"] == "sin_version"


async def test_sin_lista_detectada_pide_indicarla(verificacion: Verificacion) -> None:
    cliente = await verificacion.caso("CASO-A", archivo="sin_estilos.docx")
    verificacion.atencion()
    respuesta = await cliente.post("/caso/referencias")
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "lista_no_detectada"
    assert "vuelva a cargar la versión" in respuesta.json()["mensaje"]


async def test_con_grobid_caido_la_solicitud_queda_no_atendida(verificacion: Verificacion) -> None:
    cliente = await verificacion.caso("CASO-A")
    vista = await verificacion.verificar(cliente, verificacion.atencion(grobid_caido=True))
    assert vista["estado"] == "no_atendida" and vista["motivo"] == "grobid_no_disponible"
    assert vista["referencias"] == []


async def test_otro_caso_no_ve_la_verificacion(verificacion: Verificacion) -> None:
    cliente_a = await verificacion.caso("CASO-A")
    cliente_b = await verificacion.caso("CASO-B")
    vista = await verificacion.verificar(cliente_a, verificacion.atencion())
    ajena = await cliente_b.get(f"/caso/referencias/{vista['id']}")
    assert ajena.status_code == 404


async def test_el_registro_no_lleva_el_texto_de_las_referencias(
    verificacion: Verificacion, caplog: pytest.LogCaptureFixture
) -> None:
    cliente = await verificacion.caso("CASO-A")
    with caplog.at_level(logging.DEBUG):
        await verificacion.verificar(cliente, verificacion.atencion())
    registro = "\n".join(
        json.dumps(r.__dict__, default=str, ensure_ascii=False) for r in caplog.records
    )
    assert "entregada" in registro
    for obra in t20.OBRAS:
        assert obra.titulo not in registro
    assert "Mendoza" not in registro and "La tutoría entre pares" not in registro


def _cadena(caido: bool = False) -> tuple[CadenaModelos, list[EntradaModelo]]:
    entradas: list[EntradaModelo] = []

    def responder(entrada: EntradaModelo) -> dict[str, Any]:
        entradas.append(entrada)
        return {
            "explicaciones": [
                {"indice": int(b.etiqueta.removeprefix("R")), "explicacion": "Revise el dato."}
                for b in entrada.datos
            ]
            + [{"indice": 99, "explicacion": "Inventada."}]  # se descarta: no es de la lista
        }

    async def sin_espera(_: float) -> None:
        return None

    simulado = ProveedorSimulado(respuestas={"ExplicacionesDiscrepancias": responder})
    if caido:
        simulado.fallar = ErrorDisponibilidad(MotivoError.SOBRECARGA, Proveedor.SIMULADO)
    cadena = CadenaModelos(
        [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
        dormir=sin_espera,
    )
    return cadena, entradas


def _explicar(entorno: Entorno) -> None:
    consultar(
        entorno.url_bd,
        "UPDATE configuracion SET parametros = jsonb_set(parametros, '{explicar_discrepancias}',"
        " 'true') WHERE vigente RETURNING id",
    )


async def test_por_defecto_no_se_llama_al_modelo(verificacion: Verificacion) -> None:
    cadena, entradas = _cadena()
    cliente = await verificacion.caso("CASO-A")
    vista = await verificacion.verificar(cliente, verificacion.atencion(modelo=cadena))
    assert entradas == [] and all(r["explicacion"] is None for r in vista["referencias"])


async def test_si_se_configura_explica_cada_discrepancia(
    verificacion: Verificacion, entorno: Entorno
) -> None:
    _explicar(entorno)
    cadena, entradas = _cadena()
    cliente = await verificacion.caso("CASO-A")
    vista = await verificacion.verificar(cliente, verificacion.atencion(modelo=cadena))
    (entrada,) = entradas
    assert [b.etiqueta for b in entrada.datos] == ["R3", "R4", "R5", "R7"]
    assert (
        "anio: en la referencia del estudiante, 2022; en la fuente, 2021"
        in entrada.datos[0].contenido
    )
    # Al modelo solo van las discrepancias: ni el texto del borrador ni la lista completa.
    enviado = entrada.model_dump_json()
    assert "La tutoría entre pares reduce" not in enviado and "[11]" not in enviado
    explicadas = {r["indice"]: r["explicacion"] for r in vista["referencias"] if r["explicacion"]}
    assert explicadas == {
        3: "Revise el dato.",
        4: "Revise el dato.",
        5: "Revise el dato.",
        7: "Revise el dato.",
    }
    # El estado lo decide el sistema, no el modelo.
    assert {r["indice"]: r["estado"] for r in vista["referencias"]} == t20.esperado("ieee")[
        "estados"
    ]


async def test_si_el_modelo_falla_el_informe_sale_igual(
    verificacion: Verificacion, entorno: Entorno
) -> None:
    _explicar(entorno)
    cadena, _ = _cadena(caido=True)
    cliente = await verificacion.caso("CASO-A")
    vista = await verificacion.verificar(cliente, verificacion.atencion(modelo=cadena))
    assert vista["estado"] == "entregada" and AVISO_SIN_EXPLICACIONES in vista["avisos"]
    assert len(vista["referencias"]) == 11


async def test_la_lista_de_solicitudes_solo_muestra_las_del_caso(
    verificacion: Verificacion,
) -> None:
    """Prototipo: la lista del panel para volver a abrir un resultado (aislamiento por caso)."""
    cliente_a = await verificacion.caso("CASO-A")
    cliente_b = await verificacion.caso("CASO-B")
    vista = await verificacion.verificar(cliente_a, verificacion.atencion())
    propias = (await cliente_a.get("/caso/solicitudes")).json()
    assert [(s["id"], s["tipo"], s["estado"], s["consulta"]) for s in propias] == [
        (vista["id"], "verificacion_referencias", "entregada", None)
    ]
    assert (await cliente_b.get("/caso/solicitudes")).json() == []
