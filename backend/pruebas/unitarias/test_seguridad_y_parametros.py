"""Unitarias de credenciales (Argon2, tokens, CSRF), política y parámetros funcionales."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.administracion.parametros import ParametrosFuncionales, parametros_iniciales
from app.seguridad import credenciales, politica


def test_hash_argon2id_y_verificacion() -> None:
    hash_ = credenciales.hashear_contrasena("una-contrasena-ficticia")
    assert hash_.startswith("$argon2id$")
    assert "una-contrasena-ficticia" not in hash_
    assert credenciales.verificar_contrasena(hash_, "una-contrasena-ficticia")
    assert not credenciales.verificar_contrasena(hash_, "otra")
    assert not credenciales.verificar_contrasena("no-es-un-hash", "x")


def test_mismo_texto_produce_hashes_distintos() -> None:
    assert credenciales.hashear_contrasena("a") != credenciales.hashear_contrasena("a")


def test_contrasena_inicial_aleatoria() -> None:
    generadas = {credenciales.generar_contrasena_inicial() for _ in range(200)}
    assert len(generadas) == 200
    assert all(len(c) == 16 for c in generadas)


def test_token_y_huella() -> None:
    token = credenciales.generar_token_sesion()
    assert len(token) >= 43
    huella = credenciales.huella_token(token)
    assert len(huella) == 64 and token not in huella


def test_csrf_firmado_con_el_secreto() -> None:
    token = credenciales.generar_token_sesion()
    valor = credenciales.token_csrf("secreto-1", token)
    assert credenciales.csrf_valido("secreto-1", token, valor)
    assert not credenciales.csrf_valido("secreto-2", token, valor)
    assert not credenciales.csrf_valido("secreto-1", credenciales.generar_token_sesion(), valor)
    assert not credenciales.csrf_valido("secreto-1", token, None)


def test_valores_fijados_de_sesion() -> None:
    assert politica.DURACION_ABSOLUTA_SESION.total_seconds() == 8 * 3600
    assert politica.INACTIVIDAD_MAXIMA.total_seconds() == 60 * 60
    assert politica.MAXIMO_SESIONES_POR_CUENTA == 2
    assert politica.MAXIMO_FALLOS == 5
    assert politica.VENTANA_FALLOS.total_seconds() == 15 * 60


def test_parametros_iniciales_son_los_de_los_insumos() -> None:
    """Tabla 4 de los insumos de T04, valor por valor."""
    p = parametros_iniciales()
    assert (p.k_denso, p.k_lexico, p.rrf_constante, p.n_reranking) == (30, 30, 60, 8)
    assert (p.suficiencia_n, p.suficiencia_tau) == (2, 0.5)
    assert p.ventana_tokens.model_dump() == {"minimo": 300, "maximo": 450, "objetivo": 400}
    assert p.umbral_fidelidad == 0.90
    assert (p.limite_palabras_d3, p.factor_extension_d3, p.limite_reescritura_palabras) == (
        250,
        1.2,
        40,
    )
    assert (p.normas_citacion, p.norma_por_defecto) == (["ieee", "apa7", "vancouver"], "ieee")
    assert (p.tamano_max_docx_mb, p.tamano_max_pdf_mb, p.paginas_max_pdf) == (15, 25, 60)
    assert p.uso_minimo_por_hito == 1


def test_catalogo_de_hitos() -> None:
    """Tabla 2 de los insumos de T04: ocho hitos en orden."""
    hitos = parametros_iniciales().hitos
    assert [(h.orden, h.codigo) for h in hitos] == [
        (1, "avance_1"),
        (2, "avance_2"),
        (3, "entrega_plan"),
        (4, "avance_3"),
        (5, "avance_4"),
        (6, "avance_5"),
        (7, "avance_6"),
        (8, "entrega_final"),
    ]
    assert hitos[2].nombre == "Entrega final del plan"
    assert hitos[7].contenido == "Artículo completo"
    assert parametros_iniciales().hito("avance_4") == hitos[4]
    assert parametros_iniciales().hito("H1") is None


_HITO = {"orden": 1, "codigo": "avance_1", "nombre": "A", "contenido": "B"}


@pytest.mark.parametrize(
    "cambio",
    [
        {"norma_por_defecto": "mla"},
        {"normas_citacion": ["ieee", "ieee"]},
        {"normas_citacion": ["IEEE"], "norma_por_defecto": "IEEE"},
        {"normas_citacion": []},
        {"ventana_tokens": {"minimo": 500, "maximo": 300, "objetivo": 400}},
        {"ventana_tokens": {"minimo": 300, "maximo": 450, "objetivo": 600}},
        {"umbral_fidelidad": 1.5},
        {"suficiencia_tau": -0.1},
        {"suficiencia_n": 9},
        {"parametro_desconocido": 1},
        {"hitos": []},
        {"hitos": [_HITO, _HITO | {"orden": 2}]},
        {"hitos": [_HITO | {"orden": 2}]},
        {"hitos": [_HITO | {"codigo": "Avance 1"}]},
    ],
)
def test_parametros_invalidos_se_rechazan(cambio: dict[str, object]) -> None:
    datos = parametros_iniciales().model_dump() | cambio
    with pytest.raises(ValidationError):
        ParametrosFuncionales.model_validate(datos)
