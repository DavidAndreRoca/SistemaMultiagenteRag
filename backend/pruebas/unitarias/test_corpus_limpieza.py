"""T09: limpieza de bloques con textos controlados (casos tomados de la salida real de Docling)."""

from __future__ import annotations

import pytest

from app.corpus.bloques import Bloque, TipoBloque
from app.corpus.limpieza import (
    contar_palabras,
    es_numero_de_pagina,
    limpiar,
    normalizar_texto,
    separar_titulos_en_linea,
    unir_cortes_de_linea,
)

T = TipoBloque


def b(tipo: TipoBloque, texto: str, pagina: int = 1, fin: int | None = None) -> Bloque:
    return Bloque(tipo=tipo, texto=texto, pagina_inicio=pagina, pagina_fin=fin or pagina)


def test_normaliza_unicode_ligaduras_y_espacios() -> None:
    texto = "e\u0301xito \ufb01nal\u00a0y\u200b  e\ufb01caz\u00adment\u2010e\x07"
    assert normalizar_texto(texto) == "éxito final y eficazment-e"


@pytest.mark.parametrize(
    ("entrada", "salida"),
    [
        ("la investi- gación previa", "la investigación previa"),
        ("the experi-  ment was", "the experiment was"),
        ("pre- y postest", "pre- y postest"),  # conjunción: guion suspensivo
        ("pre- and post-test", "pre- and post-test"),
        ("COVID- 19 y SARS-CoV-2", "COVID- 19 y SARS-CoV-2"),  # sigue un número
        ("Latino- Americana", "Latino- Americana"),  # sigue una mayúscula
        ("bien-estar", "bien-estar"),  # sin espacio: guion de compuesto
    ],
)
def test_une_palabras_cortadas_al_final_de_linea(entrada: str, salida: str) -> None:
    assert unir_cortes_de_linea(entrada) == salida


@pytest.mark.parametrize(
    "texto", ["3", "Página 2 de 10", "Page 4 of 12", "p. 7", "xii", "12/40", "pág. 3"]
)
def test_reconoce_numeros_de_pagina(texto: str) -> None:
    assert es_numero_de_pagina(texto)


@pytest.mark.parametrize("texto", ["Tabla 3", "3. Resultados", "Método", "2026 fue un año"])
def test_no_confunde_texto_con_numeros_de_pagina(texto: str) -> None:
    assert not es_numero_de_pagina(texto)


def test_quita_mobiliario_marcado_y_su_repeticion_mal_etiquetada() -> None:
    """Docling marcó el encabezado como mobiliario en las páginas 1 y 3, y como título de
    sección en la 2; el texto repetido se reconoce en las tres."""
    revista = "Revista Ficticia de Educación Superior, 4(2), 2026."
    bloques = [
        b(T.ENCABEZADO_PAGINA, revista, 1),
        b(T.PARRAFO, "Primer párrafo del artículo.", 1),
        b(T.PIE_PAGINA, "Página 1 de 3", 1),
        b(T.TITULO_SECCION, revista, 2),
        b(T.PARRAFO, "Segundo párrafo.", 2),
        b(T.PIE_PAGINA, "Página 2 de 3", 2),
        b(T.ENCABEZADO_PAGINA, revista, 3),
        b(T.PARRAFO, "Tercer párrafo.", 3),
    ]
    assert [x.texto for x in limpiar(bloques, 3)] == [
        "Primer párrafo del artículo.",
        "Segundo párrafo.",
        "Tercer párrafo.",
    ]


def test_quita_textos_repetidos_sin_marca_en_la_mitad_de_las_paginas() -> None:
    contenidos = ["Uno.", "Dos.", "Tres.", "Cuatro.", "Cinco.", "Seis."]
    bloques = []
    for pagina, contenido in enumerate(contenidos, start=1):
        bloques.append(b(T.PARRAFO, f"Autor y otros, página {pagina}", pagina))
        bloques.append(b(T.PARRAFO, contenido, pagina))
    assert [x.texto for x in limpiar(bloques, 6)] == contenidos


def test_un_texto_repetido_en_dos_paginas_no_es_mobiliario() -> None:
    bloques = [b(T.PARRAFO, "Nota.", 1), b(T.PARRAFO, "Nota.", 2), b(T.PARRAFO, "Fin.", 3)]
    assert [x.texto for x in limpiar(bloques, 3)] == ["Nota.", "Nota.", "Fin."]


def test_une_un_parrafo_partido_por_salto_de_pagina() -> None:
    """Caso real: Docling partió un párrafo en una pieza por línea al pie de la página 1."""
    bloques = [
        b(T.PARRAFO, "Se usó un diseño con mediciones antes y después de la interv-", 1),
        b(T.PARRAFO, "ención. La población fueron los estudiantes del", 1),
        b(T.PARRAFO, "tercer ciclo. Se trabajó con dos secciones y la otra continuó", 1),
        b(T.ENCABEZADO_PAGINA, "Revista", 2),
        b(T.PARRAFO, "con las clases regulares.", 2),
        b(T.PARRAFO, "Otro párrafo distinto.", 2),
    ]
    resultado = limpiar(bloques, 2)
    assert [(x.texto, x.pagina_inicio, x.pagina_fin) for x in resultado] == [
        (
            "Se usó un diseño con mediciones antes y después de la intervención. La población"
            " fueron los estudiantes del tercer ciclo. Se trabajó con dos secciones y la otra"
            " continuó con las clases regulares.",
            1,
            2,
        ),
        ("Otro párrafo distinto.", 2, 2),
    ]


