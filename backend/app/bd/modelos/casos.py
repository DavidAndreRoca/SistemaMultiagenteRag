"""Caso, colección y registro de cambios de norma de citación."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from app.bd.base import Base, clave_primaria, enumeracion, momento
from app.bd.enumeraciones import EstadoCaso, TipoAutoria, TipoColeccion
from app.bd.modelos._columnas import col


class Coleccion(Base):
    __tablename__ = "coleccion"
    __table_args__ = (
        CheckConstraint(
            "(tipo = 'cientifica') = (tema IS NOT NULL)", name="tema_solo_en_cientifica"
        ),
        CheckConstraint(
            "(tipo = 'personal') = (caso_id IS NOT NULL)", name="caso_solo_en_personal"
        ),
        CheckConstraint(
            "n_incluidas >= 0 AND n_excluidas >= 0 AND n_pendientes >= 0", name="conteos_positivos"
        ),
        Index(
            "uq_coleccion_tema_cientifica",
            "tema",
            unique=True,
            postgresql_where=text("tipo = 'cientifica'"),
        ),
        Index(
            "uq_coleccion_caso_personal",
            "caso_id",
            unique=True,
            postgresql_where=text("tipo = 'personal'"),
        ),
        Index(
            "uq_coleccion_unica_guias", "tipo", unique=True, postgresql_where=text("tipo = 'guias'")
        ),
        {
            "comment": "Colección del corpus: guías (una), científica (una por tema)"
            " o personal (una por caso)."
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    tipo: Mapped[TipoColeccion] = col(
        enumeracion(TipoColeccion, "tipo_coleccion"), comentario="guias, cientifica o personal."
    )
    tema: Mapped[str | None] = col(
        String(80), nullable=True, comentario="Código del tema (solo en la colección científica)."
    )
    caso_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("caso.id", ondelete="CASCADE", use_alter=True),
        nullable=True,
        index=True,
        comentario="Caso dueño (solo en la colección personal).",
    )
    n_incluidas: Mapped[int] = col(
        Integer,
        default=0,
        server_default="0",
        comentario="Documentos incluidos.",
        alimenta="Informe del corpus por tema (RF-15)",
    )
    n_excluidas: Mapped[int] = col(
        Integer,
        default=0,
        server_default="0",
        comentario="Referencias excluidas con motivo.",
        alimenta="Informe del corpus por tema (RF-15)",
    )
    n_pendientes: Mapped[int] = col(
        Integer,
        default=0,
        server_default="0",
        comentario="Referencias pendientes de PDF.",
        alimenta="Informe del corpus por tema (RF-15)",
    )
    creada_en: Mapped[datetime] = momento("Fecha y hora de creación.")


class Caso(Base):
    __tablename__ = "caso"
    __table_args__ = (
        CheckConstraint("codigo ~ '^[A-Z0-9][A-Z0-9_-]{1,31}$'", name="codigo_formato"),
        {"comment": "Caso de estudio (estudiante o pareja), identificado solo por código (RN-12)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    codigo: Mapped[str] = col(
        String(32),
        unique=True,
        comentario="Código único del caso (sin datos personales).",
        alimenta="Clave de todas las exportaciones (RF-17)",
    )
    tipo_autoria: Mapped[TipoAutoria] = col(
        enumeracion(TipoAutoria, "tipo_autoria"),
        comentario="individual o pareja.",
        alimenta="Exportación de casos (RF-17)",
    )
    coleccion_cientifica_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("coleccion.id", ondelete="RESTRICT"),
        index=True,
        comentario="Colección científica del tema del caso. La personal es coleccion.caso_id.",
    )
    norma_citacion: Mapped[str] = col(
        String(20),
        default="ieee",
        server_default="ieee",
        comentario="Norma de citación del caso, de la lista cerrada configurada (D-12).",
    )
    estado: Mapped[EstadoCaso] = col(
        enumeracion(EstadoCaso, "estado_caso"),
        default=EstadoCaso.HABILITADO,
        server_default=EstadoCaso.HABILITADO.value,
        comentario="habilitado o desactivado.",
    )
    creado_en: Mapped[datetime] = momento("Fecha y hora del alta.")
    actualizado_en: Mapped[datetime] = momento("Último cambio de estado o norma.")


class CambioNorma(Base):
    __tablename__ = "cambio_norma"
    __table_args__ = (
        {"comment": "Registro de cada cambio de norma de citación de un caso (T07)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("caso.id", ondelete="CASCADE"),
        index=True,
        comentario="Caso afectado.",
    )
    norma_anterior: Mapped[str] = col(String(20), comentario="Norma antes del cambio.")
    norma_nueva: Mapped[str] = col(String(20), comentario="Norma después del cambio.")
    cuenta_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="RESTRICT"),
        comentario="Cuenta del investigador que hizo el cambio.",
    )
    cambiado_en: Mapped[datetime] = momento("Fecha y hora del cambio.")
