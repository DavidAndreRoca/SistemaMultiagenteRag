"""Consulta y orden del plan de tarea (T24)."""

from __future__ import annotations

from app.administracion.parametros import Hito
from app.agentes.plan import AtencionPlan, consulta_del_hito

HITO = Hito(orden=1, codigo="avance_1", nombre="Avance 1", contenido="Planteamiento")


def test_la_consulta_nombra_el_hito_y_lo_que_pide_sin_el_criterio() -> None:
    instrucciones = (
        "El estudiante entrega el título provisional y los objetivos. Criterio de logro: el"
        " problema y los objetivos se refieren a las mismas variables."
    )
    assert consulta_del_hito(HITO, instrucciones) == (
        "Instrucciones del programa para el hito Avance 1: Planteamiento y cómo redactar y"
        " organizar en el artículo científico el título provisional y los objetivos."
    )


def test_el_sistema_pone_el_hito_y_numera_las_tareas_en_orden() -> None:
    atencion = AtencionPlan.__new__(AtencionPlan)
    salida = {
        "hito": "otro",
        "tareas": [{"orden": 5, "tarea": "b"}, {"orden": 2, "tarea": "a"}],
        "notas_para_el_estudiante": [],
    }
    ajustada = atencion.ajustar(salida, "Hito de la versión: Avance 1: Planteamiento\n- 1. Intro")
    assert ajustada["hito"] == "Avance 1: Planteamiento"
    assert [(t["orden"], t["tarea"]) for t in ajustada["tareas"]] == [(1, "a"), (2, "b")]
