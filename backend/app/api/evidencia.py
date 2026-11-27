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

from app.agentes.evidencia import INVITACION_APORTE, AtencionEvidencia
from app.bd.enumeraciones import EstadoSolicitud, Etiqueta, OrigenDocumento, TipoSolicitud
from app.bd.modelos import FuenteAportada
from app.comun.errores import ErrorAplicacion
from app.orquestacion.en_api import ejecutor_de, encolar
from app.rag.modelos import AVISO_SIN_EVIDENCIA
from app.seguridad.dependencias import ContextoCaso, RelojDep, Unidad
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


class AporteCitado(BaseModel):
    """Lo que el caso declaró al aportar la fuente (RF-21: fuente de su colección personal)."""

    titulo: str
    autores: list[str]
    anio: int | None
    doi: str | None
    aportada_en: datetime


class CitaVista(BaseModel):
    identificador: str
    texto: str
    titulo: str | None
    autores: str | None  # del documento, abreviados (T33)
    anio: int | None
    doi: str | None
    seccion: str
    pagina_inicio: int | None
    pagina_fin: int | None
    acceso_abierto: bool
    url_acceso_abierto: str | None  # solo si el acceso abierto está comprobado
    incompleto: bool
    aporte: AporteCitado | None = None  # solo si es una fuente que aportó el caso (T32)


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
    """El ejecutor del tipo, uno por proceso (``app/orquestacion/en_api.py``)."""
    ejecutor: AtencionEvidencia = await ejecutor_de(
        peticion, unidad, TipoSolicitud.BUSQUEDA_EVIDENCIA
    )
    return ejecutor


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
    peticion: Request,
    contexto: ContextoCaso,
    unidad: Unidad,
    atencion: AtencionDep,
) -> SolicitudEvidencia:
    solicitud = await atencion.iniciar(unidad, contexto, pedido.consulta)
    encolar(peticion, solicitud, contexto)
    return SolicitudEvidencia(
        id=solicitud.id, estado=solicitud.estado, creada_en=solicitud.creada_en
    )


def autores_abreviados(autores: list[Any] | None, maximo: int = 3) -> str | None:
    """Apellidos de los primeros autores del documento, con "et al." si hay más."""
    nombres = []
    for autor in autores or []:
        if isinstance(autor, dict):
            nombre = autor.get("apellidos") or autor.get("nombre_completo") or autor.get("nombres")
            if isinstance(nombre, str) and nombre.strip():
                nombres.append(nombre.strip())
    if not nombres:
        return None
    texto = ", ".join(nombres[:maximo])
    return f"{texto} et al." if len(nombres) > maximo else texto


def _aporte_citado(aporte: FuenteAportada) -> AporteCitado:
    datos = aporte.datos_bibliograficos or {}
    autores = datos.get("autores")
    anio = datos.get("anio")
    return AporteCitado(
        titulo=str(datos.get("titulo", "")),
        autores=[str(a) for a in autores] if isinstance(autores, list) else [],
        anio=anio if isinstance(anio, int) else None,
        doi=aporte.doi,
        aportada_en=aporte.aportada_en,
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
    resultado = await unidad.resultados.de_solicitud(contexto, solicitud_id)
    detalle = {
        r.identificador_visible: (f, d)
        for r, f, d in await unidad.fragmentos_recuperados.detalle(contexto, solicitud_id)
    }
    salida: dict[str, Any] = (resultado.salida or {}) if resultado else {}
    abstencion = bool(resultado and resultado.abstencion)
    aportes = await unidad.fuentes_aportadas.por_documentos(
        contexto,
        [d.id for _, d in detalle.values() if d.origen is OrigenDocumento.APORTE],
    )

    def citas(identificadores: list[str]) -> list[CitaVista]:
        vistas = []
        for identificador in identificadores:
            if identificador not in detalle:
                continue
            fragmento, documento = detalle[identificador]
            abierto = documento.estado_oa.value in ACCESO_ABIERTO_COMPROBADO
            aporte = aportes.get(documento.id)
            vistas.append(
                CitaVista(
                    identificador=identificador,
                    texto=fragmento.texto,
                    titulo=documento.titulo,
                    autores=autores_abreviados(documento.autores),
                    anio=documento.anio,
                    doi=documento.doi,
                    aporte=_aporte_citado(aporte) if aporte else None,
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
