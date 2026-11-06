"""T04: configuración inicial versión 1 con el catálogo de hitos (insumos de T04, 2 y 4).

Reemplaza los parámetros provisionales que dejó 0002 en la versión 1 por los de los
insumos: nombres de parámetro de la tabla 4, tau y N de la suficiencia, constante de
RRF, ventana con objetivo, uso mínimo por hito y los ocho hitos. La versión 1 sigue
siendo provisional (T34 recalibra). Los códigos de norma pasan a minúsculas (``ieee``,
``apa7``), también en los casos y en su registro de cambios.

Solo se aplica si la versión 1 no está congelada y ninguna solicitud la usa: así ningún
dato registrado queda asociado a parámetros distintos de los que tuvo.

Revisión: 0006
Anterior: 0005
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMENTARIO_V1 = (
    "Versión 1 provisional: insumos de T04 (apartados 2 y 4) y especificación de la Fase 1"
    " (6.7, 18.4 y 18.6). T34 recalibra."
)
COMENTARIO_0002 = "Valores iniciales de la hoja de ruta técnica (T04)."

# Copia literal; la migración no depende de app.administracion.parametros.
PARAMETROS_V1 = json.loads(
    """
{
    "k_denso": 30,
    "k_lexico": 30,
    "rrf_constante": 60,
    "n_reranking": 8,
    "suficiencia_n": 2,
    "suficiencia_tau": 0.5,
    "ventana_tokens": {"minimo": 300, "maximo": 450, "objetivo": 400},
    "solapamiento_oraciones": 1,
    "umbral_fidelidad": 0.9,
    "limite_palabras_d3": 250,
    "factor_extension_d3": 1.2,
    "limite_reescritura_palabras": 40,
    "normas_citacion": ["ieee", "apa7"],
    "norma_por_defecto": "ieee",
    "tamano_max_docx_mb": 15,
    "tamano_max_pdf_mb": 25,
    "paginas_max_pdf": 60,
    "uso_minimo_por_hito": 1,
    "hitos": [
        {"orden": 1, "codigo": "avance_1", "nombre": "Avance 1", "contenido": "Planteamiento"},
        {"orden": 2, "codigo": "avance_2", "nombre": "Avance 2",
         "contenido": "Metodología y estado del arte"},
        {"orden": 3, "codigo": "entrega_plan", "nombre": "Entrega final del plan",
         "contenido": "Plan de tesis completo"},
        {"orden": 4, "codigo": "avance_3", "nombre": "Avance 3", "contenido": "Introducción"},
        {"orden": 5, "codigo": "avance_4", "nombre": "Avance 4", "contenido": "Metodología"},
        {"orden": 6, "codigo": "avance_5", "nombre": "Avance 5", "contenido": "Resultados"},
        {"orden": 7, "codigo": "avance_6", "nombre": "Avance 6",
         "contenido": "Discusión y conclusiones"},
        {"orden": 8, "codigo": "entrega_final", "nombre": "Entrega final del artículo",
         "contenido": "Artículo completo"}
    ]
}
"""
)

# Lo que dejó 0002, para el descenso.
PARAMETROS_0002 = json.loads(
    """
{
    "normas_citacion": ["IEEE", "APA7"],
    "norma_por_defecto": "IEEE",
    "hitos": [],
    "recuperacion": {"k_denso": 30, "k_lexico": 30, "numero_final": 8, "n_minimo": null,
                     "tau": null},
    "segmentacion": {"ventana_min_tokens": 300, "ventana_max_tokens": 450,
                     "solapamiento_oraciones": 1},
    "verificacion": {"umbral_fidelidad": 0.9, "max_palabras_cita_d1": 40,
                     "factor_extension_d3": 1.2, "max_palabras_parrafo_d3": 250},
    "limites": {"docx_mb": 15, "pdf_mb": 25, "pdf_paginas": 60}
}
"""
)


def _exigir_version_1_libre() -> None:
    conexion = op.get_bind()
    fila = conexion.execute(
        sa.text(
            "SELECT c.congelada, (SELECT count(*) FROM solicitud s WHERE s.configuracion_id = c.id)"
            " FROM configuracion c WHERE c.numero_version = 1"
        )
    ).one_or_none()
    if fila is None:
        raise RuntimeError("No existe la versión 1 de la configuración (migración 0002).")
    congelada, solicitudes = fila
    if congelada or solicitudes:
        raise RuntimeError(
            "La versión 1 de la configuración está congelada o ya la usan solicitudes;"
            " sus parámetros no se reemplazan. Cree una versión nueva."
        )


def _reemplazar(parametros: dict[str, object], comentario: str) -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE configuracion SET parametros = CAST(:parametros AS jsonb),"
            " comentario = :comentario WHERE numero_version = 1"
        ),
        {"parametros": json.dumps(parametros, ensure_ascii=False), "comentario": comentario},
    )


def _normas(funcion: str, por_defecto: str) -> None:
    op.execute(f"UPDATE caso SET norma_citacion = {funcion}(norma_citacion)")
    op.execute(
        f"UPDATE cambio_norma SET norma_anterior = {funcion}(norma_anterior),"
        f" norma_nueva = {funcion}(norma_nueva)"
    )
    op.alter_column(
        "caso",
        "norma_citacion",
        existing_type=sa.String(20),
        existing_nullable=False,
        server_default=por_defecto,
    )


def upgrade() -> None:
    _exigir_version_1_libre()
    _reemplazar(PARAMETROS_V1, COMENTARIO_V1)
    _normas("lower", "ieee")


def downgrade() -> None:
    _exigir_version_1_libre()
    _reemplazar(PARAMETROS_0002, COMENTARIO_0002)
    _normas("upper", "IEEE")
