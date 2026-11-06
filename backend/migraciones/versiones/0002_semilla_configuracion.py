"""T04: semilla de la configuración versionada (versión 1, vigente).

Los valores se copian aquí de forma literal para que la migración no cambie si el
código evoluciona. tau y N quedan en null y el catálogo de hitos vacío: la hoja de
ruta no los fija (especificación de la Fase 1, 18.6, y calibración en T34).

Revisión: 0002
Anterior: 0001
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PARAMETROS_V1 = json.loads(
    """
{
    "normas_citacion": [
        "IEEE",
        "APA7"
    ],
    "norma_por_defecto": "IEEE",
    "hitos": [],
    "recuperacion": {
        "k_denso": 30,
        "k_lexico": 30,
        "numero_final": 8,
        "n_minimo": null,
        "tau": null
    },
    "segmentacion": {
        "ventana_min_tokens": 300,
        "ventana_max_tokens": 450,
        "solapamiento_oraciones": 1
    },
    "verificacion": {
        "umbral_fidelidad": 0.9,
        "max_palabras_cita_d1": 40,
        "factor_extension_d3": 1.2,
        "max_palabras_parrafo_d3": 250
    },
    "limites": {
        "docx_mb": 15,
        "pdf_mb": 25,
        "pdf_paginas": 60
    }
}
"""
)


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "INSERT INTO configuracion (numero_version, parametros, comentario, vigente, congelada)"
            " VALUES (1, CAST(:parametros AS jsonb), :comentario, true, false)"
        ),
        {
            "parametros": json.dumps(PARAMETROS_V1),
            "comentario": "Valores iniciales de la hoja de ruta técnica (T04).",
        },
    )


def downgrade() -> None:
    op.execute("DELETE FROM configuracion WHERE numero_version = 1")
