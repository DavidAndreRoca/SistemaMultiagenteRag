"""Suficiencia en dos pasos (T16-01, apartado 2; RN-04, RNF-04, CP-05).

1. Umbral: al menos ``suficiencia_n`` fragmentos con puntaje de reranking >= tau. Si no
   se cumple, hay abstención sin llamar al modelo.
2. Juicio del modelo, con el adaptador de T17, la instrucción ``suficiencia`` vigente y
   los fragmentos como datos (RN-23): ``{suficiente, motivo}``.

Si el modelo no está disponible, la excepción sube tal cual: es un error técnico (la
solicitud quedará "no atendida", 4.4), no una abstención.
"""

from __future__ import annotations

from app.administracion.parametros import ParametrosFuncionales
from app.llm.interfaces import ModeloLenguaje
from app.llm.modelos import BloqueDatos, EntradaModelo, Instruccion
from app.rag.modelos import DecisionSuficiencia, JuicioSuficiencia, PasoSuficiencia, Recuperacion

MAX_CARACTERES_SOLICITUD = 3_000


def sobre_umbral(recuperacion: Recuperacion, tau: float) -> int:
    return sum(
        1
        for f in recuperacion.fragmentos
        if f.candidato.puntaje_reranking is not None and f.candidato.puntaje_reranking >= tau
    )


async def decidir(
    modelo: ModeloLenguaje,
    instruccion: Instruccion,
    solicitud: str,
    recuperacion: Recuperacion,
    parametros: ParametrosFuncionales,
) -> DecisionSuficiencia:
    n, tau = parametros.suficiencia_n, parametros.suficiencia_tau
    alcanzan = sobre_umbral(recuperacion, tau)
    if alcanzan < n:
        return DecisionSuficiencia(
            suficiente=False,
            paso=PasoSuficiencia.UMBRAL,
            motivo=(
                f"Solo {alcanzan} de los {n} fragmentos necesarios alcanzan el puntaje"
                f" mínimo de pertinencia ({tau:.2f})."
            ),
            sobre_umbral=alcanzan,
        )
    entrada = EntradaModelo(
        tarea=(
            "Decide si los fragmentos alcanzan para atender esta solicitud del estudiante: "
            + solicitud.strip()[:MAX_CARACTERES_SOLICITUD]
        ),
        datos=[
            BloqueDatos(etiqueta=f.identificador, contenido=f.texto)
            for f in recuperacion.fragmentos
        ],
    )
    resultado = await modelo.generar(instruccion, entrada, JuicioSuficiencia)
    return DecisionSuficiencia(
        suficiente=resultado.datos.suficiente,
        paso=PasoSuficiencia.MODELO,
        motivo=resultado.datos.motivo,
        sobre_umbral=alcanzan,
        instruccion=resultado.instruccion,
        proveedor=resultado.proveedor.value,
        modelo=resultado.modelo,
    )
