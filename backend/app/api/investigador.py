"""Rutas del investigador (A2): colecciones científicas, casos, cuentas y norma (RF-16)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.bd.enumeraciones import EstadoCaso, TipoAutoria, TipoColeccion
from app.bd.modelos import Caso, Coleccion
from app.casos import servicio
from app.seguridad.dependencias import ContextoInvestigador, RelojDep, Unidad

router = APIRouter(prefix="/investigador", tags=["investigador"])


class SolicitudColeccion(BaseModel):
    tema: str = Field(min_length=2, max_length=80, examples=["TEMA-01"])


class ColeccionVista(BaseModel):
    id: uuid.UUID
    tipo: TipoColeccion
    tema: str | None
    n_incluidas: int
    n_excluidas: int
    n_pendientes: int

    @classmethod
    def desde(cls, coleccion: Coleccion) -> ColeccionVista:
        return cls(
            id=coleccion.id,
            tipo=coleccion.tipo,
            tema=coleccion.tema,
            n_incluidas=coleccion.n_incluidas,
            n_excluidas=coleccion.n_excluidas,
            n_pendientes=coleccion.n_pendientes,
        )


class SolicitudCaso(BaseModel):
    codigo: str = Field(min_length=2, max_length=30, examples=["CASO-01"])
    tipo_autoria: TipoAutoria
    tema: str = Field(min_length=2, max_length=80)


class CredencialVista(BaseModel):
    cuenta: str
    contrasena_inicial: str = Field(description="Se muestra una sola vez; no se almacena en claro.")


class CasoVista(BaseModel):
    codigo: str
    tipo_autoria: TipoAutoria
    tema: str
    norma_citacion: str
    estado: EstadoCaso

    @classmethod
    def desde(cls, caso: Caso, tema: str) -> CasoVista:
        return cls(
            codigo=caso.codigo,
            tipo_autoria=caso.tipo_autoria,
            tema=tema,
            norma_citacion=caso.norma_citacion,
            estado=caso.estado,
        )


class CasoCreadoVista(CasoVista):
    credenciales: list[CredencialVista]


class CambioNormaVista(BaseModel):
    norma_anterior: str
    norma_nueva: str
    cambiado_en: datetime


class CasoDetalleVista(CasoVista):
    cuentas: list[str]
    cambios_norma: list[CambioNormaVista]


class SolicitudNorma(BaseModel):
    norma: str = Field(min_length=1, max_length=20, examples=["apa7"])


@router.get("/colecciones", response_model=list[ColeccionVista], summary="Colecciones compartidas")
async def listar_colecciones(
    contexto: ContextoInvestigador, unidad: Unidad
) -> list[ColeccionVista]:
    return [ColeccionVista.desde(c) for c in await unidad.colecciones_investigador.listar(contexto)]


@router.post(
    "/colecciones/cientificas",
    response_model=ColeccionVista,
    status_code=status.HTTP_201_CREATED,
    summary="Crear la colección científica de un tema",
)
async def crear_coleccion(
    datos: SolicitudColeccion, contexto: ContextoInvestigador, unidad: Unidad
) -> ColeccionVista:
    return ColeccionVista.desde(
        await servicio.crear_coleccion_cientifica(unidad, contexto, datos.tema)
    )


@router.get("/casos", response_model=list[CasoVista], summary="Listar casos")
async def listar_casos(contexto: ContextoInvestigador, unidad: Unidad) -> list[CasoVista]:
    return [
        CasoVista.desde(caso, coleccion.tema or "")
        for caso, coleccion in await unidad.casos_investigador.listar(contexto)
    ]


@router.post(
    "/casos",
    response_model=CasoCreadoVista,
    status_code=status.HTTP_201_CREATED,
    summary="Dar de alta un caso con su colección personal y sus cuentas",
)
async def crear_caso(
    datos: SolicitudCaso, contexto: ContextoInvestigador, unidad: Unidad
) -> CasoCreadoVista:
    creado = await servicio.crear_caso(
        unidad, contexto, datos.codigo, datos.tipo_autoria, datos.tema
    )
    base = CasoVista.desde(creado.caso, creado.tema)
    return CasoCreadoVista(
        **base.model_dump(),
        credenciales=[
            CredencialVista(cuenta=c.codigo, contrasena_inicial=c.contrasena_inicial)
            for c in creado.credenciales
        ],
    )


@router.get("/casos/{codigo}", response_model=CasoDetalleVista, summary="Detalle de un caso")
async def detalle_caso(
    codigo: str, contexto: ContextoInvestigador, unidad: Unidad
) -> CasoDetalleVista:
    caso, coleccion, cuentas, cambios = await servicio.detalle_caso(unidad, contexto, codigo)
    base = CasoVista.desde(caso, coleccion.tema or "")
    return CasoDetalleVista(
        **base.model_dump(),
        cuentas=[c.codigo for c in cuentas],
        cambios_norma=[
            CambioNormaVista(
                norma_anterior=c.norma_anterior,
                norma_nueva=c.norma_nueva,
                cambiado_en=c.cambiado_en,
            )
            for c in cambios
        ],
    )


async def _vista(unidad: Unidad, contexto: ContextoInvestigador, caso: Caso) -> CasoVista:
    coleccion = await unidad.casos_investigador.coleccion_de(contexto, caso.coleccion_cientifica_id)
    return CasoVista.desde(caso, coleccion.tema or "")


@router.post("/casos/{codigo}/desactivar", response_model=CasoVista, summary="Desactivar un caso")
async def desactivar(
    codigo: str, contexto: ContextoInvestigador, unidad: Unidad, reloj: RelojDep
) -> CasoVista:
    caso = await servicio.cambiar_estado(unidad, contexto, codigo, EstadoCaso.DESACTIVADO, reloj())
    return await _vista(unidad, contexto, caso)


@router.post("/casos/{codigo}/reactivar", response_model=CasoVista, summary="Reactivar un caso")
async def reactivar(
    codigo: str, contexto: ContextoInvestigador, unidad: Unidad, reloj: RelojDep
) -> CasoVista:
    caso = await servicio.cambiar_estado(unidad, contexto, codigo, EstadoCaso.HABILITADO, reloj())
    return await _vista(unidad, contexto, caso)


@router.put(
    "/casos/{codigo}/norma", response_model=CasoVista, summary="Elegir la norma de citación"
)
async def cambiar_norma(
    codigo: str,
    datos: SolicitudNorma,
    contexto: ContextoInvestigador,
    unidad: Unidad,
    reloj: RelojDep,
) -> CasoVista:
    caso = await servicio.cambiar_norma(unidad, contexto, codigo, datos.norma, reloj())
    return await _vista(unidad, contexto, caso)
