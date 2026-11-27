"""T32: aporte de fuentes a la colección personal (RF-13, CU-12, CP-14 a CP-17).

* ``fuente_aportada`` registra qué pasó con la indexación (indexada, ya indexada o no
  indexada, con su motivo), la cita propuesta en la norma del caso y la nueva búsqueda de
  evidencia lanzada tras indexar.
* Agrega ``versiones_instrucciones.coherencia = v1`` a la configuración vigente, igual que
  0022: si la vigente sigue libre la modifica; si no, crea una versión nueva y vigente.

Revisión: 0023. Anterior: 0022.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "fuente_aportada"
INDEXACION = ("indexada", "ya_indexada", "no_indexada")
FK_RECUPERACION = "fk_fuente_aportada_solicitud_recuperacion_id_caso_id_solicitud"

CLAVE = "coherencia"
VERSION = json.dumps({CLAVE: "v1"})
COMENTARIO = "T32: versión de la instrucción de coherencia del aporte (migración 0023)"
_AGREGAR = (
    "parametros || jsonb_build_object('versiones_instrucciones',"
    " coalesce(parametros -> 'versiones_instrucciones', '{}'::jsonb) || CAST(:version AS jsonb))"
)


def _vigente_libre() -> bool:
    fila = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT c.congelada,"
                " (SELECT count(*) FROM solicitud s WHERE s.configuracion_id = c.id)"
                " FROM configuracion c WHERE c.vigente"
            )
        )
        .one_or_none()
    )
    if fila is None:
        raise RuntimeError("No hay una versión vigente de la configuración.")
    congelada, solicitudes = fila
    return not congelada and solicitudes == 0


def _agregar_instruccion() -> None:
    conexion = op.get_bind()
    if _vigente_libre():
        conexion.execute(
            sa.text(f"UPDATE configuracion SET parametros = {_AGREGAR} WHERE vigente"),
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


def _quitar_instruccion() -> None:
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
            raise RuntimeError("La versión creada por 0023 ya la usan solicitudes.")
        conexion.execute(sa.text("DELETE FROM configuracion WHERE id = :id"), {"id": creada[0]})
        conexion.execute(
            sa.text(
                "UPDATE configuracion SET vigente = true WHERE numero_version ="
                " (SELECT max(numero_version) FROM configuracion)"
            )
        )
        return
    if not _vigente_libre():
        raise RuntimeError("La versión vigente está congelada o la usan solicitudes.")
    conexion.execute(
        sa.text(
            "UPDATE configuracion SET parametros = parametros"
            " || jsonb_build_object('versiones_instrucciones',"
            " (parametros -> 'versiones_instrucciones') - :clave)"
            " WHERE vigente"
        ),
        {"clave": CLAVE},
    )


def upgrade() -> None:
    op.add_column(
        TABLA,
        sa.Column(
            "indexacion",
            sa.String(length=40),
            server_default="no_indexada",
            nullable=False,
            comment="indexada, ya_indexada (no se duplica, CP-17) o no_indexada.",
        ),
    )
    op.create_check_constraint(
        op.f("ck_fuente_aportada_indexacion_aporte"),
        TABLA,
        "indexacion IN (" + ", ".join(f"'{v}'" for v in INDEXACION) + ")",
    )
    op.add_column(
        TABLA,
        sa.Column(
            "motivo_indexacion",
            sa.String(length=80),
            nullable=True,
            comment="Por qué no se indexó: existencia no confirmada, sin texto, PDF excluido o"
            " servicio no disponible.",
        ),
    )
    op.add_column(
        TABLA,
        sa.Column(
            "cita_propuesta",
            sa.Text(),
            nullable=True,
            comment="Cita en la norma del caso, del registro del DOI o del formateador CSL"
            " (RN-17: nunca de un modelo).",
        ),
    )
    op.add_column(
        TABLA,
        sa.Column(
            "solicitud_recuperacion_id",
            sa.UUID(),
            nullable=True,
            comment="Nueva búsqueda de evidencia con la misma consulta, lanzada tras indexar.",
        ),
    )
    op.create_foreign_key(
        op.f(FK_RECUPERACION),
        TABLA,
        "solicitud",
        ["solicitud_recuperacion_id", "caso_id"],
        ["id", "caso_id"],
    )
    _agregar_instruccion()


def downgrade() -> None:
    _quitar_instruccion()
    op.drop_constraint(op.f(FK_RECUPERACION), TABLA, type_="foreignkey")
    op.drop_column(TABLA, "solicitud_recuperacion_id")
    op.drop_column(TABLA, "cita_propuesta")
    op.drop_column(TABLA, "motivo_indexacion")
    op.drop_constraint(op.f("ck_fuente_aportada_indexacion_aporte"), TABLA, type_="check")
    op.drop_column(TABLA, "indexacion")
