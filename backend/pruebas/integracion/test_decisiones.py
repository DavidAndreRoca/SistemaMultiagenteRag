"""Decisiones y contadores con la base real (T31; CP-18, CP-19, RN-08, aislamiento).

Reutiliza el fixture ``seguimiento`` de T29: cada prueba lo recibe como parámetro, y ruff lo
toma por una redefinición del nombre importado.
"""

# ruff: noqa: F811

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest

from app.bd.enumeraciones import TipoSolicitud
from pruebas.integracion.conftest import consultar
from pruebas.integracion.test_estructura import _caso
from pruebas.integracion.test_seguimiento import Seguimiento, seguimiento  # noqa: F401

pytestmark = pytest.mark.integracion


def _entregada(
    seguimiento: Seguimiento,
    tipo: TipoSolicitud,
    *,
    abstencion: bool = False,
    intentos: int = 1,
) -> uuid.UUID:
    """Una solicitud entregada con su resultado final (y, si hubo reintento, el anterior)."""
    solicitud_id = seguimiento.crear(tipo, estado="entregada")
    for intento in range(1, intentos + 1):
        etiqueta = (
            "sin_evidencia_suficiente"
            if abstencion
            else "verificada"
            if intento == intentos
            else "con_advertencias"
        )
        consultar(
            seguimiento.entorno.url_bd,
            "INSERT INTO resultado (caso_id, solicitud_id, intento, salida, etiqueta, abstencion,"
            " creado_en) VALUES (%s, %s, %s, '{}', %s, %s, %s) RETURNING id",
            seguimiento.caso_id,
            solicitud_id,
            intento,
            etiqueta,
            abstencion,
            seguimiento.entorno.reloj(),
        )
    return solicitud_id


async def _decidir(
    seguimiento: Seguimiento, solicitud_id: uuid.UUID, opcion: str
) -> httpx.Response:
    return await seguimiento.cliente.post(
        f"/caso/solicitudes/{solicitud_id}/decision", json={"opcion": opcion}
    )


async def _vista(seguimiento: Seguimiento, solicitud_id: uuid.UUID) -> dict[str, Any]:
    respuesta = await seguimiento.cliente.get(f"/caso/solicitudes/{solicitud_id}/decision")
    assert respuesta.status_code == 200, respuesta.text
    datos: dict[str, Any] = respuesta.json()
    return datos


async def _contadores(seguimiento: Seguimiento) -> dict[str, Any]:
    respuesta = await seguimiento.cliente.get("/caso/contadores")
    assert respuesta.status_code == 200, respuesta.text
    datos: dict[str, Any] = respuesta.json()
    return datos


async def test_cp18_cada_decision_queda_asociada_y_cuenta_una_vez_por_tipo(
    seguimiento: Seguimiento,
) -> None:
    pedidos = {
        TipoSolicitud.REVISION_ESTRUCTURA: "aceptar",
        TipoSolicitud.PROPUESTA_REDACCION: "modificar",
        TipoSolicitud.REVISION_METODOLOGICA: "rechazar",
    }
    for tipo, opcion in pedidos.items():
        solicitud_id = _entregada(seguimiento, tipo)
        assert (await _vista(seguimiento, solicitud_id))["opciones"] == [
            "aceptar",
            "modificar",
            "rechazar",
        ]
        respuesta = await _decidir(seguimiento, solicitud_id, opcion)
        assert respuesta.status_code == 201, respuesta.text
        vista = await _vista(seguimiento, solicitud_id)
        assert vista["vigente"]["opcion"] == opcion and vista["vigente"]["reemplaza_a"] is None
    por_tipo = {c["tipo"]: c for c in (await _contadores(seguimiento))["por_tipo"]}
    assert por_tipo["revision_estructura"]["aceptar"] == 1
    assert por_tipo["propuesta_redaccion"]["modificar"] == 1
    assert por_tipo["revision_metodologica"]["rechazar"] == 1
    assert sum(sum(v for k, v in c.items() if k != "tipo") for c in por_tipo.values()) == 3


async def test_cambiar_de_decision_la_reemplaza_y_conserva_las_dos(
    seguimiento: Seguimiento,
) -> None:
    solicitud_id = _entregada(seguimiento, TipoSolicitud.BUSQUEDA_EVIDENCIA)
    primera = (await _decidir(seguimiento, solicitud_id, "aceptar")).json()
    segunda = (await _decidir(seguimiento, solicitud_id, "rechazar")).json()
    assert segunda["reemplaza_a"] == primera["id"]
    vista = await _vista(seguimiento, solicitud_id)
    assert vista["vigente"]["id"] == segunda["id"]
    assert [d["opcion"] for d in vista["historial"]] == ["aceptar", "rechazar"]
    # La primera sigue en la base sin cambios: nunca se edita.
    assert consultar(
        seguimiento.entorno.url_bd,
        "SELECT opcion FROM decision WHERE id = %s",
        uuid.UUID(primera["id"]),
    ) == [("aceptar",)]
    (contador,) = (await _contadores(seguimiento))["por_tipo"]
    assert (contador["aceptar"], contador["rechazar"]) == (0, 1)  # solo cuenta la vigente
    repetida = await _decidir(seguimiento, solicitud_id, "rechazar")
    assert repetida.status_code == 409 and repetida.json()["codigo"] == "decision_repetida"


