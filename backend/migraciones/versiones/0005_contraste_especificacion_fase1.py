"""T04: ajustar el esquema a la especificación de la Fase 1 (6.7, 18.2 y tabla de alcances).

Diferencias corregidas (detalle en docs/decisiones/T04-contraste-especificacion-fase1.md):

* solicitud: códigos de tipo de la tabla 3 de los insumos; alcances seccion, hito,
  fragmento, consulta y version; ``alcance_contenido`` (JSONB) pasa a ``alcance_ref``
  (texto); CHECK de alcance admitido por tipo; juicio de completitud (M3).
* verificacion: campos de la salida de 6.7 (formato_ok, limites_ok, citas_ok,
  n_fuentes_citadas, n_fuentes_confirmadas, metodo, acceso_abierto_ok, fidelidad,
  superada) en lugar de las seis comprobaciones c1 a c6.
* resultado: advertencias (6.7) y juicio de relevancia (M5).
* fragmento_recuperado: juicio de pertinencia (M2).
* documento: ISBN, ruta del archivo y revista o editorial (18.2).
* fragmento: tsvector generado con la configuración simple (18.2).

solicitud y verificacion deben estar vacías: ninguna fase anterior a T16 y T19 las
escribe, y sus datos viejos no tienen traducción exacta. Si no lo están, la migración
se detiene sin cambiar nada.

Revisión: 0005
Anterior: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIPOS_NUEVOS = (
    "revision_estructura",
    "plan_tarea",
    "revision_metodologica",
    "propuesta_redaccion",
    "busqueda_evidencia",
    "verificacion_referencias",
)
TIPOS_VIEJOS = ("estructura", "plan_tarea", "metodologico", "redaccion", "evidencia", "referencias")
ALCANCES_NUEVOS = ("seccion", "hito", "fragmento", "consulta", "version")
ALCANCES_VIEJOS = ("version", "seccion", "parrafo", "consulta")
ESTADOS_COMPROBACION = ("superada", "fallida", "no_comprobable", "no_aplica")

# Copia literal de app.bd.modelos.solicitudes (la migración no depende del código).
SQL_ALCANCE_ADMITIDO = (
    "(tipo = 'revision_estructura' AND alcance_tipo IN ('seccion'))"
    " OR (tipo = 'plan_tarea' AND alcance_tipo IN ('hito'))"
    " OR (tipo = 'revision_metodologica' AND alcance_tipo IN ('seccion'))"
    " OR (tipo = 'propuesta_redaccion' AND alcance_tipo IN ('fragmento'))"
    " OR (tipo = 'busqueda_evidencia' AND alcance_tipo IN ('consulta', 'fragmento'))"
    " OR (tipo = 'verificacion_referencias' AND alcance_tipo IN ('version'))"
)
SQL_ALCANCE_CON_REFERENCIA = (
    "(alcance_tipo IN ('consulta', 'fragmento', 'seccion')) = (alcance_ref IS NOT NULL)"
)
SQL_SUPERADA = (
    "NOT superada OR (formato_ok AND limites_ok IS NOT FALSE AND citas_ok IS NOT FALSE"
    " AND acceso_abierto_ok IS NOT FALSE AND n_fuentes_confirmadas = n_fuentes_citadas"
    " AND (fidelidad IS NULL OR umbral_fidelidad IS NULL OR fidelidad >= umbral_fidelidad))"
)


def _en(columna: str, valores: Sequence[str]) -> str:
    return f"{columna} IN (" + ", ".join(f"'{v}'" for v in valores) + ")"


def _exigir_vacias(*tablas: str) -> None:
    conexion = op.get_bind()
    for tabla in tablas:
        filas = conexion.execute(sa.text(f"SELECT count(*) FROM {tabla}")).scalar_one()
        if filas:
            raise RuntimeError(
                f"La tabla {tabla} tiene {filas} filas; esta migración solo se aplica con"
                " solicitud y verificacion vacías (ver el docstring de 0005)."
            )


def _check(nombre: str, tabla: str, condicion: str) -> None:
    op.create_check_constraint(op.f(nombre), tabla, condicion)


def _comentario(
    tabla: str, columna: str, tipo: sa.types.TypeEngine[object], nuevo: str, viejo: str, nulo: bool
) -> None:
    op.alter_column(
        tabla,
        columna,
        existing_type=tipo,
        comment=nuevo,
        existing_comment=viejo,
        existing_nullable=nulo,
    )


def upgrade() -> None:
    _exigir_vacias("solicitud", "verificacion")

    # --- solicitud: tipos, alcances y juicio de completitud ---
    op.drop_constraint(op.f("ck_solicitud_tipo_solicitud"), "solicitud", type_="check")
    _check("ck_solicitud_tipo_solicitud", "solicitud", _en("tipo", TIPOS_NUEVOS))
    op.drop_constraint(op.f("ck_solicitud_tipo_alcance"), "solicitud", type_="check")
    _check("ck_solicitud_tipo_alcance", "solicitud", _en("alcance_tipo", ALCANCES_NUEVOS))
    op.drop_column("solicitud", "alcance_contenido")
    op.add_column(
        "solicitud",
        sa.Column(
            "alcance_ref",
            sa.Text(),
            nullable=True,
            comment="Identificador de sección o de párrafo, o texto de la consulta; nulo en los"
            " alcances hito y version, que toman la versión vigente completa.",
        ),
    )
    _check("ck_solicitud_alcance_admitido_por_tipo", "solicitud", SQL_ALCANCE_ADMITIDO)
    _check("ck_solicitud_alcance_ref_segun_tipo", "solicitud", SQL_ALCANCE_CON_REFERENCIA)
    op.add_column(
        "solicitud",
        sa.Column(
            "completitud_evaluador",
            sa.Float(),
            nullable=True,
            comment="Juicio del modelo evaluador, 0 a 1: lo recuperado reúne la evidencia"
            " necesaria.",
        ),
    )
    op.add_column(
        "solicitud",
        sa.Column(
            "completitud_humana",
            sa.Float(),
            nullable=True,
            comment="Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25), para la"
            " concordancia.",
        ),
    )
    _check(
        "ck_solicitud_completitud_rango",
        "solicitud",
        "(completitud_evaluador IS NULL OR completitud_evaluador BETWEEN 0 AND 1)"
        " AND (completitud_humana IS NULL OR completitud_humana BETWEEN 0 AND 1)",
    )
    _comentario(
        "solicitud",
        "version_id",
        sa.UUID(),
        "Versión del borrador sobre la que se pide (da el hito).",
        "Versión del borrador sobre la que se pide.",
        False,
    )
    _comentario(
        "solicitud",
        "tipo",
        sa.VARCHAR(40),
        "Uno de los seis tipos (agente fijo por tipo, RN-02).",
        "Uno de los seis tipos.",
        False,
    )
    _comentario(
        "solicitud",
        "alcance_tipo",
        sa.VARCHAR(40),
        "Alcance admitido por el tipo: seccion, hito, fragmento, consulta o version.",
        "version, seccion, parrafo o consulta.",
        False,
    )

    # --- verificacion: campos de la salida de 6.7 ---
    for columna in (
        "c1_esquema",
        "c2_limites",
        "c3_citas",
        "c4_existencia",
        "c5_acceso_abierto",
        "c6_fidelidad",
    ):
        op.drop_column("verificacion", columna)  # su CHECK cae con la columna
    op.alter_column(
        "verificacion",
        "aprobada",
        new_column_name="superada",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        existing_comment="Todas las comprobaciones aplicables superadas.",
    )
    nuevas = [
        sa.Column(
            "formato_ok",
            sa.Boolean(),
            nullable=False,
            comment="Comprobación 1: la salida cumple el esquema del tipo.",
        ),
        sa.Column(
            "limites_ok",
            sa.Boolean(),
            nullable=True,
            comment="Comprobación 2: límites de extensión y ausencia de reescritura.",
        ),
        sa.Column(
            "citas_ok",
            sa.Boolean(),
            nullable=True,
            comment="Comprobación 3: toda cita es un fragmento recuperado (F1 a Fn).",
        ),
        sa.Column(
            "n_fuentes_citadas",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Comprobación 4: fuentes entregadas cuya existencia se comprobó.",
        ),
        sa.Column(
            "n_fuentes_confirmadas",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Comprobación 4: fuentes localizadas por DOI o por metadatos.",
        ),
        sa.Column(
            "n_fuentes_no_comprobables",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Comprobación 4: fuentes no comprobables porque un servicio no"
            " respondió (RN-18); no cuentan como no localizadas.",
        ),
        sa.Column(
            "metodo",
            sa.String(40),
            nullable=True,
            comment="Comprobación 4: doi, metadatos o mixto; nulo si no se confirmó ninguna.",
        ),
        sa.Column(
            "acceso_abierto_ok",
            sa.Boolean(),
            nullable=True,
            comment="Comprobación 5: las fuentes recomendadas son de acceso abierto.",
        ),
    ]
    for columna in nuevas:
        op.add_column("verificacion", columna)
    _check(
        "ck_verificacion_metodo_comprobacion",
        "verificacion",
        _en("metodo", ("doi", "metadatos", "mixto")),
    )
    _check("ck_verificacion_intento_unico_reintento", "verificacion", "intento IN (1, 2)")
    _check(
        "ck_verificacion_conteo_fuentes",
        "verificacion",
        "n_fuentes_citadas >= 0 AND n_fuentes_confirmadas >= 0 AND n_fuentes_no_comprobables >= 0"
        " AND n_fuentes_confirmadas + n_fuentes_no_comprobables <= n_fuentes_citadas",
    )
    _check(
        "ck_verificacion_metodo_si_hay_confirmadas",
        "verificacion",
        "(n_fuentes_confirmadas = 0) = (metodo IS NULL)",
    )
    _check("ck_verificacion_superada_coherente", "verificacion", SQL_SUPERADA)
    _comentario(
        "verificacion",
        "fidelidad",
        sa.Float(),
        "Comprobación 6: afirmaciones respaldadas sobre total.",
        "Afirmaciones respaldadas sobre total.",
        True,
    )
    op.create_table_comment(
        "verificacion",
        "Verificación de un resultado por intento: seis comprobaciones en orden (Fase 1, 6.7)."
        " En las comprobaciones, nulo significa que no aplica al tipo.",
        existing_comment="Verificación de un resultado por intento: seis comprobaciones"
        " (Fase 1, 6.7).",
    )

    # --- resultado: advertencias y relevancia ---
    op.add_column(
        "resultado",
        sa.Column(
            "advertencias",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
            comment="Comprobaciones fallidas que se entregan con la etiqueta con_advertencias"
            " (6.7).",
        ),
    )
    op.add_column(
        "resultado",
        sa.Column(
            "relevancia_evaluador",
            sa.Float(),
            nullable=True,
            comment="Juicio del modelo evaluador, 0 a 1: el resultado atiende lo solicitado.",
        ),
    )
    op.add_column(
        "resultado",
        sa.Column(
            "relevancia_humana",
            sa.Float(),
            nullable=True,
            comment="Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25), para la"
            " concordancia.",
        ),
    )
    _check(
        "ck_resultado_relevancia_rango",
        "resultado",
        "(relevancia_evaluador IS NULL OR relevancia_evaluador BETWEEN 0 AND 1)"
        " AND (relevancia_humana IS NULL OR relevancia_humana BETWEEN 0 AND 1)",
    )

    # --- fragmento_recuperado: pertinencia ---
    op.add_column(
        "fragmento_recuperado",
        sa.Column(
            "pertinencia_evaluador",
            sa.Boolean(),
            nullable=True,
            comment="Juicio del modelo evaluador: el fragmento es pertinente a la consulta.",
        ),
    )
    op.add_column(
        "fragmento_recuperado",
        sa.Column(
            "pertinencia_humana",
            sa.Boolean(),
            nullable=True,
            comment="Mismo juicio por revisión humana (muestra del 20 al 30 %, RF-25).",
        ),
    )
    _comentario(
        "fragmento_recuperado",
        "puntaje_reranking",
        sa.Float(),
        "Puntaje del reordenador normalizado entre 0 y 1 (sigmoide).",
        "Puntaje del reordenador.",
        True,
    )
    _comentario(
        "fuente_aportada",
        "solicitud_id",
        sa.UUID(),
        "Solicitud con abstención que motivó el aporte.",
        "Solicitud.",
        False,
    )

    # --- documento: metadatos de 18.2 ---
    op.alter_column(
        "documento",
        "fuente",
        new_column_name="revista_editorial",
        existing_type=sa.Text(),
        existing_nullable=True,
        comment="Revista (artículos) o editorial (libros).",
        existing_comment="Revista, libro o contenedor.",
    )
    op.add_column(
        "documento",
        sa.Column(
            "isbn",
            sa.String(13),
            nullable=True,
            comment="ISBN-10 o ISBN-13 sin guiones (libros, 18.9).",
        ),
    )
    _check(
        "ck_documento_isbn_normalizado",
        "documento",
        "isbn IS NULL OR isbn ~ '^(97[89][0-9]{10}|[0-9]{9}[0-9X])$'",
    )
    op.add_column(
        "documento",
        sa.Column(
            "ruta_archivo",
            sa.Text(),
            nullable=True,
            comment="Ruta interna con nombre aleatorio, fuera de la carpeta pública; nula si se"
            " indexó solo el resumen de Crossref u OpenAlex (RF-13).",
        ),
    )
    _comentario(
        "documento",
        "huella_sha256",
        sa.VARCHAR(64),
        "Huella SHA-256 del texto normalizado, para deduplicar (18.9).",
        "Huella SHA-256 del PDF, para deduplicar.",
        False,
    )
    _comentario(
        "documento",
        "estado",
        sa.VARCHAR(40),
        "activo, retirado o incompleto (un retirado deja de recuperarse, 18.9).",
        "activo, retirado o incompleto.",
        False,
    )

    # --- fragmento: tsvector generado con configuración simple ---
    op.drop_column("fragmento", "texto_lexico")
    op.add_column(
        "fragmento",
        sa.Column(
            "texto_lexico",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple'::regconfig, texto)", persisted=True),
            comment="Vector léxico tsvector con configuración simple, generado desde el texto.",
        ),
    )


def downgrade() -> None:
    _exigir_vacias("solicitud", "verificacion")

    op.drop_column("fragmento", "texto_lexico")
    op.add_column(
        "fragmento",
        sa.Column(
            "texto_lexico",
            postgresql.TSVECTOR(),
            nullable=True,
            comment="tsvector con configuración simple.",
        ),
    )

    _comentario(
        "documento",
        "estado",
        sa.VARCHAR(40),
        "activo, retirado o incompleto.",
        "activo, retirado o incompleto (un retirado deja de recuperarse, 18.9).",
        False,
    )
    _comentario(
        "documento",
        "huella_sha256",
        sa.VARCHAR(64),
        "Huella SHA-256 del PDF, para deduplicar.",
        "Huella SHA-256 del texto normalizado, para deduplicar (18.9).",
        False,
    )
    op.drop_column("documento", "ruta_archivo")
    op.drop_constraint(op.f("ck_documento_isbn_normalizado"), "documento", type_="check")
    op.drop_column("documento", "isbn")
    op.alter_column(
        "documento",
        "revista_editorial",
        new_column_name="fuente",
        existing_type=sa.Text(),
        existing_nullable=True,
        comment="Revista, libro o contenedor.",
        existing_comment="Revista (artículos) o editorial (libros).",
    )

    _comentario(
        "fuente_aportada",
        "solicitud_id",
        sa.UUID(),
        "Solicitud.",
        "Solicitud con abstención que motivó el aporte.",
        False,
    )
    _comentario(
        "fragmento_recuperado",
        "puntaje_reranking",
        sa.Float(),
        "Puntaje del reordenador.",
        "Puntaje del reordenador normalizado entre 0 y 1 (sigmoide).",
        True,
    )
    op.drop_column("fragmento_recuperado", "pertinencia_humana")
    op.drop_column("fragmento_recuperado", "pertinencia_evaluador")

    op.drop_constraint(op.f("ck_resultado_relevancia_rango"), "resultado", type_="check")
    op.drop_column("resultado", "relevancia_humana")
    op.drop_column("resultado", "relevancia_evaluador")
    op.drop_column("resultado", "advertencias")

    op.create_table_comment(
        "verificacion",
        "Verificación de un resultado por intento: seis comprobaciones (Fase 1, 6.7).",
        existing_comment="Verificación de un resultado por intento: seis comprobaciones en orden"
        " (Fase 1, 6.7). En las comprobaciones, nulo significa que no aplica al tipo.",
    )
    _comentario(
        "verificacion",
        "fidelidad",
        sa.Float(),
        "Afirmaciones respaldadas sobre total.",
        "Comprobación 6: afirmaciones respaldadas sobre total.",
        True,
    )
    for restriccion in (
        "superada_coherente",
        "metodo_si_hay_confirmadas",
        "conteo_fuentes",
        "intento_unico_reintento",
        "metodo_comprobacion",
    ):
        op.drop_constraint(op.f(f"ck_verificacion_{restriccion}"), "verificacion", type_="check")
    for columna in (
        "acceso_abierto_ok",
        "metodo",
        "n_fuentes_no_comprobables",
        "n_fuentes_confirmadas",
        "n_fuentes_citadas",
        "citas_ok",
        "limites_ok",
        "formato_ok",
    ):
        op.drop_column("verificacion", columna)
    op.alter_column(
        "verificacion",
        "superada",
        new_column_name="aprobada",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        existing_comment="Todas las comprobaciones aplicables superadas.",
    )
    viejas = {
        "c1_esquema": "Comprobación 1: esquema del tipo.",
        "c2_limites": "Comprobación 2: límites por tipo (no reescritura, números, extensión).",
        "c3_citas": "Comprobación 3: toda cita existe entre los fragmentos recuperados.",
        "c4_existencia": "Comprobación 4: existencia de las fuentes (no_comprobable si el"
        " servicio cae).",
        "c5_acceso_abierto": "Comprobación 5: acceso abierto de las fuentes recomendadas.",
        "c6_fidelidad": "Comprobación 6: fidelidad frente al umbral.",
    }
    for columna, comentario in viejas.items():
        op.add_column(
            "verificacion",
            sa.Column(columna, sa.String(40), nullable=False, comment=comentario),
        )
        _check(f"ck_verificacion_{columna}", "verificacion", _en(columna, ESTADOS_COMPROBACION))

    _comentario(
        "solicitud",
        "alcance_tipo",
        sa.VARCHAR(40),
        "version, seccion, parrafo o consulta.",
        "Alcance admitido por el tipo: seccion, hito, fragmento, consulta o version.",
        False,
    )
    _comentario(
        "solicitud",
        "tipo",
        sa.VARCHAR(40),
        "Uno de los seis tipos.",
        "Uno de los seis tipos (agente fijo por tipo, RN-02).",
        False,
    )
    _comentario(
        "solicitud",
        "version_id",
        sa.UUID(),
        "Versión del borrador sobre la que se pide.",
        "Versión del borrador sobre la que se pide (da el hito).",
        False,
    )
    op.drop_constraint(op.f("ck_solicitud_completitud_rango"), "solicitud", type_="check")
    op.drop_column("solicitud", "completitud_humana")
    op.drop_column("solicitud", "completitud_evaluador")
    op.drop_constraint(op.f("ck_solicitud_alcance_ref_segun_tipo"), "solicitud", type_="check")
    op.drop_constraint(op.f("ck_solicitud_alcance_admitido_por_tipo"), "solicitud", type_="check")
    op.drop_column("solicitud", "alcance_ref")
    op.add_column(
        "solicitud",
        sa.Column(
            "alcance_contenido",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Identificadores de sección o párrafo, o texto de la consulta.",
        ),
    )
    op.drop_constraint(op.f("ck_solicitud_tipo_alcance"), "solicitud", type_="check")
    _check("ck_solicitud_tipo_alcance", "solicitud", _en("alcance_tipo", ALCANCES_VIEJOS))
    op.drop_constraint(op.f("ck_solicitud_tipo_solicitud"), "solicitud", type_="check")
    _check("ck_solicitud_tipo_solicitud", "solicitud", _en("tipo", TIPOS_VIEJOS))
