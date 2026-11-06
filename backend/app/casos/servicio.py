"""Servicio del investigador para casos, colecciones científicas, cuentas y norma de citación.

* Código de caso repetido: rechazo con mensaje (CP-22).
* Al dar de alta un caso se crean su colección personal y una cuenta (individual) o
  dos (pareja), con contraseña inicial aleatoria que se devuelve una sola vez.
* La norma de citación sale de la lista cerrada de la configuración vigente; IEEE por
  defecto (D-12). Cada cambio queda en ``cambio_norma``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.bd.enumeraciones import EstadoCaso, Rol, TipoAutoria, TipoColeccion
from app.bd.modelos import CambioNorma, Caso, Coleccion, Cuenta
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.seguridad.credenciales import generar_contrasena_inicial, hashear_contrasena

PATRON_CODIGO = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,29}$")
PATRON_TEMA = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,79}$")
SUFIJOS_CUENTA = {TipoAutoria.INDIVIDUAL: ["1"], TipoAutoria.PAREJA: ["1", "2"]}

_registro = obtener_registrador("casos")


class CodigoRepetido(ErrorAplicacion):
    def __init__(self, codigo: str) -> None:
        super().__init__(
            "codigo_repetido",
            f"Ya existe un caso con el código {codigo}. Use otro código.",
            estado_http=409,
        )


class TemaRepetido(ErrorAplicacion):
    def __init__(self, tema: str) -> None:
        super().__init__(
            "tema_repetido", f"Ya existe la colección científica del tema {tema}.", estado_http=409
        )


class TemaInexistente(ErrorAplicacion):
    def __init__(self, tema: str) -> None:
        super().__init__(
            "tema_inexistente",
            f"No existe la colección científica del tema {tema}. Créela antes del caso.",
            estado_http=422,
        )


class NormaNoPermitida(ErrorAplicacion):
    def __init__(self, norma: str, permitidas: Sequence[str]) -> None:
        super().__init__(
            "norma_no_permitida",
            f"La norma {norma} no está en la lista configurada.",
            estado_http=422,
            detalle={"normas_permitidas": list(permitidas)},
        )


class CasoInexistente(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__("no_existe", "El recurso solicitado no existe.", estado_http=404)


class FormatoInvalido(ErrorAplicacion):
    def __init__(self, campo: str) -> None:
        super().__init__(
            "entrada_invalida",
            f"El {campo} solo admite mayúsculas, dígitos, guion y guion bajo.",
            estado_http=422,
        )


@dataclass(frozen=True)
class CredencialInicial:
    codigo: str
    contrasena_inicial: str


@dataclass(frozen=True)
class CasoCreado:
    caso: Caso
    tema: str
    coleccion_personal: Coleccion
    credenciales: list[CredencialInicial]


def normalizar_codigo(valor: str, campo: str, patron: re.Pattern[str]) -> str:
    codigo = valor.strip().upper()
    if not patron.fullmatch(codigo):
        raise FormatoInvalido(campo)
    return codigo


async def crear_coleccion_cientifica(
    unidad: UnidadDeTrabajo, contexto: ContextoAcceso, tema: str
) -> Coleccion:
    tema = normalizar_codigo(tema, "código de tema", PATRON_TEMA)
    if await unidad.colecciones_investigador.cientifica_por_tema(contexto, tema) is not None:
        raise TemaRepetido(tema)
    coleccion = await unidad.colecciones_investigador.agregar(
        contexto, Coleccion(tipo=TipoColeccion.CIENTIFICA, tema=tema)
    )
    await unidad.confirmar()
    _registro.info("coleccion creada", extra={"tipo_evento": "casos", "tema": tema})
    return coleccion


async def crear_caso(
    unidad: UnidadDeTrabajo,
    contexto: ContextoAcceso,
    codigo: str,
    tipo_autoria: TipoAutoria,
    tema: str,
) -> CasoCreado:
    codigo = normalizar_codigo(codigo, "código de caso", PATRON_CODIGO)
    tema = normalizar_codigo(tema, "código de tema", PATRON_TEMA)
    if await unidad.casos_investigador.por_codigo(contexto, codigo) is not None:
        raise CodigoRepetido(codigo)
    sufijos = SUFIJOS_CUENTA[tipo_autoria]
    for sufijo in sufijos:
        if await unidad.cuentas_investigador.existe_codigo(contexto, f"{codigo}-{sufijo}"):
            raise CodigoRepetido(codigo)
    cientifica = await unidad.colecciones_investigador.cientifica_por_tema(contexto, tema)
    if cientifica is None:
        raise TemaInexistente(tema)
    _, parametros = await unidad.configuracion.vigente()

    caso = await unidad.casos_investigador.agregar(
        contexto,
        Caso(
            codigo=codigo,
            tipo_autoria=tipo_autoria,
            coleccion_cientifica_id=cientifica.id,
            norma_citacion=parametros.norma_por_defecto,
            estado=EstadoCaso.HABILITADO,
        ),
    )
    personal = await unidad.colecciones_investigador.agregar(
        contexto, Coleccion(tipo=TipoColeccion.PERSONAL, caso_id=caso.id)
    )
    credenciales = []
    for sufijo in sufijos:
        contrasena = generar_contrasena_inicial()
        cuenta = await unidad.cuentas_investigador.agregar(
            contexto,
            Cuenta(
                codigo=f"{codigo}-{sufijo}",
                hash_contrasena=hashear_contrasena(contrasena),
                rol=Rol.CASO,
                caso_id=caso.id,
            ),
        )
        credenciales.append(CredencialInicial(cuenta.codigo, contrasena))
    await unidad.confirmar()
    _registro.info(
        "caso creado",
        extra={"tipo_evento": "casos", "caso": codigo, "cuentas": len(credenciales)},
    )
    return CasoCreado(caso=caso, tema=tema, coleccion_personal=personal, credenciales=credenciales)


async def obtener_caso(unidad: UnidadDeTrabajo, contexto: ContextoAcceso, codigo: str) -> Caso:
    caso = await unidad.casos_investigador.por_codigo(contexto, codigo.strip().upper())
    if caso is None:
        raise CasoInexistente()
    return caso


async def cambiar_estado(
    unidad: UnidadDeTrabajo,
    contexto: ContextoAcceso,
    codigo: str,
    estado: EstadoCaso,
    ahora: datetime,
) -> Caso:
    """Desactiva o reactiva un caso. Al desactivar se cierran sus sesiones abiertas."""
    caso = await obtener_caso(unidad, contexto, codigo)
    if caso.estado is not estado:
        caso.estado = estado
        caso.actualizado_en = ahora
        if estado is EstadoCaso.DESACTIVADO:
            await unidad.cuentas_investigador.cerrar_sesiones_de_caso(
                contexto, caso, motivo="caso_desactivado", ahora=ahora
            )
        await unidad.confirmar()
        _registro.info(
            "estado de caso",
            extra={"tipo_evento": "casos", "caso": caso.codigo, "estado": estado.value},
        )
    return caso


async def cambiar_norma(
    unidad: UnidadDeTrabajo, contexto: ContextoAcceso, codigo: str, norma: str, ahora: datetime
) -> Caso:
    caso = await obtener_caso(unidad, contexto, codigo)
    _, parametros = await unidad.configuracion.vigente()
    norma = norma.strip().lower()  # los códigos de norma se guardan en minúsculas
    if norma not in parametros.normas_citacion:
        raise NormaNoPermitida(norma, parametros.normas_citacion)
    if caso.norma_citacion != norma:
        anterior = caso.norma_citacion
        caso.norma_citacion = norma
        caso.actualizado_en = ahora
        await unidad.casos_investigador.registrar_cambio_norma(contexto, caso, anterior, norma)
        await unidad.confirmar()
        _registro.info(
            "norma cambiada",
            extra={"tipo_evento": "casos", "caso": caso.codigo, "norma": norma},
        )
    return caso


async def detalle_caso(
    unidad: UnidadDeTrabajo, contexto: ContextoAcceso, codigo: str
) -> tuple[Caso, Coleccion, Sequence[Cuenta], Sequence[CambioNorma]]:
    caso = await obtener_caso(unidad, contexto, codigo)
    coleccion = await unidad.casos_investigador.coleccion_de(contexto, caso.coleccion_cientifica_id)
    cuentas = await unidad.cuentas_investigador.de_caso(contexto, caso)
    cambios = await unidad.casos_investigador.cambios_norma(contexto, caso)
    return caso, coleccion, cuentas, cambios
