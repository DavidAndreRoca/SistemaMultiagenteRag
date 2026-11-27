"""Repositorio de la recuperación para una solicitud de un caso (T16; RN-03, RNF-03).

Ningún método acepta una colección: las colecciones salen siempre de
``colecciones_permitidas(tipo, contexto)``, con el caso del contexto (A1). Solo cuentan
los fragmentos de documentos recuperables (activos, o incompletos confirmados, 18.3) y
con vector del modelo vigente.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import TipoSolicitud
from app.bd.modelos import Documento, Fragmento
from app.repositorios.colecciones import colecciones_permitidas
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.corpus import recuperable


@dataclass(frozen=True)
class Coincidencia:
    fragmento_id: uuid.UUID
    puntaje: float


@dataclass(frozen=True)
class FragmentoConDocumento:
    fragmento: Fragmento
    documento: Documento


class RepositorioRecuperacion:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def _colecciones(self, contexto: ContextoAcceso, tipo: TipoSolicitud) -> list[uuid.UUID]:
        return await colecciones_permitidas(self._sesion, tipo, contexto)

    async def buscar_denso(
        self, contexto: ContextoAcceso, tipo: TipoSolicitud, vector: Sequence[float], k: int
    ) -> list[Coincidencia]:
        """Similitud coseno (índice HNSW) en las colecciones permitidas."""
        colecciones = await self._colecciones(contexto, tipo)
        if not colecciones:
            return []
        distancia = Fragmento.embedding.cosine_distance(list(vector)).label("distancia")
        resultado = await self._sesion.execute(
            select(Fragmento.id, distancia)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                Fragmento.coleccion_id.in_(colecciones),
                Documento.coleccion_id == Fragmento.coleccion_id,
                Fragmento.embedding.is_not(None),
                recuperable(),
            )
            .order_by(distancia, Fragmento.id)
            .limit(k)
        )
        return [Coincidencia(f, 1.0 - float(d)) for f, d in resultado.all()]

    async def buscar_lexico(
        self, contexto: ContextoAcceso, tipo: TipoSolicitud, consulta: str, k: int
    ) -> list[Coincidencia]:
        """``tsvector`` con configuración simple (índice GIN) en las colecciones permitidas.

        Se usa ``websearch_to_tsquery`` con ``OR`` entre los términos: la consulta de un
        estudiante es una oración, y exigir todos sus términos no devolvería casi nada.
        """
        colecciones = await self._colecciones(contexto, tipo)
        terminos = [t for t in _palabras(consulta) if len(t) > 2]
        if not colecciones or not terminos:
            return []
        consulta_ts = func.websearch_to_tsquery("simple", " or ".join(terminos))
        rango = func.ts_rank(Fragmento.texto_lexico, consulta_ts).label("rango")
        resultado = await self._sesion.execute(
            select(Fragmento.id, rango)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                Fragmento.coleccion_id.in_(colecciones),
                Documento.coleccion_id == Fragmento.coleccion_id,
                Fragmento.embedding.is_not(None),
                Fragmento.texto_lexico.op("@@")(consulta_ts),
                recuperable(),
            )
            .order_by(rango.desc(), Fragmento.id)
            .limit(k)
        )
        return [Coincidencia(f, float(r)) for f, r in resultado.all()]

    async def fragmentos(
        self, contexto: ContextoAcceso, tipo: TipoSolicitud, ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, FragmentoConDocumento]:
        """Los fragmentos pedidos, solo si están en las colecciones permitidas."""
        colecciones = await self._colecciones(contexto, tipo)
        if not colecciones or not ids:
            return {}
        resultado = await self._sesion.execute(
            select(Fragmento, Documento)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                Fragmento.id.in_(list(ids)),
                Fragmento.coleccion_id.in_(colecciones),
                recuperable(),
            )
        )
        return {f.id: FragmentoConDocumento(f, d) for f, d in resultado.all()}

    async def por_apartado(
        self, contexto: ContextoAcceso, tipo: TipoSolicitud, apartados: Sequence[str]
    ) -> list[Fragmento]:
        """Fragmentos de guía cuyo apartado (``seccion_original``) es uno de ``apartados``,
        solo de las colecciones permitidas para el tipo, en el orden del documento (T26,
        herramienta ``lista_de_comprobacion``)."""
        colecciones = await self._colecciones(contexto, tipo)
        if not colecciones or not apartados:
            return []
        resultado = await self._sesion.execute(
            select(Fragmento)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                Fragmento.coleccion_id.in_(colecciones),
                Fragmento.seccion_original.in_(list(apartados)),
                recuperable(),
            )
            .order_by(Documento.titulo, Fragmento.orden)
        )
        return list(resultado.scalars().all())


# Palabras vacías frecuentes en español e inglés: con la configuración ``simple`` no se
# descartan solas, y en una consulta con OR coincidirían con casi todos los fragmentos.
PALABRAS_VACIAS = frozenset(
    [
        "los",
        "las",
        "del",
        "una",
        "uno",
        "unos",
        "unas",
        "por",
        "para",
        "con",
        "sin",
        "sobre",
        "entre",
        "como",
        "que",
        "qué",
        "cual",
        "cuál",
        "este",
        "esta",
        "estos",
        "estas",
        "ese",
        "esa",
        "eso",
        "esos",
        "esas",
        "más",
        "menos",
        "muy",
        "pero",
        "sus",
        "son",
        "ser",
        "fue",
        "han",
        "hay",
        "está",
        "están",
        "sea",
        "también",
        "porque",
        "cuando",
        "donde",
        "dónde",
        "cómo",
        "quiero",
        "creo",
        "puede",
        "pueden",
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "these",
        "those",
        "are",
        "was",
        "were",
        "has",
        "have",
        "not",
        "but",
        "into",
    ]
)


def _palabras(texto: str) -> list[str]:
    limpio = "".join(c if c.isalnum() else " " for c in texto.lower())
    return [p for p in dict.fromkeys(limpio.split()) if p not in PALABRAS_VACIAS]
