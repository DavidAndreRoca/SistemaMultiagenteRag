"""Documento y fragmento del corpus (Fase 1, 18.2). Los índices HNSW y GIN se crean en T10."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped

from app.bd.base import Base, clave_primaria, enumeracion, momento
from app.bd.enumeraciones import (
    EstadoAccesoAbierto,
    EstadoDocumento,
    MotivoExclusionCorpus,
    ObjetoExclusion,
    OrigenDocumento,
    SeccionNormalizada,
)
from app.bd.modelos._columnas import col

DIMENSION_EMBEDDINGS = 1024


class Documento(Base):
    __tablename__ = "documento"
    __table_args__ = (
        UniqueConstraint("coleccion_id", "huella_sha256"),
        CheckConstraint("huella_sha256 ~ '^[0-9a-f]{64}$'", name="huella_hex"),
        CheckConstraint("anio IS NULL OR anio BETWEEN 1500 AND 2100", name="anio_razonable"),
        CheckConstraint(
            "isbn IS NULL OR isbn ~ '^(97[89][0-9]{10}|[0-9]{9}[0-9X])$'", name="isbn_normalizado"
        ),
        CheckConstraint(
            "huella_archivo IS NULL OR huella_archivo ~ '^[0-9a-f]{64}$'",
            name="huella_archivo_hex",
        ),
        CheckConstraint(
            "confirmado_en IS NULL OR estado <> 'activo'", name="confirmacion_solo_si_incompleto"
        ),
        Index("ix_documento_coleccion_id_huella_archivo", "coleccion_id", "huella_archivo"),
        {
            "comment": "Documento indexado en una colección, con metadatos"
            " bibliográficos (Fase 1, 18.2)."
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    coleccion_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("coleccion.id", ondelete="RESTRICT"),
        index=True,
        comentario="Colección a la que pertenece.",
    )
    titulo: Mapped[str | None] = col(Text, nullable=True, comentario="Título de la obra.")
    autores: Mapped[list[Any]] = col(
        JSONB,
        default=list,
        server_default="[]",
        comentario="Autores de la obra publicada (metadato bibliográfico, no participantes).",
    )
    anio: Mapped[int | None] = col(Integer, nullable=True, comentario="Año de publicación.")
    doi: Mapped[str | None] = col(
        String(255), nullable=True, index=True, comentario="DOI normalizado."
    )
    revista_editorial: Mapped[str | None] = col(
        Text, nullable=True, comentario="Revista (artículos) o editorial (libros)."
    )
    isbn: Mapped[str | None] = col(
        String(13), nullable=True, comentario="ISBN-10 o ISBN-13 sin guiones (libros, 18.9)."
    )
    idioma: Mapped[str | None] = col(String(8), nullable=True, comentario="Idioma (ISO 639-1).")
    licencia: Mapped[str | None] = col(String(80), nullable=True, comentario="Licencia de uso.")
    url_acceso_abierto: Mapped[str | None] = col(
        Text, nullable=True, comentario="Mejor ubicación de acceso abierto."
    )
    estado_oa: Mapped[EstadoAccesoAbierto] = col(
        enumeracion(EstadoAccesoAbierto, "estado_oa"),
        default=EstadoAccesoAbierto.DESCONOCIDO,
        server_default=EstadoAccesoAbierto.DESCONOCIDO.value,
        comentario="Estado de acceso abierto según Unpaywall.",
        alimenta="Comprobación 5 de la verificación (acceso abierto, RNF-08)",
    )
    ruta_archivo: Mapped[str | None] = col(
        Text,
        nullable=True,
        comentario="Ruta interna con nombre aleatorio, fuera de la carpeta pública; nula si se"
        " indexó solo el resumen de Crossref u OpenAlex (RF-13).",
    )
    huella_sha256: Mapped[str] = col(
        String(64),
        comentario="Huella SHA-256 del texto normalizado, para deduplicar (18.9).",
    )
    estado: Mapped[EstadoDocumento] = col(
        enumeracion(EstadoDocumento, "estado_documento"),
        default=EstadoDocumento.ACTIVO,
        server_default=EstadoDocumento.ACTIVO.value,
        comentario="activo, retirado o incompleto (un retirado deja de recuperarse, 18.9).",
    )
    motivo_estado: Mapped[str | None] = col(
        Text, nullable=True, comentario="Motivo si está incompleto o retirado."
    )
    origen: Mapped[OrigenDocumento] = col(
        enumeracion(OrigenDocumento, "origen_documento"),
        comentario="ingesta, importacion_o1 o aporte.",
    )
    num_paginas: Mapped[int | None] = col(Integer, nullable=True, comentario="Páginas del PDF.")
    huella_archivo: Mapped[str | None] = col(
        String(64),
        nullable=True,
        comentario="Huella SHA-256 del archivo subido: la ingesta es idempotente (T10).",
    )
    archivo_original: Mapped[str | None] = col(
        Text, nullable=True, comentario="Nombre con que se subió el archivo, para el investigador."
    )
    indexado_por_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="SET NULL"),
        nullable=True,
        comentario="Cuenta del investigador que lo indexó (Fase 1, 19.1: quién y cuándo).",
    )
    confirmado_en: Mapped[datetime | None] = momento(
        "Si está incompleto: cuándo el investigador confirmó indexarlo (18.3).", nulo=True
    )
    confirmado_por_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="SET NULL"),
        nullable=True,
        comentario="Cuenta del investigador que confirmó el documento incompleto.",
    )
    modelo_embeddings: Mapped[str | None] = col(
        String(120), nullable=True, comentario="Modelo de embeddings de sus vectores (RNF-21)."
    )
    revision_embeddings: Mapped[str | None] = col(
        String(64),
        nullable=True,
        comentario="Revisión exacta del modelo de embeddings; si cambia, se reindexa (18.5).",
    )
    creado_en: Mapped[datetime] = momento("Fecha y hora de indexación.")
    retirado_en: Mapped[datetime | None] = momento("Fecha y hora de retiro.", nulo=True)


class Fragmento(Base):
    __tablename__ = "fragmento"
    __table_args__ = (
        UniqueConstraint("documento_id", "orden"),
        CheckConstraint(
            "pagina_inicio IS NULL OR pagina_fin IS NULL OR pagina_inicio <= pagina_fin",
            name="paginas_ordenadas",
        ),
        # Índices de la recuperación (T10; Fase 1, 18.2): HNSW con distancia coseno sobre el
        # vector, GIN sobre el vector léxico y compuesto por colección para el filtro.
        Index(
            "ix_fragmento_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_fragmento_texto_lexico_gin", "texto_lexico", postgresql_using="gin"),
        Index("ix_fragmento_coleccion_id_documento_id", "coleccion_id", "documento_id"),
        {"comment": "Fragmento IMRaD de un documento, con vector denso y texto léxico."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    documento_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("documento.id", ondelete="CASCADE"),
        index=True,
        comentario="Documento de origen.",
    )
    coleccion_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("coleccion.id", ondelete="RESTRICT"),
        index=True,
        comentario="Colección (copiada del documento para filtrar la recuperación).",
    )
    orden: Mapped[int] = col(Integer, comentario="Posición del fragmento en el documento.")
    texto: Mapped[str] = col(Text, comentario="Texto limpio del fragmento.")
    seccion_normalizada: Mapped[SeccionNormalizada] = col(
        enumeracion(SeccionNormalizada, "seccion_normalizada"), comentario="Sección IMRaD."
    )
    seccion_original: Mapped[str | None] = col(
        Text, nullable=True, comentario="Título de la sección tal como aparece en el PDF."
    )
    pagina_inicio: Mapped[int | None] = col(Integer, nullable=True, comentario="Página inicial.")
    pagina_fin: Mapped[int | None] = col(Integer, nullable=True, comentario="Página final.")
    tokens: Mapped[int] = col(Integer, comentario="Número de tokens del fragmento.")
    embedding: Mapped[list[float] | None] = col(
        Vector(DIMENSION_EMBEDDINGS), nullable=True, comentario="Vector bge-m3 normalizado (1 024)."
    )
    texto_lexico: Mapped[str] = col(
        TSVECTOR,
        Computed("to_tsvector('simple'::regconfig, texto)", persisted=True),
        comentario="Vector léxico tsvector con configuración simple, generado desde el texto.",
    )
    creado_en: Mapped[datetime] = momento("Fecha y hora de creación.")


class ExclusionCorpus(Base):
    __tablename__ = "exclusion_corpus"
    __table_args__ = (
        CheckConstraint(
            "huella_archivo IS NULL OR huella_archivo ~ '^[0-9a-f]{64}$'",
            name="huella_archivo_hex",
        ),
        CheckConstraint(
            "(motivo = 'duplicado') = (duplicado_de_id IS NOT NULL)",
            name="duplicado_con_original",
        ),
        # Un mismo archivo se registra una sola vez por colección: la ingesta es idempotente.
        Index(
            "uq_exclusion_corpus_coleccion_id_huella_archivo",
            "coleccion_id",
            "huella_archivo",
            unique=True,
            postgresql_where=text("huella_archivo IS NOT NULL"),
        ),
        {
            "comment": "Archivo o referencia que no entró al corpus, con su motivo"
            " (RF-15, CP-21; Fase 1, 18.3 y 18.9)."
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    coleccion_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("coleccion.id", ondelete="RESTRICT"),
        index=True,
        comentario="Colección a la que se intentó agregar.",
    )
    objeto: Mapped[ObjetoExclusion] = col(
        enumeracion(ObjetoExclusion, "objeto_exclusion"),
        comentario="archivo (subido o de la ingesta) o referencia (importador del artículo O1).",
    )
    identificador: Mapped[str] = col(
        Text, comentario="Nombre del archivo, DOI o texto de la referencia."
    )
    huella_archivo: Mapped[str | None] = col(
        String(64), nullable=True, comentario="Huella SHA-256 del archivo, si lo hubo."
    )
    motivo: Mapped[MotivoExclusionCorpus] = col(
        enumeracion(MotivoExclusionCorpus, "motivo_exclusion_corpus"),
        comentario="Motivo de la exclusión.",
        alimenta="Informe del corpus por tema (RF-15)",
    )
    duplicado_de_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("documento.id", ondelete="CASCADE"),
        nullable=True,
        comentario="Documento ya indexado del que es duplicado (por texto o por DOI).",
    )
    registrado_por_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="SET NULL"),
        nullable=True,
        comentario="Cuenta del investigador que intentó agregarlo.",
    )
    registrada_en: Mapped[datetime] = momento("Fecha y hora del registro.")
