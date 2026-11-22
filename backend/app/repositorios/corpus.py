"""Repositorio del corpus para el investigador (A2): documentos, fragmentos y exclusiones.

Todo método exige un ``ContextoAcceso`` de rol A2. Las colecciones personales (aportes
de un caso) no se gestionan aquí: son de T32 y se consultan siempre con su caso.

Un documento es **recuperable** si está activo, o si está incompleto y el investigador
confirmó indexarlo (18.3). Los retirados dejan de recuperarse, pero sus fragmentos se
conservan para la trazabilidad de solicitudes pasadas (18.9).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import EstadoDocumento, EstadoReferencia
from app.bd.modelos import (
    Coleccion,
    Documento,
    ExclusionCorpus,
    Fragmento,
    FragmentoRecuperado,
    ReferenciaImportada,
)
from app.repositorios.contexto import ContextoAcceso


def recuperable() -> ColumnElement[bool]:
    return or_(
        Documento.estado == EstadoDocumento.ACTIVO,
        and_(Documento.estado == EstadoDocumento.INCOMPLETO, Documento.confirmado_en.is_not(None)),
    )


@dataclass(frozen=True)
class Encontrado:
    fragmento: Fragmento
    documento: Documento
    puntaje: float


class RepositorioCorpus:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def coleccion(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID
    ) -> Coleccion | None:
        contexto.exigir_investigador()
        return await self._sesion.get(Coleccion, coleccion_id)

    async def documento(
        self, contexto: ContextoAcceso, documento_id: uuid.UUID
    ) -> Documento | None:
        contexto.exigir_investigador()
        return await self._sesion.get(Documento, documento_id)

    async def registrado_por_archivo(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID, huella_archivo: str
    ) -> Documento | ExclusionCorpus | None:
        """Documento o exclusión que ya tiene este mismo archivo en la colección."""
        contexto.exigir_investigador()
        documento = await self._sesion.scalar(
            select(Documento).where(
                Documento.coleccion_id == coleccion_id, Documento.huella_archivo == huella_archivo
            )
        )
        if documento is not None:
            return documento
        return await self._sesion.scalar(
            select(ExclusionCorpus).where(
                ExclusionCorpus.coleccion_id == coleccion_id,
                ExclusionCorpus.huella_archivo == huella_archivo,
            )
        )

    async def duplicado(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID, huella_texto: str, doi: str | None
    ) -> Documento | None:
        """Documento de la colección con el mismo texto normalizado o el mismo DOI (18.9)."""
        contexto.exigir_investigador()
        condicion = Documento.huella_sha256 == huella_texto
        if doi:
            condicion = or_(condicion, Documento.doi == doi)
        return await self._sesion.scalar(
            select(Documento)
            .where(Documento.coleccion_id == coleccion_id, condicion)
            .order_by(Documento.creado_en)
            .limit(1)
        )

    async def agregar_documento(
        self, contexto: ContextoAcceso, documento: Documento, fragmentos: Sequence[Fragmento]
    ) -> Documento:
        contexto.exigir_investigador()
        self._sesion.add(documento)
        await self._sesion.flush()
        for fragmento in fragmentos:
            fragmento.documento_id = documento.id
            fragmento.coleccion_id = documento.coleccion_id
            self._sesion.add(fragmento)
        await self._sesion.flush()
        return documento

    async def agregar_exclusion(
        self, contexto: ContextoAcceso, exclusion: ExclusionCorpus
    ) -> ExclusionCorpus:
        contexto.exigir_investigador()
        self._sesion.add(exclusion)
        await self._sesion.flush()
        return exclusion

    async def fragmentos(
        self, contexto: ContextoAcceso, documento: Documento
    ) -> Sequence[Fragmento]:
        contexto.exigir_investigador()
        resultado = await self._sesion.scalars(
            select(Fragmento)
            .where(Fragmento.documento_id == documento.id)
            .order_by(Fragmento.orden)
        )
        return resultado.all()

    async def listar_documentos(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID
    ) -> list[tuple[Documento, int]]:
        contexto.exigir_investigador()
        cantidad = (
            select(func.count(Fragmento.id))
            .where(Fragmento.documento_id == Documento.id)
            .scalar_subquery()
        )
        resultado = await self._sesion.execute(
            select(Documento, cantidad)
            .where(Documento.coleccion_id == coleccion_id)
            .order_by(Documento.creado_en, Documento.id)
        )
        return [(fila[0], int(fila[1])) for fila in resultado.all()]

    async def fragmentos_en_uso(self, contexto: ContextoAcceso, documento: Documento) -> bool:
        """Algún fragmento del documento fue recuperado por una solicitud (trazabilidad)."""
        contexto.exigir_investigador()
        usado = await self._sesion.scalar(
            select(FragmentoRecuperado.id)
            .join(Fragmento, Fragmento.id == FragmentoRecuperado.fragmento_id)
            .where(Fragmento.documento_id == documento.id)
            .limit(1)
        )
        return usado is not None

    async def reemplazar_fragmentos(
        self, contexto: ContextoAcceso, documento: Documento, nuevos: Sequence[Fragmento]
    ) -> None:
        """Cambia los fragmentos de un documento (re-segmentación sin trazas que conservar)."""
        contexto.exigir_investigador()
        await self._sesion.execute(delete(Fragmento).where(Fragmento.documento_id == documento.id))
        for fragmento in nuevos:
            fragmento.documento_id = documento.id
            fragmento.coleccion_id = documento.coleccion_id
            self._sesion.add(fragmento)
        await self._sesion.flush()

    async def otro_con_huella(
        self, contexto: ContextoAcceso, documento: Documento, huella_texto: str
    ) -> bool:
        contexto.exigir_investigador()
        otro = await self._sesion.scalar(
            select(Documento.id).where(
                Documento.coleccion_id == documento.coleccion_id,
                Documento.huella_sha256 == huella_texto,
                Documento.id != documento.id,
            )
        )
        return otro is not None

    async def listar_exclusiones(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID
    ) -> Sequence[ExclusionCorpus]:
        contexto.exigir_investigador()
        resultado = await self._sesion.scalars(
            select(ExclusionCorpus)
            .where(ExclusionCorpus.coleccion_id == coleccion_id)
            .order_by(ExclusionCorpus.registrada_en, ExclusionCorpus.id)
        )
        return resultado.all()

    async def recontar(self, contexto: ContextoAcceso, coleccion: Coleccion) -> None:
        """Contadores del informe por tema: incluidos (recuperables), exclusiones y
        referencias del artículo O1 pendientes de PDF (T15)."""
        contexto.exigir_investigador()
        incluidas = await self._sesion.scalar(
            select(func.count(Documento.id)).where(
                Documento.coleccion_id == coleccion.id, recuperable()
            )
        )
        excluidas = await self._sesion.scalar(
            select(func.count(ExclusionCorpus.id)).where(
                ExclusionCorpus.coleccion_id == coleccion.id
            )
        )
        pendientes = await self._sesion.scalar(
            select(func.count(ReferenciaImportada.id)).where(
                ReferenciaImportada.coleccion_id == coleccion.id,
                ReferenciaImportada.estado == EstadoReferencia.PENDIENTE_PDF,
            )
        )
        await self._sesion.execute(
            update(Coleccion)
            .where(Coleccion.id == coleccion.id)
            .values(
                n_incluidas=incluidas or 0,
                n_excluidas=excluidas or 0,
                n_pendientes=pendientes or 0,
            )
        )
        await self._sesion.refresh(coleccion)

    async def por_reindexar(
        self, contexto: ContextoAcceso, modelo: str, revision: str, forzar: bool
    ) -> Sequence[Documento]:
        """Documentos recuperables cuyos vectores son de otro modelo o revisión."""
        contexto.exigir_investigador()
        consulta = select(Documento).where(recuperable()).order_by(Documento.creado_en)
        if not forzar:
            consulta = consulta.where(
                or_(
                    Documento.modelo_embeddings.is_distinct_from(modelo),
                    Documento.revision_embeddings.is_distinct_from(revision),
                )
            )
        resultado = await self._sesion.scalars(consulta)
        return resultado.all()

    async def buscar_denso(
        self,
        contexto: ContextoAcceso,
        coleccion_id: uuid.UUID,
        vector: Sequence[float],
        k: int,
    ) -> list[Encontrado]:
        """Consulta de prueba densa (distancia coseno, índice HNSW) en una colección."""
        contexto.exigir_investigador()
        distancia = Fragmento.embedding.cosine_distance(list(vector)).label("distancia")
        resultado = await self._sesion.execute(
            select(Fragmento, Documento, distancia)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                Fragmento.coleccion_id == coleccion_id,
                Fragmento.embedding.is_not(None),
                recuperable(),
            )
            .order_by(distancia)
            .limit(k)
        )
        return [Encontrado(f, d, 1.0 - float(dist)) for f, d, dist in resultado.all()]

    async def buscar_lexico(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID, consulta: str, k: int
    ) -> list[Encontrado]:
        """Consulta de prueba léxica (``tsvector`` con configuración simple, índice GIN)."""
        contexto.exigir_investigador()
        terminos = func.plainto_tsquery("simple", consulta)
        rango = func.ts_rank(Fragmento.texto_lexico, terminos).label("rango")
        resultado = await self._sesion.execute(
            select(Fragmento, Documento, rango)
            .join(Documento, Documento.id == Fragmento.documento_id)
            .where(
                Fragmento.coleccion_id == coleccion_id,
                Fragmento.texto_lexico.op("@@")(terminos),
                recuperable(),
            )
            .order_by(rango.desc(), Fragmento.orden)
            .limit(k)
        )
        return [Encontrado(f, d, float(r)) for f, d, r in resultado.all()]
