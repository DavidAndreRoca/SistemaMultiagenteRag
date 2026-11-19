"""Ajustes del servicio, leídos de variables de entorno y validados al arrancar."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ErrorAjustes(RuntimeError):
    pass


class AjustesServicio(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    directorio_modelos: Path = Field(Path("/modelos"), validation_alias="DIRECTORIO_MODELOS")
    puerto: int = Field(8000, ge=1, le=65535, validation_alias="PUERTO")
    # Textos por pasada del modelo: acota la memoria (T08, tareas técnicas).
    tamano_lote: int = Field(16, ge=1, le=256, validation_alias="TAMANO_LOTE")
    # Inferencias simultáneas: con 1, dos integrantes no saturan la instancia.
    max_concurrencia: int = Field(1, ge=1, le=8, validation_alias="MAX_CONCURRENCIA")
    # Espera en cola antes de responder 503 "servicio_ocupado".
    espera_maxima_s: float = Field(120, gt=0, le=900, validation_alias="ESPERA_MAXIMA_S")
    max_textos: int = Field(128, ge=1, le=1024, validation_alias="MAX_TEXTOS")
    # Un texto (o un par consulta y texto) más largo se rechaza: nunca se trunca en silencio.
    max_tokens: int = Field(1024, ge=16, le=8192, validation_alias="MAX_TOKENS")
    # Hilos de inferencia de PyTorch; 0 usa todos los procesadores del contenedor (T10-02).
    hilos: int = Field(0, ge=0, le=64, validation_alias="HILOS_INFERENCIA")
    # El reordenador se carga al primer /reordenar: la ingesta solo embebe (T10-02).
    reordenador_perezoso: bool = Field(True, validation_alias="REORDENADOR_PEREZOSO")

    @property
    def max_caracteres(self) -> int:
        """Corte barato antes de tokenizar: ningún token del modelo supera 16 caracteres."""
        return self.max_tokens * 16


def cargar_ajustes(entorno: Mapping[str, str] | None = None) -> AjustesServicio:
    origen = dict(os.environ if entorno is None else entorno)
    try:
        return AjustesServicio.model_validate(origen)
    except ValidationError as error:
        problemas = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors()
        )
        raise ErrorAjustes(f"Configuración inválida: {problemas}") from None
