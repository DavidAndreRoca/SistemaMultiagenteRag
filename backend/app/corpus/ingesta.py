"""Ingesta en lote de una carpeta de PDF en la colección científica de un tema (T10).

``python -m app.corpus.ingesta CARPETA --tema TEMA-01 --investigador INV-01``

* Reanudable por documento: cada documento se confirma por separado y un archivo ya
  indexado o ya excluido en la colección no se procesa otra vez. Se puede detener con
  Ctrl+C (el documento en curso se revierte entero) y continuar ejecutando el mismo
  comando.
* Muestra el avance por documento (posición, porcentaje, tiempo transcurrido y
  estimación del restante) y el tiempo de cada etapa; al final, el resumen y el tiempo
  y la memoria por etapa. Nunca imprime texto de los documentos.
* Un error transitorio (GROBID o el servicio de modelos caídos) no deja nada a medias:
  se informa y el archivo se reintenta en la próxima pasada.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.comun.errores import ErrorAplicacion
from app.configuracion import ErrorConfiguracion, cargar_ajustes
from app.corpus.fabrica import crear_indexador
from app.corpus.indexacion import Indexador, Resultado, ResultadoIngesta
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import FabricaUnidades, fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador

ERROR = "error"
ETAPAS = ("validacion", "extraccion", "segmentacion", "cabecera", "embeddings", "base")


class TemaSinColeccion(Exception):
    def __init__(self, tema: str) -> None:
        super().__init__(f"no existe la colección científica del tema {tema}")


@dataclass
class Avance:
    """Conteo, tiempos acumulados por etapa y picos de memoria de una pasada."""

    total: int
    inicio: float
    conteo: Counter[str] = field(default_factory=Counter)
    segundos: Counter[str] = field(default_factory=Counter)
    memoria_mb: dict[str, float] = field(default_factory=dict)
    duraciones: list[float] = field(default_factory=list)  # de los documentos procesados
    hechos: int = 0

    def registrar(self, resultado: ResultadoIngesta | None, duracion: float) -> None:
        self.hechos += 1
        if resultado is None:
            self.conteo[ERROR] += 1
            return
        self.conteo[resultado.resultado.value] += 1
        if resultado.resultado is not Resultado.YA_REGISTRADO:
            self.duraciones.append(duracion)
        self.segundos.update(resultado.tiempos_s)
        for etapa, pico in resultado.memoria_mb.items():
            self.memoria_mb[etapa] = max(self.memoria_mb.get(etapa, 0.0), pico)

    def prefijo(self, ahora: float) -> str:
        transcurrido = ahora - self.inicio
        pendientes = self.total - self.hechos
        media = sum(self.duraciones) / len(self.duraciones) if self.duraciones else 0.0
        restante = f"~{_duracion(media * pendientes)} restantes" if media else "estimando"
        porcentaje = 100 * self.hechos // self.total if self.total else 100
        ancho = len(str(self.total))
        return (
            f"[{self.hechos:>{ancho}}/{self.total} {porcentaje:3d} % | "
            f"{_duracion(transcurrido)} | {restante}]"
        )

    def resumen_etapas(self) -> str:
        partes = [
            f"{etapa} {self.segundos[etapa]:.0f} s"
            + (f" ({self.memoria_mb[etapa]:.0f} MB)" if etapa in self.memoria_mb else "")
            for etapa in ETAPAS
            if etapa in self.segundos
        ]
        return "; ".join(partes) or "sin documentos procesados"


def _duracion(segundos: float) -> str:
    minutos, resto = divmod(int(segundos), 60)
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f"{horas} h {minutos:02d} min"
    return f"{minutos} min {resto:02d} s" if minutos else f"{resto} s"


async def ingerir_carpeta(
    abrir: FabricaUnidades,
    indexador: Indexador,
    contexto: ContextoAcceso,
    tema: str,
    carpeta: Path,
    escribir: Callable[[str], None] = print,
    reloj: Callable[[], float] = time.monotonic,
) -> Counter[str]:
    """Ingiere cada ``*.pdf`` de la carpeta, en orden alfabético, y devuelve el conteo."""
    archivos = await asyncio.to_thread(pdf_de_la_carpeta, carpeta)
    avance = Avance(total=len(archivos), inicio=reloj())
    try:
        for ruta in archivos:
            inicio = reloj()
            async with abrir() as unidad:
                coleccion = await unidad.colecciones_investigador.cientifica_por_tema(
                    contexto, tema
                )
                if coleccion is None:
                    raise TemaSinColeccion(tema)
                resultado: ResultadoIngesta | None
                try:
                    obtenido = await indexador.ingerir(unidad, contexto, coleccion, ruta, ruta.name)
                except ErrorAplicacion as error:
                    resultado = None
                    detalle = f"{ERROR:14} {ruta.name} | {error.codigo}"
                else:
                    resultado = obtenido
                    detalle = linea(obtenido, reloj() - inicio)
            avance.registrar(resultado, reloj() - inicio)
            escribir(f"{avance.prefijo(reloj())} {detalle}")
    except (KeyboardInterrupt, asyncio.CancelledError):
        escribir(
            f"Ingesta detenida tras {avance.hechos} de {avance.total} archivos. El documento"
            " en curso se revirtió entero; vuelva a ejecutar el mismo comando para continuar."
        )
        raise
    finally:
        escribir(f"Tiempo por etapa (pico de memoria del proceso): {avance.resumen_etapas()}")
    return avance.conteo


def pdf_de_la_carpeta(carpeta: Path) -> list[Path]:
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")


def linea(resultado: ResultadoIngesta, duracion: float | None = None) -> str:
    motivos = ", ".join(resultado.motivos) or "-"
    texto = (
        f"{resultado.resultado.value:14} {resultado.archivo} | "
        f"fragmentos: {resultado.fragmentos} | motivos: {motivos}"
    )
    if duracion is not None and resultado.tiempos_s:
        etapas = ", ".join(
            f"{e} {resultado.tiempos_s[e]:.1f}" for e in ETAPAS if e in resultado.tiempos_s
        )
        texto += f" | {duracion:.1f} s ({etapas})"
    return texto


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
    except KeyboardInterrupt:
        return 130
    except (ErrorConfiguracion, CuentaNoValida, TemaSinColeccion) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except ErrorAplicacion as error:
        print(f"ERROR: {error.mensaje} {error.detalle or ''}".strip(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(principal())
