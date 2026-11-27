"""T28: tablas del checkpointer de LangGraph en PostgreSQL.

El grafo de la orquestación guarda su estado por solicitud (``thread_id`` = id de la
solicitud) en las tablas de ``langgraph-checkpoint-postgres``: ``checkpoints``,
``checkpoint_blobs``, ``checkpoint_writes`` y ``checkpoint_migrations``. Se crean aquí,
con la propia ``setup()`` de la biblioteca (versión fijada en ``restricciones-corpus.txt``),
para que el esquema solo cambie por Alembic; la aplicación nunca llama a ``setup()``.

Algunos índices se crean con ``CREATE INDEX CONCURRENTLY``, que no admite transacción:
por eso se ejecuta en un bloque con confirmación automática. El estado guardado solo
tiene identificadores, tipo, agente y nombres de comprobaciones, nunca texto del borrador
(4.6). Revisión: 0021. Anterior: 0020.
"""

from collections.abc import Sequence

from alembic import op
from langgraph.checkpoint.postgres import PostgresSaver

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = ("checkpoint_writes", "checkpoint_blobs", "checkpoints", "checkpoint_migrations")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        conexion = op.get_bind().connection.driver_connection
        PostgresSaver(conexion).setup()  # type: ignore[arg-type]


def downgrade() -> None:
    for tabla in TABLAS:
        op.execute(f"DROP TABLE IF EXISTS {tabla}")