def test_un_titulo_en_minuscula_es_la_cola_de_un_parrafo() -> None:
    """Caso real: la última línea de un párrafo de la columna izquierda llegó como título."""
    bloques = [
        b(T.PARRAFO, "Support services could emphasize that sleep is part of preparation rather"),
        b(T.TITULO_SECCION, "than a competing activity."),
        b(T.PARRAFO, "Several limitations should be noted."),
    ]
    assert [(x.tipo, x.texto) for x in limpiar(bloques, 1)] == [
        (
            T.PARRAFO,
            "Support services could emphasize that sleep is part of preparation rather than a"
            " competing activity.",
        ),
        (T.PARRAFO, "Several limitations should be noted."),
    ]


def test_descarta_tablas_formulas_referencias_y_celdas_numericas() -> None:
    bloques = [
        b(T.PARRAFO, "Texto útil."),
        b(T.TABLA, "Grupo Pretest Postest"),
        b(T.PARRAFO, "78,6 (11,2)"),
        b(T.FORMULA, "x = y + 1"),
        b(T.REFERENCIA, "Autor, A. (2020). Título. Revista."),
        b(T.PARRAFO, "   "),
        b(T.PARRAFO, "12"),
    ]
    assert [x.texto for x in limpiar(bloques, 1)] == ["Texto útil."]


def test_no_une_bloques_de_tipo_distinto_ni_oraciones_terminadas() -> None:
    bloques = [
        b(T.PARRAFO, "Una oración terminada."),
        b(T.PARRAFO, "otra que empieza en minúscula."),
        b(T.LEYENDA, "Tabla 1. Puntajes por grupo"),
        b(T.PARRAFO, "después de la tabla"),
    ]
    assert len(limpiar(bloques, 1)) == 4


def test_quita_el_encabezado_pegado_dentro_de_un_parrafo() -> None:
    """Caso real: Docling unió el párrafo que pasa de página con el encabezado de la siguiente."""
    revista = "Revista Ficticia de Educación Superior, 4(2), 2026. doi:10.5555/rfes.2026.0042"
    bloques = [
        b(T.ENCABEZADO_PAGINA, revista, 1),
        b(T.PIE_PAGINA, "Página 1 de 3", 1),
        b(T.PARRAFO, f"Los estudiantes con ansiedad inicial {revista}", 1, 2),
        b(T.PARRAFO, "alta redujeron su puntaje. Página 2 de 3", 2),
    ]
    assert [(x.texto, x.pagina_inicio, x.pagina_fin) for x in limpiar(bloques, 3)] == [
        ("Los estudiantes con ansiedad inicial alta redujeron su puntaje.", 1, 2)
    ]


def test_separa_los_titulos_que_quedaron_dentro_de_un_parrafo() -> None:
    """Caso real: el modelo de diseño tomó casi una página entera como un solo párrafo."""
    texto = (
        "la universidad. 2.2. Instrumentos La escala tiene 24 ítems. 2.4. Análisis de datos"
        " Se aplicó un análisis de covarianza. 3. Resultados En el pretest no hubo"
        " diferencias. Resultados similares se vieron antes. Agradecimientos Gracias al fondo."
        " Referencias Arias Pérez, M. (2021). Obra ficticia."
    )
    bloques = [
        b(T.PARRAFO, "Ningún estudiante había llevado antes un curso de estadística en", 1),
        b(T.PARRAFO, texto, 2),
    ]
    assert [(x.tipo, x.texto) for x in limpiar(bloques, 2)] == [
        (
            T.PARRAFO,
            "Ningún estudiante había llevado antes un curso de estadística en la universidad.",
        ),
        (T.TITULO_SECCION, "2.2. Instrumentos"),
        (T.PARRAFO, "La escala tiene 24 ítems."),
        (T.TITULO_SECCION, "2.4. Análisis de datos"),
        (T.PARRAFO, "Se aplicó un análisis de covarianza."),
        (T.TITULO_SECCION, "3. Resultados"),
        (
            T.PARRAFO,
            "En el pretest no hubo diferencias. Resultados similares se vieron antes.",
        ),
        (T.TITULO_SECCION, "Agradecimientos"),
        (T.PARRAFO, "Gracias al fondo."),
        (T.TITULO_SECCION, "Referencias"),
        (T.PARRAFO, "Arias Pérez, M. (2021). Obra ficticia."),
    ]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Resumen La ansiedad es frecuente.", ["Resumen", "La ansiedad es frecuente."]),
        ("Abstract: Sleep matters.", ["Abstract", "Sleep matters."]),
        ("Resumiendo, el estudio funciona.", ["Resumiendo, el estudio funciona."]),
        ("Hubo cambios. Resultados de la Encuesta Nacional.", None),  # termina en "la"
        ("Hubo cambios. Results showed a gain.", None),  # sigue minúscula
        ("Palabras clave: ansiedad, tutoría.", None),
        ("Se usó el Método Delphi en 2020.", None),  # no viene tras un fin de oración
        ("Fin del texto. Conclusiones", ["Fin del texto.", "Conclusiones"]),
    ],
)
def test_titulos_en_linea_solo_cuando_son_inequivocos(
    texto: str, esperado: list[str] | None
) -> None:
    piezas = [x.texto for x in separar_titulos_en_linea(b(T.PARRAFO, texto))]
    assert piezas == (esperado or [texto])


def test_cuenta_palabras_con_numeros_y_tildes() -> None:
    assert contar_palabras("La media fue 78,6 puntos en ánimo.") == 8
