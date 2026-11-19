"""Vuelve a segmentar los documentos de un tema sin volver a leer los PDF (T10-02).

``python -m app.corpus.resegmentar --tema TEMA-01 --investigador INV-01 [--aplicar]``

Para cada documento de la colección toma los bloques de la caché de extracción (si no
están, extrae una vez el PDF guardado con Docling y los deja en caché), aplica la
limpieza, las secciones y la segmentación vigentes y compara con los fragmentos
guardados. Sirve cuando cambian las reglas de limpieza o la ventana (T34).

* Sin ``--aplicar`` solo informa qué cambiaría.
* Con ``--aplicar`` reemplaza los fragmentos que cambian, reutiliza el vector de los que
  conservan su texto y embebe solo los nuevos. Cada documento se confirma por separado.
* No toca documentos retirados ni los que ya alimentaron solicitudes.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.comun.errores import ErrorAplicacion
from app.configuracion import ErrorConfiguracion, cargar_ajustes
from app.corpus.almacen import AlmacenArchivos
from app.corpus.extraccion import ParametrosCanal, procesar_extraido
from app.corpus.fabrica import CARPETA_CACHE, CorpusNoConfigurado
from app.corpus.indexacion import CambioSegmentacion, Indexador
from app.corpus.ingesta import TemaSinColeccion
from app.inferencia.interfaces import Embeddings
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.repositorios.unidad import fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador


async def _ejecutar(tema: str, investigador: str, aplicar: bool) -> int:
    from app.corpus.cache_extraccion import ExtractorEnCache
    from app.corpus.extractor_docling import ExtractorDocling, OpcionesDocling
    from app.corpus.tokenizador import ContadorTokensBgeM3

    ajustes = cargar_ajustes()
    faltan = [
        nombre
        for nombre, valor in (
            ("DIRECTORIO_RECURSOS_CORPUS", ajustes.directorio_recursos_corpus),
            ("DIRECTORIO_ARCHIVOS", ajustes.directorio_archivos),
            ("URL_SERVICIO_MODELOS", ajustes.url_servicio_modelos if aplicar else "-"),
        )
        if not valor
    ]
    if faltan:
        raise CorpusNoConfigurado(faltan)
    assert ajustes.directorio_recursos_corpus and ajustes.directorio_archivos
    recursos, archivos = Path(ajustes.directorio_recursos_corpus), Path(ajustes.directorio_archivos)
    docling = ExtractorDocling(recursos, OpcionesDocling(hilos=ajustes.hilos_docling))
    extractor = ExtractorEnCache(docling, archivos / CARPETA_CACHE, docling.firma)
    contador = ContadorTokensBgeM3(recursos)
    almacen = AlmacenArchivos(archivos)
    indexador = Indexador(
        None, cliente_desde_ajustes(ajustes) if aplicar else _SinEmbeddings(), almacen
    )
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    conteo: Counter[str] = Counter()
    try:
        async with abrir() as unidad:
            contexto = await contexto_de_investigador(unidad, investigador)
            coleccion = await unidad.colecciones_investigador.cientifica_por_tema(contexto, tema)
            if coleccion is None:
                raise TemaSinColeccion(tema)
            _, vigentes = await unidad.configuracion.vigente()
            parametros = ParametrosCanal.desde(vigentes)
            documentos = [
                d for d, _ in await unidad.corpus.listar_documentos(contexto, coleccion.id)
            ]
        for posicion, documento in enumerate(documentos, start=1):
            if not documento.ruta_archivo or not documento.huella_archivo:
                conteo["sin_archivo"] += 1
                continue
            ruta = almacen.ruta(documento.ruta_archivo)
            extraido = await asyncio.to_thread(extractor.extraer, ruta)
            procesado = procesar_extraido(
                extraido, documento.huella_archivo, documento.num_paginas, contador, parametros
            )
            async with abrir() as unidad:
                actual = await unidad.corpus.documento(contexto, documento.id)
                assert actual is not None
                informe = await indexador.resegmentar(
                    unidad, contexto, actual, procesado, aplicar=aplicar
                )
            conteo[informe.cambio.value] += 1
            detalle = (
                f" | fragmentos {informe.fragmentos_antes} -> {informe.fragmentos_despues},"
                f" reutilizados {informe.reutilizados}, embebidos {informe.embebidos}"
                if informe.cambio in (CambioSegmentacion.CAMBIARIA, CambioSegmentacion.ACTUALIZADO)
                else ""
            )
            avance = f"[{posicion}/{len(documentos)}]"
            print(f"{avance} {informe.cambio.value:12} {informe.archivo}{detalle}")
    finally:
        await motor.dispose()
    print(
        f"Resumen: {', '.join(f'{k}: {v}' for k, v in sorted(conteo.items()))};"
        f" caché de extracción: {extractor.aciertos} aciertos, {extractor.fallos} extracciones"
    )
    if not aplicar and conteo[CambioSegmentacion.CAMBIARIA.value]:
        print("Simulación: vuelva a ejecutar con --aplicar para guardar los cambios.")
    return 0


class _SinEmbeddings:
    """En la simulación no se embebe nada."""

    async def embeber(self, textos: Sequence[str]) -> Embeddings:  # pragma: no cover
        raise RuntimeError("la simulación no embebe")


def principal(argumentos: Sequence[str] | None = None) -> int:
    lector = argparse.ArgumentParser(description="Vuelve a segmentar los documentos de un tema.")
    lector.add_argument("--tema", required=True)
    lector.add_argument("--investigador", required=True)
    lector.add_argument("--aplicar", action="store_true", help="Guarda los cambios")
    args = lector.parse_args(argumentos)
    try:
        return asyncio.run(_ejecutar(args.tema.strip().upper(), args.investigador, args.aplicar))
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
