"""Versión del borrador: carga, validación y párrafos en T11; secciones en T12."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped

from app.bd.base import Base, clave_primaria, enumeracion, momento
from app.bd.enumeraciones import MetodoDeteccionSecciones
from app.bd.metricas import USO_MINIMO
from app.bd.modelos._columnas import col


class VersionBorrador(Base):
    __tablename__ = "version_borrador"
    __table_args__ = (
        UniqueConstraint("id", "caso_id"),  # destino de claves compuestas (aislamiento)
        CheckConstraint("huella_sha256 ~ '^[0-9a-f]{64}$'", name="huella_hex"),
        CheckConstraint("palabras >= 0", name="palabras_no_negativas"),
        Index(
            "uq_version_borrador_vigente_por_hito",
            "caso_id",
            "hito",
            unique=True,
            postgresql_where=text("vigente"),
        ),
        {"comment": "Versión del borrador .docx cargada por un caso en un hito (RF-01, RN-09)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("caso.id", ondelete="CASCADE"),
        index=True,
        comentario="Caso dueño.",
    )
    hito: Mapped[str] = col(
        String(40),
        comentario="Código del hito, del catálogo de la configuración versionada.",
        alimenta=f"{USO_MINIMO}; historial (RF-14)",
    )
    cargada_en: Mapped[datetime] = momento(
        "Fecha y hora de la carga.", alimenta="Historial (RF-14); exportación (RF-17)"
    )
    ruta_archivo: Mapped[str] = col(
        Text, comentario="Ruta interna con nombre aleatorio, fuera de la carpeta pública."
    )
    huella_sha256: Mapped[str] = col(String(64), comentario="Huella SHA-256 del archivo.")
    tamano_bytes: Mapped[int] = col(BigInteger, comentario="Tamaño del archivo.")
    vigente: Mapped[bool] = col(
        Boolean, default=True, server_default="true", comentario="Versión vigente de su hito."
    )
    # Carga diferida: listar versiones no trae el texto (decisión T11-01, apartado 5).
    parrafos: Mapped[list[dict[str, Any]]] = col(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        deferred=True,
        comentario="Párrafos extraídos con identificador estable (p1, p2...), texto, estilo"
        " y origen (cuerpo o tabla).",
    )
    palabras: Mapped[int] = col(
        Integer, default=0, server_default="0", comentario="Palabras del texto extraído."
    )
    secciones: Mapped[dict[str, Any] | None] = col(
        JSONB, nullable=True, comentario="Secciones detectadas con identificadores estables (T12)."
    )
    metodo_deteccion: Mapped[MetodoDeteccionSecciones | None] = col(
        enumeracion(MetodoDeteccionSecciones, "metodo_deteccion"),
        nullable=True,
        comentario="estilos o manual.",
    )
