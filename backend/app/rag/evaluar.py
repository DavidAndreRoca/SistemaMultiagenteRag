"""Línea base de la recuperación sobre un conjunto de consultas (T16-01, apartado 7).

``python -m app.rag.evaluar <conjunto.json> [--salida informe.json]``

Para cada tema del conjunto abre una transacción que **siempre se revierte**: crea en
ella un caso transitorio del tema (sin cuenta ni datos) y recupera con el mismo camino
que usará un agente (``Recuperador.recuperar`` con ``busqueda_evidencia``). Nada queda
escrito: el corpus provisional no se modifica.

Métricas, sin modelo de lenguaje, con los documentos esperados como referencia (un
fragmento es pertinente si pertenece a un documento esperado):

* **Precisión contextual:** precisión promedio ponderada por posición sobre ``F1`` a ``Fn``.
* **Exhaustividad:** fracción de documentos esperados presentes en el contexto.

Necesita la base y el servicio de modelos (``URL_SERVICIO_MODELOS``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.bd.enumeraciones import Rol, TipoSolicitud
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.bibliografia.normalizacion import normalizar_doi
from app.configuracion import cargar_ajustes
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.rag.recuperacion import Recuperador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.evaluacion import RepositorioEvaluacion
from app.repositorios.unidad import UnidadDeTrabajo


class Origen(BaseModel):
    doi: str
    titulo: str


class ConsultaPrueba(BaseModel):
    id: str
    tema: str
    tipo: TipoSolicitud = TipoSolicitud.BUSQUEDA_EVIDENCIA
    forma: str
    consulta: str = Field(min_length=10)
    origen: Origen
    documentos_esperados: list[str] = Field(min_length=1)


class Conjunto(BaseModel):
    nombre: str
    version: str
    estado: str
    consultas: list[ConsultaPrueba] = Field(min_length=1)


def precision_contextual(pertinentes: Sequence[bool]) -> float:
    """Precisión promedio: media de precisión@k en cada posición pertinente."""
    aciertos, suma = 0, 0.0
    for posicion, es_pertinente in enumerate(pertinentes, start=1):
        if es_pertinente:
            aciertos += 1
            suma += aciertos / posicion
    return suma / aciertos if aciertos else 0.0


def exhaustividad(encontrados: set[str], esperados: set[str]) -> float:
    return len(encontrados & esperados) / len(esperados) if esperados else 0.0


async def evaluar(conjunto: Conjunto) -> dict[str, Any]:
    ajustes = cargar_ajustes()
    motor = crear_motor(ajustes)
    fabrica = crear_fabrica_sesiones(motor)
    servicio = cliente_desde_ajustes(ajustes)
    recuperador = Recuperador(servicio, servicio)
    filas: list[dict[str, Any]] = []
    try:
        temas = sorted({c.tema for c in conjunto.consultas})
        for tema in temas:
            async with fabrica() as sesion:
                try:
                    unidad = UnidadDeTrabajo(sesion)
                    evaluacion = RepositorioEvaluacion(sesion)
                    contexto = await _caso_transitorio(evaluacion, tema)
                    _, parametros = await unidad.configuracion.vigente()
                    for consulta in (c for c in conjunto.consultas if c.tema == tema):
                        inicio = time.perf_counter()
                        recuperacion = await recuperador.recuperar(
                            unidad, contexto, consulta.tipo, consulta.consulta, parametros
                        )
                        dois = await _dois(
                            evaluacion, [f.documento_id for f in recuperacion.fragmentos]
                        )
                        esperados = {normalizar_doi(d) or d for d in consulta.documentos_esperados}
                        pertinentes = [
                            dois.get(f.documento_id) in esperados for f in recuperacion.fragmentos
                        ]
                        filas.append(
                            {
                                "id": consulta.id,
                                "tema": tema,
                                "fragmentos": len(recuperacion.fragmentos),
                                "pertinentes": sum(pertinentes),
                                "precision_contextual": round(precision_contextual(pertinentes), 4),
                                "exhaustividad": round(
                                    exhaustividad({d for d in dois.values() if d}, esperados), 4
                                ),
                                "posicion_primer_acierto": next(
                                    (i for i, p in enumerate(pertinentes, start=1) if p), None
                                ),
                                "sobre_umbral": sum(
                                    1
                                    for f in recuperacion.fragmentos
                                    if (f.candidato.puntaje_reranking or 0)
                                    >= parametros.suficiencia_tau
                                ),
                                "tokens_contexto": sum(f.tokens for f in recuperacion.fragmentos),
                                "duracion_s": round(time.perf_counter() - inicio, 1),
                                "duracion_reranking_ms": recuperacion.duracion_reranking_ms,
                            }
                        )
                        print(_linea(filas[-1]), flush=True)
                finally:
                    await unidad.revertir()  # nada de lo hecho queda en la base
    finally:
        await servicio.cerrar()
        await motor.dispose()
    return _informe(conjunto, filas, parametros.model_dump(mode="json"))


# El evaluador actúa como investigador (A2) para crear el caso transitorio y leer DOI.
_EVALUADOR = ContextoAcceso(cuenta_id=uuid.UUID(int=0), rol=Rol.INVESTIGADOR, caso_id=None)


async def _caso_transitorio(evaluacion: RepositorioEvaluacion, tema: str) -> ContextoAcceso:
    coleccion = await evaluacion.coleccion_del_tema(_EVALUADOR, tema)
    if coleccion is None:
        raise SystemExit(f"no existe la colección científica del tema {tema}")
    caso = await evaluacion.caso_transitorio(_EVALUADOR, coleccion)
    return ContextoAcceso(cuenta_id=uuid.uuid4(), rol=Rol.CASO, caso_id=caso.id)


async def _dois(
    evaluacion: RepositorioEvaluacion, ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    crudos = await evaluacion.dois(_EVALUADOR, ids)
    return {i: (normalizar_doi(d) if d else None) for i, d in crudos.items()}


def _linea(fila: dict[str, Any]) -> str:
    return (
        f"{fila['id']}: precisión {fila['precision_contextual']:.2f}, exhaustividad"
        f" {fila['exhaustividad']:.2f}, primer acierto {fila['posicion_primer_acierto']},"
        f" {fila['fragmentos']} fragmentos, {fila['duracion_s']} s"
    )


def _media(valores: Sequence[float]) -> float:
    return round(sum(valores) / len(valores), 4) if valores else 0.0


def _informe(
    conjunto: Conjunto, filas: list[dict[str, Any]], parametros: dict[str, Any]
) -> dict[str, Any]:
    por_tema = {}
    for tema in sorted({f["tema"] for f in filas}):
        del_tema = [f for f in filas if f["tema"] == tema]
        por_tema[tema] = {
            "consultas": len(del_tema),
            "precision_contextual": _media([f["precision_contextual"] for f in del_tema]),
            "exhaustividad": _media([f["exhaustividad"] for f in del_tema]),
        }
    return {
        "conjunto": {
            "nombre": conjunto.nombre,
            "version": conjunto.version,
            "estado": conjunto.estado,
        },
        "parametros": {
            k: parametros[k]
            for k in (
                "k_denso",
                "k_lexico",
                "rrf_constante",
                "candidatos_reranking",
                "n_reranking",
                "presupuesto_tokens_contexto",
                "suficiencia_n",
                "suficiencia_tau",
            )
        },
        "global": {
            "consultas": len(filas),
            "precision_contextual": _media([f["precision_contextual"] for f in filas]),
            "exhaustividad": _media([f["exhaustividad"] for f in filas]),
            "con_acierto": sum(1 for f in filas if f["posicion_primer_acierto"]),
            "duracion_media_s": _media([f["duracion_s"] for f in filas]),
        },
        "por_tema": por_tema,
        "consultas": filas,
    }


def principal() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("conjunto", type=Path)
    argumentos.add_argument("--salida", type=Path)
    leidos = argumentos.parse_args()
    conjunto = Conjunto.model_validate_json(leidos.conjunto.read_text(encoding="utf-8-sig"))
    # psycopg asíncrono no funciona con el bucle Proactor de Windows (desarrollo local).
    fabrica = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    informe = asyncio.run(evaluar(conjunto), loop_factory=fabrica)
    texto = json.dumps(informe, ensure_ascii=False, indent=2) + "\n"
    if leidos.salida:
        leidos.salida.write_bytes(texto.encode("utf-8"))
    print(json.dumps(informe["global"], ensure_ascii=False))


if __name__ == "__main__":
    principal()
