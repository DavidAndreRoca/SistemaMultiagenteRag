"""Fusión por rangos recíprocos y presupuesto de contexto (T16-01, apartados 2 y 4). Sin base."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from app.rag.modelos import Candidato


class ConPuntaje(Protocol):
    @property
    def fragmento_id(self) -> uuid.UUID: ...

    @property
    def puntaje(self) -> float: ...


def fusionar(
    densos: Sequence[ConPuntaje], lexicos: Sequence[ConPuntaje], constante: int
) -> list[Candidato]:
    """RRF: puntaje = suma de 1 / (constante + posición), con posiciones desde 1.

    Un fragmento que aparece en ambas listas suma las dos contribuciones. Los empates se
    resuelven por el mejor puesto en cualquiera de las listas y luego por el identificador,
    para que el orden sea determinista.
    """
    puntajes: dict[uuid.UUID, float] = {}
    mejor_puesto: dict[uuid.UUID, int] = {}
    densidad = {c.fragmento_id: c.puntaje for c in densos}
    lexico = {c.fragmento_id: c.puntaje for c in lexicos}
    for lista in (densos, lexicos):
        for posicion, coincidencia in enumerate(lista, start=1):
            clave = coincidencia.fragmento_id
            puntajes[clave] = puntajes.get(clave, 0.0) + 1.0 / (constante + posicion)
            mejor_puesto[clave] = min(mejor_puesto.get(clave, posicion), posicion)
    orden = sorted(puntajes, key=lambda f: (-puntajes[f], mejor_puesto[f], str(f)))
    return [
        Candidato(
            fragmento_id=f,
            puntaje_denso=densidad.get(f),
            puntaje_lexico=lexico.get(f),
            puntaje_fusionado=puntajes[f],
        )
        for f in orden
    ]


def recortar_por_presupuesto(
    tokens: Sequence[int], maximo_fragmentos: int, presupuesto: int
) -> int:
    """Cuántos de los primeros entran sin superar el presupuesto, sin cortar ninguno.

    El primero entra siempre, aunque solo él supere el presupuesto: sin él no habría
    contexto que juzgar.
    """
    acumulado = 0
    cantidad = 0
    for valor in tokens[:maximo_fragmentos]:
        if cantidad and acumulado + valor > presupuesto:
            break
        acumulado += valor
        cantidad += 1
    return cantidad
