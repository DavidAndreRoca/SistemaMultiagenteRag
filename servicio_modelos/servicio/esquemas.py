"""Contrato HTTP del servicio. El cliente de la API (``app/inferencia``) lo replica."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SolicitudEmbeber(_Estricto):
    textos: list[str] = Field(min_length=1)


class SolicitudReordenar(_Estricto):
    consulta: str = Field(min_length=1)
    textos: list[str] = Field(min_length=1)


class IdentidadModelo(BaseModel):
    modelo: str = Field(examples=["BAAI/bge-m3"])
    revision: str = Field(description="Commit exacto del repositorio del modelo (RNF-21)")


class RespuestaEmbeber(IdentidadModelo):
    dimension: int
    vectores: list[list[float]]


class RespuestaReordenar(IdentidadModelo):
    puntajes: list[float] = Field(description="Uno por texto, en el orden recibido; 0 a 1")


class ModeloCargado(IdentidadModelo):
    tipo: str
    licencia: str


class Memoria(BaseModel):
    residente_mb: float | None = None
    pico_mb: float | None = None


class RespuestaSalud(BaseModel):
    estado: str
    version: str
    modelos: list[ModeloCargado]
    memoria: Memoria
    max_textos: int
    max_tokens: int
    tamano_lote: int
    max_concurrencia: int


class RespuestaError(BaseModel):
    codigo: str
    mensaje: str
    detalle: Any | None = None
    incidencia_id: str
