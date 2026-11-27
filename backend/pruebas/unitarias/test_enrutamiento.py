"""Enrutamiento determinista tipo a agente (T28; CP-03, RN-02)."""

from __future__ import annotations

import pytest

from app.bd.enumeraciones import TipoSolicitud
from app.orquestacion.enrutamiento import (
    TABLA_DE_AGENTES,
    AgenteSistema,
    TipoDesconocido,
    enrutar,
)

TABLA_9 = {
    "revision_estructura": "D1",
    "plan_tarea": "D1",
    "revision_metodologica": "D2",
    "propuesta_redaccion": "D3",
    "busqueda_evidencia": "D4",
    "verificacion_referencias": "D4",
}


def test_cp03_cada_tipo_va_a_un_solo_agente_segun_la_tabla_9() -> None:
    assert set(TABLA_DE_AGENTES) == set(TipoSolicitud)
    assert {t.value: enrutar(t.value).value for t in TipoSolicitud} == TABLA_9


@pytest.mark.parametrize("tipo", ["", None, "redactar_todo", "REVISION_ESTRUCTURA"])
def test_un_tipo_desconocido_es_un_error_de_validacion(tipo: str | None) -> None:
    with pytest.raises(TipoDesconocido):
        enrutar(tipo)


def test_la_tabla_no_se_puede_cambiar_en_ejecucion() -> None:
    with pytest.raises(TypeError):
        TABLA_DE_AGENTES[TipoSolicitud.PLAN_TAREA] = AgenteSistema.ESTILISTICO  # type: ignore[index]
