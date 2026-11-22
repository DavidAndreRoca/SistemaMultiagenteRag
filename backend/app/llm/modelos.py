"""Tipos del adaptador de modelos de lenguaje (T17-01, apartado 1).

Todo lo que se envía a un proveedor sale de ``EntradaModelo``: una tarea y bloques de
texto etiquetados (la sección del alcance o los fragmentos ``F1`` a ``Fn``). No admite
archivos ni bytes, de modo que el .docx nunca puede viajar al proveedor (RNF-10).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

MAX_CARACTERES_BLOQUE = 20_000
MAX_BLOQUES = 40
PATRON_ETIQUETA = r"^[A-Za-z0-9_\-]{1,40}$"


class Proveedor(StrEnum):
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    SIMULADO = "simulado"


class _Inmutable(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Instruccion(_Inmutable):
    """Instrucción versionada de un agente (``app/instrucciones/``)."""

    agente: str
    version: str
    huella: str = Field(pattern=r"^[0-9a-f]{64}$")
    texto: str = Field(min_length=1)

    @property
    def identificador(self) -> str:
        return f"{self.agente}/{self.version}"


class _Texto(_Inmutable):
    # Estricto: un ``bytes`` (por ejemplo, el .docx) no se convierte en texto (RNF-10).
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class BloqueDatos(_Texto):
    """Datos que el modelo lee pero nunca obedece (RN-23): una sección o un fragmento."""

    etiqueta: str = Field(pattern=PATRON_ETIQUETA)
    contenido: str = Field(max_length=MAX_CARACTERES_BLOQUE)


class EntradaModelo(_Texto):
    tarea: str = Field(min_length=1, max_length=4_000)
    datos: list[BloqueDatos] = Field(default_factory=list, max_length=MAX_BLOQUES)


class Uso(_Inmutable):
    tokens_entrada: int | None = None
    tokens_salida: int | None = None


class RespuestaProveedor(_Inmutable):
    """Lo que devuelve un proveedor antes de validar: el texto JSON y su uso."""

    texto: str
    uso: Uso = Uso()
    version_informada: str | None = None  # el modelo que el proveedor dice haber usado


class ResultadoEstructurado[T: BaseModel](BaseModel):
    model_config = ConfigDict(frozen=True)

    datos: T
    proveedor: Proveedor
    modelo: str
    version_informada: str | None
    instruccion: str  # agente/version
    huella_instruccion: str
    tokens_entrada: int | None
    tokens_salida: int | None
    duracion_ms: int
    costo_estimado: Decimal | None
    intentos: int
    respaldo: bool  # True si respondió un proveedor que no era el primero de la cadena


class MotivoError(StrEnum):
    SIN_CONEXION = "sin_conexion"
    TIEMPO_AGOTADO = "tiempo_agotado"
    LIMITE_DE_TASA = "limite_de_tasa"
    LIMITE_DIARIO = "limite_diario"  # del limitador del cliente (R-01)
    SOBRECARGA = "sobrecarga"
    ERROR_DEL_SERVICIO = "error_del_servicio"
    SALDO_INSUFICIENTE = "saldo_insuficiente"
    CLAVE_RECHAZADA = "clave_rechazada"
    SOLICITUD_RECHAZADA = "solicitud_rechazada"
    NO_CONFIGURADO = "no_configurado"
    RESPUESTA_ILEGIBLE = "respuesta_ilegible"
    SALIDA_INVALIDA = "salida_invalida"
    SIN_PROVEEDORES = "sin_proveedores"


class ErrorModelo(Exception):
    """Falla de una llamada al modelo. Nunca lleva contenido de la entrada ni de la salida."""

    def __init__(
        self, motivo: MotivoError, proveedor: Proveedor | None = None, detalle: str = ""
    ) -> None:
        super().__init__(f"{proveedor.value if proveedor else '-'}: {motivo.value} {detalle}")
        self.motivo = motivo
        self.proveedor = proveedor
        self.detalle = detalle[:200]


class ErrorDisponibilidad(ErrorModelo):
    """El proveedor no está disponible ahora: se reintenta y luego pasa al respaldo."""

    def __init__(
        self,
        motivo: MotivoError,
        proveedor: Proveedor | None = None,
        detalle: str = "",
        espera_s: float | None = None,
    ) -> None:
        super().__init__(motivo, proveedor, detalle)
        self.espera_s = espera_s


class ErrorSolicitud(ErrorModelo):
    """La solicitud o la configuración están mal (clave, formato): no pasa al respaldo."""


class SalidaInvalida(ErrorModelo):
    """La salida no cumple el esquema: se rechaza localmente y se reporta."""

    def __init__(self, proveedor: Proveedor, errores: list[str]) -> None:
        super().__init__(MotivoError.SALIDA_INVALIDA, proveedor, "; ".join(errores))
        self.errores = errores
