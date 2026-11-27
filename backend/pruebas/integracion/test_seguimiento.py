"""Estado en tiempo real, reenvío y mismo alcance con la base real (T29; RF-22, F-06, F-16)."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import httpx
import pytest

from app.agentes.ejecucion import Ejecucion
from app.agentes.metodologia import AtencionMetodologia
from app.agentes.seccion import AtencionSeccion
from app.bd.enumeraciones import Etiqueta, Rol, TipoSolicitud
from app.bd.modelos import Solicitud
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import Comprobacion
from pruebas.integracion.conftest import Entorno, consultar, esperar_orquestador
from pruebas.integracion.test_estructura import _caso
from pruebas.integracion.test_orquestacion import ALCANCES, EjecutorDoble

pytestmark = pytest.mark.integracion

ORDEN = ["recibida", "asignada", "recuperando", "generando", "verificando", "entregada"]


@dataclass
class EjecutorLento(EjecutorDoble):
    """Se detiene en cada paso para que el canal alcance a ver cada estado."""

    pausa: float = 0.3

    async def ejecutar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> Ejecucion:
        await asyncio.sleep(self.pausa)
        return await super().ejecutar(unidad, contexto, solicitud)

    async def registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
        comprobaciones: Sequence[Comprobacion],
        etiqueta: Etiqueta | None,
    ) -> None:
        await asyncio.sleep(self.pausa)
        await super().registrar(unidad, contexto, solicitud, ejecucion, comprobaciones, etiqueta)


@dataclass
class Seguimiento:
    entorno: Entorno
    cliente: httpx.AsyncClient
    caso_id: uuid.UUID
    version_id: uuid.UUID
    configuracion_id: uuid.UUID
    contexto: ContextoAcceso

    def crear(
        self, tipo: TipoSolicitud, estado: str = "recibida", ref: str | None = None
    ) -> uuid.UUID:
        alcance_tipo, alcance_ref = ALCANCES[tipo]
        ((solicitud_id,),) = consultar(
            self.entorno.url_bd,
            "INSERT INTO solicitud (caso_id, version_id, tipo, alcance_tipo, alcance_ref,"
            " configuracion_id, estado, creada_en, actualizada_en)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            self.caso_id,
            self.version_id,
            tipo.value,
            alcance_tipo,
            ref if ref is not None else alcance_ref,
            self.configuracion_id,
            estado,
            self.entorno.reloj(),
            self.entorno.reloj(),
        )
        assert isinstance(solicitud_id, uuid.UUID)
        return solicitud_id

    async def eventos(self, solicitud_id: uuid.UUID) -> list[dict[str, Any]]:
        respuesta = await self.cliente.get(f"/caso/solicitudes/{solicitud_id}/eventos")
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.headers["content-type"].startswith("text/event-stream")
        return [
            json.loads(linea.removeprefix("data: "))
            for linea in respuesta.text.splitlines()
            if linea.startswith("data: ")
        ]


@pytest.fixture
async def seguimiento(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> AsyncIterator[Seguimiento]:
    entorno.aplicacion.state.intervalo_eventos_s = 0.02
    cliente = await _caso(entorno, investigador, "CASO-A")
    ((caso_id, version_id),) = consultar(
        entorno.url_bd, "SELECT caso_id, id FROM version_borrador LIMIT 1"
    )
    ((configuracion_id,),) = consultar(entorno.url_bd, "SELECT id FROM configuracion WHERE vigente")
    ((cuenta_id,),) = consultar(
        entorno.url_bd, "SELECT id FROM cuenta WHERE caso_id = %s LIMIT 1", caso_id
    )
    assert isinstance(caso_id, uuid.UUID) and isinstance(cuenta_id, uuid.UUID)
    assert isinstance(version_id, uuid.UUID) and isinstance(configuracion_id, uuid.UUID)
    yield Seguimiento(
        entorno,
        cliente,
        caso_id,
        version_id,
        configuracion_id,
        ContextoAcceso(cuenta_id, Rol.CASO, caso_id),
    )
    await cliente.aclose()


async def test_el_canal_transmite_la_secuencia_de_estados_hasta_el_final(
    seguimiento: Seguimiento,
) -> None:
    doble = EjecutorLento(TipoSolicitud.PLAN_TAREA)
    seguimiento.entorno.aplicacion.state.atencion_plan = doble
    solicitud_id = seguimiento.crear(TipoSolicitud.PLAN_TAREA)
    from app.orquestacion.en_api import orquestador_en_proceso

    class _Peticion:  # el orquestador solo usa el reloj de la petición
        app = seguimiento.entorno.aplicacion

    orquestador = orquestador_en_proceso(seguimiento.entorno.aplicacion, _Peticion())  # type: ignore[arg-type]
    canal = asyncio.create_task(seguimiento.eventos(solicitud_id))
    await asyncio.sleep(0.1)  # el estudiante se suscribe antes de que el trabajador la tome
    final = await orquestador.atender(solicitud_id, seguimiento.contexto)
    eventos = await canal
    estados = [e["estado"] for e in eventos]
    assert final == "entregada"
    assert estados[0] == "recibida" and estados[-1] == "entregada"
    assert {"asignada", "verificando"} <= set(estados)
    assert estados == sorted(estados, key=ORDEN.index)  # siempre hacia adelante
    # Solo se transmite lo que cambia (el estado, o el motivo dentro de un mismo estado).
    assert all(anterior != actual for anterior, actual in pairwise(eventos))


async def test_al_reconectarse_recibe_el_estado_actual_y_el_canal_termina(
    seguimiento: Seguimiento,
) -> None:
    entregada = seguimiento.crear(TipoSolicitud.PLAN_TAREA, estado="entregada")
    assert await seguimiento.eventos(entregada) == [
        {"estado": "entregada", "motivo": None, "intentos_tecnicos": 0}
    ]


async def test_un_caso_no_puede_suscribirse_a_los_eventos_de_otro(
    seguimiento: Seguimiento, investigador: httpx.AsyncClient
) -> None:
    propia = seguimiento.crear(TipoSolicitud.PLAN_TAREA, estado="entregada")
    otro = await _caso(seguimiento.entorno, investigador, "CASO-B")
    respuesta = await otro.get(f"/caso/solicitudes/{propia}/eventos")
    assert respuesta.status_code == 404
    assert "text/event-stream" not in respuesta.headers.get("content-type", "")
    assert (await otro.post(f"/caso/solicitudes/{propia}/reenvio")).status_code == 404
    await otro.aclose()


async def test_el_reenvio_de_una_no_atendida_queda_enlazado_y_se_atiende(
    seguimiento: Seguimiento,
) -> None:
    doble = EjecutorDoble(TipoSolicitud.BUSQUEDA_EVIDENCIA)
    seguimiento.entorno.aplicacion.state.atencion_evidencia = doble
    original = seguimiento.crear(TipoSolicitud.BUSQUEDA_EVIDENCIA, estado="no_atendida")
    respuesta = await seguimiento.cliente.post(f"/caso/solicitudes/{original}/reenvio")
    assert respuesta.status_code == 202, respuesta.text
    nueva = respuesta.json()
    assert nueva["solicitud_origen_id"] == str(original) and nueva["id"] != str(original)
    assert nueva["tipo"] == "busqueda_evidencia"
    await esperar_orquestador(seguimiento.entorno)
    assert doble.atendidas == [uuid.UUID(nueva["id"])]
    ((alcance, estado),) = consultar(
        seguimiento.entorno.url_bd,
        "SELECT alcance_ref, estado FROM solicitud WHERE id = %s",
        uuid.UUID(nueva["id"]),
    )
    assert alcance == ALCANCES[TipoSolicitud.BUSQUEDA_EVIDENCIA][1] and estado == "entregada"
    lista = (await seguimiento.cliente.get("/caso/solicitudes")).json()
    assert {s["id"]: s["solicitud_origen_id"] for s in lista}[nueva["id"]] == str(original)
    # Solo una no atendida se reenvía.
    entregada = await seguimiento.cliente.post(f"/caso/solicitudes/{nueva['id']}/reenvio")
    assert entregada.status_code == 409 and entregada.json()["codigo"] == "no_reenviable"


async def test_otra_solicitud_con_el_mismo_alcance_valida_el_tipo(
    seguimiento: Seguimiento,
) -> None:
    estado = seguimiento.entorno.aplicacion.state
    estado.ajustes = estado.ajustes.model_copy(update={"ejecucion_en_proceso": False})
    # ``iniciar`` no usa el agente: bastan ejecutores reales sin modelo.
    estado.atencion_estructura = AtencionSeccion(
        TipoSolicitud.REVISION_ESTRUCTURA,
        None,
        seguimiento.entorno.reloj,  # type: ignore[arg-type]
    )
    estado.atencion_metodologia = AtencionMetodologia(
        TipoSolicitud.REVISION_METODOLOGICA,
        None,
        seguimiento.entorno.reloj,  # type: ignore[arg-type]
    )
    secciones = (await seguimiento.cliente.get("/caso/estructura/secciones")).json()
    metodo = next(s["id"] for s in secciones if "Método" in s["titulo"])
    original = seguimiento.crear(TipoSolicitud.REVISION_ESTRUCTURA, "entregada", ref=metodo)
    ruta = f"/caso/solicitudes/{original}/mismo-alcance"
    respuesta = await seguimiento.cliente.post(ruta, json={"tipo": "revision_metodologica"})
    assert respuesta.status_code == 202, respuesta.text
    nueva = respuesta.json()
    assert nueva["tipo"] == "revision_metodologica" and nueva["estado"] == "recibida"
    ((alcance,),) = consultar(
        seguimiento.entorno.url_bd,
        "SELECT alcance_ref FROM solicitud WHERE id = %s",
        uuid.UUID(nueva["id"]),
    )
    assert alcance == metodo
    for tipo in ("revision_estructura", "propuesta_redaccion", "verificacion_referencias"):
        rechazo = await seguimiento.cliente.post(ruta, json={"tipo": tipo})
        assert rechazo.status_code == 422, tipo
        assert rechazo.json()["codigo"] == "mismo_alcance_no_admitido"
