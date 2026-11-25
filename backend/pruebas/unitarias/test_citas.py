"""Extractores de citas en el texto por norma y cruce con la lista (T20, actividades 2 y 5)."""

from __future__ import annotations

import pytest

from app.agentes.citas import (
    EntradaLista,
    cruzar,
    entrada_desde_texto,
    extraer_citas,
)
from app.agentes.referencias import anio_del_texto
from app.borradores.extraccion import ParrafoBorrador


def _parrafos(*textos: str) -> list[ParrafoBorrador]:
    return [
        ParrafoBorrador(id=f"p{i}", texto=t, estilo=None, origen="cuerpo")
        for i, t in enumerate(textos, start=1)
    ]


def _numeros(norma: str, texto: str) -> list[list[int]]:
    return [c.numeros for c in extraer_citas(_parrafos(texto), norma)]


# ------------------------------------------------------------------ numéricas (IEEE)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Como muestra [1], el efecto es claro.", [[1]]),
        ("Varios estudios [1], [3] lo confirman.", [[1], [3]]),
        ("Hay acuerdo [1]\u2013[3] en la literatura.", [[1, 2, 3]]),
        ("Hay acuerdo [1]-[3] en la literatura.", [[1, 2, 3]]),
        ("Hay acuerdo [2\u20134] y también [7, 9].", [[2, 3, 4], [7, 9]]),
        ("Con espacios [ 5 ] y rangos [1-2, 6].", [[5], [1, 2, 6]]),
        ("Sin citas: la Tabla 2 y la ecuación (3).", []),
        ("Corchetes que no son citas [sic] ni [n = 40].", []),
    ],
)
def test_ieee_extrae_citas_numericas(texto: str, esperado: list[list[int]]) -> None:
    assert _numeros("ieee", texto) == esperado


def test_un_rango_invertido_o_enorme_no_se_expande() -> None:
    assert _numeros("ieee", "Mal escrito [5\u20132] y exagerado [1\u2013900].") == [
        [5, 2],
        [1, 900],
    ]


def test_la_cita_conserva_el_texto_y_el_parrafo() -> None:
    (cita,) = extraer_citas(_parrafos("Texto previo.", "Se observa [1]\u2013[3]."), "ieee")
    assert (cita.texto, cita.parrafo) == ("[1]\u2013[3]", "p2")


# ------------------------------------------------------------- numéricas (Vancouver)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Se ha descrito (1) y confirmado (2,3).", [[1], [2, 3]]),
        ("Rangos (1-3) y listas (4, 6\u20137).", [[1, 2, 3], [4, 6, 7]]),
        ("También con corchetes [5].", [[5]]),
        ("Un año entre paréntesis (2020) no es cita.", []),
        ("Ni (n = 30) ni (p < 0,05).", []),
    ],
)
def test_vancouver_extrae_citas_numericas(texto: str, esperado: list[list[int]]) -> None:
    assert _numeros("vancouver", texto) == esperado


def test_ieee_no_toma_parentesis_como_citas() -> None:
    assert _numeros("ieee", "Se ha descrito (1) antes.") == []


# ------------------------------------------------------------------ autor y año (APA 7)


def _obras(texto: str) -> list[list[tuple[str, str | None]]]:
    return [
        [(o.apellido, o.anio) for o in c.obras] for c in extraer_citas(_parrafos(texto), "apa7")
    ]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("La evidencia es clara (García, 2020).", [[("garcia", "2020")]]),
        ("Lo confirman (García & López, 2021).", [[("garcia", "2021")]]),
        ("Lo confirman (García y López, 2021).", [[("garcia", "2021")]]),
        ("Hay riesgos (Kasneci et al., 2023).", [[("kasneci", "2023")]]),
        (
            "Varias obras (García, 2020; Pérez et al., 2019).",
            [[("garcia", "2020"), ("perez", "2019")]],
        ),
        ("Mismo autor (García, 2019, 2021).", [[("garcia", "2019"), ("garcia", "2021")]]),
        ("Con letra (García, 2020a, 2020b).", [[("garcia", "2020a"), ("garcia", "2020b")]]),
        ("Con página (García, 2020, p. 14).", [[("garcia", "2020")]]),
        ("Sin fecha (Ministerio de Educación, s. f.).", [[("ministerio de educacion", "s. f.")]]),
        ("Kasneci et al. (2023) señalan riesgos.", [[("kasneci", "2023")]]),
        ("Según García y López (2021), el efecto es claro.", [[("garcia", "2021")]]),
        ("Como dice García (2020, p. 3), hay acuerdo.", [[("garcia", "2020")]]),
        ("Con apellido compuesto (García Márquez, 2018).", [[("garcia marquez", "2018")]]),
        ("Un año suelto en 2020 (sin autor) no es cita.", []),
        ("Una lista numérica [1] no es APA.", []),
        ("Entre paréntesis sin año (véase la Tabla 2).", []),
    ],
)
def test_apa7_extrae_autor_y_anio(texto: str, esperado: list[list[tuple[str, str | None]]]) -> None:
    assert _obras(texto) == esperado


def test_apa7_no_toma_palabras_de_enlace_como_autores() -> None:
    assert _obras("Durante la pandemia (2020) cambió todo. En (2021) también.") == []


# ----------------------------------------------------------------------- entradas


def test_entrada_desde_texto_apa_toma_primer_apellido_anio_y_letra() -> None:
    entrada = entrada_desde_texto(
        3, "García, A., & López, B. (2020b). Un título ficticio. Revista Ficticia, 4(2), 1-9."
    )
    assert (entrada.indice, entrada.apellido, entrada.anio) == (3, "garcia", "2020b")


