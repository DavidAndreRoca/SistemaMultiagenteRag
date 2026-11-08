"""Pruebas estáticas de arquitectura: consultas solo en repositorios, esquema sin datos
personales, repositorios de caso siempre con contexto y matriz de rutas completa."""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

import app.bd.modelos as modelos
from app.bd.base import Base
from app.bd.diccionario import RUTA_DICCIONARIO, alimenta, generar, indice_de_metricas
from app.bd.metricas import CODIGOS
from app.repositorios import caso as repos_caso
from app.repositorios import investigador as repos_investigador
from app.repositorios.base import RepositorioDeCaso
from app.repositorios.contexto import ContextoAcceso
from pruebas.matriz_autorizacion import MATRIZ, RUTAS_EXCLUIDAS

RAIZ_APP = Path(__file__).resolve().parents[2] / "app"
PERMITIDOS = {"repositorios", "bd"}  # bd: motor, modelos y comandos que usan repositorios
METODOS_DE_CONSULTA = {
    "execute",
    "scalar",
    "scalars",
    "stream",
    "stream_scalars",
    "commit",
    "rollback",
    "flush",
    "refresh",
    "merge",
}
CONSTRUCTORES_SQL = {"select", "insert", "update", "delete", "text", "func", "or_", "and_"}
COLUMNAS_PROHIBIDAS = re.compile(
    r"(^|_)(nombre|nombres|apellido|apellidos|correo|email|e_mail|dni|telefono|celular|"
    r"direccion|documento_identidad|pasaporte|fecha_nacimiento)($|_)"
)


def _archivos_fuera_de_repositorios() -> list[Path]:
    return [p for p in RAIZ_APP.rglob("*.py") if p.relative_to(RAIZ_APP).parts[0] not in PERMITIDOS]


def test_no_hay_consultas_fuera_de_repositorios() -> None:
    hallazgos = []
    for archivo in _archivos_fuera_de_repositorios():
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("sqlalchemy"):
                for alias in nodo.names:
                    if alias.name in CONSTRUCTORES_SQL or alias.name == "AsyncSession":
                        hallazgos.append(f"{archivo.name}:{nodo.lineno} importa {alias.name}")
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in METODOS_DE_CONSULTA
            ):
                hallazgos.append(f"{archivo.name}:{nodo.lineno} llama a .{nodo.func.attr}()")
    assert hallazgos == []


def test_la_prueba_estatica_detecta_una_consulta_fuera_de_la_capa(tmp_path: Path) -> None:
    falso = "from sqlalchemy import select\nasync def f(s):\n    await s.execute(select(1))\n"
    arbol = ast.parse(falso)
    llamadas = [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr in METODOS_DE_CONSULTA
    ]
    assert llamadas


def test_el_canal_de_extraccion_no_accede_a_la_base() -> None:
    """T09: procesar_pdf es una función pura sin acceso a la base (tareas técnicas de T09)."""
    prohibidos = ("sqlalchemy", "psycopg", "app.bd.sesion", "app.repositorios")
    hallazgos = []
    for archivo in (RAIZ_APP / "corpus").glob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            modulos = []
            if isinstance(nodo, ast.ImportFrom):
                modulos = [nodo.module or ""]
            elif isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            hallazgos += [f"{archivo.name}: {m}" for m in modulos if m.startswith(prohibidos)]
    assert hallazgos == []


def test_sin_columnas_de_datos_personales() -> None:
    _ = modelos
    prohibidas = [
        f"{t.name}.{c.name}"
        for t in Base.metadata.tables.values()
        for c in t.columns
        if COLUMNAS_PROHIBIDAS.search(c.name)
    ]
    assert prohibidas == []


def test_la_busqueda_de_columnas_prohibidas_funciona() -> None:
    for nombre in ("nombre", "correo_alumno", "dni", "email"):
        assert COLUMNAS_PROHIBIDAS.search(nombre)
    for nombre in ("documento_id", "codigo", "seccion_original"):
        assert not COLUMNAS_PROHIBIDAS.search(nombre)


def test_tablas_de_caso_tienen_caso_id_indexado() -> None:
    for nombre in modelos.TABLAS_DE_CASO:
        tabla = Base.metadata.tables[nombre]
        assert "caso_id" in tabla.c, nombre
        assert any(next(c.name for c in indice.columns) == "caso_id" for indice in tabla.indexes), (
            f"{nombre} sin índice por caso_id"
        )


def test_fragmento_indexado_por_coleccion() -> None:
    tabla = Base.metadata.tables["fragmento"]
    assert any([c.name for c in i.columns] == ["coleccion_id"] for i in tabla.indexes)


