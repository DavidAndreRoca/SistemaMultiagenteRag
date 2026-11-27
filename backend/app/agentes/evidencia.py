"""Agente D4 de búsqueda de evidencia y su atención directa (T19-01; RF-08, CU-07, CP-11).

* ``AgenteEvidencia``: el contrato común de T18 con la instrucción ``evidencia`` y la
  consulta del estudiante como alcance.
* ``AtencionEvidencia``: en la API valida la consulta antes de encolar y crea la solicitud;
  desde T28 la ejecuta el orquestador con los pasos del ejecutor (``ejecutar``,
  ``verificar`` y ``registrar``). Aplica las comprobaciones 1, 3 y 5:

  - las fuentes recomendadas son solo los documentos citados con acceso abierto
    comprobado (RN-14), más las que aportó el caso (T32, RN-14 no se les aplica), con su
    referencia armada desde los metadatos (RN-17);
  - si una comprobación falla, el resultado se entrega con la etiqueta "Con advertencias"
    y la lista de las fallidas. El reintento y la verificación completa son de T30.

El registro guarda estados, motivos y cantidades, nunca la consulta ni la salida (4.6).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import datetime

from app.agentes.contrato import Agente, EstadoAgente, ResultadoAgente
from app.agentes.ejecucion import Ejecucion, cambiar_estado
from app.agentes.validacion_consulta import Rechazo, validar
from app.bd.enumeraciones import (
    EstadoSolicitud,
    Etiqueta,
    OrigenDocumento,
    TipoAlcance,
    TipoSolicitud,
)
from app.bd.modelos import Resultado, Solicitud
from app.bibliografia.interfaces import ServicioBibliografico
from app.bibliografia.referencias import ConstructorReferencias
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.inferencia.interfaces import ProveedorEmbeddings
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import (
    ACCESO_ABIERTO_COMPROBADO,
    Comprobacion,
    comprobar_acceso_abierto,
    comprobar_citas,
    comprobar_esquema,
    identificadores_citados,
)
from app.verificacion.evaluador import Evaluador
from app.verificacion.fuentes import comprobar_existencia
from app.verificacion.registro import advertencias_de

TIPO = TipoSolicitud.BUSQUEDA_EVIDENCIA
INVITACION_APORTE = (
    "Puede aportar una fuente sobre su consulta, con o sin su PDF, para que el sistema la"
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


class AtencionEvidencia:
    def __init__(
        self,
        agente: AgenteEvidencia,
        embeddings: ProveedorEmbeddings,
        referencias: ConstructorReferencias,
        reloj: Callable[[], datetime],
        evaluador: Evaluador | None = None,
        crossref: ServicioBibliografico | None = None,
    ) -> None:
        """``evaluador`` (comprobación 6) y ``crossref`` (comprobación 4 por DOI) son de T30;
        sin ``crossref``, la existencia de las fuentes se comprueba por metadatos."""
        self.tipo = TIPO
        self._agente = agente
        self._embeddings = embeddings
        self._referencias = referencias
        self._reloj = reloj
        self._evaluador = evaluador
        self._crossref = crossref

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

    async def ejecutar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> Ejecucion:
        await cambiar_estado(
            unidad, contexto, solicitud.id, EstadoSolicitud.RECUPERANDO, self._reloj
        )
        estado = EstadoAgente(
            solicitud_id=solicitud.id,
            caso_id=solicitud.caso_id,
            tipo=TIPO,
            alcance=solicitud.alcance_ref or "",
            version_id=solicitud.version_id,
        )

        async def generando() -> None:
            await cambiar_estado(
                unidad, contexto, solicitud.id, EstadoSolicitud.GENERANDO, self._reloj
            )

        resultado = await self._agente.atender(unidad, contexto, estado, generando)
        if resultado.abstencion:  # T16 ya registró la abstención y sus fragmentos
            return Ejecucion(abstencion=True)
        textos = {
            r.identificador_visible: f.texto
            for r, f, _ in await unidad.fragmentos_recuperados.detalle(contexto, solicitud.id)
        }
        return await self._ejecucion(unidad, contexto, solicitud, resultado, textos, intento=1)

    async def _ejecucion(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        resultado: ResultadoAgente,
        textos: dict[str, str],
        intento: int,
    ) -> Ejecucion:
        assert resultado.salida is not None
        salida = resultado.salida.model_dump(mode="json")
        documentos = await unidad.fragmentos_recuperados.documentos_citados(
            contexto, solicitud.id, identificadores_citados(salida)
        )
        # RN-14 no se aplica a las fuentes que aportó el caso (T32): se recomiendan y no
        # pasan por la comprobación 5.
        aportados = {i for i, d in documentos if d.origen is OrigenDocumento.APORTE}
        recomendados = [
            (i, d)
            for i, d in documentos
            if i in aportados or d.estado_oa.value in ACCESO_ABIERTO_COMPROBADO
        ]
        _, parametros = await unidad.configuracion.vigente()
        return Ejecucion(
            abstencion=False,
            salida=salida,
            intento=intento,
            datos={
                "textos": textos,
                "estado_oa": {i: d.estado_oa.value for i, d in documentos if i not in aportados},
                "recomendables": [i for i, _ in recomendados],
                "documentos_recomendados": [d for _, d in recomendados],
                "umbral": parametros.umbral_fidelidad,
                "estado": resultado.estado,
                "evidencia": resultado.evidencia,
                "modelo": {
                    "instruccion": resultado.instruccion,
                    "proveedor": resultado.proveedor,
                    "modelo": resultado.modelo,
                },
            },
        )

    async def reintentar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        anterior: Ejecucion,
        motivos: Sequence[str],
    ) -> Ejecucion:
        datos = anterior.datos
        resultado = await self._agente.reintentar(
            unidad, datos["estado"], datos["evidencia"], motivos
        )
        return await self._ejecucion(
            unidad, contexto, solicitud, resultado, datos["textos"], intento=2
        )

    async def verificar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
    ) -> list[Comprobacion]:
        """Comprobaciones 1, 3, 4 (existencia de las fuentes recomendadas), 5 (su acceso
        abierto) y 6 (fidelidad de las afirmaciones a los fragmentos citados)."""
        assert ejecucion.salida is not None
        datos = ejecucion.datos
        comprobaciones = [
            comprobar_esquema(TIPO, ejecucion.salida),
            comprobar_citas(ejecucion.salida, datos["textos"]),
            await comprobar_existencia(datos["documentos_recomendados"], self._crossref),
            comprobar_acceso_abierto(datos["estado_oa"]),
        ]
        if self._evaluador is not None:
            comprobaciones.append(
                await self._evaluador.fidelidad(
                    unidad, TIPO, ejecucion.salida, datos["textos"], datos["umbral"]
                )
            )
        return comprobaciones

    async def registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
        comprobaciones: Sequence[Comprobacion],
        etiqueta: Etiqueta,
    ) -> Resultado:
        salida = ejecucion.salida or {}
        caso = await unidad.caso_propio.obtener(contexto)
        assert caso is not None
        referencias = await self._referencias.construir(
            unidad, contexto, solicitud.id, ejecucion.datos["recomendables"], caso[0].norma_citacion
        )
        resultado = await unidad.resultados.agregar(
            contexto,
            Resultado(
                solicitud_id=solicitud.id,
                intento=ejecucion.intento,
                salida={
                    **salida,
                    "fuentes": [
                        {"documento_id": str(r.documento_id), "identificadores": r.identificadores}
                        for r in referencias
                    ],
                    "referencias": [r.model_dump(mode="json") for r in referencias],
                    "comprobaciones": [c.model_dump(mode="json") for c in comprobaciones],
                    "modelo": ejecucion.datos.get("modelo"),
                },
                etiqueta=etiqueta,
                advertencias=advertencias_de(comprobaciones),
                creado_en=self._reloj(),
            ),
        )
        _registro.info(
            "evidencia registrada",
            extra={
                "tipo_evento": "agentes",
                "solicitud_id": str(solicitud.id),
                "intento": ejecucion.intento,
                "afirmaciones": len(salida.get("respuesta", [])),
                "fuentes_recomendadas": len(referencias),
                "comprobaciones_fallidas": [c.nombre for c in comprobaciones if not c.superada],
            },
        )
        return resultado
