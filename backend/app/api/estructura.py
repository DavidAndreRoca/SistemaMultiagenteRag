"""Rutas del caso para el diagnóstico de estructura y coherencia de una sección (T23; RF-04,
CU-03, CP-08).

* ``GET /caso/estructura/secciones``: secciones revisables de la versión vigente.
* ``POST /caso/estructura``: pide el diagnóstico de una sección; responde 202 y el trabajo
  sigue en segundo plano.
* ``GET /caso/estructura/{id}``: avance y resultado, con los hallazgos de mayor a menor
  severidad y cada cita desplegable a su guía y apartado.

Una solicitud de otro caso responde 404, igual que una inexistente (4.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.agentes.estructura import AgenteEstructura
from app.agentes.seccion import AtencionSeccion, alcance_de_seccion, secciones_revisables
from app.api.evidencia import ComprobacionVista, SolicitudInexistente
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoSolicitud
from app.configuracion import Ajustes
from app.corpus.fabrica import CorpusNoConfigurado
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.rag.modelos import AVISO_SIN_EVIDENCIA
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoCaso, Reloj, RelojDep, Unidad, obtener_reloj

router = APIRouter(prefix="/caso/estructura", tags=["estructura"])
TIPO = TipoSolicitud.REVISION_ESTRUCTURA
INDICADORES = {
    "alineacion_problema_objetivos_hipotesis": "Alineación entre problema, objetivos e hipótesis",
    "secuencia_logica_discursiva": "Secuencia lógica y discursiva",
    "cohesion_entre_apartados": "Cohesión entre apartados",
}


class SeccionRevisable(BaseModel):
    id: str
    titulo: str
    palabras: int


class PedidoEstructura(BaseModel):
    seccion_id: str = Field(min_length=1, max_length=40)


class SolicitudEstructura(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    creada_en: datetime


class CitaGuia(BaseModel):
    identificador: str
    texto: str
    guia: str | None
    apartado: str | None


class HallazgoVista(BaseModel):
    indicador: str
    indicador_nombre: str
    ubicacion: str
    descripcion: str
    severidad: str
    recomendacion: str
    citas: list[CitaGuia]


class VistaEstructura(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    entregada_en: datetime | None
    seccion_id: str | None
    seccion_titulo: str | None
    abstencion: bool
    aviso: str | None
    etiqueta: Etiqueta | None
    hallazgos: list[HallazgoVista]
    fortalezas: list[str]
    notas_para_el_estudiante: list[str]
    advertencias: list[str]
    comprobaciones: list[ComprobacionVista]


async def obtener_atencion(peticion: Request, unidad: Unidad) -> AtencionSeccion:
    """Una por proceso; usa el servicio de modelos y el adaptador."""
    estado = peticion.app.state
    actual: AtencionSeccion | None = getattr(estado, "atencion_estructura", None)
    if actual is not None:
        return actual
    ajustes: Ajustes = estado.ajustes
    if not ajustes.url_servicio_modelos:
        raise CorpusNoConfigurado(["URL_SERVICIO_MODELOS"])
    _, parametros = await unidad.configuracion.vigente()
    reloj: Reloj = obtener_reloj(peticion)
    abrir = fabrica_de_unidades(estado.fabrica_sesiones)
    modelos = cliente_desde_ajustes(ajustes)
    cadena = crear_cadena(ajustes, parametros, registrador_en_base(abrir))
    evidencia = ServicioEvidencia(Recuperador(modelos, modelos), cadena, reloj)
    actual = AtencionSeccion(TIPO, AgenteEstructura(evidencia, cadena), abrir, reloj)
    estado.atencion_estructura = actual
    return actual


AtencionDep = Annotated[AtencionSeccion, Depends(obtener_atencion)]


@router.get(
    "/secciones",
    response_model=list[SeccionRevisable],
    summary="Secciones de la versión vigente que se pueden revisar",
)
async def secciones(contexto: ContextoCaso, unidad: Unidad) -> list[SeccionRevisable]:
    version = await unidad.versiones.vigente_mas_reciente(contexto)
    if version is None:
        return []
    completa = await unidad.versiones.con_parrafos(contexto, version.id)
    assert completa is not None
    return [
        SeccionRevisable(id=i, titulo=t, palabras=p) for i, t, p in secciones_revisables(completa)
    ]


@router.post(
    "",
    response_model=SolicitudEstructura,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}, 503: {}},
    summary="Pedir el diagnóstico de estructura y coherencia de una sección",
)
async def pedir_estructura(
    pedido: PedidoEstructura, contexto: ContextoCaso, unidad: Unidad, atencion: AtencionDep
) -> SolicitudEstructura:
    solicitud = await atencion.iniciar(unidad, contexto, pedido.seccion_id)
    atencion.lanzar(solicitud, contexto)
    return SolicitudEstructura(
        id=solicitud.id, estado=solicitud.estado, creada_en=solicitud.creada_en
    )


@router.get(
    "/{solicitud_id}",
    response_model=VistaEstructura,
    summary="Avance y resultado de un diagnóstico de estructura",
)
async def ver_estructura(
    solicitud_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> VistaEstructura:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None or solicitud.tipo is not TIPO:
        raise SolicitudInexistente()
    atencion: AtencionSeccion | None = getattr(peticion.app.state, "atencion_estructura", None)
    if atencion is not None:
        await atencion.marcar_interrumpida(unidad, contexto, solicitud)
    elif solicitud.estado in {
        EstadoSolicitud.RECIBIDA,
        EstadoSolicitud.RECUPERANDO,
        EstadoSolicitud.GENERANDO,
    }:
        solicitud.estado, solicitud.motivo = EstadoSolicitud.NO_ATENDIDA, "interrumpida"
        solicitud.actualizada_en = reloj()
        await unidad.confirmar()
    titulo: str | None = None
    version = await unidad.versiones.con_parrafos(contexto, solicitud.version_id)
    if version is not None and solicitud.alcance_ref:
        try:
            titulo, _ = alcance_de_seccion(version, solicitud.alcance_ref)
        except Exception:  # la versión ya no tiene esa sección: se muestra sin título
            titulo = None
    resultado = await unidad.resultados.de_solicitud(contexto, solicitud_id)
    salida: dict[str, Any] = (resultado.salida or {}) if resultado else {}
    abstencion = bool(resultado and resultado.abstencion)
    detalle = {
        r.identificador_visible: (f, d)
        for r, f, d in await unidad.fragmentos_recuperados.detalle(contexto, solicitud_id)
    }

    def citas(identificadores: list[str]) -> list[CitaGuia]:
        return [
            CitaGuia(
                identificador=i,
                texto=detalle[i][0].texto,
                guia=detalle[i][1].titulo,
                apartado=detalle[i][0].seccion_original,
            )
            for i in identificadores
            if i in detalle
        ]

    return VistaEstructura(
        id=solicitud.id,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        creada_en=solicitud.creada_en,
        entregada_en=solicitud.entregada_en,
        seccion_id=solicitud.alcance_ref,
        seccion_titulo=titulo,
        abstencion=abstencion,
        aviso=AVISO_SIN_EVIDENCIA if abstencion else None,
        etiqueta=resultado.etiqueta if resultado else None,
        hallazgos=[
            HallazgoVista(
                indicador=h["indicador"],
                indicador_nombre=INDICADORES.get(h["indicador"], h["indicador"]),
                ubicacion=h["ubicacion"],
                descripcion=h["descripcion"],
                severidad=h["severidad"],
                recomendacion=h["recomendacion"],
                citas=citas(h.get("citas", [])),
            )
            for h in salida.get("hallazgos", [])
            if isinstance(h, dict)
        ],
        fortalezas=[str(f) for f in salida.get("fortalezas", [])],
        notas_para_el_estudiante=[str(n) for n in salida.get("notas_para_el_estudiante", [])],
        advertencias=[str(a) for a in (resultado.advertencias if resultado else [])],
        comprobaciones=[ComprobacionVista(**c) for c in salida.get("comprobaciones", [])],
    )
