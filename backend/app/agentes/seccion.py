"""Atención de los agentes que trabajan sobre una parte del borrador (T23, T24, T26 y T27; D1
a D3). Desde T28 la ejecuta el orquestador (``app/orquestacion/``).

``AtencionPorAlcance`` es el camino común:

* ``iniciar`` (en la API): exige una versión vigente, valida el alcance (``resolver``) antes
  de crear nada y crea la solicitud, que queda en la cola.
* ``ejecutar``, ``verificar`` y ``registrar`` (ejecutor de T28, ``app/agentes/ejecucion.py``):
  el agente recupera de las guías, decide la suficiencia y genera (contrato de T18); se
  aplican las comprobaciones del tipo y se guarda el resultado. Si alguna falla, el
  resultado va "Con advertencias" (el reintento es de T30).

``AtencionSeccion`` (D1 y D2) toma una sección que no sea la lista de referencias y aplica
las comprobaciones 1 (esquema), 3 (citas a los fragmentos recuperados) y 2 (no reescritura,
CP-08); los hallazgos se guardan de mayor a menor severidad. D3 tiene la suya en
``app/agentes/redaccion.py``.

El registro guarda estados y cantidades, nunca el texto del borrador ni de la salida (4.6).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any, ClassVar

from app.administracion.parametros import ParametrosFuncionales
from app.agentes.contrato import Agente, EstadoAgente
from app.agentes.ejecucion import Ejecucion, advertencias_de, cambiar_estado
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoAlcance, TipoSolicitud
from app.bd.modelos import Resultado, Solicitud, VersionBorrador
from app.borradores.secciones import descendientes
from app.borradores.servicio import parrafos_de, secciones_de
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import (
    Comprobacion,
    comprobar_citas,
    comprobar_esquema,
    comprobar_no_reescritura,
)

ORDEN_SEVERIDAD = {"alta": 0, "media": 1, "baja": 2}
_registro = obtener_registrador("agentes")


class SinVersion(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sin_version",
            "Para pedir una revisión, primero cargue una versión de su borrador.",
            estado_http=409,
        )


class SinSecciones(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sin_secciones",
            "No se detectaron las secciones de su versión. Use estilos de título (Título 1,"
            " Título 2) en el documento y vuelva a cargarlo.",
            estado_http=422,
        )


class SeccionInexistente(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "seccion_inexistente",
            "Esa sección no está en su versión vigente.",
            estado_http=422,
        )


def secciones_revisables(version: VersionBorrador) -> list[tuple[str, str, int]]:
    """(id, título, palabras) de las secciones que se pueden revisar: todas menos la lista
    de referencias, con el texto de sus subsecciones."""
    secciones = secciones_de(version)
    if secciones is None:
        return []
    texto = {p.id: p.texto for p in parrafos_de(version)}
    referencias = secciones.referencias.seccion if secciones.referencias else None
    revisables = []
    for seccion in secciones.secciones:
        if seccion.id == referencias or seccion.clase == "referencias":
            continue
        incluidas = descendientes(secciones.secciones, seccion.id)
        palabras = sum(len(texto.get(p, "").split()) for s in incluidas for p in s.parrafos)
        if palabras:
            revisables.append((seccion.id, seccion.titulo, palabras))
    return revisables


def alcance_de_seccion(version: VersionBorrador, seccion_id: str) -> tuple[str, str]:
    """(título, texto) de la sección con sus subsecciones; cada párrafo con su identificador
    para que el agente pueda ubicar sus hallazgos."""
    secciones = secciones_de(version)
    if secciones is None or not secciones.secciones:
        raise SinSecciones()
    if seccion_id not in {s[0] for s in secciones_revisables(version)}:
        raise SeccionInexistente()
    texto = {p.id: p.texto for p in parrafos_de(version)}
    incluidas = descendientes(secciones.secciones, seccion_id)
    lineas: list[str] = []
    for seccion in incluidas:
        lineas.append(f"## {seccion.titulo}")
        lineas.extend(f"[{p}] {texto[p]}" for p in seccion.parrafos if p in texto)
    return incluidas[0].titulo, "\n".join(lineas)


class AtencionPorAlcance:
    """Camino común de los agentes que trabajan sobre una parte de la versión vigente."""

    alcance_tipo: ClassVar[TipoAlcance]

    def __init__(
        self,
        tipo: TipoSolicitud,
        agente: Agente,
        reloj: Callable[[], datetime],
    ) -> None:
        self.tipo = tipo
        self._agente = agente
        self._reloj = reloj

    async def version_vigente(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso
    ) -> VersionBorrador:
        version = await unidad.versiones.vigente_mas_reciente(contexto)
        if version is None:
            raise SinVersion()
        completa = await unidad.versiones.con_parrafos(contexto, version.id)
        assert completa is not None
        return completa

    def resolver(
        self, version: VersionBorrador, referencia: str, parametros: ParametrosFuncionales
    ) -> str:
        """El texto del alcance que recibe el agente; lanza un error si no es válido."""
        raise NotImplementedError

    def ajustar(self, salida: dict[str, Any], texto: str) -> dict[str, Any]:
        """Ajuste determinista de la salida antes de comprobarla y guardarla."""
        return salida

    def comprobaciones(
        self,
        salida: dict[str, Any],
        texto: str,
        parametros: ParametrosFuncionales,
        recuperados: Mapping[str, str],
    ) -> list[Comprobacion]:
        return [comprobar_esquema(self.tipo, salida), comprobar_citas(salida, recuperados)]

    async def version_para(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        referencia: str,
        parametros: ParametrosFuncionales,
    ) -> VersionBorrador:
        """La versión sobre la que se atiende: por defecto, la vigente más reciente."""
        return await self.version_vigente(unidad, contexto)

    def referencia_guardada(self, referencia: str) -> str | None:
        """``alcance_ref`` de la solicitud. Un alcance de hito no la lleva (T24)."""
        return referencia

    async def iniciar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, referencia: str
    ) -> Solicitud:
        configuracion, parametros = await unidad.configuracion.vigente()
        version = await self.version_para(unidad, contexto, referencia, parametros)
        self.resolver(version, referencia, parametros)  # valida antes de crear nada
        ahora = self._reloj()
        solicitud = await unidad.solicitudes.agregar(
            contexto,
            Solicitud(
                version_id=version.id,
                tipo=self.tipo,
                alcance_tipo=self.alcance_tipo,
                alcance_ref=self.referencia_guardada(referencia),
                configuracion_id=configuracion.id,
                estado=EstadoSolicitud.RECIBIDA,
                creada_en=ahora,
                actualizada_en=ahora,
            ),
        )
        await unidad.confirmar()
        _registro.info(
            "solicitud sobre una parte del borrador",
            extra={
                "tipo_evento": "agentes",
                "solicitud_id": str(solicitud.id),
                "tipo": self.tipo.value,
            },
        )
        return solicitud

    async def ejecutar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> Ejecucion:
        await cambiar_estado(
            unidad, contexto, solicitud.id, EstadoSolicitud.RECUPERANDO, self._reloj
        )
        version = await unidad.versiones.con_parrafos(contexto, solicitud.version_id)
        assert version is not None
        _, parametros = await unidad.configuracion.vigente()
        texto = self.resolver(version, solicitud.alcance_ref or "", parametros)
        estado = EstadoAgente(
            solicitud_id=solicitud.id,
            caso_id=solicitud.caso_id,
            tipo=self.tipo,
            alcance=texto,
            hito=version.hito,
            version_id=solicitud.version_id,
        )

        async def generando() -> None:
            await cambiar_estado(
                unidad, contexto, solicitud.id, EstadoSolicitud.GENERANDO, self._reloj
            )

        resultado = await self._agente.atender(unidad, contexto, estado, generando)
        if resultado.abstencion:  # T16 ya registró la abstención
            return Ejecucion(abstencion=True)
        assert resultado.salida is not None
        salida = self.ajustar(resultado.salida.model_dump(mode="json"), texto)
        recuperados = {
            r.identificador_visible: f.texto
            for r, f, _ in await unidad.fragmentos_recuperados.detalle(contexto, solicitud.id)
        }
        return Ejecucion(
            abstencion=False,
            salida=salida,
            datos={
                "texto": texto,
                "parametros": parametros,
                "recuperados": recuperados,
                "modelo": {
                    "instruccion": resultado.instruccion,
                    "proveedor": resultado.proveedor,
                    "modelo": resultado.modelo,
                },
            },
        )

    def verificar(self, ejecucion: Ejecucion) -> list[Comprobacion]:
        assert ejecucion.salida is not None
        datos = ejecucion.datos
        return self.comprobaciones(
            ejecucion.salida, datos["texto"], datos["parametros"], datos["recuperados"]
        )

    async def registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
        comprobaciones: Sequence[Comprobacion],
        etiqueta: Etiqueta | None,
    ) -> None:
        salida = ejecucion.salida or {}
        await unidad.resultados.agregar(
            contexto,
            Resultado(
                solicitud_id=solicitud.id,
                intento=1,
                salida={
                    **salida,
                    "comprobaciones": [c.model_dump(mode="json") for c in comprobaciones],
                    "modelo": ejecucion.datos.get("modelo"),
                },
                etiqueta=etiqueta,
                advertencias=advertencias_de(comprobaciones),
                creado_en=self._reloj(),
            ),
        )
        await unidad.confirmar()
        _registro.info(
            "solicitud sobre una parte del borrador registrada",
            extra={
                "tipo_evento": "agentes",
                "solicitud_id": str(solicitud.id),
                "tipo": self.tipo.value,
                "hallazgos": len(salida.get("hallazgos", [])),
                "cambios": len(salida.get("cambios", [])),
                "tareas": len(salida.get("tareas", [])),
                "comprobaciones_fallidas": [c.nombre for c in comprobaciones if not c.superada],
            },
        )


class AtencionSeccion(AtencionPorAlcance):
    """D1 y D2: una sección con sus subsecciones (CP-08)."""

    alcance_tipo = TipoAlcance.SECCION

    def resolver(
        self, version: VersionBorrador, referencia: str, parametros: ParametrosFuncionales
    ) -> str:
        return alcance_de_seccion(version, referencia)[1]

    def ajustar(self, salida: dict[str, Any], texto: str) -> dict[str, Any]:
        if "hallazgos" in salida:
            salida["hallazgos"] = sorted(
                salida["hallazgos"], key=lambda h: ORDEN_SEVERIDAD.get(h.get("severidad"), 3)
            )
        return salida

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
