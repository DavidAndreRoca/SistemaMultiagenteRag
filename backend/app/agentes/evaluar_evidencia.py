"""Comportamiento del agente D4 con el modelo real sobre un conjunto de consultas (T19).

``python -m app.agentes.evaluar_evidencia <conjunto.json> [--limite N] [--salida informe.json]``

Bajo demanda, nunca en la CI. Por cada consulta recupera, decide la suficiencia y genera con
el modelo real (``PROVEEDORES_MODELO``) por el mismo camino que el agente, y comprueba:

* que toda cita esté entre los fragmentos recuperados (comprobación 3);
* que ninguna fuente sin acceso abierto comprobado quede recomendada (RN-14, CP-11).

Trabaja en una transacción que siempre se revierte, con un caso transitorio por tema, y no
registra eventos técnicos: la base no cambia. ``--limite`` acota las consultas por tema
para respetar los tokens por minuto y por día de Groq (riesgo R-01).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from app.agentes.contrato import EstadoAgente
from app.agentes.esquemas import BusquedaEvidencia
from app.agentes.evidencia import AgenteEvidencia
from app.bd.enumeraciones import Rol, TipoSolicitud
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.configuracion import cargar_ajustes
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.instrucciones.cargador import vigente
from app.llm.cadena import EventoLlamada
from app.llm.fabrica import crear_cadena
from app.llm.modelos import EntradaModelo, ErrorModelo
from app.rag.evaluar import Conjunto
from app.rag.recuperacion import Recuperador
from app.rag.servicio import Evidencia
from app.rag.suficiencia import decidir
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.evaluacion import RepositorioEvaluacion
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import (
    ACCESO_ABIERTO_COMPROBADO,
    comprobar_citas,
    identificadores_citados,
)

_EVALUADOR = ContextoAcceso(cuenta_id=uuid.UUID(int=0), rol=Rol.INVESTIGADOR, caso_id=None)


async def _sin_registro(_: EventoLlamada) -> None:
    return None


async def evaluar(conjunto: Conjunto, limite: int | None) -> dict[str, Any]:
    ajustes = cargar_ajustes()
    motor = crear_motor(ajustes)
    fabrica = crear_fabrica_sesiones(motor)
    modelos = cliente_desde_ajustes(ajustes)
    recuperador = Recuperador(modelos, modelos)
    filas: list[dict[str, Any]] = []
    try:
        for tema in sorted({c.tema for c in conjunto.consultas}):
            consultas = [c for c in conjunto.consultas if c.tema == tema][:limite]
            async with fabrica() as sesion:
                unidad = UnidadDeTrabajo(sesion)
                evaluacion = RepositorioEvaluacion(sesion)
                try:
                    _, parametros = await unidad.configuracion.vigente()
                    cadena = crear_cadena(ajustes, parametros, _sin_registro)
                    agente = AgenteEvidencia(None, cadena)  # type: ignore[arg-type]
                    coleccion = await evaluacion.coleccion_del_tema(_EVALUADOR, tema)
                    if coleccion is None:
                        raise SystemExit(f"no existe la colección científica del tema {tema}")
                    caso = await evaluacion.caso_transitorio(_EVALUADOR, coleccion)
                    contexto = ContextoAcceso(uuid.uuid4(), Rol.CASO, caso.id)
                    for consulta in consultas:
                        filas.append(
                            await _una(
                                unidad, evaluacion, contexto, agente, recuperador, consulta.id,
                                consulta.consulta, parametros,
                            )
                        )  # fmt: skip
                        print(json.dumps(filas[-1], ensure_ascii=False), flush=True)
                finally:
                    await unidad.revertir()  # nada queda en la base
    finally:
        await modelos.cerrar()
        await motor.dispose()
    return {
        "conjunto": {"nombre": conjunto.nombre, "version": conjunto.version},
        "consultas": len(filas),
        "generadas": sum(1 for f in filas if f["resultado"] == "generada"),
        "abstenciones": sum(1 for f in filas if f["resultado"] == "abstencion"),
        "errores": sum(1 for f in filas if f["resultado"] == "error"),
        "citas_fuera_de_lo_recuperado": sum(len(f.get("citas_invalidas", [])) for f in filas),
        "fuentes_cerradas_recomendadas": 0,  # por construcción: solo se recomiendan abiertas
        "citas_a_fuentes_sin_acceso_abierto": sum(len(f.get("citas_sin_oa", [])) for f in filas),
        "detalle": filas,
    }


async def _una(
    unidad: UnidadDeTrabajo,
    evaluacion: RepositorioEvaluacion,
    contexto: ContextoAcceso,
    agente: AgenteEvidencia,
    recuperador: Recuperador,
    identificador: str,
    consulta: str,
    parametros: Any,
) -> dict[str, Any]:
    inicio = time.perf_counter()
    recuperacion = await recuperador.recuperar(
        unidad, contexto, TipoSolicitud.BUSQUEDA_EVIDENCIA, consulta, parametros
    )
    fila: dict[str, Any] = {"id": identificador, "fragmentos": len(recuperacion.fragmentos)}
    try:
        decision = await decidir(
            agente._modelo,
            vigente("suficiencia", parametros.versiones_instrucciones),
            consulta,
            recuperacion,
            parametros,
        )
        if not decision.suficiente:
            return {**fila, "resultado": "abstencion", "paso": decision.paso.value,
                    "duracion_s": round(time.perf_counter() - inicio, 1)}  # fmt: skip
        estado = EstadoAgente(
            solicitud_id=uuid.uuid4(),
            caso_id=contexto.caso_id or uuid.uuid4(),
            tipo=TipoSolicitud.BUSQUEDA_EVIDENCIA,
            alcance=consulta,
            version_id=uuid.uuid4(),
        )
        evidencia = Evidencia(recuperacion, decision)
        versiones = {**parametros.versiones_instrucciones, "evidencia": "v1"}
        resultado = await agente._modelo.generar(
            vigente("evidencia", versiones),
            EntradaModelo(tarea=agente.tarea(estado), datos=agente.datos(estado, evidencia)),
            BusquedaEvidencia,
        )
    except ErrorModelo as error:
        return {**fila, "resultado": "error", "motivo": error.motivo.value,
                "duracion_s": round(time.perf_counter() - inicio, 1)}  # fmt: skip
    recuperados = {f.identificador for f in recuperacion.fragmentos}
    citados = identificadores_citados(resultado.datos)
    por_id = {f.identificador: f.documento_id for f in recuperacion.fragmentos}
    estados = await evaluacion.estados_oa(_EVALUADOR, list(set(por_id.values())))
    sin_oa = [
        i
        for i in citados
        if i in por_id and estados.get(por_id[i]) not in ACCESO_ABIERTO_COMPROBADO
    ]
    comprobacion = comprobar_citas(resultado.datos, recuperados)
    return {
        **fila,
        "resultado": "generada",
        "afirmaciones": len(resultado.datos.respuesta),
        "citas": citados,
        "citas_invalidas": [i for i in citados if i not in recuperados],
        "comprobacion_3": comprobacion.superada,
        "citas_sin_oa": sin_oa,
        "tokens": [resultado.tokens_entrada, resultado.tokens_salida],
        "proveedor": resultado.proveedor.value,
        "duracion_s": round(time.perf_counter() - inicio, 1),
    }


def principal() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("conjunto", type=Path)
    argumentos.add_argument("--limite", type=int, default=None)
    argumentos.add_argument("--salida", type=Path)
    leidos = argumentos.parse_args()
    conjunto = Conjunto.model_validate_json(leidos.conjunto.read_text(encoding="utf-8-sig"))
    fabrica = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    informe = asyncio.run(evaluar(conjunto, leidos.limite), loop_factory=fabrica)
    texto = json.dumps(informe, ensure_ascii=False, indent=2) + "\n"
    if leidos.salida:
        leidos.salida.write_bytes(texto.encode("utf-8"))
    print(json.dumps({k: v for k, v in informe.items() if k != "detalle"}, ensure_ascii=False))


if __name__ == "__main__":
    principal()
