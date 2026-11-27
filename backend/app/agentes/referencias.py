"""Agente D4 de verificación de referencias y su atención (T20; RF-09, CU-08, CP-12, CP-13,
RN-18; decisión T20-01). Desde T28 la ejecuta el orquestador.

1. ``iniciar`` (en la API): exige una versión vigente con la lista de referencias detectada
   (T12) y crea la solicitud sobre esa versión. Si la lista no se detectó, pide indicarla
   (RF-09, A).
2. ``ejecutar`` (ejecutor de T28), con avance (referencias hechas de un total):
   - estructura las entradas con GROBID (``processCitationList``);
   - verifica cada referencia por DOI o por metadatos (``Verificador``);
   - extrae las citas del texto según la norma del caso y las cruza con la lista;
   - si se configura, pide al modelo una explicación breve de cada discrepancia. El modelo
     no decide estados ni escribe referencias (RN-17);
   - ``verificar`` aplica la comprobación 1 al informe y ``registrar`` lo guarda.

El registro guarda estados, cantidades y motivos, nunca el texto del borrador ni de las
referencias (4.6).
"""

from __future__ import annotations

import asyncio
import re
import uuid
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.agentes.citas import (
    NUMERICAS,
    EntradaLista,
    cruzar,
    entrada_desde_texto,
    extraer_citas,
)
from app.agentes.ejecucion import Ejecucion, advertencias_de, cambiar_estado
from app.agentes.esquemas import (
    EstadoReferencia,
    ReferenciaVerificada,
    TextoCorto,
    VerificacionReferencias,
)
from app.agentes.verificacion_referencias import Verificador
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoAlcance, TipoSolicitud
from app.bd.modelos import Resultado, Solicitud
from app.bibliografia.normalizacion import normalizar, normalizar_doi
from app.borradores.extraccion import ParrafoBorrador
from app.borradores.secciones import SeccionesVersion
from app.borradores.servicio import parrafos_de, secciones_de
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.corpus.grobid import ReferenciaGrobid
from app.instrucciones.cargador import vigente
from app.llm.interfaces import ModeloLenguaje
from app.llm.modelos import BloqueDatos, EntradaModelo, ErrorModelo
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import Comprobacion, comprobar_esquema

TIPO = TipoSolicitud.VERIFICACION_REFERENCIAS
MAX_REFERENCIAS = 150
AVISO_NO_COMPROBABLES = (
    "La verificación no pudo completarse para {n} de las referencias porque un servicio"
    " bibliográfico no respondió. No se marcaron como inexistentes: vuelva a pedir la"
    " verificación más tarde."
)
AVISO_SUPERINDICES = (
    "En Vancouver solo se reconocen las citas numéricas entre corchetes o paréntesis. Las"
    " citas en superíndice no se detectan: revíselas a mano."
)
AVISO_SIN_CITAS = (
    "No se encontraron citas en el texto con la forma de la norma {norma}. Revise que cite"
    " con el formato de su norma."
)
AVISO_SIN_EXPLICACIONES = (
    "No se pudieron generar las explicaciones de las discrepancias; el informe está completo"
    " sin ellas."
)
_DOI_EN_TEXTO = r"10\.\d{4,9}/[^\s\"<>]+"
_registro = obtener_registrador("agentes")


class ExtractorReferencias(Protocol):
    def referencias_de_texto(self, entradas: list[str]) -> list[ReferenciaGrobid]: ...


class SinVersion(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sin_version",
            "Para verificar sus referencias, primero cargue una versión de su borrador.",
            estado_http=409,
        )


class ListaNoDetectada(ErrorAplicacion):
    def __init__(self, version_id: uuid.UUID) -> None:
        super().__init__(
            "lista_no_detectada",
            "No se detectó la lista de referencias de su versión. Póngale un título con"
            " estilo de título (por ejemplo, «Referencias» con el estilo Título 1), vuelva a"
            " cargar la versión y pida otra vez la verificación.",
            estado_http=422,
            detalle={"version_id": str(version_id)},
        )


