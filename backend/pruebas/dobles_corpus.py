"""Dobles de prueba del corpus (T10): canal de extracción y servicio de embeddings.

* ``CanalFicticio`` decide el resultado por el contenido del archivo (una marca en el
  texto), sin Docling: permite probar la indexación con la base real en la CI.
* ``EmbeddingsFicticios`` produce vectores deterministas de bolsa de palabras (1 024
  dimensiones, normalizados): textos que comparten palabras quedan cerca, así que las
  consultas densas de prueba tienen sentido.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from pathlib import Path

from app.bd.enumeraciones import SeccionNormalizada
from app.bd.modelos.corpus import DIMENSION_EMBEDDINGS
from app.corpus.esquemas import (
    Autor,
    DocumentoProcesado,
    EstadoProcesamiento,
    FragmentoProcesado,
    MetadatosCabecera,
    MotivoExclusion,
    MotivoIncompleto,
)
from app.corpus.extraccion import ParametrosCanal, huella_de_texto
from app.inferencia.interfaces import Embeddings, IdentidadModelo

TEXTOS = {
    "TUTORIA": [
        (SeccionNormalizada.INTRODUCCION, "1. Introducción", 1, "La tutoría entre pares reduce"
         " la ansiedad ante la estadística en estudiantes de Psicología."),
        (SeccionNormalizada.METODOS, "2. Método", 2, "Participaron 84 estudiantes en un"
         " diseño cuasiexperimental con grupo control."),
        (SeccionNormalizada.RESULTADOS, "3. Resultados", 3, "El grupo con tutoría redujo su"
         " puntaje de ansiedad más que el grupo control."),
    ],
    "SUENO": [
        (SeccionNormalizada.INTRODUCCION, "1. Introduction", 1, "Short sleep before an exam"
         " impairs working memory in first-year students."),
        (SeccionNormalizada.RESULTADOS, "3. Results", 2, "Students who slept less than six"
         " hours obtained lower statistics exam scores."),
    ],
}  # fmt: skip


def contenido(marca: str, variante: str = "") -> bytes:
    """Bytes de un "PDF" de prueba: la marca decide el resultado del canal ficticio."""
    return f"%PDF-1.4\n% {marca} {variante}\n%%EOF\n".encode()


class CanalFicticio:
    """Marcas: ``TUTORIA`` o ``SUENO`` (procesado), ``INCOMPLETO``, ``ESCANEADO``,
    ``ILEGIBLE``. ``DOI=...`` fija el DOI de la cabecera."""

    def __init__(self) -> None:
        self.parametros: ParametrosCanal | None = None
        self.procesados = 0

    def con_parametros(self, parametros: ParametrosCanal) -> CanalFicticio:
        self.parametros = parametros
        return self

    def procesar_pdf(self, ruta: Path) -> DocumentoProcesado:
        self.procesados += 1
        datos = ruta.read_bytes()
        texto = datos.decode(errors="replace")
        huella_archivo = hashlib.sha256(datos).hexdigest()
        if "ESCANEADO" in texto or "ILEGIBLE" in texto:
            motivo = (
                MotivoExclusion.SIN_CAPA_DE_TEXTO
                if "ESCANEADO" in texto
                else MotivoExclusion.PDF_ILEGIBLE
            )
            return DocumentoProcesado(
                estado=EstadoProcesamiento.EXCLUIDO,
                motivo_exclusion=motivo,
                huella_archivo=huella_archivo,
                num_paginas=1,
            )
        tema = "SUENO" if "SUENO" in texto else "TUTORIA"
        incompleto = "INCOMPLETO" in texto
        piezas = TEXTOS[tema][:1] if incompleto else TEXTOS[tema]
        fragmentos = [
            FragmentoProcesado(
                orden=i,
                texto=cuerpo,
                seccion_normalizada=seccion,
                seccion_original=titulo,
                pagina_inicio=pagina,
                pagina_fin=pagina,
                tokens=len(cuerpo.split()),
            )
            for i, (seccion, titulo, pagina, cuerpo) in enumerate(piezas)
        ]
        doi = re.search(r"DOI=(\S+)", texto)
        return DocumentoProcesado(
            estado=EstadoProcesamiento.INCOMPLETO if incompleto else EstadoProcesamiento.PROCESADO,
            motivos_incompleto=[MotivoIncompleto.TEXTO_INSUFICIENTE] if incompleto else [],
            huella_archivo=huella_archivo,
            huella_texto=huella_de_texto("\n".join(f.texto for f in fragmentos)),
            num_paginas=3,
            palabras=sum(f.tokens for f in fragmentos),
            secciones=list(dict.fromkeys(f.seccion_normalizada for f in fragmentos)),
            metadatos=MetadatosCabecera(
                titulo=f"Artículo ficticio {tema.lower()}",
                autores=[Autor(nombres="Ana", apellidos="Prueba Ficticia")],
                anio=2026,
                doi=doi.group(1) if doi else None,
                idioma="es",
            ),
            fragmentos=fragmentos,
        )


def vector_de(texto: str) -> list[float]:
    vector = [0.0] * DIMENSION_EMBEDDINGS
    for palabra in re.findall(r"\w+", texto.lower()):
        indice = int(hashlib.sha256(palabra.encode()).hexdigest(), 16) % DIMENSION_EMBEDDINGS
        vector[indice] += 1.0
    norma = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norma for v in vector]


class EmbeddingsFicticios:
    def __init__(self, revision: str = "rev-1") -> None:
        self.revision = revision
        self.llamadas = 0
        self.textos: list[str] = []

    async def embeber(self, textos: Sequence[str]) -> Embeddings:
        self.llamadas += 1
        self.textos.extend(textos)
        return Embeddings(
            identidad=IdentidadModelo(modelo="ficticio/bolsa-de-palabras", revision=self.revision),
            vectores=[vector_de(t) for t in textos],
        )
