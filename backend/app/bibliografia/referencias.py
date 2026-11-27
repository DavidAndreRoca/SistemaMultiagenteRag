"""Constructor de referencias desde los metadatos guardados (T18-01, apartado 5; RN-17).

Para los identificadores ``F<n>`` citados en una solicitud obtiene sus documentos, siempre
con el caso del contexto, y arma una referencia por documento en la norma del caso:

* **Con DOI:** la cita del registro del DOI por doi.org, en el estilo CSL de la norma
  (cliente y caché de T14).
* **Sin DOI, o si doi.org no responde:** el formateador CSL local con los metadatos
  guardados (``app/bibliografia/csl.py``).

Ningún texto de referencia sale de un modelo de lenguaje.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.bd.modelos import Documento
from app.bibliografia.csl import ESTILOS, NormaNoAdmitida, formatear, quitar_numero
from app.bibliografia.doi import estilo_csl
from app.bibliografia.interfaces import FormateadorDeCitas
from app.bibliografia.modelos import Estado
from app.comun.registro import obtener_registrador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo

_registro = obtener_registrador("bibliografia")


class MetodoReferencia(StrEnum):
    DOI = "doi"  # cita del registro del DOI (doi.org)
    CSL_LOCAL = "csl_local"  # formateador local con los metadatos guardados


class ReferenciaArmada(BaseModel):
    model_config = ConfigDict(frozen=True)

    documento_id: uuid.UUID
    identificadores: list[str]  # los F<n> que citan este documento
    norma: str
    texto: str
    metodo: MetodoReferencia
    doi: str | None
    url_acceso_abierto: str | None


def metadatos(documento: Documento) -> dict[str, Any]:
    return {
        "titulo": documento.titulo,
        "autores": list(documento.autores or []),
        "anio": documento.anio,
        "revista_editorial": documento.revista_editorial,
        "isbn": documento.isbn,
        "doi": documento.doi,
        "idioma": documento.idioma,
        "url": documento.url_acceso_abierto,
    }


class ConstructorReferencias:
    def __init__(self, citas_doi: FormateadorDeCitas | None) -> None:
        """Sin ``citas_doi`` todas las referencias se arman en local."""
        self._citas_doi = citas_doi

    async def construir(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud_id: uuid.UUID,
        identificadores: Sequence[str],
        norma: str,
    ) -> list[ReferenciaArmada]:
        if norma not in ESTILOS:
            raise NormaNoAdmitida(f"norma sin estilo CSL: {norma}")
        citados = await unidad.fragmentos_recuperados.documentos_citados(
            contexto, solicitud_id, list(dict.fromkeys(identificadores))
        )
        documentos: dict[uuid.UUID, Documento] = {}
        por_documento: dict[uuid.UUID, list[str]] = {}
        for identificador, documento in citados:
            documentos.setdefault(documento.id, documento)
            por_documento.setdefault(documento.id, []).append(identificador)
        referencias = [
            await self._armar(documentos[d], ids, norma) for d, ids in por_documento.items()
        ]
        _registro.info(
            "referencias armadas",
            extra={
                "tipo_evento": "referencias",
                "solicitud_id": str(solicitud_id),
                "norma": norma,
                "documentos": len(referencias),
                "por_doi": sum(1 for r in referencias if r.metodo is MetodoReferencia.DOI),
            },
        )
        return referencias

    async def de_documento(self, documento: Documento, norma: str) -> ReferenciaArmada:
        """Referencia de un documento suelto: la cita propuesta de una fuente aportada (T32)."""
        if norma not in ESTILOS:
            raise NormaNoAdmitida(f"norma sin estilo CSL: {norma}")
        return await self._armar(documento, [], norma)

    async def _armar(
        self, documento: Documento, identificadores: list[str], norma: str
    ) -> ReferenciaArmada:
        texto, metodo = None, MetodoReferencia.CSL_LOCAL
        estilo = estilo_csl(norma)
        if documento.doi and self._citas_doi is not None and estilo is not None:
            resultado = await self._citas_doi.cita(documento.doi, estilo)
            if resultado.estado is Estado.ENCONTRADO and resultado.cita:
                texto, metodo = quitar_numero(resultado.cita), MetodoReferencia.DOI
        if texto is None:
            texto = formatear(norma, metadatos(documento))
        return ReferenciaArmada(
            documento_id=documento.id,
            identificadores=identificadores,
            norma=norma,
            texto=texto,
            metodo=metodo,
            doi=documento.doi,
            url_acceso_abierto=documento.url_acceso_abierto,
        )
