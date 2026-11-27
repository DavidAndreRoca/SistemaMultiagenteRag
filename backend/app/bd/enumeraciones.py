"""Valores permitidos del esquema. Son también el contrato de la API y del registro."""

from __future__ import annotations

from enum import StrEnum


class TipoAutoria(StrEnum):
    INDIVIDUAL = "individual"
    PAREJA = "pareja"


class EstadoCaso(StrEnum):
    HABILITADO = "habilitado"
    DESACTIVADO = "desactivado"


class TipoColeccion(StrEnum):
    GUIAS = "guias"
    CIENTIFICA = "cientifica"
    PERSONAL = "personal"


class EstadoDocumento(StrEnum):
    ACTIVO = "activo"
    RETIRADO = "retirado"
    INCOMPLETO = "incompleto"


class OrigenDocumento(StrEnum):
    INGESTA = "ingesta"
    IMPORTACION_O1 = "importacion_o1"
    APORTE = "aporte"


class ObjetoExclusion(StrEnum):
    """Qué se excluyó del corpus: un archivo subido o una referencia (importador, T15)."""

    ARCHIVO = "archivo"
    REFERENCIA = "referencia"


class MotivoExclusionCorpus(StrEnum):
    """Motivo de exclusión del corpus (RF-15, CP-21; Fase 1, 18.3 y 18.9)."""

    NO_ES_PDF = "no_es_pdf"
    PDF_ILEGIBLE = "pdf_ilegible"
    PDF_CIFRADO = "pdf_cifrado"
    EXCEDE_TAMANO = "excede_tamano"
    EXCEDE_PAGINAS = "excede_paginas"
    SIN_CAPA_DE_TEXTO = "sin_capa_de_texto"
    DUPLICADO = "duplicado"
    SIN_ACCESO_ABIERTO = "sin_acceso_abierto"
    # Referencias del artículo O1 (T15)
    NO_LOCALIZADA = "no_localizada"  # los servicios respondieron y no hay coincidencia
    SIN_DOI = "sin_doi"  # localizada sin DOI: no se puede comprobar el acceso abierto
    DOI_INVALIDO = "doi_invalido"  # lista de DOI: la línea no tiene forma de DOI


class OrigenImportacion(StrEnum):
    """Formato del artículo O1 o lista de DOI (T15-01, apartado 2)."""

    PDF = "pdf"
    DOCX = "docx"
    DOI = "doi"


class EstadoImportacion(StrEnum):
    EN_COLA = "en_cola"
    EN_PROCESO = "en_proceso"
    TERMINADA = "terminada"
    INTERRUMPIDA = "interrumpida"  # la API se reinició durante la importación
    FALLIDA = "fallida"  # no se pudieron extraer las referencias


class EstadoReferencia(StrEnum):
    """Estado de una referencia del artículo O1 en la colección del tema (T15)."""

    INCLUIDA = "incluida"  # su PDF está en la colección
    PENDIENTE_PDF = "pendiente_pdf"  # de acceso abierto, el investigador sube el PDF
    EXCLUIDA = "excluida"  # con motivo (no localizada, sin acceso abierto...)
    NO_COMPROBABLE = "no_comprobable"  # un servicio no respondió (RN-18): se reintenta


class EstadoAccesoAbierto(StrEnum):
    """Estados de Unpaywall más ``desconocido`` (aún no consultado)."""

    GOLD = "gold"
    GREEN = "green"
    HYBRID = "hybrid"
    BRONZE = "bronze"
    CLOSED = "closed"
    DESCONOCIDO = "desconocido"


class SeccionNormalizada(StrEnum):
    RESUMEN = "resumen"
    INTRODUCCION = "introduccion"
    METODOS = "metodos"
    RESULTADOS = "resultados"
    DISCUSION = "discusion"
    CONCLUSIONES = "conclusiones"
    OTRA = "otra"


class MetodoDeteccionSecciones(StrEnum):
    ESTILOS = "estilos"
    MANUAL = "manual"


