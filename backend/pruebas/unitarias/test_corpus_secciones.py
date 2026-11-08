"""T09: normalización de secciones a IMRaD y exclusión de referencias y agradecimientos."""

from __future__ import annotations

import pytest

from app.bd.enumeraciones import SeccionNormalizada as S
from app.corpus.bloques import Bloque, TipoBloque
from app.corpus.secciones import SeccionExcluida, clasificar_titulo, seccionar, titulo_completo

T = TipoBloque


def titulo(texto: str, pagina: int = 1) -> Bloque:
    return Bloque(tipo=T.TITULO_SECCION, texto=texto, pagina_inicio=pagina, pagina_fin=pagina)


def parrafo(texto: str, pagina: int = 1) -> Bloque:
    return Bloque(tipo=T.PARRAFO, texto=texto, pagina_inicio=pagina, pagina_fin=pagina)


@pytest.mark.parametrize(
    ("texto", "clase"),
    [
        ("Resumen", S.RESUMEN),
        ("ABSTRACT", S.RESUMEN),
        ("1. Introducción", S.INTRODUCCION),
        ("I. INTRODUCTION", S.INTRODUCCION),
        ("Marco teórico", S.INTRODUCCION),
        ("Literature review", S.INTRODUCCION),
        ("2. Método", S.METODOS),
        ("Materiales y métodos", S.METODOS),
        ("Methodology", S.METODOS),
        ("2.1. Participantes", S.METODOS),
        ("Statistical analysis", S.METODOS),
        ("3 Resultados", S.RESULTADOS),
        ("Results and discussion", S.RESULTADOS),
        ("Resultados y discusión", S.RESULTADOS),
        ("IV. Discusión", S.DISCUSION),
        ("Discusión y conclusiones", S.DISCUSION),
        ("Limitations", S.DISCUSION),
        ("5. Conclusiones", S.CONCLUSIONES),
        ("Conclusion", S.CONCLUSIONES),
        ("Consideraciones finales", S.CONCLUSIONES),
        ("Referencias bibliográficas", SeccionExcluida.REFERENCIAS),
        ("REFERENCES", SeccionExcluida.REFERENCIAS),
        ("Bibliografía", SeccionExcluida.REFERENCIAS),
        ("Agradecimientos", SeccionExcluida.AGRADECIMIENTOS),
        ("Acknowledgments", SeccionExcluida.AGRADECIMIENTOS),
        ("Acknowledgements", SeccionExcluida.AGRADECIMIENTOS),
        ("Anexo A", S.OTRA),
        ("Conflicto de intereses", S.OTRA),
        ("Funding", S.OTRA),
    ],
)
def test_clasifica_titulos_en_espanol_e_ingles(texto: str, clase: object) -> None:
    assert clasificar_titulo(texto) == clase


@pytest.mark.parametrize(
    "texto",
    [
        "Tutoría entre pares y ansiedad ante la estadística",
        "Daniel Torres Medina and Ana Huanca Rojas",
        "Revista Ficticia de Educación Superior",
        "Métodos usados por estudios previos en contextos muy distintos al de este trabajo",
        "Discussing",
        "",
    ],
)
def test_no_reconoce_titulos_que_no_son_secciones(texto: str) -> None:
    assert clasificar_titulo(texto) is None


@pytest.mark.parametrize(
    ("frase", "clase"),
    [
        ("Análisis de datos", S.METODOS),
        ("Resultados y discusión", S.RESULTADOS),
        ("Discussion and conclusions", S.DISCUSION),
        ("Materiales y métodos", S.METODOS),
        ("Referencias", SeccionExcluida.REFERENCIAS),
        ("Results showed a gain", None),
        ("Resultados de la encuesta", None),
        ("Resultados y otras cosas", None),
        ("", None),
    ],
)
def test_titulo_completo_no_admite_palabras_de_mas(frase: str, clase: object) -> None:
    assert titulo_completo(frase) == clase


