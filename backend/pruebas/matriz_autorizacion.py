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
    # Códigos que el propio caso puede recibir sin que sea un error de autorización:
    # 503 si la ruta necesita un servicio que las pruebas no tienen, 404 si el
    # ejemplo usa un identificador ficticio (T19).
    admite_propio: frozenset[int] = frozenset()


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
    # Búsqueda de evidencia (T19). Sin servicio de modelos en las pruebas responde 503.
    ("POST", "/caso/evidencias"): Entrada(
        Politica.CASO,
        cuerpo={"consulta": "¿La tutoría entre pares reduce la ansiedad?"},
        admite_propio=frozenset({503}),
    ),
    ("GET", "/caso/evidencias/{solicitud_id}"): Entrada(
        Politica.CASO,
        ejemplo=f"/caso/evidencias/{ID_FICTICIO}",
        admite_propio=frozenset({404}),
    ),
    ("GET", "/caso/solicitudes"): Entrada(Politica.CASO, datos_de_caso=True),
    # Estructura y coherencia (T23). Sin servicio de modelos en las pruebas responde 503.
    ("GET", "/caso/estructura/secciones"): Entrada(Politica.CASO, datos_de_caso=True),
    ("POST", "/caso/estructura"): Entrada(
        Politica.CASO, cuerpo={"seccion_id": "s1"}, admite_propio=frozenset({503})
    ),
    ("GET", "/caso/estructura/{solicitud_id}"): Entrada(
        Politica.CASO,
        ejemplo=f"/caso/estructura/{ID_FICTICIO}",
        admite_propio=frozenset({404}),
    ),
    # Plan de tarea (T24). Sin servicio de modelos en las pruebas responde 503.
    ("GET", "/caso/plan/hitos"): Entrada(Politica.CASO, datos_de_caso=True),
    ("POST", "/caso/plan"): Entrada(
        Politica.CASO, cuerpo={"hito": "avance_1"}, admite_propio=frozenset({503})
    ),
    ("GET", "/caso/plan/{solicitud_id}"): Entrada(
        Politica.CASO,
        ejemplo=f"/caso/plan/{ID_FICTICIO}",
        admite_propio=frozenset({404}),
    ),
    # Diagnóstico metodológico (T26). Sin servicio de modelos en las pruebas responde 503.
    ("GET", "/caso/metodologia/secciones"): Entrada(Politica.CASO, datos_de_caso=True),
    ("POST", "/caso/metodologia"): Entrada(
        Politica.CASO, cuerpo={"seccion_id": "s1"}, admite_propio=frozenset({503})
    ),
    ("GET", "/caso/metodologia/{solicitud_id}"): Entrada(
        Politica.CASO,
        ejemplo=f"/caso/metodologia/{ID_FICTICIO}",
        admite_propio=frozenset({404}),
    ),
    # Propuesta de redacción (T27). Sin servicio de modelos en las pruebas responde 503.
    ("GET", "/caso/redaccion/parrafos"): Entrada(Politica.CASO, datos_de_caso=True),
    ("POST", "/caso/redaccion"): Entrada(
        Politica.CASO, cuerpo={"parrafo_id": "p1"}, admite_propio=frozenset({503})
    ),
    ("GET", "/caso/redaccion/{solicitud_id}"): Entrada(
        Politica.CASO,
        ejemplo=f"/caso/redaccion/{ID_FICTICIO}",
        admite_propio=frozenset({404}),
    ),
    # Verificación de referencias (T20). Sin GROBID en las pruebas responde 503.
    ("POST", "/caso/referencias"): Entrada(Politica.CASO, admite_propio=frozenset({503})),
    ("GET", "/caso/referencias/{solicitud_id}"): Entrada(
        Politica.CASO,
        ejemplo=f"/caso/referencias/{ID_FICTICIO}",
        admite_propio=frozenset({404}),
    ),
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
    # Importador de referencias del artículo O1 (T15)
    ("POST", "/investigador/colecciones/{coleccion_id}/importaciones"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/colecciones/{ID_FICTICIO}/importaciones"
    ),
    ("GET", "/investigador/importaciones/{importacion_id}"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/importaciones/{ID_FICTICIO}"
    ),
    ("GET", "/investigador/colecciones/{coleccion_id}/informe"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/colecciones/{ID_FICTICIO}/informe"
    ),
    ("GET", "/investigador/colecciones/{coleccion_id}/referencias"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/colecciones/{ID_FICTICIO}/referencias"
    ),
    ("POST", "/investigador/referencias/{referencia_id}/pdf"): Entrada(
        Politica.INVESTIGADOR, ejemplo=f"/investigador/referencias/{ID_FICTICIO}/pdf"
    ),
}

RUTAS_EXCLUIDAS = {"/docs", "/docs/oauth2-redirect", "/openapi.json"}
