"""Estado de cada referencia de la lista del borrador (T20, actividades 3 y 4; RF-09, CP-12,
CP-13, RN-18; decisión T20-01). Determinista: el modelo no decide estados.

1. **Con DOI:** Crossref por DOI y, si no lo conoce, OpenAlex (los DOI de DataCite no están
   en Crossref). Si alguno la encuentra, se comparan título, autores y año.
2. **Sin DOI, o con un DOI que nadie conoce:** búsqueda por metadatos en Crossref y, si no
   aparece, en OpenAlex. El candidato es el de título más parecido, si llega al umbral del
   comparador de T14. Así se verifican también los libros (sin servicio de ISBN).
3. **Estado:**
   - ``verificada``: la obra existe y título, autores y año coinciden;
   - ``con_discrepancias``: la obra existe, pero algún dato difiere o falta. Un año que
     difiere, aunque sea en uno, cuenta (T20-01, b). Un DOI que lleva a otra obra también,
     nunca ``verificada`` (T20-01, a). Un DOI mal escrito de una obra que se encontró por
     metadatos se informa como discrepancia de DOI;
   - ``no_localizada``: todos los servicios respondieron y ninguno la encontró;
   - ``no_comprobable``: algún servicio no respondió y nada la encontró (RN-18: nunca
     ``no_localizada`` en ese caso).
"""

from __future__ import annotations

from collections.abc import Sequence

from app.agentes.esquemas import Discrepancia, EstadoReferencia, ReferenciaVerificada
from app.bibliografia.comparador import UMBRAL_TITULO, algun_autor_coincide, similitud_titulo
from app.bibliografia.interfaces import BuscadorBibliografico
from app.bibliografia.modelos import ConsultaBibliografica, Estado, MetadatosBibliograficos
from app.bibliografia.normalizacion import normalizar
from app.corpus.grobid import ReferenciaGrobid

MAX_TEXTO = 2000
MAX_AUTORES_MOSTRADOS = 3


def _autores(apellidos: Sequence[str]) -> str | None:
    if not apellidos:
        return None
    texto = ", ".join(apellidos[:MAX_AUTORES_MOSTRADOS])
    return f"{texto} et al." if len(apellidos) > MAX_AUTORES_MOSTRADOS else texto


def _apellidos_fuente(fuente: MetadatosBibliograficos) -> list[str]:
    return [a for a in (autor.apellidos_para_comparar() for autor in fuente.autores) if a]


def discrepancias(
    referencia: ReferenciaGrobid, fuente: MetadatosBibliograficos
) -> list[Discrepancia]:
    """Título, autores y año de la referencia frente a los de la fuente. Un dato que falta
    en la referencia es una discrepancia; uno que no trae la fuente no se compara."""
    halladas: list[Discrepancia] = []
    # Si el título de la fuente está tal cual en la entrada, el estudiante lo escribió bien
    # aunque GROBID haya tomado otra parte como título (por ejemplo, la revista).
    titulo_en_texto = bool(fuente.titulo) and normalizar(fuente.titulo) in normalizar(
        referencia.texto
    )
    if (
        fuente.titulo
        and not titulo_en_texto
        and (
            not referencia.titulo
            or similitud_titulo(referencia.titulo, fuente.titulo) < UMBRAL_TITULO
        )
    ):
        halladas.append(
            Discrepancia(
                campo="titulo", valor_borrador=referencia.titulo, valor_fuente=fuente.titulo
            )
        )
    apellidos = _apellidos_fuente(fuente)
    # Un primer autor cambiado es un error aunque los coautores coincidan: la cita en el
    # texto (APA) y el orden de la lista dependen de él.
    if apellidos and (
        not referencia.apellidos
        or not algun_autor_coincide(referencia.apellidos, fuente.autores)
        or not algun_autor_coincide(referencia.apellidos[:1], fuente.autores[:1])
    ):
        halladas.append(
            Discrepancia(
                campo="autores",
                valor_borrador=_autores(referencia.apellidos),
                valor_fuente=_autores(apellidos),
            )
        )
    if fuente.anio is not None and referencia.anio != fuente.anio:
        halladas.append(
            Discrepancia(
                campo="anio",
                valor_borrador=str(referencia.anio) if referencia.anio is not None else None,
                valor_fuente=str(fuente.anio),
            )
        )
    return halladas


