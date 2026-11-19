"""Carga de una versión del borrador (RF-01, CU-01; decisión T11-01).

Valida el archivo, extrae sus párrafos, lo guarda con nombre aleatorio y registra la
versión como vigente de su hito, sin borrar las anteriores (RN-09). Si algo falla, no
queda versión ni archivo. El registro nunca lleva el nombre ni el texto del borrador.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from app.administracion.parametros import Hito
from app.bd.modelos import VersionBorrador
from app.borradores.extraccion import TextoBorrador, extraer_parrafos
from app.borradores.validacion import (
    BorradorRechazado,
    MotivoRechazo,
    validar_docx,
)
from app.comun.almacen import AlmacenPrivado
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo

SUBCARPETA = "borradores"
_registro = obtener_registrador("borradores")


class HitoDesconocido(ErrorAplicacion):
    def __init__(self, validos: Sequence[str]) -> None:
        super().__init__(
            "hito_desconocido",
            "El hito indicado no existe en el programa.",
            estado_http=422,
            detalle={"hitos": list(validos)},
        )


class BorradorDemasiadoGrande(ErrorAplicacion):
    def __init__(self, limite_mb: int) -> None:
        super().__init__(
            "archivo_demasiado_grande",
            f"El borrador supera el tamaño máximo de {limite_mb} MB.",
            estado_http=413,
            detalle={"limite_mb": limite_mb},
        )


class VersionResumen(BaseModel):
    id: str
    hito: str
    nombre_hito: str | None  # None si el hito salió del catálogo vigente
    cargada_en: datetime
    vigente: bool
    tamano_bytes: int
    palabras: int

    @classmethod
    def desde(cls, version: VersionBorrador, hitos: Sequence[Hito]) -> VersionResumen:
        nombre = next((h.nombre for h in hitos if h.codigo == version.hito), None)
        return cls(
            id=str(version.id),
            hito=version.hito,
            nombre_hito=nombre,
            cargada_en=version.cargada_en,
            vigente=version.vigente,
            tamano_bytes=version.tamano_bytes,
            palabras=version.palabras,
        )


class VersionDetalle(VersionResumen):
    huella_sha256: str
    parrafos: int

    @classmethod
    def con_detalle(cls, version: VersionBorrador, hitos: Sequence[Hito]) -> VersionDetalle:
        resumen = VersionResumen.desde(version, hitos)
        return cls(
            **resumen.model_dump(),
            huella_sha256=version.huella_sha256,
            parrafos=len(version.parrafos),
        )


class ResultadoCarga(BaseModel):
    version: VersionDetalle
    primera_del_hito: bool
    mensajes: list[str]


def evento_de_validacion(contexto: ContextoAcceso, motivo: str, tamano_bytes: int) -> None:
    """Evento de validación (CP-02): motivo, caso y tamaño; nunca el nombre ni el texto."""
    _registro.warning(
        "borrador rechazado",
        extra={
            "tipo_evento": "validacion_borrador",
            "motivo": motivo,
            "caso_id": str(contexto.caso_exigido()),
            "tamano_bytes": tamano_bytes,
        },
    )


def _huella(ruta: Path) -> str:
    calculo = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for parte in iter(lambda: archivo.read(1 << 20), b""):
            calculo.update(parte)
    return calculo.hexdigest()


def _preparar(ruta: Path, nombre: str | None, tipo: str | None) -> tuple[TextoBorrador, str]:
    validar_docx(ruta, nombre, tipo)
    try:
        texto = extraer_parrafos(ruta)
    except (KeyError, ValueError, AttributeError) as error:  # ya validado: no debería ocurrir
        raise BorradorRechazado(MotivoRechazo.DOCX_DANADO) from error
    return texto, _huella(ruta)


class ServicioBorradores:
    def __init__(self, almacen: AlmacenPrivado) -> None:
        self._almacen = almacen

    async def cargar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        hito: str,
        ruta: Path,
        nombre: str | None,
        tipo: str | None,
        ahora: datetime,
    ) -> ResultadoCarga:
        _, parametros = await unidad.configuracion.vigente()
        hito_elegido = parametros.hito(hito)
        if hito_elegido is None:
            raise HitoDesconocido([h.codigo for h in parametros.hitos])
        tamano = (await asyncio.to_thread(ruta.stat)).st_size
        try:
            texto, huella = await asyncio.to_thread(_preparar, ruta, nombre, tipo)
        except BorradorRechazado as rechazo:
            evento_de_validacion(contexto, rechazo.motivo.value, tamano)
            raise

        relativa = await asyncio.to_thread(self._almacen.guardar, ruta)
        try:
            version = VersionBorrador(
                hito=hito_elegido.codigo,
                cargada_en=ahora,
                ruta_archivo=relativa,
                huella_sha256=huella,
                tamano_bytes=tamano,
                parrafos=[p.model_dump() for p in texto.parrafos],
                palabras=texto.palabras,
            )
            anterior = await unidad.versiones.registrar_vigente(contexto, version)
            await unidad.confirmar()
        except BaseException:
            self._almacen.borrar(relativa)
            raise
        _registro.info(
            "version de borrador registrada",
            extra={
                "tipo_evento": "borrador",
                "caso_id": str(contexto.caso_exigido()),
                "version_id": str(version.id),
                "hito": hito_elegido.codigo,
                "palabras": texto.palabras,
                "parrafos": len(texto.parrafos),
                "tamano_bytes": tamano,
            },
        )
        nombre_hito = hito_elegido.nombre
        mensajes = [
            f"Es la primera versión del hito {nombre_hito}."
            if anterior is None
            else f"Esta versión reemplaza como vigente a la anterior del hito {nombre_hito}."
        ]
        if not texto.parrafos:
            mensajes.append("No se encontró texto en el documento.")
        return ResultadoCarga(
            version=VersionDetalle.con_detalle(version, parametros.hitos),
            primera_del_hito=anterior is None,
            mensajes=mensajes,
        )
