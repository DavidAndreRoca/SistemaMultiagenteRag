"""T12: secciones, lista de referencias, ``estructura_borrador`` y alcance (T12-01, CP-09).

Con .docx ficticios variados de ``pruebas/datos/docx/``: con estilos integrados y propios,
sin estilos, con campos y controles de contenido de Mendeley y Zotero, y con tablas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.administracion.parametros import parametros_iniciales
from app.bd.enumeraciones import ALCANCES_ADMITIDOS, TipoAlcance, TipoSolicitud
from app.borradores.alcance import AlcanceInvalido, validar_alcance
from app.borradores.extraccion import ParrafoBorrador, extraer_parrafos
from app.borradores.secciones import (
    SeccionesInvalidas,
    SeccionesVersion,
    TituloMarcado,
    detectar_por_estilos,
    estructura_borrador,
    marcar_a_mano,
    referencias_a_mano,
)

DOCX = Path(__file__).parents[1] / "datos" / "docx"
PARAMETROS = parametros_iniciales()


def _parrafos(nombre: str) -> list[ParrafoBorrador]:
    return extraer_parrafos(DOCX / nombre).parrafos


def _estructura() -> tuple[list[ParrafoBorrador], SeccionesVersion]:
    parrafos = _parrafos("estructura.docx")
    secciones = detectar_por_estilos(parrafos)
    assert secciones is not None
    return parrafos, secciones


def test_un_docx_con_estilos_produce_su_arbol_de_secciones() -> None:
    parrafos, secciones = _estructura()
    assert secciones.titulo_documento == "Tutoría entre pares y ansiedad ante la estadística"
    assert secciones.preliminares == ["p2"]  # autores: antes del primer título
    resumen = [(s.id, s.titulo, s.nivel, s.clase, s.padre) for s in secciones.secciones]
    assert resumen == [
        ("s1", "Resumen", 1, "resumen", None),
        ("s2", "1. Introducción", 1, "introduccion", None),
        ("s3", "1.1. Planteamiento del problema", 2, "introduccion", "s2"),  # estilo propio
        ("s4", "1.2. Hipótesis", 2, "introduccion", "s2"),  # clase heredada
        ("s5", "2. Método", 1, "metodos", None),
        ("s6", "2.1. Participantes", 2, "metodos", "s5"),
        ("s7", "2.1.1. Criterios de inclusión", 3, "metodos", "s6"),  # nivel de esquema
        ("s8", "2.2. Instrumentos", 2, "metodos", "s5"),
        ("s9", "3. Resultados", 1, "resultados", None),
        ("s10", "4. Discusión", 1, "discusion", None),
        ("s11", "Referencias", 1, "referencias", None),
    ]
    por_id = {s.id: s for s in secciones.secciones}
    assert por_id["s2"].parrafos == ["p6", "p7"]
    assert por_id["s8"].parrafos == ["p18", "p19"]  # las celdas de la tabla, sin títulos
    assert all(p.nivel is None for p in parrafos if p.origen == "tabla")


def test_la_lista_de_referencias_se_separa_en_entradas() -> None:
    _, secciones = _estructura()
    referencias = secciones.referencias
    assert referencias is not None
    assert (referencias.metodo, referencias.seccion, referencias.desde, referencias.hasta) == (
        "automatica",
        "s11",
        "p25",
        "p26",
    )
    assert referencias.entradas == [  # la entrada partida por un salto de línea, separada
        "Quispe, R. (2020). Ansiedad ficticia. Revista Imaginaria, 3(2), 10-20.",
        "Torres, A. (2021). Tutoría ficticia. Editorial Inventada.",
        "Arias, M. (2019). Pares ficticios. Revista Supuesta, 1(1), 1-9.",
    ]


def test_tolera_los_campos_y_controles_de_mendeley() -> None:
    parrafos = _parrafos("mendeley.docx")
    assert parrafos[1].texto == "La ansiedad es frecuente (Quispe, 2020) y persiste (Torres, 2021)."
    assert not any("CSL_CITATION" in p.texto or "MENDELEY" in p.texto for p in parrafos)
    secciones = detectar_por_estilos(parrafos)
    assert secciones is not None and secciones.referencias is not None
    # La bibliografía está en un control de contenido de bloque y no se pierde.
    assert secciones.referencias.entradas == [
        "Quispe, R. (2020). Ansiedad ficticia. Revista Imaginaria, 3(2), 10-20.",
        "Torres, A. (2021). Tutoría ficticia. Editorial Inventada.",
    ]


def test_zotero_con_la_lista_sin_titulo_se_indica_a_mano() -> None:
    parrafos = _parrafos("zotero.docx")
    assert parrafos[1].texto == "Hay evidencia previa [1]."
    secciones = detectar_por_estilos(parrafos)
    assert secciones is not None and secciones.referencias is None  # "Bibliografía" sin estilo
    con_lista = referencias_a_mano(secciones, parrafos, desde="p6", hasta=None)
    referencias = con_lista.referencias
    assert referencias is not None and referencias.metodo == "manual"
    assert referencias.seccion == "s2"  # cae dentro de "Conclusiones"
    assert referencias.entradas == [
        '[1] R. Quispe, "Ansiedad ficticia," Rev. Imag., vol. 3, 2020.',
        "[2] A. Torres, Tutoría ficticia. Editorial Inventada, 2021.",
    ]
    assert con_lista.secciones == secciones.secciones  # las secciones no cambian
    with pytest.raises(SeccionesInvalidas):
        referencias_a_mano(secciones, parrafos, desde="p6", hasta="p2")  # al revés
    with pytest.raises(SeccionesInvalidas):
        referencias_a_mano(secciones, parrafos, desde="p99", hasta=None)


def test_un_docx_sin_estilos_pide_seleccion_manual_y_la_aplica() -> None:
    parrafos = _parrafos("sin_estilos.docx")
    assert detectar_por_estilos(parrafos) is None
    marcadas = marcar_a_mano(
        parrafos, [TituloMarcado(parrafo=pid) for pid in ("p1", "p3", "p5", "p7")]
    )
    assert [(s.id, s.titulo, s.clase, s.parrafos) for s in marcadas.secciones] == [
        ("s1", "Introducción", "introduccion", ["p2"]),
        ("s2", "Método", "metodos", ["p4"]),
        ("s3", "Resultados", "resultados", ["p6"]),
        ("s4", "Referencias", "referencias", ["p8"]),
    ]
    assert marcadas.referencias is not None and marcadas.referencias.desde == "p8"


@pytest.mark.parametrize(
    "titulos",
    [
        [],
        [TituloMarcado(parrafo="p99")],
        [TituloMarcado(parrafo="p1"), TituloMarcado(parrafo="p1")],
        [TituloMarcado(parrafo="p1", nivel=0)],
        [TituloMarcado(parrafo="p1", nivel=10)],
    ],
)
def test_la_seleccion_manual_se_valida(titulos: list[TituloMarcado]) -> None:
    with pytest.raises(SeccionesInvalidas):
        marcar_a_mano(_parrafos("sin_estilos.docx"), titulos)


def test_una_celda_de_tabla_no_puede_ser_titulo() -> None:
    with pytest.raises(SeccionesInvalidas):
        marcar_a_mano(_parrafos("estructura.docx"), [TituloMarcado(parrafo="p18")])


def test_estructura_borrador_ubica_problema_objetivos_e_hipotesis() -> None:
    parrafos, secciones = _estructura()
    estructura = estructura_borrador(parrafos, secciones, "estilos")
    assert estructura.metodo == "estilos" and estructura.seccion_referencias == "s11"
    assert [n.id for n in estructura.arbol] == ["s1", "s2", "s5", "s9", "s10", "s11"]
    metodo = next(n for n in estructura.arbol if n.id == "s5")
    assert [h.id for h in metodo.hijos] == ["s6", "s8"]
    assert [h.id for h in metodo.hijos[0].hijos] == ["s7"]
    ubicaciones = {(u.elemento, u.seccion, u.parrafo, u.por) for u in estructura.ubicaciones}
    assert ubicaciones == {
        ("problema", "s2", "p6", "texto"),  # la pregunta entre signos
        ("objetivos", "s2", "p7", "texto"),
        ("problema", "s3", "p8", "titulo"),
        ("hipotesis", "s4", "p10", "titulo"),
        ("hipotesis", "s4", "p11", "texto"),  # H1:
    }  # ni la celda "Hipótesis de la escala" ni las referencias cuentan


def test_estructura_sin_secciones() -> None:
    parrafos = _parrafos("sin_estilos.docx")
    estructura = estructura_borrador(parrafos, None, None)
    assert estructura.arbol == [] and estructura.metodo is None


# ------------------------------------------------------------------------------- alcance

PARRAFO_LARGO = ParrafoBorrador(
    id="p1", texto=" ".join(["palabra"] * 251), estilo="Normal", origen="cuerpo"
)
PARRAFO_LIMITE = PARRAFO_LARGO.model_copy(update={"id": "p2", "texto": " ".join(["palabra"] * 250)})


def _referencia_valida(alcance: TipoAlcance) -> str | None:
    return {
        TipoAlcance.SECCION: "s2",
        TipoAlcance.FRAGMENTO: "p7",
        TipoAlcance.CONSULTA: "evidencia sobre tutoría entre pares",
    }.get(alcance)


@pytest.mark.parametrize("tipo", list(TipoSolicitud))
@pytest.mark.parametrize("alcance", list(TipoAlcance))
def test_los_seis_tipos_solo_admiten_sus_alcances(
    tipo: TipoSolicitud, alcance: TipoAlcance
) -> None:
    parrafos, secciones = _estructura()
    argumentos = (tipo, alcance, _referencia_valida(alcance), parrafos, secciones, PARAMETROS)
    if alcance in ALCANCES_ADMITIDOS[tipo]:
        resuelto = validar_alcance(*argumentos)
        assert resuelto.texto and resuelto.palabras > 0
    else:
        with pytest.raises(AlcanceInvalido) as error:
            validar_alcance(*argumentos)
        assert error.value.motivo == "alcance_no_admitido"


def test_el_alcance_de_seccion_incluye_sus_subsecciones() -> None:
    parrafos, secciones = _estructura()
    resuelto = validar_alcance(
        TipoSolicitud.REVISION_METODOLOGICA,
        TipoAlcance.SECCION,
        "s5",
        parrafos,
        secciones,
        PARAMETROS,
    )
    assert resuelto.parrafos == ["p12", "p13", "p14", "p15", "p16", "p17", "p18", "p19"]
    assert resuelto.texto.startswith("2. Método\n\n2.1. Participantes")


def test_cp09_un_parrafo_de_mas_de_250_palabras_se_rechaza_para_d3() -> None:
    parrafos = [PARRAFO_LARGO, PARRAFO_LIMITE]
    with pytest.raises(AlcanceInvalido) as error:
        validar_alcance(
            TipoSolicitud.PROPUESTA_REDACCION,
            TipoAlcance.FRAGMENTO,
            "p1",
            parrafos,
            None,
            PARAMETROS,
        )
    assert error.value.motivo == "alcance_demasiado_largo" and error.value.estado_http == 422
    assert "251 palabras" in error.value.mensaje and "250" in error.value.mensaje
    assert error.value.detalle == {
        "motivo": "alcance_demasiado_largo",
        "palabras": 251,
        "limite": 250,
    }
    # El límite exacto se admite, y el mismo párrafo largo sí sirve para buscar evidencia.
    validar_alcance(
        TipoSolicitud.PROPUESTA_REDACCION, TipoAlcance.FRAGMENTO, "p2", parrafos, None, PARAMETROS
    )
    validar_alcance(
        TipoSolicitud.BUSQUEDA_EVIDENCIA, TipoAlcance.FRAGMENTO, "p1", parrafos, None, PARAMETROS
    )


def test_el_limite_de_d3_sale_de_la_configuracion() -> None:
    parametros = PARAMETROS.model_copy(update={"limite_palabras_d3": 300})
    validar_alcance(
        TipoSolicitud.PROPUESTA_REDACCION,
        TipoAlcance.FRAGMENTO,
        "p1",
        [PARRAFO_LARGO],
        None,
        parametros,
    )


@pytest.mark.parametrize(
    ("tipo", "alcance", "ref", "motivo"),
    [
        (TipoSolicitud.REVISION_ESTRUCTURA, TipoAlcance.SECCION, "s99", "seccion_inexistente"),
        (TipoSolicitud.REVISION_ESTRUCTURA, TipoAlcance.SECCION, None, "alcance_sin_referencia"),
        (TipoSolicitud.PROPUESTA_REDACCION, TipoAlcance.FRAGMENTO, "p99", "parrafo_inexistente"),
        (TipoSolicitud.BUSQUEDA_EVIDENCIA, TipoAlcance.CONSULTA, "   ", "consulta_vacia"),
        (
            TipoSolicitud.BUSQUEDA_EVIDENCIA,
            TipoAlcance.CONSULTA,
            "x" * 2001,
            "consulta_demasiado_larga",
        ),
        (TipoSolicitud.PLAN_TAREA, TipoAlcance.HITO, "s1", "alcance_ref_no_admitido"),
        (
            TipoSolicitud.VERIFICACION_REFERENCIAS,
            TipoAlcance.VERSION,
            "p1",
            "alcance_ref_no_admitido",
        ),
    ],
)
def test_alcances_con_referencias_invalidas(
    tipo: TipoSolicitud, alcance: TipoAlcance, ref: str | None, motivo: str
) -> None:
    parrafos, secciones = _estructura()
    with pytest.raises(AlcanceInvalido) as error:
        validar_alcance(tipo, alcance, ref, parrafos, secciones, PARAMETROS)
    assert error.value.motivo == motivo and error.value.mensaje


def test_sin_secciones_el_alcance_de_seccion_pide_marcarlas() -> None:
    with pytest.raises(AlcanceInvalido) as error:
        validar_alcance(
            TipoSolicitud.REVISION_ESTRUCTURA,
            TipoAlcance.SECCION,
            "s1",
            _parrafos("sin_estilos.docx"),
            None,
            PARAMETROS,
        )
    assert error.value.motivo == "sin_secciones" and "Marque" in error.value.mensaje
