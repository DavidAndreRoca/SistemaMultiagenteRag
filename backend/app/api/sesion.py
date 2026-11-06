"""Rutas de sesión: iniciar, consultar, cerrar y cambiar la contraseña (RF-18)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.bd.enumeraciones import Rol
from app.configuracion import Ajustes
from app.seguridad import politica
from app.seguridad.credenciales import token_csrf
from app.seguridad.dependencias import AjustesDep, RelojDep, SesionDep, Unidad
from app.seguridad.servicio import cambiar_contrasena, cerrar_sesion, iniciar_sesion

router = APIRouter(prefix="/sesion", tags=["sesion"])


class SolicitudInicio(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    contrasena: str = Field(min_length=1, max_length=256)


class EstadoSesion(BaseModel):
    cuenta: str
    rol: Rol
    debe_cambiar_contrasena: bool
    expira_en: datetime
    csrf: str = Field(description="Valor que debe enviarse en la cabecera X-CSRF-Token.")


class SolicitudCambioContrasena(BaseModel):
    contrasena_actual: str = Field(min_length=1, max_length=256)
    contrasena_nueva: str = Field(min_length=1, max_length=256)


def _poner_cookies(respuesta: Response, ajustes: Ajustes, token: str) -> str:
    csrf = token_csrf(ajustes.secreto_sesion.get_secret_value(), token)
    duracion = int(politica.DURACION_ABSOLUTA_SESION.total_seconds())
    respuesta.set_cookie(
        politica.COOKIE_SESION,
        token,
        max_age=duracion,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    respuesta.set_cookie(
        politica.COOKIE_CSRF,
        csrf,
        max_age=duracion,
        httponly=False,
        secure=True,
        samesite="strict",
        path="/",
    )
    return csrf


def _borrar_cookies(respuesta: Response) -> None:
    for nombre in (politica.COOKIE_SESION, politica.COOKIE_CSRF):
        respuesta.delete_cookie(
            nombre, path="/", secure=True, httponly=nombre == politica.COOKIE_SESION
        )


@router.post("", response_model=EstadoSesion, summary="Iniciar sesión")
async def iniciar(
    datos: SolicitudInicio,
    respuesta: Response,
    unidad: Unidad,
    reloj: RelojDep,
    ajustes: AjustesDep,
) -> EstadoSesion:
    iniciada = await iniciar_sesion(unidad, datos.codigo, datos.contrasena, reloj())
    csrf = _poner_cookies(respuesta, ajustes, iniciada.token)
    return EstadoSesion(
        cuenta=iniciada.cuenta.codigo,
        rol=iniciada.cuenta.rol,
        debe_cambiar_contrasena=not iniciada.cuenta.contrasena_inicial_cambiada,
        expira_en=iniciada.sesion.expira_en,
        csrf=csrf,
    )


@router.get("", response_model=EstadoSesion, summary="Sesión actual")
async def consultar(actual: SesionDep, ajustes: AjustesDep) -> EstadoSesion:
    return EstadoSesion(
        cuenta=actual.cuenta.codigo,
        rol=actual.cuenta.rol,
        debe_cambiar_contrasena=not actual.cuenta.contrasena_inicial_cambiada,
        expira_en=actual.sesion.expira_en,
        csrf=token_csrf(ajustes.secreto_sesion.get_secret_value(), actual.token),
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
async def cerrar(actual: SesionDep, respuesta: Response, unidad: Unidad, reloj: RelojDep) -> None:
    await cerrar_sesion(unidad, actual, reloj())
    _borrar_cookies(respuesta)


@router.post("/contrasena", status_code=status.HTTP_204_NO_CONTENT, summary="Cambiar contraseña")
async def cambiar(
    datos: SolicitudCambioContrasena, actual: SesionDep, unidad: Unidad, reloj: RelojDep
) -> None:
    await cambiar_contrasena(
        unidad, actual, datos.contrasena_actual, datos.contrasena_nueva, reloj()
    )
