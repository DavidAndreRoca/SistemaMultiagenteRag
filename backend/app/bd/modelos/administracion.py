"""Configuración versionada, evento técnico y caché de metadatos."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped

from app.bd.base import Base, clave_primaria, momento
from app.bd.modelos._columnas import col


class Configuracion(Base):
    __tablename__ = "configuracion"
    __table_args__ = (
        Index(
            "uq_configuracion_una_vigente", "vigente", unique=True, postgresql_where=text("vigente")
        ),
        {"comment": "Parámetros funcionales versionados (RF-23). Se validan con Pydantic."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    numero_version: Mapped[int] = col(Integer, unique=True, comentario="Número de versión.")
    parametros: Mapped[dict[str, Any]] = col(
        JSONB, comentario="Parámetros validados por app.administracion.parametros."
    )
    comentario: Mapped[str] = col(Text, comentario="Motivo del cambio.")
    vigente: Mapped[bool] = col(
        Boolean, default=False, server_default="false", comentario="Vigente."
    )
    congelada: Mapped[bool] = col(
        Boolean, default=False, server_default="false", comentario="Congelada (RN-21)."
    )
    creada_en: Mapped[datetime] = momento("Fecha y hora de creación.")


class EventoTecnico(Base):
    __tablename__ = "evento_tecnico"
    __table_args__ = (
        {
            "comment": "Evento técnico por etapa: latencia, tokens, costo y error (separado del "
            "registro metodológico)."
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    solicitud_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("solicitud.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comentario="Solicitud asociada, si la hay.",
    )
    etapa: Mapped[str] = col(String(60), comentario="Etapa (recuperacion, generacion, ...).")
    inicio: Mapped[datetime] = momento("Inicio de la etapa.", alimenta="Monitoreo (RF-24)")
    duracion_ms: Mapped[int] = col(
        Integer, comentario="Duración en milisegundos.", alimenta="Latencia p95 (RNF-12)"
    )
    proveedor: Mapped[str | None] = col(String(60), nullable=True, comentario="Proveedor usado.")
    modelo: Mapped[str | None] = col(
        String(120), nullable=True, comentario="Identificador fijo del modelo (RN-24)."
    )
    tokens_entrada: Mapped[int | None] = col(
        Integer, nullable=True, comentario="Tokens de entrada.", alimenta="Costos (RNF-24)"
    )
    tokens_salida: Mapped[int | None] = col(
        Integer, nullable=True, comentario="Tokens de salida.", alimenta="Costos (RNF-24)"
    )
    costo_estimado: Mapped[Decimal | None] = col(
        Numeric(12, 6),
        nullable=True,
        comentario="Costo estimado en USD.",
        alimenta="Tope de gasto y modo protegido (RN-22)",
    )
    error: Mapped[str | None] = col(
        String(120),
        nullable=True,
        comentario="Tipo de error, sin contenido.",
        alimenta="Tasa de errores (RF-24)",
    )


class CacheMetadatos(Base):
    __tablename__ = "cache_metadatos"
    __table_args__ = (
        UniqueConstraint("servicio", "clave"),
        {"comment": "Caché de respuestas de servicios bibliográficos (T14)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    servicio: Mapped[str] = col(String(40), comentario="crossref, doi, unpaywall u openalex.")
    clave: Mapped[str] = col(Text, comentario="DOI o consulta normalizada.")
    respuesta: Mapped[dict[str, Any]] = col(JSONB, comentario="Respuesta normalizada.")
    obtenida_en: Mapped[datetime] = momento("Fecha de obtención.")
    vigente_hasta: Mapped[datetime] = momento("Fin de vigencia.")
