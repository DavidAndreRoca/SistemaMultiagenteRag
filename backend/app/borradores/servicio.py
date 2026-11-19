"""Carga de una versión del borrador y sus secciones (RF-01, CU-01, F-05; T11-01 y T12-01).

Valida el archivo, extrae sus párrafos, detecta sus secciones por estilos, lo guarda con
nombre aleatorio y registra la versión como vigente de su hito, sin borrar las anteriores
(RN-09). Si algo falla, no queda versión ni archivo. Sin estilos de título, la versión se
crea igual y se pide marcar las secciones a mano. El registro nunca lleva el nombre ni el
texto del borrador.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from app.administracion.parametros import Hito
from app.bd.enumeraciones import MetodoDeteccionSecciones
from app.bd.modelos import VersionBorrador
from app.borradores.extraccion import Origen, ParrafoBorrador, TextoBorrador, extraer_parrafos
from app.borradores.secciones import (
    ListaReferencias,
    Seccion,
    SeccionesVersion,
    TituloMarcado,
    detectar_por_estilos,
    marcar_a_mano,
    referencias_a_mano,
)
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
MENSAJE_SIN_ESTILOS = (
    "No se detectaron títulos con estilo. Marque los títulos de sus secciones para poder"
    " pedir revisiones por sección."
)


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
    metodo_deteccion: MetodoDeteccionSecciones | None  # None: sin secciones marcadas
    secciones: int
    referencias: int  # entradas de la lista de referencias

    @classmethod
    def con_detalle(cls, version: VersionBorrador, hitos: Sequence[Hito]) -> VersionDetalle:
        resumen = VersionResumen.desde(version, hitos)
        secciones = secciones_de(version)
        return cls(
            **resumen.model_dump(),
            huella_sha256=version.huella_sha256,
            parrafos=len(version.parrafos),
            metodo_deteccion=version.metodo_deteccion,
            secciones=len(secciones.secciones) if secciones else 0,
            referencias=len(secciones.referencias.entradas)
            if secciones and secciones.referencias
            else 0,
        )


class ParrafoVista(BaseModel):
    id: str
    texto: str
    origen: Origen
    seccion: str | None
    es_titulo: bool


class VistaSecciones(BaseModel):
    """Secciones y párrafos de una versión, para que el caso elija el alcance (F-05)."""

    version_id: str
    metodo_deteccion: MetodoDeteccionSecciones | None
    titulo_documento: str | None
    secciones: list[Seccion]
    parrafos: list[ParrafoVista]
    referencias: ListaReferencias | None
    mensajes: list[str]

    @classmethod
    def desde(cls, version: VersionBorrador) -> VistaSecciones:
        secciones = secciones_de(version)
        lista = secciones.secciones if secciones else []
        seccion_de = {pid: s.id for s in lista for pid in (s.parrafo_titulo, *s.parrafos)}
        titulos = {s.parrafo_titulo for s in lista}
        return cls(
            version_id=str(version.id),
            metodo_deteccion=version.metodo_deteccion,
            titulo_documento=secciones.titulo_documento if secciones else None,
            secciones=lista,
            parrafos=[
                ParrafoVista(
                    id=p.id,
                    texto=p.texto,
                    origen=p.origen,
                    seccion=seccion_de.get(p.id),
                    es_titulo=p.id in titulos,
                )
                for p in parrafos_de(version)
            ],
            referencias=secciones.referencias if secciones else None,
            mensajes=[] if lista else [MENSAJE_SIN_ESTILOS],
        )


def parrafos_de(version: VersionBorrador) -> list[ParrafoBorrador]:
    return [ParrafoBorrador.model_validate(p) for p in version.parrafos]


def secciones_de(version: VersionBorrador) -> SeccionesVersion | None:
    if version.secciones is None:
        return None
    return SeccionesVersion.model_validate(version.secciones)


class VersionInexistente(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__("no_existe", "La versión solicitada no existe.", estado_http=404)


class VersionEnUso(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "version_en_uso",
            "Esta versión ya tiene solicitudes: sus secciones no pueden cambiar.",
            estado_http=409,
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

        secciones = detectar_por_estilos(texto.parrafos)
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
                secciones=secciones.model_dump() if secciones else None,
                metodo_deteccion=MetodoDeteccionSecciones.ESTILOS if secciones else None,
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
                "secciones": len(secciones.secciones) if secciones else 0,
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
        elif secciones is None:
            mensajes.append(MENSAJE_SIN_ESTILOS)
        return ResultadoCarga(
            version=VersionDetalle.con_detalle(version, parametros.hitos),
            primera_del_hito=anterior is None,
            mensajes=mensajes,
        )

    async def _modificable(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, version_id: uuid.UUID
    ) -> VersionBorrador:
        version = await unidad.versiones.con_parrafos(contexto, version_id)
        if version is None:
            raise VersionInexistente()
        if await unidad.solicitudes.hay_de_version(contexto, version.id):
            raise VersionEnUso()  # el alcance de una solicitud se refiere a estos ids (RNF-01)
        return version

    async def marcar_secciones(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        version_id: uuid.UUID,
        titulos: Sequence[TituloMarcado],
    ) -> VistaSecciones:
        """Secciones marcadas a mano (respaldo sin estilos, T12-01, apartado 3)."""
        version = await self._modificable(unidad, contexto, version_id)
        secciones = marcar_a_mano(parrafos_de(version), titulos)
        version.secciones = secciones.model_dump()
        version.metodo_deteccion = MetodoDeteccionSecciones.MANUAL
        await unidad.confirmar()
        self._registrar_cambio(contexto, version, "secciones marcadas a mano")
        return VistaSecciones.desde(version)

    async def marcar_referencias(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        version_id: uuid.UUID,
        desde: str,
        hasta: str | None,
    ) -> VistaSecciones:
        """Lista de referencias indicada a mano (T12-01, apartado 4)."""
        version = await self._modificable(unidad, contexto, version_id)
        secciones = referencias_a_mano(secciones_de(version), parrafos_de(version), desde, hasta)
        version.secciones = secciones.model_dump()
        await unidad.confirmar()
        self._registrar_cambio(contexto, version, "referencias marcadas a mano")
        return VistaSecciones.desde(version)

    @staticmethod
    def _registrar_cambio(contexto: ContextoAcceso, version: VersionBorrador, evento: str) -> None:
        secciones = secciones_de(version)
        _registro.info(
            evento,
            extra={
                "tipo_evento": "borrador",
                "caso_id": str(contexto.caso_exigido()),
                "version_id": str(version.id),
                "secciones": len(secciones.secciones) if secciones else 0,
                "referencias": len(secciones.referencias.entradas)
                if secciones and secciones.referencias
                else 0,
            },
        )
