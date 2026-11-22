"""T15: importación de referencias del artículo O1 (RF-20, RN-19).

* ``importacion_referencias``: una por importación, con su origen, estado y avance.
* ``referencia_importada``: una por referencia y colección (única por clave), con su
  estado (incluida, pendiente de PDF, excluida o no comprobable) y motivo. Solo la entrada
  bibliográfica: el artículo O1 no se guarda (RN-19).
* ``motivo_exclusion_corpus``: ``no_localizada`` y ``sin_doi`` para las referencias.

Revisión: 0011
Anterior: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MOTIVOS_ANTERIORES = (
    "no_es_pdf",
    "pdf_ilegible",
    "pdf_cifrado",
    "excede_tamano",
    "excede_paginas",
    "sin_capa_de_texto",
    "duplicado",
    "sin_acceso_abierto",
)
MOTIVOS = (*MOTIVOS_ANTERIORES, "no_localizada", "sin_doi", "doi_invalido")
RESTRICCION_MOTIVO = "ck_exclusion_corpus_motivo_exclusion_corpus"


def _enumeracion(nombre: str, *valores: str) -> sa.Enum:
    return sa.Enum(*valores, name=nombre, native_enum=False, create_constraint=True, length=40)


def _lista(valores: Sequence[str]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _momento(nombre: str, comentario: str, *, nulo: bool = False) -> sa.Column:
    return sa.Column(
        nombre,
        sa.DateTime(timezone=True),
        server_default=None if nulo else sa.text("now()"),
        nullable=nulo,
        comment=comentario,
    )


def _id() -> sa.Column:
    return sa.Column(
        "id",
        sa.UUID(),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
        comment="Identificador interno (UUID).",
    )


def upgrade() -> None:
    op.drop_constraint(op.f(RESTRICCION_MOTIVO), "exclusion_corpus", type_="check")
    op.create_check_constraint(
        op.f(RESTRICCION_MOTIVO), "exclusion_corpus", f"motivo IN ({_lista(MOTIVOS)})"
    )

    op.create_table(
        "importacion_referencias",
        _id(),
        sa.Column(
            "coleccion_id", sa.UUID(), nullable=False, comment="Colección científica del tema."
        ),
        sa.Column(
            "origen",
            _enumeracion("origen_importacion", "pdf", "docx", "doi"),
            nullable=False,
            comment="pdf o docx (artículo O1, que no se guarda) o doi (lista de DOI).",
        ),
        sa.Column(
            "estado",
            _enumeracion(
                "estado_importacion",
                "en_cola",
                "en_proceso",
                "terminada",
                "interrumpida",
                "fallida",
            ),
            server_default="en_cola",
            nullable=False,
            comment="Avance del proceso en segundo plano.",
        ),
        sa.Column(
            "total",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Referencias extraídas.",
        ),
        sa.Column(
            "procesadas",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Referencias ya resueltas.",
        ),
        sa.Column(
            "error",
            sa.String(length=60),
            nullable=True,
            comment="Código del error si la importación falló.",
        ),
        sa.Column("creada_por_id", sa.UUID(), nullable=True, comment="Investigador que la pidió."),
        _momento("creada_en", "Fecha y hora de la solicitud."),
        _momento("iniciada_en", "Inicio del proceso.", nulo=True),
        _momento("terminada_en", "Fin del proceso.", nulo=True),
        sa.CheckConstraint(
            "procesadas >= 0 AND total >= 0 AND procesadas <= total",
            name=op.f("ck_importacion_referencias_avance_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["coleccion_id"],
            ["coleccion.id"],
            name=op.f("fk_importacion_referencias_coleccion_id_coleccion"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["creada_por_id"],
            ["cuenta.id"],
            name=op.f("fk_importacion_referencias_creada_por_id_cuenta"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_importacion_referencias")),
        comment="Importación de las referencias de un artículo O1 o de una lista de DOI"
        " (RF-20, T15).",
    )
    op.create_index(
        op.f("ix_importacion_referencias_coleccion_id"), "importacion_referencias", ["coleccion_id"]
    )

    op.create_table(
        "referencia_importada",
        _id(),
        sa.Column(
            "coleccion_id", sa.UUID(), nullable=False, comment="Colección científica del tema."
        ),
        sa.Column(
            "importacion_id",
            sa.UUID(),
            nullable=False,
            comment="Última importación que la trató.",
        ),
        sa.Column(
            "clave",
            sa.String(length=300),
            nullable=False,
            comment="doi:<DOI normalizado> o texto:<huella SHA-256 del texto normalizado>;"
            " única por colección (idempotencia).",
        ),
        sa.Column(
            "texto",
            sa.Text(),
            nullable=False,
            comment="Entrada bibliográfica tal como la extrajo GROBID.",
        ),
        sa.Column(
            "doi",
            sa.String(length=255),
            nullable=True,
            comment="DOI normalizado, si se conoce.",
        ),
        sa.Column("titulo", sa.Text(), nullable=True, comment="Título de la obra."),
        sa.Column(
            "autores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
            comment="Apellidos de los autores de la obra (metadato bibliográfico).",
        ),
        sa.Column("anio", sa.Integer(), nullable=True, comment="Año de publicación."),
        sa.Column(
            "estado",
            _enumeracion(
                "estado_referencia", "incluida", "pendiente_pdf", "excluida", "no_comprobable"
            ),
            nullable=False,
            comment="incluida, pendiente_pdf, excluida o no_comprobable.",
        ),
        sa.Column(
            "motivo",
            sa.String(length=60),
            nullable=True,
            comment="Motivo del estado si no está incluida.",
        ),
        sa.Column(
            "estado_oa",
            sa.String(length=20),
            nullable=True,
            comment="Estado de acceso abierto según Unpaywall.",
        ),
        sa.Column(
            "url_acceso_abierto",
            sa.Text(),
            nullable=True,
            comment="Página de acceso abierto (para bajar el PDF a mano).",
        ),
        sa.Column("url_pdf", sa.Text(), nullable=True, comment="Enlace directo al PDF, si lo hay."),
        sa.Column("licencia", sa.String(length=80), nullable=True, comment="Licencia de uso."),
        sa.Column(
            "documento_id",
            sa.UUID(),
            nullable=True,
            comment="Documento indexado, si está incluida.",
        ),
        _momento("actualizada_en", "Último cambio de estado."),
        sa.CheckConstraint(
            "(estado = 'incluida') = (documento_id IS NOT NULL)",
            name=op.f("ck_referencia_importada_incluida_con_documento"),
        ),
        sa.CheckConstraint(
            "(estado = 'incluida') OR motivo IS NOT NULL",
            name=op.f("ck_referencia_importada_motivo_si_no_incluida"),
        ),
        sa.ForeignKeyConstraint(
            ["coleccion_id"],
            ["coleccion.id"],
            name=op.f("fk_referencia_importada_coleccion_id_coleccion"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["documento_id"],
            ["documento.id"],
            name=op.f("fk_referencia_importada_documento_id_documento"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["importacion_id"],
            ["importacion_referencias.id"],
            name=op.f("fk_referencia_importada_importacion_id_importacion_referencias"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referencia_importada")),
        sa.UniqueConstraint(
            "coleccion_id", "clave", name=op.f("uq_referencia_importada_coleccion_id_clave")
        ),
        comment="Referencia de un artículo O1 en la colección de su tema, con su estado"
        " (RF-20). Solo la entrada bibliográfica: nunca texto del artículo (RN-19).",
    )
    for columna in ("coleccion_id", "importacion_id", "doi"):
        op.create_index(
            op.f(f"ix_referencia_importada_{columna}"), "referencia_importada", [columna]
        )


def downgrade() -> None:
    op.drop_table("referencia_importada")
    op.drop_table("importacion_referencias")
    op.execute(
        "DELETE FROM exclusion_corpus WHERE motivo IN ('no_localizada', 'sin_doi', 'doi_invalido')"
    )
    op.drop_constraint(op.f(RESTRICCION_MOTIVO), "exclusion_corpus", type_="check")
    op.create_check_constraint(
        op.f(RESTRICCION_MOTIVO), "exclusion_corpus", f"motivo IN ({_lista(MOTIVOS_ANTERIORES)})"
    )
