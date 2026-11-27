"""Diseño declarado y comprobación de datos inventados del agente metodológico (T26)."""

from __future__ import annotations

import pytest

from app.agentes.metodologia import (
    Diseno,
    comprimir_criterios,
    consulta_de_lista,
    identificar_diseno,
)
from app.verificacion.comprobaciones import comprobar_numeros, numeros

ESTUDIANTE = (
    "## 2. Método\n[p7] Diseño correlacional con 120 estudiantes de pregrado seleccionados por"
    " conveniencia. [p8] Se usó un cuestionario de 24 ítems con alfa de 0,87."
)
GUIA = "COR-2. Se justifica el tamaño de la muestra y se describe cómo se seleccionó."


@pytest.mark.parametrize(
    ("texto", "diseno"),
    [
        ("Estudio cuasiexperimental con grupos intactos.", Diseno.CUASIEXPERIMENTAL),
        ("Diseño cuasi-experimental de dos grupos.", Diseno.CUASIEXPERIMENTAL),
        ("Un diseño experimental con asignación aleatoria.", Diseno.EXPERIMENTAL),
        ("Diseño no experimental, de alcance correlacional.", Diseno.CORRELACIONAL),
        ("Estudio descriptivo correlacional de corte transversal.", Diseno.CORRELACIONAL),
        ("Investigación DESCRIPTIVA con encuesta.", Diseno.DESCRIPTIVO),
        ("Diseño no experimental transversal.", None),
        ("Se aplicó un cuestionario a estudiantes de pregrado.", None),
    ],
)
def test_identifica_el_diseno_declarado(texto: str, diseno: Diseno | None) -> None:
    assert identificar_diseno(texto) is diseno


def test_los_numeros_ignoran_identificadores_y_normalizan_la_coma() -> None:
    texto = "En p12, H1 y COR-6 hay 120 casos con alfa de 0,87 (30 %)."
    assert numeros(texto) == {"120", "0.87", "30"}


def _salida(recomendacion: str, citas: list[str] | None = None) -> dict[str, object]:
    return {
        "hallazgos": [
            {
                "indicador": "validez_de_tecnicas_e_instrumentos",
                "ubicacion": "p7",
                "descripcion": "No se justifica el tamaño de muestra (COR-2).",
                "severidad": "media",
                "recomendacion": recomendacion,
                "citas": citas or ["F1"],
            }
        ],
        "preguntas_al_estudiante": ["¿Cómo se calculó el tamaño de la muestra de 120?"],
        "notas_para_el_estudiante": [],
    }


def test_numeros_del_estudiante_y_de_fragmentos_citados_se_admiten() -> None:
    salida = _salida("Justifique por qué 120 estudiantes bastan y cómo midió el alfa de 0.87.")
    comprobacion = comprobar_numeros(salida, ESTUDIANTE, {"F1": GUIA})
    assert comprobacion.nombre == "sin_datos_inventados" and comprobacion.superada


def test_un_valor_estadistico_inventado_se_rechaza() -> None:
    salida = _salida("Informe que la correlación fue r = 0,62 con p < 0,05.")
    comprobacion = comprobar_numeros(salida, ESTUDIANTE, {"F1": GUIA})
    assert not comprobacion.superada
    assert comprobacion.motivos == [
        "dato posiblemente inventado en hallazgos[0].recomendacion: 2 números que no están"
        " en el texto del estudiante ni en un fragmento citado"
    ]


def test_un_numero_de_un_fragmento_no_citado_no_se_admite() -> None:
    salida = _salida("Use al menos 85 participantes.", citas=["F1"])
    fragmentos = {"F1": GUIA, "F2": "Se recomiendan al menos 85 participantes."}
    assert not comprobar_numeros(salida, ESTUDIANTE, fragmentos).superada
    citando = _salida("Use al menos 85 participantes.", citas=["F1", "F2"])
    assert comprobar_numeros(citando, ESTUDIANTE, fragmentos).superada


def test_la_consulta_abrevia_los_criterios_del_corpus_sin_sus_codigos() -> None:
    criterios = [
        "COR-1. Se nombran las variables que se relacionan y cómo se mide cada una.\n"
        "COR-6. La interpretación no afirma causalidad.",
        "GEN-2. Se informan los criterios de inclusión y exclusión de los participantes.",
    ]
    assert comprimir_criterios(criterios, 5) == (
        "Se nombran las variables que; La interpretación no afirma causalidad;"
        " Se informan los criterios de"
    )
    consulta = consulta_de_lista(Diseno.CORRELACIONAL, criterios)
    assert consulta.startswith("Criterios mínimos del diseño correlacional y elementos comunes")
    assert "COR-" not in consulta and "GEN-" not in consulta
    assert consulta_de_lista(None, criterios).startswith(
        "Criterios mínimos que debe informar la sección de método"
    )
