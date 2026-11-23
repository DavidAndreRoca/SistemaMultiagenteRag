"""Esquemas de salida de los seis tipos de solicitud (Fase 1, tablas 12 a 15; T18-01).

* Estrictos: sin campos extra, con longitudes máximas.
* Citas: identificadores ``F<n>`` de los fragmentos recuperados, al menos uno por
  afirmación, hallazgo, tarea o cambio.
* RN-17: ningún esquema que produce el modelo tiene un campo para referencias, fuentes o
  documentos. Las fuentes las arma el sistema desde los fragmentos citados.

``VerificacionReferencias`` no la produce un modelo: es la salida determinista de T20.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.bd.enumeraciones import TipoSolicitud

PATRON_FRAGMENTO = r"^F[1-9][0-9]{0,3}$"
Cita = Annotated[str, Field(pattern=PATRON_FRAGMENTO)]
Citas = Annotated[list[Cita], Field(min_length=1, max_length=12)]
TextoCorto = Annotated[str, Field(min_length=1, max_length=300)]
Texto = Annotated[str, Field(min_length=1, max_length=1200)]
Notas = Annotated[list[Texto], Field(max_length=8)]


class _Salida(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Severidad(StrEnum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class IndicadorEstructural(StrEnum):
    """Tabla 12: indicadores que orienta el agente estructural (D1)."""

    ALINEACION = "alineacion_problema_objetivos_hipotesis"
    SECUENCIA = "secuencia_logica_discursiva"
    COHESION = "cohesion_entre_apartados"


class IndicadorMetodologico(StrEnum):
    """Tabla 13: indicadores que orienta el agente metodológico (D2)."""

    DISENO = "justificacion_del_diseno"
    INSTRUMENTOS = "validez_de_tecnicas_e_instrumentos"
    ANALISIS = "precision_del_analisis_de_datos"


class TipoCambio(StrEnum):
    """Tabla 14: indicadores que orienta el agente estilístico (D3)."""

    REGISTRO = "registro_formal"
    FLUIDEZ = "fluidez_y_precision_lexica"
    GRAMATICA = "correccion_gramatical_y_claridad"


class HallazgoEstructural(_Salida):
    indicador: IndicadorEstructural
    ubicacion: TextoCorto  # identificador de párrafo o sección del borrador
    descripcion: Texto
    severidad: Severidad
    recomendacion: Texto
    citas: Citas


class HallazgoMetodologico(_Salida):
    indicador: IndicadorMetodologico
    ubicacion: TextoCorto
    descripcion: Texto
    severidad: Severidad
    recomendacion: Texto
    citas: Citas


class RevisionEstructura(_Salida):
    hallazgos: list[HallazgoEstructural] = Field(max_length=15)
    fortalezas: list[Texto] = Field(max_length=8)
    notas_para_el_estudiante: Notas


class Tarea(_Salida):
    orden: int = Field(ge=1, le=30)
    tarea: Texto
    criterio_de_logro: Texto
    citas: Citas


class PlanTarea(_Salida):
    hito: TextoCorto
    tareas: list[Tarea] = Field(min_length=1, max_length=20)
    notas_para_el_estudiante: Notas


class RevisionMetodologica(_Salida):
    hallazgos: list[HallazgoMetodologico] = Field(max_length=15)
    preguntas_al_estudiante: list[Texto] = Field(max_length=10)
    notas_para_el_estudiante: Notas


class Cambio(_Salida):
    tipo: TipoCambio
    antes: Texto
    despues: Texto
    razon: Texto
    citas: Citas


class PropuestaRedaccion(_Salida):
    original: Annotated[str, Field(min_length=1, max_length=4000)]
    propuesta: Annotated[str, Field(min_length=1, max_length=4000)]
    cambios: list[Cambio] = Field(max_length=20)
    notas_para_el_estudiante: Notas


class Afirmacion(_Salida):
    afirmacion: Texto
    citas: Citas


class BusquedaEvidencia(_Salida):
    respuesta: list[Afirmacion] = Field(min_length=1, max_length=12)
    evidencia_divergente: list[Afirmacion] = Field(max_length=8)
    notas_para_el_estudiante: Notas


# --- Salida determinista de la verificación de referencias (T20), no del modelo ---


class EstadoReferencia(StrEnum):
    VERIFICADA = "verificada"
    CON_DISCREPANCIAS = "con_discrepancias"
    NO_LOCALIZADA = "no_localizada"
    NO_COMPROBABLE = "no_comprobable"  # RN-18: un servicio no respondió


class Discrepancia(_Salida):
    campo: TextoCorto
    valor_borrador: str | None = None
    valor_fuente: str | None = None


class ReferenciaVerificada(_Salida):
    indice: int = Field(ge=1)
    texto_original: Annotated[str, Field(max_length=2000)]  # la del estudiante, extraída
    estado: EstadoReferencia
    metodo: Literal["doi", "metadatos"] | None = None
    discrepancias: list[Discrepancia] = Field(default_factory=list)
    doi_encontrado: str | None = None


class VerificacionReferencias(_Salida):
    referencias: list[ReferenciaVerificada]
    citas_sin_entrada: list[TextoCorto] = Field(default_factory=list)
    entradas_no_citadas: list[int] = Field(default_factory=list)


ESQUEMAS: dict[TipoSolicitud, type[BaseModel]] = {
    TipoSolicitud.REVISION_ESTRUCTURA: RevisionEstructura,
    TipoSolicitud.PLAN_TAREA: PlanTarea,
    TipoSolicitud.REVISION_METODOLOGICA: RevisionMetodologica,
    TipoSolicitud.PROPUESTA_REDACCION: PropuestaRedaccion,
    TipoSolicitud.BUSQUEDA_EVIDENCIA: BusquedaEvidencia,
    TipoSolicitud.VERIFICACION_REFERENCIAS: VerificacionReferencias,
}

# Los que produce un modelo de lenguaje: sin campos de referencias (RN-17).
GENERADOS_POR_MODELO = frozenset(ESQUEMAS) - {TipoSolicitud.VERIFICACION_REFERENCIAS}
