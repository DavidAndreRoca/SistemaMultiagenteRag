"""Alta de una cuenta de investigador (A2): ``python -m app.seguridad.crear_investigador CODIGO``.

Es la única forma de crear la primera cuenta A2 (no hay registro abierto de usuarios).
La contraseña inicial aleatoria se imprime una sola vez y debe cambiarse al entrar.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.bd.enumeraciones import Rol
from app.bd.modelos import Cuenta
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.casos.servicio import PATRON_CODIGO, FormatoInvalido, normalizar_codigo
from app.configuracion import ErrorConfiguracion, cargar_ajustes
from app.repositorios.unidad import UnidadDeTrabajo
from app.seguridad.credenciales import generar_contrasena_inicial, hashear_contrasena


async def crear_cuenta_investigador(unidad: UnidadDeTrabajo, codigo: str) -> str | None:
    """Crea la cuenta A2 y devuelve la contraseña inicial, o ``None`` si el código existe."""
    codigo = normalizar_codigo(codigo, "código de cuenta", PATRON_CODIGO)
    if await unidad.autenticacion.cuenta_por_codigo(codigo) is not None:
        return None
    contrasena = generar_contrasena_inicial()
    await unidad.autenticacion.agregar_cuenta(
        Cuenta(codigo=codigo, hash_contrasena=hashear_contrasena(contrasena), rol=Rol.INVESTIGADOR)
    )
    await unidad.confirmar()
    return contrasena


async def _ejecutar(codigo: str) -> int:
    ajustes = cargar_ajustes()
    motor = crear_motor(ajustes)
    try:
        async with crear_fabrica_sesiones(motor)() as sesion:
            contrasena = await crear_cuenta_investigador(UnidadDeTrabajo(sesion), codigo)
    finally:
        await motor.dispose()
    if contrasena is None:
        print(f"ERROR: ya existe una cuenta con el código {codigo.upper()}", file=sys.stderr)
        return 1
    print(f"Cuenta de investigador {codigo.upper()} creada.")
    print(f"Contraseña inicial (se muestra una sola vez): {contrasena}")
    return 0


def principal(argumentos: Sequence[str] | None = None) -> int:
    lector = argparse.ArgumentParser(description="Crea una cuenta de investigador (A2).")
    lector.add_argument("codigo", help="Código de la cuenta, por ejemplo INV-01")
    args = lector.parse_args(argumentos)
    try:
        return asyncio.run(_ejecutar(args.codigo))
    except ErrorConfiguracion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except FormatoInvalido as error:
        print(f"ERROR: {error.mensaje}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(principal())
