"""Agente D1 de estructura y coherencia: diagnóstico de una sección (T23; RF-04, CU-03, CP-08).

Recupera de las guías (T22) los criterios que corresponden a la sección y genera, con la
instrucción ``estructura``, hallazgos sobre tres indicadores (alineación entre problema,
objetivos e hipótesis; secuencia lógica; cohesión), con ubicación, severidad, recomendación
y citas a las guías. No reescribe: la comprobación 2 lo vigila (``AtencionSeccion``).

La consulta de recuperación nombra los criterios y el título de la sección, sin el texto
del estudiante: las guías tratan de estructura, no del tema del artículo, y con el texto
mezclado el reordenador no las encontraba (prueba con el modelo real, T23-01).
"""

from __future__ import annotations

from app.agentes.contrato import Agente, EstadoAgente
from app.bd.enumeraciones import TipoSolicitud


def titulo_de_seccion(alcance: str) -> str:
    """El título de la sección: la primera línea ``## ...`` del alcance."""
    primera = alcance.splitlines()[0] if alcance else ""
    return primera.removeprefix("## ").strip() or "sección del artículo"


class AgenteEstructura(Agente):
    tipos = frozenset({TipoSolicitud.REVISION_ESTRUCTURA})
    instruccion = "estructura"

    def consulta(self, estado: EstadoAgente) -> str:
        return (
            f"Criterios para revisar la sección «{titulo_de_seccion(estado.alcance)}» de un"
            " artículo científico empírico: planteamiento del problema, objetivos e hipótesis y"
            " su alineación; secuencia lógica de las ideas y de los párrafos; cohesión entre"
            " apartados y transiciones."
        )

    def tarea(self, estado: EstadoAgente) -> str:
        return (
            "Diagnostica la sección del estudiante (bloque alcance) en los tres indicadores de"
            " estructura y coherencia, usando como criterio los fragmentos de las guías. No la"
            " reescribas."
        )
