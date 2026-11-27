"""Fábrica de los ejecutores de cada tipo (T28), la misma para la API y el trabajador.

Un proceso usa una sola cadena de modelos y un solo cliente del servicio de modelos para
todos los agentes: así el limitador de cada proveedor cuenta las llamadas de todos (antes,
cada pantalla armaba su propia cadena). La API usa el ejecutor de un tipo para validar y
crear la solicitud (``iniciar``); el orquestador, para ejecutarla.

Si falta un servicio que el tipo necesita (servicio de modelos o GROBID), la fábrica lanza
``CorpusNoConfigurado``: la API responde 503 sin crear la solicitud.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.administracion.parametros import ParametrosFuncionales
from app.agentes.ejecucion import Ejecutor
from app.agentes.estructura import AgenteEstructura
from app.agentes.evidencia import AgenteEvidencia, AtencionEvidencia
from app.agentes.metodologia import AgenteMetodologia, AtencionMetodologia
from app.agentes.plan import AgentePlan, AtencionPlan
from app.agentes.redaccion import AgenteRedaccion, AtencionRedaccion
from app.agentes.referencias import AtencionReferencias
from app.agentes.seccion import AtencionSeccion
from app.agentes.verificacion_referencias import Verificador
from app.bd.enumeraciones import TipoSolicitud
from app.bibliografia.fabrica import crear_servicios
from app.bibliografia.referencias import ConstructorReferencias
from app.configuracion import Ajustes
from app.corpus.fabrica import CorpusNoConfigurado
from app.corpus.grobid import ClienteGrobid
from app.inferencia.servicio_modelos import ClienteServicioModelos, cliente_desde_ajustes
from app.llm.cadena import CadenaModelos
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from app.repositorios.unidad import FabricaUnidades

# Atributo de ``app.state`` con el ejecutor de cada tipo (las pruebas lo sustituyen).
ATRIBUTOS: dict[TipoSolicitud, str] = {
    TipoSolicitud.BUSQUEDA_EVIDENCIA: "atencion_evidencia",
    TipoSolicitud.VERIFICACION_REFERENCIAS: "atencion_referencias",
    TipoSolicitud.REVISION_ESTRUCTURA: "atencion_estructura",
    TipoSolicitud.PROPUESTA_REDACCION: "atencion_redaccion",
    TipoSolicitud.REVISION_METODOLOGICA: "atencion_metodologia",
    TipoSolicitud.PLAN_TAREA: "atencion_plan",
}


class FabricaEjecutores:
    def __init__(
        self,
        ajustes: Ajustes,
        parametros: ParametrosFuncionales,
        abrir: FabricaUnidades,
        reloj: Callable[[], datetime],
    ) -> None:
        self._ajustes = ajustes
        self._parametros = parametros
        self._abrir = abrir
        self._reloj = reloj
        self._cadena: CadenaModelos | None = None
        self._modelos: ClienteServicioModelos | None = None
        self._ejecutores: dict[TipoSolicitud, Ejecutor] = {}

    def _cadena_compartida(self) -> CadenaModelos:
        if self._cadena is None:
            self._cadena = crear_cadena(
                self._ajustes, self._parametros, registrador_en_base(self._abrir)
            )
        return self._cadena

    def _servicio_modelos(self) -> ClienteServicioModelos:
        if not self._ajustes.url_servicio_modelos:
            raise CorpusNoConfigurado(["URL_SERVICIO_MODELOS"])
        if self._modelos is None:
            self._modelos = cliente_desde_ajustes(self._ajustes)
        return self._modelos

    def _evidencia(self) -> ServicioEvidencia:
        modelos = self._servicio_modelos()
        return ServicioEvidencia(
            Recuperador(modelos, modelos), self._cadena_compartida(), self._reloj
        )

    def __call__(self, tipo: TipoSolicitud) -> Ejecutor:
        if tipo not in self._ejecutores:
            self._ejecutores[tipo] = self._crear(tipo)
        return self._ejecutores[tipo]

    def _crear(self, tipo: TipoSolicitud) -> Any:
        reloj, cadena = self._reloj, self._cadena_compartida
        if tipo is TipoSolicitud.VERIFICACION_REFERENCIAS:
            if not self._ajustes.url_grobid:
                raise CorpusNoConfigurado(["URL_GROBID"])
            servicios = crear_servicios(self._ajustes, self._abrir)
            return AtencionReferencias(
                ClienteGrobid(self._ajustes.url_grobid),
                Verificador(servicios.crossref, servicios.openalex),
                cadena(),
                reloj,
            )
        evidencia = self._evidencia()
        if tipo is TipoSolicitud.BUSQUEDA_EVIDENCIA:
            return AtencionEvidencia(
                AgenteEvidencia(evidencia, cadena()),
                self._servicio_modelos(),
                ConstructorReferencias(crear_servicios(self._ajustes, self._abrir).doi),
                reloj,
            )
        if tipo is TipoSolicitud.REVISION_ESTRUCTURA:
            return AtencionSeccion(tipo, AgenteEstructura(evidencia, cadena()), reloj)
        if tipo is TipoSolicitud.REVISION_METODOLOGICA:
            return AtencionMetodologia(tipo, AgenteMetodologia(evidencia, cadena()), reloj)
        if tipo is TipoSolicitud.PROPUESTA_REDACCION:
            return AtencionRedaccion(tipo, AgenteRedaccion(evidencia, cadena()), reloj)
        if tipo is TipoSolicitud.PLAN_TAREA:
            return AtencionPlan(tipo, AgentePlan(evidencia, cadena()), reloj)
        raise ValueError(f"tipo sin ejecutor: {tipo}")

    async def cerrar(self) -> None:
        if self._modelos is not None:
            await self._modelos.cerrar()
