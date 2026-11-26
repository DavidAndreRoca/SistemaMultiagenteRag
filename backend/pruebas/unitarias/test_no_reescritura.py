"""Comprobación 2 de no reescritura para D1 y D2 (T23; CP-08)."""

from __future__ import annotations

from app.verificacion.comprobaciones import comprobar_no_reescritura

ESTUDIANTE = (
    "La ansiedad ante la estadística reduce el rendimiento de los estudiantes de primer año"
    " y afecta su permanencia en la universidad durante los primeros ciclos."
)


def _salida(recomendacion: str, nota: str = "Nota breve.") -> dict[str, object]:
    return {
        "hallazgos": [
            {
                "indicador": "secuencia_logica_discursiva",
                "ubicacion": "p3",
                "descripcion": "El párrafo mezcla dos ideas.",
                "severidad": "media",
                "recomendacion": recomendacion,
                "citas": ["F1"],
            }
        ],
        "fortalezas": [],
        "notas_para_el_estudiante": [nota],
    }


def test_textos_breves_superan_la_comprobacion() -> None:
    resultado = comprobar_no_reescritura(
        _salida("Separe las dos ideas en párrafos."), ESTUDIANTE, 40
    )
    assert resultado.superada and resultado.numero == 2


def test_un_texto_largo_propio_es_posible_reescritura() -> None:
    larga = " ".join(["Reescriba el párrafo de esta manera completa"] * 8)  # 56 palabras
    resultado = comprobar_no_reescritura(_salida(larga), ESTUDIANTE, 40)
    assert not resultado.superada
    assert resultado.motivos == [
        "posible reescritura en hallazgos[0].recomendacion: 56 palabras (límite 40)"
    ]


def test_una_cita_del_propio_estudiante_no_cuenta() -> None:
    texto = f"El párrafo dice «{ESTUDIANTE}» y conviene separar las dos ideas."
    assert comprobar_no_reescritura(_salida(texto), ESTUDIANTE, 40).superada


def test_tambien_se_revisan_las_notas() -> None:
    nota = " ".join(["Esta es una versión mejorada del texto"] * 7)
    resultado = comprobar_no_reescritura(_salida("Breve.", nota), ESTUDIANTE, 40)
    assert not resultado.superada and "notas_para_el_estudiante" in resultado.motivos[0]
