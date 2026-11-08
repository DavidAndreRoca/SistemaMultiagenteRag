"""Canal de extracción de PDF: ``procesar_pdf(ruta) -> DocumentoProcesado`` (T09).

El canal no toca la base de datos ni indexa (eso es T10). Pasos:

1. Validación del archivo (RN-16): tamaño, tipo real, cifrado, páginas y capa de texto.
2. Extracción con Docling (texto, títulos, orden de lectura y páginas).
3. Limpieza, normalización de secciones a IMRaD y exclusión de referencias y
   agradecimientos.
4. Segmentación con la ventana y el solapamiento de la configuración vigente.
5. Metadatos de cabecera con GROBID.
6. Regla de documento incompleto (18.3): menos palabras que el umbral o ninguna
   sección IMRaD. Un incompleto conserva sus fragmentos, pero solo se indexa si el
   investigador lo confirma (T10).

El contenido del PDF es dato (RN-23): nada de él se interpreta como instrucción, y el
registro solo guarda cantidades y estados, nunca texto (4.6).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.administracion.parametros import ParametrosFuncionales, VentanaTokens
from app.comun.registro import obtener_registrador
from app.corpus.bloques import DocumentoExtraido
from app.corpus.esquemas import (
    DocumentoProcesado,
    EstadoProcesamiento,
    MetadatosCabecera,
    MotivoExclusion,
    MotivoIncompleto,
)
from app.corpus.extractor_docling import ErrorExtraccion
from app.corpus.limpieza import contar_palabras, limpiar
from app.corpus.secciones import seccionar
from app.corpus.segmentacion import ContadorTokens, segmentar
from app.corpus.validacion import LimitesPdf, validar_pdf

_registro = obtener_registrador("corpus")


class Extractor(Protocol):
    def extraer(self, ruta: Path) -> DocumentoExtraido: ...


class FuenteCabecera(Protocol):
    def cabecera(self, ruta: Path) -> MetadatosCabecera: ...


@dataclass(frozen=True)
class ParametrosCanal:
    limites: LimitesPdf
    ventana: VentanaTokens
    solapamiento_oraciones: int
    palabras_minimas: int

    @classmethod
    def desde(cls, parametros: ParametrosFuncionales) -> ParametrosCanal:
        """Toma los valores de la versión vigente de la configuración (tabla configuracion)."""
        return cls(
            limites=LimitesPdf(parametros.tamano_max_pdf_mb, parametros.paginas_max_pdf),
            ventana=parametros.ventana_tokens,
            solapamiento_oraciones=parametros.solapamiento_oraciones,
            palabras_minimas=parametros.palabras_minimas_articulo,
        )


def huella_de_texto(texto: str) -> str:
    """SHA-256 del texto normalizado (minúsculas y espacios simples), para deduplicar."""
    normalizado = " ".join(texto.lower().split())
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


class CanalPdf:
    def __init__(
        self,
        extractor: Extractor,
        cabecera: FuenteCabecera,
        contador: ContadorTokens,
        parametros: ParametrosCanal,
    ) -> None:
        self._extractor = extractor
        self._cabecera = cabecera
        self._contador = contador
        self._parametros = parametros

    def procesar_pdf(self, ruta: Path) -> DocumentoProcesado:
        inicio = time.perf_counter()
        documento = self._procesar(ruta)
        _registro.info(
            "pdf procesado",
            extra={
                "tipo_evento": "extraccion",
                "estado": documento.estado.value,
                "motivos": [
                    m.value
                    for m in (
                        [documento.motivo_exclusion]
                        if documento.motivo_exclusion
                        else documento.motivos_incompleto
                    )
                ],
                "paginas": documento.num_paginas,
                "palabras": documento.palabras,
                "fragmentos": len(documento.fragmentos),
                "duracion_ms": round((time.perf_counter() - inicio) * 1000),
            },
        )
        return documento

    def _procesar(self, ruta: Path) -> DocumentoProcesado:
        informe = validar_pdf(ruta, self._parametros.limites)
        if informe.motivo is not None:
            return _excluido(informe.huella_archivo, informe.motivo, informe.num_paginas)

        try:
            extraido = self._extractor.extraer(ruta)
        except ErrorExtraccion:
            return _excluido(
                informe.huella_archivo, MotivoExclusion.PDF_ILEGIBLE, informe.num_paginas
            )
        seccionado = seccionar(limpiar(extraido.bloques, extraido.num_paginas))
        cuerpo = "\n".join(p.texto for s in seccionado.secciones for p in s.parrafos)
        palabras = contar_palabras(cuerpo)
        if palabras == 0:
            return _excluido(
                informe.huella_archivo, MotivoExclusion.SIN_CAPA_DE_TEXTO, informe.num_paginas
            )

        fragmentos = segmentar(
            seccionado.secciones,
            self._contador,
            self._parametros.ventana,
            self._parametros.solapamiento_oraciones,
        )
        metadatos = self._cabecera.cabecera(ruta)
        motivos: list[MotivoIncompleto] = []
        if palabras < self._parametros.palabras_minimas:
            motivos.append(MotivoIncompleto.TEXTO_INSUFICIENTE)
        if not seccionado.tiene_imrad:
            motivos.append(MotivoIncompleto.SIN_SECCIONES_IMRAD)
        return DocumentoProcesado(
            estado=EstadoProcesamiento.INCOMPLETO if motivos else EstadoProcesamiento.PROCESADO,
            motivos_incompleto=motivos,
            huella_archivo=informe.huella_archivo,
            huella_texto=huella_de_texto(cuerpo),
            num_paginas=extraido.num_paginas or informe.num_paginas,
            palabras=palabras,
            secciones=seccionado.detectadas,
            metadatos=metadatos,
            fragmentos=fragmentos,
        )


def _excluido(
    huella_archivo: str, motivo: MotivoExclusion, num_paginas: int | None
) -> DocumentoProcesado:
    return DocumentoProcesado(
        estado=EstadoProcesamiento.EXCLUIDO,
        motivo_exclusion=motivo,
        huella_archivo=huella_archivo,
        num_paginas=num_paginas,
    )


def crear_canal(
    recursos: Path, url_grobid: str, parametros: ParametrosCanal, *, hilos: int = 4
) -> CanalPdf:
    """Canal real: Docling, GROBID y el tokenizador de bge-m3 (requiere el extra corpus)."""
    from app.corpus.extractor_docling import ExtractorDocling
    from app.corpus.grobid import ClienteGrobid
    from app.corpus.tokenizador import ContadorTokensBgeM3

    return CanalPdf(
        ExtractorDocling(recursos, hilos=hilos),
        ClienteGrobid(url_grobid),
        ContadorTokensBgeM3(recursos),
        parametros,
    )
