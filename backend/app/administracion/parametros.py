"""Esquema validado de los parámetros funcionales (tabla ``configuracion``).

Los nombres y los valores iniciales salen de los insumos de T04 (apartado 4) y de la
especificación de la Fase 1 (6.3, 6.7, 18.4 y 18.6). La versión 1 es provisional: T34
recalibra la recuperación y la ventana, y T35 completa el esquema. Los modelos, sus
límites y precios y las versiones de las instrucciones llegan en T17 (migración 0012).
Ningún valor de aquí se lee del entorno.
"""

from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

NORMAS_INICIALES = ["ieee", "apa7", "vancouver"]  # D-12: lista cerrada (6 de noviembre de 2026)
NORMA_POR_DEFECTO = "ieee"
PATRON_CODIGO = r"^[a-z0-9_]{1,40}$"


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Hito(_Estricto):
    """Hito del programa de titulación (tesis 6.2.2). No tiene semana fija."""

    orden: int = Field(ge=1)
    codigo: str = Field(pattern=PATRON_CODIGO)
    nombre: str = Field(min_length=1)
    contenido: str = Field(min_length=1)


class VentanaTokens(_Estricto):
    """Ventana de segmentación en tokens (Fase 1, 18.4)."""

    minimo: int = Field(ge=50)
    maximo: int = Field(ge=50)
    objetivo: int = Field(ge=50)

    @model_validator(mode="after")
    def _ordenada(self) -> Self:
        if not self.minimo <= self.objetivo <= self.maximo:
            raise ValueError("la ventana debe cumplir mínimo <= objetivo <= máximo")
        return self


class LimitesModelo(_Estricto):
    """Límites del proveedor para el limitador del cliente (R-01). ``None``: sin límite."""

    rpm: int | None = Field(None, ge=1)
    rpd: int | None = Field(None, ge=1)
    tpm: int | None = Field(None, ge=1)
    tpd: int | None = Field(None, ge=1)


class ModeloConfigurado(_Estricto):
    """Un modelo de lenguaje de la cadena (T17-01, apartado 2). ``alias`` marca un
    identificador que el proveedor puede cambiar: solo se admite en desarrollo (RN-24)."""

    proveedor: str = Field(pattern=r"^(groq|deepseek|gemini)$")
    modelo: str = Field(min_length=1, max_length=120)
    alias: bool = False
    max_tokens_salida: int = Field(2048, ge=1, le=65_536)
    precio_entrada_usd_millon: float | None = Field(None, ge=0)
    precio_salida_usd_millon: float | None = Field(None, ge=0)
    limites: LimitesModelo = Field(default_factory=LimitesModelo)


MODELOS_INICIALES: tuple[ModeloConfigurado, ...] = (
    # D-06. Groq: límites del plan publicados en su página (22 de noviembre de 2026).
    ModeloConfigurado(
        proveedor="groq",
        modelo="openai/gpt-oss-120b",
        precio_entrada_usd_millon=0.15,
        precio_salida_usd_millon=0.60,
        limites=LimitesModelo(rpm=30, rpd=1000, tpm=8000, tpd=200_000),
    ),
    # DeepSeek no ofrece identificadores fijos: alias, solo en desarrollo (decisión del
    # equipo). Precio de hora punta, sin caché. Sin límite de tasa publicado.
    ModeloConfigurado(
        proveedor="deepseek",
        modelo="deepseek-flash",
        alias=True,
        precio_entrada_usd_millon=0.30,
        precio_salida_usd_millon=1.20,
    ),
    # Gemini estable (decisión del equipo). Límites gratuitos no publicados: conservadores.
    ModeloConfigurado(
        proveedor="gemini",
        modelo="gemini-3.8-flash",
        limites=LimitesModelo(rpm=5, rpd=100),
    ),
)


HITOS_INICIALES: tuple[Hito, ...] = (
    Hito(orden=1, codigo="avance_1", nombre="Avance 1", contenido="Planteamiento"),
    Hito(
        orden=2,
        codigo="avance_2",
        nombre="Avance 2",
        contenido="Metodología y estado del arte",
    ),
    Hito(
        orden=3,
        codigo="entrega_plan",
        nombre="Entrega final del plan",
        contenido="Plan de tesis completo",
    ),
    Hito(orden=4, codigo="avance_3", nombre="Avance 3", contenido="Introducción"),
    Hito(orden=5, codigo="avance_4", nombre="Avance 4", contenido="Metodología"),
    Hito(orden=6, codigo="avance_5", nombre="Avance 5", contenido="Resultados"),
    Hito(orden=7, codigo="avance_6", nombre="Avance 6", contenido="Discusión y conclusiones"),
    Hito(
        orden=8,
        codigo="entrega_final",
        nombre="Entrega final del artículo",
        contenido="Artículo completo",
    ),
)


