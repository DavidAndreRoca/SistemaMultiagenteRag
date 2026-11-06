"""Ficha de registro de métricas (tesis, Tabla 22; insumos de T04, apartado 1).

Las seis métricas no se guardan como columnas: se calculan a partir del registro
exportado (RF-17). Cada columna que las alimenta lo declara en ``info["alimenta"]``
(o su tabla, si la alimentan todas sus columnas) con el código ``M1`` a ``M6``; el
diccionario de datos arma con eso el índice inverso métrica a columnas.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metrica:
    codigo: str
    nombre: str
    dimension: str
    umbral: str


METRICAS: tuple[Metrica, ...] = (
    Metrica("M1", "Cobertura del corpus documental", "Calidad de la recuperación", "Se describe"),
    Metrica(
        "M2", "Precisión contextual de los fragmentos", "Calidad de la recuperación", "0.80 o más"
    ),
    Metrica("M3", "Completitud de la recuperación", "Calidad de la recuperación", "Se describe"),
    Metrica("M4", "Fidelidad respuesta-fuente", "Fidelidad de la respuesta", "0.90 o más"),
    Metrica("M5", "Relevancia de la respuesta", "Fidelidad de la respuesta", "Se describe"),
    Metrica(
        "M6", "Tasa de referencias no verificables", "Fidelidad de la respuesta", "0.05 o menos"
    ),
)

CODIGOS = tuple(m.codigo for m in METRICAS)

# Datos del registro que se exportan sin ser métricas de la ficha (insumos, apartado 1).
CONTADORES_DECISIONES = "Contadores de decisiones por tipo y caso (RF-12)"
USO_MINIMO = "Uso mínimo por hito (tesis 6.2.2.2)"
