"""Agente D1, segundo tipo: plan de tarea del hito (T24; RF-05, CU-04, CP-03).

* **Alcance:** el hito de una versión vigente (``alcance_tipo = hito``, sin ``alcance_ref``).
  Al modelo no va el texto del borrador sino su estado: el árbol de títulos con sus
  palabras, los elementos detectados (problema, objetivos, hipótesis) y si tiene lista de
  referencias (herramienta ``estructura_borrador`` de T12). Es lo que el plan compara con
  las instrucciones del hito.
* **Herramienta ``instrucciones_del_hito``:** lee del corpus de guías el apartado del hito
  (por su nombre, "Avance 1: Planteamiento" o "Entrega final del plan"). Ese texto es la
  consulta de recuperación, así que llega al modelo como fragmento citable. Si el corpus no
  tiene instrucciones del hito, el agente se abstiene sin recuperar ni generar (RF-05,
  flujo alternativo).
* **Comprobaciones:** 1 (esquema), 2 (no reescritura, también sobre tareas y criterios) y 3
  (citas). El plan no se guarda como edición del borrador: es un resultado más.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.administracion.parametros import Hito, ParametrosFuncionales
from app.agentes.contrato import Agente, EstadoAgente
from app.agentes.seccion import AtencionPorAlcance, SinVersion, secciones_revisables
from app.bd.enumeraciones import TipoAlcance, TipoSolicitud
from app.bd.modelos import VersionBorrador
from app.borradores.secciones import NodoSeccion, estructura_borrador
from app.borradores.servicio import parrafos_de, secciones_de
from app.comun.errores import ErrorAplicacion
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import (
    Comprobacion,
    comprobar_citas,
    comprobar_esquema,
    comprobar_no_reescritura,
)

TIPO = TipoSolicitud.PLAN_TAREA
MAX_CARACTERES_CONSULTA = 2000
_SUJETO = re.compile(r"^El estudiante \w+ ")


class HitoInexistente(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "hito_inexistente", "Ese hito no está en el programa configurado.", estado_http=422
        )


class SinVersionDelHito(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sin_version_del_hito",
            "Todavía no cargó una versión para ese hito. Cárguela desde el panel.",
            estado_http=409,
        )


def hito_configurado(parametros: ParametrosFuncionales, codigo: str | None) -> Hito | None:
    return next((h for h in parametros.hitos if h.codigo == codigo), None)


def nombre_del_hito(hito: Hito) -> str:
    return f"{hito.nombre}: {hito.contenido}"


async def instrucciones_del_hito(
    unidad: UnidadDeTrabajo, contexto: ContextoAcceso, hito: Hito
) -> list[str]:
    """El apartado del hito en las guías, por su nombre completo o solo por el nombre."""
    fragmentos = await unidad.recuperacion.por_apartado(
        contexto, TIPO, [nombre_del_hito(hito), hito.nombre]
    )
    return [f.texto for f in fragmentos]


def consulta_del_hito(hito: Hito, instrucciones: str) -> str:
    """La consulta de recuperación: el hito y lo que pide entregar, sin su criterio de logro
    ni el sujeto "El estudiante entrega". Trae primero las instrucciones del hito y después
    las pautas de las guías para esas partes; con el texto completo de las instrucciones,
    solo ellas superaban el umbral y el sistema se abstenía (prueba de T24-01)."""
    entrega = " ".join(instrucciones.split()).split(" Criterio de logro:")[0]
    entrega = _SUJETO.sub("", entrega)
    return (
        f"Instrucciones del programa para el hito {nombre_del_hito(hito)} y cómo redactar y"
        f" organizar en el artículo científico {entrega}"
    )[:MAX_CARACTERES_CONSULTA]


def _lineas_arbol(nodos: list[NodoSeccion], palabras: Mapping[str, int], nivel: int) -> list[str]:
    lineas: list[str] = []
    for nodo in nodos:
        cuantas = palabras.get(nodo.id)
        detalle = f" ({cuantas} palabras)" if cuantas is not None else ""
        lineas.append(f"{'  ' * nivel}- {nodo.titulo}{detalle}")
        lineas.extend(_lineas_arbol(nodo.hijos, palabras, nivel + 1))
    return lineas


def estado_del_borrador(version: VersionBorrador, hito: Hito) -> str:
    """El estado de la versión para el plan: títulos, palabras y elementos detectados, sin el
    texto del estudiante."""
    secciones = secciones_de(version)
    metodo = version.metodo_deteccion.value if version.metodo_deteccion else None
    estructura = estructura_borrador(parrafos_de(version), secciones, metodo)
    palabras = {i: p for i, _, p in secciones_revisables(version)}
    lineas = [f"Hito de la versión: {nombre_del_hito(hito)}"]
    if estructura.titulo_documento:
        lineas.append(f"Título del documento: {estructura.titulo_documento}")
    if estructura.arbol:
        lineas.append("Secciones presentes:")
        lineas.extend(_lineas_arbol(estructura.arbol, palabras, 0))
    else:
        lineas.append("Secciones presentes: ninguna detectada (el documento no usa títulos).")
    elementos = sorted({u.elemento for u in estructura.ubicaciones})
    lineas.append("Elementos detectados: " + (", ".join(elementos) if elementos else "ninguno"))
    referencias = secciones.referencias if secciones else None
    lineas.append(
        f"Lista de referencias: sí, {len(referencias.entradas)} entradas"
        if referencias
        else "Lista de referencias: no detectada"
    )
    return "\n".join(lineas)


class AgentePlan(Agente):
    tipos = frozenset({TIPO})
    instruccion = "plan"

    async def _hito(self, unidad: UnidadDeTrabajo, estado: EstadoAgente) -> Hito | None:
        _, parametros = await unidad.configuracion.vigente()
        return hito_configurado(parametros, estado.hito)

    def consulta(self, estado: EstadoAgente) -> str:
        return f"Instrucciones del programa para el hito {estado.hito or ''} del artículo."

    async def falta_insumo(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, estado: EstadoAgente
    ) -> str | None:
        hito = await self._hito(unidad, estado)
        if hito is None or not await instrucciones_del_hito(unidad, contexto, hito):
            nombre = nombre_del_hito(hito) if hito else (estado.hito or "")
            return f"El corpus de guías no tiene instrucciones del hito {nombre}."
        return None

    async def consulta_con_herramientas(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, estado: EstadoAgente
    ) -> str:
        hito = await self._hito(unidad, estado)
        if hito is None:
            return self.consulta(estado)
        instrucciones = " ".join(await instrucciones_del_hito(unidad, contexto, hito))
        return consulta_del_hito(hito, instrucciones)

    def tarea(self, estado: EstadoAgente) -> str:
        return (
            "Arma el plan de tareas del hito: compara lo que piden las instrucciones del"
            " programa (fragmentos) con el estado del borrador (bloque alcance) y ordena lo que"
            " falta o hay que completar, cada tarea con su criterio de logro y su cita."
        )


class AtencionPlan(AtencionPorAlcance):
    alcance_tipo = TipoAlcance.HITO

    async def version_para(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        referencia: str,
        parametros: ParametrosFuncionales,
    ) -> VersionBorrador:
        if hito_configurado(parametros, referencia) is None:
            raise HitoInexistente()
        version = await unidad.versiones.vigente_del_hito(contexto, referencia)
        if version is None:
            if await unidad.versiones.vigente_mas_reciente(contexto) is None:
                raise SinVersion()
            raise SinVersionDelHito()
        completa = await unidad.versiones.con_parrafos(contexto, version.id)
        assert completa is not None
        return completa

    def referencia_guardada(self, referencia: str) -> str | None:
        return None

    def resolver(
        self, version: VersionBorrador, referencia: str, parametros: ParametrosFuncionales
    ) -> str:
        hito = hito_configurado(parametros, version.hito)
        if hito is None:
            raise HitoInexistente()
        return estado_del_borrador(version, hito)

    def ajustar(self, salida: dict[str, Any], texto: str) -> dict[str, Any]:
        """El hito lo pone el sistema; las tareas, en orden y numeradas desde 1."""
        primera = texto.splitlines()[0] if texto else ""
        tareas = sorted(
            (t for t in salida.get("tareas", []) if isinstance(t, dict)),
            key=lambda t: t.get("orden", 0),
        )
        return {
            **salida,
            "hito": primera.removeprefix("Hito de la versión: ") or salida.get("hito", ""),
            "tareas": [{**t, "orden": i} for i, t in enumerate(tareas, 1)],
        }

    def comprobaciones(
        self,
        salida: dict[str, Any],
        texto: str,
        parametros: ParametrosFuncionales,
        recuperados: Mapping[str, str],
    ) -> list[Comprobacion]:
        return [
            comprobar_esquema(self.tipo, salida),
            comprobar_no_reescritura(salida, texto, parametros.limite_reescritura_palabras),
            comprobar_citas(salida, recuperados),
        ]
