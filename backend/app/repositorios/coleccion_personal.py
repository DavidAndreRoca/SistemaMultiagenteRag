"""Colección personal del caso (T32; RF-13, CU-12, 4.5).

Las fuentes que el caso aporta tras una abstención se indexan solo aquí: la colección
personal se toma siempre del caso del contexto, nunca de un identificador que llegue de
afuera, así que un aporte no puede entrar en una colección compartida ni en la de otro
caso. La recuperación de D4 la incluye por el tipo de solicitud (``colecciones.py``).
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import EstadoDocumento, TipoColeccion
from app.bd.modelos import Coleccion, Documento, Fragmento
from app.repositorios.contexto import ContextoAcceso


class ColeccionPersonalInexistente(RuntimeError):
    """El caso no tiene colección personal (se crea con el caso; no debería ocurrir)."""


class RepositorioColeccionPersonal:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def coleccion(self, contexto: ContextoAcceso) -> Coleccion:
        caso_id = contexto.caso_exigido()
        coleccion = await self._sesion.scalar(
            select(Coleccion).where(
                Coleccion.tipo == TipoColeccion.PERSONAL, Coleccion.caso_id == caso_id
            )
        )
        if coleccion is None:
            raise ColeccionPersonalInexistente()
        return coleccion

    async def duplicado(
        self, contexto: ContextoAcceso, huella_texto: str | None, doi: str | None
    ) -> Documento | None:
        """Documento de la colección personal con el mismo DOI o el mismo texto (CP-17)."""
        coleccion = await self.coleccion(contexto)
        condiciones = []
        if doi:
            condiciones.append(func.lower(Documento.doi) == doi.lower())
        if huella_texto:
            condiciones.append(Documento.huella_sha256 == huella_texto)
        if not condiciones:
            return None
        documento: Documento | None = await self._sesion.scalar(
            select(Documento)
            .where(Documento.coleccion_id == coleccion.id, or_(*condiciones))
            .order_by(Documento.creado_en)
            .limit(1)
        )
        return documento

    async def agregar_documento(
        self, contexto: ContextoAcceso, documento: Documento, fragmentos: Sequence[Fragmento]
    ) -> Documento:
        """Guarda el documento y sus fragmentos en la colección personal del caso (se ignora
        la colección que traiga)."""
        coleccion = await self.coleccion(contexto)
        documento.coleccion_id = coleccion.id
        self._sesion.add(documento)
        await self._sesion.flush()
        for fragmento in fragmentos:
            fragmento.documento_id = documento.id
            fragmento.coleccion_id = coleccion.id
            self._sesion.add(fragmento)
        await self._sesion.flush()
        incluidas = await self._sesion.scalar(
            select(func.count(Documento.id)).where(
                Documento.coleccion_id == coleccion.id,
                Documento.estado == EstadoDocumento.ACTIVO,
            )
        )
        await self._sesion.execute(
            update(Coleccion).where(Coleccion.id == coleccion.id).values(n_incluidas=incluidas)
        )
        return documento
