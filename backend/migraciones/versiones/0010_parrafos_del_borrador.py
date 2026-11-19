"""T11: párrafos extraídos de cada versión del borrador.

* ``version_borrador.parrafos``: lista de párrafos con identificador estable dentro de la
  versión (``p1``, ``p2``...), texto, estilo y origen (cuerpo o tabla). Es el texto que se
  sirve como alcance; el archivo original nunca sale del servidor (RNF-10).
* ``version_borrador.palabras``: total de palabras del texto extraído.

Las versiones anteriores a esta migración no existen fuera de las pruebas (la carga llega
en T11); quedan con una lista vacía.

Revisión: 0010
Anterior: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "version_borrador",
        sa.Column(
            "parrafos",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Párrafos extraídos con identificador estable (p1, p2...), texto, estilo"
            " y origen (cuerpo o tabla).",
        ),
    )
    op.add_column(
        "version_borrador",
        sa.Column(
            "palabras",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Palabras del texto extraído.",
        ),
    )
    op.create_check_constraint(
        op.f("ck_version_borrador_palabras_no_negativas"), "version_borrador", "palabras >= 0"
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_version_borrador_palabras_no_negativas"), "version_borrador", type_="check"
    )
    op.drop_column("version_borrador", "palabras")
    op.drop_column("version_borrador", "parrafos")
