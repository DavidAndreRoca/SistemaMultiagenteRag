"""T09: división en oraciones y segmentación con ventana y solapamiento (textos controlados).

El contador simulado cuenta una palabra como un token, para que la ventana sea exacta.
"""

from __future__ import annotations

import pytest

from app.administracion.parametros import VentanaTokens
from app.bd.enumeraciones import SeccionNormalizada as S
from app.corpus.secciones import Parrafo, SeccionTexto
from app.corpus.segmentacion import dividir_oraciones, segmentar


class PorPalabras:
    def contar(self, texto: str) -> int:
        return len(texto.split())


VENTANA = VentanaTokens(minimo=60, maximo=90, objetivo=80)


def oracion(n: int, palabras: int = 10) -> str:
    """Oración identificable de ``palabras`` palabras: "O7 w w w ... fin."."""
    return " ".join([f"O{n}", *["w"] * (palabras - 2), "fin."])


def parrafo_de(*numeros: int, palabras: int = 10, pagina: int = 1) -> Parrafo:
    return Parrafo(" ".join(oracion(n, palabras) for n in numeros), pagina, pagina)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Primera oración. Segunda oración.", ["Primera oración.", "Segunda oración."]),
        ("¿Funciona? ¡Sí! Bien.", ["¿Funciona?", "¡Sí!", "Bien."]),
        (
            "Según Pérez et al. (2020) funciona. Fin.",
            ["Según Pérez et al. (2020) funciona.", "Fin."],
        ),
        ("Ver Fig. 2 y la Tabla 1. Luego sigue.", ["Ver Fig. 2 y la Tabla 1.", "Luego sigue."]),
        ("Tabla 1. Puntajes por grupo", ["Tabla 1.", "Puntajes por grupo"]),
        ("El valor fue 0.05 en total. Otra.", ["El valor fue 0.05 en total.", "Otra."]),
        ("J. R. Smith lo propuso. Bien.", ["J. R. Smith lo propuso.", "Bien."]),
        ("aprox. el doble. Después.", ["aprox. el doble.", "Después."]),
        ("Dijo: «Basta.» Luego calló.", ["Dijo: «Basta.»", "Luego calló."]),
        ("In 2020. 48 students slept.", ["In 2020.", "48 students slept."]),
        ("Sin punto final", ["Sin punto final"]),
        ("", []),
    ],
)
def test_divide_oraciones_sin_cortar_abreviaturas(texto: str, esperado: list[str]) -> None:
    assert dividir_oraciones(texto) == esperado


def seccion(clase: S, titulo: str, *parrafos: Parrafo) -> SeccionTexto:
    return SeccionTexto(clase, titulo, list(parrafos))


def test_agrupa_parrafos_hasta_la_ventana_y_solapa_una_oracion() -> None:
    # Cinco párrafos de 30 palabras (3 oraciones de 10): caben 3 párrafos (90 tokens).
    parrafos = [parrafo_de(3 * i + 1, 3 * i + 2, 3 * i + 3, pagina=i + 1) for i in range(5)]
    fragmentos = segmentar([seccion(S.METODOS, "Método", *parrafos)], PorPalabras(), VENTANA)
    assert [f.tokens for f in fragmentos] == [90, 70]
    primero, segundo = fragmentos
    assert primero.texto.split("\n")[0].startswith("O1 ")
    assert primero.texto.count("\n") == 2  # tres párrafos
    # El segundo empieza con la última oración del primero (O9) y sigue con O10.
    assert segundo.texto.startswith(oracion(9))
    assert segundo.texto.split("\n")[1].startswith("O10 ")
    assert (primero.pagina_inicio, primero.pagina_fin) == (1, 3)
    assert (segundo.pagina_inicio, segundo.pagina_fin) == (3, 5)
    assert [f.orden for f in fragmentos] == [0, 1]
    assert all(
        f.seccion_normalizada is S.METODOS and f.seccion_original == "Método" for f in fragmentos
    )


def test_ningun_fragmento_supera_el_maximo_y_casi_todos_alcanzan_el_minimo() -> None:
    parrafos = [parrafo_de(*range(10 * i, 10 * i + 4 + i % 3), palabras=13) for i in range(12)]
    fragmentos = segmentar([seccion(S.RESULTADOS, "Resultados", *parrafos)], PorPalabras(), VENTANA)
    assert all(f.tokens <= VENTANA.maximo for f in fragmentos)
    assert all(f.tokens >= VENTANA.minimo for f in fragmentos[:-1])


