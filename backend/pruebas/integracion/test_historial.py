"""Historial del caso, resumen y panel con la base real (T33; CP-20, RF-14, RF-19).

Reutiliza el fixture ``seguimiento`` de T29 (caso A con una versión del Avance 1) y el
ayudante de T31 que inserta una solicitud entregada con su resultado.
"""

# ruff: noqa: F811

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import httpx
import pytest

from app.bd.enumeraciones import TipoSolicitud
from pruebas.integracion.conftest import consultar
from pruebas.integracion.test_decisiones import _decidir, _entregada
from pruebas.integracion.test_estructura import _caso
from pruebas.integracion.test_seguimiento import Seguimiento, seguimiento  # noqa: F401

pytestmark = pytest.mark.integracion

CONSULTA_A = "Consulta ficticia del caso A sobre tutoría entre pares"


async def _historial(cliente: httpx.AsyncClient, **filtros: str) -> list[dict[str, Any]]:
    respuesta = await cliente.get("/caso/historial", params=filtros)
    assert respuesta.status_code == 200, respuesta.text
    eventos: list[dict[str, Any]] = respuesta.json()["eventos"]
    return eventos


async def _trayectoria(seguimiento: Seguimiento) -> dict[str, uuid.UUID]:
    """Caso A: la versión del fixture, una revisión de estructura que acepta y luego cambia
    a "con cambios", y una búsqueda sin evidencia suficiente en la que continúa."""
    reloj = seguimiento.entorno.reloj
    reloj.avanzar(minutes=10)
    estructura = _entregada(seguimiento, TipoSolicitud.REVISION_ESTRUCTURA, intentos=2)
    reloj.avanzar(minutes=10)
    assert (await _decidir(seguimiento, estructura, "aceptar")).status_code == 201
    reloj.avanzar(minutes=10)
    assert (await _decidir(seguimiento, estructura, "modificar")).status_code == 201
    reloj.avanzar(minutes=10)
    evidencia = seguimiento.crear(
        TipoSolicitud.BUSQUEDA_EVIDENCIA, estado="entregada", ref=CONSULTA_A
    )
    consultar(
        seguimiento.entorno.url_bd,
        "INSERT INTO resultado (caso_id, solicitud_id, intento, salida, etiqueta, abstencion,"
        " creado_en) VALUES (%s, %s, 1, %s, 'sin_evidencia_suficiente', true, %s)"
        " RETURNING id",
        seguimiento.caso_id,
        evidencia,
        '{"modelo": {"proveedor": "simulado", "modelo": "modelo-ficticio"}}',
        reloj(),
    )
    reloj.avanzar(minutes=5)
    assert (await _decidir(seguimiento, evidencia, "continuar")).status_code == 201
    return {"estructura": estructura, "evidencia": evidencia}


async def test_cp20_cada_caso_ve_solo_su_trayectoria_en_orden_cronologico(
    seguimiento: Seguimiento, investigador: httpx.AsyncClient
) -> None:
    ids = await _trayectoria(seguimiento)
    otro = await _caso(seguimiento.entorno, investigador, "CASO-B")
    eventos = await _historial(seguimiento.cliente)
    momentos = [datetime.fromisoformat(e["momento"]) for e in eventos]
    assert momentos == sorted(momentos)
    assert [e["clase"] for e in eventos] == [
        "version",
        "solicitud",
        "resultado",
        "decision",
        "decision",
        "solicitud",
        "resultado",
        "decision",
    ]
    assert {e["hito"] for e in eventos} == {"avance_1"}
    assert eventos[2]["etiqueta"] == "verificada" and "reintento" in eventos[2]["descripcion"]
    decisiones = [e for e in eventos if e["clase"] == "decision"]
    assert [(d["opcion"], d["vigente"]) for d in decisiones] == [
        ("aceptar", False),
        ("modificar", True),
        ("continuar", True),
    ]
    assert CONSULTA_A in eventos[5]["descripcion"]
    # El caso B ve solo su versión: nada de las solicitudes ni decisiones de A.
    eventos_b = await _historial(otro)
    assert [e["clase"] for e in eventos_b] == ["version"]
    assert not {str(i) for i in ids.values()} & {e["solicitud_id"] for e in eventos_b}
    resumen_b = await otro.get("/caso/historial/resumen")
    assert CONSULTA_A not in resumen_b.text and "CASO-B" in resumen_b.text
    await otro.aclose()


