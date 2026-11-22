"""T17: cada intento de llamada al modelo queda en ``evento_tecnico``, sin contenido."""

from __future__ import annotations

import pytest

from app.administracion.parametros import parametros_iniciales
from app.instrucciones import cargador
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import ErrorDisponibilidad, MotivoError, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.repositorios.unidad import fabrica_de_unidades
from pruebas.integracion.conftest import Entorno, consultar
from pruebas.unitarias.test_llm import ENTRADA, Clasificacion

pytestmark = pytest.mark.integracion


async def _sin_espera(_: float) -> None:
    return None


async def test_cada_intento_queda_en_evento_tecnico_sin_contenido(entorno: Entorno) -> None:
    registrar = registrador_en_base(fabrica_de_unidades(entorno.aplicacion.state.fabrica_sesiones))
    instruccion = cargador.cargar("contrato", "v1")
    caido = ProveedorSimulado(
        modelo="simulado-caido",
        fallar=ErrorDisponibilidad(MotivoError.SOBRECARGA, Proveedor.SIMULADO),
    )
    cadena = CadenaModelos(
        [
            Eslabon(caido, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0),
            Eslabon(
                ProveedorSimulado(), LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0
            ),
        ],
        registrar,
        dormir=_sin_espera,
    )
    resultado = await cadena.generar(instruccion, ENTRADA, Clasificacion)
    assert resultado.respaldo and resultado.intentos == 4

    filas = consultar(
        entorno.url_bd,
        "SELECT etapa, proveedor, modelo, tokens_entrada, tokens_salida, duracion_ms, error,"
        " solicitud_id FROM evento_tecnico ORDER BY inicio, modelo DESC",
    )
    assert len(filas) == 4
    assert {f[0] for f in filas} == {"modelo:contrato"}
    assert [f[2] for f in filas].count("simulado-caido") == 3
    exitosa = next(f for f in filas if f[2] == "simulado-determinista")
    assert exitosa[3] and exitosa[4] and exitosa[6] is None
    assert all(isinstance(f[5], int) and f[5] >= 0 for f in filas)
    assert {f[6] for f in filas if f[2] == "simulado-caido"} == {"ErrorDisponibilidad:sobrecarga"}
    # Ni la tarea, ni los datos, ni la salida (4.6).
    for parte in ("Participaron 84", "Clasifica el fragmento", "introduccion"):
        assert consultar(
            entorno.url_bd,
            "SELECT count(*) FROM evento_tecnico t WHERE t::text ILIKE %s",
            f"%{parte}%",
        ) == [(0,)]


async def test_la_cadena_de_pruebas_usa_el_simulado_y_registra(entorno: Entorno) -> None:
    ajustes = entorno.aplicacion.state.ajustes
    registrar = registrador_en_base(fabrica_de_unidades(entorno.aplicacion.state.fabrica_sesiones))
    cadena = crear_cadena(ajustes, parametros_iniciales(), registrar)
    resultado = await cadena.generar(cargador.cargar("contrato", "v1"), ENTRADA, Clasificacion)
    assert resultado.proveedor is Proveedor.SIMULADO
    assert consultar(entorno.url_bd, "SELECT proveedor FROM evento_tecnico") == [("simulado",)]
