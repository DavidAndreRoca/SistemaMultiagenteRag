"""Tipos de la recuperación y la suficiencia (T16-01)."""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

AVISO_SIN_EVIDENCIA = "Sin evidencia suficiente"


class _Inmutable(BaseModel):
    model_config = ConfigDict(frozen=True)


class Candidato(_Inmutable):
    """Un fragmento con los puntajes de cada etapa (``fragmento_recuperado``)."""

    fragmento_id: uuid.UUID
    puntaje_denso: float | None = None
    puntaje_lexico: float | None = None
    puntaje_fusionado: float
    puntaje_reranking: float | None = None


class FragmentoContexto(_Inmutable):
    """Fragmento numerado del contexto cerrado: lo único que un agente puede citar."""

    identificador: str = Field(pattern=r"^F[1-9][0-9]*$")
    posicion: int = Field(ge=1)
    candidato: Candidato
    texto: str
    tokens: int
    documento_id: uuid.UUID
    titulo: str | None
    seccion: str
    pagina_inicio: int | None
    pagina_fin: int | None
    incompleto: bool  # el documento está incompleto y lo confirmó el investigador (18.3)


class Recuperacion(_Inmutable):
    consulta_tokens_estimados: int
    colecciones: int
    candidatos_densos: int
    candidatos_lexicos: int
    reordenados: int
    fragmentos: list[FragmentoContexto]
    duracion_recuperacion_ms: int
    duracion_reranking_ms: int


class PasoSuficiencia(StrEnum):
    UMBRAL = "umbral"  # paso 1: N fragmentos con puntaje >= tau
    MODELO = "modelo"  # paso 2: juicio del modelo


class JuicioSuficiencia(BaseModel):
    """Salida estructurada del paso 2 (18.6): ``{suficiente, motivo}``."""

    model_config = ConfigDict(extra="forbid")

    suficiente: bool
    motivo: str = Field(min_length=1, max_length=600)


class DecisionSuficiencia(_Inmutable):
    suficiente: bool
    paso: PasoSuficiencia
    motivo: str
    sobre_umbral: int  # fragmentos con puntaje >= tau
    instruccion: str | None = None  # agente/version del juicio, si llegó al paso 2
    proveedor: str | None = None
    modelo: str | None = None

    @property
    def aviso(self) -> str | None:
        return None if self.suficiente else AVISO_SIN_EVIDENCIA
