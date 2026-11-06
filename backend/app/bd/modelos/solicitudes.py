"""Registro metodológico: solicitud, fragmentos recuperados, resultado, verificación,
decisión y fuente aportada (RNF-01).

Las tablas hijas llevan ``caso_id`` y una clave foránea compuesta (padre_id, caso_id)
hacia el padre: la base impide que un registro de un caso cuelgue de otro caso.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
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
from app.bd.enumeraciones import (
    ALCANCES_ADMITIDOS,
    ALCANCES_CON_REFERENCIA,
    CoherenciaFuente,
    EstadoSolicitud,
    Etiqueta,
    ExistenciaFuente,
    MetodoComprobacionFuentes,
    MetodoExistencia,
    OpcionDecision,
    TipoAlcance,
    TipoSolicitud,
)
from app.bd.metricas import CONTADORES_DECISIONES, USO_MINIMO
from app.bd.modelos._columnas import col

ESTADOS_EN_COLA = (
    "recibida",
    "asignada",
    "recuperando",
    "generando",
    "verificando",
    "reintentando",
)


def _caso_id(alimenta: str | None = None) -> Any:
    return col(
        UUID(as_uuid=True),
        ForeignKey("caso.id", ondelete="CASCADE"),
        index=True,
        comentario="Caso dueño (filtro obligatorio de aislamiento).",
        alimenta=alimenta,
    )


def _lista_sql(valores: Iterable[str]) -> str:
    return ", ".join(f"'{v}'" for v in sorted(valores))


# CHECK que impone la tabla de tipos y alcances admitidos (insumos de T04, tabla 3).
SQL_ALCANCE_ADMITIDO = " OR ".join(
    f"(tipo = '{tipo}' AND alcance_tipo IN ({_lista_sql(alcances)}))"
    for tipo, alcances in ALCANCES_ADMITIDOS.items()
)
SQL_ALCANCE_CON_REFERENCIA = (
    f"(alcance_tipo IN ({_lista_sql(ALCANCES_CON_REFERENCIA)})) = (alcance_ref IS NOT NULL)"
)


def _juicio(comentario: str, alimenta: str | None = None) -> Any:
    """Juicio de evaluación 0 a 1, nulo hasta que se evalúe (T38 y cálculo de O2)."""
    return col(Float, nullable=True, comentario=comentario, alimenta=alimenta)


class Solicitud(Base):
    __tablename__ = "solicitud"
    __table_args__ = (
        UniqueConstraint("id", "caso_id"),
        ForeignKeyConstraint(
            ["version_id", "caso_id"],
            ["version_borrador.id", "version_borrador.caso_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["solicitud_origen_id", "caso_id"],
            ["solicitud.id", "solicitud.caso_id"],
        ),
        CheckConstraint("intentos_tecnicos BETWEEN 0 AND 3", name="intentos_tecnicos_rango"),
        CheckConstraint(SQL_ALCANCE_ADMITIDO, name="alcance_admitido_por_tipo"),
        CheckConstraint(SQL_ALCANCE_CON_REFERENCIA, name="alcance_ref_segun_tipo"),
        CheckConstraint(
            "(completitud_evaluador IS NULL OR completitud_evaluador BETWEEN 0 AND 1)"
            " AND (completitud_humana IS NULL OR completitud_humana BETWEEN 0 AND 1)",
            name="completitud_rango",
        ),
        Index(
            "ix_solicitud_cola",
            "estado",
            "creada_en",
            postgresql_where=text("estado IN ('" + "', '".join(ESTADOS_EN_COLA) + "')"),
        ),
        {"comment": "Solicitud tipificada de un caso sobre una versión (RF-02)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = _caso_id()
    version_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        index=True,
        comentario="Versión del borrador sobre la que se pide (da el hito).",
        alimenta=f"{USO_MINIMO}, unida a version_borrador.hito",
    )
    tipo: Mapped[TipoSolicitud] = col(
        enumeracion(TipoSolicitud, "tipo_solicitud"),
        comentario="Uno de los seis tipos (agente fijo por tipo, RN-02).",
        alimenta=f"M1; {CONTADORES_DECISIONES}; arnés por tipo (RF-25)",
    )
    alcance_tipo: Mapped[TipoAlcance] = col(
        enumeracion(TipoAlcance, "tipo_alcance"),
        comentario="Alcance admitido por el tipo: seccion, hito, fragmento, consulta o version.",
        alimenta="M5",
    )
    alcance_ref: Mapped[str | None] = col(
        Text,
        nullable=True,
        comentario="Identificador de sección o de párrafo, o texto de la consulta; nulo en los"
        " alcances hito y version, que toman la versión vigente completa.",
        alimenta="M5; exportación (RF-17, excluible por RN-20)",
    )
    estado: Mapped[EstadoSolicitud] = col(
        enumeracion(EstadoSolicitud, "estado_solicitud"),
        default=EstadoSolicitud.RECIBIDA,
        server_default=EstadoSolicitud.RECIBIDA.value,
        comentario="Estado en la cola y entrega.",
        alimenta="M1; estado visible (RF-22)",
    )
    motivo: Mapped[str | None] = col(
        Text, nullable=True, comentario="Motivo de rechazo o de no atención."
    )
    configuracion_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("configuracion.id", ondelete="RESTRICT"),
        index=True,
        comentario="Versión de configuración vigente al crearla (RNF-21).",
    )
    solicitud_origen_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True), nullable=True, comentario="Solicitud original si es un reenvío."
    )
    intentos_tecnicos: Mapped[int] = col(
        Integer, default=0, server_default="0", comentario="Reintentos técnicos ante el proveedor."
    )
    creada_en: Mapped[datetime] = momento(
        "Fecha y hora de creación.", alimenta="Latencia por solicitud (RNF-12); historial"
    )
    actualizada_en: Mapped[datetime] = momento("Último cambio de estado.")
    entregada_en: Mapped[datetime | None] = momento(
        "Fecha y hora de entrega.", nulo=True, alimenta="Latencia por solicitud (RNF-12)"
    )
    completitud_evaluador: Mapped[float | None] = _juicio(
        "Juicio del modelo evaluador, 0 a 1: lo recuperado reúne la evidencia necesaria.", "M3"
    )
    completitud_humana: Mapped[float | None] = _juicio(
        "Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25), para la concordancia.",
        "M3",
    )


class FragmentoRecuperado(Base):
    __tablename__ = "fragmento_recuperado"
    __table_args__ = (
        ForeignKeyConstraint(
            ["solicitud_id", "caso_id"], ["solicitud.id", "solicitud.caso_id"], ondelete="CASCADE"
        ),
        UniqueConstraint("solicitud_id", "identificador_visible"),
        CheckConstraint("identificador_visible ~ '^F[1-9][0-9]*$'", name="identificador_formato"),
        {
            "comment": "Fragmento recuperado para una solicitud, con sus puntajes (RF-10).",
            "info": {"alimenta": "M2, M3"},
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = _caso_id()
    solicitud_id: Mapped[uuid.UUID] = col(UUID(as_uuid=True), index=True, comentario="Solicitud.")
    fragmento_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        ForeignKey("fragmento.id", ondelete="RESTRICT"),
        index=True,
        comentario="Fragmento del corpus.",
    )
    identificador_visible: Mapped[str] = col(
        String(8), comentario="F1 a Fn, citable por el agente."
    )
    puntaje_denso: Mapped[float | None] = col(Float, nullable=True, comentario="Similitud coseno.")
    puntaje_lexico: Mapped[float | None] = col(Float, nullable=True, comentario="Puntaje léxico.")
    puntaje_fusionado: Mapped[float | None] = col(
        Float, nullable=True, comentario="Fusión por rangos recíprocos."
    )
    puntaje_reranking: Mapped[float | None] = col(
        Float,
        nullable=True,
        comentario="Puntaje del reordenador normalizado entre 0 y 1 (sigmoide).",
        alimenta="Suficiencia, paso 1 (tau, RF-10)",
    )
    posicion: Mapped[int] = col(Integer, comentario="Posición final tras el reranking.")
    pertinencia_evaluador: Mapped[bool | None] = col(
        Boolean,
        nullable=True,
        comentario="Juicio del modelo evaluador: el fragmento es pertinente a la consulta.",
    )
    pertinencia_humana: Mapped[bool | None] = col(
        Boolean,
        nullable=True,
        comentario="Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25).",
    )


class Resultado(Base):
    __tablename__ = "resultado"
    __table_args__ = (
        UniqueConstraint("id", "caso_id"),
        UniqueConstraint("solicitud_id", "intento"),
        ForeignKeyConstraint(
            ["solicitud_id", "caso_id"], ["solicitud.id", "solicitud.caso_id"], ondelete="CASCADE"
        ),
        CheckConstraint("intento IN (1, 2)", name="intento_unico_reintento"),
        CheckConstraint(
            "(relevancia_evaluador IS NULL OR relevancia_evaluador BETWEEN 0 AND 1)"
            " AND (relevancia_humana IS NULL OR relevancia_humana BETWEEN 0 AND 1)",
            name="relevancia_rango",
        ),
        {
            "comment": "Salida estructurada de un agente por intento (RN-05).",
            "info": {"alimenta": "M5"},
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = _caso_id()
    solicitud_id: Mapped[uuid.UUID] = col(UUID(as_uuid=True), index=True, comentario="Solicitud.")
    intento: Mapped[int] = col(Integer, comentario="1 o 2 (un solo reintento).")
    salida: Mapped[dict[str, Any] | None] = col(
        JSONB, nullable=True, comentario="Salida estructurada validada por tipo."
    )
    etiqueta: Mapped[Etiqueta | None] = col(
        enumeracion(Etiqueta, "etiqueta"),
        nullable=True,
        comentario="verificada, con_advertencias o sin_evidencia_suficiente.",
        alimenta="Distribución de etiquetas (RF-25)",
    )
    advertencias: Mapped[list[Any]] = col(
        JSONB,
        default=list,
        server_default="[]",
        comentario="Comprobaciones fallidas que se entregan con la etiqueta con_advertencias"
        " (6.7).",
    )
    abstencion: Mapped[bool] = col(
        Boolean,
        default=False,
        server_default="false",
        comentario="El agente se abstuvo.",
        alimenta="M1 (las abstenciones solo cuentan en la cobertura)",
    )
    creado_en: Mapped[datetime] = momento("Fecha y hora de generación.")
    relevancia_evaluador: Mapped[float | None] = _juicio(
        "Juicio del modelo evaluador, 0 a 1: el resultado atiende lo solicitado."
    )
    relevancia_humana: Mapped[float | None] = _juicio(
        "Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25), para la concordancia."
    )


class Verificacion(Base):
    __tablename__ = "verificacion"
    __table_args__ = (
        ForeignKeyConstraint(
            ["resultado_id", "caso_id"], ["resultado.id", "resultado.caso_id"], ondelete="CASCADE"
        ),
        UniqueConstraint("resultado_id", "intento"),
        CheckConstraint("intento IN (1, 2)", name="intento_unico_reintento"),
        CheckConstraint("fidelidad IS NULL OR fidelidad BETWEEN 0 AND 1", name="fidelidad_rango"),
        CheckConstraint(
            "n_fuentes_citadas >= 0 AND n_fuentes_confirmadas >= 0"
            " AND n_fuentes_no_comprobables >= 0"
            " AND n_fuentes_confirmadas + n_fuentes_no_comprobables <= n_fuentes_citadas",
            name="conteo_fuentes",
        ),
        CheckConstraint(
            "(n_fuentes_confirmadas = 0) = (metodo IS NULL)", name="metodo_si_hay_confirmadas"
        ),
        CheckConstraint(
            "NOT superada OR (formato_ok AND limites_ok IS NOT FALSE AND citas_ok IS NOT FALSE"
            " AND acceso_abierto_ok IS NOT FALSE AND n_fuentes_confirmadas = n_fuentes_citadas"
            " AND (fidelidad IS NULL OR umbral_fidelidad IS NULL"
            " OR fidelidad >= umbral_fidelidad))",
            name="superada_coherente",
        ),
        {
            "comment": "Verificación de un resultado por intento: seis comprobaciones en orden"
            " (Fase 1, 6.7). En las comprobaciones, nulo significa que no aplica al tipo."
        },
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = _caso_id()
    resultado_id: Mapped[uuid.UUID] = col(UUID(as_uuid=True), index=True, comentario="Resultado.")
    intento: Mapped[int] = col(
        Integer,
        comentario="Intento verificado (1 o 2).",
        alimenta="M4 (se toma la verificación final de cada resultado)",
    )
    formato_ok: Mapped[bool] = col(
        Boolean, comentario="Comprobación 1: la salida cumple el esquema del tipo."
    )
    limites_ok: Mapped[bool | None] = col(
        Boolean,
        nullable=True,
        comentario="Comprobación 2: límites de extensión y ausencia de reescritura.",
    )
    citas_ok: Mapped[bool | None] = col(
        Boolean,
        nullable=True,
        comentario="Comprobación 3: toda cita es un fragmento recuperado (F1 a Fn).",
    )
    n_fuentes_citadas: Mapped[int] = col(
        Integer,
        default=0,
        server_default="0",
        comentario="Comprobación 4: fuentes entregadas cuya existencia se comprobó.",
        alimenta="M6",
    )
    n_fuentes_confirmadas: Mapped[int] = col(
        Integer,
        default=0,
        server_default="0",
        comentario="Comprobación 4: fuentes localizadas por DOI o por metadatos.",
        alimenta="M6",
    )
    n_fuentes_no_comprobables: Mapped[int] = col(
        Integer,
        default=0,
        server_default="0",
        comentario="Comprobación 4: fuentes no comprobables porque un servicio no respondió"
        " (RN-18); no cuentan como no localizadas.",
        alimenta="M6 (se informan aparte)",
    )
    metodo: Mapped[MetodoComprobacionFuentes | None] = col(
        enumeracion(MetodoComprobacionFuentes, "metodo_comprobacion"),
        nullable=True,
        comentario="Comprobación 4: doi, metadatos o mixto; nulo si no se confirmó ninguna.",
        alimenta="M6",
    )
    acceso_abierto_ok: Mapped[bool | None] = col(
        Boolean,
        nullable=True,
        comentario="Comprobación 5: las fuentes recomendadas son de acceso abierto.",
    )
    fidelidad: Mapped[float | None] = col(
        Float,
        nullable=True,
        comentario="Comprobación 6: afirmaciones respaldadas sobre total.",
        alimenta="M4",
    )
    umbral_fidelidad: Mapped[float | None] = col(
        Float, nullable=True, comentario="Umbral aplicado (de la configuración)."
    )
    afirmaciones_total: Mapped[int | None] = col(Integer, nullable=True, comentario="Afirmaciones.")
    afirmaciones_respaldadas: Mapped[int | None] = col(
        Integer, nullable=True, comentario="Respaldadas."
    )
    afirmaciones_no_respaldadas: Mapped[int | None] = col(
        Integer, nullable=True, comentario="No respaldadas."
    )
    afirmaciones_contradichas: Mapped[int | None] = col(
        Integer, nullable=True, comentario="Contradichas."
    )
    motivos_falla: Mapped[list[Any]] = col(
        JSONB, default=list, server_default="[]", comentario="Motivos usados en el reintento."
    )
    superada: Mapped[bool] = col(
        Boolean, comentario="Todas las comprobaciones aplicables superadas."
    )
    modelo_evaluador: Mapped[str | None] = col(
        String(120), nullable=True, comentario="Identificador fijo del modelo evaluador (RN-24)."
    )
    verificada_en: Mapped[datetime] = momento("Fecha y hora de la verificación.")


class Decision(Base):
    __tablename__ = "decision"
    __table_args__ = (
        ForeignKeyConstraint(
            ["resultado_id", "caso_id"], ["resultado.id", "resultado.caso_id"], ondelete="CASCADE"
        ),
        UniqueConstraint("decision_reemplazada_id"),
        {"comment": "Decisión del caso sobre un resultado; un cambio crea otra fila (RN-08)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = _caso_id(alimenta=CONTADORES_DECISIONES)
    resultado_id: Mapped[uuid.UUID] = col(UUID(as_uuid=True), index=True, comentario="Resultado.")
    opcion: Mapped[OpcionDecision] = col(
        enumeracion(OpcionDecision, "opcion_decision"),
        comentario="aceptar, modificar, rechazar, continuar o aportar.",
        alimenta=CONTADORES_DECISIONES,
    )
    decidida_en: Mapped[datetime] = momento("Fecha y hora de la decisión.")
    decision_reemplazada_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("decision.id", ondelete="RESTRICT"),
        nullable=True,
        comentario="Decisión anterior a la que reemplaza (se conserva).",
    )


class FuenteAportada(Base):
    __tablename__ = "fuente_aportada"
    __table_args__ = (
        ForeignKeyConstraint(
            ["solicitud_id", "caso_id"], ["solicitud.id", "solicitud.caso_id"], ondelete="CASCADE"
        ),
        {"comment": "Fuente aportada por el caso tras una abstención (RF-13)."},
    )

    id: Mapped[uuid.UUID] = clave_primaria()
    caso_id: Mapped[uuid.UUID] = _caso_id()
    solicitud_id: Mapped[uuid.UUID] = col(
        UUID(as_uuid=True),
        index=True,
        comentario="Solicitud con abstención que motivó el aporte.",
        alimenta="M1 (lo resuelto solo tras un aporte cuenta como no cubierto; se reporta aparte)",
    )
    datos_bibliograficos: Mapped[dict[str, Any]] = col(
        JSONB, comentario="Título, autores de la obra y año declarados por el caso."
    )
    doi: Mapped[str | None] = col(String(255), nullable=True, comentario="DOI declarado.")
    existencia: Mapped[ExistenciaFuente] = col(
        enumeracion(ExistenciaFuente, "existencia_fuente"),
        comentario="confirmada, no_localizada o no_comprobable (RN-18).",
    )
    metodo_existencia: Mapped[MetodoExistencia | None] = col(
        enumeracion(MetodoExistencia, "metodo_existencia"),
        nullable=True,
        comentario="doi o metadatos.",
    )
    coherencia: Mapped[CoherenciaFuente] = col(
        enumeracion(CoherenciaFuente, "coherencia_fuente"),
        default=CoherenciaFuente.NO_EVALUADA,
        server_default=CoherenciaFuente.NO_EVALUADA.value,
        comentario="Coherencia con la afirmación (informativa).",
    )
    documento_id: Mapped[uuid.UUID | None] = col(
        UUID(as_uuid=True),
        ForeignKey("documento.id", ondelete="SET NULL"),
        nullable=True,
        comentario="Documento indexado en la colección personal, si existe.",
    )
    aportada_en: Mapped[datetime] = momento("Fecha y hora del aporte.")
