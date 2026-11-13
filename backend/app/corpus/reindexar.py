"""Reindexación del corpus cuando cambia el modelo de embeddings (T10; 18.5, RNF-21).

``python -m app.corpus.reindexar --investigador INV-01 [--forzar]``

Vuelve a embeber los fragmentos de todo documento recuperable cuyos vectores sean de
otro modelo o de otra revisión que los del servicio de modelos actual. Con ``--forzar``
reindexa todo. Cada documento se confirma por separado: si el servicio se cae a mitad,
basta con volver a ejecutar el comando.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.comun.errores import ErrorAplicacion
from app.configuracion import ErrorConfiguracion, cargar_ajustes
from app.corpus.fabrica import crear_reindexador
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador


async def _ejecutar(investigador: str, forzar: bool) -> int:
    ajustes = cargar_ajustes()
    indexador = crear_reindexador(ajustes)
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    try:
        async with abrir() as unidad:
            contexto = await contexto_de_investigador(unidad, investigador)
            total = await indexador.reindexar(unidad, contexto, forzar=forzar)
    finally:
        await motor.dispose()
    print(f"Documentos reindexados: {total}")
    return 0


def principal(argumentos: Sequence[str] | None = None) -> int:
    lector = argparse.ArgumentParser(description="Vuelve a embeber el corpus indexado.")
    lector.add_argument("--investigador", required=True, help="Cuenta A2 que ejecuta")
    lector.add_argument(
        "--forzar", action="store_true", help="Reindexa todo, aunque el modelo no haya cambiado"
    )
    args = lector.parse_args(argumentos)
    try:
        return asyncio.run(_ejecutar(args.investigador, args.forzar))
    except (ErrorConfiguracion, CuentaNoValida) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except ErrorAplicacion as error:
        print(f"ERROR: {error.mensaje} {error.detalle or ''}".strip(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(principal())