class TipoSolicitud(StrEnum):
    """Los seis tipos de solicitud (insumos de T04, tabla 3) y el agente que los atiende."""

    REVISION_ESTRUCTURA = "revision_estructura"  # D1, CU-03
    PLAN_TAREA = "plan_tarea"  # D1, CU-04
    REVISION_METODOLOGICA = "revision_metodologica"  # D2, CU-05
    PROPUESTA_REDACCION = "propuesta_redaccion"  # D3, CU-06
    BUSQUEDA_EVIDENCIA = "busqueda_evidencia"  # D4, CU-07
    VERIFICACION_REFERENCIAS = "verificacion_referencias"  # D4, CU-08


class TipoAlcance(StrEnum):
    """RF-02 define seccion, fragmento y consulta; hito y version se deducen de RF-05 y RF-09."""

    SECCION = "seccion"
    HITO = "hito"
    FRAGMENTO = "fragmento"
    CONSULTA = "consulta"
    VERSION = "version"


# Alcances admitidos por tipo (insumos de T04, tabla 3). La base lo impone con un CHECK.
ALCANCES_ADMITIDOS: dict[TipoSolicitud, frozenset[TipoAlcance]] = {
    TipoSolicitud.REVISION_ESTRUCTURA: frozenset({TipoAlcance.SECCION}),
    TipoSolicitud.PLAN_TAREA: frozenset({TipoAlcance.HITO}),
    TipoSolicitud.REVISION_METODOLOGICA: frozenset({TipoAlcance.SECCION}),
    TipoSolicitud.PROPUESTA_REDACCION: frozenset({TipoAlcance.FRAGMENTO}),
    TipoSolicitud.BUSQUEDA_EVIDENCIA: frozenset({TipoAlcance.CONSULTA, TipoAlcance.FRAGMENTO}),
    TipoSolicitud.VERIFICACION_REFERENCIAS: frozenset({TipoAlcance.VERSION}),
}

# Alcances que señalan una parte elegida o un texto, y por eso exigen ``alcance_ref``.
ALCANCES_CON_REFERENCIA = frozenset(
    {TipoAlcance.SECCION, TipoAlcance.FRAGMENTO, TipoAlcance.CONSULTA}
)


class EstadoSolicitud(StrEnum):
    RECIBIDA = "recibida"
    ASIGNADA = "asignada"
    RECUPERANDO = "recuperando"
    GENERANDO = "generando"
    VERIFICANDO = "verificando"
    REINTENTANDO = "reintentando"
    ENTREGADA = "entregada"
    NO_ATENDIDA = "no_atendida"
    RECHAZADA = "rechazada"


class Etiqueta(StrEnum):
    VERIFICADA = "verificada"
    CON_ADVERTENCIAS = "con_advertencias"
    SIN_EVIDENCIA_SUFICIENTE = "sin_evidencia_suficiente"


class OpcionDecision(StrEnum):
    ACEPTAR = "aceptar"
    MODIFICAR = "modificar"
    RECHAZAR = "rechazar"
    CONTINUAR = "continuar"
    APORTAR = "aportar"


class ExistenciaFuente(StrEnum):
    CONFIRMADA = "confirmada"
    NO_LOCALIZADA = "no_localizada"
    NO_COMPROBABLE = "no_comprobable"


class MetodoExistencia(StrEnum):
    DOI = "doi"
    METADATOS = "metadatos"


class MetodoComprobacionFuentes(StrEnum):
    """Método de la comprobación 4 de una verificación (Fase 1, 6.7, campo ``metodo``).

    ``mixto`` cuando unas fuentes se confirmaron por DOI y otras por metadatos.
    """

    DOI = "doi"
    METADATOS = "metadatos"
    MIXTO = "mixto"


class CoherenciaFuente(StrEnum):
    COHERENTE = "coherente"
    PARCIAL = "parcial"
    NO_COHERENTE = "no_coherente"
    NO_EVALUADA = "no_evaluada"


class IndexacionAporte(StrEnum):
    """Qué pasó con una fuente aportada en la colección personal (T32; CP-14 a CP-17)."""

    INDEXADA = "indexada"
    YA_INDEXADA = "ya_indexada"  # ya estaba en la colección: no se duplica (CP-17)
    NO_INDEXADA = "no_indexada"  # existencia no confirmada, sin texto o servicio caído


class Rol(StrEnum):
    """A1: caso (estudiante o pareja); A2: investigador."""

    CASO = "A1"
    INVESTIGADOR = "A2"
