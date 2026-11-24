"""Completa el acceso abierto de los documentos con DOI de un tema (T19-01, apartado 6).

``python -m app.corpus.acceso_abierto --tema T --investigador I [--aplicar]``

Para cada documento con DOI cuyo estado de acceso abierto es ``desconocido`` consulta
Unpaywall (cliente y caché de T14) y guarda el estado, la página de acceso abierto y la
licencia. Solo cambia esos metadatos: el texto, los fragmentos y los vectores no se tocan.
Sin ``--aplicar`` solo informa lo que cambiaría. Si Unpaywall no responde, el documento
queda como estaba (RN-18) y se puede repetir el comando.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from collections import Counter

from app.bd.enumeraciones import EstadoAccesoAbierto
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.bibliografia.fabrica import crear_servicios
from app.bibliografia.interfaces import ServicioBibliografico
from app.bibliografia.modelos import Estado
from app.configuracion import cargar_ajustes
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo, fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador


def _estado(valor: str | None) -> EstadoAccesoAbierto:
    try:
        return EstadoAccesoAbierto(valor or "")
    except ValueError:
        return EstadoAccesoAbierto.DESCONOCIDO


async def completar(
    unidad: UnidadDeTrabajo,
    contexto: ContextoAcceso,
    coleccion_id: uuid.UUID,
    unpaywall: ServicioBibliografico,
    *,
    aplicar: bool,
) -> Counter[str]:
    """Consulta Unpaywall por cada documento con DOI sin acceso abierto y, con ``aplicar``,
    guarda el estado, la página de acceso abierto y la licencia. Devuelve los conteos."""
    conteo: Counter[str] = Counter()
    documentos = await unidad.corpus.sin_acceso_abierto_comprobado(contexto, coleccion_id)
    for documento in documentos:
        assert documento.doi is not None
        resultado = await unpaywall.por_doi(documento.doi)
        if resultado.estado is Estado.NO_COMPROBABLE:
            conteo["no_comprobable"] += 1
            continue
        abierto = resultado.acceso_abierto
        if resultado.estado is Estado.NO_ENCONTRADO or abierto is None:
            # Unpaywall no lo conoce: sigue sin comprobarse y no se recomienda (RN-14).
            conteo["sin_registro"] += 1
            continue
        if abierto.es_abierto:
            nuevo = _estado(abierto.estado)
            if nuevo in (EstadoAccesoAbierto.DESCONOCIDO, EstadoAccesoAbierto.CLOSED):
                nuevo = EstadoAccesoAbierto.GREEN
        else:
            nuevo = EstadoAccesoAbierto.CLOSED
        conteo[nuevo.value] += 1
        if aplicar:
            documento.estado_oa = nuevo
            if abierto is not None and abierto.es_abierto:
                documento.url_acceso_abierto = abierto.url or abierto.url_pdf
                documento.licencia = (abierto.licencia or "")[:80] or documento.licencia
    if aplicar:
        await unidad.confirmar()
    return conteo


async def _ejecutar(tema: str, investigador: str, aplicar: bool) -> int:
    ajustes = cargar_ajustes()
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    servicios = crear_servicios(ajustes, abrir)
    conteo: Counter[str] = Counter()
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
            conteo = await completar(
                unidad, contexto, coleccion.id, servicios.unpaywall, aplicar=aplicar
            )
    finally:
        await servicios.cerrar()
        await motor.dispose()
    modo = "aplicado" if aplicar else "simulación (use --aplicar para guardar)"
    print(f"{tema}: {sum(conteo.values())} documentos con DOI sin acceso abierto, {modo}")
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
