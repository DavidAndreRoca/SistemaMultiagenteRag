"""Datos de demostración del prototipo: ``python -m app.bd.demo --credenciales RUTA``.

Crea, si no existen, el investigador ``INV-DEMO`` y el caso individual ``DEMO-01`` en el
tema ``TEMA-1-IA-EDUCACION`` (el del corpus provisional), con norma IEEE. En cada ejecución
asigna contraseñas nuevas a las dos cuentas, ya cambiadas (no piden el cambio al entrar), y
las escribe solo en el archivo indicado, que debe quedar fuera de Git (``datos/`` lo está).
No las imprime. Todo es ficticio; se niega a ejecutarse en producción.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.bd.enumeraciones import Rol, TipoAutoria
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.casos import servicio
from app.configuracion import ErrorConfiguracion, cargar_ajustes
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.seguridad.crear_investigador import crear_cuenta_investigador
from app.seguridad.credenciales import generar_contrasena_inicial, hashear_contrasena

INVESTIGADOR = "INV-DEMO"
CASO = "DEMO-01"
TEMA = "TEMA-1-IA-EDUCACION"


async def preparar(unidad: UnidadDeTrabajo) -> dict[str, str]:
    """Crea lo que falte y devuelve las contraseñas nuevas por cuenta."""
    await crear_cuenta_investigador(unidad, INVESTIGADOR)
    investigador = await unidad.autenticacion.cuenta_por_codigo(INVESTIGADOR)
    assert investigador is not None
    contexto = ContextoAcceso(cuenta_id=investigador.id, rol=Rol.INVESTIGADOR, caso_id=None)
    if await unidad.colecciones_investigador.cientifica_por_tema(contexto, TEMA) is None:
        raise SystemExit(f"no existe la colección científica de {TEMA}: cargue el corpus primero")
    if await unidad.casos_investigador.por_codigo(contexto, CASO) is None:
        await servicio.crear_caso(unidad, contexto, CASO, TipoAutoria.INDIVIDUAL, TEMA)
    sufijos = servicio.SUFIJOS_CUENTA[TipoAutoria.INDIVIDUAL]
    cuentas = [INVESTIGADOR, *(f"{CASO}-{sufijo}" for sufijo in sufijos)]
    contrasenas: dict[str, str] = {}
    for codigo in cuentas:
        cuenta = await unidad.autenticacion.cuenta_por_codigo(codigo)
        assert cuenta is not None
        contrasena = generar_contrasena_inicial()
        cuenta.hash_contrasena = hashear_contrasena(contrasena)
        cuenta.contrasena_inicial_cambiada = True
        cuenta.intentos_fallidos = 0
        cuenta.bloqueada_hasta = None
        contrasenas[codigo] = contrasena
    await unidad.confirmar()
    return contrasenas


async def _ejecutar() -> dict[str, str] | None:
    ajustes = cargar_ajustes()
    if ajustes.es_produccion:
        print("ERROR: los datos de demostración no se cargan en producción.", file=sys.stderr)
        return None
    motor = crear_motor(ajustes)
    try:
        async with crear_fabrica_sesiones(motor)() as sesion:
            return await preparar(UnidadDeTrabajo(sesion))
    finally:
        await motor.dispose()


def escribir(destino: Path, contrasenas: dict[str, str]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    lineas = ["Cuentas de la demostración (ficticias; no se versionan)", ""]
    lineas += [f"{cuenta}: {contrasena}" for cuenta, contrasena in contrasenas.items()]
    destino.write_bytes(("\n".join(lineas) + "\n").encode("utf-8"))


def principal() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--credenciales", type=Path, required=True)
    leidos = argumentos.parse_args()
    try:
        contrasenas = asyncio.run(_ejecutar())
    except ErrorConfiguracion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if contrasenas is None:
        return 1
    escribir(leidos.credenciales, contrasenas)
    print(f"Cuentas listas: {', '.join(contrasenas)}. Contraseñas en {leidos.credenciales}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
