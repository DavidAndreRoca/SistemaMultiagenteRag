"""Repositorio del importador de referencias del artículo O1 (A2, T15).

Todo método exige un ``ContextoAcceso`` de rol A2 y filtra por la colección científica
del tema: las importaciones y sus referencias no son datos de caso.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import EstadoImportacion, EstadoReferencia
from app.bd.modelos import Documento, ImportacionReferencias, ReferenciaImportada
from app.repositorios.contexto import ContextoAcceso

EN_CURSO = (EstadoImportacion.EN_COLA, EstadoImportacion.EN_PROCESO)


class RepositorioImportacion:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def agregar(
        self, contexto: ContextoAcceso, importacion: ImportacionReferencias
    ) -> ImportacionReferencias:
        contexto.exigir_investigador()
        importacion.creada_por_id = contexto.cuenta_id
        self._sesion.add(importacion)
        await self._sesion.flush()
        return importacion

    async def obtener(
        self, contexto: ContextoAcceso, importacion_id: uuid.UUID
    ) -> ImportacionReferencias | None:
        contexto.exigir_investigador()
        return await self._sesion.get(ImportacionReferencias, importacion_id)

    async def marcar_interrumpidas(
        self, contexto: ContextoAcceso, activas: Collection[uuid.UUID], ahora: datetime
    ) -> int:
        """Las importaciones en curso que ningún proceso atiende (tras un reinicio)."""
        contexto.exigir_investigador()
        consulta = (
            update(ImportacionReferencias)
            .where(ImportacionReferencias.estado.in_(EN_CURSO))
            .values(estado=EstadoImportacion.INTERRUMPIDA, terminada_en=ahora)
        )
        if activas:
            consulta = consulta.where(ImportacionReferencias.id.not_in(list(activas)))
        resultado = await self._sesion.execute(consulta)
        return int(resultado.rowcount or 0)  # type: ignore[attr-defined]

    async def referencia_por_clave(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID, clave: str
    ) -> ReferenciaImportada | None:
        contexto.exigir_investigador()
        return await self._sesion.scalar(
            select(ReferenciaImportada).where(
                ReferenciaImportada.coleccion_id == coleccion_id,
                ReferenciaImportada.clave == clave,
            )
        )

    async def referencia(
        self, contexto: ContextoAcceso, referencia_id: uuid.UUID
    ) -> ReferenciaImportada | None:
        contexto.exigir_investigador()
        return await self._sesion.get(ReferenciaImportada, referencia_id)

    async def agregar_referencia(
        self, contexto: ContextoAcceso, referencia: ReferenciaImportada
    ) -> ReferenciaImportada:
        contexto.exigir_investigador()
        self._sesion.add(referencia)
        await self._sesion.flush()
        return referencia

    async def referencias(
        self,
        contexto: ContextoAcceso,
        coleccion_id: uuid.UUID,
        estado: EstadoReferencia | None = None,
    ) -> Sequence[ReferenciaImportada]:
        contexto.exigir_investigador()
        consulta = select(ReferenciaImportada).where(
            ReferenciaImportada.coleccion_id == coleccion_id
        )
        if estado is not None:
            consulta = consulta.where(ReferenciaImportada.estado == estado)
        resultado = await self._sesion.scalars(
            consulta.order_by(ReferenciaImportada.actualizada_en, ReferenciaImportada.id)
        )
        return resultado.all()

    async def conteos(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID
    ) -> list[tuple[EstadoReferencia, str | None, bool, int]]:
        """Referencias por estado, motivo y si son de acceso abierto comprobado."""
        contexto.exigir_investigador()
        abierta = func.coalesce(ReferenciaImportada.estado_oa.not_in(["closed"]), False)
        resultado = await self._sesion.execute(
            select(
                ReferenciaImportada.estado,
                ReferenciaImportada.motivo,
                abierta,
                func.count(ReferenciaImportada.id),
            )
            .where(ReferenciaImportada.coleccion_id == coleccion_id)
            .group_by(ReferenciaImportada.estado, ReferenciaImportada.motivo, abierta)
        )
        return [(fila[0], fila[1], bool(fila[2]), int(fila[3])) for fila in resultado.all()]

    async def pendientes(self, contexto: ContextoAcceso, coleccion_id: uuid.UUID) -> int:
        contexto.exigir_investigador()
        cantidad = await self._sesion.scalar(
            select(func.count(ReferenciaImportada.id)).where(
                ReferenciaImportada.coleccion_id == coleccion_id,
                ReferenciaImportada.estado == EstadoReferencia.PENDIENTE_PDF,
            )
        )
        return int(cantidad or 0)

    async def documento_por_doi(
        self, contexto: ContextoAcceso, coleccion_id: uuid.UUID, doi: str
    ) -> Documento | None:
        contexto.exigir_investigador()
        return await self._sesion.scalar(
            select(Documento)
            .where(Documento.coleccion_id == coleccion_id, func.lower(Documento.doi) == doi)
            .order_by(Documento.creado_en)
            .limit(1)
        )
