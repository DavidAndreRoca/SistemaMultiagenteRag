"""T19: validación previa de la consulta de evidencia y comprobación de acceso abierto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.administracion.parametros import ParametrosFuncionales, parametros_iniciales
from app.agentes.validacion_consulta import MENSAJES, MotivoRechazo, por_reglas
from app.verificacion.comprobaciones import comprobar_acceso_abierto

CONJUNTOS = Path(__file__).parents[3] / "evaluacion" / "conjuntos"
M = MotivoRechazo


@pytest.mark.parametrize(
    ("consulta", "motivo"),
    [
        ("ansiedad", M.MUY_CORTA),
        ("ChatGPT en clase", M.MUY_CORTA),
        ("x " * 600, M.MUY_LARGA),
        ("Redacta la introducción completa de mi artículo", M.FUERA_DE_ALCANCE),
        ("Escríbeme el marco teórico sobre el uso de ChatGPT", M.FUERA_DE_ALCANCE),
        ("Corrige este párrafo de mi borrador por favor", M.FUERA_DE_ALCANCE),
        ("Hazme la tarea de metodología de la investigación", M.FUERA_DE_ALCANCE),
        ("Traduce al inglés el resumen de mi tesis", M.FUERA_DE_ALCANCE),
        ("¿Qué opinas de mi tema de investigación?", M.AMBIGUA),
        ("Quiero saber algo sobre esto para mi trabajo", M.AMBIGUA),
        ("Necesito ayuda con mi tema por favor gracias", M.AMBIGUA),
    ],
)
def test_las_reglas_rechazan_con_su_motivo(consulta: str, motivo: MotivoRechazo) -> None:
    rechazo = por_reglas(consulta, parametros_iniciales())
    assert rechazo is not None and rechazo.motivo is motivo
    assert rechazo.mensaje == MENSAJES[motivo] and "Por ejemplo" in rechazo.mensaje


@pytest.mark.parametrize(
    "consulta",
    [
        "Quiero sustentar que la tutoría entre pares reduce la ansiedad ante la estadística",
        "¿Qué evidencia hay sobre el uso de ChatGPT en la retroalimentación académica?",
        "Busco estudios que resuman los efectos de la gamificación en el aprendizaje",
        "¿La capacitación de los microemprendedores aumenta el uso de internet en sus ventas?",
    ],
)
def test_las_reglas_aceptan_consultas_bien_formuladas(consulta: str) -> None:
    assert por_reglas(consulta, parametros_iniciales()) is None


def test_ninguna_consulta_del_conjunto_de_t16_se_rechaza_por_reglas() -> None:
    conjunto = json.loads((CONJUNTOS / "recuperacion-t16.json").read_text(encoding="utf-8"))
    rechazadas = [
        c["id"] for c in conjunto["consultas"] if por_reglas(c["consulta"], parametros_iniciales())
    ]
    assert rechazadas == []


def test_el_conjunto_de_validacion_borrador_se_cumple_con_las_reglas() -> None:
    """El borrador de ``validacion-consultas-t19.json``: las reglas aciertan en las que no
    dependen del clasificador de pertinencia (las ajenas al tema se prueban con la base)."""
    conjunto = json.loads((CONJUNTOS / "validacion-consultas-t19.json").read_text(encoding="utf-8"))
    assert conjunto["estado"] == "borrador"
    for consulta in conjunto["consultas"]:
        rechazo = por_reglas(consulta["consulta"], parametros_iniciales())
        if consulta["esperado"] == "aceptada" or consulta.get("detecta") == "pertinencia":
            assert rechazo is None, consulta["id"]
        else:
            assert rechazo is not None and rechazo.motivo.value == consulta["motivo"], consulta[
                "id"
            ]


def test_los_parametros_de_validacion_estan_en_la_configuracion() -> None:
    parametros = parametros_iniciales()
    assert (parametros.consulta_min_palabras, parametros.consulta_max_caracteres) == (5, 1000)
    assert parametros.pertinencia_umbral == 0.55
    assert parametros.versiones_instrucciones["evidencia"] == "v1"
    corta = ParametrosFuncionales(consulta_min_palabras=12)
    assert por_reglas("¿La tutoría entre pares reduce la ansiedad?", corta) is not None


def test_comprobacion_5_rechaza_citas_de_fuentes_sin_acceso_abierto() -> None:
    """CP-11: si la propuesta cita una fuente cerrada, la verificación no se supera."""
    abierta = comprobar_acceso_abierto({"F1": "gold", "F2": "green"})
    assert (abierta.numero, abierta.superada) == (5, True)
    cerrada = comprobar_acceso_abierto({"F1": "gold", "F2": "closed", "F3": "desconocido"})
    assert not cerrada.superada
    assert cerrada.motivos == [
        "cita a una fuente sin acceso abierto comprobado: F2",
        "cita a una fuente sin acceso abierto comprobado: F3",
    ]
