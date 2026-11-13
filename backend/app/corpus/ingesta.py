"""Ingesta en lote de una carpeta de PDF en la colección científica de un tema (T10).

``python -m app.corpus.ingesta CARPETA --tema TEMA-01 --investigador INV-01``

* Idempotente: un archivo ya indexado o ya excluido en la colección no se procesa otra
  vez, así que la carpeta puede volver a pasarse tras agregar archivos o tras un error.
* Informa, por archivo, el resultado (indexado, incompleto, excluido, duplicado o ya
  registrado) y, al final, el resumen. Nunca imprime texto de los documentos.
* Un error transitorio (GROBID o el servicio de modelos caídos) no deja nada a medias:
  se informa y el archivo se reintenta en la próxima pasada.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.comun.errores import ErrorAplicacion
from app.configuracion import ErrorConfiguracion, cargar_ajustes
from app.corpus.fabrica import crear_indexador
from app.corpus.indexacion import Indexador, ResultadoIngesta
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import FabricaUnidades, fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador

ERROR = "error"


class TemaSinColeccion(Exception):
    def __init__(self, tema: str) -> None:
        super().__init__(f"no existe la colección científica del tema {tema}")


async def ingerir_carpeta(
    abrir: FabricaUnidades,
    indexador: Indexador,
    contexto: ContextoAcceso,
    tema: str,
    carpeta: Path,
    escribir: Callable[[str], None] = print,
) -> Counter[str]:
    """Ingiere cada ``*.pdf`` de la carpeta, en orden alfabético, y devuelve el conteo."""
    conteo: Counter[str] = Counter()
    for ruta in await asyncio.to_thread(pdf_de_la_carpeta, carpeta):
        async with abrir() as unidad:
            coleccion = await unidad.colecciones_investigador.cientifica_por_tema(contexto, tema)
            if coleccion is None:
                raise TemaSinColeccion(tema)
            try:
                resultado = await indexador.ingerir(unidad, contexto, coleccion, ruta, ruta.name)
            except ErrorAplicacion as error:
                conteo[ERROR] += 1
                escribir(f"{ERROR:14} {ruta.name} | {error.codigo}")
                continue
        conteo[resultado.resultado.value] += 1
        escribir(linea(resultado))
    return conteo


def pdf_de_la_carpeta(carpeta: Path) -> list[Path]:
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")


def linea(resultado: ResultadoIngesta) -> str:
    motivos = ", ".join(resultado.motivos) or "-"
    return (
        f"{resultado.resultado.value:14} {resultado.archivo} | "
        f"fragmentos: {resultado.fragmentos} | motivos: {motivos}"
    )


async def _ejecutar(carpeta: Path, tema: str, investigador: str) -> int:
    ajustes = cargar_ajustes()
    indexador = await asyncio.to_thread(crear_indexador, ajustes)
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    try:
        async with abrir() as unidad:
            contexto = await contexto_de_investigador(unidad, investigador)
        conteo = await ingerir_carpeta(abrir, indexador, contexto, tema.strip().upper(), carpeta)
    finally:
        await motor.dispose()
    resumen = ", ".join(f"{clave}: {valor}" for clave, valor in sorted(conteo.items()))
    print(f"Resumen ({sum(conteo.values())} archivos): {resumen or 'carpeta sin PDF'}")
    return 1 if conteo[ERROR] else 0


def principal(argumentos: Sequence[str] | None = None) -> int:
    lector = argparse.ArgumentParser(description="Ingiere una carpeta de PDF en un tema.")
    lector.add_argument("carpeta", type=Path, help="Carpeta con los PDF")
    lector.add_argument("--tema", required=True, help="Código del tema, por ejemplo TEMA-01")
    lector.add_argument("--investigador", required=True, help="Cuenta A2 que indexa")
    args = lector.parse_args(argumentos)
    if not args.carpeta.is_dir():
        print(f"ERROR: {args.carpeta} no es una carpeta", file=sys.stderr)
        return 2
    try:
        return asyncio.run(_ejecutar(args.carpeta, args.tema, args.investigador))
    except (ErrorConfiguracion, CuentaNoValida, TemaSinColeccion) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except ErrorAplicacion as error:
        print(f"ERROR: {error.mensaje} {error.detalle or ''}".strip(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(principal())
