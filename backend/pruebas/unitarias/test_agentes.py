"""T18: esquemas de salida, comprobaciones 1 y 3, estado del agente y formateador CSL."""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.agentes.contrato import EstadoAgente
from app.agentes.esquemas import ESQUEMAS, GENERADOS_POR_MODELO, BusquedaEvidencia
from app.bd.enumeraciones import TipoSolicitud
from app.bibliografia.csl import (
    DIRECTORIO_ESTILOS,
    ESTILOS,
    NormaNoAdmitida,
    formatear,
    huella_estilo,
    item_csl,
    quitar_numero,
)
from app.llm.esquema import esquema_estricto
from app.llm.proveedores import valores_neutros
from app.verificacion.comprobaciones import (
    comprobar_citas,
    comprobar_esquema,
    identificadores_citados,
)

T = TipoSolicitud
RECUPERADOS = {f"F{i}" for i in range(1, 9)}  # F1 a F8

VALIDAS: dict[TipoSolicitud, dict[str, Any]] = {
    T.REVISION_ESTRUCTURA: {
        "hallazgos": [
            {
                "indicador": "alineacion_problema_objetivos_hipotesis",
                "ubicacion": "p3",
                "descripcion": "El objetivo general no responde al problema planteado.",
                "severidad": "alta",
                "recomendacion": "Revise que el objetivo derive del problema (F1).",
                "citas": ["F1"],
            }
        ],
        "fortalezas": ["La introducción presenta el contexto."],
        "notas_para_el_estudiante": [],
    },
    T.PLAN_TAREA: {
        "hito": "avance_1",
        "tareas": [
            {
                "orden": 1,
                "tarea": "Redactar el problema de investigación.",
                "criterio_de_logro": "El problema se formula como pregunta.",
                "citas": ["F2"],
            }
        ],
        "notas_para_el_estudiante": ["Empiece por el problema."],
    },
    T.REVISION_METODOLOGICA: {
        "hallazgos": [
            {
                "indicador": "precision_del_analisis_de_datos",
                "ubicacion": "sec4",
                "descripcion": "No se informa el tamaño del efecto.",
                "severidad": "media",
                "recomendacion": "Reporte el tamaño del efecto junto a la prueba.",
                "citas": ["F3", "F4"],
            }
        ],
        "preguntas_al_estudiante": ["¿Cómo eligió la muestra?"],
        "notas_para_el_estudiante": [],
    },
    T.PROPUESTA_REDACCION: {
        "original": "Los alumnos tuvieron menos ansiedad.",
        "propuesta": "Los estudiantes mostraron menor ansiedad.",
        "cambios": [
            {
                "tipo": "registro_formal",
                "antes": "alumnos tuvieron",
                "despues": "estudiantes mostraron",
                "razon": "Registro formal (F5).",
                "citas": ["F5"],
            }
        ],
        "notas_para_el_estudiante": [],
    },
    T.BUSQUEDA_EVIDENCIA: {
        "respuesta": [{"afirmacion": "La tutoría reduce la ansiedad.", "citas": ["F1", "F6"]}],
        "evidencia_divergente": [],
        "notas_para_el_estudiante": [],
    },
    T.VERIFICACION_REFERENCIAS: {
        "referencias": [
            {
                "indice": 1,
                "texto_original": "Quispe, A. (2021). Ansiedad. Revista Ficticia.",
                "estado": "no_comprobable",
                "metodo": "doi",
                "discrepancias": [],
                "doi_encontrado": None,
            }
        ],
        "citas_sin_entrada": [],
        "entradas_no_citadas": [],
    },
}


@pytest.mark.parametrize("tipo", list(TipoSolicitud))
def test_cada_tipo_tiene_esquema_y_acepta_una_salida_valida(tipo: TipoSolicitud) -> None:
    assert comprobar_esquema(tipo, VALIDAS[tipo]).superada
    ESQUEMAS[tipo].model_validate(VALIDAS[tipo])


def _con(datos: dict[str, Any], ruta: list[Any], valor: Any) -> dict[str, Any]:
    copia: Any = json.loads(json.dumps(datos))
    nodo = copia
    for paso in ruta[:-1]:
        nodo = nodo[paso]
    if valor is _QUITAR:
        del nodo[ruta[-1]]
    else:
        nodo[ruta[-1]] = valor
    assert isinstance(copia, dict)
    return copia


_QUITAR = object()


