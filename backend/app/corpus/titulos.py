"""Títulos del corpus desde Crossref (``python -m app.corpus.titulos``).

``python -m app.corpus.titulos --tema T --investigador I [--aplicar]``

La extracción con GROBID (T10) dejó algunos títulos vacíos, cortados o en mayúsculas (por
ejemplo, el nombre de la revista). Para cada documento con DOI cuyo título parece dudoso
(vacío, de menos de 30 caracteres o todo en mayúsculas), toma el título que registra
Crossref y, con ``--aplicar``, lo guarda. Solo cambia el título: ni fragmentos ni vectores.
Sin ``--aplicar`` solo informa. Un título de Crossref también en mayúsculas no se usa.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from collections import Counter

from app.bd.modelos import Documento
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.bibliografia.fabrica import crear_servicios
from app.bibliografia.interfaces import ServicioBibliografico
from app.bibliografia.modelos import Estado
from app.configuracion import cargar_ajustes
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo, fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador

LARGO_MINIMO = 30


def dudoso(titulo: str | None) -> bool:
    if not titulo:
        return True
    letras = [c for c in titulo if c.isalpha()]
    return len(titulo) < LARGO_MINIMO or (bool(letras) and titulo == titulo.upper())


async def corregir(
    unidad: UnidadDeTrabajo,
    contexto: ContextoAcceso,
    coleccion_id: uuid.UUID,
    crossref: ServicioBibliografico,
    *,
    aplicar: bool,
) -> Counter[str]:
    conteo: Counter[str] = Counter()
    documentos: list[Documento] = [
        d for d in await unidad.corpus.con_doi(contexto, coleccion_id) if dudoso(d.titulo)
    ]
    for documento in documentos:
        assert documento.doi is not None
        resultado = await crossref.por_doi(documento.doi)
        nuevo = resultado.metadatos.titulo if resultado.metadatos else None
        if resultado.estado is not Estado.ENCONTRADO or not nuevo or dudoso(nuevo):
            conteo["sin_titulo_util"] += 1
            continue
        conteo["corregido"] += 1
        if aplicar:
            documento.titulo = " ".join(nuevo.split())
    if aplicar:
        await unidad.confirmar()
    return conteo


async def _ejecutar(tema: str, investigador: str, aplicar: bool) -> int:
    ajustes = cargar_ajustes()
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    servicios = crear_servicios(ajustes, abrir)
    try:
        async with abrir() as unidad:
            try:
                contexto = await contexto_de_investigador(unidad, investigador)
            except CuentaNoValida as error:
                print(error)
                return 2
            coleccion = await unidad.corpus.coleccion_del_tema(contexto, tema)
            if coleccion is None:
                print(f"no existe la colección científica del tema {tema}")
                return 2
            conteo = await corregir(
                unidad, contexto, coleccion.id, servicios.crossref, aplicar=aplicar
            )
    finally:
        await servicios.cerrar()
        await motor.dispose()
    modo = "aplicado" if aplicar else "simulación (use --aplicar para guardar)"
    print(f"{tema}: {sum(conteo.values())} títulos dudosos, {modo}")
    for clave, cantidad in sorted(conteo.items()):
        print(f"  {clave}: {cantidad}")
    return 0


def principal() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--tema", required=True)
    argumentos.add_argument("--investigador", required=True)
    argumentos.add_argument("--aplicar", action="store_true")
    leidos = argumentos.parse_args()
    fabrica = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    codigo = asyncio.run(
        _ejecutar(leidos.tema, leidos.investigador, leidos.aplicar), loop_factory=fabrica
    )
    raise SystemExit(codigo)


if __name__ == "__main__":
    principal()
