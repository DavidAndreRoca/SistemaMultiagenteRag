"""Comprobación 6: fidelidad respuesta-fuente con un modelo evaluador (T30; Fase 1, 6.7).

Un evaluador con rol e instrucción propios (``instrucciones/evaluador/``), que no comparte
instrucciones con los agentes, divide la salida en afirmaciones y clasifica cada una como
respaldada, no respaldada o contradicha por los fragmentos que la salida cita. Fidelidad =
respaldadas / total; se supera con el umbral de la configuración (``umbral_fidelidad``, 0.90).

* ``fidelidad``: para evidencia (afirmaciones), estructura y metodología (hallazgos, cuyo
  criterio debe estar en la guía citada) y plan de tarea (tareas).
* ``conservacion``: para la propuesta de redacción (D3): cada afirmación de la propuesta
  debe estar en el párrafo original; una idea, un dato o una cita nueva no está respaldada.

Al evaluador van la salida del agente y los fragmentos citados, nada más (RNF-10). Si el
servicio del modelo no responde, la comprobación no se supera pero no pide reintento
(regenerar no lo arregla): el resultado sale "Con advertencias".
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from app.bd.enumeraciones import TipoSolicitud
from app.comun.registro import obtener_registrador
from app.instrucciones.cargador import vigente
from app.llm.interfaces import ModeloLenguaje
from app.llm.modelos import BloqueDatos, EntradaModelo, ErrorModelo
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import Comprobacion, identificadores_citados

AGENTE_EVALUADOR = "evaluador"
MAX_AFIRMACIONES = 40
_registro = obtener_registrador("verificacion")


class Clasificacion(StrEnum):
    RESPALDADA = "respaldada"
    NO_RESPALDADA = "no_respaldada"
    CONTRADICHA = "contradicha"


class AfirmacionEvaluada(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    afirmacion: Annotated[str, Field(min_length=1, max_length=400)]
    clasificacion: Clasificacion


class JuicioFidelidad(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    afirmaciones: list[AfirmacionEvaluada] = Field(max_length=MAX_AFIRMACIONES)


def _con_citas(texto: str, citas: Any) -> str:
    ids = ", ".join(c for c in citas if isinstance(c, str)) if isinstance(citas, list) else ""
    return f"{texto} [{ids}]" if ids else texto


def afirmaciones_de(tipo: TipoSolicitud, salida: Mapping[str, Any]) -> list[str]:
    """Lo que el evaluador juzga de cada tipo, con sus citas al final de cada línea."""
    lineas: list[str] = []
    if tipo is TipoSolicitud.BUSQUEDA_EVIDENCIA:
        for clave in ("respuesta", "evidencia_divergente"):
            lineas += [
                _con_citas(str(a.get("afirmacion", "")), a.get("citas"))
                for a in salida.get(clave, [])
                if isinstance(a, dict)
            ]
    elif tipo in (TipoSolicitud.REVISION_ESTRUCTURA, TipoSolicitud.REVISION_METODOLOGICA):
        lineas += [
            _con_citas(
                f"Hallazgo: {h.get('descripcion', '')} Qué revisar: {h.get('recomendacion', '')}",
                h.get("citas"),
            )
            for h in salida.get("hallazgos", [])
            if isinstance(h, dict)
        ]
    elif tipo is TipoSolicitud.PLAN_TAREA:
        lineas += [
            _con_citas(
                f"Tarea: {t.get('tarea', '')} Criterio de logro: {t.get('criterio_de_logro', '')}",
                t.get("citas"),
            )
            for t in salida.get("tareas", [])
            if isinstance(t, dict)
        ]
    return [linea for linea in lineas if linea.strip()][:MAX_AFIRMACIONES]


class Evaluador:
    def __init__(
        self,
        modelo: ModeloLenguaje,
        versiones: Callable[[], dict[str, str]] | None = None,
    ) -> None:
        """``versiones`` da la versión de la instrucción; por defecto, la configuración
        vigente (RNF-21)."""
        self._modelo = modelo
        self._versiones = versiones

    async def _juzgar(
        self, unidad: UnidadDeTrabajo, tarea: str, datos: list[BloqueDatos]
    ) -> tuple[JuicioFidelidad, str]:
        if self._versiones is not None:
            versiones = self._versiones()
        else:
            _, parametros = await unidad.configuracion.vigente()
            versiones = parametros.versiones_instrucciones
        instruccion = vigente(AGENTE_EVALUADOR, versiones)
        resultado = await self._modelo.generar(
            instruccion, EntradaModelo(tarea=tarea, datos=datos), JuicioFidelidad
        )
        return resultado.datos, f"{resultado.proveedor.value}:{resultado.modelo}"

    async def fidelidad(
        self,
        unidad: UnidadDeTrabajo,
        tipo: TipoSolicitud,
        salida: Mapping[str, Any],
        fragmentos: Mapping[str, str],
        umbral: float,
    ) -> Comprobacion:
        lineas = afirmaciones_de(tipo, salida)
        if not lineas:  # nada que juzgar (por ejemplo, ningún hallazgo)
            return _comprobacion("fidelidad", None, umbral, [], None)
        citados = [
            i for i in dict.fromkeys(identificadores_citados(dict(salida))) if i in fragmentos
        ]
        datos = [BloqueDatos(etiqueta="salida", contenido="\n".join(f"- {x}" for x in lineas))]
        datos += [BloqueDatos(etiqueta=i, contenido=fragmentos[i]) for i in citados]
        tarea = (
            "Divide la salida en afirmaciones y clasifica cada una según los fragmentos que cita"
            " entre corchetes: respaldada, no_respaldada o contradicha."
        )
        return await self._evaluar("fidelidad", tarea, datos, unidad, umbral)

    async def conservacion(
        self, unidad: UnidadDeTrabajo, original: str, propuesta: str, umbral: float
    ) -> Comprobacion:
        datos = [
            BloqueDatos(etiqueta="original", contenido=original),
            BloqueDatos(etiqueta="propuesta", contenido=propuesta),
        ]
        tarea = (
            "Divide la propuesta en afirmaciones y clasifica cada una según el original:"
            " respaldada si el original dice lo mismo, no_respaldada si agrega una idea, un dato"
            " o una cita, contradicha si cambia el sentido."
        )
        return await self._evaluar("conservacion_del_contenido", tarea, datos, unidad, umbral)

    async def _evaluar(
        self,
        nombre: str,
        tarea: str,
        datos: list[BloqueDatos],
        unidad: UnidadDeTrabajo,
        umbral: float,
    ) -> Comprobacion:
        try:
            juicio, modelo = await self._juzgar(unidad, tarea, datos)
        except ErrorModelo as error:
            _registro.warning(
                "evaluador no disponible",
                extra={"tipo_evento": "verificacion", "motivo": error.motivo.value},
            )
            return Comprobacion(
                numero=6,
                nombre=nombre,
                superada=False,
                reintentable=False,
                motivos=["no se pudo evaluar la fidelidad: el servicio del modelo no respondió"],
                datos={"umbral": umbral},
            )
        return _comprobacion(nombre, juicio, umbral, juicio.afirmaciones, modelo)


def _comprobacion(
    nombre: str,
    juicio: JuicioFidelidad | None,
    umbral: float,
    afirmaciones: list[AfirmacionEvaluada],
    modelo: str | None,
) -> Comprobacion:
    total = len(afirmaciones)
    cuentas = {c: sum(a.clasificacion is c for a in afirmaciones) for c in Clasificacion}
    fidelidad = cuentas[Clasificacion.RESPALDADA] / total if total else None
    datos: dict[str, Any] = {
        "fidelidad": fidelidad,
        "umbral": umbral,
        "total": total if juicio is not None else None,
        "respaldadas": cuentas[Clasificacion.RESPALDADA] if juicio is not None else None,
        "no_respaldadas": cuentas[Clasificacion.NO_RESPALDADA] if juicio is not None else None,
        "contradichas": cuentas[Clasificacion.CONTRADICHA] if juicio is not None else None,
        "modelo": modelo,
    }
    if fidelidad is None or fidelidad >= umbral:
        return Comprobacion(numero=6, nombre=nombre, superada=True, datos=datos)
    sin_respaldo = [
        a.afirmacion[:200] for a in afirmaciones if a.clasificacion is not Clasificacion.RESPALDADA
    ]
    motivos = [
        f"fidelidad {fidelidad:.2f} menor que el umbral {umbral:.2f}:"
        f" {cuentas[Clasificacion.NO_RESPALDADA]} afirmaciones no respaldadas y"
        f" {cuentas[Clasificacion.CONTRADICHA]} contradichas",
        *[f"sin respaldo: {a}" for a in sin_respaldo[:5]],
    ]
    return Comprobacion(numero=6, nombre=nombre, superada=False, motivos=motivos, datos=datos)
