"""Datos semilla ficticios para desarrollo: ``python -m app.bd.semillas``.

Crea, si no existen, un investigador, un tema y dos casos (individual y pareja), todos
con códigos ficticios. Es idempotente y se niega a ejecutarse en producción. Las
contraseñas iniciales se imprimen una sola vez en la consola de quien ejecuta.
"""

from __future__ import annotations

import asyncio
import sys

from app.bd.enumeraciones import Rol, TipoAutoria
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.casos import servicio
from app.configuracion import ErrorConfiguracion, cargar_ajustes
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.seguridad.crear_investigador import crear_cuenta_investigador

INVESTIGADOR = "INV-DEV"
TEMA = "TEMA-DEV-01"
CASOS = [("CASO-DEV-01", TipoAutoria.INDIVIDUAL), ("CASO-DEV-02", TipoAutoria.PAREJA)]


async def sembrar(unidad: UnidadDeTrabajo) -> list[tuple[str, str]]:
    """Crea los datos que falten. Devuelve (cuenta, contraseña inicial) de lo creado."""
    creadas: list[tuple[str, str]] = []
    contrasena = await crear_cuenta_investigador(unidad, INVESTIGADOR)
    if contrasena is not None:
        creadas.append((INVESTIGADOR, contrasena))
    investigador = await unidad.autenticacion.cuenta_por_codigo(INVESTIGADOR)
    assert investigador is not None
    contexto = ContextoAcceso(cuenta_id=investigador.id, rol=Rol.INVESTIGADOR, caso_id=None)

    if await unidad.colecciones_investigador.cientifica_por_tema(contexto, TEMA) is None:
        await servicio.crear_coleccion_cientifica(unidad, contexto, TEMA)
    for codigo, autoria in CASOS:
        if await unidad.casos_investigador.por_codigo(contexto, codigo) is None:
            caso = await servicio.crear_caso(unidad, contexto, codigo, autoria, TEMA)
            creadas.extend((c.codigo, c.contrasena_inicial) for c in caso.credenciales)
    return creadas


async def _ejecutar() -> int:
    ajustes = cargar_ajustes()
    if ajustes.es_produccion:
        print("ERROR: las semillas ficticias no se cargan en producción.", file=sys.stderr)
        return 1
    motor = crear_motor(ajustes)
    try:
        async with crear_fabrica_sesiones(motor)() as sesion:
            creadas = await sembrar(UnidadDeTrabajo(sesion))
    finally:
        await motor.dispose()
    if not creadas:
        print("Las semillas ya existían; no se creó nada.")
    for cuenta, contrasena in creadas:
        print(f"{cuenta}: contraseña inicial {contrasena}")
    return 0


def principal() -> int:
    try:
        return asyncio.run(_ejecutar())
    except ErrorConfiguracion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(principal())
