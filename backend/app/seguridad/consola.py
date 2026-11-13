"""Contexto de acceso para los comandos de consola del investigador (T10).

Los comandos se ejecutan en el servidor, con acceso a la base, por quien lo administra
(igual que ``crear_investigador``). El contexto se construye desde una cuenta A2
existente, que queda registrada como autora de lo que el comando haga (por ejemplo,
quién indexó cada documento). Nunca se construye desde datos de una petición web.
"""

from __future__ import annotations

from app.bd.enumeraciones import Rol
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo


class CuentaNoValida(Exception):
    """El código no corresponde a una cuenta de investigador."""


async def contexto_de_investigador(unidad: UnidadDeTrabajo, codigo: str) -> ContextoAcceso:
    cuenta = await unidad.autenticacion.cuenta_por_codigo(codigo.strip().upper())
    if cuenta is None or cuenta.rol is not Rol.INVESTIGADOR:
        raise CuentaNoValida(f"{codigo} no es una cuenta de investigador")
    return ContextoAcceso(cuenta_id=cuenta.id, rol=Rol.INVESTIGADOR, caso_id=None)