@pytest.mark.parametrize(
    ("tipo", "ruta", "valor", "esperado"),
    [
        (T.REVISION_ESTRUCTURA, ["hallazgos", 0, "citas"], [], "too_short"),
        (T.REVISION_ESTRUCTURA, ["hallazgos", 0, "severidad"], "critica", "enum"),
        (T.REVISION_ESTRUCTURA, ["hallazgos", 0, "indicador"], "estilo", "enum"),
        (T.PLAN_TAREA, ["tareas"], [], "too_short"),
        (T.REVISION_METODOLOGICA, ["hallazgos", 0, "citas"], ["fragmento 3"], "string_pattern"),
        (T.PROPUESTA_REDACCION, ["referencias"], ["Quispe (2021)"], "extra_forbidden"),
        (T.BUSQUEDA_EVIDENCIA, ["respuesta", 0, "citas"], ["F0"], "string_pattern"),
        (T.BUSQUEDA_EVIDENCIA, ["notas_para_el_estudiante"], _QUITAR, "missing"),
        (T.BUSQUEDA_EVIDENCIA, ["fuentes"], [{"documento_id": "x"}], "extra_forbidden"),
    ],
)
def test_la_comprobacion_1_rechaza_salidas_defectuosas(
    tipo: TipoSolicitud, ruta: list[Any], valor: Any, esperado: str
) -> None:
    comprobacion = comprobar_esquema(tipo, _con(VALIDAS[tipo], ruta, valor))
    assert not comprobacion.superada and comprobacion.numero == 1
    assert any(esperado in m for m in comprobacion.motivos), comprobacion.motivos
    # Los motivos nombran campos y tipos de error, nunca el contenido (4.6).
    assert all("Quispe" not in m and "fragmento 3" not in m for m in comprobacion.motivos)


def test_ningun_esquema_del_modelo_tiene_campos_de_referencias() -> None:
    """RN-17: el modelo no puede escribir referencias, fuentes ni documentos."""
    prohibidos = ("referencia", "bibliograf", "fuente", "documento", "doi", "url", "autor")

    def nombres(esquema: dict[str, Any]) -> set[str]:
        encontrados: set[str] = set()
        for definicion in [esquema, *esquema.get("$defs", {}).values()]:
            encontrados |= set(definicion.get("properties", {}))
        return encontrados

    for tipo in GENERADOS_POR_MODELO:
        campos = nombres(ESQUEMAS[tipo].model_json_schema())
        assert campos and not [c for c in campos if any(p in c for p in prohibidos)], tipo


@pytest.mark.parametrize("tipo", sorted(GENERADOS_POR_MODELO))
def test_los_esquemas_del_modelo_admiten_el_modo_estricto(tipo: TipoSolicitud) -> None:
    esquema = esquema_estricto(ESQUEMAS[tipo])
    assert esquema["additionalProperties"] is False
    ESQUEMAS[tipo].model_validate(valores_neutros(esquema))  # el simulado arma algo válido


def test_comprobacion_3_rechaza_una_cita_a_f9_cuando_solo_hay_f1_a_f8() -> None:
    salida = _con(VALIDAS[T.BUSQUEDA_EVIDENCIA], ["respuesta", 0, "citas"], ["F1", "F9"])
    comprobacion = comprobar_citas(salida, RECUPERADOS)
    assert (comprobacion.numero, comprobacion.superada) == (3, False)
    assert comprobacion.motivos == ["cita a un fragmento no recuperado: F9"]
    assert comprobar_citas(VALIDAS[T.BUSQUEDA_EVIDENCIA], RECUPERADOS).superada


def test_comprobacion_3_tambien_lee_las_citas_dentro_del_texto() -> None:
    salida = _con(
        VALIDAS[T.REVISION_ESTRUCTURA],
        ["hallazgos", 0, "recomendacion"],
        "Siga lo que dicen F2 y [F12].",
    )
    comprobacion = comprobar_citas(salida, RECUPERADOS)
    assert not comprobacion.superada and comprobacion.motivos == [
        "cita a un fragmento no recuperado: F12"
    ]
    assert identificadores_citados(salida) == ["F2", "F12", "F1"]
    assert identificadores_citados(
        BusquedaEvidencia.model_validate(VALIDAS[T.BUSQUEDA_EVIDENCIA])
    ) == [
        "F1",
        "F6",
    ]
    assert not comprobar_citas(VALIDAS[T.BUSQUEDA_EVIDENCIA], set()).superada


