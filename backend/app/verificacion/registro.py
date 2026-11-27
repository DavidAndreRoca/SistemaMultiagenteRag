"""Registro de una verificación por intento (T30; RF-11, PI-04, RNF-05).

Traduce las comprobaciones de un intento a una fila de ``verificacion``, en el orden de la
Fase 1 (6.7). Una comprobación que no aplica al tipo queda en nulo. ``superada`` es la
conjunción de todas: coincide con la restricción ``superada_coherente`` de la tabla.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.bd.enumeraciones import Etiqueta, MetodoComprobacionFuentes
from app.bd.modelos import Verificacion
from app.verificacion.comprobaciones import Comprobacion


def _todas(comprobaciones: Sequence[Comprobacion], numero: int) -> bool | None:
    propias = [c for c in comprobaciones if c.numero == numero]
    return all(c.superada for c in propias) if propias else None


def _dato(comprobaciones: Sequence[Comprobacion], numero: int, clave: str) -> Any:
    for comprobacion in comprobaciones:
        if comprobacion.numero == numero and clave in comprobacion.datos:
            return comprobacion.datos[clave]
    return None


def superadas(comprobaciones: Sequence[Comprobacion]) -> bool:
    return all(c.superada for c in comprobaciones)


def etiqueta_de(comprobaciones: Sequence[Comprobacion]) -> Etiqueta:
    """Verificada si se superan todas; si no, "Con advertencias" (RN-06). La abstención,
    "Sin evidencia suficiente", la pone la recuperación (T16)."""
    return Etiqueta.VERIFICADA if superadas(comprobaciones) else Etiqueta.CON_ADVERTENCIAS


def advertencias_de(comprobaciones: Sequence[Comprobacion]) -> list[str]:
    return [m for c in comprobaciones if not c.superada for m in c.motivos]


def motivos_para_reintento(comprobaciones: Sequence[Comprobacion]) -> list[str]:
    """Los motivos de las fallas que el agente puede corregir (a lo sumo diez)."""
    return [m for c in comprobaciones if not c.superada and c.reintentable for m in c.motivos][:10]


def verificacion_de(
    resultado_id: uuid.UUID,
    intento: int,
    comprobaciones: Sequence[Comprobacion],
    ahora: datetime,
) -> Verificacion:
    formato = _todas(comprobaciones, 1)
    metodo = _dato(comprobaciones, 4, "metodo")
    return Verificacion(
        resultado_id=resultado_id,
        intento=intento,
        formato_ok=bool(formato),
        limites_ok=_todas(comprobaciones, 2),
        citas_ok=_todas(comprobaciones, 3),
        n_fuentes_citadas=_dato(comprobaciones, 4, "citadas") or 0,
        n_fuentes_confirmadas=_dato(comprobaciones, 4, "confirmadas") or 0,
        n_fuentes_no_comprobables=_dato(comprobaciones, 4, "no_comprobables") or 0,
        metodo=MetodoComprobacionFuentes(metodo) if metodo else None,
        acceso_abierto_ok=_todas(comprobaciones, 5),
        fidelidad=_dato(comprobaciones, 6, "fidelidad"),
        umbral_fidelidad=_dato(comprobaciones, 6, "umbral"),
        afirmaciones_total=_dato(comprobaciones, 6, "total"),
        afirmaciones_respaldadas=_dato(comprobaciones, 6, "respaldadas"),
        afirmaciones_no_respaldadas=_dato(comprobaciones, 6, "no_respaldadas"),
        afirmaciones_contradichas=_dato(comprobaciones, 6, "contradichas"),
        motivos_falla=advertencias_de(comprobaciones),
        superada=superadas(comprobaciones),
        modelo_evaluador=(_dato(comprobaciones, 6, "modelo") or None),
        verificada_en=ahora,
    )
