"""Resultado común de los servicios bibliográficos (T14-01, apartado 2; RN-18).

``no_encontrado`` solo sale de una respuesta válida del servicio que dice que la obra no
existe. Toda falla (red, tiempo agotado, 429 o 5xx tras los reintentos, respuesta
ilegible, servicio sin configurar) da ``no_comprobable``: una caída nunca se confunde con
una inexistencia.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.bibliografia.normalizacion import normalizar


class Servicio(StrEnum):
    CROSSREF = "crossref"
    DOI = "doi"
    UNPAYWALL = "unpaywall"
    OPENALEX = "openalex"


class Estado(StrEnum):
    ENCONTRADO = "encontrado"
    NO_ENCONTRADO = "no_encontrado"
    NO_COMPROBABLE = "no_comprobable"


class Motivo(StrEnum):
    """Por qué un resultado no es ``encontrado``."""

    NO_EXISTE = "no_existe"  # el servicio respondió que no existe (404)
    SIN_COINCIDENCIAS = "sin_coincidencias"  # la búsqueda respondió sin candidatos
    SIN_CONEXION = "sin_conexion"
    TIEMPO_AGOTADO = "tiempo_agotado"
    LIMITE_DE_TASA = "limite_de_tasa"  # 429 tras los reintentos
    ERROR_DEL_SERVICIO = "error_del_servicio"  # 5xx tras los reintentos u otro estado
    RESPUESTA_INVALIDA = "respuesta_invalida"
    NO_CONFIGURADO = "no_configurado"  # falta el correo o la clave del servicio
    DOI_INVALIDO = "doi_invalido"


class _Inmutable(BaseModel):
    model_config = ConfigDict(frozen=True)


class Autor(_Inmutable):
    apellidos: str | None = None
    nombres: str | None = None
    nombre_completo: str | None = None  # cuando el servicio no separa (OpenAlex)

    def apellidos_para_comparar(self) -> str | None:
        if self.apellidos:
            return self.apellidos
        if self.nombre_completo:
            partes = self.nombre_completo.split()
            return partes[-1] if partes else None
        return None


class MetadatosBibliograficos(_Inmutable):
    doi: str | None = None
    titulo: str | None = None
    autores: list[Autor] = []
    anio: int | None = None
    revista: str | None = None
    volumen: str | None = None
    numero: str | None = None
    paginas: str | None = None
    editorial: str | None = None
    tipo: str | None = None
    # Resumen de la obra (T32: se indexa si el caso aporta una fuente sin PDF).
    resumen: str | None = None


class AccesoAbierto(_Inmutable):
    es_abierto: bool
    estado: str | None = None  # gold, green, hybrid, bronze, diamond o closed
    url: str | None = None
    url_pdf: str | None = None
    licencia: str | None = None
    version: str | None = None


class ResultadoBibliografico(_Inmutable):
    servicio: Servicio
    estado: Estado
    metadatos: MetadatosBibliograficos | None = None
    acceso_abierto: AccesoAbierto | None = None
    cita: str | None = None
    candidatos: list[MetadatosBibliograficos] = []  # resultado de una búsqueda
    motivo: Motivo | None = None
    desde_cache: bool = False

    @classmethod
    def no_comprobable(cls, servicio: Servicio, motivo: Motivo) -> ResultadoBibliografico:
        return cls(servicio=servicio, estado=Estado.NO_COMPROBABLE, motivo=motivo)

    @classmethod
    def no_encontrado(cls, servicio: Servicio, motivo: Motivo) -> ResultadoBibliografico:
        return cls(servicio=servicio, estado=Estado.NO_ENCONTRADO, motivo=motivo)


class ConsultaBibliografica(_Inmutable):
    """Datos de una referencia sin DOI para buscarla por metadatos (18.9)."""

    titulo: str
    autores: list[str] = []  # apellidos
    anio: int | None = None

    def clave(self) -> str:
        autores = ",".join(sorted(normalizar(a) for a in self.autores))
        return f"busqueda|{normalizar(self.titulo)}|{autores}|{self.anio or ''}"

    def texto(self) -> str:
        """Texto libre para la búsqueda: título, apellidos y año."""
        partes = (self.titulo, " ".join(self.autores), str(self.anio or ""))
        return " ".join(parte for parte in partes if parte)
