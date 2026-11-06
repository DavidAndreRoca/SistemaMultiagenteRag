"""T06: tabla de sesiones de navegador.

Revisión: 0003
Anterior: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sesion",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column("cuenta_id", sa.UUID(), nullable=False, comment="Cuenta dueña."),
        sa.Column(
            "huella_token",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 del token de la cookie; el token no se guarda.",
        ),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Inicio de la sesión.",
        ),
        sa.Column(
            "ultima_actividad_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Última petición autenticada.",
        ),
        sa.Column(
            "expira_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Expiración absoluta.",
        ),
        sa.Column(
            "cerrada_en",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Cierre o invalidación.",
        ),
        sa.Column(
            "motivo_cierre",
            sa.String(length=40),
            nullable=True,
            comment="cierre, inactividad, expiracion, limite o contrasena.",
        ),
        sa.ForeignKeyConstraint(
            ["cuenta_id"],
            ["cuenta.id"],
            name=op.f("fk_sesion_cuenta_id_cuenta"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sesion")),
        sa.UniqueConstraint("huella_token", name=op.f("uq_sesion_huella_token")),
        comment="Sesión de navegador (8 h absolutas, 60 min de inactividad, dos por cuenta).",
    )
    op.create_index(
        "ix_sesion_activas_por_cuenta",
        "sesion",
        ["cuenta_id", "creada_en"],
        unique=False,
        postgresql_where=sa.text("cerrada_en IS NULL"),
    )
    op.create_index(op.f("ix_sesion_cuenta_id"), "sesion", ["cuenta_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sesion_cuenta_id"), table_name="sesion")
    op.drop_index(
        "ix_sesion_activas_por_cuenta",
        table_name="sesion",
        postgresql_where=sa.text("cerrada_en IS NULL"),
    )
    op.drop_table("sesion")
