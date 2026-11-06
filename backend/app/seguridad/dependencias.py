"""Dependencias de autorización de FastAPI que producen el ``ContextoAcceso``.

* ``sesion_actual``: cookie válida; en métodos que modifican datos exige además la
  cabecera CSRF.
* ``requiere_caso``: cuenta A1 con la contraseña inicial ya cambiada.
* ``requiere_investigador``: cuenta A2 con la contraseña inicial ya cambiada.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request

from app.bd.enumeraciones import Rol
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.configuracion import Ajustes
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo, obtener_unidad
from app.seguridad import politica
from app.seguridad.credenciales import csrf_valido
from app.seguridad.servicio import SesionActual, validar_sesion

METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})

Reloj = Callable[[], datetime]


def reloj_sistema() -> datetime:
    return datetime.now(UTC)


def obtener_reloj(peticion: Request) -> Reloj:
    """Reloj inyectable (las pruebas lo sustituyen para simular el paso del tiempo)."""
    reloj: Reloj = getattr(peticion.app.state, "reloj", reloj_sistema)
    return reloj


def obtener_ajustes(peticion: Request) -> Ajustes:
    ajustes: Ajustes = peticion.app.state.ajustes
    return ajustes


Unidad = Annotated[UnidadDeTrabajo, Depends(obtener_unidad)]
RelojDep = Annotated[Reloj, Depends(obtener_reloj)]
AjustesDep = Annotated[Ajustes, Depends(obtener_ajustes)]


class SinPermiso(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "sin_permiso", "No tiene permiso para realizar esta operación.", estado_http=403
        )


class CambioContrasenaRequerido(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "cambio_contrasena_requerido",
            "Debe cambiar su contraseña inicial antes de continuar.",
            estado_http=403,
        )


class CsrfInvalido(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "csrf_invalido",
            "La petición no incluye una protección válida. Recargue la página.",
            estado_http=403,
        )


async def sesion_actual(
    peticion: Request, unidad: Unidad, reloj: RelojDep, ajustes: AjustesDep
) -> SesionActual:
    token = peticion.cookies.get(politica.COOKIE_SESION)
    actual = await validar_sesion(unidad, token, reloj())
    if peticion.method not in METODOS_SEGUROS and not csrf_valido(
        ajustes.secreto_sesion.get_secret_value(),
        actual.token,
        peticion.headers.get(politica.CABECERA_CSRF),
    ):
        obtener_registrador("seguridad").warning(
            "csrf invalido", extra={"tipo_evento": "seguridad", "cuenta_id": str(actual.cuenta.id)}
        )
        raise CsrfInvalido()
    return actual


SesionDep = Annotated[SesionActual, Depends(sesion_actual)]


def _exigir_rol(actual: SesionActual, rol: Rol) -> ContextoAcceso:
    if actual.cuenta.rol is not rol:
        obtener_registrador("seguridad").warning(
            "rol insuficiente",
            extra={"tipo_evento": "seguridad", "cuenta_id": str(actual.cuenta.id)},
        )
        raise SinPermiso()
    if not actual.cuenta.contrasena_inicial_cambiada:
        raise CambioContrasenaRequerido()
    return actual.contexto


async def requiere_caso(actual: SesionDep) -> ContextoAcceso:
    return _exigir_rol(actual, Rol.CASO)


async def requiere_investigador(actual: SesionDep) -> ContextoAcceso:
    return _exigir_rol(actual, Rol.INVESTIGADOR)


ContextoCaso = Annotated[ContextoAcceso, Depends(requiere_caso)]
ContextoInvestigador = Annotated[ContextoAcceso, Depends(requiere_investigador)]