async def test_filtros_por_hito_y_por_periodo(seguimiento: Seguimiento) -> None:
    ids = await _trayectoria(seguimiento)
    # La sesión vence si el reloj avanza un día: se mueve a mano lo que pasó "al día
    # siguiente" (el cambio de decisión y la búsqueda de evidencia).
    url = seguimiento.entorno.url_bd
    consultar(
        url,
        "UPDATE solicitud SET creada_en = creada_en + interval '1 day' WHERE id = %s RETURNING id",
        ids["evidencia"],
    )
    consultar(
        url,
        "UPDATE resultado SET creado_en = creado_en + interval '1 day'"
        " WHERE solicitud_id = %s RETURNING id",
        ids["evidencia"],
    )
    consultar(
        url,
        "UPDATE decision SET decidida_en = decidida_en + interval '1 day'"
        " WHERE opcion IN ('modificar', 'continuar') RETURNING id",
    )
    assert await _historial(seguimiento.cliente, hito="avance_2") == []
    assert len(await _historial(seguimiento.cliente, hito="avance_1")) == 8
    # El fixture empieza el 6 de noviembre a las 12:00 UTC (7:00 en Lima); el cambio de
    # decisión y la búsqueda de evidencia son del día siguiente.
    del_dia_7 = await _historial(seguimiento.cliente, desde="2026-11-07", hasta="2026-11-07")
    assert [e["clase"] for e in del_dia_7] == [
        "decision",
        "solicitud",
        "resultado",
        "decision",
    ]
    assert await _historial(seguimiento.cliente, desde="2026-12-01") == []
    invertido = await seguimiento.cliente.get(
        "/caso/historial", params={"desde": "2026-11-08", "hasta": "2026-11-01"}
    )
    assert invertido.status_code == 422 and invertido.json()["codigo"] == "periodo_invalido"


async def test_el_resumen_se_descarga_para_la_declaracion(seguimiento: Seguimiento) -> None:
    await _trayectoria(seguimiento)
    respuesta = await seguimiento.cliente.get("/caso/historial/resumen")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/plain")
    assert respuesta.headers["content-disposition"].startswith("attachment;")
    texto = respuesta.text
    ((codigo,),) = consultar(
        seguimiento.entorno.url_bd, "SELECT codigo FROM caso WHERE id = %s", seguimiento.caso_id
    )
    assert f"Caso: {codigo}" in texto
    assert "Solicitudes: 2 pedidas, 2 entregadas." in texto
    assert "La usará con cambios: 1" in texto and "La aceptó" not in texto  # solo vigentes
    assert "Continuó sin aportar una fuente: 1" in texto
    assert "de estructura y coherencia tras un reintento. Etiqueta: Verificada." in texto
    assert "modelo-ficticio (simulado)" in texto
    assert CONSULTA_A in texto
    assert "\u2014" not in texto and "\u2013" not in texto  # sin guiones largos
    vacio = await seguimiento.cliente.get("/caso/historial/resumen", params={"desde": "2026-12-01"})
    assert "Sin registros en este periodo." in vacio.text


async def test_el_panel_muestra_la_etiqueta_de_cada_solicitud(seguimiento: Seguimiento) -> None:
    ids = await _trayectoria(seguimiento)
    en_cola = seguimiento.crear(TipoSolicitud.PLAN_TAREA)
    respuesta = await seguimiento.cliente.get("/caso/solicitudes")
    etiquetas = {s["id"]: s["etiqueta"] for s in respuesta.json()}
    assert etiquetas[str(ids["estructura"])] == "verificada"
    assert etiquetas[str(ids["evidencia"])] == "sin_evidencia_suficiente"
    assert etiquetas[str(en_cola)] is None
