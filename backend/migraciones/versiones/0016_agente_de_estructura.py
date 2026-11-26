"""T23: versión de la instrucción del agente de estructura (D1).

Agrega ``versiones_instrucciones.estructura = v1`` a la configuración:

* si la versión 1 sigue libre (no congelada y sin solicitudes), la modifica, igual que 0006
  a 0015;
* si no (por ejemplo, una base de desarrollo con solicitudes de la demostración), crea una
  versión nueva y vigente, copia de la vigente con el agregado. Las solicitudes anteriores
  conservan su versión (RNF-21).

Es una migración de datos. Revisión: 0016. Anterior: 0015.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSION = json.dumps({"estructura": "v1"})
COMENTARIO = "T23: versión de la instrucción del agente de estructura (migración 0016)"
_AGREGAR = (
    "parametros || jsonb_build_object('versiones_instrucciones',"
    " coalesce(parametros -> 'versiones_instrucciones', '{}'::jsonb) || CAST(:version AS jsonb))"
)


def _version_1_libre() -> bool:
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
    return not congelada and solicitudes == 0


def upgrade() -> None:
    conexion = op.get_bind()
    if _version_1_libre():
        conexion.execute(
            sa.text(f"UPDATE configuracion SET parametros = {_AGREGAR} WHERE numero_version = 1"),
            {"version": VERSION},
        )
        return
    # Tres pasos, para respetar en todo momento el índice de una sola versión vigente.
    nueva = conexion.execute(
        sa.text(
            "INSERT INTO configuracion (id, numero_version, parametros, comentario, vigente,"
            " congelada, creada_en)"
            " SELECT gen_random_uuid(), (SELECT max(numero_version) + 1 FROM configuracion),"
            f" {_AGREGAR}, :comentario, false, false, now()"
            " FROM configuracion WHERE vigente RETURNING id"
        ),
        {"version": VERSION, "comentario": COMENTARIO},
    ).scalar_one()
    conexion.execute(sa.text("UPDATE configuracion SET vigente = false WHERE vigente"))
    conexion.execute(
        sa.text("UPDATE configuracion SET vigente = true WHERE id = :id"), {"id": nueva}
    )


def downgrade() -> None:
    conexion = op.get_bind()
    creada = conexion.execute(
        sa.text(
            "SELECT c.id, (SELECT count(*) FROM solicitud s WHERE s.configuracion_id = c.id)"
            " FROM configuracion c WHERE c.comentario = :comentario"
        ),
        {"comentario": COMENTARIO},
    ).one_or_none()
    if creada is not None:
        if creada[1]:
            raise RuntimeError("La versión creada por 0016 ya la usan solicitudes.")
        conexion.execute(sa.text("DELETE FROM configuracion WHERE id = :id"), {"id": creada[0]})
        conexion.execute(
            sa.text(
                "UPDATE configuracion SET vigente = true WHERE numero_version ="
                " (SELECT max(numero_version) FROM configuracion)"
            )
        )
        return
    if not _version_1_libre():
        raise RuntimeError("La versión 1 está congelada o la usan solicitudes.")
    op.execute(
        "UPDATE configuracion SET parametros = parametros"
        " || jsonb_build_object('versiones_instrucciones',"
        " (parametros -> 'versiones_instrucciones') - 'estructura')"
        " WHERE numero_version = 1"
    )