async def test_cp19_tras_una_abstencion_se_registra_continuar(seguimiento: Seguimiento) -> None:
    solicitud_id = _entregada(seguimiento, TipoSolicitud.BUSQUEDA_EVIDENCIA, abstencion=True)
    assert (await _vista(seguimiento, solicitud_id))["opciones"] == ["continuar", "aportar"]
    aceptar = await _decidir(seguimiento, solicitud_id, "aceptar")
    assert aceptar.status_code == 422 and aceptar.json()["codigo"] == "opcion_no_admitida"
    assert (await _decidir(seguimiento, solicitud_id, "continuar")).status_code == 201
    ((abstencion, opcion),) = consultar(
        seguimiento.entorno.url_bd,
        "SELECT r.abstencion, d.opcion FROM decision d JOIN resultado r ON r.id = d.resultado_id"
        " WHERE r.solicitud_id = %s",
        solicitud_id,
    )
    assert (abstencion, opcion) == (True, "continuar")  # la abstención y la elección


async def test_la_decision_va_al_resultado_final_tras_un_reintento(
    seguimiento: Seguimiento,
) -> None:
    solicitud_id = _entregada(seguimiento, TipoSolicitud.PLAN_TAREA, intentos=2)
    assert (await _decidir(seguimiento, solicitud_id, "aceptar")).status_code == 201
    assert consultar(
        seguimiento.entorno.url_bd,
        "SELECT r.intento FROM decision d JOIN resultado r ON r.id = d.resultado_id",
    ) == [(2,)]


async def test_sin_resultado_entregado_no_se_decide(seguimiento: Seguimiento) -> None:
    en_cola = seguimiento.crear(TipoSolicitud.PLAN_TAREA)
    assert (await _vista(seguimiento, en_cola))["opciones"] == []
    respuesta = await _decidir(seguimiento, en_cola, "aceptar")
    assert respuesta.status_code == 409 and respuesta.json()["codigo"] == "sin_resultado"


async def test_uso_minimo_por_hito(seguimiento: Seguimiento) -> None:
    _entregada(seguimiento, TipoSolicitud.PLAN_TAREA)
    seguimiento.crear(TipoSolicitud.PLAN_TAREA)  # en cola: no cuenta
    por_hito = {h["hito"]: h for h in (await _contadores(seguimiento))["por_hito"]}
    assert por_hito["avance_1"] == {
        "hito": "avance_1",
        "nombre": "Avance 1: Planteamiento",
        "solicitudes": 1,
        "minimo": 1,
        "cumple": True,
    }
    assert por_hito["avance_2"]["solicitudes"] == 0 and por_hito["avance_2"]["cumple"] is False


async def test_un_caso_no_decide_ni_ve_los_contadores_de_otro(
    seguimiento: Seguimiento, investigador: httpx.AsyncClient
) -> None:
    solicitud_id = _entregada(seguimiento, TipoSolicitud.REVISION_ESTRUCTURA)
    await _decidir(seguimiento, solicitud_id, "aceptar")
    otro = await _caso(seguimiento.entorno, investigador, "CASO-B")
    ajena = await otro.post(
        f"/caso/solicitudes/{solicitud_id}/decision", json={"opcion": "rechazar"}
    )
    assert ajena.status_code == 404
    assert (await otro.get(f"/caso/solicitudes/{solicitud_id}/decision")).status_code == 404
    assert (await otro.get("/caso/contadores")).json()["por_tipo"] == []
    await otro.aclose()


async def test_tras_otra_abstencion_solo_se_continua(seguimiento: Seguimiento) -> None:
    """Aportar una fuente solo sirve a la búsqueda de evidencia (T32): la colección personal
    la recupera solo D4."""
    solicitud_id = _entregada(seguimiento, TipoSolicitud.PLAN_TAREA, abstencion=True)
    assert (await _vista(seguimiento, solicitud_id))["opciones"] == ["continuar"]
    aportar = await _decidir(seguimiento, solicitud_id, "aportar")
    assert aportar.status_code == 422 and aportar.json()["codigo"] == "opcion_no_admitida"
