"""T04: lista cerrada de normas de citación (D-12, confirmada el 6 de noviembre de 2026).

La versión 1 de la configuración pasa de ``["ieee", "apa7"]`` a
``["ieee", "apa7", "vancouver"]``, con ``ieee`` por defecto. Igual que 0006, solo se
aplica si la versión 1 no está congelada y ninguna solicitud la usa.

El descenso se detiene si algún caso usa ``vancouver``: quitar la norma dejaría ese caso
con un valor fuera de la lista.

Revisión: 0007
Anterior: 0006
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NORMAS = ["ieee", "apa7", "vancouver"]
NORMAS_0006 = ["ieee", "apa7"]


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


def _poner_normas(normas: list[str]) -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE configuracion SET parametros = jsonb_set(parametros, '{normas_citacion}',"
            " CAST(:normas AS jsonb)) WHERE numero_version = 1"
        ),
        {"normas": json.dumps(normas)},
    )


def upgrade() -> None:
    _exigir_version_1_libre()
    _poner_normas(NORMAS)


def downgrade() -> None:
    _exigir_version_1_libre()
    en_uso = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM caso WHERE norma_citacion = 'vancouver'"))
        .scalar_one()
    )
    if en_uso:
        raise RuntimeError(f"{en_uso} casos usan la norma vancouver; no se puede quitar.")
    _poner_normas(NORMAS_0006)
