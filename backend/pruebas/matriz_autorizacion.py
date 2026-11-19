"""Matriz automática de autorización (T05, apartado 4.5).

**Toda ruta nueva se añade aquí en la misma solicitud de cambio.** Una prueba unitaria
falla si la aplicación expone una ruta que no está en la matriz (o al revés), y una
prueba de integración recorre la matriz con sesiones de cada rol y de otro caso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Politica(StrEnum):
    PUBLICA = "publica"  # sin sesión
    SESION = "sesion"  # cualquier sesión válida (incluso con contraseña inicial pendiente)
    CASO = "caso"  # solo A1
    INVESTIGADOR = "investigador"  # solo A2


@dataclass(frozen=True)
class Entrada:
    politica: Politica
    ejemplo: str | None = None  # ruta concreta si tiene parámetros; {CASO_A} = código del caso A
    cuerpo: dict[str, Any] = field(default_factory=dict)
    datos_de_caso: bool = False  # devuelve datos de un caso: otro caso no debe verlos
    # Formulario con archivo (multipart): campos y nombre de un .docx de pruebas/datos/docx/.
    formulario: dict[str, str] = field(default_factory=dict)
    archivo: str | None = None


ID_FICTICIO = "00000000-0000-4000-8000-000000000000"  # basta para comprobar 401 y 403

MATRIZ: dict[tuple[str, str], Entrada] = {
    ("GET", "/salud"): Entrada(Politica.PUBLICA),
    ("POST", "/sesion"): Entrada(Politica.PUBLICA, cuerpo={"codigo": "X", "contrasena": "x"}),
    ("GET", "/sesion"): Entrada(Politica.SESION),
    ("DELETE", "/sesion"): Entrada(Politica.SESION),
    ("POST", "/sesion/contrasena"): Entrada(
        Politica.SESION, cuerpo={"contrasena_actual": "x", "contrasena_nueva": "y"}
    ),
    ("GET", "/caso"): Entrada(Politica.CASO, datos_de_caso=True),
    # Borrador (T11). {VERSION_A} = una versión del caso A creada por la prueba.
    ("POST", "/caso/versiones"): Entrada(
        Politica.CASO, datos_de_caso=True, formulario={"hito": "avance_1"}, archivo="valido.docx"
    ),
    ("GET", "/caso/versiones"): Entrada(Politica.CASO, datos_de_caso=True),
    ("GET", "/caso/versiones/{version_id}"): Entrada(
        Politica.CASO, ejemplo="/caso/versiones/{VERSION_A}", datos_de_caso=True
    ),
    # Secciones del borrador (T12).
    ("GET", "/caso/versiones/{version_id}/secciones"): Entrada(
        Politica.CASO, ejemplo="/caso/versiones/{VERSION_A}/secciones", datos_de_caso=True
    ),
    ("PUT", "/caso/versiones/{version_id}/secciones"): Entrada(
        Politica.CASO,
        ejemplo="/caso/versiones/{VERSION_A}/secciones",
        cuerpo={"titulos": [{"parrafo": "p2", "nivel": 1}]},
        datos_de_caso=True,
    ),
    ("PUT", "/caso/versiones/{version_id}/referencias"): Entrada(
        Politica.CASO,
        ejemplo="/caso/versiones/{VERSION_A}/referencias",
        cuerpo={"desde": "p13"},
        datos_de_caso=True,
    ),
    ("GET", "/investigador/colecciones"): Entrada(Politica.INVESTIGADOR),
    ("POST", "/investigador/colecciones/cientificas"): Entrada(
        Politica.INVESTIGADOR, cuerpo={"tema": "TEMA-MATRIZ"}
    ),
    ("GET", "/investigador/casos"): Entrada(Politica.INVESTIGADOR),
    ("POST", "/investigador/casos"): Entrada(
        Politica.INVESTIGADOR,
        cuerpo={"codigo": "CASO-MATRIZ", "tipo_autoria": "individual", "tema": "TEMA-A"},
    ),
    ("GET", "/investigador/casos/{codigo}"): Entrada(
        Politica.INVESTIGADOR, ejemplo="/investigador/casos/{CASO_A}"
    ),
    ("POST", "/investigador/casos/{codigo}/desactivar"): Entrada(
        Politica.INVESTIGADOR, ejemplo="/investigador/casos/{CASO_A}/desactivar"
    ),
    ("POST", "/investigador/casos/{codigo}/reactivar"): Entrada(
        Politica.INVESTIGADOR, ejemplo="/investigador/casos/{CASO_A}/reactivar"
    ),
    ("PUT", "/investigador/casos/{codigo}/norma"): Entrada(
        Politica.INVESTIGADOR,
        ejemplo="/investigador/casos/{CASO_A}/norma",
        cuerpo={"norma": "ieee"},
    ),
    # Corpus científico (T10)
    ("GET", "/investigador/colecciones/{coleccion_id}/documentos"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/colecciones/{ID_FICTICIO}/documentos"
    ),
    ("POST", "/investigador/colecciones/{coleccion_id}/documentos"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/colecciones/{ID_FICTICIO}/documentos"
    ),
    ("GET", "/investigador/colecciones/{coleccion_id}/exclusiones"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/colecciones/{ID_FICTICIO}/exclusiones"
    ),
    ("POST", "/investigador/documentos/{documento_id}/confirmar"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/documentos/{ID_FICTICIO}/confirmar"
    ),
    ("POST", "/investigador/documentos/{documento_id}/retirar"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/documentos/{ID_FICTICIO}/retirar"
    ),
}

RUTAS_EXCLUIDAS = {"/docs", "/docs/oauth2-redirect", "/openapi.json"}
