"""Coherencia de la fuente aportada con la afirmación (T32; RF-13, actividad 3).

Informativa: no bloquea la indexación. Al modelo van la afirmación del estudiante y el
resumen o los primeros fragmentos de la fuente, nada más (RNF-10). Si el modelo no
responde, la coherencia queda ``no_evaluada``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.bd.enumeraciones import CoherenciaFuente
from app.comun.registro import obtener_registrador
from app.instrucciones.cargador import vigente
from app.llm.interfaces import ModeloLenguaje
from app.llm.modelos import BloqueDatos, EntradaModelo, ErrorModelo

AGENTE_COHERENCIA = "coherencia"
MAX_BLOQUES_FUENTE = 3
MAX_CARACTERES_FUENTE = 4_000
_registro = obtener_registrador("aportes")


class JuicioCoherencia(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    coherencia: Literal["coherente", "parcial", "no_coherente"]
    explicacion: Annotated[str, Field(min_length=1, max_length=600)]


class Coherencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    valor: CoherenciaFuente
    explicacion: str | None = None


NO_EVALUADA = Coherencia(valor=CoherenciaFuente.NO_EVALUADA)


async def evaluar_coherencia(
    modelo: ModeloLenguaje | None,
    versiones: Callable[[], dict[str, str]],
    afirmacion: str,
    textos: Sequence[str],
) -> Coherencia:
    if modelo is None or not textos:
        return NO_EVALUADA
    datos = [BloqueDatos(etiqueta="afirmacion", contenido=afirmacion[:2_000])]
    datos += [
        BloqueDatos(etiqueta="fuente", contenido=t[:MAX_CARACTERES_FUENTE])
        for t in textos[:MAX_BLOQUES_FUENTE]
    ]
    tarea = (
        "Juzga si la fuente aportada por el estudiante trata lo que quiere sustentar:"
        " coherente, parcial o no_coherente, con una explicación breve."
    )
    try:
        resultado = await modelo.generar(
            vigente(AGENTE_COHERENCIA, versiones()),
            EntradaModelo(tarea=tarea, datos=datos),
            JuicioCoherencia,
        )
    except ErrorModelo as error:
        _registro.warning(
            "coherencia no evaluada",
            extra={"tipo_evento": "aportes", "motivo": error.motivo.value},
        )
        return NO_EVALUADA
    juicio = resultado.datos
    return Coherencia(valor=CoherenciaFuente(juicio.coherencia), explicacion=juicio.explicacion)