def test_entrada_desde_texto_sin_fecha() -> None:
    entrada = entrada_desde_texto(1, "Ministerio de Educación. (s. f.). Guía ficticia.")
    assert (entrada.apellido, entrada.anio) == ("ministerio de educacion", "s. f.")


def test_entrada_apa_con_apellido_compuesto_no_usa_el_de_grobid() -> None:
    """GROBID parte "Alarcón Llontop" y devuelve solo "Llontop"."""
    entrada = entrada_desde_texto(
        2, "Alarcón Llontop, L. R., & Pasapera, S. (2023). Título.", apellido="Llontop", anio=2023
    )
    assert entrada.apellido == "alarcon llontop"


def test_entrada_usa_el_apellido_de_grobid_si_lo_hay() -> None:
    entrada = entrada_desde_texto(1, "[1] A. García, “Título,” 2020.", apellido="García", anio=2020)
    assert (entrada.apellido, entrada.anio) == ("garcia", "2020")


# ------------------------------------------------------------------------ cruce


def _lista_numerica(cantidad: int) -> list[EntradaLista]:
    return [EntradaLista(indice=i, texto=f"[{i}] Ficticia {i}") for i in range(1, cantidad + 1)]


def test_cruce_numerico_detecta_citas_sin_entrada_y_entradas_no_citadas() -> None:
    citas = extraer_citas(
        _parrafos("Uno [1], rango [2]\u2013[3] y otro [9].", "Repite [1] y [3]."), "ieee"
    )
    cruce = cruzar(citas, _lista_numerica(5), "ieee")
    assert cruce.citas_sin_entrada == ["[9]"]
    assert cruce.entradas_no_citadas == [4, 5]
    assert [c.destinos for c in cruce.citas] == [[1], [2, 3], [], [1], [3]]


def test_cruce_numerico_con_parte_del_rango_sin_entrada() -> None:
    cruce = cruzar(
        extraer_citas(_parrafos("Rango [2\u20134]."), "ieee"), _lista_numerica(3), "ieee"
    )
    assert cruce.citas_sin_entrada == ["[4]"]
    assert cruce.citas[0].destinos == [2, 3]


def test_cruce_apa_por_apellido_y_anio() -> None:
    entradas = [
        entrada_desde_texto(1, "García, A. (2020a). Uno. Revista, 1, 1-2."),
        entrada_desde_texto(2, "García, A. (2020b). Dos. Revista, 1, 3-4."),
        entrada_desde_texto(3, "Kasneci, E., Seßler, K., & Küchemann, S. (2023). Tres."),
        entrada_desde_texto(4, "Pérez, C. (2019). Cuatro. Revista, 2, 5-6."),
        entrada_desde_texto(5, "Quispe, D. (2018). Cinco. Revista, 3, 7-8."),
    ]
    citas = extraer_citas(
        _parrafos(
            "Primero (García, 2020a) y luego Kasneci et al. (2023).",
            "Además (Pérez, 2021; López, 2017) y (garcía, 2020b).",
        ),
        "apa7",
    )
    cruce = cruzar(citas, entradas, "apa7")
    assert [c.destinos for c in cruce.citas] == [[1], [3], [], [2]]
    assert cruce.citas_sin_entrada == ["(Pérez, 2021)", "(López, 2017)"]
    assert cruce.entradas_no_citadas == [4, 5]


def test_cruce_apa_sin_letra_acepta_una_sola_obra_del_anio() -> None:
    entradas = [entrada_desde_texto(1, "García, A. (2020). Uno.")]
    cruce = cruzar(extraer_citas(_parrafos("Así (García, 2020)."), "apa7"), entradas, "apa7")
    assert cruce.citas[0].destinos == [1] and cruce.entradas_no_citadas == []


def test_cruce_apa_con_apellido_compuesto_o_sin_tildes() -> None:
    entradas = [entrada_desde_texto(1, "García Márquez, G. (2018). Uno.")]
    citas = extraer_citas(_parrafos("Uno (Garcia Marquez, 2018) y García Márquez (2018)."), "apa7")
    assert [c.destinos for c in cruzar(citas, entradas, "apa7").citas] == [[1], [1]]


def test_una_cita_repetida_sin_entrada_se_informa_una_vez() -> None:
    cruce = cruzar(
        extraer_citas(_parrafos("Uno [7].", "Otra vez [7]."), "ieee"), _lista_numerica(2), "ieee"
    )
    assert cruce.citas_sin_entrada == ["[7]"]


def test_norma_desconocida_falla() -> None:
    with pytest.raises(ValueError, match="norma"):
        extraer_citas(_parrafos("Algo [1]."), "chicago")


@pytest.mark.parametrize(
    ("entrada", "anio"),
    [
        (
            "[1] A. Ali, \u201cXAI,\u201d Inf. Fusion, vol. 99, pp. 101805, 2023,"
            " doi: 10.1016/j.inffus.2023.101805.",
            2023,
        ),
        (
            "Torres, C. (2022). Escritura. Cuadernos, 4(2), 10-25."
            " https://doi.org/10.5555/t20.torres.2021",
            2022,
        ),
        ("[3] B. Ramos, Metodología. Lima: Editorial, 2015.", 2015),
        ("Sin fecha alguna, doi: 10.5555/t20.2019.1", None),
    ],
)
def test_anio_del_texto_ignora_el_doi(entrada: str, anio: int | None) -> None:
    assert anio_del_texto(entrada) == anio
