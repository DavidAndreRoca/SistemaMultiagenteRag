"""Agente D4 de búsqueda de evidencia y su atención directa (T19-01; RF-08, CU-07, CP-11).

* ``AgenteEvidencia``: el contrato común de T18 con la instrucción ``evidencia`` y la
  consulta del estudiante como alcance.
* ``AtencionEvidencia``: la ruta directa del bloque 1, sin orquestador (T28). Valida la
  consulta antes de encolar, crea la solicitud y la atiende en segundo plano, una a la vez
  por proceso. Al terminar aplica las comprobaciones 1, 3 y 5:

  - las fuentes recomendadas son solo los documentos citados con acceso abierto
    comprobado (RN-14), con su referencia armada desde los metadatos (RN-17);
  - si una comprobación falla, el resultado se entrega con la etiqueta "Con advertencias"
    y la lista de las fallidas. El reintento y la verificación completa son de T30.

El registro guarda estados, motivos y cantidades, nunca la consulta ni la salida (4.6).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.agentes.contrato import Agente, EstadoAgente
from app.agentes.validacion_consulta import Rechazo, validar
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoAlcance, TipoSolicitud
from app.bd.modelos import Resultado, Solicitud
from app.bibliografia.referencias import ConstructorReferencias
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.inferencia.interfaces import ProveedorEmbeddings
from app.llm.modelos import ErrorModelo
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import FabricaUnidades, UnidadDeTrabajo
from app.verificacion.comprobaciones import (
    ACCESO_ABIERTO_COMPROBADO,
    comprobar_acceso_abierto,
    comprobar_citas,
    comprobar_esquema,
    identificadores_citados,
)

TIPO = TipoSolicitud.BUSQUEDA_EVIDENCIA
EN_CURSO = frozenset(
    {EstadoSolicitud.RECIBIDA, EstadoSolicitud.ASIGNADA, EstadoSolicitud.RECUPERANDO,
     EstadoSolicitud.GENERANDO}
)  # fmt: skip
INVITACION_APORTE = (
    "Puede aportar una fuente de acceso abierto sobre su consulta para que el sistema la"
    " compruebe y la incluya en su colección personal."
)
_registro = obtener_registrador("agentes")


class AgenteEvidencia(Agente):
    tipos = frozenset({TIPO})
    instruccion = "evidencia"

    def consulta(self, estado: EstadoAgente) -> str:
        return estado.alcance

    def tarea(self, estado: EstadoAgente) -> str:
        return (
            "Responde la consulta del estudiante (bloque alcance) solo con la evidencia de los"
            " fragmentos, citando en cada afirmación los fragmentos que la sostienen."
        )


class SinVersion(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sin_version",
            "Para pedir evidencia, primero cargue una versión de su borrador.",
            estado_http=409,
        )


class ConsultaRechazada(ErrorAplicacion):
    def __init__(self, rechazo: Rechazo, solicitud_id: uuid.UUID) -> None:
        super().__init__(
            "consulta_rechazada",
            rechazo.mensaje,
            estado_http=422,
            detalle={"motivo": rechazo.motivo.value, "solicitud_id": str(solicitud_id)},
        )


@dataclass
class _Avance:
    activas: set[uuid.UUID] = field(default_factory=set)
    tareas: set[asyncio.Task[None]] = field(default_factory=set)


class AtencionEvidencia:
    def __init__(
        self,
        agente: AgenteEvidencia,
        embeddings: ProveedorEmbeddings,
        referencias: ConstructorReferencias,
        abrir: FabricaUnidades,
        reloj: Callable[[], datetime],
    ) -> None:
        self._agente = agente
        self._embeddings = embeddings
        self._referencias = referencias
        self._abrir = abrir
        self._reloj = reloj
        self._candado = asyncio.Lock()
        self._avance = _Avance()

    @property
    def activas(self) -> frozenset[uuid.UUID]:
        return frozenset(self._avance.activas)

    async def iniciar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, consulta: str
    ) -> Solicitud:
        """Valida, crea la solicitud y la deja en curso. Una rechazada queda registrada."""
        version = await unidad.versiones.vigente_mas_reciente(contexto)
        if version is None:
            raise SinVersion()
        configuracion, parametros = await unidad.configuracion.vigente()
        rechazo = await validar(unidad, contexto, consulta, parametros, self._embeddings)
        ahora = self._reloj()
        solicitud = await unidad.solicitudes.agregar(
            contexto,
            Solicitud(
                version_id=version.id,
                tipo=TIPO,
                alcance_tipo=TipoAlcance.CONSULTA,
                alcance_ref=consulta.strip(),
                configuracion_id=configuracion.id,
                estado=EstadoSolicitud.RECHAZADA if rechazo else EstadoSolicitud.RECIBIDA,
                motivo=rechazo.motivo.value if rechazo else None,
                creada_en=ahora,
                actualizada_en=ahora,
            ),
        )
        await unidad.confirmar()
        _registro.info(
            "solicitud de evidencia",
            extra={
                "tipo_evento": "validacion" if rechazo else "agentes",
                "solicitud_id": str(solicitud.id),
                "estado": solicitud.estado.value,
                "motivo": solicitud.motivo,
                "similitud": rechazo.similitud if rechazo else None,
            },
        )
        if rechazo is not None:
            raise ConsultaRechazada(rechazo, solicitud.id)
        return solicitud

    def lanzar(self, solicitud: Solicitud, contexto: ContextoAcceso) -> None:
        estado = EstadoAgente(
            solicitud_id=solicitud.id,
            caso_id=solicitud.caso_id,
            tipo=TIPO,
            alcance=solicitud.alcance_ref or "",
            version_id=solicitud.version_id,
        )
        self._avance.activas.add(solicitud.id)
        tarea = asyncio.create_task(self.atender(contexto, estado))
        self._avance.tareas.add(tarea)
        tarea.add_done_callback(self._avance.tareas.discard)

    async def esperar(self) -> None:
        while self._avance.tareas:
            await asyncio.gather(*list(self._avance.tareas), return_exceptions=True)

    def cancelar(self) -> None:
        for tarea in list(self._avance.tareas):
            tarea.cancel()

    async def atender(self, contexto: ContextoAcceso, estado: EstadoAgente) -> None:
        self._avance.activas.add(estado.solicitud_id)
        try:
            async with self._candado, self._abrir() as unidad:
                await self._atender(unidad, contexto, estado)
        except Exception as error:
            motivo = (
                f"modelo:{error.motivo.value}"
                if isinstance(error, ErrorModelo)
                else getattr(error, "codigo", type(error).__name__)
            )
            _registro.warning(
                "solicitud de evidencia no atendida",
                extra={
                    "tipo_evento": "agentes",
                    "solicitud_id": str(estado.solicitud_id),
                    "motivo": motivo,
                },
            )
            async with self._abrir() as unidad:
                await self._cambiar(
                    unidad, contexto, estado.solicitud_id, EstadoSolicitud.NO_ATENDIDA, motivo
                )
        finally:
            self._avance.activas.discard(estado.solicitud_id)

    async def _atender(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, estado: EstadoAgente
    ) -> None:
        await self._cambiar(unidad, contexto, estado.solicitud_id, EstadoSolicitud.RECUPERANDO)
        resultado = await self._agente.atender(unidad, contexto, estado)
        if resultado.abstencion:  # T16 ya registró la abstención y sus fragmentos
            await self._cambiar(unidad, contexto, estado.solicitud_id, EstadoSolicitud.ENTREGADA)
            return
        assert resultado.salida is not None
        salida = resultado.salida.model_dump(mode="json")
        citados = identificadores_citados(salida)
        documentos = await unidad.fragmentos_recuperados.documentos_citados(
            contexto, estado.solicitud_id, citados
        )
        recuperados = await unidad.fragmentos_recuperados.identificadores(
            contexto, estado.solicitud_id
        )
        estado_oa = {i: d.estado_oa.value for i, d in documentos}
        comprobaciones = [
            comprobar_esquema(TIPO, salida),
            comprobar_citas(salida, recuperados),
            comprobar_acceso_abierto(estado_oa),
        ]
        recomendables = [i for i, d in documentos if d.estado_oa.value in ACCESO_ABIERTO_COMPROBADO]
        caso = await unidad.caso_propio.obtener(contexto)
        assert caso is not None
        referencias = await self._referencias.construir(
            unidad, contexto, estado.solicitud_id, recomendables, caso[0].norma_citacion
        )
        fallidas = [c for c in comprobaciones if not c.superada]
        await unidad.resultados.agregar(
            contexto,
            Resultado(
                solicitud_id=estado.solicitud_id,
                intento=estado.intento,
                salida={
                    **salida,
                    "fuentes": [
                        {"documento_id": str(r.documento_id), "identificadores": r.identificadores}
                        for r in referencias
                    ],
                    "referencias": [r.model_dump(mode="json") for r in referencias],
                    "comprobaciones": [c.model_dump(mode="json") for c in comprobaciones],
                    "modelo": {
                        "instruccion": resultado.instruccion,
                        "proveedor": resultado.proveedor,
                        "modelo": resultado.modelo,
                    },
                },
                etiqueta=Etiqueta.CON_ADVERTENCIAS if fallidas else None,
                advertencias=[m for c in fallidas for m in c.motivos],
                creado_en=self._reloj(),
            ),
        )
        await self._cambiar(unidad, contexto, estado.solicitud_id, EstadoSolicitud.ENTREGADA)
        _registro.info(
            "evidencia entregada",
            extra={
                "tipo_evento": "agentes",
                "solicitud_id": str(estado.solicitud_id),
                "afirmaciones": len(salida.get("respuesta", [])),
                "fuentes_recomendadas": len(referencias),
                "comprobaciones_fallidas": [c.nombre for c in fallidas],
            },
        )

    async def _cambiar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud_id: uuid.UUID,
        estado: EstadoSolicitud,
        motivo: str | None = None,
    ) -> None:
        solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
        if solicitud is None:
            return
        ahora = self._reloj()
        solicitud.estado = estado
        solicitud.actualizada_en = ahora
        if motivo is not None:
            solicitud.motivo = motivo[:200]
        if estado is EstadoSolicitud.ENTREGADA:
            solicitud.entregada_en = ahora
        await unidad.confirmar()

    async def marcar_interrumpida(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> None:
        """Una solicitud en curso que este proceso no atiende quedó cortada (reinicio)."""
        if solicitud.estado in EN_CURSO and solicitud.id not in self.activas:
            await self._cambiar(
                unidad, contexto, solicitud.id, EstadoSolicitud.NO_ATENDIDA, "interrumpida"
            )
