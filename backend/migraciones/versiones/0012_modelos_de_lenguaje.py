"""T17: modelos de lenguaje y versiones de instrucciones en la configuración (RNF-21).

Añade a la versión 1 de la configuración ``modelos`` (Groq, DeepSeek y Gemini, con sus
límites y precios de lista) y ``versiones_instrucciones`` (vacío: cada agente agrega la
suya en su fase). Igual que 0006 a 0008, solo se aplica si la versión 1 no está congelada
y ninguna solicitud la usa. Es una migración de datos: el esquema no cambia.

Revisión: 0012
Anterior: 0011
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Valores congelados de T17-01 (22 de noviembre de 2026); no se importan del código.
MODELOS = [
    {
        "proveedor": "groq",
        "modelo": "openai/gpt-oss-120b",
        "alias": False,
        "max_tokens_salida": 2048,
        "precio_entrada_usd_millon": 0.15,
        "precio_salida_usd_millon": 0.6,
        "limites": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200000},
    },
    {
        "proveedor": "deepseek",
        "modelo": "deepseek-flash",
        "alias": True,
        "max_tokens_salida": 2048,
        "precio_entrada_usd_millon": 0.3,
        "precio_salida_usd_millon": 1.2,
        "limites": {"rpm": None, "rpd": None, "tpm": None, "tpd": None},
    },
    {
        "proveedor": "gemini",
        "modelo": "gemini-3.8-flash",
        "alias": False,
        "max_tokens_salida": 2048,
        "precio_entrada_usd_millon": None,
        "precio_salida_usd_millon": None,
        "limites": {"rpm": 5, "rpd": 100, "tpm": None, "tpd": None},
    },
]
CLAVES = ("modelos", "versiones_instrucciones")


def _exigir_version_1_libre() -> None:
    fila = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT c.congelada,"
                " (SELECT count(*) FROM solicitud s WHERE s.configuracion_id = c.id)"
                " FROM configuracion c WHERE c.numero_version = 1"
            )
        )
        .one_or_none()
    )
    if fila is None:
        raise RuntimeError("No existe la versión 1 de la configuración (migración 0002).")
    congelada, solicitudes = fila
    if congelada or solicitudes:
        raise RuntimeError(
            "La versión 1 de la configuración está congelada o ya la usan solicitudes;"
            " sus parámetros no se reemplazan. Cree una versión nueva."
        )


def upgrade() -> None:
    _exigir_version_1_libre()
    op.get_bind().execute(
        sa.text(
            "UPDATE configuracion SET parametros = parametros"
            " || jsonb_build_object('modelos', CAST(:modelos AS jsonb),"
            " 'versiones_instrucciones', '{}'::jsonb)"
            " WHERE numero_version = 1"
        ),
        {"modelos": json.dumps(MODELOS)},
    )


def downgrade() -> None:
    _exigir_version_1_libre()
    op.execute(
        "UPDATE configuracion SET parametros = parametros - 'modelos'"
        " - 'versiones_instrucciones' WHERE numero_version = 1"
    )
