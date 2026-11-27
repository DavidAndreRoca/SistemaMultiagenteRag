"""Comprobación 2 para D3, límites de la propuesta de redacción (T27; CP-10, RN-07)."""

from __future__ import annotations

import pytest

from app.borradores.alcance import contar_palabras
from app.verificacion.comprobaciones import comprobar_limites_propuesta

ORIGINAL = (
    "En este estudio se hizo una medición de la ansiedad de 84 estudiantes [3], y se vio que"
    " la tutoría entre pares es muy importante para bajar la ansiedad."
)
PROPUESTA = (
    "En este estudio se midió la ansiedad de 84 estudiantes [3] y se observó que la tutoría"
    " entre pares contribuye a reducirla."
)


def _salida(propuesta: str = PROPUESTA, **cambio: str) -> dict[str, object]:
    return {
        "original": ORIGINAL,
        "propuesta": propuesta,
        "cambios": [
            {
                "tipo": "fluidez_y_precision_lexica",
                "antes": cambio.get("antes", "se hizo una medición de"),
                "despues": cambio.get("despues", "se midió"),
                "razon": "Verbo preciso en lugar de un verbo genérico.",
                "citas": ["F1"],
            }
        ],
        "notas_para_el_estudiante": [],
    }


def test_contar_palabras_separa_por_espacios() -> None:
    assert contar_palabras("  Uno, dos\ny  tres. ") == 4
    assert contar_palabras("") == 0


def test_una_propuesta_dentro_de_los_limites_supera_la_comprobacion() -> None:
    comprobacion = comprobar_limites_propuesta(_salida(), 1.2)
    assert comprobacion.numero == 2 and comprobacion.nombre == "limites_propuesta"
    assert comprobacion.superada, comprobacion.motivos


def test_cp10_una_propuesta_de_mas_de_1_2_veces_no_se_supera() -> None:
    larga = PROPUESTA + " " + " ".join(["Además, esto se repite."] * 8)
    assert contar_palabras(larga) > int(contar_palabras(ORIGINAL) * 1.2)
    comprobacion = comprobar_limites_propuesta(_salida(larga), 1.2)
    assert not comprobacion.superada
    assert any("palabras y el límite es" in m for m in comprobacion.motivos)


def test_justo_en_el_limite_se_supera() -> None:
    original = " ".join(["palabra"] * 10)
    salida = {"original": original, "propuesta": " ".join(["otra"] * 12), "cambios": []}
    assert comprobar_limites_propuesta(salida, 1.2).superada
    salida["propuesta"] = " ".join(["otra"] * 13)
    assert not comprobar_limites_propuesta(salida, 1.2).superada


def test_mas_de_un_parrafo_no_se_supera() -> None:
    partida = PROPUESTA.replace(" y se observó", ".\n\nSe observó")
    motivos = comprobar_limites_propuesta(_salida(partida), 1.2).motivos
    assert "la propuesta tiene más de un párrafo" in motivos


@pytest.mark.parametrize(
    "agregado",
    [
        "con un tamaño del efecto de 0,45",  # un dato que el original no tiene
        "como señala otro estudio [7]",  # una cita nueva, numérica
        "(Pérez, 2021)",  # una cita nueva, de autor y año
    ],
)
def test_un_numero_o_una_cita_nueva_no_se_supera(agregado: str) -> None:
    propuesta = PROPUESTA.replace("reducirla.", f"reducirla {agregado}.")
    motivos = comprobar_limites_propuesta(_salida(propuesta), 1.5).motivos
    assert any("números o citas que no están en el original" in m for m in motivos)


def test_conservar_las_citas_y_los_numeros_del_original_se_supera() -> None:
    assert comprobar_limites_propuesta(_salida(), 1.2).superada  # [3] y 84 se conservan


def test_un_cambio_que_no_esta_en_el_original_o_en_la_propuesta_no_se_supera() -> None:
    motivos = comprobar_limites_propuesta(
        _salida(antes="una frase que no existe", despues="otra que tampoco"), 1.2
    ).motivos
    assert "cambios[0].antes no está en el original" in motivos
    assert "cambios[0].despues no está en la propuesta" in motivos


def test_los_cambios_se_comparan_sin_puntuacion_ni_mayusculas() -> None:
    salida = _salida(antes="Se hizo una medición de,", despues="SE MIDIÓ")
    assert comprobar_limites_propuesta(salida, 1.2).superada
