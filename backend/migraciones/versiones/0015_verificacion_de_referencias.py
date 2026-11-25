"""T20: parámetro de la explicación de discrepancias y versión de la instrucción de D4.

Añade a la versión 1 de la configuración ``explicar_discrepancias = false`` (T20-01, d) y
fija ``versiones_instrucciones.referencias = v1``. Igual que 0006 a 0014, solo se aplica si
la versión 1 no está congelada y ninguna solicitud la usa. Es una migración de datos.

Revisión: 0015
Anterior: 0014
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PARAMETROS = {"explicar_discrepancias": False}


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
            "UPDATE configuracion SET parametros = parametros || CAST(:nuevos AS jsonb)"
            " || jsonb_build_object('versiones_instrucciones',"
            " coalesce(parametros -> 'versiones_instrucciones', '{}'::jsonb)"
            " || CAST(:version AS jsonb))"
            " WHERE numero_version = 1"
        ),
        {"nuevos": json.dumps(PARAMETROS), "version": json.dumps({"referencias": "v1"})},
    )


def downgrade() -> None:
    _exigir_version_1_libre()
    op.execute(
        "UPDATE configuracion SET parametros = (parametros - 'explicar_discrepancias')"
        " || jsonb_build_object('versiones_instrucciones',"
        " (parametros -> 'versiones_instrucciones') - 'referencias')"
        " WHERE numero_version = 1"
    )
