"""T10: índices de recuperación, registro de exclusiones y trazabilidad de la ingesta.

* Índices de ``fragmento`` (Fase 1, 18.2): HNSW con distancia coseno sobre el vector,
  GIN sobre el vector léxico y compuesto por colección y documento.
* Tabla ``exclusion_corpus``: archivos y referencias que no entraron al corpus, con su
  motivo (RF-15, CP-21). Un mismo archivo se registra una sola vez por colección.
* ``documento``: huella del archivo (ingesta idempotente), nombre original, quién lo
  indexó, confirmación de los incompletos (18.3) y modelo y revisión de sus vectores
  (18.5, RNF-21).

Revisión: 0009
Anterior: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MOTIVOS = (
    "no_es_pdf",
    "pdf_ilegible",
    "pdf_cifrado",
    "excede_tamano",
    "excede_paginas",
    "sin_capa_de_texto",
    "duplicado",
    "sin_acceso_abierto",
)


def upgrade() -> None:
    op.create_table(
        "exclusion_corpus",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "coleccion_id",
            sa.UUID(),
            nullable=False,
            comment="Colección a la que se intentó agregar.",
        ),
        sa.Column(
            "objeto",
            sa.Enum(
                "archivo",
                "referencia",
                name="objeto_exclusion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="archivo (subido o de la ingesta) o referencia (importador del artículo O1).",
        ),
        sa.Column(
            "identificador",
            sa.Text(),
            nullable=False,
            comment="Nombre del archivo, DOI o texto de la referencia.",
        ),
        sa.Column(
            "huella_archivo",
            sa.String(length=64),
            nullable=True,
            comment="Huella SHA-256 del archivo, si lo hubo.",
        ),
        sa.Column(
            "motivo",
            sa.Enum(
                *MOTIVOS,
                name="motivo_exclusion_corpus",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Motivo de la exclusión.",
        ),
        sa.Column(
            "duplicado_de_id",
            sa.UUID(),
            nullable=True,
            comment="Documento ya indexado del que es duplicado (por texto o por DOI).",
        ),
        sa.Column(
            "registrado_por_id",
            sa.UUID(),
            nullable=True,
            comment="Cuenta del investigador que intentó agregarlo.",
        ),
        sa.Column(
            "registrada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora del registro.",
        ),
        sa.CheckConstraint(
            "(motivo = 'duplicado') = (duplicado_de_id IS NOT NULL)",
            name=op.f("ck_exclusion_corpus_duplicado_con_original"),
        ),
        sa.CheckConstraint(
            "huella_archivo IS NULL OR huella_archivo ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_exclusion_corpus_huella_archivo_hex"),
        ),
        sa.ForeignKeyConstraint(
            ["coleccion_id"],
            ["coleccion.id"],
            name=op.f("fk_exclusion_corpus_coleccion_id_coleccion"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["duplicado_de_id"],
            ["documento.id"],
            name=op.f("fk_exclusion_corpus_duplicado_de_id_documento"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["registrado_por_id"],
            ["cuenta.id"],
            name=op.f("fk_exclusion_corpus_registrado_por_id_cuenta"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exclusion_corpus")),
        comment="Archivo o referencia que no entró al corpus, con su motivo"
        " (RF-15, CP-21; Fase 1, 18.3 y 18.9).",
    )
    op.create_index(op.f("ix_exclusion_corpus_coleccion_id"), "exclusion_corpus", ["coleccion_id"])
    op.create_index(
        "uq_exclusion_corpus_coleccion_id_huella_archivo",
        "exclusion_corpus",
        ["coleccion_id", "huella_archivo"],
        unique=True,
        postgresql_where=sa.text("huella_archivo IS NOT NULL"),
    )

    columnas = [
        sa.Column(
            "huella_archivo",
            sa.String(length=64),
            nullable=True,
            comment="Huella SHA-256 del archivo subido: la ingesta es idempotente (T10).",
        ),
        sa.Column(
            "archivo_original",
            sa.Text(),
            nullable=True,
            comment="Nombre con que se subió el archivo, para el investigador.",
        ),
        sa.Column(
            "indexado_por_id",
            sa.UUID(),
            nullable=True,
            comment="Cuenta del investigador que lo indexó (Fase 1, 19.1: quién y cuándo).",
        ),
        sa.Column(
            "confirmado_en",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Si está incompleto: cuándo el investigador confirmó indexarlo (18.3).",
        ),
        sa.Column(
            "confirmado_por_id",
            sa.UUID(),
            nullable=True,
            comment="Cuenta del investigador que confirmó el documento incompleto.",
        ),
        sa.Column(
            "modelo_embeddings",
            sa.String(length=120),
            nullable=True,
            comment="Modelo de embeddings de sus vectores (RNF-21).",
        ),
        sa.Column(
            "revision_embeddings",
            sa.String(length=64),
            nullable=True,
            comment="Revisión exacta del modelo de embeddings; si cambia, se reindexa (18.5).",
        ),
    ]
    for columna in columnas:
        op.add_column("documento", columna)
    op.create_check_constraint(
        op.f("ck_documento_huella_archivo_hex"),
        "documento",
        "huella_archivo IS NULL OR huella_archivo ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        op.f("ck_documento_confirmacion_solo_si_incompleto"),
        "documento",
        "confirmado_en IS NULL OR estado <> 'activo'",
    )
    op.create_index(
        "ix_documento_coleccion_id_huella_archivo", "documento", ["coleccion_id", "huella_archivo"]
    )
    op.create_foreign_key(
        op.f("fk_documento_indexado_por_id_cuenta"),
        "documento",
        "cuenta",
        ["indexado_por_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_documento_confirmado_por_id_cuenta"),
        "documento",
        "cuenta",
        ["confirmado_por_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_fragmento_coleccion_id_documento_id", "fragmento", ["coleccion_id", "documento_id"]
    )
    op.create_index(
        "ix_fragmento_embedding_hnsw",
        "fragmento",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_fragmento_texto_lexico_gin", "fragmento", ["texto_lexico"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_fragmento_texto_lexico_gin", table_name="fragmento")
    op.drop_index("ix_fragmento_embedding_hnsw", table_name="fragmento")
    op.drop_index("ix_fragmento_coleccion_id_documento_id", table_name="fragmento")

    op.drop_constraint(op.f("fk_documento_confirmado_por_id_cuenta"), "documento")
    op.drop_constraint(op.f("fk_documento_indexado_por_id_cuenta"), "documento")
    op.drop_index("ix_documento_coleccion_id_huella_archivo", table_name="documento")
    op.drop_constraint(op.f("ck_documento_confirmacion_solo_si_incompleto"), "documento")
    op.drop_constraint(op.f("ck_documento_huella_archivo_hex"), "documento")
    for nombre in (
        "revision_embeddings",
        "modelo_embeddings",
        "confirmado_por_id",
        "confirmado_en",
        "indexado_por_id",
        "archivo_original",
        "huella_archivo",
    ):
        op.drop_column("documento", nombre)

    op.drop_index("uq_exclusion_corpus_coleccion_id_huella_archivo", table_name="exclusion_corpus")
    op.drop_index(op.f("ix_exclusion_corpus_coleccion_id"), table_name="exclusion_corpus")
    op.drop_table("exclusion_corpus")
