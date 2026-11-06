"""Contexto de acceso: quién pide (cuenta, rol) y para qué caso (RNF-03, RN-13).

Se construye solo desde una sesión validada (``app.seguridad.dependencias``); ningún
módulo lo fabrica a partir de datos enviados por el cliente.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.bd.enumeraciones import Rol


class ErrorContexto(Exception):
    """Un repositorio recibió un contexto que no corresponde a su rol."""


@dataclass(frozen=True, slots=True)
class ContextoAcceso:
    cuenta_id: uuid.UUID
    rol: Rol
    caso_id: uuid.UUID | None

    def __post_init__(self) -> None:
        if self.rol is Rol.CASO and self.caso_id is None:
            raise ErrorContexto("un contexto A1 exige caso")
        if self.rol is Rol.INVESTIGADOR and self.caso_id is not None:
            raise ErrorContexto("un contexto A2 no tiene caso")

    def caso_exigido(self) -> uuid.UUID:
        """Caso del contexto; falla si el contexto no es de un caso (A1)."""
        if self.rol is not Rol.CASO or self.caso_id is None:
            raise ErrorContexto("operación de datos de caso con un contexto que no es A1")
        return self.caso_id

    def exigir_investigador(self) -> None:
        if self.rol is not Rol.INVESTIGADOR:
            raise ErrorContexto("operación del investigador con un contexto que no es A2")