def test_secciona_un_articulo_y_excluye_referencias_y_agradecimientos() -> None:
    bloques = [
        parrafo("Título del artículo Autora Uno Universidad Ficticia"),
        titulo("Resumen"),
        parrafo("Este estudio ficticio analiza algo."),
        titulo("1. Introducción"),
        parrafo("Texto de introducción."),
        titulo("2. Método"),
        titulo("2.1. Participantes"),
        parrafo("Participaron 84 estudiantes.", 2),
        titulo("2.2. Instrumentos", 2),
        parrafo("Se usó una escala.", 2),
        titulo("3. Resultados", 2),
        parrafo("La media bajó.", 2),
        titulo("4. Discusión", 3),
        parrafo("Se confirma la hipótesis.", 3),
        titulo("Implicaciones para la docencia", 3),
        parrafo("Sirve en clase.", 3),
        titulo("5. Conclusiones", 3),
        parrafo("Funciona.", 3),
        titulo("Agradecimientos", 3),
        parrafo("Gracias al fondo ficticio.", 3),
        titulo("Referencias", 3),
        parrafo("Autor, A. (2020). Obra ficticia.", 3),
        titulo("Anexo A", 3),
        parrafo("Cuestionario.", 3),
    ]
    documento = seccionar(bloques)
    assert [(s.clase, s.titulo, [p.texto for p in s.parrafos]) for s in documento.secciones] == [
        (S.RESUMEN, "Resumen", ["Este estudio ficticio analiza algo."]),
        (S.INTRODUCCION, "1. Introducción", ["Texto de introducción."]),
        (S.METODOS, "2.1. Participantes", ["Participaron 84 estudiantes."]),
        (S.METODOS, "2.2. Instrumentos", ["Se usó una escala."]),
        (S.RESULTADOS, "3. Resultados", ["La media bajó."]),
        (S.DISCUSION, "4. Discusión", ["Se confirma la hipótesis."]),
        (S.DISCUSION, "Implicaciones para la docencia", ["Sirve en clase."]),
        (S.CONCLUSIONES, "5. Conclusiones", ["Funciona."]),
        (S.OTRA, "Anexo A", ["Cuestionario."]),
    ]
    assert documento.detectadas == [
        S.RESUMEN,
        S.INTRODUCCION,
        S.METODOS,
        S.RESULTADOS,
        S.DISCUSION,
        S.CONCLUSIONES,
    ]
    assert documento.tiene_imrad


def test_los_preliminares_con_titulos_no_reconocidos_no_se_segmentan() -> None:
    """Caso real del artículo en inglés: título y autores llegaron como títulos."""
    bloques = [
        titulo("Sleep duration and exam performance: a fictitious study"),
        titulo("Daniel Torres Medina and Ana Huanca Rojas"),
        parrafo("School of Health Sciences, Fictitious University"),
        titulo("Abstract"),
        parrafo("Insufficient sleep is common."),
        titulo("Unknown heading right after the abstract"),
        parrafo("Still front matter, but after a recognized section."),
    ]
    documento = seccionar(bloques)
    assert [(s.clase, s.titulo) for s in documento.secciones] == [
        (S.RESUMEN, "Abstract"),
        (S.OTRA, "Unknown heading right after the abstract"),
    ]
    assert not documento.tiene_imrad


def test_un_summary_dentro_del_cuerpo_no_reinicia_el_resumen() -> None:
    bloques = [
        titulo("Discussion"),
        parrafo("Main point."),
        titulo("Summary of findings"),
        parrafo("Short recap."),
    ]
    assert [s.clase for s in seccionar(bloques).secciones] == [S.DISCUSION, S.DISCUSION]


def test_sin_secciones_reconocidas_todo_es_otra() -> None:
    bloques = [titulo("Primera parte"), parrafo("Uno."), titulo("Segunda parte"), parrafo("Dos.")]
    documento = seccionar(bloques)
    assert [(s.clase, s.titulo) for s in documento.secciones] == [
        (S.OTRA, "Primera parte"),
        (S.OTRA, "Segunda parte"),
    ]
    assert documento.detectadas == [] and not documento.tiene_imrad


def test_texto_sin_ningun_titulo_es_otra_sin_titulo() -> None:
    documento = seccionar([parrafo("Solo texto corrido.")])
    assert [(s.clase, s.titulo) for s in documento.secciones] == [(S.OTRA, None)]


def test_un_resumen_solo_no_cuenta_como_imrad() -> None:
    documento = seccionar([titulo("Resumen"), parrafo("Texto.")])
    assert documento.detectadas == [S.RESUMEN] and not documento.tiene_imrad
