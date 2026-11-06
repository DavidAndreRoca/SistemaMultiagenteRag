"""Cuenta y sesión. Sin nombre, correo ni documento de identidad (RNF-02)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from app.bd.base import Base, clave_primaria, enumeracion, momento
from app.bd.enumeraciones import Rol
from app.bd.modelos._columnas import col


class Cuenta(Base):
    __tablename__ = "cuenta"
    __table_args__ = (
        CheckConstraint("(rol = 'A1') = (caso_id IS NOT NULL)", name="caso_solo_en_a1"),
        CheckConstraint("intentos_fallidos >= 0", name="intentos_positivos"),
        CheckConstraint("codigo ~ '^[A-Z0-9][A-Z0-9_-]{1,39}$'", name="codigo_formato"),
        {"comment": "Cuenta de acceso: A1 (caso) o A2 (investigador)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    codigo: Mapped[str] = col(String(40), unique=True, comentario="Código de inicio de sesión.")
    hash_contrasena: Mapped[str] = col(
        String(255), comentario="Hash Argon2id; nunca la contraseña."
    )
    rol: Mapped[Rol] = col(enumeracion(Rol, "rol"), comentario="A1 (caso) o A2 (investigador).")
    caso_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("caso.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comentario="Caso de la cuenta A1.",
    )
    intentos_fallidos: Mapped[int] = col(
        Integer, default=0, server_default="0", comentario="Fallos en la ventana actual."
    )
    primer_fallo_en: Mapped[datetime | None] = momento(
        "Inicio de la ventana de 15 minutos de fallos.", nulo=True
    )
    bloqueada_hasta: Mapped[datetime | None] = momento("Fin del bloqueo temporal.", nulo=True)
    contrasena_inicial_cambiada: Mapped[bool] = col(
        Boolean,
        default=False,
        server_default="false",
        comentario="La contraseña inicial ya fue reemplazada.",
    )
    creada_en: Mapped[datetime] = momento("Fecha y hora del alta.")


class Sesion(Base):
    __tablename__ = "sesion"
    __table_args__ = (
        Index(
            "ix_sesion_activas_por_cuenta",
            "cuenta_id",
            "creada_en",
            postgresql_where=text("cerrada_en IS NULL"),
        ),
        {"comment": "Sesión de navegador (8 h absolutas, 60 min de inactividad, dos por cuenta)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    cuenta_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("cuenta.id", ondelete="CASCADE"),
        index=True,
        comentario="Cuenta dueña.",
    )
    huella_token: Mapped[str] = col(
        String(64), unique=True, comentario="SHA-256 del token de la cookie; el token no se guarda."
    )
    creada_en: Mapped[datetime] = momento("Inicio de la sesión.")
    ultima_actividad_en: Mapped[datetime] = momento("Última petición autenticada.")
    expira_en: Mapped[datetime] = momento("Expiración absoluta.")
    cerrada_en: Mapped[datetime | None] = momento("Cierre o invalidación.", nulo=True)
    motivo_cierre: Mapped[str | None] = col(
        String(40),
        nullable=True,
        comentario="cierre, inactividad, expiracion, limite o contrasena.",
    )
