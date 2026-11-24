"""Rutas del caso para la búsqueda de evidencia (T19; RF-08, CU-07, RF-21 en parte).

* ``POST /caso/evidencias``: valida la consulta (T19-01, apartado 3). Si la rechaza no la
  encola y responde 422 con qué se puede pedir; si no, responde 202 y la atiende en
  segundo plano.
* ``GET /caso/evidencias/{id}``: avance y resultado, con cada cita desplegable (fragmento,
  documento, sección, páginas y enlace de acceso abierto).

Una solicitud de otro caso responde 404, igual que una inexistente (4.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.agentes.evidencia import INVITACION_APORTE, AgenteEvidencia, AtencionEvidencia
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, TipoSolicitud
from app.bibliografia.fabrica import crear_servicios
from app.bibliografia.referencias import ConstructorReferencias
from app.comun.errores import ErrorAplicacion
from app.configuracion import Ajustes
from app.corpus.fabrica import CorpusNoConfigurado
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.llm.fabrica import crear_cadena, registrador_en_base
from app.rag.modelos import AVISO_SIN_EVIDENCIA
from app.rag.recuperacion import Recuperador
from app.rag.servicio import ServicioEvidencia
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.dependencias import ContextoCaso, Reloj, RelojDep, Unidad, obtener_reloj
from app.verificacion.comprobaciones import ACCESO_ABIERTO_COMPROBADO

router = APIRouter(prefix="/caso", tags=["evidencia"])


class SolicitudInexistente(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__("no_existe", "El recurso solicitado no existe.", estado_http=404)


class PedidoEvidencia(BaseModel):
    consulta: str = Field(min_length=1, max_length=5000)


class SolicitudEvidencia(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    creada_en: datetime


class CitaVista(BaseModel):
    identificador: str
    texto: str
    titulo: str | None
    seccion: str
    pagina_inicio: int | None
    pagina_fin: int | None
    acceso_abierto: bool
    url_acceso_abierto: str | None  # solo si el acceso abierto está comprobado
    incompleto: bool


class AfirmacionVista(BaseModel):
    afirmacion: str
    citas: list[CitaVista]


class FuenteVista(BaseModel):
    documento_id: uuid.UUID
    referencia: str
    metodo: str
    url_acceso_abierto: str | None
    identificadores: list[str]


class ComprobacionVista(BaseModel):
    numero: int
    nombre: str
    superada: bool
    motivos: list[str]


class VistaEvidencia(BaseModel):
    id: uuid.UUID
    consulta: str
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    entregada_en: datetime | None
    abstencion: bool
    aviso: str | None
    invitacion_aporte: str | None
    etiqueta: Etiqueta | None
    respuesta: list[AfirmacionVista]
    evidencia_divergente: list[AfirmacionVista]
    notas_para_el_estudiante: list[str]
    fuentes: list[FuenteVista]
    advertencias: list[str]
    comprobaciones: list[ComprobacionVista]


async def obtener_atencion(peticion: Request, unidad: Unidad) -> AtencionEvidencia:
    """Una por proceso; usa el servicio de modelos, el adaptador y doi.org."""
    estado = peticion.app.state
    actual: AtencionEvidencia | None = getattr(estado, "atencion_evidencia", None)
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
    actual = AtencionEvidencia(
        AgenteEvidencia(evidencia, cadena),
        modelos,
        ConstructorReferencias(crear_servicios(ajustes, abrir).doi),
        abrir,
        reloj,
    )
    estado.atencion_evidencia = actual
    return actual


AtencionDep = Annotated[AtencionEvidencia, Depends(obtener_atencion)]


@router.post(
    "/evidencias",
    response_model=SolicitudEvidencia,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {}, 503: {}},
    summary="Pedir evidencia para una consulta o una afirmación",
    description="202 si la consulta se encola; 422 con el motivo y qué se puede pedir si"
    " la validación la rechaza (no se encola ni consume el modelo).",
)
async def pedir_evidencia(
    pedido: PedidoEvidencia,
    contexto: ContextoCaso,
    unidad: Unidad,
    atencion: AtencionDep,
) -> SolicitudEvidencia:
    solicitud = await atencion.iniciar(unidad, contexto, pedido.consulta)
    atencion.lanzar(solicitud, contexto)
    return SolicitudEvidencia(
        id=solicitud.id, estado=solicitud.estado, creada_en=solicitud.creada_en
    )


@router.get(
    "/evidencias/{solicitud_id}",
    response_model=VistaEvidencia,
    summary="Avance y resultado de una búsqueda de evidencia",
)
async def ver_evidencia(
    solicitud_id: uuid.UUID,
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    reloj: RelojDep,
) -> VistaEvidencia:
    solicitud = await unidad.solicitudes.obtener(contexto, solicitud_id)
    if solicitud is None or solicitud.tipo is not TipoSolicitud.BUSQUEDA_EVIDENCIA:
        raise SolicitudInexistente()
    atencion: AtencionEvidencia | None = getattr(peticion.app.state, "atencion_evidencia", None)
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
    resultado = await unidad.resultados.de_solicitud(contexto, solicitud_id)
    detalle = {
        r.identificador_visible: (f, d)
        for r, f, d in await unidad.fragmentos_recuperados.detalle(contexto, solicitud_id)
    }
    salida: dict[str, Any] = (resultado.salida or {}) if resultado else {}
    abstencion = bool(resultado and resultado.abstencion)

    def citas(identificadores: list[str]) -> list[CitaVista]:
        vistas = []
        for identificador in identificadores:
            if identificador not in detalle:
                continue
            fragmento, documento = detalle[identificador]
            abierto = documento.estado_oa.value in ACCESO_ABIERTO_COMPROBADO
            vistas.append(
                CitaVista(
                    identificador=identificador,
                    texto=fragmento.texto,
                    titulo=documento.titulo,
                    seccion=fragmento.seccion_normalizada.value,
                    pagina_inicio=fragmento.pagina_inicio,
                    pagina_fin=fragmento.pagina_fin,
                    acceso_abierto=abierto,
                    url_acceso_abierto=documento.url_acceso_abierto if abierto else None,
                    incompleto=documento.estado.value == "incompleto",
                )
            )
        return vistas

    def afirmaciones(clave: str) -> list[AfirmacionVista]:
        return [
            AfirmacionVista(afirmacion=a["afirmacion"], citas=citas(a.get("citas", [])))
            for a in salida.get(clave, [])
            if isinstance(a, dict) and "afirmacion" in a
        ]

    return VistaEvidencia(
        id=solicitud.id,
        consulta=solicitud.alcance_ref or "",
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        creada_en=solicitud.creada_en,
        entregada_en=solicitud.entregada_en,
        abstencion=abstencion,
        aviso=AVISO_SIN_EVIDENCIA if abstencion else None,
        invitacion_aporte=INVITACION_APORTE if abstencion else None,
        etiqueta=resultado.etiqueta if resultado else None,
        respuesta=afirmaciones("respuesta"),
        evidencia_divergente=afirmaciones("evidencia_divergente"),
        notas_para_el_estudiante=[str(n) for n in salida.get("notas_para_el_estudiante", [])],
        fuentes=[
            FuenteVista(
                documento_id=uuid.UUID(r["documento_id"]),
                referencia=r["texto"],
                metodo=r["metodo"],
                url_acceso_abierto=r.get("url_acceso_abierto"),
                identificadores=r.get("identificadores", []),
            )
            for r in salida.get("referencias", [])
        ],
        advertencias=[str(a) for a in (resultado.advertencias if resultado else [])],
        comprobaciones=[ComprobacionVista(**c) for c in salida.get("comprobaciones", [])],
    )
