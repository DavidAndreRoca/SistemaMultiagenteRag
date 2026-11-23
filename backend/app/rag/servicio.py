"""Recuperar, decidir la suficiencia y registrar, para una solicitud (T16-01, apartados 2 y 5).

``ServicioEvidencia.preparar`` es lo que el grafo de T28 llamará antes de generar:
devuelve el contexto cerrado (``F1`` a ``Fn``) o la abstención. Con abstención, la
función de generación no se llama nunca (RN-04, RNF-04, CP-05).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from app.bd.enumeraciones import Etiqueta
from app.bd.modelos import EventoTecnico, FragmentoRecuperado, Resultado, Solicitud
from app.comun.registro import obtener_registrador
from app.instrucciones.cargador import vigente
from app.llm.interfaces import ModeloLenguaje
from app.rag.modelos import AVISO_SIN_EVIDENCIA, DecisionSuficiencia, Recuperacion
from app.rag.recuperacion import Recuperador
from app.rag.suficiencia import decidir
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo

AGENTE_SUFICIENCIA = "suficiencia"
_registro = obtener_registrador("rag")


class SolicitudInexistente(LookupError):
    pass


@dataclass(frozen=True)
class Evidencia:
    recuperacion: Recuperacion
    decision: DecisionSuficiencia

    @property
    def suficiente(self) -> bool:
        return self.decision.suficiente


class ServicioEvidencia:
    def __init__(
        self,
        recuperador: Recuperador,
        modelo: ModeloLenguaje,
        reloj: Callable[[], datetime],
    ) -> None:
        self._recuperador = recuperador
        self._modelo = modelo
        self._reloj = reloj

    async def preparar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud_id: uuid.UUID,
        consulta: str,
    ) -> Evidencia:
        solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
        if solicitud is None:  # de otro caso o inexistente: lo mismo (4.4)
            raise SolicitudInexistente(str(solicitud_id))
        _, parametros = await unidad.configuracion.vigente()
        inicio = self._reloj()
        recuperacion = await self._recuperador.recuperar(
            unidad, contexto, solicitud.tipo, consulta, parametros
        )
        instruccion = vigente(AGENTE_SUFICIENCIA, parametros.versiones_instrucciones)
        decision = await decidir(self._modelo, instruccion, consulta, recuperacion, parametros)
        await self._registrar(unidad, contexto, solicitud, recuperacion, decision, inicio)
        return Evidencia(recuperacion, decision)

    async def atender[T](
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud_id: uuid.UUID,
        consulta: str,
        generar: Callable[[Evidencia], Awaitable[T]],
    ) -> T | Evidencia:
        """Genera solo si la evidencia alcanza; si no, devuelve la abstención (RN-04)."""
        evidencia = await self.preparar(unidad, contexto, solicitud_id, consulta)
        if not evidencia.suficiente:
            return evidencia
        return await generar(evidencia)

    async def _registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        recuperacion: Recuperacion,
        decision: DecisionSuficiencia,
        inicio: datetime,
    ) -> None:
        for fragmento in recuperacion.fragmentos:
            candidato = fragmento.candidato
            await unidad.fragmentos_recuperados.agregar(
                contexto,
                FragmentoRecuperado(
                    solicitud_id=solicitud.id,
                    fragmento_id=candidato.fragmento_id,
                    identificador_visible=fragmento.identificador,
                    puntaje_denso=candidato.puntaje_denso,
                    puntaje_lexico=candidato.puntaje_lexico,
                    puntaje_fusionado=candidato.puntaje_fusionado,
                    puntaje_reranking=candidato.puntaje_reranking,
                    posicion=fragmento.posicion,
                ),
            )
        for etapa, duracion in (
            ("recuperacion", recuperacion.duracion_recuperacion_ms),
            ("reranking", recuperacion.duracion_reranking_ms),
        ):
            await unidad.eventos_tecnicos.agregar(
                EventoTecnico(
                    solicitud_id=solicitud.id, etapa=etapa, inicio=inicio, duracion_ms=duracion
                )
            )
        if not decision.suficiente:
            await unidad.resultados.agregar(
                contexto,
                Resultado(
                    solicitud_id=solicitud.id,
                    intento=1,
                    salida={
                        "aviso": AVISO_SIN_EVIDENCIA,
                        "paso": decision.paso.value,
                        "motivo": decision.motivo,
                        "sobre_umbral": decision.sobre_umbral,
                    },
                    etiqueta=Etiqueta.SIN_EVIDENCIA_SUFICIENTE,
                    abstencion=True,
                ),
            )
        await unidad.confirmar()
        _registro.info(
            "suficiencia",
            extra={
                "tipo_evento": "rag",
                "solicitud_id": str(solicitud.id),
                "suficiente": decision.suficiente,
                "paso": decision.paso.value,
                "sobre_umbral": decision.sobre_umbral,
                "fragmentos": len(recuperacion.fragmentos),
            },
        )