class ParametrosFuncionales(_Estricto):
    # Recuperación, reranking y suficiencia (Fase 1, 18.6)
    k_denso: int = Field(30, ge=1)
    k_lexico: int = Field(30, ge=1)
    rrf_constante: int = Field(60, ge=1)
    # T16-01: candidatos que pasan por el reordenador (18.6 dice 30; 20 por latencia,
    # decisión del equipo, a calibrar en T34) y tope de tokens del contexto (R-01)
    candidatos_reranking: int = Field(20, ge=1)
    n_reranking: int = Field(8, ge=1)
    presupuesto_tokens_contexto: int = Field(2400, ge=1)
    suficiencia_n: int = Field(2, ge=1)
    suficiencia_tau: float = Field(
        0.5,
        ge=0,
        le=1,
        description="Sobre el puntaje del reranker normalizado entre 0 y 1 (sigmoide). Provisional",
    )
    # Validación previa de la consulta de evidencia (T19-01; Fase 1, 7.2): reglas y
    # clasificador de pertinencia (similitud coseno máxima con el corpus del caso)
    consulta_min_palabras: int = Field(5, ge=1)
    consulta_max_caracteres: int = Field(1000, ge=50)
    pertinencia_umbral: float = Field(
        0.55, ge=0, le=1, description="Similitud coseno mínima con el corpus. Provisional"
    )
    # Segmentación (Fase 1, 18.4)
    ventana_tokens: VentanaTokens = Field(
        default_factory=lambda: VentanaTokens(minimo=300, maximo=450, objetivo=400)
    )
    solapamiento_oraciones: int = Field(1, ge=0)
    # Documento incompleto (Fase 1, 18.3): menos palabras que esto o sin secciones IMRaD
    palabras_minimas_articulo: int = Field(1500, ge=1)
    # Verificación y límites de los agentes (6.3, 6.7, RF-07)
    umbral_fidelidad: float = Field(0.90, ge=0, le=1)
    limite_palabras_d3: int = Field(250, ge=1)
    factor_extension_d3: float = Field(1.2, gt=0)
    limite_reescritura_palabras: int = Field(40, ge=1)
    # Norma de citación (D-12)
    normas_citacion: list[str] = Field(default_factory=lambda: list(NORMAS_INICIALES), min_length=1)
    norma_por_defecto: str = NORMA_POR_DEFECTO
    # Archivos (RN-16)
    tamano_max_docx_mb: int = Field(15, ge=1)
    tamano_max_pdf_mb: int = Field(25, ge=1)
    paginas_max_pdf: int = Field(60, ge=1)
    # Hitos (tesis 6.2.2) y uso mínimo orientativo (6.2.2.2): se reporta, no bloquea
    uso_minimo_por_hito: int = Field(1, ge=0)
    hitos: list[Hito] = Field(default_factory=lambda: list(HITOS_INICIALES), min_length=1)
    # Modelos de lenguaje (T17): el orden de respaldo lo da PROVEEDORES_MODELO
    modelos: list[ModeloConfigurado] = Field(
        default_factory=lambda: list(MODELOS_INICIALES), min_length=1
    )
    # Versión vigente de la instrucción de cada agente (RNF-21): agente -> vN
    versiones_instrucciones: dict[str, str] = Field(
        default_factory=lambda: {"suficiencia": "v1", "evidencia": "v1"}
    )

    @model_validator(mode="after")
    def _coherencia(self) -> Self:
        for norma in self.normas_citacion:
            if not _es_codigo(norma):
                raise ValueError(f"código de norma inválido: {norma}")
        if self.norma_por_defecto not in self.normas_citacion:
            raise ValueError("la norma por defecto debe estar en la lista de normas")
        if len(set(self.normas_citacion)) != len(self.normas_citacion):
            raise ValueError("la lista de normas tiene duplicados")
        if self.n_reranking > self.k_denso + self.k_lexico:
            raise ValueError("n_reranking no puede superar los candidatos recuperados")
        if not self.n_reranking <= self.candidatos_reranking <= self.k_denso + self.k_lexico:
            raise ValueError(
                "candidatos_reranking debe estar entre n_reranking y los candidatos recuperados"
            )
        if self.suficiencia_n > self.n_reranking:
            raise ValueError("suficiencia_n no puede superar n_reranking")
        proveedores = [m.proveedor for m in self.modelos]
        if len(set(proveedores)) != len(proveedores):
            raise ValueError("hay más de un modelo para el mismo proveedor")
        for agente, version in self.versiones_instrucciones.items():
            if not _es_codigo(agente) or re.fullmatch(r"v[0-9]{1,4}", version) is None:
                raise ValueError(f"versión de instrucción inválida: {agente}={version}")
        codigos = [h.codigo for h in self.hitos]
        if len(set(codigos)) != len(codigos):
            raise ValueError("hay hitos repetidos")
        if [h.orden for h in self.hitos] != list(range(1, len(self.hitos) + 1)):
            raise ValueError("los hitos deben estar ordenados de 1 a n sin saltos")
        return self

    def hito(self, codigo: str) -> Hito | None:
        return next((h for h in self.hitos if h.codigo == codigo), None)

    def modelo(self, proveedor: str) -> ModeloConfigurado | None:
        return next((m for m in self.modelos if m.proveedor == proveedor), None)


def _es_codigo(valor: str) -> bool:
    return re.fullmatch(PATRON_CODIGO, valor) is not None


def parametros_iniciales() -> ParametrosFuncionales:
    return ParametrosFuncionales()