def _mejor_por_titulo(
    referencia: ReferenciaGrobid, candidatos: Sequence[MetadatosBibliograficos]
) -> MetadatosBibliograficos | None:
    """El candidato de título más parecido, si llega al umbral; a igual título, el que
    comparte algún autor."""
    puntuados = [
        (
            similitud_titulo(referencia.titulo, c.titulo),
            algun_autor_coincide(referencia.apellidos, c.autores),
            c,
        )
        for c in candidatos
    ]
    validos = [p for p in puntuados if p[0] >= UMBRAL_TITULO]
    if not validos:
        return None
    return max(validos, key=lambda p: (round(p[0], 2), p[1]))[2]


class Verificador:
    def __init__(self, crossref: BuscadorBibliografico, openalex: BuscadorBibliografico) -> None:
        self._servicios = (crossref, openalex)

    async def verificar(self, indice: int, referencia: ReferenciaGrobid) -> ReferenciaVerificada:
        texto = referencia.texto[:MAX_TEXTO]
        fallas = False
        doi_sin_registro = False
        if referencia.doi:
            for servicio in self._servicios:
                resultado = await servicio.por_doi(referencia.doi)
                if resultado.estado is Estado.ENCONTRADO and resultado.metadatos is not None:
                    halladas = discrepancias(referencia, resultado.metadatos)
                    return ReferenciaVerificada(
                        indice=indice,
                        texto_original=texto,
                        estado=EstadoReferencia.CON_DISCREPANCIAS
                        if halladas
                        else EstadoReferencia.VERIFICADA,
                        metodo="doi",
                        discrepancias=halladas,
                        doi_encontrado=resultado.metadatos.doi or referencia.doi,
                    )
                fallas = fallas or resultado.estado is Estado.NO_COMPROBABLE
            doi_sin_registro = not fallas
        if not referencia.titulo:
            estado = EstadoReferencia.NO_COMPROBABLE if fallas else EstadoReferencia.NO_LOCALIZADA
            return ReferenciaVerificada(
                indice=indice,
                texto_original=texto,
                estado=estado,
                metodo="doi" if referencia.doi else None,
                discrepancias=[]
                if fallas
                else [Discrepancia(campo="titulo", valor_borrador=None, valor_fuente=None)],
            )
        consulta = ConsultaBibliografica(
            titulo=referencia.titulo, autores=referencia.apellidos, anio=referencia.anio
        )
        for servicio in self._servicios:
            busqueda = await servicio.buscar(consulta)
            if busqueda.estado is Estado.NO_COMPROBABLE:
                fallas = True
                continue
            fuente = _mejor_por_titulo(referencia, busqueda.candidatos)
            if fuente is None:
                continue
            halladas = discrepancias(referencia, fuente)
            if doi_sin_registro:
                halladas.insert(
                    0,
                    Discrepancia(
                        campo="doi", valor_borrador=referencia.doi, valor_fuente=fuente.doi
                    ),
                )
            return ReferenciaVerificada(
                indice=indice,
                texto_original=texto,
                estado=EstadoReferencia.CON_DISCREPANCIAS
                if halladas
                else EstadoReferencia.VERIFICADA,
                metodo="metadatos",
                discrepancias=halladas,
                doi_encontrado=fuente.doi,
            )
        return ReferenciaVerificada(
            indice=indice,
            texto_original=texto,
            estado=EstadoReferencia.NO_COMPROBABLE if fallas else EstadoReferencia.NO_LOCALIZADA,
            metodo="metadatos",
        )
