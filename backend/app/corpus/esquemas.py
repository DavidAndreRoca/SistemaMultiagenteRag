"""Datos del canal de extracción de PDF (T09; Fase 1, 18.2 a 18.4).

``DocumentoProcesado`` es lo que el canal entrega a la indexación (T10). El estado y el
motivo son explícitos: un PDF escaneado, ilegible o con texto insuficiente nunca produce
fragmentos silenciosos (criterio de T09).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.bd.enumeraciones import SeccionNormalizada

PATRON_SHA256 = r"^[0-9a-f]{64}$"


class _Inmutable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EstadoProcesamiento(StrEnum):
    PROCESADO = "procesado"
    INCOMPLETO = "incompleto"  # se indexa solo si el investigador lo confirma (18.3)
    EXCLUIDO = "excluido"  # no se indexa; se registra con su motivo


class MotivoExclusion(StrEnum):
    NO_ES_PDF = "no_es_pdf"
    PDF_ILEGIBLE = "pdf_ilegible"
    PDF_CIFRADO = "pdf_cifrado"
    EXCEDE_TAMANO = "excede_tamano"
    EXCEDE_PAGINAS = "excede_paginas"
    SIN_CAPA_DE_TEXTO = "sin_capa_de_texto"


class MotivoIncompleto(StrEnum):
    TEXTO_INSUFICIENTE = "texto_insuficiente"
    SIN_SECCIONES_IMRAD = "sin_secciones_imrad"


MENSAJES_MOTIVO: dict[MotivoExclusion | MotivoIncompleto, str] = {
    MotivoExclusion.NO_ES_PDF: "El archivo no es un PDF.",
    MotivoExclusion.PDF_ILEGIBLE: "El PDF está dañado o no se puede leer.",
    MotivoExclusion.PDF_CIFRADO: "El PDF está protegido con contraseña de apertura.",
    MotivoExclusion.EXCEDE_TAMANO: "El PDF supera el tamaño máximo permitido.",
    MotivoExclusion.EXCEDE_PAGINAS: "El PDF supera el número máximo de páginas.",
    MotivoExclusion.SIN_CAPA_DE_TEXTO: (
        "El PDF parece escaneado: no tiene capa de texto. En el corpus científico se excluye."
    ),
    MotivoIncompleto.TEXTO_INSUFICIENTE: ("Se extrajo menos texto del esperado para un artículo."),
    MotivoIncompleto.SIN_SECCIONES_IMRAD: (
        "No se identificó ninguna sección IMRaD (introducción, métodos, resultados,"
        " discusión o conclusiones)."
    ),
}


class Autor(_Inmutable):
    """Autor de la obra publicada (metadato bibliográfico, no un participante)."""

    nombres: str | None = None
    apellidos: str = Field(min_length=1)


class MetadatosCabecera(_Inmutable):
    """Metadatos bibliográficos de la cabecera, extraídos con GROBID (sin consolidar)."""

    titulo: str | None = None
    autores: list[Autor] = Field(default_factory=list)
    anio: int | None = Field(default=None, ge=1500, le=2100)
    doi: str | None = None
    revista: str | None = None
    idioma: str | None = Field(default=None, max_length=8)


class FragmentoProcesado(_Inmutable):
    orden: int = Field(ge=0)
    texto: str = Field(min_length=1)
    seccion_normalizada: SeccionNormalizada
    seccion_original: str | None
    pagina_inicio: int = Field(ge=1)
    pagina_fin: int = Field(ge=1)
    tokens: int = Field(ge=1)

    @model_validator(mode="after")
    def _paginas_ordenadas(self) -> Self:
        if self.pagina_inicio > self.pagina_fin:
            raise ValueError("pagina_inicio no puede ser mayor que pagina_fin")
        return self


class DocumentoProcesado(_Inmutable):
    estado: EstadoProcesamiento
    motivo_exclusion: MotivoExclusion | None = None
    motivos_incompleto: list[MotivoIncompleto] = Field(default_factory=list)
    huella_archivo: str = Field(pattern=PATRON_SHA256, description="SHA-256 del archivo.")
    huella_texto: str | None = Field(
        default=None,
        pattern=PATRON_SHA256,
        description="SHA-256 del texto normalizado, para deduplicar (18.9).",
    )
    num_paginas: int | None = Field(default=None, ge=0)
    palabras: int = Field(default=0, ge=0, description="Palabras del texto que se segmenta.")
    secciones: list[SeccionNormalizada] = Field(default_factory=list)
    metadatos: MetadatosCabecera | None = None
    fragmentos: list[FragmentoProcesado] = Field(default_factory=list)

    @model_validator(mode="after")
    def _estado_coherente(self) -> Self:
        if self.estado is EstadoProcesamiento.EXCLUIDO:
            if self.motivo_exclusion is None or self.fragmentos or self.motivos_incompleto:
                raise ValueError("un documento excluido lleva motivo y ningún fragmento")
            return self
        if self.motivo_exclusion is not None:
            raise ValueError("solo un documento excluido lleva motivo de exclusión")
        if self.estado is EstadoProcesamiento.INCOMPLETO and not self.motivos_incompleto:
            raise ValueError("un documento incompleto lleva al menos un motivo")
        if self.estado is EstadoProcesamiento.PROCESADO and self.motivos_incompleto:
            raise ValueError("un documento procesado no lleva motivos de incompleto")
        if self.estado is EstadoProcesamiento.PROCESADO and not self.fragmentos:
            raise ValueError("un documento procesado tiene fragmentos")
        if [f.orden for f in self.fragmentos] != list(range(len(self.fragmentos))):
            raise ValueError("los fragmentos se numeran de 0 a n-1")
        return self

    @property
    def mensajes(self) -> list[str]:
        """Motivos legibles para el investigador."""
        motivos: list[MotivoExclusion | MotivoIncompleto] = (
            [self.motivo_exclusion] if self.motivo_exclusion else list(self.motivos_incompleto)
        )
        return [MENSAJES_MOTIVO[m] for m in motivos]
