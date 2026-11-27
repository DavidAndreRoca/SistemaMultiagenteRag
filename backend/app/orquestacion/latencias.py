"""Informe de latencias por tipo y por etapa (T30, actividad 9; RNF-12; Fase 1, n.° 11).

``python -m app.orquestacion.latencias --investigador INV-01 [--desde 2026-11-27]``

Para las solicitudes entregadas, calcula la mediana y el percentil 95 de:

* el tiempo total que espera el estudiante (de la creación a la entrega, con la cola);
* cada etapa registrada como evento técnico: ``orquestacion`` (el grafo completo),
  ``ejecucion`` (recuperar, suficiencia y generar), ``verificacion``, ``reintento``,
  ``recuperacion`` y ``reranking``;

y compara el percentil 95 del tiempo total con el objetivo de RNF-12: 60 s para D1, D2, D3
y evidencia; 120 s para la verificación de referencias. Solo lee duraciones y tipos.
"""

from __future__ import annotations

import argparse
import asyncio
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.bd.enumeraciones import TipoSolicitud
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.configuracion import cargar_ajustes
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.tiempos import TiemposSolicitud
from app.repositorios.unidad import fabrica_de_unidades

OBJETIVO_S = {t: 60.0 for t in TipoSolicitud} | {TipoSolicitud.VERIFICACION_REFERENCIAS: 120.0}
ETAPAS = ("orquestacion", "ejecucion", "verificacion", "reintento", "recuperacion", "reranking")


def percentil(valores: Sequence[float], p: float) -> float | None:
    """Percentil por el método del rango más cercano (sin interpolar)."""
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[max(math.ceil(p / 100 * len(ordenados)) - 1, 0)]


@dataclass(frozen=True)
class Fila:
    tipo: TipoSolicitud
    n: int
    mediana_s: float
    p95_s: float
    objetivo_s: float
    etapas_p95_s: dict[str, float]

    @property
    def cumple(self) -> bool:
        return self.p95_s <= self.objetivo_s


def resumir(tiempos: Sequence[TiemposSolicitud]) -> list[Fila]:
    filas = []
    for tipo in TipoSolicitud:
        propios = [t for t in tiempos if t.tipo is tipo]
        if not propios:
            continue
        totales = [t.total_ms / 1000 for t in propios]
        etapas = {
            etapa: percentil([t.etapas[etapa] / 1000 for t in propios if etapa in t.etapas], 95)
            for etapa in ETAPAS
        }
        filas.append(
            Fila(
                tipo=tipo,
                n=len(propios),
                mediana_s=percentil(totales, 50) or 0.0,
                p95_s=percentil(totales, 95) or 0.0,
                objetivo_s=OBJETIVO_S[tipo],
                etapas_p95_s={e: v for e, v in etapas.items() if v is not None},
            )
        )
    return filas


def texto(filas: Sequence[Fila]) -> str:
    if not filas:
        return "No hay solicitudes entregadas con eventos técnicos."
    lineas = ["Tipo | n | mediana (s) | p95 (s) | objetivo (s) | cumple | p95 por etapa (s)"]
    for f in filas:
        etapas = ", ".join(f"{e} {v:.1f}" for e, v in f.etapas_p95_s.items())
        lineas.append(
            f"{f.tipo.value} | {f.n} | {f.mediana_s:.1f} | {f.p95_s:.1f} | {f.objetivo_s:.0f}"
            f" | {'sí' if f.cumple else 'no'} | {etapas}"
        )
    return "\n".join(lineas)


async def principal(codigo: str, desde: datetime | None) -> str:
    ajustes = cargar_ajustes()
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    try:
        async with abrir() as unidad:
            cuenta = await unidad.autenticacion.cuenta_por_codigo(codigo)
            if cuenta is None:
                raise SystemExit(f"No existe la cuenta {codigo}.")
            contexto = ContextoAcceso(cuenta.id, cuenta.rol, None)
            tiempos = await unidad.monitoreo.tiempos(contexto, desde)
    finally:
        await motor.dispose()
    return texto(resumir(tiempos))


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--investigador", required=True)
    analizador.add_argument("--desde", type=datetime.fromisoformat, default=None)
    argumentos = analizador.parse_args()
    desde = (
        argumentos.desde.replace(tzinfo=argumentos.desde.tzinfo or UTC)
        if argumentos.desde
        else None
    )
    print(asyncio.run(principal(argumentos.investigador, desde)))