def test_toda_columna_tiene_descripcion() -> None:
    sin_comentario = [
        f"{t.name}.{c.name}"
        for t in Base.metadata.tables.values()
        for c in t.columns
        if not c.comment
    ]
    assert sin_comentario == []


def test_diccionario_de_datos_al_dia() -> None:
    assert RUTA_DICCIONARIO.read_text(encoding="utf-8") == generar(), (
        "Regenere con: python -m app.bd.diccionario"
    )


def _columnas(tabla: str) -> set[str]:
    return {f"{tabla}.{c.name}" for c in Base.metadata.tables[tabla].columns}


# Ficha de métricas (insumos de T04, apartado 1): columnas que alimentan cada métrica.
COLUMNAS_POR_METRICA = {
    "M1": {
        "solicitud.tipo",
        "solicitud.estado",
        "resultado.abstencion",
        "fuente_aportada.solicitud_id",
    },
    "M2": _columnas("fragmento_recuperado"),
    "M3": _columnas("fragmento_recuperado")
    | {"solicitud.completitud_evaluador", "solicitud.completitud_humana"},
    "M4": {"verificacion.fidelidad", "verificacion.intento"},
    "M5": _columnas("resultado") | {"solicitud.alcance_tipo", "solicitud.alcance_ref"},
    "M6": {
        "verificacion.n_fuentes_citadas",
        "verificacion.n_fuentes_confirmadas",
        "verificacion.metodo",
    },
}


@pytest.mark.parametrize("metrica", sorted(COLUMNAS_POR_METRICA))
def test_alimenta_cubre_la_ficha_de_metricas(metrica: str) -> None:
    indice = indice_de_metricas()
    faltan = COLUMNAS_POR_METRICA[metrica] - set(indice[metrica])
    assert faltan == set(), f"{metrica}: columnas sin declarar en Alimenta"


def test_los_juicios_de_evaluacion_existen() -> None:
    """M2, M3 y M5 necesitan dónde guardar el juicio del evaluador y el de la muestra humana."""
    columnas = {f"{t.name}.{c.name}" for t in Base.metadata.tables.values() for c in t.columns}
    assert {
        "fragmento_recuperado.pertinencia_evaluador",
        "fragmento_recuperado.pertinencia_humana",
        "solicitud.completitud_evaluador",
        "solicitud.completitud_humana",
        "resultado.relevancia_evaluador",
        "resultado.relevancia_humana",
    } <= columnas


def test_ninguna_columna_alimenta_una_metrica_inexistente() -> None:
    for tabla in Base.metadata.tables.values():
        for columna in tabla.columns:
            codigos = re.findall(r"\bM\d+\b", alimenta(tabla, columna))
            assert set(codigos) <= set(CODIGOS), f"{tabla.name}.{columna.name}: {codigos}"


@pytest.mark.parametrize(
    "clase",
    [
        c
        for _, c in inspect.getmembers(repos_caso, inspect.isclass)
        if c.__module__ == repos_caso.__name__
    ]
    + [
        c
        for _, c in inspect.getmembers(repos_investigador, inspect.isclass)
        if c.__module__ == repos_investigador.__name__
    ],
)
def test_todo_metodo_de_repositorio_exige_contexto(clase: type) -> None:
    metodos = {
        nombre: m
        for nombre, m in inspect.getmembers(clase, inspect.isfunction)
        if not nombre.startswith("_")
    }
    if issubclass(clase, RepositorioDeCaso):
        metodos |= {
            n: m
            for n, m in inspect.getmembers(RepositorioDeCaso, inspect.isfunction)
            if not n.startswith("_")
        }
    assert metodos
    for nombre, metodo in metodos.items():
        parametros = list(inspect.signature(metodo).parameters.values())
        assert len(parametros) >= 2 and parametros[1].name == "contexto", (
            f"{clase.__name__}.{nombre}"
        )
        assert parametros[1].default is inspect.Parameter.empty
        anotacion = parametros[1].annotation
        assert anotacion in (ContextoAcceso, "ContextoAcceso"), f"{clase.__name__}.{nombre}"


def test_toda_ruta_esta_en_la_matriz_de_autorizacion() -> None:
    from app.configuracion import cargar_ajustes
    from app.main import crear_aplicacion
    from pruebas.conftest import variables_base

    aplicacion = crear_aplicacion(cargar_ajustes(variables_base()))
    expuestas = {
        (metodo.upper(), ruta)
        for ruta, operaciones in aplicacion.openapi()["paths"].items()
        if ruta not in RUTAS_EXCLUIDAS
        for metodo in operaciones
    }
    assert expuestas == set(MATRIZ)
