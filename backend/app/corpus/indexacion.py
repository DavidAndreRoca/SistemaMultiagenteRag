"""Indexación y gestión del corpus científico (T10; RF-15, CU-14, CP-21; Fase 1, 18).

* ``ingerir``: idempotente por la huella del archivo. Un archivo ya indexado o ya
  excluido en la colección no se vuelve a procesar ni a registrar.
* ``indexar``: lleva un ``DocumentoProcesado`` (T09) a la base.
  - Un excluido se registra con su motivo.
  - Un duplicado (mismo texto normalizado o mismo DOI que un documento de la colección,
    18.9) se registra como exclusión ``duplicado``.
  - Un incompleto se guarda con sus fragmentos pero sin vectores hasta que el
    investigador lo confirme (18.3).
  - Un procesado se embebe con el servicio de modelos y queda recuperable.
* ``confirmar`` y ``retirar``: un retirado deja de recuperarse y conserva sus fragmentos
  para la trazabilidad (18.9).
* ``reindexar``: vuelve a embeber lo indexado con otro modelo o revisión (18.5, RNF-21).

Solo se gestionan colecciones científicas: las guías se segmentan por apartado (T22) y
las colecciones personales reciben aportes de los casos (T32). Por eso, en T10, ninguna
vía indexa en el corpus de guías y la rúbrica no puede entrar en él (RN-11).

El registro guarda estados y cantidades, nunca texto del documento (4.6, RN-23).
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from app.bd.enumeraciones import (
    EstadoDocumento,
    MotivoExclusionCorpus,
    ObjetoExclusion,
    OrigenDocumento,
    TipoColeccion,
)
from app.bd.modelos import Coleccion, Documento, ExclusionCorpus, Fragmento
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.corpus.almacen import AlmacenArchivos
from app.corpus.esquemas import (
    MENSAJES_MOTIVO,
    DocumentoProcesado,
    EstadoProcesamiento,
    MotivoExclusion,
)
from app.corpus.extraccion import ParametrosCanal
from app.corpus.validacion import huella
from app.inferencia.interfaces import IdentidadModelo, ProveedorEmbeddings
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo

LARGO_MAXIMO_NOMBRE = 255

_registro = obtener_registrador("corpus")


class ProcesadorPdf(Protocol):
    """El canal de T09 (``CanalPdf``) o un doble de prueba."""

    def con_parametros(self, parametros: ParametrosCanal) -> ProcesadorPdf: ...

    def procesar_pdf(self, ruta: Path) -> DocumentoProcesado: ...


class Resultado(StrEnum):
    INDEXADO = "indexado"
    INCOMPLETO = "incompleto"  # guardado; se indexa si el investigador lo confirma
    EXCLUIDO = "excluido"
    DUPLICADO = "duplicado"
    YA_REGISTRADO = "ya_registrado"  # el mismo archivo ya se procesó en la colección


class ResultadoIngesta(BaseModel):
    archivo: str
    resultado: Resultado
    documento_id: uuid.UUID | None = None
    motivos: list[str] = []
    mensajes: list[str] = []
    fragmentos: int = 0


MENSAJE_DUPLICADO = "La colección ya tiene un documento con el mismo texto o el mismo DOI."
MENSAJE_YA_REGISTRADO = "Este archivo ya se procesó en la colección; no se repite."


class ColeccionNoAdmitida(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__(
            "coleccion_no_admitida",
            "En esta etapa solo se indexan documentos en colecciones científicas de un tema.",
            estado_http=422,
        )


class RecursoInexistente(ErrorAplicacion):
    def __init__(self) -> None:
        super().__init__("no_existe", "El recurso solicitado no existe.", estado_http=404)


class EstadoNoPermite(ErrorAplicacion):
    def __init__(self, mensaje: str) -> None:
        super().__init__("estado_no_permite", mensaje, estado_http=409)


def nombre_seguro(nombre: str | None) -> str:
    """Solo el nombre, sin rutas, recortado; es un dato que se muestra, nunca una ruta."""
    base = Path((nombre or "").replace("\\", "/")).name.strip()
    return (base or "documento.pdf")[:LARGO_MAXIMO_NOMBRE]


class Indexador:
    def __init__(
        self,
        procesador: ProcesadorPdf | None,
        embeddings: ProveedorEmbeddings,
        almacen: AlmacenArchivos | None,
    ) -> None:
        """``procesador`` y ``almacen`` pueden faltar si solo se reindexa."""
        self._procesador = procesador
        self._embeddings = embeddings
        self._almacen = almacen
        # Docling ocupa más de 1 GB al convertir: un PDF a la vez por proceso.
        self._candado = threading.Lock()

    def _procesar(self, ruta: Path, parametros: ParametrosCanal) -> DocumentoProcesado:
        assert self._procesador is not None, "indexador creado sin canal de extracción"
        with self._candado:
            return self._procesador.con_parametros(parametros).procesar_pdf(ruta)

    async def ingerir(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        coleccion: Coleccion,
        ruta: Path,
        archivo_original: str | None = None,
    ) -> ResultadoIngesta:
        """Procesa e indexa un PDF con los parámetros de la configuración vigente."""
        exigir_cientifica(coleccion)
        _, vigentes = await unidad.configuracion.vigente()
        parametros = ParametrosCanal.desde(vigentes)
        nombre = nombre_seguro(archivo_original or ruta.name)
        huella_archivo = await asyncio.to_thread(lambda: huella(ruta.read_bytes()))
        previo = await unidad.corpus.registrado_por_archivo(contexto, coleccion.id, huella_archivo)
        if previo is not None:
            return self._informar(
                coleccion,
                ResultadoIngesta(
                    archivo=nombre,
                    resultado=Resultado.YA_REGISTRADO,
                    documento_id=previo.id if isinstance(previo, Documento) else None,
                    mensajes=[MENSAJE_YA_REGISTRADO],
                ),
            )
        procesado = await asyncio.to_thread(self._procesar, ruta, parametros)
        return await self.indexar(
            unidad, contexto, coleccion, procesado, ruta=ruta, archivo_original=nombre
        )

    async def indexar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        coleccion: Coleccion,
        procesado: DocumentoProcesado,
        *,
        ruta: Path,
        archivo_original: str,
    ) -> ResultadoIngesta:
        exigir_cientifica(coleccion)
        if procesado.estado is EstadoProcesamiento.EXCLUIDO:
            assert procesado.motivo_exclusion is not None
            await self._excluir(
                unidad,
                contexto,
                coleccion,
                archivo_original,
                procesado.huella_archivo,
                MotivoExclusionCorpus(procesado.motivo_exclusion.value),
            )
            return self._informar(
                coleccion,
                ResultadoIngesta(
                    archivo=archivo_original,
                    resultado=Resultado.EXCLUIDO,
                    motivos=[procesado.motivo_exclusion.value],
                    mensajes=procesado.mensajes,
                ),
            )

        assert procesado.huella_texto is not None
        doi = procesado.metadatos.doi if procesado.metadatos else None
        original = await unidad.corpus.duplicado(
            contexto, coleccion.id, procesado.huella_texto, doi
        )
        if original is not None:
            await self._excluir(
                unidad,
                contexto,
                coleccion,
                archivo_original,
                procesado.huella_archivo,
                MotivoExclusionCorpus.DUPLICADO,
                duplicado_de=original,
            )
            return self._informar(
                coleccion,
                ResultadoIngesta(
                    archivo=archivo_original,
                    resultado=Resultado.DUPLICADO,
                    documento_id=original.id,
                    motivos=[MotivoExclusionCorpus.DUPLICADO.value],
                    mensajes=[MENSAJE_DUPLICADO],
                ),
            )

        completo = procesado.estado is EstadoProcesamiento.PROCESADO
        vectores: list[list[float]] | None = None
        identidad: IdentidadModelo | None = None
        if completo:
            embebidos = await self._embeddings.embeber([f.texto for f in procesado.fragmentos])
            vectores, identidad = embebidos.vectores, embebidos.identidad

        documento = _documento(coleccion, procesado, archivo_original, contexto, identidad)
        fragmentos = [
            Fragmento(
                orden=f.orden,
                texto=f.texto,
                seccion_normalizada=f.seccion_normalizada,
                seccion_original=f.seccion_original,
                pagina_inicio=f.pagina_inicio,
                pagina_fin=f.pagina_fin,
                tokens=f.tokens,
                embedding=vectores[i] if vectores is not None else None,
            )
            for i, f in enumerate(procesado.fragmentos)
        ]
        almacen = self._almacen
        assert almacen is not None, "indexador creado sin almacén"
        guardado = await asyncio.to_thread(almacen.guardar, ruta)
        documento.ruta_archivo = guardado
        try:
            await unidad.corpus.agregar_documento(contexto, documento, fragmentos)
            await unidad.corpus.recontar(contexto, coleccion)
            await unidad.confirmar()
        except BaseException:
            await unidad.revertir()
            almacen.borrar(guardado)
            raise
        return self._informar(
            coleccion,
            ResultadoIngesta(
                archivo=archivo_original,
                resultado=Resultado.INDEXADO if completo else Resultado.INCOMPLETO,
                documento_id=documento.id,
                motivos=[m.value for m in procesado.motivos_incompleto],
                mensajes=procesado.mensajes,
                fragmentos=len(fragmentos),
            ),
        )

    async def _excluir(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        coleccion: Coleccion,
        archivo_original: str,
        huella_archivo: str,
        motivo: MotivoExclusionCorpus,
        duplicado_de: Documento | None = None,
    ) -> None:
        await unidad.corpus.agregar_exclusion(
            contexto,
            ExclusionCorpus(
                coleccion_id=coleccion.id,
                objeto=ObjetoExclusion.ARCHIVO,
                identificador=archivo_original,
                huella_archivo=huella_archivo,
                motivo=motivo,
                duplicado_de_id=duplicado_de.id if duplicado_de else None,
                registrado_por_id=contexto.cuenta_id,
            ),
        )
        await unidad.corpus.recontar(contexto, coleccion)
        await unidad.confirmar()

    @staticmethod
    def _informar(coleccion: Coleccion, resultado: ResultadoIngesta) -> ResultadoIngesta:
        _registro.info(
            "ingesta de documento",
            extra={
                "tipo_evento": "corpus",
                "coleccion_id": str(coleccion.id),
                "resultado": resultado.resultado.value,
                "motivos": resultado.motivos,
                "fragmentos": resultado.fragmentos,
            },
        )
        return resultado

    async def confirmar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        documento_id: uuid.UUID,
        ahora: datetime,
    ) -> Documento:
        """Indexa un documento incompleto: se embebe y conserva su marca (18.3)."""
        documento, coleccion = await _documento_gestionable(unidad, contexto, documento_id)
        if documento.estado is not EstadoDocumento.INCOMPLETO or documento.confirmado_en:
            raise EstadoNoPermite("Solo se confirma un documento incompleto aún sin confirmar.")
        fragmentos = await unidad.corpus.fragmentos(contexto, documento)
        identidad = await self._embeber(fragmentos)
        documento.confirmado_en = ahora
        documento.confirmado_por_id = contexto.cuenta_id
        documento.modelo_embeddings = identidad.modelo
        documento.revision_embeddings = identidad.revision
        await unidad.corpus.recontar(contexto, coleccion)
        await unidad.confirmar()
        _registro.info(
            "documento confirmado",
            extra={"tipo_evento": "corpus", "documento_id": str(documento.id)},
        )
        return documento

    @staticmethod
    async def retirar(
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        documento_id: uuid.UUID,
        ahora: datetime,
    ) -> Documento:
        """Deja de recuperarse; sus fragmentos se conservan para la trazabilidad (18.9)."""
        documento, coleccion = await _documento_gestionable(unidad, contexto, documento_id)
        if documento.estado is EstadoDocumento.RETIRADO:
            raise EstadoNoPermite("El documento ya está retirado.")
        documento.estado = EstadoDocumento.RETIRADO
        documento.retirado_en = ahora
        await unidad.corpus.recontar(contexto, coleccion)
        await unidad.confirmar()
        _registro.info(
            "documento retirado",
            extra={
                "tipo_evento": "corpus",
                "documento_id": str(documento.id),
                "cuenta_id": str(contexto.cuenta_id),
            },
        )
        return documento

    async def reindexar(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, *, forzar: bool = False
    ) -> int:
        """Vuelve a embeber los documentos recuperables con otro modelo o revisión.

        Devuelve cuántos documentos se reindexaron. Cada documento se confirma por
        separado: si el servicio se cae a mitad, lo hecho queda y lo demás se retoma.
        """
        contexto.exigir_investigador()
        actual = (await self._embeddings.embeber(["reindexacion"])).identidad
        documentos = await unidad.corpus.por_reindexar(
            contexto, actual.modelo, actual.revision, forzar
        )
        for documento in documentos:
            identidad = await self._embeber(await unidad.corpus.fragmentos(contexto, documento))
            documento.modelo_embeddings = identidad.modelo
            documento.revision_embeddings = identidad.revision
            await unidad.confirmar()
        _registro.info(
            "corpus reindexado",
            extra={"tipo_evento": "corpus", "documentos": len(documentos), "forzar": forzar},
        )
        return len(documentos)

    async def _embeber(self, fragmentos: Sequence[Fragmento]) -> IdentidadModelo:
        if not fragmentos:
            return (await self._embeddings.embeber(["vacio"])).identidad
        embebidos = await self._embeddings.embeber([f.texto for f in fragmentos])
        for fragmento, vector in zip(fragmentos, embebidos.vectores, strict=True):
            fragmento.embedding = vector
        return embebidos.identidad


def exigir_cientifica(coleccion: Coleccion) -> None:
    if coleccion.tipo is not TipoColeccion.CIENTIFICA:
        raise ColeccionNoAdmitida()


async def _documento_gestionable(
    unidad: UnidadDeTrabajo, contexto: ContextoAcceso, documento_id: uuid.UUID
) -> tuple[Documento, Coleccion]:
    documento = await unidad.corpus.documento(contexto, documento_id)
    coleccion = (
        await unidad.corpus.coleccion(contexto, documento.coleccion_id) if documento else None
    )
    if documento is None or coleccion is None or coleccion.tipo is not TipoColeccion.CIENTIFICA:
        raise RecursoInexistente()
    return documento, coleccion


def _documento(
    coleccion: Coleccion,
    procesado: DocumentoProcesado,
    archivo_original: str,
    contexto: ContextoAcceso,
    identidad: IdentidadModelo | None,
) -> Documento:
    metadatos = procesado.metadatos
    completo = procesado.estado is EstadoProcesamiento.PROCESADO
    assert procesado.huella_texto is not None
    return Documento(
        id=uuid.uuid4(),
        coleccion_id=coleccion.id,
        titulo=metadatos.titulo if metadatos else None,
        autores=[a.model_dump() for a in metadatos.autores] if metadatos else [],
        anio=metadatos.anio if metadatos else None,
        doi=metadatos.doi if metadatos else None,
        revista_editorial=metadatos.revista if metadatos else None,
        idioma=metadatos.idioma if metadatos else None,
        huella_sha256=procesado.huella_texto,
        estado=EstadoDocumento.ACTIVO if completo else EstadoDocumento.INCOMPLETO,
        motivo_estado=", ".join(m.value for m in procesado.motivos_incompleto) or None,
        origen=OrigenDocumento.INGESTA,
        num_paginas=procesado.num_paginas,
        huella_archivo=procesado.huella_archivo,
        archivo_original=archivo_original,
        indexado_por_id=contexto.cuenta_id,
        modelo_embeddings=identidad.modelo if identidad else None,
        revision_embeddings=identidad.revision if identidad else None,
    )


def mensaje_de_motivo(motivo: MotivoExclusionCorpus) -> str:
    """Mensaje legible de un motivo de exclusión guardado."""
    if motivo is MotivoExclusionCorpus.DUPLICADO:
        return MENSAJE_DUPLICADO
    if motivo is MotivoExclusionCorpus.SIN_ACCESO_ABIERTO:
        return "La referencia no tiene una versión de acceso abierto (RN-14)."
    return MENSAJES_MOTIVO[MotivoExclusion(motivo.value)]