# --- Explicación opcional de las discrepancias (decisión T20-01, d) -------------------


class ExplicacionDiscrepancia(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    indice: int = Field(ge=1)
    explicacion: TextoCorto


class ExplicacionesDiscrepancias(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    explicaciones: list[ExplicacionDiscrepancia] = Field(max_length=MAX_REFERENCIAS)


def _bloque(referencia: ReferenciaVerificada) -> BloqueDatos:
    lineas = [
        f"{d.campo}: en la referencia del estudiante, {d.valor_borrador or 'no figura'};"
        f" en la fuente, {d.valor_fuente or 'no figura'}"
        for d in referencia.discrepancias
    ]
    return BloqueDatos(etiqueta=f"R{referencia.indice}", contenido="\n".join(lineas))


# --- Atención -------------------------------------------------------------------------


def cuerpo(
    parrafos: Sequence[ParrafoBorrador], secciones: SeccionesVersion
) -> list[ParrafoBorrador]:
    """Los párrafos de texto fuera de la lista de referencias (donde se buscan las citas)."""
    orden = [p.id for p in parrafos]
    lista = secciones.referencias
    excluidos: set[str] = set()
    if lista is not None and lista.desde in orden and lista.hasta in orden:
        excluidos = set(orden[orden.index(lista.desde) : orden.index(lista.hasta) + 1])
    return [p for p in parrafos if p.nivel is None and p.id not in excluidos]


def anio_del_texto(entrada: str) -> int | None:
    """El año de una entrada, sin mirar su DOI: el de ``(2020)`` en APA o, si no, el último
    año suelto (IEEE y Vancouver lo ponen al final)."""
    sin_doi = re.sub(_DOI_EN_TEXTO, " ", entrada)
    if entre := re.search(r"\((\d{4})[a-z]?\)", sin_doi):
        return int(entre.group(1))
    sueltos = re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", sin_doi)
    return int(sueltos[-1]) if sueltos else None


def alinear(
    entradas: Sequence[str], analizadas: Sequence[ReferenciaGrobid]
) -> list[ReferenciaGrobid]:
    """Una referencia analizada por entrada, en el orden de la lista. El texto es siempre el
    del estudiante. Si GROBID no trae el DOI o el año pero la entrada los tiene, se toman del
    texto (con páginas largas como ``pp. 101805``, GROBID a veces no devuelve el año)."""
    por_texto = {normalizar(r.texto): r for r in analizadas}
    alineadas = []
    for posicion, entrada in enumerate(entradas):
        analizada = por_texto.get(normalizar(entrada))
        if analizada is None and len(analizadas) == len(entradas):
            analizada = analizadas[posicion]
        base = analizada or ReferenciaGrobid(texto=entrada)
        doi = base.doi
        if not doi and (hallado := re.search(_DOI_EN_TEXTO, entrada)):
            doi = normalizar_doi(hallado.group(0).rstrip(".,;"))
        anio = base.anio if base.anio is not None else anio_del_texto(entrada)
        alineadas.append(base.model_copy(update={"texto": entrada, "doi": doi, "anio": anio}))
    return alineadas


def lista_para_cruce(referencias: Sequence[ReferenciaGrobid], norma: str) -> list[EntradaLista]:
    """Las entradas numeradas en el orden de la lista; en APA, con primer apellido y año."""
    if norma in NUMERICAS:
        return [EntradaLista(indice=i, texto=r.texto) for i, r in enumerate(referencias, start=1)]
    return [
        entrada_desde_texto(
            i, r.texto, apellido=r.apellidos[0] if r.apellidos else None, anio=r.anio
        )
        for i, r in enumerate(referencias, start=1)
    ]


@dataclass
class _Avance:
    progreso: dict[uuid.UUID, tuple[int, int]] = field(default_factory=dict)


class AtencionReferencias:
    def __init__(
        self,
        extractor: ExtractorReferencias,
        verificador: Verificador,
        modelo: ModeloLenguaje | None,
        reloj: Callable[[], datetime],
    ) -> None:
        self.tipo = TIPO
        self._extractor = extractor
        self._verificador = verificador
        self._modelo = modelo
        self._reloj = reloj
        self._avance = _Avance()

    def progreso(self, solicitud_id: uuid.UUID) -> tuple[int, int] | None:
        """Referencias verificadas y total, mientras la solicitud está en curso."""
        return self._avance.progreso.get(solicitud_id)

    async def iniciar(self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso) -> Solicitud:
        version = await unidad.versiones.vigente_mas_reciente(contexto)
        if version is None:
            raise SinVersion()
        secciones = secciones_de(version)
        if secciones is None or secciones.referencias is None or not secciones.referencias.entradas:
            raise ListaNoDetectada(version.id)
        configuracion, _ = await unidad.configuracion.vigente()
        ahora = self._reloj()
        solicitud = await unidad.solicitudes.agregar(
            contexto,
            Solicitud(
                version_id=version.id,
                tipo=TIPO,
                alcance_tipo=TipoAlcance.VERSION,
                alcance_ref=None,
                configuracion_id=configuracion.id,
                estado=EstadoSolicitud.RECIBIDA,
                creada_en=ahora,
                actualizada_en=ahora,
            ),
        )
        await unidad.confirmar()
        _registro.info(
            "solicitud de verificación de referencias",
            extra={
                "tipo_evento": "agentes",
                "solicitud_id": str(solicitud.id),
                "referencias": len(secciones.referencias.entradas),
            },
        )
        return solicitud

    async def ejecutar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> Ejecucion:
        try:
            return await self._ejecutar(unidad, contexto, solicitud.id, solicitud.version_id)
        finally:
            self._avance.progreso.pop(solicitud.id, None)

    async def _ejecutar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> Ejecucion:
        await cambiar_estado(
            unidad, contexto, solicitud_id, EstadoSolicitud.RECUPERANDO, self._reloj
        )
        version = await unidad.versiones.con_parrafos(contexto, version_id)
        caso = await unidad.caso_propio.obtener(contexto)
        assert version is not None and caso is not None
        norma = caso[0].norma_citacion
        secciones = secciones_de(version)
        assert secciones is not None and secciones.referencias is not None
        entradas = secciones.referencias.entradas[:MAX_REFERENCIAS]
        analizadas = await asyncio.to_thread(self._extractor.referencias_de_texto, list(entradas))
        referencias = alinear(entradas, analizadas)

        verificadas: list[ReferenciaVerificada] = []
        self._avance.progreso[solicitud_id] = (0, len(referencias))
        for indice, referencia in enumerate(referencias, start=1):
            verificadas.append(await self._verificador.verificar(indice, referencia))
            self._avance.progreso[solicitud_id] = (indice, len(referencias))

        citas = extraer_citas(cuerpo(parrafos_de(version), secciones), norma)
        cruce = cruzar(citas, lista_para_cruce(referencias, norma), norma)
        informe = VerificacionReferencias(
            referencias=verificadas,
            citas_sin_entrada=[c[:300] for c in cruce.citas_sin_entrada],
            entradas_no_citadas=cruce.entradas_no_citadas,
        )

        avisos: list[str] = []
        resumen = Counter(r.estado.value for r in verificadas)
        if resumen[EstadoReferencia.NO_COMPROBABLE.value]:
            avisos.append(
                AVISO_NO_COMPROBABLES.format(n=resumen[EstadoReferencia.NO_COMPROBABLE.value])
            )
        if norma == "vancouver":
            avisos.append(AVISO_SUPERINDICES)
        if not citas:
            avisos.append(
                AVISO_SIN_CITAS.format(norma=norma.upper() if norma != "apa7" else "APA 7")
            )

        await cambiar_estado(unidad, contexto, solicitud_id, EstadoSolicitud.GENERANDO, self._reloj)
        explicaciones, modelo = await self._explicar(unidad, verificadas, norma, avisos)
        salida = informe.model_dump(mode="json")
        _registro.info(
            "verificación de referencias hecha",
            extra={
                "tipo_evento": "agentes",
                "solicitud_id": str(solicitud_id),
                "norma": norma,
                "referencias": len(verificadas),
                "estados": dict(resumen),
                "citas": len(citas),
                "citas_sin_entrada": len(cruce.citas_sin_entrada),
                "entradas_no_citadas": len(cruce.entradas_no_citadas),
            },
        )
        return Ejecucion(
            abstencion=False,
            salida=salida,
            datos={
                "explicaciones": explicaciones,
                "extra": {
                    "norma": norma,
                    "citas": [c.model_dump(mode="json") for c in cruce.citas],
                    "resumen": dict(resumen),
                    "avisos": avisos,
                    "modelo": modelo,
                },
            },
        )

    def verificar(self, ejecucion: Ejecucion) -> list[Comprobacion]:
        """Comprobación 1: el informe determinista cumple su esquema (sin modelo, RN-17)."""
        assert ejecucion.salida is not None
        return [comprobar_esquema(TIPO, ejecucion.salida)]

    async def registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
        comprobaciones: Sequence[Comprobacion],
        etiqueta: Etiqueta | None,
    ) -> None:
        salida = dict(ejecucion.salida or {})
        explicaciones = ejecucion.datos.get("explicaciones", {})
        salida["referencias"] = [
            {**r, "explicacion": explicaciones.get(r["indice"])}
            for r in salida.get("referencias", [])
        ]
        await unidad.resultados.agregar(
            contexto,
            Resultado(
                solicitud_id=solicitud.id,
                intento=1,
                salida={
                    **salida,
                    **ejecucion.datos.get("extra", {}),
                    "comprobaciones": [c.model_dump(mode="json") for c in comprobaciones],
                },
                etiqueta=etiqueta,
                advertencias=advertencias_de(comprobaciones),
                creado_en=self._reloj(),
            ),
        )
        await unidad.confirmar()

    async def _explicar(
        self,
        unidad: UnidadDeTrabajo,
        verificadas: Sequence[ReferenciaVerificada],
        norma: str,
        avisos: list[str],
    ) -> tuple[dict[int, str], dict[str, Any] | None]:
        con_discrepancias = [
            r
            for r in verificadas
            if r.discrepancias and r.estado is EstadoReferencia.CON_DISCREPANCIAS
        ]
        _, parametros = await unidad.configuracion.vigente()
        if not parametros.explicar_discrepancias or self._modelo is None or not con_discrepancias:
            return {}, None
        try:
            instruccion = vigente("referencias", parametros.versiones_instrucciones)
            resultado = await self._modelo.generar(
                instruccion,
                EntradaModelo(
                    tarea=(
                        "Explica en una frase breve cada discrepancia de las referencias R1 a Rn,"
                        f" para un estudiante que cita en {norma}."
                    ),
                    datos=[_bloque(r) for r in con_discrepancias[:40]],
                ),
                ExplicacionesDiscrepancias,
            )
        except ErrorModelo as error:
            _registro.warning(
                "explicaciones de discrepancias no generadas",
                extra={"tipo_evento": "agentes", "motivo": error.motivo.value},
            )
            avisos.append(AVISO_SIN_EXPLICACIONES)
            return {}, None
        validos = {r.indice for r in con_discrepancias}
        explicaciones = {
            e.indice: e.explicacion for e in resultado.datos.explicaciones if e.indice in validos
        }
        return explicaciones, {
            "instruccion": resultado.instruccion,
            "proveedor": resultado.proveedor.value,
            "modelo": resultado.modelo,
        }
