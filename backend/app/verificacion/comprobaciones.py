"""Comprobaciones deterministas 1 y 3 del módulo de verificación (6.7; D-07; T18-01).

Viven fuera de los agentes para que el módulo de integración y verificación (T30) las
reutilice sobre la salida guardada de cualquier tipo.

1. **Esquema del tipo:** la salida cumple el esquema Pydantic de su tipo.
3. **Citas:** todo identificador ``F<n>`` de la salida, en los campos ``citas`` o dentro de
   un texto, está entre los fragmentos recuperados para esa solicitud.

Los motivos nombran campos e identificadores, nunca el contenido (4.6).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterator, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.agentes.esquemas import ESQUEMAS
from app.bd.enumeraciones import TipoSolicitud

_IDENTIFICADOR = re.compile(r"\bF[1-9][0-9]*\b")


class Comprobacion(BaseModel):
    model_config = ConfigDict(frozen=True)

    numero: int
    nombre: str
    superada: bool
    motivos: list[str] = []


def comprobar_esquema(tipo: TipoSolicitud, salida: Any) -> Comprobacion:
    """Comprobación 1: la salida (``dict`` o modelo) cumple el esquema de su tipo."""
    esquema = ESQUEMAS[tipo]
    datos = salida.model_dump(mode="json") if isinstance(salida, BaseModel) else salida
    try:
        esquema.model_validate(datos)
    except ValidationError as error:
        motivos = [
            f"{'.'.join(str(p) for p in e['loc']) or '(raíz)'}: {e['type']}"
            for e in error.errors(include_input=False, include_url=False)
        ]
        return Comprobacion(numero=1, nombre="esquema", superada=False, motivos=motivos[:20])
    return Comprobacion(numero=1, nombre="esquema", superada=True)


def identificadores_citados(salida: Any) -> list[str]:
    """Todos los ``F<n>`` de la salida, en el orden en que aparecen y sin repetir."""
    datos = salida.model_dump(mode="json") if isinstance(salida, BaseModel) else salida
    return list(dict.fromkeys(_recorrer(datos)))


def _recorrer(valor: Any) -> Iterator[str]:
    if isinstance(valor, str):
        yield from _IDENTIFICADOR.findall(valor)
    elif isinstance(valor, dict):
        for sub in valor.values():
            yield from _recorrer(sub)
    elif isinstance(valor, list | tuple):
        for sub in valor:
            yield from _recorrer(sub)


def comprobar_citas(salida: Any, recuperados: Collection[str]) -> Comprobacion:
    """Comprobación 3: cada cita existe entre los fragmentos recuperados de la solicitud."""
    disponibles = set(recuperados)
    inexistentes = [i for i in identificadores_citados(salida) if i not in disponibles]
    if inexistentes:
        return Comprobacion(
            numero=3,
            nombre="citas",
            superada=False,
            motivos=[f"cita a un fragmento no recuperado: {i}" for i in inexistentes],
        )
    return Comprobacion(numero=3, nombre="citas", superada=True)


# Estados de Unpaywall que comprueban el acceso abierto (RN-14). ``closed`` y
# ``desconocido`` no: una fuente sin acceso abierto comprobado no se recomienda.
ACCESO_ABIERTO_COMPROBADO = frozenset({"gold", "green", "hybrid", "bronze"})


def comprobar_acceso_abierto(estado_oa_por_cita: Mapping[str, str | None]) -> Comprobacion:
    """Comprobación 5 (CP-11): toda cita es de un documento con acceso abierto comprobado.

    ``estado_oa_por_cita`` da, para cada identificador citado, el estado de acceso
    abierto del documento al que pertenece.
    """
    sin_acceso = [
        i for i, estado in estado_oa_por_cita.items() if estado not in ACCESO_ABIERTO_COMPROBADO
    ]
    if sin_acceso:
        return Comprobacion(
            numero=5,
            nombre="acceso_abierto",
            superada=False,
            motivos=[f"cita a una fuente sin acceso abierto comprobado: {i}" for i in sin_acceso],
        )
    return Comprobacion(numero=5, nombre="acceso_abierto", superada=True)
