"""Ajustes de la aplicación leídos de variables de entorno y validados al arrancar.

Reglas (hoja de ruta, apartado 4.3):

* Toda configuración sale de variables de entorno; si falta una obligatoria, la
  aplicación no arranca y lo informa con el nombre de la variable.
* Los parámetros funcionales (tau, N, k, umbrales, normas, modelos) NO viven aquí:
  están en la configuración versionada (tabla ``configuracion``, T04 y T35).
* Los secretos son ``SecretStr``: no aparecen en ``repr`` ni en el registro.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from enum import StrEnum
from typing import Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    model_validator,
)

LONGITUD_MINIMA_SECRETO = 32
PROVEEDORES_MODELO_CONOCIDOS = ("groq", "deepseek", "gemini", "simulado")
# D-10: la lista de producción se llena en T25. Mientras esté vacía, en producción no
# se puede habilitar ningún proveedor gratuito de desarrollo (T17-01, apartado 3).
PROVEEDORES_DE_PRODUCCION: frozenset[str] = frozenset()
PROVEEDORES_POR_ENTORNO = {
    "desarrollo": ("groq", "deepseek", "gemini"),
    "pruebas": ("simulado",),
    "produccion": (),
}


class Entorno(StrEnum):
    DESARROLLO = "desarrollo"
    PRUEBAS = "pruebas"
    PRODUCCION = "produccion"


class ErrorConfiguracion(RuntimeError):
    """La configuración es inválida; el mensaje nombra cada variable con problema."""


def _vacia(valor: SecretStr | str | None) -> bool:
    if valor is None:
        return True
    texto = valor.get_secret_value() if isinstance(valor, SecretStr) else valor
    return not texto.strip()


class Ajustes(BaseModel):
    """Variables de entorno de la aplicación.

    Es un modelo Pydantic y no ``BaseSettings`` a propósito: el origen de los datos
    (``os.environ`` o un diccionario inyectado) lo decide ``cargar_ajustes`` y la
    lectura es hermética en pruebas.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True, frozen=True)

    # Obligatorias en todos los entornos
    entorno: Entorno = Field(validation_alias=AliasChoices("ENTORNO"))
    url_bd: SecretStr = Field(validation_alias=AliasChoices("URL_BD"))
    secreto_sesion: SecretStr = Field(validation_alias=AliasChoices("SECRETO_SESION"))

    # Obligatorias según entorno (ver validador)
    correo_polite: str | None = Field(default=None, validation_alias=AliasChoices("CORREO_POLITE"))
    clave_openalex: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("CLAVE_OPENALEX")
    )

    # Proveedores de modelo de desarrollo (D-06). Opcionales para arrancar; el comando
    # de diagnóstico verifica las que existan.
    clave_groq: SecretStr | None = Field(default=None, validation_alias=AliasChoices("CLAVE_GROQ"))
    clave_deepseek: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("CLAVE_DEEPSEEK")
    )
    clave_gemini: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("CLAVE_GEMINI")
    )

    # Servicio compartido de modelos (T08). Opcional hasta que la indexación lo use (T10).
    url_servicio_modelos: str | None = Field(
        default=None, validation_alias=AliasChoices("URL_SERVICIO_MODELOS")
    )

    # Canal de extracción de PDF (T09): GROBID compartido y carpeta con el modelo de diseño
    # de página y el tokenizador (python -m app.corpus.recursos). Opcionales hasta T10.
    url_grobid: str | None = Field(default=None, validation_alias=AliasChoices("URL_GROBID"))
    directorio_recursos_corpus: str | None = Field(
        default=None, validation_alias=AliasChoices("DIRECTORIO_RECURSOS_CORPUS")
    )
    # Carpeta privada de los PDF del corpus (T10); nunca se sirve por la API.
    directorio_archivos: str | None = Field(
        default=None, validation_alias=AliasChoices("DIRECTORIO_ARCHIVOS")
    )
    # Hilos de Docling (modelo de diseño de página): en un portátil compartido conviene
    # dejar núcleos libres (decisión T10-02). No cambia el resultado de la extracción.
    hilos_docling: int = Field(
        default=4, ge=1, le=32, validation_alias=AliasChoices("HILOS_DOCLING")
    )

    # Servicios bibliográficos (T14). Ajustes de operación, no parámetros funcionales: no
    # cambian qué se verifica, solo el ritmo y la espera (decisión T14-01, apartados 3 a 5).
    # Tasas en consultas por segundo, según la documentación de cada servicio.
    tasa_crossref: float = Field(default=10, gt=0, le=50, validation_alias="TASA_CROSSREF")
    tasa_crossref_busqueda: float = Field(
        default=3, gt=0, le=50, validation_alias="TASA_CROSSREF_BUSQUEDA"
    )
    tasa_doi: float = Field(default=5, gt=0, le=50, validation_alias="TASA_DOI")
    tasa_unpaywall: float = Field(default=1.15, gt=0, le=50, validation_alias="TASA_UNPAYWALL")
    tasa_openalex: float = Field(default=10, gt=0, le=50, validation_alias="TASA_OPENALEX")
    tiempo_maximo_bibliografia_s: float = Field(
        default=15, gt=0, le=120, validation_alias="TIEMPO_MAXIMO_BIBLIOGRAFIA_S"
    )
    reintentos_bibliografia: int = Field(
        default=3, ge=1, le=6, validation_alias="REINTENTOS_BIBLIOGRAFIA"
    )
    vigencia_cache_bibliografia_dias: int = Field(
        default=30, ge=1, le=365, validation_alias="VIGENCIA_CACHE_BIBLIOGRAFIA_DIAS"
    )
    vigencia_no_encontrado_horas: int = Field(
        default=24, ge=1, le=720, validation_alias="VIGENCIA_NO_ENCONTRADO_HORAS"
    )
    # Modelos de lenguaje (T17): proveedores habilitados en orden de respaldo. Vacío o
    # ausente: los del entorno (PROVEEDORES_POR_ENTORNO).
    proveedores_modelo: str | None = Field(
        default=None, validation_alias=AliasChoices("PROVEEDORES_MODELO")
    )
    tiempo_maximo_modelo_s: float = Field(
        default=120, gt=0, le=600, validation_alias="TIEMPO_MAXIMO_MODELO_S"
    )
    espera_maxima_limitador_s: float = Field(
        default=30, ge=0, le=300, validation_alias="ESPERA_MAXIMA_LIMITADOR_S"
    )

    @property
    def cadena_modelos(self) -> tuple[str, ...]:
        """Proveedores de modelo habilitados, en orden de respaldo."""
        if self.proveedores_modelo is None or not self.proveedores_modelo.strip():
            return PROVEEDORES_POR_ENTORNO[self.entorno.value]
        return tuple(p.strip().lower() for p in self.proveedores_modelo.split(",") if p.strip())

    @model_validator(mode="after")
    def _validar_por_entorno(self) -> Self:
        for nombre, url in (
            ("URL_SERVICIO_MODELOS", self.url_servicio_modelos),
            ("URL_GROBID", self.url_grobid),
        ):
            if url and not url.startswith(("http://", "https://")):
                raise ValueError(f"{nombre} debe empezar con http:// o https://")
        self._validar_modelos()
        faltantes: list[str] = []
        if _vacia(self.url_bd):
            faltantes.append("URL_BD")
        if _vacia(self.secreto_sesion):
            faltantes.append("SECRETO_SESION")
        elif (
            self.entorno is not Entorno.PRUEBAS
            and len(self.secreto_sesion.get_secret_value()) < LONGITUD_MINIMA_SECRETO
        ):
            raise ValueError(
                f"SECRETO_SESION debe tener al menos {LONGITUD_MINIMA_SECRETO} caracteres "
                f"en el entorno {self.entorno.value}"
            )
        if self.entorno in (Entorno.DESARROLLO, Entorno.PRODUCCION) and _vacia(self.correo_polite):
            faltantes.append("CORREO_POLITE")
        if self.entorno is Entorno.PRODUCCION and _vacia(self.clave_openalex):
            faltantes.append("CLAVE_OPENALEX")
        if faltantes:
            raise ValueError(
                "faltan variables obligatorias para el entorno "
                f"{self.entorno.value}: {', '.join(faltantes)}"
            )
        return self

    def _validar_modelos(self) -> None:
        """Regla de entorno de T17: falla al arrancar si no se cumple."""
        cadena = self.cadena_modelos
        desconocidos = [p for p in cadena if p not in PROVEEDORES_MODELO_CONOCIDOS]
        if desconocidos:
            raise ValueError(f"PROVEEDORES_MODELO nombra proveedores desconocidos: {desconocidos}")
        if len(set(cadena)) != len(cadena):
            raise ValueError("PROVEEDORES_MODELO repite proveedores")
        if self.entorno is Entorno.PRODUCCION:
            prohibidos = [p for p in cadena if p not in PROVEEDORES_DE_PRODUCCION]
            if prohibidos:
                raise ValueError(
                    "en producción solo se admiten los proveedores de la lista de producción"
                    f" (D-10); PROVEEDORES_MODELO incluye: {', '.join(prohibidos)}"
                )
        if "simulado" in cadena and self.entorno is not Entorno.PRUEBAS:
            raise ValueError("el proveedor simulado solo se admite en el entorno de pruebas")

    @property
    def es_produccion(self) -> bool:
        return self.entorno is Entorno.PRODUCCION

    @property
    def documentacion_habilitada(self) -> bool:
        """OpenAPI interactivo solo fuera de producción (RNF-22 en desarrollo)."""
        return not self.es_produccion


def cargar_ajustes(entorno: Mapping[str, str] | None = None) -> Ajustes:
    """Lee y valida los ajustes. Lanza ``ErrorConfiguracion`` con un mensaje legible.

    ``entorno`` permite inyectar un diccionario en pruebas; por defecto ``os.environ``.
    """
    origen = dict(os.environ if entorno is None else entorno)
    try:
        return Ajustes.model_validate(origen)
    except ValidationError as error:
        problemas = []
        for detalle in error.errors():
            ubicacion = ".".join(str(parte) for parte in detalle["loc"])
            if detalle["type"] == "missing":
                problemas.append(f"falta la variable obligatoria {ubicacion}")
            else:
                mensaje = str(detalle["msg"]).removeprefix("Value error, ")
                problemas.append(f"{ubicacion}: {mensaje}" if ubicacion else mensaje)
        raise ErrorConfiguracion("Configuración inválida: " + "; ".join(problemas)) from None
