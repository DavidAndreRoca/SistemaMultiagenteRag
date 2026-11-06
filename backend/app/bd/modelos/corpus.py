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
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped

from app.bd.base import Base, clave_primaria, enumeracion, momento
from app.bd.enumeraciones import (
    EstadoAccesoAbierto,
    EstadoDocumento,
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
