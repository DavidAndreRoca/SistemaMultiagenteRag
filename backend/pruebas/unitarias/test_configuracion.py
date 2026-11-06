import pytest

from app.configuracion import Entorno, ErrorConfiguracion, cargar_ajustes
from pruebas.conftest import SECRETO_PRUEBAS, variables_base

SECRETO_LARGO = "s" * 40


def test_pruebas_solo_exige_las_tres_obligatorias() -> None:
    ajustes = cargar_ajustes(variables_base())
    assert ajustes.entorno is Entorno.PRUEBAS
    assert ajustes.documentacion_habilitada


@pytest.mark.parametrize("faltante", ["ENTORNO", "URL_BD", "SECRETO_SESION"])
def test_falta_obligatoria_en_todo_entorno_informa_el_nombre(faltante: str) -> None:
    variables = variables_base()
    del variables[faltante]
    with pytest.raises(ErrorConfiguracion, match=faltante):
        cargar_ajustes(variables)


def test_variable_vacia_cuenta_como_faltante() -> None:
    with pytest.raises(ErrorConfiguracion, match="URL_BD"):
        cargar_ajustes(variables_base(URL_BD="   "))


def test_desarrollo_exige_correo_polite() -> None:
    variables = variables_base(ENTORNO="desarrollo", SECRETO_SESION=SECRETO_LARGO)
    with pytest.raises(ErrorConfiguracion, match="CORREO_POLITE"):
        cargar_ajustes(variables)
    variables["CORREO_POLITE"] = "proyecto@example.org"
    assert cargar_ajustes(variables).entorno is Entorno.DESARROLLO


def test_produccion_exige_correo_y_clave_openalex() -> None:
    variables = variables_base(ENTORNO="produccion", SECRETO_SESION=SECRETO_LARGO)
    with pytest.raises(ErrorConfiguracion) as info:
        cargar_ajustes(variables)
    assert "CORREO_POLITE" in str(info.value)
    assert "CLAVE_OPENALEX" in str(info.value)
    variables.update(CORREO_POLITE="proyecto@example.org", CLAVE_OPENALEX="k")
    ajustes = cargar_ajustes(variables)
    assert ajustes.es_produccion
    assert not ajustes.documentacion_habilitada


def test_secreto_corto_se_rechaza_fuera_de_pruebas() -> None:
    variables = variables_base(ENTORNO="desarrollo", SECRETO_SESION="corto")
    variables["CORREO_POLITE"] = "proyecto@example.org"
    with pytest.raises(ErrorConfiguracion, match="al menos 32"):
        cargar_ajustes(variables)


def test_entorno_desconocido_se_rechaza() -> None:
    with pytest.raises(ErrorConfiguracion, match="ENTORNO"):
        cargar_ajustes(variables_base(ENTORNO="staging"))


def test_los_secretos_no_aparecen_en_repr_ni_en_el_mensaje_de_error() -> None:
    ajustes = cargar_ajustes(variables_base(CLAVE_GROQ="gsk_clave_muy_secreta"))
    texto = repr(ajustes) + str(ajustes)
    assert "gsk_clave_muy_secreta" not in texto
    assert SECRETO_PRUEBAS not in texto
    with pytest.raises(ErrorConfiguracion) as info:
        cargar_ajustes(variables_base(ENTORNO="staging", SECRETO_SESION="valor-secreto-xyz"))
    assert "valor-secreto-xyz" not in str(info.value)
