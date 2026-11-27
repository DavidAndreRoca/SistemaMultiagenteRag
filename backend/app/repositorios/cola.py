"""Cola de solicitudes sobre ``solicitud.estado`` (T28; RNF-07, decisión T28-01).

Es el único repositorio que lee solicitudes de todos los casos, porque el trabajador no
tiene sesión: solo devuelve identificadores (solicitud y caso) y la cuenta del caso con la
que el trabajador arma su ``ContextoAcceso``. Todo lo demás (alcance, borrador, resultado)
se lee después con los repositorios de caso y ese contexto, como en la API (4.5).

* ``tomar``: la solicitud recibida más antigua, con ``SELECT ... FOR UPDATE SKIP LOCKED``,
  que pasa a ``asignada`` en la misma transacción. Dos trabajadores nunca toman la misma.
  Una solicitud reencolada por una caída del proveedor espera ``espera_reintento`` segundos
  por cada intento técnico antes de volver a tomarse.
* ``recuperar_huerfanas``: las que quedaron en curso sin cambios durante ``antes_de`` (el
  trabajador se reinició a mitad) vuelven a la cola, hasta ``max_intentos``; después quedan
  "no atendida".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.enumeraciones import EstadoSolicitud, Rol
from app.bd.modelos import Cuenta, Solicitud

EN_CURSO = (
    EstadoSolicitud.ASIGNADA,
    EstadoSolicitud.RECUPERANDO,
    EstadoSolicitud.GENERANDO,
    EstadoSolicitud.VERIFICANDO,
    EstadoSolicitud.REINTENTANDO,
)


class RepositorioCola:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def tomar(
        self, ahora: datetime, espera_reintento: timedelta
    ) -> tuple[uuid.UUID, uuid.UUID] | None:
        """(solicitud, caso) de la siguiente solicitud, ya en ``asignada``; el que llama
        confirma la transacción."""
        disponible = or_(
            Solicitud.intentos_tecnicos == 0,
            Solicitud.actualizada_en
            <= ahora - espera_reintento * func.greatest(Solicitud.intentos_tecnicos, 1),
        )
        fila = (
            await self._sesion.execute(
                select(Solicitud.id, Solicitud.caso_id)
                .where(Solicitud.estado == EstadoSolicitud.RECIBIDA, disponible)
                .order_by(Solicitud.creada_en, Solicitud.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).one_or_none()
        if fila is None:
            return None
        await self._sesion.execute(
            update(Solicitud)
            .where(Solicitud.id == fila.id)
            .values(estado=EstadoSolicitud.ASIGNADA, actualizada_en=ahora)
        )
        return fila.id, fila.caso_id

    async def recuperar_huerfanas(
        self, ahora: datetime, antes_de: datetime, max_intentos: int
    ) -> int:
        """Vuelve a la cola las solicitudes en curso abandonadas; las que agotaron los
        intentos técnicos quedan "no atendida" (recuperables con el reenvío de T29)."""
        abandonadas = and_(Solicitud.estado.in_(EN_CURSO), Solicitud.actualizada_en < antes_de)
        reencoladas = await self._sesion.execute(
            update(Solicitud)
            .where(abandonadas, Solicitud.intentos_tecnicos < max_intentos)
            .values(
                estado=EstadoSolicitud.RECIBIDA,
                intentos_tecnicos=Solicitud.intentos_tecnicos + 1,
                motivo="interrumpida",
                actualizada_en=ahora,
            )
        )
        agotadas = await self._sesion.execute(
            update(Solicitud)
            .where(abandonadas, Solicitud.intentos_tecnicos >= max_intentos)
            .values(estado=EstadoSolicitud.NO_ATENDIDA, motivo="interrumpida", actualizada_en=ahora)
        )
        return int(getattr(reencoladas, "rowcount", 0) or 0) + int(
            getattr(agotadas, "rowcount", 0) or 0
        )

    async def cuenta_del_caso(self, caso_id: uuid.UUID) -> uuid.UUID | None:
        """Una cuenta A1 del caso, para el contexto con el que el trabajador lo atiende."""
        return (
            await self._sesion.execute(
                select(Cuenta.id)
                .where(Cuenta.caso_id == caso_id, Cuenta.rol == Rol.CASO)
                .order_by(Cuenta.codigo)
                .limit(1)
            )
        ).scalar_one_or_none()