def test_un_parrafo_largo_se_divide_por_oraciones() -> None:
    largo = parrafo_de(*range(1, 13))  # 120 palabras en 12 oraciones
    fragmentos = segmentar([seccion(S.DISCUSION, "Discusión", largo)], PorPalabras(), VENTANA)
    # 90 (O1 a O9) y luego O9 de solapamiento más O10 a O12: el último queda corto.
    assert [f.tokens for f in fragmentos] == [90, 40]
    assert fragmentos[1].texto.startswith(oracion(9))


def test_una_oracion_mas_larga_que_el_maximo_se_parte_por_palabras() -> None:
    enorme = Parrafo(" ".join(["palabra"] * 200) + ".", 4, 4)
    fragmentos = segmentar([seccion(S.RESULTADOS, "R", enorme)], PorPalabras(), VENTANA)
    assert sum(f.tokens for f in fragmentos) == 200
    assert all(f.tokens <= VENTANA.maximo for f in fragmentos)
    assert all((f.pagina_inicio, f.pagina_fin) == (4, 4) for f in fragmentos)


def test_las_secciones_no_se_mezclan_ni_se_solapan() -> None:
    secciones = [
        seccion(S.INTRODUCCION, "Introducción", parrafo_de(1, 2)),
        seccion(S.METODOS, "Método", parrafo_de(3, 4)),
    ]
    fragmentos = segmentar(secciones, PorPalabras(), VENTANA)
    assert [(f.seccion_normalizada, f.texto) for f in fragmentos] == [
        (S.INTRODUCCION, f"{oracion(1)} {oracion(2)}"),
        (S.METODOS, f"{oracion(3)} {oracion(4)}"),
    ]


def test_las_subsecciones_de_la_misma_seccion_forman_un_tramo() -> None:
    secciones = [
        seccion(S.METODOS, "2.1. Participantes", parrafo_de(1, 2)),
        seccion(S.METODOS, "2.2. Instrumentos", parrafo_de(3, 4)),
        seccion(S.METODOS, "2.3. Procedimiento", parrafo_de(5, 6)),
    ]
    (fragmento,) = segmentar(secciones, PorPalabras(), VENTANA)
    assert fragmento.tokens == 60
    assert fragmento.seccion_original == "2.1. Participantes"


def test_cierra_en_el_borde_del_parrafo_si_ya_alcanzo_el_minimo() -> None:
    parrafos = [parrafo_de(*range(1, 8)), parrafo_de(8, 9, 10)]  # 70 y 30 tokens
    fragmentos = segmentar([seccion(S.RESULTADOS, "R", *parrafos)], PorPalabras(), VENTANA)
    assert [f.tokens for f in fragmentos] == [70, 40]
    assert fragmentos[0].texto == parrafos[0].texto
    assert fragmentos[1].texto == f"{oracion(7)}\n{parrafos[1].texto}"


def test_sin_solapamiento() -> None:
    parrafos = [parrafo_de(3 * i + 1, 3 * i + 2, 3 * i + 3) for i in range(5)]
    fragmentos = segmentar(
        [seccion(S.METODOS, "M", *parrafos)], PorPalabras(), VENTANA, solapamiento=0
    )
    assert [f.tokens for f in fragmentos] == [90, 60]
    assert fragmentos[1].texto.startswith("O10 ")


def test_solapamiento_negativo_es_un_error() -> None:
    with pytest.raises(ValueError, match="solapamiento"):
        segmentar([], PorPalabras(), VENTANA, solapamiento=-1)


def test_la_oracion_de_solapamiento_extiende_las_paginas() -> None:
    parrafos = [
        parrafo_de(1, 2, 3, pagina=1),
        parrafo_de(4, 5, 6, pagina=2),
        parrafo_de(7, 8, 9, pagina=3),
        parrafo_de(10, 11, 12, pagina=4),
    ]
    fragmentos = segmentar([seccion(S.METODOS, "M", *parrafos)], PorPalabras(), VENTANA)
    assert (fragmentos[1].pagina_inicio, fragmentos[1].pagina_fin) == (3, 4)
