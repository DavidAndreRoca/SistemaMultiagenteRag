"""T07: registro de cambios de norma de citación por caso.

Revisión: 0004
Anterior: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cambio_norma",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column("caso_id", sa.UUID(), nullable=False, comment="Caso afectado."),
        sa.Column(
            "norma_anterior",
            sa.String(length=20),
            nullable=False,
            comment="Norma antes del cambio.",
        ),
        sa.Column(
            "norma_nueva", sa.String(length=20), nullable=False, comment="Norma después del cambio."
        ),
        sa.Column(
            "cuenta_id",
            sa.UUID(),
            nullable=False,
            comment="Cuenta del investigador que hizo el cambio.",
        ),
        sa.Column(
            "cambiado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora del cambio.",
        ),
        sa.ForeignKeyConstraint(
            ["caso_id"], ["caso.id"], name=op.f("fk_cambio_norma_caso_id_caso"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["cuenta_id"],
            ["cuenta.id"],
            name=op.f("fk_cambio_norma_cuenta_id_cuenta"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cambio_norma")),
        comment="Registro de cada cambio de norma de citación de un caso (T07).",
    )
    op.create_index(op.f("ix_cambio_norma_caso_id"), "cambio_norma", ["caso_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cambio_norma_caso_id"), table_name="cambio_norma")
    op.drop_table("cambio_norma")
