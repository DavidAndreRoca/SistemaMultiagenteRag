"""T04: modelo de datos inicial (15 tablas) y extensión vector.

Los índices HNSW y GIN se crean en T10; las tablas del checkpointer de LangGraph en T28.

Revisión: 0001
Anterior: ninguna
Creada: 2026-11-06 20:04:12.778838+00:00
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "cache_metadatos",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "servicio",
            sa.String(length=40),
            nullable=False,
            comment="crossref, doi, unpaywall u openalex.",
        ),
        sa.Column("clave", sa.Text(), nullable=False, comment="DOI o consulta normalizada."),
        sa.Column(
            "respuesta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Respuesta normalizada.",
        ),
        sa.Column(
            "obtenida_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha de obtención.",
        ),
        sa.Column(
            "vigente_hasta",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fin de vigencia.",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cache_metadatos")),
        sa.UniqueConstraint("servicio", "clave", name=op.f("uq_cache_metadatos_servicio_clave")),
        comment="Caché de respuestas de servicios bibliográficos (T14).",
    )
    op.create_table(
        "coleccion",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "tipo",
            sa.Enum(
                "guias",
                "cientifica",
                "personal",
                name="tipo_coleccion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="guias, cientifica o personal.",
        ),
        sa.Column(
            "tema",
            sa.String(length=80),
            nullable=True,
            comment="Código del tema (solo en la colección científica).",
        ),
        sa.Column(
            "caso_id",
            sa.UUID(),
            nullable=True,
            comment="Caso dueño (solo en la colección personal).",
        ),
        sa.Column(
            "n_incluidas",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Documentos incluidos.",
        ),
        sa.Column(
            "n_excluidas",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Referencias excluidas con motivo.",
        ),
        sa.Column(
            "n_pendientes",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Referencias pendientes de PDF.",
        ),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de creación.",
        ),
        sa.CheckConstraint(
            "(tipo = 'cientifica') = (tema IS NOT NULL)",
            name=op.f("ck_coleccion_tema_solo_en_cientifica"),
        ),
        sa.CheckConstraint(
            "(tipo = 'personal') = (caso_id IS NOT NULL)",
            name=op.f("ck_coleccion_caso_solo_en_personal"),
        ),
        sa.CheckConstraint(
            "n_incluidas >= 0 AND n_excluidas >= 0 AND n_pendientes >= 0",
            name=op.f("ck_coleccion_conteos_positivos"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coleccion")),
        comment="Colección del corpus: guías (una), científica (una por tema) o personal (una por caso).",
    )
    op.create_index(op.f("ix_coleccion_caso_id"), "coleccion", ["caso_id"], unique=False)
    op.create_index(
        "uq_coleccion_caso_personal",
        "coleccion",
        ["caso_id"],
        unique=True,
        postgresql_where=sa.text("tipo = 'personal'"),
    )
    op.create_index(
        "uq_coleccion_tema_cientifica",
        "coleccion",
        ["tema"],
        unique=True,
        postgresql_where=sa.text("tipo = 'cientifica'"),
    )
    op.create_index(
        "uq_coleccion_unica_guias",
        "coleccion",
        ["tipo"],
        unique=True,
        postgresql_where=sa.text("tipo = 'guias'"),
    )
    op.create_table(
        "configuracion",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column("numero_version", sa.Integer(), nullable=False, comment="Número de versión."),
        sa.Column(
            "parametros",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Parámetros validados por app.administracion.parametros.",
        ),
        sa.Column("comentario", sa.Text(), nullable=False, comment="Motivo del cambio."),
        sa.Column(
            "vigente", sa.Boolean(), server_default="false", nullable=False, comment="Vigente."
        ),
        sa.Column(
            "congelada",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Congelada (RN-21).",
        ),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de creación.",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_configuracion")),
        sa.UniqueConstraint("numero_version", name=op.f("uq_configuracion_numero_version")),
        comment="Parámetros funcionales versionados (RF-23). Se validan con Pydantic.",
    )
    op.create_index(
        "uq_configuracion_una_vigente",
        "configuracion",
        ["vigente"],
        unique=True,
        postgresql_where=sa.text("vigente"),
    )
    op.create_table(
        "caso",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "codigo",
            sa.String(length=32),
            nullable=False,
            comment="Código único del caso (sin datos personales).",
        ),
        sa.Column(
            "tipo_autoria",
            sa.Enum(
                "individual",
                "pareja",
                name="tipo_autoria",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="individual o pareja.",
        ),
        sa.Column(
            "coleccion_cientifica_id",
            sa.UUID(),
            nullable=False,
            comment="Colección científica del tema del caso. La personal es coleccion.caso_id.",
        ),
        sa.Column(
            "norma_citacion",
            sa.String(length=20),
            server_default="IEEE",
            nullable=False,
            comment="Norma de citación del caso, de la lista cerrada configurada (D-12).",
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "habilitado",
                "desactivado",
                name="estado_caso",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            server_default="habilitado",
            nullable=False,
            comment="habilitado o desactivado.",
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora del alta.",
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Último cambio de estado o norma.",
        ),
        sa.CheckConstraint(
            "codigo ~ '^[A-Z0-9][A-Z0-9_-]{1,31}$'", name=op.f("ck_caso_codigo_formato")
        ),
        sa.ForeignKeyConstraint(
            ["coleccion_cientifica_id"],
            ["coleccion.id"],
            name=op.f("fk_caso_coleccion_cientifica_id_coleccion"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_caso")),
        sa.UniqueConstraint("codigo", name=op.f("uq_caso_codigo")),
        comment="Caso de estudio (estudiante o pareja), identificado solo por código (RN-12).",
    )
    op.create_index(
        op.f("ix_caso_coleccion_cientifica_id"), "caso", ["coleccion_cientifica_id"], unique=False
    )
    # Clave circular coleccion.caso_id -> caso (la colección personal), creada tras caso.
    op.create_foreign_key(
        op.f("fk_coleccion_caso_id_caso"),
        "coleccion",
        "caso",
        ["caso_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_table(
        "documento",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "coleccion_id", sa.UUID(), nullable=False, comment="Colección a la que pertenece."
        ),
        sa.Column("titulo", sa.Text(), nullable=True, comment="Título de la obra."),
        sa.Column(
            "autores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
            comment="Autores de la obra publicada (metadato bibliográfico, no participantes).",
        ),
        sa.Column("anio", sa.Integer(), nullable=True, comment="Año de publicación."),
        sa.Column("doi", sa.String(length=255), nullable=True, comment="DOI normalizado."),
        sa.Column("fuente", sa.Text(), nullable=True, comment="Revista, libro o contenedor."),
        sa.Column("idioma", sa.String(length=8), nullable=True, comment="Idioma (ISO 639-1)."),
        sa.Column("licencia", sa.String(length=80), nullable=True, comment="Licencia de uso."),
        sa.Column(
            "url_acceso_abierto",
            sa.Text(),
            nullable=True,
            comment="Mejor ubicación de acceso abierto.",
        ),
        sa.Column(
            "estado_oa",
            sa.Enum(
                "gold",
                "green",
                "hybrid",
                "bronze",
                "closed",
                "desconocido",
                name="estado_oa",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            server_default="desconocido",
            nullable=False,
            comment="Estado de acceso abierto según Unpaywall.",
        ),
        sa.Column(
            "huella_sha256",
            sa.String(length=64),
            nullable=False,
            comment="Huella SHA-256 del PDF, para deduplicar.",
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "activo",
                "retirado",
                "incompleto",
                name="estado_documento",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            server_default="activo",
            nullable=False,
            comment="activo, retirado o incompleto.",
        ),
        sa.Column(
            "motivo_estado",
            sa.Text(),
            nullable=True,
            comment="Motivo si está incompleto o retirado.",
        ),
        sa.Column(
            "origen",
            sa.Enum(
                "ingesta",
                "importacion_o1",
                "aporte",
                name="origen_documento",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="ingesta, importacion_o1 o aporte.",
        ),
        sa.Column("num_paginas", sa.Integer(), nullable=True, comment="Páginas del PDF."),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de indexación.",
        ),
        sa.Column(
            "retirado_en",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Fecha y hora de retiro.",
        ),
        sa.CheckConstraint(
            "huella_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_documento_huella_hex")
        ),
        sa.CheckConstraint(
            "anio IS NULL OR anio BETWEEN 1500 AND 2100", name=op.f("ck_documento_anio_razonable")
        ),
        sa.ForeignKeyConstraint(
            ["coleccion_id"],
            ["coleccion.id"],
            name=op.f("fk_documento_coleccion_id_coleccion"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documento")),
        sa.UniqueConstraint(
            "coleccion_id", "huella_sha256", name=op.f("uq_documento_coleccion_id_huella_sha256")
        ),
        comment="Documento indexado en una colección, con metadatos bibliográficos (Fase 1, 18.2).",
    )
    op.create_index(op.f("ix_documento_coleccion_id"), "documento", ["coleccion_id"], unique=False)
    op.create_index(op.f("ix_documento_doi"), "documento", ["doi"], unique=False)
    op.create_table(
        "cuenta",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "codigo", sa.String(length=40), nullable=False, comment="Código de inicio de sesión."
        ),
        sa.Column(
            "hash_contrasena",
            sa.String(length=255),
            nullable=False,
            comment="Hash Argon2id; nunca la contraseña.",
        ),
        sa.Column(
            "rol",
            sa.Enum("A1", "A2", name="rol", native_enum=False, create_constraint=True, length=40),
            nullable=False,
            comment="A1 (caso) o A2 (investigador).",
        ),
        sa.Column("caso_id", sa.UUID(), nullable=True, comment="Caso de la cuenta A1."),
        sa.Column(
            "intentos_fallidos",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Fallos en la ventana actual.",
        ),
        sa.Column(
            "primer_fallo_en",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Inicio de la ventana de 15 minutos de fallos.",
        ),
        sa.Column(
            "bloqueada_hasta",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Fin del bloqueo temporal.",
        ),
        sa.Column(
            "contrasena_inicial_cambiada",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="La contraseña inicial ya fue reemplazada.",
        ),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora del alta.",
        ),
        sa.CheckConstraint(
            "(rol = 'A1') = (caso_id IS NOT NULL)", name=op.f("ck_cuenta_caso_solo_en_a1")
        ),
        sa.CheckConstraint(
            "codigo ~ '^[A-Z0-9][A-Z0-9_-]{1,39}$'", name=op.f("ck_cuenta_codigo_formato")
        ),
        sa.CheckConstraint("intentos_fallidos >= 0", name=op.f("ck_cuenta_intentos_positivos")),
        sa.ForeignKeyConstraint(
            ["caso_id"], ["caso.id"], name=op.f("fk_cuenta_caso_id_caso"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cuenta")),
        sa.UniqueConstraint("codigo", name=op.f("uq_cuenta_codigo")),
        comment="Cuenta de acceso: A1 (caso) o A2 (investigador).",
    )
    op.create_index(op.f("ix_cuenta_caso_id"), "cuenta", ["caso_id"], unique=False)
    op.create_table(
        "fragmento",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column("documento_id", sa.UUID(), nullable=False, comment="Documento de origen."),
        sa.Column(
            "coleccion_id",
            sa.UUID(),
            nullable=False,
            comment="Colección (copiada del documento para filtrar la recuperación).",
        ),
        sa.Column(
            "orden", sa.Integer(), nullable=False, comment="Posición del fragmento en el documento."
        ),
        sa.Column("texto", sa.Text(), nullable=False, comment="Texto limpio del fragmento."),
        sa.Column(
            "seccion_normalizada",
            sa.Enum(
                "resumen",
                "introduccion",
                "metodos",
                "resultados",
                "discusion",
                "conclusiones",
                "otra",
                name="seccion_normalizada",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Sección IMRaD.",
        ),
        sa.Column(
            "seccion_original",
            sa.Text(),
            nullable=True,
            comment="Título de la sección tal como aparece en el PDF.",
        ),
        sa.Column("pagina_inicio", sa.Integer(), nullable=True, comment="Página inicial."),
        sa.Column("pagina_fin", sa.Integer(), nullable=True, comment="Página final."),
        sa.Column(
            "tokens", sa.Integer(), nullable=False, comment="Número de tokens del fragmento."
        ),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=1024),
            nullable=True,
            comment="Vector bge-m3 normalizado (1 024).",
        ),
        sa.Column(
            "texto_lexico",
            postgresql.TSVECTOR(),
            nullable=True,
            comment="tsvector con configuración simple.",
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de creación.",
        ),
        sa.CheckConstraint(
            "pagina_inicio IS NULL OR pagina_fin IS NULL OR pagina_inicio <= pagina_fin",
            name=op.f("ck_fragmento_paginas_ordenadas"),
        ),
        sa.ForeignKeyConstraint(
            ["coleccion_id"],
            ["coleccion.id"],
            name=op.f("fk_fragmento_coleccion_id_coleccion"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["documento_id"],
            ["documento.id"],
            name=op.f("fk_fragmento_documento_id_documento"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fragmento")),
        sa.UniqueConstraint("documento_id", "orden", name=op.f("uq_fragmento_documento_id_orden")),
        comment="Fragmento IMRaD de un documento, con vector denso y texto léxico.",
    )
    op.create_index(op.f("ix_fragmento_coleccion_id"), "fragmento", ["coleccion_id"], unique=False)
    op.create_index(op.f("ix_fragmento_documento_id"), "fragmento", ["documento_id"], unique=False)
    op.create_table(
        "version_borrador",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column("caso_id", sa.UUID(), nullable=False, comment="Caso dueño."),
        sa.Column(
            "hito",
            sa.String(length=40),
            nullable=False,
            comment="Código del hito, del catálogo de la configuración versionada.",
        ),
        sa.Column(
            "cargada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de la carga.",
        ),
        sa.Column(
            "ruta_archivo",
            sa.Text(),
            nullable=False,
            comment="Ruta interna con nombre aleatorio, fuera de la carpeta pública.",
        ),
        sa.Column(
            "huella_sha256",
            sa.String(length=64),
            nullable=False,
            comment="Huella SHA-256 del archivo.",
        ),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=False, comment="Tamaño del archivo."),
        sa.Column(
            "vigente",
            sa.Boolean(),
            server_default="true",
            nullable=False,
            comment="Versión vigente de su hito.",
        ),
        sa.Column(
            "secciones",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Secciones detectadas con identificadores estables (T12).",
        ),
        sa.Column(
            "metodo_deteccion",
            sa.Enum(
                "estilos",
                "manual",
                name="metodo_deteccion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
            comment="estilos o manual.",
        ),
        sa.CheckConstraint(
            "huella_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_version_borrador_huella_hex")
        ),
        sa.ForeignKeyConstraint(
            ["caso_id"],
            ["caso.id"],
            name=op.f("fk_version_borrador_caso_id_caso"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_version_borrador")),
        sa.UniqueConstraint("id", "caso_id", name=op.f("uq_version_borrador_id_caso_id")),
        comment="Versión del borrador .docx cargada por un caso en un hito (RF-01, RN-09).",
    )
    op.create_index(
        op.f("ix_version_borrador_caso_id"), "version_borrador", ["caso_id"], unique=False
    )
    op.create_index(
        "uq_version_borrador_vigente_por_hito",
        "version_borrador",
        ["caso_id", "hito"],
        unique=True,
        postgresql_where=sa.text("vigente"),
    )
    op.create_table(
        "solicitud",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "caso_id",
            sa.UUID(),
            nullable=False,
            comment="Caso dueño (filtro obligatorio de aislamiento).",
        ),
        sa.Column(
            "version_id",
            sa.UUID(),
            nullable=False,
            comment="Versión del borrador sobre la que se pide.",
        ),
        sa.Column(
            "tipo",
            sa.Enum(
                "estructura",
                "plan_tarea",
                "metodologico",
                "redaccion",
                "evidencia",
                "referencias",
                name="tipo_solicitud",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Uno de los seis tipos.",
        ),
        sa.Column(
            "alcance_tipo",
            sa.Enum(
                "version",
                "seccion",
                "parrafo",
                "consulta",
                name="tipo_alcance",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="version, seccion, parrafo o consulta.",
        ),
        sa.Column(
            "alcance_contenido",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Identificadores de sección o párrafo, o texto de la consulta.",
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "recibida",
                "asignada",
                "recuperando",
                "generando",
                "verificando",
                "reintentando",
                "entregada",
                "no_atendida",
                "rechazada",
                name="estado_solicitud",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            server_default="recibida",
            nullable=False,
            comment="Estado en la cola y entrega.",
        ),
        sa.Column(
            "motivo", sa.Text(), nullable=True, comment="Motivo de rechazo o de no atención."
        ),
        sa.Column(
            "configuracion_id",
            sa.UUID(),
            nullable=False,
            comment="Versión de configuración vigente al crearla (RNF-21).",
        ),
        sa.Column(
            "solicitud_origen_id",
            sa.UUID(),
            nullable=True,
            comment="Solicitud original si es un reenvío.",
        ),
        sa.Column(
            "intentos_tecnicos",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Reintentos técnicos ante el proveedor.",
        ),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de creación.",
        ),
        sa.Column(
            "actualizada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Último cambio de estado.",
        ),
        sa.Column(
            "entregada_en",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Fecha y hora de entrega.",
        ),
        sa.CheckConstraint(
            "intentos_tecnicos BETWEEN 0 AND 3", name=op.f("ck_solicitud_intentos_tecnicos_rango")
        ),
        sa.ForeignKeyConstraint(
            ["caso_id"], ["caso.id"], name=op.f("fk_solicitud_caso_id_caso"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["configuracion_id"],
            ["configuracion.id"],
            name=op.f("fk_solicitud_configuracion_id_configuracion"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["solicitud_origen_id", "caso_id"],
            ["solicitud.id", "solicitud.caso_id"],
            name=op.f("fk_solicitud_solicitud_origen_id_caso_id_solicitud"),
        ),
        sa.ForeignKeyConstraint(
            ["version_id", "caso_id"],
            ["version_borrador.id", "version_borrador.caso_id"],
            name=op.f("fk_solicitud_version_id_caso_id_version_borrador"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solicitud")),
        sa.UniqueConstraint("id", "caso_id", name=op.f("uq_solicitud_id_caso_id")),
        comment="Solicitud tipificada de un caso sobre una versión (RF-02).",
    )
    op.create_index(op.f("ix_solicitud_caso_id"), "solicitud", ["caso_id"], unique=False)
    op.create_index(
        "ix_solicitud_cola",
        "solicitud",
        ["estado", "creada_en"],
        unique=False,
        postgresql_where=sa.text(
            "estado IN ('recibida', 'asignada', 'recuperando', 'generando', 'verificando', 'reintentando')"
        ),
    )
    op.create_index(
        op.f("ix_solicitud_configuracion_id"), "solicitud", ["configuracion_id"], unique=False
    )
    op.create_index(op.f("ix_solicitud_version_id"), "solicitud", ["version_id"], unique=False)
    op.create_table(
        "evento_tecnico",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "solicitud_id", sa.UUID(), nullable=True, comment="Solicitud asociada, si la hay."
        ),
        sa.Column(
            "etapa",
            sa.String(length=60),
            nullable=False,
            comment="Etapa (recuperacion, generacion, ...).",
        ),
        sa.Column(
            "inicio",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Inicio de la etapa.",
        ),
        sa.Column("duracion_ms", sa.Integer(), nullable=False, comment="Duración en milisegundos."),
        sa.Column("proveedor", sa.String(length=60), nullable=True, comment="Proveedor usado."),
        sa.Column(
            "modelo",
            sa.String(length=120),
            nullable=True,
            comment="Identificador fijo del modelo (RN-24).",
        ),
        sa.Column("tokens_entrada", sa.Integer(), nullable=True, comment="Tokens de entrada."),
        sa.Column("tokens_salida", sa.Integer(), nullable=True, comment="Tokens de salida."),
        sa.Column(
            "costo_estimado",
            sa.Numeric(precision=12, scale=6),
            nullable=True,
            comment="Costo estimado en USD.",
        ),
        sa.Column(
            "error", sa.String(length=120), nullable=True, comment="Tipo de error, sin contenido."
        ),
        sa.ForeignKeyConstraint(
            ["solicitud_id"],
            ["solicitud.id"],
            name=op.f("fk_evento_tecnico_solicitud_id_solicitud"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evento_tecnico")),
        comment="Evento técnico por etapa: latencia, tokens, costo y error (separado del registro metodológico).",
    )
    op.create_index(
        op.f("ix_evento_tecnico_solicitud_id"), "evento_tecnico", ["solicitud_id"], unique=False
    )
    op.create_table(
        "fragmento_recuperado",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "caso_id",
            sa.UUID(),
            nullable=False,
            comment="Caso dueño (filtro obligatorio de aislamiento).",
        ),
        sa.Column("solicitud_id", sa.UUID(), nullable=False, comment="Solicitud."),
        sa.Column("fragmento_id", sa.UUID(), nullable=False, comment="Fragmento del corpus."),
        sa.Column(
            "identificador_visible",
            sa.String(length=8),
            nullable=False,
            comment="F1 a Fn, citable por el agente.",
        ),
        sa.Column("puntaje_denso", sa.Float(), nullable=True, comment="Similitud coseno."),
        sa.Column("puntaje_lexico", sa.Float(), nullable=True, comment="Puntaje léxico."),
        sa.Column(
            "puntaje_fusionado", sa.Float(), nullable=True, comment="Fusión por rangos recíprocos."
        ),
        sa.Column(
            "puntaje_reranking", sa.Float(), nullable=True, comment="Puntaje del reordenador."
        ),
        sa.Column(
            "posicion", sa.Integer(), nullable=False, comment="Posición final tras el reranking."
        ),
        sa.CheckConstraint(
            "identificador_visible ~ '^F[1-9][0-9]*$'",
            name=op.f("ck_fragmento_recuperado_identificador_formato"),
        ),
        sa.ForeignKeyConstraint(
            ["caso_id"],
            ["caso.id"],
            name=op.f("fk_fragmento_recuperado_caso_id_caso"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fragmento_id"],
            ["fragmento.id"],
            name=op.f("fk_fragmento_recuperado_fragmento_id_fragmento"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["solicitud_id", "caso_id"],
            ["solicitud.id", "solicitud.caso_id"],
            name=op.f("fk_fragmento_recuperado_solicitud_id_caso_id_solicitud"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fragmento_recuperado")),
        sa.UniqueConstraint(
            "solicitud_id",
            "identificador_visible",
            name=op.f("uq_fragmento_recuperado_solicitud_id_identificador_visible"),
        ),
        comment="Fragmento recuperado para una solicitud, con sus puntajes (RF-10).",
    )
    op.create_index(
        op.f("ix_fragmento_recuperado_caso_id"), "fragmento_recuperado", ["caso_id"], unique=False
    )
    op.create_index(
        op.f("ix_fragmento_recuperado_fragmento_id"),
        "fragmento_recuperado",
        ["fragmento_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fragmento_recuperado_solicitud_id"),
        "fragmento_recuperado",
        ["solicitud_id"],
        unique=False,
    )
    op.create_table(
        "fuente_aportada",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "caso_id",
            sa.UUID(),
            nullable=False,
            comment="Caso dueño (filtro obligatorio de aislamiento).",
        ),
        sa.Column("solicitud_id", sa.UUID(), nullable=False, comment="Solicitud."),
        sa.Column(
            "datos_bibliograficos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Título, autores de la obra y año declarados por el caso.",
        ),
        sa.Column("doi", sa.String(length=255), nullable=True, comment="DOI declarado."),
        sa.Column(
            "existencia",
            sa.Enum(
                "confirmada",
                "no_localizada",
                "no_comprobable",
                name="existencia_fuente",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="confirmada, no_localizada o no_comprobable (RN-18).",
        ),
        sa.Column(
            "metodo_existencia",
            sa.Enum(
                "doi",
                "metadatos",
                name="metodo_existencia",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
            comment="doi o metadatos.",
        ),
        sa.Column(
            "coherencia",
            sa.Enum(
                "coherente",
                "parcial",
                "no_coherente",
                "no_evaluada",
                name="coherencia_fuente",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            server_default="no_evaluada",
            nullable=False,
            comment="Coherencia con la afirmación (informativa).",
        ),
        sa.Column(
            "documento_id",
            sa.UUID(),
            nullable=True,
            comment="Documento indexado en la colección personal, si existe.",
        ),
        sa.Column(
            "aportada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora del aporte.",
        ),
        sa.ForeignKeyConstraint(
            ["caso_id"],
            ["caso.id"],
            name=op.f("fk_fuente_aportada_caso_id_caso"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["documento_id"],
            ["documento.id"],
            name=op.f("fk_fuente_aportada_documento_id_documento"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["solicitud_id", "caso_id"],
            ["solicitud.id", "solicitud.caso_id"],
            name=op.f("fk_fuente_aportada_solicitud_id_caso_id_solicitud"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuente_aportada")),
        comment="Fuente aportada por el caso tras una abstención (RF-13).",
    )
    op.create_index(
        op.f("ix_fuente_aportada_caso_id"), "fuente_aportada", ["caso_id"], unique=False
    )
    op.create_index(
        op.f("ix_fuente_aportada_solicitud_id"), "fuente_aportada", ["solicitud_id"], unique=False
    )
    op.create_table(
        "resultado",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "caso_id",
            sa.UUID(),
            nullable=False,
            comment="Caso dueño (filtro obligatorio de aislamiento).",
        ),
        sa.Column("solicitud_id", sa.UUID(), nullable=False, comment="Solicitud."),
        sa.Column("intento", sa.Integer(), nullable=False, comment="1 o 2 (un solo reintento)."),
        sa.Column(
            "salida",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Salida estructurada validada por tipo.",
        ),
        sa.Column(
            "etiqueta",
            sa.Enum(
                "verificada",
                "con_advertencias",
                "sin_evidencia_suficiente",
                name="etiqueta",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
            comment="verificada, con_advertencias o sin_evidencia_suficiente.",
        ),
        sa.Column(
            "abstencion",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="El agente se abstuvo.",
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de generación.",
        ),
        sa.CheckConstraint("intento IN (1, 2)", name=op.f("ck_resultado_intento_unico_reintento")),
        sa.ForeignKeyConstraint(
            ["caso_id"], ["caso.id"], name=op.f("fk_resultado_caso_id_caso"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["solicitud_id", "caso_id"],
            ["solicitud.id", "solicitud.caso_id"],
            name=op.f("fk_resultado_solicitud_id_caso_id_solicitud"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resultado")),
        sa.UniqueConstraint("id", "caso_id", name=op.f("uq_resultado_id_caso_id")),
        sa.UniqueConstraint(
            "solicitud_id", "intento", name=op.f("uq_resultado_solicitud_id_intento")
        ),
        comment="Salida estructurada de un agente por intento (RN-05).",
    )
    op.create_index(op.f("ix_resultado_caso_id"), "resultado", ["caso_id"], unique=False)
    op.create_index(op.f("ix_resultado_solicitud_id"), "resultado", ["solicitud_id"], unique=False)
    op.create_table(
        "decision",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "caso_id",
            sa.UUID(),
            nullable=False,
            comment="Caso dueño (filtro obligatorio de aislamiento).",
        ),
        sa.Column("resultado_id", sa.UUID(), nullable=False, comment="Resultado."),
        sa.Column(
            "opcion",
            sa.Enum(
                "aceptar",
                "modificar",
                "rechazar",
                "continuar",
                "aportar",
                name="opcion_decision",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="aceptar, modificar, rechazar, continuar o aportar.",
        ),
        sa.Column(
            "decidida_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de la decisión.",
        ),
        sa.Column(
            "decision_reemplazada_id",
            sa.UUID(),
            nullable=True,
            comment="Decisión anterior a la que reemplaza (se conserva).",
        ),
        sa.ForeignKeyConstraint(
            ["caso_id"], ["caso.id"], name=op.f("fk_decision_caso_id_caso"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["decision_reemplazada_id"],
            ["decision.id"],
            name=op.f("fk_decision_decision_reemplazada_id_decision"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resultado_id", "caso_id"],
            ["resultado.id", "resultado.caso_id"],
            name=op.f("fk_decision_resultado_id_caso_id_resultado"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decision")),
        sa.UniqueConstraint(
            "decision_reemplazada_id", name=op.f("uq_decision_decision_reemplazada_id")
        ),
        comment="Decisión del caso sobre un resultado; un cambio crea otra fila (RN-08).",
    )
    op.create_index(op.f("ix_decision_caso_id"), "decision", ["caso_id"], unique=False)
    op.create_index(op.f("ix_decision_resultado_id"), "decision", ["resultado_id"], unique=False)
    op.create_table(
        "verificacion",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Identificador interno (UUID).",
        ),
        sa.Column(
            "caso_id",
            sa.UUID(),
            nullable=False,
            comment="Caso dueño (filtro obligatorio de aislamiento).",
        ),
        sa.Column("resultado_id", sa.UUID(), nullable=False, comment="Resultado."),
        sa.Column("intento", sa.Integer(), nullable=False, comment="Intento verificado (1 o 2)."),
        sa.Column(
            "c1_esquema",
            sa.Enum(
                "superada",
                "fallida",
                "no_comprobable",
                "no_aplica",
                name="c1_esquema",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Comprobación 1: esquema del tipo.",
        ),
        sa.Column(
            "c2_limites",
            sa.Enum(
                "superada",
                "fallida",
                "no_comprobable",
                "no_aplica",
                name="c2_limites",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Comprobación 2: límites por tipo (no reescritura, números, extensión).",
        ),
        sa.Column(
            "c3_citas",
            sa.Enum(
                "superada",
                "fallida",
                "no_comprobable",
                "no_aplica",
                name="c3_citas",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Comprobación 3: toda cita existe entre los fragmentos recuperados.",
        ),
        sa.Column(
            "c4_existencia",
            sa.Enum(
                "superada",
                "fallida",
                "no_comprobable",
                "no_aplica",
                name="c4_existencia",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Comprobación 4: existencia de las fuentes (no_comprobable si el servicio cae).",
        ),
        sa.Column(
            "c5_acceso_abierto",
            sa.Enum(
                "superada",
                "fallida",
                "no_comprobable",
                "no_aplica",
                name="c5_acceso_abierto",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Comprobación 5: acceso abierto de las fuentes recomendadas.",
        ),
        sa.Column(
            "c6_fidelidad",
            sa.Enum(
                "superada",
                "fallida",
                "no_comprobable",
                "no_aplica",
                name="c6_fidelidad",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
            comment="Comprobación 6: fidelidad frente al umbral.",
        ),
        sa.Column(
            "fidelidad", sa.Float(), nullable=True, comment="Afirmaciones respaldadas sobre total."
        ),
        sa.Column(
            "umbral_fidelidad",
            sa.Float(),
            nullable=True,
            comment="Umbral aplicado (de la configuración).",
        ),
        sa.Column("afirmaciones_total", sa.Integer(), nullable=True, comment="Afirmaciones."),
        sa.Column("afirmaciones_respaldadas", sa.Integer(), nullable=True, comment="Respaldadas."),
        sa.Column(
            "afirmaciones_no_respaldadas", sa.Integer(), nullable=True, comment="No respaldadas."
        ),
        sa.Column(
            "afirmaciones_contradichas", sa.Integer(), nullable=True, comment="Contradichas."
        ),
        sa.Column(
            "motivos_falla",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
            comment="Motivos usados en el reintento.",
        ),
        sa.Column(
            "aprobada",
            sa.Boolean(),
            nullable=False,
            comment="Todas las comprobaciones aplicables superadas.",
        ),
        sa.Column(
            "modelo_evaluador",
            sa.String(length=120),
            nullable=True,
            comment="Identificador fijo del modelo evaluador (RN-24).",
        ),
        sa.Column(
            "verificada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Fecha y hora de la verificación.",
        ),
        sa.CheckConstraint(
            "fidelidad IS NULL OR fidelidad BETWEEN 0 AND 1",
            name=op.f("ck_verificacion_fidelidad_rango"),
        ),
        sa.ForeignKeyConstraint(
            ["caso_id"], ["caso.id"], name=op.f("fk_verificacion_caso_id_caso"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["resultado_id", "caso_id"],
            ["resultado.id", "resultado.caso_id"],
            name=op.f("fk_verificacion_resultado_id_caso_id_resultado"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verificacion")),
        sa.UniqueConstraint(
            "resultado_id", "intento", name=op.f("uq_verificacion_resultado_id_intento")
        ),
        comment="Verificación de un resultado por intento: seis comprobaciones (Fase 1, 6.7).",
    )
    op.create_index(op.f("ix_verificacion_caso_id"), "verificacion", ["caso_id"], unique=False)
    op.create_index(
        op.f("ix_verificacion_resultado_id"), "verificacion", ["resultado_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_verificacion_resultado_id"), table_name="verificacion")
    op.drop_index(op.f("ix_verificacion_caso_id"), table_name="verificacion")
    op.drop_table("verificacion")
    op.drop_index(op.f("ix_decision_resultado_id"), table_name="decision")
    op.drop_index(op.f("ix_decision_caso_id"), table_name="decision")
    op.drop_table("decision")
    op.drop_index(op.f("ix_resultado_solicitud_id"), table_name="resultado")
    op.drop_index(op.f("ix_resultado_caso_id"), table_name="resultado")
    op.drop_table("resultado")
    op.drop_index(op.f("ix_fuente_aportada_solicitud_id"), table_name="fuente_aportada")
    op.drop_index(op.f("ix_fuente_aportada_caso_id"), table_name="fuente_aportada")
    op.drop_table("fuente_aportada")
    op.drop_index(op.f("ix_fragmento_recuperado_solicitud_id"), table_name="fragmento_recuperado")
    op.drop_index(op.f("ix_fragmento_recuperado_fragmento_id"), table_name="fragmento_recuperado")
    op.drop_index(op.f("ix_fragmento_recuperado_caso_id"), table_name="fragmento_recuperado")
    op.drop_table("fragmento_recuperado")
    op.drop_index(op.f("ix_evento_tecnico_solicitud_id"), table_name="evento_tecnico")
    op.drop_table("evento_tecnico")
    op.drop_index(op.f("ix_solicitud_version_id"), table_name="solicitud")
    op.drop_index(op.f("ix_solicitud_configuracion_id"), table_name="solicitud")
    op.drop_index(
        "ix_solicitud_cola",
        table_name="solicitud",
        postgresql_where=sa.text(
            "estado IN ('recibida', 'asignada', 'recuperando', 'generando', 'verificando', 'reintentando')"
        ),
    )
    op.drop_index(op.f("ix_solicitud_caso_id"), table_name="solicitud")
    op.drop_table("solicitud")
    op.drop_index(
        "uq_version_borrador_vigente_por_hito",
        table_name="version_borrador",
        postgresql_where=sa.text("vigente"),
    )
    op.drop_index(op.f("ix_version_borrador_caso_id"), table_name="version_borrador")
    op.drop_table("version_borrador")
    op.drop_index(op.f("ix_fragmento_documento_id"), table_name="fragmento")
    op.drop_index(op.f("ix_fragmento_coleccion_id"), table_name="fragmento")
    op.drop_table("fragmento")
    op.drop_index(op.f("ix_cuenta_caso_id"), table_name="cuenta")
    op.drop_table("cuenta")
    op.drop_index(op.f("ix_documento_doi"), table_name="documento")
    op.drop_index(op.f("ix_documento_coleccion_id"), table_name="documento")
    op.drop_table("documento")
    op.drop_constraint(op.f("fk_coleccion_caso_id_caso"), "coleccion", type_="foreignkey")
    op.drop_index(op.f("ix_caso_coleccion_cientifica_id"), table_name="caso")
    op.drop_table("caso")
    op.drop_index(
        "uq_configuracion_una_vigente",
        table_name="configuracion",
        postgresql_where=sa.text("vigente"),
    )
    op.drop_table("configuracion")
    op.drop_index(
        "uq_coleccion_unica_guias",
        table_name="coleccion",
        postgresql_where=sa.text("tipo = 'guias'"),
    )
    op.drop_index(
        "uq_coleccion_tema_cientifica",
        table_name="coleccion",
        postgresql_where=sa.text("tipo = 'cientifica'"),
    )
    op.drop_index(
        "uq_coleccion_caso_personal",
        table_name="coleccion",
        postgresql_where=sa.text("tipo = 'personal'"),
    )
    op.drop_index(op.f("ix_coleccion_caso_id"), table_name="coleccion")
    op.drop_table("coleccion")
    op.drop_table("cache_metadatos")
