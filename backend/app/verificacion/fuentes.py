"""Comprobación 4: existencia de las fuentes que se entregan (T30; Fase 1, 6.7; RN-18).

Para cada documento que el resultado entrega como fuente recomendada:

* con DOI, se busca en Crossref (servicios de T14, con caché): encontrado confirma la fuente
  por DOI; no encontrado pasa a los metadatos;
* sin DOI (o con un DOI que Crossref no tiene), se confirma por metadatos si tiene título, al
  menos un autor y año;
* si Crossref no responde, la fuente queda "no comprobable" (RN-18): nunca inexistente. La
  comprobación no se supera, pero no pide reintento: regenerar no lo arregla.

Una fuente no confirmada sí pide reintento: el agente puede citar otros fragmentos.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.bd.enumeraciones import MetodoComprobacionFuentes
from app.bd.modelos import Documento
from app.bibliografia.interfaces import ServicioBibliografico
from app.bibliografia.modelos import Estado
from app.verificacion.comprobaciones import Comprobacion


def _metadatos_completos(documento: Documento) -> bool:
    return bool((documento.titulo or "").strip() and documento.autores and documento.anio)


async def comprobar_existencia(
    documentos: Sequence[Documento], crossref: ServicioBibliografico | None
) -> Comprobacion:
    unicos = list({d.id: d for d in documentos}.values())
    por_doi = por_metadatos = no_comprobables = 0
    no_confirmadas: list[str] = []
    for documento in unicos:
        if documento.doi and crossref is not None:
            resultado = await crossref.por_doi(documento.doi)
            if resultado.estado is Estado.ENCONTRADO:
                por_doi += 1
                continue
            if resultado.estado is Estado.NO_COMPROBABLE:
                no_comprobables += 1
                continue
        if _metadatos_completos(documento):
            por_metadatos += 1
        else:
            no_confirmadas.append((documento.titulo or "sin título")[:120])
    confirmadas = por_doi + por_metadatos
    metodo = (
        None
        if not confirmadas
        else MetodoComprobacionFuentes.MIXTO
        if por_doi and por_metadatos
        else MetodoComprobacionFuentes.DOI
        if por_doi
        else MetodoComprobacionFuentes.METADATOS
    )
    motivos = [f"fuente sin existencia comprobada: {t}" for t in no_confirmadas]
    if no_comprobables:
        motivos.append(
            f"{no_comprobables} fuentes no comprobables: el servicio bibliográfico no respondió"
        )
    return Comprobacion(
        numero=4,
        nombre="existencia_de_fuentes",
        superada=confirmadas == len(unicos),
        reintentable=bool(no_confirmadas),
        motivos=motivos,
        datos={
            "citadas": len(unicos),
            "confirmadas": confirmadas,
            "no_comprobables": no_comprobables,
            "metodo": metodo.value if metodo else None,
        },
    )
