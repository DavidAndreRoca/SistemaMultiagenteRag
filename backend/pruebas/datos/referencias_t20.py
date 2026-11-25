# ruff: noqa: E501  (tabla de referencias ficticias: una por línea)
"""Borradores ficticios con lista de referencias para la verificación (T20, CP-12, CP-13).

Todo es ficticio: autores, títulos, revistas y DOI (prefijo 10.5555, reservado para
pruebas). Cada obra declara su escenario. Los dobles de Crossref y OpenAlex responden a
partir de este módulo y la clave (``ESPERADO``) dice qué debe informar el sistema.

El mismo conjunto de obras se escribe en IEEE (numérica, en orden de aparición) y en
APA 7 (autor y año, en orden alfabético). En ambas:
- la obra ``NO_CITADA`` está en la lista, pero ninguna cita la alcanza;
- el texto cita una obra que no está en la lista (``CITA_SIN_ENTRADA``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Escenario(StrEnum):
    CORRECTA_DOI = "correcta_doi"  # con DOI y datos correctos: verificada
    CORRECTA_SIN_DOI = "correcta_sin_doi"  # sin DOI, la búsqueda la encuentra: verificada
    ANIO = "anio"  # año corrido en uno: con discrepancias (T20-01, b)
    TITULO = "titulo"  # título cambiado: con discrepancias
    AUTOR = "autor"  # primer autor cambiado, sin DOI: con discrepancias
    FABRICADA = "fabricada"  # no existe, sin DOI: no localizada
    DOI_AJENO = "doi_ajeno"  # fabricada con el DOI real de otra obra: con discrepancias (T20-01, a)
    DOI_INEXISTENTE = "doi_inexistente"  # fabricada con un DOI que no existe: no localizada
    LIBRO = "libro"  # libro sin DOI, por metadatos: verificada (T20-01, f)
    CAIDA = "caida"  # el servicio no responde para esta obra: no comprobable (RN-18)
    NO_CITADA = "no_citada"  # correcta, pero ninguna cita la alcanza


@dataclass(frozen=True)
class Obra:
    escenario: Escenario
    autores: tuple[tuple[str, str], ...]  # (apellido, inicial) tal como los escribe el estudiante
    anio: int  # el que escribe el estudiante
    titulo: str  # el que escribe el estudiante
    revista: str | None  # None en libros
    doi: str | None  # el que escribe el estudiante
    editorial: str | None = None
    # Lo que registra la fuente cuando difiere de lo escrito
    anio_real: int | None = None
    titulo_real: str | None = None
    autores_reales: tuple[tuple[str, str], ...] | None = None
    doi_real: str | None = None
    existe: bool = True

    @property
    def fuente(self) -> dict[str, object]:
        return {
            "titulo": self.titulo_real or self.titulo,
            "autores": self.autores_reales or self.autores,
            "anio": self.anio_real or self.anio,
            "doi": self.doi_real if self.doi_real is not None else self.doi,
        }


E = Escenario
OBRAS = [
    Obra(
        E.CORRECTA_DOI,
        (("Quispe", "A."), ("Huamán", "L.")),
        2021,
        "Tutoría entre pares y ansiedad ante la estadística en universitarios",
        "Revista Ficticia de Pedagogía",
        "10.5555/t20.quispe.2021",
    ),
    Obra(
        E.CORRECTA_SIN_DOI,
        (("Mamani", "R."),),
        2019,
        "Retroalimentación formativa en cursos de metodología de la investigación",
        "Educación y Datos Imaginarios",
        None,
        doi_real="10.5555/t20.mamani.2019",
    ),
    Obra(
        E.ANIO,
        (("Torres", "C."), ("Paredes", "M.")),
        2022,
        "Escritura académica asistida por herramientas digitales",
        "Cuadernos Ficticios de Escritura",
        "10.5555/t20.torres.2021",
        anio_real=2021,
    ),
    Obra(
        E.TITULO,
        (("Rojas", "E."),),
        2020,
        "Uso de chatbots en la enseñanza secundaria rural",
        "Revista Andina Ficticia",
        "10.5555/t20.rojas.2020",
        titulo_real="Percepciones docentes sobre la evaluación por competencias en zonas rurales",
    ),
    Obra(
        E.AUTOR,
        (("Gutiérrez", "P."),),
        2018,
        "Comercio electrónico en microempresas de la costa sur",
        "Gestión Ficticia",
        None,
        autores_reales=(("Salazar", "V."),),
        doi_real="10.5555/t20.salazar.2018",
    ),
    Obra(
        E.FABRICADA,
        (("Condori", "J."),),
        2023,
        "Tutores neuronales en la sierra andina: un ensayo controlado",
        "Revista Inexistente de Tecnología Educativa",
        None,
        existe=False,
    ),
    Obra(
        E.DOI_AJENO,
        (("Villanueva", "S."),),
        2022,
        "Inteligencia artificial generativa y plagio en la universidad",
        "Ética Ficticia",
        "10.5555/t20.quispe.2021",
        existe=False,
    ),
    Obra(
        E.DOI_INEXISTENTE,
        (("Benites", "F."),),
        2021,
        "Algoritmos de recomendación para bibliotecas escolares",
        "Bibliotecología Imaginaria",
        "10.5555/t20.no.existe",
        existe=False,
    ),
    Obra(
        E.LIBRO,
        (("Ramos", "G."),),
        2015,
        "Metodología de la investigación educativa",
        None,
        None,
        editorial="Editorial Ficticia",
    ),
    Obra(
        E.CAIDA,
        (("Cárdenas", "N."),),
        2017,
        "Brecha digital en hogares de estudiantes de secundaria",
        "Sociedad Ficticia",
        "10.5555/t20.cardenas.2017",
    ),
    Obra(
        E.NO_CITADA,
        (("Espinoza", "H."),),
        2016,
        "Lectura crítica de artículos científicos en pregrado",
        "Docencia Ficticia",
        "10.5555/t20.espinoza.2016",
    ),
]
# Cita del texto que no tiene entrada en la lista.
CITA_SIN_ENTRADA = (("Mendoza", "T."), 2018)

ESTADO_ESPERADO = {
    E.CORRECTA_DOI: "verificada",
    E.CORRECTA_SIN_DOI: "verificada",
    E.ANIO: "con_discrepancias",
    E.TITULO: "con_discrepancias",
    E.AUTOR: "con_discrepancias",
    E.FABRICADA: "no_localizada",
    E.DOI_AJENO: "con_discrepancias",
    E.DOI_INEXISTENTE: "no_localizada",
    E.LIBRO: "verificada",
    E.CAIDA: "no_comprobable",
    E.NO_CITADA: "verificada",
}
CAMPOS_ESPERADOS = {
    E.ANIO: {"anio"},
    E.TITULO: {"titulo"},
    E.AUTOR: {"autores"},
    E.DOI_AJENO: {"titulo", "autores", "anio"},
}
FABRICADAS = {E.FABRICADA, E.DOI_AJENO, E.DOI_INEXISTENTE}


# ------------------------------------------------------------------------------ IEEE


def _ieee_autores(autores: tuple[tuple[str, str], ...]) -> str:
    nombres = [f"{inicial} {apellido}" for apellido, inicial in autores]
    return (
        " and ".join(nombres)
        if len(nombres) < 3
        else ", ".join(nombres[:-1]) + ", and " + nombres[-1]
    )


def entrada_ieee(numero: int, obra: Obra) -> str:
    autores = _ieee_autores(obra.autores)
    if obra.revista is None:
        return f"[{numero}] {autores}, {obra.titulo}. Lima, Perú: {obra.editorial}, {obra.anio}."
    doi = f", doi: {obra.doi}" if obra.doi else ""
    return f"[{numero}] {autores}, \u201c{obra.titulo},\u201d {obra.revista}, vol. 4, no. 2, pp. 10-25, {obra.anio}{doi}."


def lista_ieee() -> list[Obra]:
    """En IEEE, en orden de aparición: la no citada va al final."""
    return [o for o in OBRAS if o.escenario is not E.NO_CITADA] + [
        o for o in OBRAS if o.escenario is E.NO_CITADA
    ]


def cuerpo_ieee() -> list[str]:
    n = {o.escenario: i for i, o in enumerate(lista_ieee(), start=1)}
    sin_entrada = len(OBRAS) + 1
    return [
        f"La tutoría entre pares reduce la ansiedad ante la estadística [{n[E.CORRECTA_DOI]}], y la retroalimentación formativa mejora el aprendizaje de la metodología [{n[E.CORRECTA_SIN_DOI]}]\u2013[{n[E.ANIO]}].",
        f"Los chatbots ya se usan en zonas rurales [{n[E.TITULO]}], igual que el comercio electrónico en las microempresas [{n[E.AUTOR]}, {n[E.FABRICADA]}].",
        f"El plagio con inteligencia artificial preocupa a las universidades [{n[E.DOI_AJENO]}], [{n[E.DOI_INEXISTENTE]}], y conviene seguir un método riguroso [{n[E.LIBRO]}].",
        f"La brecha digital persiste en los hogares [{n[E.CAIDA]}] y en las escuelas públicas [{sin_entrada}].",
    ]


# ------------------------------------------------------------------------------ APA 7


def _apa_autores(autores: tuple[tuple[str, str], ...]) -> str:
    nombres = [f"{apellido}, {inicial}" for apellido, inicial in autores]
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + ", & " + nombres[-1]


def entrada_apa(obra: Obra) -> str:
    autores = _apa_autores(obra.autores)
    if obra.revista is None:
        return f"{autores} ({obra.anio}). {obra.titulo}. {obra.editorial}."
    doi = f" https://doi.org/{obra.doi}" if obra.doi else ""
    return f"{autores} ({obra.anio}). {obra.titulo}. {obra.revista}, 4(2), 10-25.{doi}"


def lista_apa() -> list[Obra]:
    """En APA 7, en orden alfabético por el primer apellido."""
    return sorted(OBRAS, key=lambda o: o.autores[0][0].replace("á", "a").replace("Á", "A"))


def _cita_apa(obra: Obra) -> str:
    apellidos = [a for a, _ in obra.autores]
    autor = apellidos[0] if len(apellidos) == 1 else f"{apellidos[0]} y {apellidos[1]}"
    return f"{autor}, {obra.anio}"


def cuerpo_apa() -> list[str]:
    o = {obra.escenario: obra for obra in OBRAS}
    return [
        f"La tutoría entre pares reduce la ansiedad ante la estadística ({_cita_apa(o[E.CORRECTA_DOI])}), y {o[E.CORRECTA_SIN_DOI].autores[0][0]} ({o[E.CORRECTA_SIN_DOI].anio}) muestra que la retroalimentación formativa mejora el aprendizaje ({_cita_apa(o[E.ANIO])}).",
        f"Los chatbots ya se usan en zonas rurales ({_cita_apa(o[E.TITULO])}), igual que el comercio electrónico en las microempresas ({_cita_apa(o[E.AUTOR])}; {_cita_apa(o[E.FABRICADA])}).",
        f"El plagio con inteligencia artificial preocupa a las universidades ({_cita_apa(o[E.DOI_AJENO])}; {_cita_apa(o[E.DOI_INEXISTENTE])}), y conviene seguir un método riguroso ({_cita_apa(o[E.LIBRO])}).",
        f"La brecha digital persiste en los hogares ({_cita_apa(o[E.CAIDA])}) y en las escuelas públicas ({CITA_SIN_ENTRADA[0][0]}, {CITA_SIN_ENTRADA[1]}).",
    ]


# ------------------------------------------------------------------------------ clave


def esperado(norma: str) -> dict[str, object]:
    """Lo que debe informar el sistema para el borrador de la norma."""
    lista = lista_ieee() if norma == "ieee" else lista_apa()
    if norma == "ieee":
        sin_entrada = [f"[{len(OBRAS) + 1}]"]
    else:
        sin_entrada = [f"({CITA_SIN_ENTRADA[0][0]}, {CITA_SIN_ENTRADA[1]})"]
    return {
        "estados": {i: ESTADO_ESPERADO[o.escenario] for i, o in enumerate(lista, start=1)},
        "campos": {
            i: CAMPOS_ESPERADOS[o.escenario]
            for i, o in enumerate(lista, start=1)
            if o.escenario in CAMPOS_ESPERADOS
        },
        "fabricadas": [i for i, o in enumerate(lista, start=1) if o.escenario in FABRICADAS],
        "citas_sin_entrada": sin_entrada,
        "entradas_no_citadas": [
            i for i, o in enumerate(lista, start=1) if o.escenario is E.NO_CITADA
        ],
    }


TITULO_BORRADOR = "Tutoría, escritura y tecnología en la universidad: un borrador ficticio"
INTRODUCCION = "Este borrador ficticio sirve para probar la verificación de referencias."
