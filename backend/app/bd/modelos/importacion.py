"""Importación de referencias del artículo O1 (T15; RF-20, RN-19).

Solo se guardan las referencias y el avance de cada importación: el artículo O1 no se
almacena ni se indexa (RN-19). No son datos de caso: pertenecen a la colección científica
de un tema y los administra el investigador (A2).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped

from app.bd.base import Base, clave_primaria, enumeracion, momento
from app.bd.enumeraciones import EstadoImportacion, EstadoReferencia, OrigenImportacion
from app.bd.modelos._columnas import col


class ImportacionReferencias(Base):
    __tablename__ = "importacion_referencias"
    __table_args__ = (
        CheckConstraint(
            "procesadas >= 0 AND total >= 0 AND procesadas <= total", name="avance_valido"
        ),
        {
            "comment": "Importación de las referencias de un artículo O1 o de una lista de DOI"
            " (RF-20, T15)."
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    coleccion_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("coleccion.id", ondelete="RESTRICT"),
        index=True,
        comentario="Colección científica del tema.",
    )
    origen: Mapped[OrigenImportacion] = col(
        enumeracion(OrigenImportacion, "origen_importacion"),
        comentario="pdf o docx (artículo O1, que no se guarda) o doi (lista de DOI).",
    )
    estado: Mapped[EstadoImportacion] = col(
        enumeracion(EstadoImportacion, "estado_importacion"),
        default=EstadoImportacion.EN_COLA,
        server_default=EstadoImportacion.EN_COLA.value,
        comentario="Avance del proceso en segundo plano.",
    )
    total: Mapped[int] = col(
        Integer, default=0, server_default="0", comentario="Referencias extraídas."
    )
    procesadas: Mapped[int] = col(
        Integer, default=0, server_default="0", comentario="Referencias ya resueltas."
    )
    error: Mapped[str | None] = col(
        String(60), nullable=True, comentario="Código del error si la importación falló."
    )
    creada_por_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="SET NULL"),
        nullable=True,
        comentario="Investigador que la pidió.",
    )
    creada_en: Mapped[datetime] = momento("Fecha y hora de la solicitud.")
    iniciada_en: Mapped[datetime | None] = momento("Inicio del proceso.", nulo=True)
    terminada_en: Mapped[datetime | None] = momento("Fin del proceso.", nulo=True)


class ReferenciaImportada(Base):
    __tablename__ = "referencia_importada"
    __table_args__ = (
        UniqueConstraint("coleccion_id", "clave"),
        CheckConstraint(
            "(estado = 'incluida') = (documento_id IS NOT NULL)", name="incluida_con_documento"
        ),
        CheckConstraint(
            "(estado = 'incluida') OR motivo IS NOT NULL", name="motivo_si_no_incluida"
        ),
        {
            "comment": "Referencia de un artículo O1 en la colección de su tema, con su estado"
            " (RF-20). Solo la entrada bibliográfica: nunca texto del artículo (RN-19)."
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    coleccion_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("coleccion.id", ondelete="RESTRICT"),
        index=True,
        comentario="Colección científica del tema.",
    )
    importacion_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("importacion_referencias.id", ondelete="CASCADE"),
        index=True,
        comentario="Última importación que la trató.",
    )
    clave: Mapped[str] = col(
        String(300),
        comentario="doi:<DOI normalizado> o texto:<huella SHA-256 del texto normalizado>;"
        " única por colección (idempotencia).",
    )
    texto: Mapped[str] = col(Text, comentario="Entrada bibliográfica tal como la extrajo GROBID.")
    doi: Mapped[str | None] = col(
        String(255), nullable=True, index=True, comentario="DOI normalizado, si se conoce."
    )
    titulo: Mapped[str | None] = col(Text, nullable=True, comentario="Título de la obra.")
    autores: Mapped[list[Any]] = col(
        JSONB,
        default=list,
        server_default="[]",
        comentario="Apellidos de los autores de la obra (metadato bibliográfico).",
    )
    anio: Mapped[int | None] = col(Integer, nullable=True, comentario="Año de publicación.")
    estado: Mapped[EstadoReferencia] = col(
        enumeracion(EstadoReferencia, "estado_referencia"),
        comentario="incluida, pendiente_pdf, excluida o no_comprobable.",
    )
    motivo: Mapped[str | None] = col(
        String(60), nullable=True, comentario="Motivo del estado si no está incluida."
    )
    estado_oa: Mapped[str | None] = col(
        String(20), nullable=True, comentario="Estado de acceso abierto según Unpaywall."
    )
    url_acceso_abierto: Mapped[str | None] = col(
        Text, nullable=True, comentario="Página de acceso abierto (para bajar el PDF a mano)."
    )
    url_pdf: Mapped[str | None] = col(
        Text, nullable=True, comentario="Enlace directo al PDF, si lo hay."
    )
    licencia: Mapped[str | None] = col(String(80), nullable=True, comentario="Licencia de uso.")
    documento_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("documento.id", ondelete="SET NULL"),
        nullable=True,
        comentario="Documento indexado, si está incluida.",
    )
    actualizada_en: Mapped[datetime] = momento("Último cambio de estado.")
