"""T16: parámetros de la recuperación y versión de la instrucción de suficiencia.

Añade a la versión 1 de la configuración ``candidatos_reranking = 20`` y
``presupuesto_tokens_contexto = 2400`` (decisiones del equipo, T16-01, apartados 3 y 4) y
fija ``versiones_instrucciones.suficiencia = v1``. Igual que 0006 a 0012, solo se aplica
si la versión 1 no está congelada y ninguna solicitud la usa. Es una migración de datos.

Revisión: 0013
Anterior: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CANDIDATOS_RERANKING = 20
PRESUPUESTO_TOKENS_CONTEXTO = 2400


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
            " || jsonb_build_object('candidatos_reranking', CAST(:candidatos AS integer),"
            " 'presupuesto_tokens_contexto', CAST(:presupuesto AS integer))"
            " || jsonb_build_object('versiones_instrucciones',"
            " coalesce(parametros -> 'versiones_instrucciones', '{}'::jsonb)"
            " || '{\"suficiencia\": \"v1\"}'::jsonb)"
            " WHERE numero_version = 1"
        ),
        {"candidatos": CANDIDATOS_RERANKING, "presupuesto": PRESUPUESTO_TOKENS_CONTEXTO},
    )


def downgrade() -> None:
    _exigir_version_1_libre()
    op.execute(
        "UPDATE configuracion SET parametros = (parametros - 'candidatos_reranking'"
        " - 'presupuesto_tokens_contexto')"
        " || jsonb_build_object('versiones_instrucciones',"
        " (parametros -> 'versiones_instrucciones') - 'suficiencia')"
        " WHERE numero_version = 1"
    )
