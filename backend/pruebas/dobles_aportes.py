"""Dobles del aporte de fuentes (T32): servicios bibliográficos con obras ficticias y el
servicio de aportes armado con el canal ficticio, los embeddings de bolsa de palabras y el
formateador CSL local (sin red ni modelo real)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.aportes.servicio import ServicioAportes
from app.bibliografia.comparador import similitud_titulo
from app.bibliografia.modelos import (
    Autor,
    ConsultaBibliografica,
    Estado,
    MetadatosBibliograficos,
    Motivo,
    ResultadoBibliografico,
    Servicio,
)
from app.bibliografia.referencias import ConstructorReferencias
from app.corpus.almacen import AlmacenArchivos
from app.corpus.indexacion import Indexador
from app.llm.interfaces import ModeloLenguaje
from pruebas.dobles_corpus import CanalFicticio, EmbeddingsFicticios

RESUMEN_MONETARIA = (
    "Este estudio ficticio analiza los efectos de la política monetaria en la inflación de"
    " economías emergentes entre 2010 y 2020. La política monetaria restrictiva redujo la"
    " inflación de los precios al consumidor en las economías emergentes estudiadas. Los"
    " efectos de la tasa de interés sobre la inflación aparecieron a los seis meses y se"
    " mantuvieron dos años. En las economías emergentes con metas de inflación, los efectos"
    " de la política monetaria fueron mayores. Los resultados sugieren que la credibilidad"
    " del banco central modera los efectos de la política monetaria en la inflación."
)
OBRA_MONETARIA = MetadatosBibliograficos(
    doi="10.5555/monetaria.2024",
    titulo="Efectos de la política monetaria en la inflación de economías emergentes",
    autores=[Autor(apellidos="Ficticia", nombres="Ana")],
    anio=2024,
    revista="Revista Ficticia de Economía",
    resumen=RESUMEN_MONETARIA,
)
OBRA_SIN_DOI = MetadatosBibliograficos(
    titulo="Tasas de interés y precios en mercados emergentes ficticios",
    autores=[Autor(apellidos="Prueba", nombres="Luis")],
    anio=2023,
    revista="Cuadernos Ficticios",
)
RESUMEN_SIN_DOI = (
    "Las tasas de interés altas moderaron la inflación de los precios en economías emergentes"
    " ficticias durante dos años."
)


@dataclass
class BibliografiaFicticia:
    """Un servicio bibliográfico: obras por DOI y candidatos de búsqueda por título."""

    servicio: Servicio
    por_doi_: dict[str, MetadatosBibliograficos] = field(default_factory=dict)
    obras: list[MetadatosBibliograficos] = field(default_factory=list)
    caido: bool = False
    consultas: int = 0

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        self.consultas += 1
        if self.caido:
            return ResultadoBibliografico.no_comprobable(self.servicio, Motivo.SIN_CONEXION)
        obra = self.por_doi_.get(doi)
        if obra is None:
            return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.NO_EXISTE)
        return ResultadoBibliografico(
            servicio=self.servicio, estado=Estado.ENCONTRADO, metadatos=obra
        )

    async def buscar(self, consulta: ConsultaBibliografica) -> ResultadoBibliografico:
        self.consultas += 1
        if self.caido:
            return ResultadoBibliografico.no_comprobable(self.servicio, Motivo.SIN_CONEXION)
        candidatos = [o for o in self.obras if similitud_titulo(consulta.titulo, o.titulo) > 0.5]
        if not candidatos:
            return ResultadoBibliografico.no_encontrado(self.servicio, Motivo.SIN_COINCIDENCIAS)
        # La búsqueda, como la de Crossref, no trae el resumen.
        return ResultadoBibliografico(
            servicio=self.servicio,
            estado=Estado.ENCONTRADO,
            candidatos=[c.model_copy(update={"resumen": None}) for c in candidatos],
        )


def bibliografia_ficticia() -> tuple[BibliografiaFicticia, BibliografiaFicticia]:
    """Crossref conoce la obra con DOI; OpenAlex, además, la obra sin DOI con su resumen."""
    con_doi_sin_resumen = OBRA_SIN_DOI.model_copy(update={"doi": "10.5555/tasas.2023"})
    crossref = BibliografiaFicticia(
        Servicio.CROSSREF,
        por_doi_={OBRA_MONETARIA.doi or "": OBRA_MONETARIA},
        obras=[OBRA_MONETARIA, con_doi_sin_resumen],
    )
    openalex = BibliografiaFicticia(
        Servicio.OPENALEX,
        por_doi_={
            "10.5555/tasas.2023": con_doi_sin_resumen.model_copy(
                update={"resumen": RESUMEN_SIN_DOI}
            )
        },
    )
    return crossref, openalex


def servicio_ficticio(
    crossref: BibliografiaFicticia,
    openalex: BibliografiaFicticia,
    archivos: Path,
    reloj: Callable[[], datetime],
    modelo: ModeloLenguaje | None = None,
) -> tuple[ServicioAportes, CanalFicticio]:
    canal = CanalFicticio()
    indexador = Indexador(canal, EmbeddingsFicticios(), AlmacenArchivos(archivos))

    async def dar() -> Indexador:
        return indexador

    return (
        ServicioAportes(
            servicios=[crossref, openalex],
            citas=ConstructorReferencias(None),
            modelo=modelo,
            embebedor=dar,
            canal_pdf=dar,
            reloj=reloj,
        ),
        canal,
    )
