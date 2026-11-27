"""Trabajador: proceso aparte que atiende la cola de solicitudes (T28; RNF-07).

``python -m app.orquestacion.trabajador`` (servicio ``trabajador`` de Compose):

* toma solicitudes "recibida" de la cola (``RepositorioCola.tomar``, con ``SKIP LOCKED``),
  hasta ``CONCURRENCIA_TRABAJADOR`` a la vez, y recorre el grafo para cada una con el
  contexto de la cuenta de su caso;
* cada minuto vuelve a la cola las solicitudes huérfanas: en curso y sin cambios durante
  ``ESPERA_HUERFANA_S`` (por ejemplo, porque el trabajador se reinició a mitad);
* guarda el estado del grafo en PostgreSQL con el checkpointer de LangGraph (tablas de la
  migración 0021);
* al recibir SIGTERM o SIGINT deja de tomar y espera las que tiene en curso.

Los parámetros funcionales (modelos y límites) se leen al arrancar: un cambio de la
configuración se aplica al reiniciar el trabajador.
"""

from __future__ import annotations

import asyncio
import signal
import uuid
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy.engine import make_url

from app.bd.enumeraciones import Rol
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.comun.registro import configurar_registro, obtener_registrador
from app.configuracion import Ajustes, cargar_ajustes
from app.orquestacion.fabrica import FabricaEjecutores
from app.orquestacion.grafo import MAX_INTENTOS_TECNICOS, Orquestador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import FabricaUnidades, fabrica_de_unidades

INTERVALO_HUERFANAS_S = 60
_registro = obtener_registrador("trabajador")


def _ahora() -> datetime:
    return datetime.now(UTC)


class Trabajador:
    def __init__(
        self,
        abrir: FabricaUnidades,
        orquestador: Orquestador,
        *,
        concurrencia: int,
        espera_cola_s: float,
        espera_reintento_s: float,
        espera_huerfana_s: float,
        reloj: Callable[[], datetime] = _ahora,
    ) -> None:
        self._abrir = abrir
        self._orquestador = orquestador
        self._concurrencia = concurrencia
        self._espera_cola = espera_cola_s
        self._espera_reintento = timedelta(seconds=espera_reintento_s)
        self._espera_huerfana = timedelta(seconds=espera_huerfana_s)
        self._reloj = reloj
        self._en_curso: set[asyncio.Task[str | None]] = set()

    async def recuperar_huerfanas(self) -> int:
        ahora = self._reloj()
        async with self._abrir() as unidad:
            cantidad = await unidad.cola.recuperar_huerfanas(
                ahora, ahora - self._espera_huerfana, MAX_INTENTOS_TECNICOS
            )
            await unidad.confirmar()
        if cantidad:
            _registro.warning(
                "solicitudes huérfanas recuperadas",
                extra={"tipo_evento": "orquestacion", "cantidad": cantidad},
            )
        return cantidad

    async def tomar(self) -> tuple[uuid.UUID, ContextoAcceso] | None:
        """La siguiente solicitud de la cola, ya asignada, con el contexto de su caso."""
        async with self._abrir() as unidad:
            tomada = await unidad.cola.tomar(self._reloj(), self._espera_reintento)
            if tomada is None:
                return None
            solicitud_id, caso_id = tomada
            cuenta = await unidad.cola.cuenta_del_caso(caso_id)
            await unidad.confirmar()
        if cuenta is None:  # sin cuenta no hay contexto: queda huérfana y se recupera
            _registro.error(
                "solicitud de un caso sin cuenta",
                extra={"tipo_evento": "orquestacion", "solicitud_id": str(solicitud_id)},
            )
            return None
        return solicitud_id, ContextoAcceso(cuenta, Rol.CASO, caso_id)

    async def una_vuelta(self) -> int:
        """Toma solicitudes hasta llenar la concurrencia; devuelve cuántas tomó."""
        tomadas = 0
        while len(self._en_curso) < self._concurrencia:
            siguiente = await self.tomar()
            if siguiente is None:
                break
            tarea = asyncio.create_task(self._orquestador.atender(*siguiente))
            self._en_curso.add(tarea)
            tarea.add_done_callback(self._en_curso.discard)
            tomadas += 1
        return tomadas

    async def esperar_en_curso(self) -> None:
        while self._en_curso:
            await asyncio.gather(*list(self._en_curso), return_exceptions=True)

    async def ejecutar(self, detener: asyncio.Event) -> None:
        ultima_recuperacion = datetime.min.replace(tzinfo=UTC)
        while not detener.is_set():
            try:
                if self._reloj() - ultima_recuperacion >= timedelta(seconds=INTERVALO_HUERFANAS_S):
                    await self.recuperar_huerfanas()
                    ultima_recuperacion = self._reloj()
                tomadas = await self.una_vuelta()
            except Exception:  # la base no respondió: se reintenta en la próxima vuelta
                _registro.exception(
                    "vuelta del trabajador fallida", extra={"tipo_evento": "orquestacion"}
                )
                tomadas = 0
            if not tomadas:
                with suppress(TimeoutError):
                    await asyncio.wait_for(detener.wait(), timeout=self._espera_cola)
        await self.esperar_en_curso()


def url_checkpointer(ajustes: Ajustes) -> str:
    """La URL de la base sin el controlador de SQLAlchemy, para psycopg."""
    url = make_url(ajustes.url_bd.get_secret_value()).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


async def principal() -> None:
    ajustes = cargar_ajustes()
    configurar_registro()
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    async with abrir() as unidad:
        _, parametros = await unidad.configuracion.vigente()
    fabrica = FabricaEjecutores(ajustes, parametros, abrir, _ahora)
    detener = asyncio.Event()
    bucle = asyncio.get_running_loop()
    for senal in (signal.SIGTERM, signal.SIGINT):
        with suppress(NotImplementedError):  # Windows no admite señales en el bucle
            bucle.add_signal_handler(senal, detener.set)
    try:
        async with AsyncPostgresSaver.from_conn_string(url_checkpointer(ajustes)) as guardado:
            orquestador = Orquestador(fabrica, abrir, _ahora, guardado)
            trabajador = Trabajador(
                abrir,
                orquestador,
                concurrencia=ajustes.concurrencia_trabajador,
                espera_cola_s=ajustes.espera_cola_s,
                espera_reintento_s=ajustes.espera_reintento_s,
                espera_huerfana_s=ajustes.espera_huerfana_s,
            )
            _registro.info(
                "trabajador iniciado",
                extra={
                    "tipo_evento": "arranque",
                    "concurrencia": ajustes.concurrencia_trabajador,
                },
            )
            await trabajador.ejecutar(detener)
    finally:
        await fabrica.cerrar()
        await motor.dispose()
        _registro.info("trabajador detenido", extra={"tipo_evento": "apagado"})


if __name__ == "__main__":
    asyncio.run(principal())
