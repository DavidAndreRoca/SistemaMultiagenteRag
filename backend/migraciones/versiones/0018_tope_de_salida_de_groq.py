"""T27: sube el tope de salida del modelo de Groq de 2048 a 4096 tokens.

gpt-oss-120b razona antes de responder y esos tokens cuentan en la salida: en una propuesta
de redacción (D3) gastó unos 1800, y con 2048 la respuesta se cortaba y Groq la rechazaba
(``json_validate_failed``). El limitador ajusta cada reserva al uso real, así que el tope
mayor no frena a los demás agentes.

Igual que 0017: modifica la configuración vigente si sigue libre (no congelada y sin
solicitudes); si no, crea una versión nueva y vigente, copia de la vigente con el cambio
(RNF-21). Es una migración de datos. Revisión: 0018. Anterior: 0017.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TOPE, TOPE_ANTERIOR = 4096, 2048
COMENTARIO = "T27: tope de salida de Groq de 4096 tokens (migración 0018)"


def _con_tope(valor: int) -> str:
    """``parametros`` con ``max_tokens_salida`` de Groq fijado en ``valor``."""
    return (
        "parametros || CASE WHEN jsonb_typeof(parametros -> 'modelos') = 'array' THEN"
        " jsonb_build_object('modelos', (SELECT jsonb_agg(CASE WHEN m ->> 'proveedor' = 'groq'"
        f" THEN m || jsonb_build_object('max_tokens_salida', {valor}) ELSE m END"
        " ORDER BY orden) FROM jsonb_array_elements(parametros -> 'modelos')"
        " WITH ORDINALITY AS t(m, orden))) ELSE '{}'::jsonb END"
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


def upgrade() -> None:
    conexion = op.get_bind()
    if _vigente_libre():
        conexion.execute(
            sa.text(f"UPDATE configuracion SET parametros = {_con_tope(TOPE)} WHERE vigente")
        )
        return
    # Tres pasos, para respetar en todo momento el índice de una sola versión vigente.
    nueva = conexion.execute(
        sa.text(
            "INSERT INTO configuracion (id, numero_version, parametros, comentario, vigente,"
            " congelada, creada_en)"
            " SELECT gen_random_uuid(), (SELECT max(numero_version) + 1 FROM configuracion),"
            f" {_con_tope(TOPE)}, :comentario, false, false, now()"
            " FROM configuracion WHERE vigente RETURNING id"
        ),
        {"comentario": COMENTARIO},
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
            raise RuntimeError("La versión creada por 0018 ya la usan solicitudes.")
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
        sa.text(f"UPDATE configuracion SET parametros = {_con_tope(TOPE_ANTERIOR)} WHERE vigente")
    )
