"""Servicio de autenticación: inicio, validación y cierre de sesión; cambio de contraseña.

Reglas (T06): sesión de 8 h absolutas con 60 min de inactividad; dos sesiones por
cuenta (una tercera cierra la más antigua, decisión T06-01); bloqueo de 15 min tras
5 fallos en 15 min; cambio obligatorio de la contraseña inicial; mensajes que no
revelan si la cuenta existe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.bd.enumeraciones import Rol
from app.bd.modelos import Cuenta, Sesion
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.seguridad import politica
from app.seguridad.credenciales import (
    generar_token_sesion,
    hashear_contrasena,
    huella_token,
    verificar_contra_senuelo,
    verificar_contrasena,
)

MENSAJE_CREDENCIALES = (
    "Código o contraseña incorrectos. Si superó cinco intentos, espere 15 minutos."
)

_seguridad = obtener_registrador("seguridad")


def _evento(accion: str, **datos: object) -> None:
    _seguridad.info(
        "evento de seguridad", extra={"tipo_evento": "seguridad", "accion": accion, **datos}
    )


class CredencialesInvalidas(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__("credenciales_invalidas", MENSAJE_CREDENCIALES, estado_http=401)


class SesionInvalida(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sesion_invalida",
            "La sesión no es válida o expiró. Inicie sesión de nuevo.",
            estado_http=401,
        )


class ContrasenaRechazada(ErrorAplicacion):
    def __init__(self, mensaje: str) -> None:
        super().__init__("contrasena_rechazada", mensaje, estado_http=422)


@dataclass(frozen=True)
class SesionIniciada:
    token: str
    cuenta: Cuenta
    sesion: Sesion


@dataclass(frozen=True)
class SesionActual:
    token: str
    cuenta: Cuenta
    sesion: Sesion

    @property
    def contexto(self) -> ContextoAcceso:
        return ContextoAcceso(
            cuenta_id=self.cuenta.id, rol=self.cuenta.rol, caso_id=self.cuenta.caso_id
        )


def _registrar_fallo(cuenta: Cuenta, ahora: datetime) -> None:
    if cuenta.primer_fallo_en is None or ahora - cuenta.primer_fallo_en > politica.VENTANA_FALLOS:
        cuenta.primer_fallo_en = ahora
        cuenta.intentos_fallidos = 1
    else:
        cuenta.intentos_fallidos += 1
    if cuenta.intentos_fallidos >= politica.MAXIMO_FALLOS:
        cuenta.bloqueada_hasta = ahora + politica.DURACION_BLOQUEO
        cuenta.intentos_fallidos = 0
        cuenta.primer_fallo_en = None
        _evento("bloqueo", cuenta_id=str(cuenta.id))
    else:
        _evento("fallo", cuenta_id=str(cuenta.id))


async def iniciar_sesion(
    unidad: UnidadDeTrabajo, codigo: str, contrasena: str, ahora: datetime
) -> SesionIniciada:
    cuenta = await unidad.autenticacion.cuenta_por_codigo(codigo.strip().upper())
    if cuenta is None:
        verificar_contra_senuelo(contrasena)
        _evento("fallo")  # sin el código: podría ser una contraseña escrita en el campo
        raise CredencialesInvalidas()

    if cuenta.bloqueada_hasta is not None and ahora < cuenta.bloqueada_hasta:
        verificar_contra_senuelo(contrasena)
        _evento("rechazo_bloqueada", cuenta_id=str(cuenta.id))
        raise CredencialesInvalidas()

    if not verificar_contrasena(cuenta.hash_contrasena, contrasena):
        _registrar_fallo(cuenta, ahora)
        await unidad.confirmar()
        raise CredencialesInvalidas()

    if (
        cuenta.rol is Rol.CASO
        and cuenta.caso_id is not None
        and not await unidad.autenticacion.caso_habilitado(cuenta.caso_id)
    ):
        _evento("rechazo_caso_desactivado", cuenta_id=str(cuenta.id))
        raise CredencialesInvalidas()

    cuenta.intentos_fallidos = 0
    cuenta.primer_fallo_en = None
    cuenta.bloqueada_hasta = None

    abiertas = list(await unidad.autenticacion.sesiones_abiertas(cuenta.id))
    exceso = len(abiertas) - (politica.MAXIMO_SESIONES_POR_CUENTA - 1)
    for antigua in abiertas[: max(exceso, 0)]:
        antigua.cerrada_en = ahora
        antigua.motivo_cierre = "limite"

    token = generar_token_sesion()
    sesion = await unidad.autenticacion.agregar_sesion(
        Sesion(
            cuenta_id=cuenta.id,
            huella_token=huella_token(token),
            creada_en=ahora,
            ultima_actividad_en=ahora,
            expira_en=ahora + politica.DURACION_ABSOLUTA_SESION,
        )
    )
    await unidad.confirmar()
    _evento("inicio", cuenta_id=str(cuenta.id), sesiones_cerradas_por_limite=max(exceso, 0))
    return SesionIniciada(token=token, cuenta=cuenta, sesion=sesion)


async def validar_sesion(
    unidad: UnidadDeTrabajo, token: str | None, ahora: datetime
) -> SesionActual:
    """Sesión vigente del token o ``SesionInvalida``. Renueva la marca de actividad."""
    if not token:
        raise SesionInvalida()
    sesion = await unidad.autenticacion.sesion_por_huella(huella_token(token))
    if sesion is None or sesion.cerrada_en is not None:
        raise SesionInvalida()

    motivo = None
    if ahora >= sesion.expira_en:
        motivo = "expiracion"
    elif ahora - sesion.ultima_actividad_en >= politica.INACTIVIDAD_MAXIMA:
        motivo = "inactividad"
    cuenta = await unidad.autenticacion.cuenta_por_id(sesion.cuenta_id)
    if motivo is None and (
        cuenta is None
        or (
            cuenta.rol is Rol.CASO
            and cuenta.caso_id is not None
            and not await unidad.autenticacion.caso_habilitado(cuenta.caso_id)
        )
    ):
        motivo = "caso_desactivado"
    if motivo is not None or cuenta is None:
        sesion.cerrada_en = ahora
        sesion.motivo_cierre = motivo
        await unidad.confirmar()
        _evento("sesion_vencida", motivo=motivo)
        raise SesionInvalida()

    sesion.ultima_actividad_en = ahora
    await unidad.confirmar()
    return SesionActual(token=token, cuenta=cuenta, sesion=sesion)


async def cerrar_sesion(unidad: UnidadDeTrabajo, actual: SesionActual, ahora: datetime) -> None:
    actual.sesion.cerrada_en = ahora
    actual.sesion.motivo_cierre = "cierre"
    await unidad.confirmar()
    _evento("cierre", cuenta_id=str(actual.cuenta.id))


def _validar_politica(cuenta: Cuenta, nueva: str) -> None:
    if len(nueva) < politica.LONGITUD_MINIMA_CONTRASENA:
        raise ContrasenaRechazada(
            f"La contraseña nueva debe tener al menos {politica.LONGITUD_MINIMA_CONTRASENA} "
            "caracteres."
        )
    if nueva.strip().upper() == cuenta.codigo:
        raise ContrasenaRechazada("La contraseña nueva no puede ser igual al código de la cuenta.")
    if verificar_contrasena(cuenta.hash_contrasena, nueva):
        raise ContrasenaRechazada("La contraseña nueva debe ser distinta de la actual.")


async def cambiar_contrasena(
    unidad: UnidadDeTrabajo,
    actual: SesionActual,
    contrasena_actual: str,
    nueva: str,
    ahora: datetime,
) -> None:
    """Cambia la contraseña y cierra las demás sesiones de la cuenta."""
    cuenta = actual.cuenta
    if not verificar_contrasena(cuenta.hash_contrasena, contrasena_actual):
        _evento("cambio_contrasena_rechazado", cuenta_id=str(cuenta.id))
        raise ContrasenaRechazada("La contraseña actual no es correcta.")
    _validar_politica(cuenta, nueva)
    cuenta.hash_contrasena = hashear_contrasena(nueva)
    cuenta.contrasena_inicial_cambiada = True
    await unidad.autenticacion.cerrar_otras_sesiones(
        cuenta.id, conservar=actual.sesion.id, ahora=ahora, motivo="contrasena"
    )
    await unidad.confirmar()
    _evento("cambio_contrasena", cuenta_id=str(cuenta.id))
