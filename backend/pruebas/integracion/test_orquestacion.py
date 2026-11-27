"""Orquestación, cola y trabajador con la base real (T28; CP-03, CP-04, CP-07, RNF-07).

Los ejecutores son dobles que registran qué tipo atendieron; el camino de los agentes
reales por el grafo lo cubren las pruebas de cada pantalla (estructura, evidencia, etc.),
que ahora pasan por el mismo orquestador.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agentes.ejecucion import Ejecucion
from app.agentes.plan import AtencionPlan
from app.bd.enumeraciones import Etiqueta, Rol, TipoSolicitud
from app.bd.modelos import Solicitud
from app.llm.modelos import ErrorDisponibilidad, MotivoError
from app.orquestacion.grafo import MAX_INTENTOS_TECNICOS, Orquestador
from app.orquestacion.trabajador import Trabajador, url_checkpointer
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo, fabrica_de_unidades
from app.verificacion.comprobaciones import Comprobacion
from pruebas.integracion.conftest import Entorno, consultar
from pruebas.integracion.test_estructura import _caso

pytestmark = pytest.mark.integracion

ALCANCES = {
    TipoSolicitud.REVISION_ESTRUCTURA: ("seccion", "s1"),
    TipoSolicitud.PLAN_TAREA: ("hito", None),
    TipoSolicitud.REVISION_METODOLOGICA: ("seccion", "s2"),
    TipoSolicitud.PROPUESTA_REDACCION: ("fragmento", "p3"),
    TipoSolicitud.BUSQUEDA_EVIDENCIA: ("consulta", "¿La tutoría reduce la ansiedad?"),
    TipoSolicitud.VERIFICACION_REFERENCIAS: ("version", None),
}


@dataclass
class EjecutorDoble:
    tipo: TipoSolicitud
    atendidas: list[uuid.UUID] = field(default_factory=list)
    caidas: int = 0  # cuántas veces falla el proveedor antes de responder
    abstenerse: bool = False
    falla_esquema: bool = False

    async def ejecutar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, solicitud: Solicitud
    ) -> Ejecucion:
        if self.caidas:
            self.caidas -= 1
            raise ErrorDisponibilidad(MotivoError.SOBRECARGA)
        self.atendidas.append(solicitud.id)
        if self.abstenerse:
            return Ejecucion(abstencion=True)
        return Ejecucion(abstencion=False, salida={"texto": "salida ficticia del borrador"})

    def verificar(self, ejecucion: Ejecucion) -> list[Comprobacion]:
        return [Comprobacion(numero=1, nombre="esquema", superada=not self.falla_esquema)]

    async def registrar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        ejecucion: Ejecucion,
        comprobaciones: Sequence[Comprobacion],
        etiqueta: Etiqueta | None,
    ) -> None:
        solicitud.motivo = f"registrada:{etiqueta.value if etiqueta else 'sin_etiqueta'}"
        await unidad.confirmar()


@dataclass
class Escenario:
    entorno: Entorno
    caso_id: uuid.UUID
    version_id: uuid.UUID
    configuracion_id: uuid.UUID
    contexto: ContextoAcceso
    dobles: dict[TipoSolicitud, EjecutorDoble]

    def orquestador(self, checkpointer: Any = None) -> Orquestador:
        return Orquestador(
            lambda tipo: self.dobles[tipo],
            fabrica_de_unidades(self.entorno.aplicacion.state.fabrica_sesiones),
            self.entorno.reloj,
            checkpointer,
        )

    def crear(self, tipo: TipoSolicitud, estado: str = "recibida", **extra: object) -> uuid.UUID:
        alcance_tipo, alcance_ref = ALCANCES[tipo]
        columnas = "".join(f", {c}" for c in extra)
        valores = ", %s" * len(extra)
        ((solicitud_id,),) = consultar(
            self.entorno.url_bd,
            "INSERT INTO solicitud (caso_id, version_id, tipo, alcance_tipo, alcance_ref,"
            f" configuracion_id, estado, creada_en, actualizada_en{columnas})"
            f" VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s{valores})"
            " RETURNING id",
            self.caso_id,
            self.version_id,
            tipo.value,
            alcance_tipo,
            alcance_ref,
            self.configuracion_id,
            estado,
            self.entorno.reloj(),
            self.entorno.reloj(),
            *extra.values(),
        )
        assert isinstance(solicitud_id, uuid.UUID)
        return solicitud_id

    def estado(self, solicitud_id: uuid.UUID) -> tuple[object, ...]:
        ((fila),) = consultar(
            self.entorno.url_bd,
            "SELECT estado, motivo, intentos_tecnicos FROM solicitud WHERE id = %s",
            solicitud_id,
        )
        return tuple(fila)


@pytest.fixture
async def escenario(entorno: Entorno, investigador: httpx.AsyncClient) -> AsyncIterator[Escenario]:
    cliente = await _caso(entorno, investigador, "CASO-A")
    await cliente.aclose()
    ((caso_id, version_id),) = consultar(
        entorno.url_bd, "SELECT caso_id, id FROM version_borrador LIMIT 1"
    )
    ((configuracion_id,),) = consultar(entorno.url_bd, "SELECT id FROM configuracion WHERE vigente")
    ((cuenta_id,),) = consultar(
        entorno.url_bd, "SELECT id FROM cuenta WHERE caso_id = %s LIMIT 1", caso_id
    )
    assert isinstance(caso_id, uuid.UUID) and isinstance(cuenta_id, uuid.UUID)
    assert isinstance(version_id, uuid.UUID) and isinstance(configuracion_id, uuid.UUID)
    yield Escenario(
        entorno,
        caso_id,
        version_id,
        configuracion_id,
        ContextoAcceso(cuenta_id, Rol.CASO, caso_id),
        {tipo: EjecutorDoble(tipo) for tipo in TipoSolicitud},
    )


async def test_cp03_los_seis_tipos_llegan_a_su_agente_y_solo_a_uno(escenario: Escenario) -> None:
    orquestador = escenario.orquestador()
    for tipo in TipoSolicitud:
        solicitud_id = escenario.crear(tipo)
        assert await orquestador.atender(solicitud_id, escenario.contexto) == "entregada"
        assert escenario.dobles[tipo].atendidas == [solicitud_id]
        assert escenario.estado(solicitud_id) == ("entregada", "registrada:sin_etiqueta", 0)
    assert all(len(d.atendidas) == 1 for d in escenario.dobles.values())


async def test_una_comprobacion_fallida_etiqueta_con_advertencias_y_la_abstencion_no_verifica(
    escenario: Escenario,
) -> None:
    orquestador = escenario.orquestador()
    escenario.dobles[TipoSolicitud.REVISION_ESTRUCTURA].falla_esquema = True
    con_falla = escenario.crear(TipoSolicitud.REVISION_ESTRUCTURA)
    await orquestador.atender(con_falla, escenario.contexto)
    assert escenario.estado(con_falla)[:2] == ("entregada", "registrada:con_advertencias")
    escenario.dobles[TipoSolicitud.PLAN_TAREA].abstenerse = True
    abstenida = escenario.crear(TipoSolicitud.PLAN_TAREA)
    await orquestador.atender(abstenida, escenario.contexto)
    assert escenario.estado(abstenida)[:2] == ("entregada", None)  # sin registrar ni verificar


async def test_cp07_una_caida_del_proveedor_reencola_hasta_agotar_los_intentos(
    escenario: Escenario,
) -> None:
    orquestador = escenario.orquestador()
    doble = escenario.dobles[TipoSolicitud.BUSQUEDA_EVIDENCIA]
    doble.caidas = 1
    recuperable = escenario.crear(TipoSolicitud.BUSQUEDA_EVIDENCIA)
    assert await orquestador.atender(recuperable, escenario.contexto) == "recibida"
    assert escenario.estado(recuperable) == ("recibida", "modelo:sobrecarga", 1)
    assert await orquestador.atender(recuperable, escenario.contexto) == "entregada"
    assert doble.atendidas == [recuperable]

    doble.caidas = MAX_INTENTOS_TECNICOS + 1
    agotada = escenario.crear(TipoSolicitud.BUSQUEDA_EVIDENCIA)
    for _ in range(MAX_INTENTOS_TECNICOS):
        assert await orquestador.atender(agotada, escenario.contexto) == "recibida"
    assert await orquestador.atender(agotada, escenario.contexto) == "no_atendida"
    assert escenario.estado(agotada) == ("no_atendida", "modelo:sobrecarga", MAX_INTENTOS_TECNICOS)


async def test_una_solicitud_que_ya_no_esta_en_cola_no_se_ejecuta(escenario: Escenario) -> None:
    entregada = escenario.crear(TipoSolicitud.PLAN_TAREA, estado="entregada")
    assert await escenario.orquestador().atender(entregada, escenario.contexto) == "entregada"
    assert escenario.dobles[TipoSolicitud.PLAN_TAREA].atendidas == []
    otro_caso = ContextoAcceso(escenario.contexto.cuenta_id, Rol.CASO, uuid.uuid4())
    nueva = escenario.crear(TipoSolicitud.PLAN_TAREA)
    assert await escenario.orquestador().atender(nueva, otro_caso) is None  # aislamiento
    assert escenario.estado(nueva)[0] == "recibida"


def _trabajador(escenario: Escenario, orquestador: Orquestador, concurrencia: int) -> Trabajador:
    return Trabajador(
        fabrica_de_unidades(escenario.entorno.aplicacion.state.fabrica_sesiones),
        orquestador,
        concurrencia=concurrencia,
        espera_cola_s=0.01,
        espera_reintento_s=30,
        espera_huerfana_s=600,
        reloj=escenario.entorno.reloj,
    )


async def test_cp04_dos_trabajadores_nunca_toman_la_misma_solicitud(escenario: Escenario) -> None:
    creadas = {escenario.crear(TipoSolicitud.REVISION_ESTRUCTURA) for _ in range(12)}
    orquestador = escenario.orquestador()
    uno, dos = _trabajador(escenario, orquestador, 4), _trabajador(escenario, orquestador, 4)
    tomadas: list[uuid.UUID] = []

    async def tomar_todas(trabajador: Trabajador) -> None:
        while (siguiente := await trabajador.tomar()) is not None:
            tomadas.append(siguiente[0])
            assert siguiente[1].caso_id == escenario.caso_id

    await asyncio.gather(tomar_todas(uno), tomar_todas(dos))
    assert sorted(tomadas) == sorted(creadas)  # todas, y ninguna dos veces
    estados = consultar(escenario.entorno.url_bd, "SELECT DISTINCT estado FROM solicitud")
    assert estados == [("asignada",)]


async def test_el_trabajador_respeta_la_espera_tras_una_caida(escenario: Escenario) -> None:
    reencolada = escenario.crear(TipoSolicitud.PLAN_TAREA, intentos_tecnicos=1)
    trabajador = _trabajador(escenario, escenario.orquestador(), 1)
    assert await trabajador.tomar() is None  # actualizada recién: todavía no
    escenario.entorno.reloj.avanzar(seconds=31)
    tomada = await trabajador.tomar()
    assert tomada is not None and tomada[0] == reencolada


async def test_las_huerfanas_vuelven_a_la_cola_y_al_agotar_intentos_quedan_no_atendidas(
    escenario: Escenario,
) -> None:
    cortada = escenario.crear(TipoSolicitud.REVISION_ESTRUCTURA, estado="generando")
    agotada = escenario.crear(
        TipoSolicitud.REVISION_ESTRUCTURA, estado="verificando", intentos_tecnicos=3
    )
    reciente = escenario.crear(TipoSolicitud.REVISION_ESTRUCTURA, estado="recuperando")
    trabajador = _trabajador(escenario, escenario.orquestador(), 1)
    escenario.entorno.reloj.avanzar(minutes=11)
    consultar(
        escenario.entorno.url_bd,
        "UPDATE solicitud SET actualizada_en = %s WHERE id = %s RETURNING id",
        escenario.entorno.reloj(),
        reciente,
    )
    assert await trabajador.recuperar_huerfanas() == 2
    assert escenario.estado(cortada) == ("recibida", "interrumpida", 1)
    assert escenario.estado(agotada) == ("no_atendida", "interrumpida", 3)
    assert escenario.estado(reciente)[0] == "recuperando"  # sigue viva


async def test_el_trabajador_atiende_la_cola_y_guarda_el_estado_del_grafo_sin_texto(
    escenario: Escenario,
) -> None:
    ajustes = escenario.entorno.aplicacion.state.ajustes
    async with AsyncPostgresSaver.from_conn_string(url_checkpointer(ajustes)) as guardado:
        trabajador = _trabajador(escenario, escenario.orquestador(guardado), 3)
        creadas = [escenario.crear(tipo) for tipo in TipoSolicitud]
        while await trabajador.una_vuelta():
            await trabajador.esperar_en_curso()
        await trabajador.esperar_en_curso()
        estado = await guardado.aget_tuple({"configurable": {"thread_id": str(creadas[0])}})
    assert all(escenario.estado(s)[0] == "entregada" for s in creadas)
    assert estado is not None
    valores = estado.checkpoint["channel_values"]
    assert valores["agente"] == "D1" and valores["estado_final"] == "entregada"
    texto = consultar(
        escenario.entorno.url_bd,
        "SELECT count(*) FROM checkpoints c, checkpoint_writes w"
        " WHERE c::text ILIKE %s OR w::text ILIKE %s",
        "%salida ficticia%",
        "%salida ficticia%",
    )
    assert texto == [(0,)]
    ((eventos,),) = consultar(
        escenario.entorno.url_bd,
        "SELECT count(*) FROM evento_tecnico WHERE etapa = 'orquestacion'",
    )
    assert eventos == len(creadas)


async def test_la_api_crea_la_solicitud_y_la_deja_en_cola_para_el_trabajador(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> None:
    """Sin ``EJECUCION_EN_PROCESO``, la API valida y crea la solicitud, pero no la atiende:
    queda "recibida" para el trabajador."""
    estado_app = entorno.aplicacion.state
    estado_app.ajustes = estado_app.ajustes.model_copy(update={"ejecucion_en_proceso": False})
    # ``iniciar`` no usa el agente: basta un ejecutor real sin modelo.
    estado_app.atencion_plan = AtencionPlan(TipoSolicitud.PLAN_TAREA, None, entorno.reloj)  # type: ignore[arg-type]
    cliente = await _caso(entorno, investigador, "CASO-A")
    respuesta = await cliente.post("/caso/plan", json={"hito": "avance_1"})
    assert respuesta.status_code == 202, respuesta.text
    assert estado_app.orquestador is None
    ((estado,),) = consultar(
        entorno.url_bd,
        "SELECT estado FROM solicitud WHERE id = %s",
        uuid.UUID(respuesta.json()["id"]),
    )
    assert estado == "recibida"
    await cliente.aclose()
