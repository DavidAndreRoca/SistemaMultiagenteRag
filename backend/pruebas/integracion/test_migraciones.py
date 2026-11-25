"""T04: migraciones reversibles y restricciones del esquema con PostgreSQL real."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from sqlalchemy.engine import make_url

from pruebas.integracion.conftest import _conninfo, configuracion_alembic, consultar

pytestmark = pytest.mark.integracion

TABLAS_T04 = {
    "caso",
    "version_borrador",
    "solicitud",
    "fragmento_recuperado",
    "resultado",
    "verificacion",
    "decision",
    "fuente_aportada",
    "documento",
    "coleccion",
    "fragmento",
    "cuenta",
    "configuracion",
    "evento_tecnico",
    "cache_metadatos",
}


@pytest.fixture
def base_vacia(servidor_pruebas: str) -> Iterator[str]:
    nombre = f"sma_migracion_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(_conninfo(servidor_pruebas), autocommit=True) as conexion:
        conexion.execute(f'CREATE DATABASE "{nombre}"')
    try:
        yield make_url(servidor_pruebas).set(database=nombre).render_as_string(hide_password=False)
    finally:
        with psycopg.connect(_conninfo(servidor_pruebas), autocommit=True) as conexion:
            conexion.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')


def _tablas(url: str) -> set[str]:
    return {
        str(f[0])
        for f in consultar(url, "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    }


def test_migracion_asciende_y_desciende_sin_errores(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0002")
    assert _tablas(base_vacia) >= TABLAS_T04
    assert len(TABLAS_T04 & _tablas(base_vacia)) == 15
    command.upgrade(cfg, "head")
    assert {"sesion", "cambio_norma"} <= _tablas(base_vacia)
    command.downgrade(cfg, "base")
    assert _tablas(base_vacia) <= {"alembic_version"}
    command.upgrade(cfg, "head")  # de nuevo, sobre la base revertida
    assert TABLAS_T04 | {"sesion", "cambio_norma"} <= _tablas(base_vacia)


def test_semilla_de_configuracion_vigente(url_bd_migrada: str) -> None:
    filas = consultar(
        url_bd_migrada, "SELECT numero_version, vigente, congelada, parametros FROM configuracion"
    )
    assert len(filas) == 1
    numero, vigente, congelada, parametros = filas[0]
    assert (numero, vigente, congelada) == (1, True, False)
    assert isinstance(parametros, dict)
    assert parametros["norma_por_defecto"] == "ieee"
    assert parametros["umbral_fidelidad"] == 0.9
    assert [h["codigo"] for h in parametros["hitos"]] == [
        "avance_1",
        "avance_2",
        "entrega_plan",
        "avance_3",
        "avance_4",
        "avance_5",
        "avance_6",
        "entrega_final",
    ]


def test_la_semilla_es_la_configuracion_inicial_del_codigo(url_bd_migrada: str) -> None:
    """La versión 1 que escribe la migración (copia literal) coincide con el esquema validado
    y con sus valores por defecto: ni falta ni sobra un parámetro."""
    from app.administracion.parametros import ParametrosFuncionales, parametros_iniciales

    (parametros,) = consultar(url_bd_migrada, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict)
    assert set(parametros) == set(ParametrosFuncionales.model_fields)
    assert ParametrosFuncionales.model_validate(parametros) == parametros_iniciales()


def _ejecutar(url: str, sql: str, *parametros: object) -> None:
    with psycopg.connect(_conninfo(url), autocommit=True) as conexion:
        conexion.execute(sql, parametros)  # type: ignore[arg-type]


def _coleccion_y_caso(url: str, codigo: str, tema: str) -> tuple[str, str]:
    (coleccion_id,) = consultar(
        url,
        "INSERT INTO coleccion (tipo, tema) VALUES ('cientifica', %s) RETURNING id::text",
        tema,
    )[0]
    (caso_id,) = consultar(
        url,
        "INSERT INTO caso (codigo, tipo_autoria, coleccion_cientifica_id)"
        " VALUES (%s, 'individual', %s) RETURNING id::text",
        codigo,
        coleccion_id,
    )[0]
    return str(coleccion_id), str(caso_id)


def test_codigo_de_caso_unico(bd_limpia: str) -> None:
    _, _ = _coleccion_y_caso(bd_limpia, "CASO-A", "TEMA-1")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _coleccion_y_caso(bd_limpia, "CASO-A", "TEMA-2")


@pytest.mark.parametrize(
    ("sql", "error"),
    [
        ("INSERT INTO coleccion (tipo) VALUES ('desconocido')", psycopg.errors.CheckViolation),
        ("INSERT INTO coleccion (tipo) VALUES ('cientifica')", psycopg.errors.CheckViolation),
        ("INSERT INTO coleccion (tipo, tema) VALUES ('guias', 'X')", psycopg.errors.CheckViolation),
        (
            "INSERT INTO cuenta (codigo, hash_contrasena, rol) VALUES ('C-1', 'h', 'A1')",
            psycopg.errors.CheckViolation,
        ),
        (
            "INSERT INTO cuenta (codigo, hash_contrasena, rol) VALUES ('c minus', 'h', 'A2')",
            psycopg.errors.CheckViolation,
        ),
        (
            "INSERT INTO cuenta (codigo, hash_contrasena, rol) VALUES ('C-2', 'h', 'A3')",
            psycopg.errors.CheckViolation,
        ),
    ],
)
def test_valores_permitidos(bd_limpia: str, sql: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        _ejecutar(bd_limpia, sql)


def test_una_sola_coleccion_cientifica_por_tema_y_una_de_guias(bd_limpia: str) -> None:
    _ejecutar(bd_limpia, "INSERT INTO coleccion (tipo, tema) VALUES ('cientifica', 'T-1')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _ejecutar(bd_limpia, "INSERT INTO coleccion (tipo, tema) VALUES ('cientifica', 'T-1')")
    _ejecutar(bd_limpia, "INSERT INTO coleccion (tipo) VALUES ('guias')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _ejecutar(bd_limpia, "INSERT INTO coleccion (tipo) VALUES ('guias')")


def test_clave_compuesta_impide_colgar_datos_de_otro_caso(bd_limpia: str) -> None:
    """Una solicitud del caso B no puede apuntar a una versión del caso A (aislamiento)."""
    _, caso_a = _coleccion_y_caso(bd_limpia, "CASO-A", "TEMA-1")
    _, caso_b = _coleccion_y_caso(bd_limpia, "CASO-B", "TEMA-2")
    version_a = _version(bd_limpia, caso_a)
    (configuracion_id,) = consultar(bd_limpia, "SELECT id::text FROM configuracion")[0]
    insercion = (
        "INSERT INTO solicitud (caso_id, version_id, tipo, alcance_tipo, alcance_ref,"
        " configuracion_id) VALUES (%s, %s, 'busqueda_evidencia', 'consulta', 'x', %s)"
    )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _ejecutar(bd_limpia, insercion, caso_b, version_a, configuracion_id)
    _ejecutar(bd_limpia, insercion, caso_a, version_a, configuracion_id)


def _version(url: str, caso_id: str) -> str:
    (version_id,) = consultar(
        url,
        "INSERT INTO version_borrador (caso_id, hito, ruta_archivo, huella_sha256, tamano_bytes)"
        " VALUES (%s, 'avance_1', '/x', %s, 10) RETURNING id::text",
        caso_id,
        uuid.uuid4().hex + uuid.uuid4().hex,
    )[0]
    return str(version_id)


def _solicitud(url: str, tipo: str, alcance: str, ref: str | None) -> str:
    _, caso = _coleccion_y_caso(url, f"CASO-{uuid.uuid4().hex[:6].upper()}", uuid.uuid4().hex[:8])
    (configuracion_id,) = consultar(url, "SELECT id::text FROM configuracion")[0]
    (solicitud_id,) = consultar(
        url,
        "INSERT INTO solicitud (caso_id, version_id, tipo, alcance_tipo, alcance_ref,"
        " configuracion_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id::text",
        caso,
        _version(url, caso),
        tipo,
        alcance,
        ref,
        configuracion_id,
    )[0]
    return str(solicitud_id)


# Tabla 3 de los insumos de T04: alcances admitidos por tipo.
ADMITIDOS = [
    ("revision_estructura", "seccion", "sec-2"),
    ("plan_tarea", "hito", None),
    ("revision_metodologica", "seccion", "sec-3"),
    ("propuesta_redaccion", "fragmento", "par-14"),
    ("busqueda_evidencia", "consulta", "texto de una consulta ficticia"),
    ("busqueda_evidencia", "fragmento", "par-7"),
    ("verificacion_referencias", "version", None),
]


@pytest.mark.parametrize(("tipo", "alcance", "ref"), ADMITIDOS)
def test_alcances_admitidos_por_tipo(bd_limpia: str, tipo: str, alcance: str, ref: str) -> None:
    _solicitud(bd_limpia, tipo, alcance, ref)


@pytest.mark.parametrize(
    ("tipo", "alcance", "ref"),
    [
        ("revision_estructura", "fragmento", "par-1"),  # estructura trabaja sobre secciones
        ("plan_tarea", "seccion", "sec-1"),
        ("propuesta_redaccion", "seccion", "sec-1"),  # D3: un párrafo, no una sección
        ("propuesta_redaccion", "consulta", "x"),  # la consulta libre es solo de CU-07
        ("verificacion_referencias", "consulta", "x"),
        ("revision_estructura", "seccion", None),  # sección sin identificar
        ("plan_tarea", "hito", "sec-1"),  # el hito toma la versión completa
        ("estructura", "seccion", "sec-1"),  # código viejo, ya no admitido
        ("busqueda_evidencia", "parrafo", "par-1"),
    ],
)
def test_alcances_no_admitidos_se_rechazan(
    bd_limpia: str, tipo: str, alcance: str, ref: str | None
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _solicitud(bd_limpia, tipo, alcance, ref)


def _resultado(url: str) -> tuple[str, str]:
    solicitud_id = _solicitud(url, "busqueda_evidencia", "consulta", "consulta ficticia")
    (resultado_id, caso_id) = consultar(
        url,
        "INSERT INTO resultado (caso_id, solicitud_id, intento)"
        " SELECT caso_id, id, 1 FROM solicitud WHERE id = %s RETURNING id::text, caso_id::text",
        solicitud_id,
    )[0]
    return str(resultado_id), str(caso_id)


def _verificar(url: str, **campos: object) -> None:
    resultado_id, caso_id = _resultado(url)
    valores = {"formato_ok": True, "superada": False} | campos
    columnas = ", ".join(valores)
    marcas = ", ".join(["%s"] * len(valores))
    _ejecutar(
        url,
        f"INSERT INTO verificacion (caso_id, resultado_id, intento, {columnas})"
        f" VALUES (%s, %s, 1, {marcas})",
        caso_id,
        resultado_id,
        *valores.values(),
    )


def test_verificacion_con_los_campos_de_6_7(bd_limpia: str) -> None:
    _verificar(
        bd_limpia,
        formato_ok=True,
        limites_ok=True,
        citas_ok=True,
        n_fuentes_citadas=3,
        n_fuentes_confirmadas=3,
        metodo="mixto",
        acceso_abierto_ok=True,
        fidelidad=0.95,
        umbral_fidelidad=0.9,
        superada=True,
    )
    _verificar(bd_limpia, limites_ok=None, citas_ok=None, superada=True)  # D1 sin fuentes
    filas = consultar(bd_limpia, "SELECT count(*) FROM verificacion WHERE superada")
    assert filas == [(2,)]


@pytest.mark.parametrize(
    "campos",
    [
        {"formato_ok": False, "superada": True},
        {"citas_ok": False, "superada": True},
        {"fidelidad": 0.85, "umbral_fidelidad": 0.9, "superada": True},
        {"n_fuentes_citadas": 2, "n_fuentes_confirmadas": 1, "metodo": "doi", "superada": True},
        {"n_fuentes_citadas": 1, "n_fuentes_confirmadas": 2, "metodo": "doi"},
        {
            "n_fuentes_citadas": 2,
            "n_fuentes_confirmadas": 1,
            "n_fuentes_no_comprobables": 2,
            "metodo": "doi",
        },
        {"n_fuentes_citadas": 1, "n_fuentes_confirmadas": 1},  # confirmada sin método
        {"n_fuentes_citadas": 1, "metodo": "doi"},  # método sin confirmadas
        {"metodo": "isbn", "n_fuentes_citadas": 1, "n_fuentes_confirmadas": 1},
        {"fidelidad": 1.2},
    ],
)
def test_verificacion_incoherente_se_rechaza(bd_limpia: str, campos: dict[str, object]) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _verificar(bd_limpia, **campos)


def test_no_comprobable_no_hace_fallar_el_conteo(bd_limpia: str) -> None:
    """RN-18: un servicio caído deja la fuente no comprobable, no no localizada."""
    _verificar(
        bd_limpia,
        n_fuentes_citadas=2,
        n_fuentes_confirmadas=1,
        n_fuentes_no_comprobables=1,
        metodo="doi",
    )


@pytest.mark.parametrize(
    ("tabla", "columna", "valor"),
    [
        ("resultado", "relevancia_evaluador", 1.5),
        ("resultado", "relevancia_humana", -0.1),
        ("solicitud", "completitud_evaluador", 2.0),
        ("solicitud", "completitud_humana", -1.0),
    ],
)
def test_juicios_de_evaluacion_entre_0_y_1(
    bd_limpia: str, tabla: str, columna: str, valor: float
) -> None:
    resultado_id, _ = _resultado(bd_limpia)
    destino = (
        "id = %s"
        if tabla == "resultado"
        else "id = (SELECT solicitud_id FROM resultado WHERE id = %s)"
    )
    _ejecutar(bd_limpia, f"UPDATE {tabla} SET {columna} = 0.5 WHERE {destino}", resultado_id)
    with pytest.raises(psycopg.errors.CheckViolation):
        _ejecutar(
            bd_limpia, f"UPDATE {tabla} SET {columna} = %s WHERE {destino}", valor, resultado_id
        )


def _documento(url: str, **campos: object) -> str:
    (coleccion_id,) = consultar(
        url, "INSERT INTO coleccion (tipo) VALUES ('guias') RETURNING id::text"
    )[0]
    valores = {"huella_sha256": "e" * 64, "origen": "ingesta"} | campos
    columnas = ", ".join(valores)
    marcas = ", ".join(["%s"] * len(valores))
    (documento_id,) = consultar(
        url,
        f"INSERT INTO documento (coleccion_id, {columnas}) VALUES (%s, {marcas})"
        " RETURNING id::text",
        coleccion_id,
        *valores.values(),
    )[0]
    return str(documento_id)


def test_documento_con_los_metadatos_de_18_2(bd_limpia: str) -> None:
    _documento(
        bd_limpia,
        titulo="Título ficticio",
        autores=json.dumps([{"apellido": "Autora", "inicial": "A."}]),
        anio=2024,
        revista_editorial="Revista ficticia",
        doi="10.0000/ficticio",
        isbn="9780000000002",
        idioma="es",
        licencia="CC BY 4.0",
        estado_oa="gold",
        url_acceso_abierto="https://ejemplo.test/a.pdf",
        ruta_archivo="/privado/a1b2c3.pdf",
    )


@pytest.mark.parametrize("isbn", ["978-00000-000", "12345", "978000000000X", "123456789x"])
def test_isbn_se_guarda_normalizado(bd_limpia: str, isbn: str) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _documento(bd_limpia, isbn=isbn)


def test_vector_lexico_generado_con_configuracion_simple(bd_limpia: str) -> None:
    documento_id = _documento(bd_limpia)
    _ejecutar(
        bd_limpia,
        "INSERT INTO fragmento (documento_id, coleccion_id, orden, texto, seccion_normalizada,"
        " tokens) SELECT id, coleccion_id, 1, 'Los Métodos de ANOVA', 'metodos', 5"
        " FROM documento WHERE id = %s",
        documento_id,
    )
    (lexico,) = consultar(bd_limpia, "SELECT texto_lexico::text FROM fragmento")[0]
    # 'simple' no quita palabras vacías ni reduce a raíces: conserva siglas y términos exactos.
    assert lexico == "'anova':4 'de':3 'los':1 'métodos':2"
    with pytest.raises(psycopg.errors.GeneratedAlways):
        _ejecutar(bd_limpia, "UPDATE fragmento SET texto_lexico = to_tsvector('x')")


def _restricciones_check(url: str) -> set[tuple[str, str, str]]:
    return {
        (str(t), str(n), str(d))
        for t, n, d in consultar(
            url,
            "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)"
            " FROM pg_constraint WHERE contype = 'c' AND connamespace = 'public'::regnamespace",
        )
    }


def test_restricciones_de_las_migraciones_iguales_a_los_modelos(
    url_bd_migrada: str, base_vacia: str
) -> None:
    """Alembic no compara restricciones CHECK ni columnas generadas: se comparan aquí con
    el esquema que crean los modelos directamente."""
    from sqlalchemy import create_engine

    import app.bd.modelos  # noqa: F401
    from app.bd.base import Base

    motor = create_engine(base_vacia)
    with motor.begin() as conexion:
        conexion.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        Base.metadata.create_all(conexion)
    motor.dispose()
    assert _restricciones_check(url_bd_migrada) == _restricciones_check(base_vacia)
    generadas = (
        "SELECT attrelid::regclass::text, attname, pg_get_expr(adbin, adrelid) FROM pg_attribute"
        " JOIN pg_attrdef ON adrelid = attrelid AND adnum = attnum WHERE attgenerated = 's'"
    )
    assert consultar(url_bd_migrada, generadas) == consultar(base_vacia, generadas)


def test_la_migracion_0005_no_pisa_solicitudes_existentes(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0004")
    _, caso = _coleccion_y_caso(base_vacia, "CASO-A", "TEMA-1")
    (configuracion_id,) = consultar(base_vacia, "SELECT id::text FROM configuracion")[0]
    (version_id,) = consultar(
        base_vacia,
        "INSERT INTO version_borrador (caso_id, hito, ruta_archivo, huella_sha256, tamano_bytes)"
        " VALUES (%s, 'H1', '/x', %s, 10) RETURNING id::text",
        caso,
        "a" * 64,
    )[0]
    _ejecutar(
        base_vacia,
        "INSERT INTO solicitud (caso_id, version_id, tipo, alcance_tipo, alcance_contenido,"
        " configuracion_id) VALUES (%s, %s, 'evidencia', 'consulta', '{}', %s)",
        caso,
        version_id,
        configuracion_id,
    )
    with pytest.raises(RuntimeError, match="solicitud tiene 1 filas"):
        command.upgrade(cfg, "head")
    assert consultar(base_vacia, "SELECT version_num FROM alembic_version") == [("0004",)]


def test_la_migracion_0006_pasa_las_normas_a_minusculas_y_vuelve(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0005")
    _, caso = _coleccion_y_caso(base_vacia, "CASO-A", "TEMA-1")
    _ejecutar(base_vacia, "UPDATE caso SET norma_citacion = 'APA7' WHERE id = %s", caso)
    command.upgrade(cfg, "0006")
    assert consultar(base_vacia, "SELECT norma_citacion FROM caso") == [("apa7",)]
    command.downgrade(cfg, "0005")
    assert consultar(base_vacia, "SELECT norma_citacion FROM caso") == [("APA7",)]
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and parametros["hitos"] == []


def test_la_migracion_0006_respeta_una_version_1_congelada(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0005")
    _ejecutar(base_vacia, "UPDATE configuracion SET congelada = true")
    with pytest.raises(RuntimeError, match="congelada"):
        command.upgrade(cfg, "0006")


def test_una_version_vigente_por_hito(bd_limpia: str) -> None:
    _, caso = _coleccion_y_caso(bd_limpia, "CASO-A", "TEMA-1")
    insercion = (
        "INSERT INTO version_borrador (caso_id, hito, ruta_archivo, huella_sha256, tamano_bytes,"
        " vigente) VALUES (%s, 'H1', '/x', %s, 10, %s)"
    )
    _ejecutar(bd_limpia, insercion, caso, "a" * 64, True)
    _ejecutar(bd_limpia, insercion, caso, "b" * 64, False)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _ejecutar(bd_limpia, insercion, caso, "c" * 64, True)


def test_extension_vector_y_columna_de_1024(url_bd_migrada: str) -> None:
    filas = consultar(
        url_bd_migrada,
        "SELECT format_type(atttypid, atttypmod) FROM pg_attribute"
        " WHERE attrelid = 'fragmento'::regclass AND attname = 'embedding'",
    )
    assert filas == [("vector(1024)",)]


def test_la_migracion_0007_cierra_la_lista_de_normas_d12(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0007")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict)
    assert parametros["normas_citacion"] == ["ieee", "apa7", "vancouver"]
    assert parametros["norma_por_defecto"] == "ieee"
    _, caso = _coleccion_y_caso(base_vacia, "CASO-A", "TEMA-1")
    _ejecutar(base_vacia, "UPDATE caso SET norma_citacion = 'vancouver' WHERE id = %s", caso)
    with pytest.raises(RuntimeError, match="vancouver"):
        command.downgrade(cfg, "0006")
    _ejecutar(base_vacia, "UPDATE caso SET norma_citacion = 'ieee'")
    command.downgrade(cfg, "0006")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and parametros["normas_citacion"] == ["ieee", "apa7"]


def test_la_migracion_0008_agrega_el_umbral_de_documento_incompleto(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0008")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and parametros["palabras_minimas_articulo"] == 1500
    command.downgrade(cfg, "0007")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and "palabras_minimas_articulo" not in parametros
    _ejecutar(base_vacia, "UPDATE configuracion SET congelada = true")
    with pytest.raises(RuntimeError, match="congelada"):
        command.upgrade(cfg, "0008")


def test_la_migracion_0012_agrega_los_modelos_de_lenguaje(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0012")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict)
    assert [m["proveedor"] for m in parametros["modelos"]] == ["groq", "deepseek", "gemini"]
    assert parametros["modelos"][0]["modelo"] == "openai/gpt-oss-120b"
    assert parametros["versiones_instrucciones"] == {}
    command.downgrade(cfg, "0011")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and "modelos" not in parametros
    assert "versiones_instrucciones" not in parametros
    _ejecutar(base_vacia, "UPDATE configuracion SET congelada = true")
    with pytest.raises(RuntimeError, match="congelada"):
        command.upgrade(cfg, "0012")


def test_la_migracion_0013_agrega_los_parametros_de_recuperacion(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0013")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict)
    assert (parametros["candidatos_reranking"], parametros["presupuesto_tokens_contexto"]) == (
        20,
        2400,
    )
    assert parametros["versiones_instrucciones"] == {"suficiencia": "v1"}
    command.downgrade(cfg, "0012")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and "candidatos_reranking" not in parametros
    assert parametros["versiones_instrucciones"] == {}
    _ejecutar(base_vacia, "UPDATE configuracion SET congelada = true")
    with pytest.raises(RuntimeError, match="congelada"):
        command.upgrade(cfg, "0013")


def test_la_migracion_0014_agrega_la_validacion_de_consultas(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0014")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict)
    assert (parametros["consulta_min_palabras"], parametros["pertinencia_umbral"]) == (5, 0.55)
    assert parametros["versiones_instrucciones"] == {"suficiencia": "v1", "evidencia": "v1"}
    command.downgrade(cfg, "0013")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and "pertinencia_umbral" not in parametros
    assert parametros["versiones_instrucciones"] == {"suficiencia": "v1"}
    _ejecutar(base_vacia, "UPDATE configuracion SET congelada = true")
    with pytest.raises(RuntimeError, match="congelada"):
        command.upgrade(cfg, "0014")


def test_la_migracion_0015_agrega_la_explicacion_de_discrepancias(base_vacia: str) -> None:
    cfg = configuracion_alembic(base_vacia)
    command.upgrade(cfg, "0015")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and parametros["explicar_discrepancias"] is False
    assert parametros["versiones_instrucciones"] == {
        "suficiencia": "v1",
        "evidencia": "v1",
        "referencias": "v1",
    }
    command.downgrade(cfg, "0014")
    (parametros,) = consultar(base_vacia, "SELECT parametros FROM configuracion")[0]
    assert isinstance(parametros, dict) and "explicar_discrepancias" not in parametros
    assert parametros["versiones_instrucciones"] == {"suficiencia": "v1", "evidencia": "v1"}
    _ejecutar(base_vacia, "UPDATE configuracion SET congelada = true")
    with pytest.raises(RuntimeError, match="congelada"):
        command.upgrade(cfg, "0015")
