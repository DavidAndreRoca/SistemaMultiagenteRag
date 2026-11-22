# ruff: noqa: E501  (tabla de referencias ficticias: una por línea)
"""Artículo O1 ficticio para probar el importador de referencias (T15).

Todo es ficticio: autores, títulos, revistas y DOI (prefijo 10.5555, reservado para
pruebas). Cada referencia declara qué debe pasarle en las pruebas, que simulan los
servicios bibliográficos y la descarga a partir de este módulo. El cuerpo lleva una
``FRASE_DEL_CUERPO`` única: después de importar no debe aparecer en ningún lado (RN-19).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

FRASE_DEL_CUERPO = (
    "Esta frase ficticia aparece solo en el cuerpo del artículo O1 de prueba y nunca debe"
    " quedar guardada después de importar sus referencias."
)
TITULO = "Tutoría entre pares y ansiedad ante la estadística: un artículo O1 ficticio"


class Escenario(StrEnum):
    INCLUIDA = "incluida"  # DOI, acceso abierto con PDF directo que se descarga e indexa
    DESCARGA_403 = "descarga_403"  # PDF directo que el sitio rechaza: pendiente de PDF
    DESCARGA_HTML = "descarga_html"  # el "PDF" es una página HTML: pendiente de PDF
    SIN_ENLACE_DIRECTO = "sin_enlace_directo"  # abierto, sin PDF directo: pendiente
    CERRADA = "cerrada"  # sin acceso abierto: excluida
    SIN_UNPAYWALL = "sin_unpaywall"  # Unpaywall no la conoce: excluida (no comprobado OA)
    POR_METADATOS = "por_metadatos"  # sin DOI; la búsqueda la confirma con DOI: incluida
    NO_LOCALIZADA = "no_localizada"  # sin DOI; la búsqueda no la confirma: excluida
    SIN_DOI = "sin_doi"  # sin DOI; confirmada, pero la obra no tiene DOI: excluida
    CAIDA = "caida"  # Crossref no responde: no comprobable (RN-18)
    ESCANEADA = "escaneada"  # el PDF descargado no tiene capa de texto: excluida (T10)


@dataclass(frozen=True)
class Referencia:
    escenario: Escenario
    apellido: str
    inicial: str
    anio: int
    titulo: str
    revista: str
    doi: str | None  # escrito en la referencia
    doi_real: str | None = None  # el que encuentra la búsqueda (escenario por metadatos)

    def entrada(self) -> str:
        """La entrada en APA, como la escribiría un autor."""
        texto = f"{self.apellido}, {self.inicial}. ({self.anio}). {self.titulo}. {self.revista}."
        return f"{texto} https://doi.org/{self.doi}" if self.doi else texto


def _doi(n: int) -> str:
    return f"10.5555/sma.o1.{n:02d}"


E = Escenario
REFERENCIAS: list[Referencia] = [
    *(
        Referencia(E.INCLUIDA, apellido, "A", 2020 + n % 5, titulo, "Revista Ficticia de Pedagogía", _doi(n))
        for n, (apellido, titulo) in enumerate(
            [
                ("Quispe", "Ansiedad estadística en estudiantes de primer año"),
                ("Huamán", "Tutoría entre pares en cursos de métodos cuantitativos"),
                ("Mendoza", "Autoeficacia y rendimiento en estadística universitaria"),
                ("Ccahuana", "Aprendizaje cooperativo en la enseñanza de la probabilidad"),
                ("Salazar", "Actitudes hacia la estadística en ciencias sociales"),
                ("Paredes", "Evaluación formativa en asignaturas de investigación"),
                ("Vilca", "Mentoría académica y permanencia estudiantil"),
            ],
            start=1,
        )
    ),
    Referencia(E.DESCARGA_403, "Arroyo", "B", 2021, "Programas de nivelación matemática en la universidad", "Revista Ficticia de Docencia", _doi(8)),
    Referencia(E.DESCARGA_HTML, "Benavides", "C", 2022, "Motivación y estrategias de estudio en estadística", "Revista Ficticia de Docencia", _doi(9)),
    *(
        Referencia(E.SIN_ENLACE_DIRECTO, apellido, "D", 2019, titulo, "Revista Ficticia de Educación", _doi(n))
        for n, (apellido, titulo) in enumerate(
            [
                ("Cárdenas", "Ansiedad matemática y elección de carrera"),
                ("Delgado", "Clima de aula en cursos de estadística aplicada"),
                ("Espinoza", "Retroalimentación entre pares en educación superior"),
            ],
            start=10,
        )
    ),
    *(
        Referencia(E.CERRADA, apellido, "E", 2018, titulo, "Revista Ficticia Cerrada", _doi(n))
        for n, (apellido, titulo) in enumerate(
            [
                ("Flores", "Medición de la ansiedad ante los exámenes"),
                ("Gutiérrez", "Rendimiento académico y apoyo social percibido"),
                ("Herrera", "Diseños cuasiexperimentales en educación"),
            ],
            start=13,
        )
    ),
    Referencia(E.SIN_UNPAYWALL, "Ibáñez", "F", 2017, "Hábitos de estudio en estudiantes de ingeniería", "Revista Ficticia Regional", _doi(16)),
    Referencia(E.POR_METADATOS, "Jiménez", "G", 2020, "Escalas de ansiedad estadística validadas en el Perú", "Revista Ficticia de Psicometría", None, _doi(17)),
    Referencia(E.POR_METADATOS, "Lazo", "H", 2021, "Efectos de la tutoría virtual en estudiantes de primer ciclo", "Revista Ficticia de Psicometría", None, _doi(18)),
    Referencia(E.NO_LOCALIZADA, "Montes", "I", 2015, "Informe interno sobre deserción en cursos de estadística", "Universidad Ficticia", None),
    Referencia(E.NO_LOCALIZADA, "Núñez", "J", 2016, "Apuntes de clase de estadística descriptiva", "Material docente ficticio", None),
    Referencia(E.SIN_DOI, "Ortiz", "K", 2014, "Manual ficticio de estadística para ciencias sociales", "Editorial Ficticia", None),
    Referencia(E.CAIDA, "Pacheco", "L", 2022, "Ansiedad y procrastinación académica", "Revista Ficticia de Psicología", _doi(22)),
    Referencia(E.CAIDA, "Ramos", "M", 2023, "Bienestar estudiantil y carga académica", "Revista Ficticia de Psicología", _doi(23)),
    Referencia(E.ESCANEADA, "Soto", "N", 2012, "Estudio pionero de ansiedad estadística digitalizado", "Revista Ficticia Histórica", _doi(24)),
]  # fmt: skip

assert len(REFERENCIAS) == 24  # criterio de T15: al menos 20 referencias

CUERPO = [
    ("titulo", TITULO),
    ("seccion", "Introducción"),
    (
        "parrafo",
        "La ansiedad ante la estadística afecta el rendimiento de los estudiantes. "
        + FRASE_DEL_CUERPO,
    ),
    ("parrafo", "Este artículo ficticio solo sirve para probar el importador de referencias."),
    ("seccion", "Método"),
    ("parrafo", "Participaron estudiantes ficticios de una universidad ficticia."),
    ("seccion", "Referencias"),
]
