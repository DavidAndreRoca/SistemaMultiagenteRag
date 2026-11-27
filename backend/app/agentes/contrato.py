"""Contrato común de los agentes (Fase 1, 6.1; T18-01, apartados 1 y 2).

* ``EstadoAgente``: lo único que recibe un agente. No incluye el historial del caso: cada
  solicitud se resuelve con su estado y la evidencia recuperada (sin memoria, n.° 8).
* ``Agente``: recupera y decide la suficiencia (T16); si no alcanza, se abstiene sin
  llamar al modelo (RN-04); si alcanza, genera con el adaptador (T17) y el esquema de su
  tipo, con el alcance y los fragmentos ``F1`` a ``Fn`` como datos (RN-23).

Cada agente concreto (D1 a D4, desde T19) fija sus tipos, su instrucción y cómo arma la
consulta y presenta el alcance. Las comprobaciones viven en ``app/verificacion/``.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agentes.esquemas import ESQUEMAS
from app.bd.enumeraciones import TipoSolicitud
from app.instrucciones.cargador import DIRECTORIO, vigente
from app.llm.interfaces import ModeloLenguaje
from app.llm.modelos import BloqueDatos, EntradaModelo
from app.rag.servicio import Evidencia, ServicioEvidencia
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo

MAX_MOTIVOS = 10


class EstadoAgente(BaseModel):
    """Estado del grafo que recibe todo agente (6.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    solicitud_id: uuid.UUID
    caso_id: uuid.UUID
    tipo: TipoSolicitud
    alcance: str = Field(min_length=1, max_length=20_000)
    hito: str | None = None
    tema_id: uuid.UUID | None = None
    version_id: uuid.UUID
    intento: int = Field(1, ge=1, le=2)
    motivos_falla: list[str] = Field(default_factory=list, max_length=MAX_MOTIVOS)

    @model_validator(mode="after")
    def _motivos_solo_en_el_reintento(self) -> EstadoAgente:
        if self.intento == 1 and self.motivos_falla:
            raise ValueError("los motivos de falla solo llegan en el intento 2")
        return self


class ResultadoAgente(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    estado: EstadoAgente
    abstencion: bool
    salida: BaseModel | None  # validada con el esquema del tipo; None si hubo abstención
    evidencia: Evidencia
    instruccion: str | None = None
    proveedor: str | None = None
    modelo: str | None = None


class TipoNoAtendido(ValueError):
    pass


class Agente(ABC):
    tipos: ClassVar[frozenset[TipoSolicitud]]
    instruccion: ClassVar[str]  # nombre del agente en ``backend/instrucciones/``

    def __init__(
        self,
        evidencia: ServicioEvidencia,
        modelo: ModeloLenguaje,
        versiones: Callable[[], dict[str, str]] | None = None,
        directorio_instrucciones: Path = DIRECTORIO,
    ) -> None:
        """``versiones`` da la versión de cada instrucción; por defecto, la configuración
        vigente de la unidad de trabajo (RNF-21)."""
        self._evidencia = evidencia
        self._modelo = modelo
        self._versiones = versiones
        self._directorio = directorio_instrucciones

    @abstractmethod
    def consulta(self, estado: EstadoAgente) -> str:
        """Texto con el que se recupera la evidencia, a partir del alcance."""

    @abstractmethod
    def tarea(self, estado: EstadoAgente) -> str:
        """Qué se le pide al modelo para este tipo."""

    async def falta_insumo(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, estado: EstadoAgente
    ) -> str | None:
        """Motivo para abstenerse sin recuperar ni generar, si falta un insumo que el agente
        exige (por ejemplo, las instrucciones del hito del plan de tarea, T24)."""
        return None

    async def consulta_con_herramientas(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, estado: EstadoAgente
    ) -> str:
        """La consulta de recuperación cuando el agente usa una herramienta que lee la base
        (por ejemplo, la lista de comprobación de D2, T26). Por defecto, ``consulta``."""
        return self.consulta(estado)

    def datos(self, estado: EstadoAgente, evidencia: Evidencia) -> list[BloqueDatos]:
        """El alcance y los fragmentos del contexto cerrado, como datos (RN-23)."""
        return [BloqueDatos(etiqueta="alcance", contenido=estado.alcance[:20_000])] + [
            BloqueDatos(etiqueta=f.identificador, contenido=f.texto)
            for f in evidencia.recuperacion.fragmentos
        ]

    async def atender(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        estado: EstadoAgente,
        al_generar: Callable[[], Awaitable[None]] | None = None,
    ) -> ResultadoAgente:
        """``al_generar`` se llama con la evidencia suficiente, justo antes de generar: el
        orquestador marca la solicitud "generando" (T29, estado visible)."""
        if estado.tipo not in self.tipos:
            raise TipoNoAtendido(f"{type(self).__name__} no atiende {estado.tipo.value}")
        if contexto.caso_id != estado.caso_id:
            raise TipoNoAtendido("el estado no corresponde al caso del contexto")
        motivo = await self.falta_insumo(unidad, contexto, estado)
        if motivo is not None:
            evidencia = await self._evidencia.abstener(
                unidad, contexto, estado.solicitud_id, motivo
            )
            return ResultadoAgente(estado=estado, abstencion=True, salida=None, evidencia=evidencia)
        evidencia = await self._evidencia.preparar(
            unidad,
            contexto,
            estado.solicitud_id,
            await self.consulta_con_herramientas(unidad, contexto, estado),
        )
        if not evidencia.suficiente:
            return ResultadoAgente(estado=estado, abstencion=True, salida=None, evidencia=evidencia)
        if al_generar is not None:
            await al_generar()
        if self._versiones is not None:
            versiones = self._versiones()
        else:
            _, parametros = await unidad.configuracion.vigente()
            versiones = parametros.versiones_instrucciones
        instruccion = vigente(self.instruccion, versiones, self._directorio)
        tarea = self.tarea(estado)
        if estado.intento == 2 and estado.motivos_falla:
            tarea += " Corrige estos problemas de la propuesta anterior: " + "; ".join(
                estado.motivos_falla
            )
        resultado = await self._modelo.generar(
            instruccion,
            EntradaModelo(tarea=tarea[:4000], datos=self.datos(estado, evidencia)),
            ESQUEMAS[estado.tipo],
        )
        return ResultadoAgente(
            estado=estado,
            abstencion=False,
            salida=resultado.datos,
            evidencia=evidencia,
            instruccion=resultado.instruccion,
            proveedor=resultado.proveedor.value,
            modelo=resultado.modelo,
        )
