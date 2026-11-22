"""Interfaz única de los modelos de lenguaje (T17-01, apartado 1; RNF-20).

Los agentes (T18 en adelante) dependen solo de ``ModeloLenguaje``. ``CadenaModelos``
la implementa con los proveedores de la configuración.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.llm.modelos import EntradaModelo, Instruccion, ResultadoEstructurado


class ModeloLenguaje(Protocol):
    async def generar[T: BaseModel](
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[T]
    ) -> ResultadoEstructurado[T]: ...