def test_estado_del_agente() -> None:
    base = {
        "solicitud_id": uuid.uuid4(),
        "caso_id": uuid.uuid4(),
        "tipo": T.BUSQUEDA_EVIDENCIA,
        "alcance": "¿La tutoría reduce la ansiedad?",
        "version_id": uuid.uuid4(),
    }
    assert EstadoAgente(**base).intento == 1
    with pytest.raises(ValidationError, match="intento 2"):
        EstadoAgente(**base, motivos_falla=["cita F9 inexistente"])
    assert EstadoAgente(**base, intento=2, motivos_falla=["x"]).motivos_falla == ["x"]
    with pytest.raises(ValidationError):
        EstadoAgente(**base, intento=3)
    with pytest.raises(ValidationError):
        EstadoAgente(**base, historial=["otra solicitud"])  # sin memoria entre solicitudes


# --- Formateador CSL (sin DOI) ---

ARTICULO = {
    "titulo": "Tutoría entre pares y ansiedad ante la estadística",
    "autores": [
        {"nombres": "Ana", "apellidos": "Quispe"},
        {"nombres": "Luis", "apellidos": "Huamán"},
    ],
    "anio": 2021,
    "revista_editorial": "Revista Ficticia de Pedagogía",
    "idioma": "es",
    "doi": None,
}
LIBRO = {
    "titulo": "Manual ficticio de estadística para ciencias sociales",
    "autores": [{"nombres": "Karla", "apellidos": "Ortiz"}],
    "anio": 2014,
    "revista_editorial": "Editorial Ficticia",
    "isbn": "9786120000000",
    "idioma": "es",
}


@pytest.mark.parametrize(
    ("norma", "articulo", "libro"),
    [
        (
            "apa7",
            "Quispe, A., & Huamán, L. (2021). Tutoría entre pares y ansiedad ante la estadística."
            " Revista Ficticia de Pedagogía.",
            "Ortiz, K. (2014). Manual ficticio de estadística para ciencias sociales."
            " Editorial Ficticia.",
        ),
        (
            "ieee",
            "A. Quispe y L. Huamán, «Tutoría entre pares y ansiedad ante la estadística»,"
            " Revista Ficticia de Pedagogía, 2021.",
            "K. Ortiz, Manual ficticio de estadística para ciencias sociales. Editorial Ficticia,"
            " 2014.",
        ),
        (
            "vancouver",
            "Quispe A, Huamán L. Tutoría entre pares y ansiedad ante la estadística. Revista"
            " Ficticia de Pedagogía. 2021.",
            "Ortiz K. Manual ficticio de estadística para ciencias sociales. Editorial Ficticia;"
            " 2014.",
        ),
    ],
)
def test_el_formateador_csl_arma_las_tres_normas(norma: str, articulo: str, libro: str) -> None:
    assert formatear(norma, ARTICULO) == articulo
    assert formatear(norma, LIBRO).startswith(libro.removesuffix("."))


def test_el_formateador_agrega_el_doi_y_la_url_guardados() -> None:
    con_doi = {**ARTICULO, "doi": "10.5555/sma.o1.01", "url": "https://repositorio.example/x"}
    assert formatear("apa7", con_doi).endswith("https://doi.org/10.5555/sma.o1.01")
    assert "doi: 10.5555/sma.o1.01" in formatear("ieee", con_doi)
    assert item_csl("x", {"titulo": None, "autores": [{"nombres": None, "apellidos": "Soto"}]}) == {
        "id": "x",
        "type": "article-journal",
        "title": "Sin título",
        "author": [{"family": "Soto"}],
    }
    with pytest.raises(NormaNoAdmitida):
        formatear("chicago", ARTICULO)


def test_los_estilos_son_los_oficiales_fijados() -> None:
    assert set(ESTILOS) == {"ieee", "apa7", "vancouver"}  # la lista cerrada de D-12
    for estilo in ESTILOS.values():
        assert huella_estilo(DIRECTORIO_ESTILOS / estilo.archivo) == estilo.huella
        assert estilo.titulo in (DIRECTORIO_ESTILOS / estilo.archivo).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("[1]A. Quispe, «Título», Revista, 2021.", "A. Quispe, «Título», Revista, 2021."),
        ("1. Quispe A. Título. Revista. 2021.", "Quispe A. Título. Revista. 2021."),
        ("  Quispe, A. (2021).\n Título. ", "Quispe, A. (2021). Título."),
    ],
)
def test_se_quita_el_numero_de_lista(texto: str, esperado: str) -> None:
    assert quitar_numero(texto) == esperado
