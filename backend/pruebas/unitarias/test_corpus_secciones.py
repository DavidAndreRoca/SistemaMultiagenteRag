"""T09: normalización de secciones a IMRaD y exclusión de referencias y agradecimientos."""

from __future__ import annotations

import pytest

from app.bd.enumeraciones import SeccionNormalizada as S
from app.corpus.bloques import Bloque, TipoBloque
from app.corpus.secciones import (
    SeccionExcluida,
    clasificar_titulo,
    es_referencia_bibliografica,
    seccionar,
    titulo_completo,
)

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


@pytest.mark.parametrize(
    "texto",
    [
        # APA (caso real del corpus provisional, con DOI)
        "Molla, A., & Licker, P. S. (2005). eCommerce adoption in developing countries: a"
        " model and instrument. Information & Management, 42(6), 877-899."
        " https://doi.org/10.1016/j.im.2004.09.002",
        # IEEE (caso real)
        'T. Adiguzel, M. H. Kaya, and F. K. Cansu, "Revolutionizing education with AI,"'
        " Contemporary Educational Technology, vol. 15, no. 3, pp. 1-13, 2023. Available:"
        " https://doi.org/10.30935/cedtech/13152",
        # Varias entradas APA sin DOI en un mismo bloque
        "Pérez, J. (2019). Título ficticio uno. Revista Ficticia, 3(2), 10-20. Gómez, A. B."
        " (2020). Título ficticio dos. Editorial Imaginaria.",
        # Vancouver
        "Quispe R, Torres A. Ansiedad y estadística. Rev Fict Educ. 2021;12(3):45-61."
        " doi:10.5555/rfe.2021.12",
        # Harvard con el nombre de pila y el título entre comillas
        'Quispe, Rosa and Torres, Ana (2016). "Ansiedad ante la estadística en primer año".'
        " Revista Ficticia, 4 (2), 35-48. <https://doi.org/10.5555/rf.2016.4>",
        # Recuadro de cita del propio artículo
        "Citation: Quispe, R.; Torres, A. Ansiedad ante la estadística. Educ. Fict. 2023, 13,"
        " 856. https://doi.org/10.5555/ef13090856",
    ],
)
def test_reconoce_entradas_bibliograficas_por_su_forma(texto: str) -> None:
    assert es_referencia_bibliografica(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "La ansiedad ante la estadística es frecuente (Pérez, 2020; Gómez et al., 2021) y se"
        " asocia con menor rendimiento, como mostraron estudios previos (Arias, 2019).",
        "Se aplicó el coeficiente alfa de Cronbach (1951), que fue de 0,91 en el pretest y de"
        " 0,93 en el postest, con una muestra de 84 estudiantes de tercer ciclo.",
        "Los datos están disponibles en https://osf.io/ficticio para quien quiera replicar el"
        " análisis descrito en esta sección.",
        "Participaron 84 estudiantes (42 en cada grupo) con una edad media de 20,4 años.",
        # Casos del corpus provisional (decisión T09-01, apartado 10), con nombres ficticios:
        # citas narrativas en serie,
        "Así, Quispe y Torres (2006), Arias et al. (2006), Gómez-Rivas y Lera (2007), Salas,"
        " Tello y Mena (2007) y Paz (2008) midieron el tamaño de la empresa. Rojas y Vera"
        " (2002) usaron el número de empleados, como Gómez-Rivas y Lera (2007).",
        # una lista de autores en un resultado bibliométrico,
        "La figura 4 muestra los autores con más producción: Quispe, R.C., Torres, L.,"
        " Arias, M., Gómez, A., Salas, S. y Tello, D.R., con al menos tres artículos cada uno.",
        # enlaces a las herramientas usadas
        "Se usaron Escritor (https://escritor.example, consultado el 8 de julio de 2024),"
        " Imagina (https://imagina.example) y Dibuja (https://dibuja.example) en las tareas.",
        # y una lista entre comillas con la coma dentro, al estilo estadounidense.
        'We used terms such as "dynamic pricing in retail," "AI impact on retail," "data'
        ' usage in retail," and "retail efficiency," in the search of industry reports.',
    ],
)
def test_no_confunde_prosa_con_citas_con_una_referencia(texto: str) -> None:
    assert not es_referencia_bibliografica(texto)


def test_excluye_referencias_sin_titulo_o_desordenadas() -> None:
    """Caso real: Docling dejó el título "5. Conclusion" después de la lista de
    referencias, y otra lista aparece al final de la discusión sin título."""
    referencia = (
        'E. Agbaglo and E. M. Bonsu, "The role of digital technologies," Cogent Education,'
        " vol. 9, no. 1, pp. 1-12, 2022. Available: https://doi.org/10.1080/2331186X.2022.2"
    )
    bloques = [
        titulo("Introducción"),
        parrafo("Texto de introducción sin referencias."),
        titulo("4. Discussion"),
        parrafo("Discusión de los hallazgos (Pérez, 2020)."),
        parrafo(referencia),
        parrafo("Industrial Management & Data Systems, 109(2), 224-244."),  # resto partido
        titulo("5. Conclusion"),
        parrafo("La conclusión del estudio."),
        parrafo(referencia),
    ]
    textos = [p.texto for s in seccionar(bloques).secciones for p in s.parrafos]
    assert textos == [
        "Texto de introducción sin referencias.",
        "Discusión de los hallazgos (Pérez, 2020).",
        "La conclusión del estudio.",
    ]


@pytest.mark.parametrize(
    "titulo_texto",
    ["Reference", "Referencia", "Bibliographic references", "Lista de referencias"],
)
def test_titulos_de_referencias_en_singular_y_variantes(titulo_texto: str) -> None:
    assert clasificar_titulo(titulo_texto) is SeccionExcluida.REFERENCIAS


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
