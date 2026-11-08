"""T09: umbral de palabras del documento incompleto (Fase 1, 18.3).

Añade ``palabras_minimas_articulo = 1500`` a la versión 1 de la configuración: un
artículo del que se extraen menos palabras queda "incompleto" y solo se indexa si el
investigador lo confirma. Igual que 0006 y 0007, solo se aplica si la versión 1 no está
congelada y ninguna solicitud la usa. Es una migración de datos: el esquema no cambia.

Revisión: 0008
Anterior: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PALABRAS_MINIMAS_ARTICULO = 1500


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
            "UPDATE configuracion SET parametros = jsonb_set(parametros,"
            " '{palabras_minimas_articulo}', CAST(:valor AS jsonb)) WHERE numero_version = 1"
        ),
        {"valor": str(PALABRAS_MINIMAS_ARTICULO)},
    )


def downgrade() -> None:
    _exigir_version_1_libre()
    op.execute(
        "UPDATE configuracion SET parametros = parametros - 'palabras_minimas_articulo'"
        " WHERE numero_version = 1"
    )
