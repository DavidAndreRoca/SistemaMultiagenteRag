"""Importador de referencias del artículo O1 (T15-01; RF-20, RN-14, RN-18, RN-19).

Una importación corre en segundo plano, una a la vez por proceso (Docling ocupa más de
1 GB). El archivo del artículo vive solo en ``DIRECTORIO_ARCHIVOS/importacion/<id>/`` y
se borra en cuanto se extraen sus referencias, antes de resolver ninguna, también si la
extracción falla (RN-19). El artículo nunca pasa por el indexador.

El registro guarda estados y cantidades, nunca el texto del artículo ni de las
referencias (4.6).
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.bd.enumeraciones import (
    EstadoAccesoAbierto,
    EstadoImportacion,
    EstadoReferencia,
    MotivoExclusionCorpus,
    ObjetoExclusion,
    OrigenDocumento,
    OrigenImportacion,
)
from app.bd.modelos import Coleccion, ExclusionCorpus, ImportacionReferencias, ReferenciaImportada
from app.bibliografia.interfaces import ServicioBibliografico
from app.bibliografia.modelos import Estado, MetadatosBibliograficos
from app.bibliografia.normalizacion import normalizar
from app.comun.registro import obtener_registrador
from app.corpus.grobid import ReferenciaGrobid
from app.corpus.indexacion import (
    EstadoNoPermite,
    Indexador,
    RecursoInexistente,
    Resultado,
    ResultadoIngesta,
)
from app.corpus.validacion import LimitesPdf
from app.importacion.descarga import Descargador
from app.importacion.extraccion import (
    ErrorImportacion,
    ExtractorReferencias,
    referencias_de_dois,
    referencias_del_archivo,
)
from app.importacion.resolucion import Localizacion, Localizador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import FabricaUnidades, UnidadDeTrabajo

CARPETA = "importacion"
BYTES_POR_MB = 1024 * 1024
# Motivos que se registran también como exclusión de referencia en el informe (RF-15).
MOTIVOS_DE_REFERENCIA = frozenset(
    {
        MotivoExclusionCorpus.NO_LOCALIZADA,
        MotivoExclusionCorpus.SIN_DOI,
        MotivoExclusionCorpus.SIN_ACCESO_ABIERTO,
        MotivoExclusionCorpus.DOI_INVALIDO,
    }
)
FINALES = frozenset({EstadoReferencia.INCLUIDA, EstadoReferencia.EXCLUIDA})
SIN_ENLACE_DIRECTO = "sin_enlace_directo"
ERROR_AL_INDEXAR = "error_al_indexar"

_registro = obtener_registrador("importacion")


@dataclass(frozen=True)
class Entrada:
    """Lo que pidió el investigador: un archivo ya guardado en la carpeta de la
    importación o el texto de la lista de DOI (que no se guarda)."""

    origen: OrigenImportacion
    ruta: Path | None = None
    nombre: str | None = None  # solo aporta la extensión; no se guarda
    tipo: str | None = None
    dois: str | None = None


@dataclass
class Desenlace:
    estado: EstadoReferencia
    motivo: str | None = None
    documento_id: uuid.UUID | None = None
    metadatos: MetadatosBibliograficos | None = None
    estado_oa: str | None = None
    url_acceso_abierto: str | None = None
    url_pdf: str | None = None
    licencia: str | None = None


@dataclass
class Avance:
    activas: set[uuid.UUID] = field(default_factory=set)
    tareas: set[asyncio.Task[None]] = field(default_factory=set)


def clave_de(referencia: ReferenciaGrobid) -> str:
    if referencia.doi:
        return f"doi:{referencia.doi}"[:300]
    huella = hashlib.sha256(normalizar(referencia.texto).encode("utf-8")).hexdigest()
    return f"texto:{huella}"


def carpeta_de(directorio: Path, importacion_id: uuid.UUID) -> Path:
    return directorio / CARPETA / str(importacion_id)


def purgar(directorio: Path) -> int:
    """Borra lo que haya quedado de importaciones anteriores (RN-19). Devuelve cuántas."""
    base = directorio / CARPETA
    if not base.is_dir():
        return 0
    restos = list(base.iterdir())
    for resto in restos:
        if resto.is_dir():
            shutil.rmtree(resto, ignore_errors=True)
        else:
            resto.unlink(missing_ok=True)
    return len(restos)


class Importador:
    def __init__(
        self,
        *,
        extractor: ExtractorReferencias,
        localizador: Localizador,
        unpaywall: ServicioBibliografico,
        descargador: Descargador,
        indexador: Indexador,
        abrir: FabricaUnidades,
        directorio: Path,
        reloj: Callable[[], datetime],
    ) -> None:
        self._extractor = extractor
        self._localizador = localizador
        self._unpaywall = unpaywall
        self._descargador = descargador
        self._indexador = indexador
        self._abrir = abrir
        self._directorio = directorio
        self._reloj = reloj
        self._candado = asyncio.Lock()
        self._avance = Avance()

    @property
    def activas(self) -> frozenset[uuid.UUID]:
        return frozenset(self._avance.activas)

    def carpeta(self, importacion_id: uuid.UUID) -> Path:
        carpeta = carpeta_de(self._directorio, importacion_id)
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def lanzar(self, importacion_id: uuid.UUID, contexto: ContextoAcceso, entrada: Entrada) -> None:
        """Sigue la importación en segundo plano; la petición ya respondió 202."""
        self._avance.activas.add(importacion_id)
        tarea = asyncio.create_task(self.ejecutar(importacion_id, contexto, entrada))
        self._avance.tareas.add(tarea)
        tarea.add_done_callback(self._avance.tareas.discard)

    def cancelar(self) -> None:
        """Al apagar: las importaciones cortadas se marcan interrumpidas en la próxima
        consulta y sus archivos se borran al arrancar (RN-19)."""
        for tarea in list(self._avance.tareas):
            tarea.cancel()

    async def esperar(self) -> None:
        """Espera las importaciones lanzadas (pruebas y apagado)."""
        while self._avance.tareas:
            await asyncio.gather(*list(self._avance.tareas), return_exceptions=True)

    async def ejecutar(
        self, importacion_id: uuid.UUID, contexto: ContextoAcceso, entrada: Entrada
    ) -> None:
        self._avance.activas.add(importacion_id)
        try:
            async with self._candado, self._abrir() as unidad:
                await self._ejecutar(unidad, importacion_id, contexto, entrada)
        except Exception:
            _registro.exception(
                "importacion fallida",
                extra={"tipo_evento": "importacion", "importacion_id": str(importacion_id)},
            )
            async with self._abrir() as unidad:
                importacion = await unidad.importacion.obtener(contexto, importacion_id)
                if importacion is not None:
                    importacion.estado = EstadoImportacion.FALLIDA
                    importacion.error = "error_interno"
                    importacion.terminada_en = self._reloj()
                    await unidad.confirmar()
        finally:
            self._borrar_carpeta(importacion_id)
            self._avance.activas.discard(importacion_id)

    async def _ejecutar(
        self,
        unidad: UnidadDeTrabajo,
        importacion_id: uuid.UUID,
        contexto: ContextoAcceso,
        entrada: Entrada,
    ) -> None:
        importacion = await unidad.importacion.obtener(contexto, importacion_id)
        if importacion is None:
            return
        coleccion = await unidad.corpus.coleccion(contexto, importacion.coleccion_id)
        assert coleccion is not None
        importacion.estado = EstadoImportacion.EN_PROCESO
        importacion.iniciada_en = self._reloj()
        await unidad.confirmar()

        try:
            referencias, invalidas = await self._extraer(unidad, entrada)
        except ErrorImportacion as error:
            importacion.estado = EstadoImportacion.FALLIDA
            importacion.error = error.codigo[:60]
            importacion.terminada_en = self._reloj()
            await unidad.confirmar()
            self._informar(importacion)
            return
        finally:
            # RN-19: el artículo se borra antes de resolver ninguna referencia.
            self._borrar_carpeta(importacion_id)

        importacion.total = len(referencias) + len(invalidas)
        await unidad.confirmar()
        for texto in invalidas:
            invalida = ReferenciaGrobid(texto=texto)
            previa = await unidad.importacion.referencia_por_clave(
                contexto, coleccion.id, clave_de(invalida)
            )
            if previa is None:
                await self._guardar(
                    unidad,
                    contexto,
                    coleccion,
                    importacion,
                    invalida,
                    Desenlace(EstadoReferencia.EXCLUIDA, MotivoExclusionCorpus.DOI_INVALIDO.value),
                )
            else:
                previa.importacion_id = importacion.id
            importacion.procesadas += 1
            await unidad.confirmar()
        for referencia in referencias:
            await self._tratar(unidad, contexto, coleccion, importacion, referencia)
        importacion = await unidad.importacion.obtener(contexto, importacion_id)
        assert importacion is not None
        importacion.estado = EstadoImportacion.TERMINADA
        importacion.terminada_en = self._reloj()
        await unidad.corpus.recontar(contexto, coleccion)
        await unidad.confirmar()
        self._informar(importacion)

    async def _extraer(
        self, unidad: UnidadDeTrabajo, entrada: Entrada
    ) -> tuple[list[ReferenciaGrobid], list[str]]:
        if entrada.origen is OrigenImportacion.DOI:
            referencias, invalidas = referencias_de_dois(entrada.dois or "")
            if not referencias and not invalidas:
                raise ErrorImportacion("sin_referencias", "La lista de DOI está vacía.")
            return referencias, invalidas
        assert entrada.ruta is not None
        _, parametros = await unidad.configuracion.vigente()
        limites = LimitesPdf(parametros.tamano_max_pdf_mb, parametros.paginas_max_pdf)
        referencias = await asyncio.to_thread(
            referencias_del_archivo,
            entrada.ruta,
            entrada.origen,
            entrada.nombre,
            entrada.tipo,
            self._extractor,
            limites,
        )
        return referencias, []

    async def _tratar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        coleccion: Coleccion,
        importacion: ImportacionReferencias,
        referencia: ReferenciaGrobid,
    ) -> None:
        importacion_id, coleccion_id = importacion.id, coleccion.id
        previa = await unidad.importacion.referencia_por_clave(
            contexto, coleccion_id, clave_de(referencia)
        )
        if previa is not None and previa.estado in FINALES:
            previa.importacion_id = importacion_id  # se cuenta, pero no se vuelve a procesar
            desenlace = None
        else:
            try:
                desenlace = await self._resolver(unidad, contexto, coleccion, referencia)
            except Exception:
                _registro.exception(
                    "referencia no resuelta",
                    extra={"tipo_evento": "importacion", "importacion_id": str(importacion_id)},
                )
                await unidad.revertir()  # vence los objetos cargados: se vuelven a leer
                desenlace = Desenlace(EstadoReferencia.NO_COMPROBABLE, ERROR_AL_INDEXAR)
        actual = await unidad.importacion.obtener(contexto, importacion_id)
        recargada = await unidad.corpus.coleccion(contexto, coleccion_id)
        assert actual is not None and recargada is not None
        coleccion = recargada
        if desenlace is not None:
            await self._guardar(unidad, contexto, coleccion, actual, referencia, desenlace)
        actual.procesadas = min(actual.procesadas + 1, actual.total)
        await unidad.confirmar()

    async def _resolver(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        coleccion: Coleccion,
        referencia: ReferenciaGrobid,
    ) -> Desenlace:
        localizacion = await self._localizador.localizar(referencia)
        if localizacion.localizacion is Localizacion.NO_COMPROBABLE:
            return Desenlace(EstadoReferencia.NO_COMPROBABLE, localizacion.motivo)
        if localizacion.localizacion is Localizacion.NO_LOCALIZADA:
            return Desenlace(EstadoReferencia.EXCLUIDA, MotivoExclusionCorpus.NO_LOCALIZADA.value)
        metadatos = localizacion.metadatos
        assert metadatos is not None
        doi = metadatos.doi or referencia.doi
        if not doi:
            return Desenlace(
                EstadoReferencia.EXCLUIDA, MotivoExclusionCorpus.SIN_DOI.value, metadatos=metadatos
            )
        metadatos = metadatos.model_copy(update={"doi": doi})

        existente = await unidad.importacion.documento_por_doi(contexto, coleccion.id, doi)
        if existente is not None:
            return Desenlace(
                EstadoReferencia.INCLUIDA,
                documento_id=existente.id,
                metadatos=metadatos,
                estado_oa=existente.estado_oa.value,
                url_acceso_abierto=existente.url_acceso_abierto,
                licencia=existente.licencia,
            )

        acceso = await self._unpaywall.por_doi(doi)
        if acceso.estado is Estado.NO_COMPROBABLE:
            motivo = acceso.motivo.value if acceso.motivo else "sin_respuesta"
            return Desenlace(
                EstadoReferencia.NO_COMPROBABLE,
                f"{acceso.servicio.value}_{motivo}"[:60],
                metadatos=metadatos,
            )
        abierto = acceso.acceso_abierto
        if acceso.estado is Estado.NO_ENCONTRADO:
            # Sin registro en Unpaywall (DOI de DataCite): vale el de OpenAlex, si lo dio.
            abierto = localizacion.acceso_abierto
        if abierto is None or not abierto.es_abierto:
            return Desenlace(
                EstadoReferencia.EXCLUIDA,
                MotivoExclusionCorpus.SIN_ACCESO_ABIERTO.value,
                metadatos=metadatos,
                estado_oa=abierto.estado if abierto else None,
            )
        desenlace = Desenlace(
            EstadoReferencia.PENDIENTE_PDF,
            SIN_ENLACE_DIRECTO,
            metadatos=metadatos,
            estado_oa=abierto.estado,
            url_acceso_abierto=abierto.url,
            url_pdf=abierto.url_pdf,
            licencia=abierto.licencia,
        )
        if not abierto.url_pdf:
            return desenlace

        _, parametros = await unidad.configuracion.vigente()
        ruta = self.carpeta(uuid.uuid4()) / "descarga.pdf"
        try:
            falla = await self._descargador.descargar(
                abierto.url_pdf, ruta, parametros.tamano_max_pdf_mb * BYTES_POR_MB
            )
            if falla is not None:
                desenlace.motivo = falla
                return desenlace
            resultado = await self._indexador.ingerir(
                unidad, contexto, coleccion, ruta, doi.replace("/", "_") + ".pdf"
            )
        finally:
            shutil.rmtree(ruta.parent, ignore_errors=True)
        return await self._tras_ingerir(unidad, contexto, resultado, desenlace)

    async def _tras_ingerir(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        resultado: ResultadoIngesta,
        desenlace: Desenlace,
    ) -> Desenlace:
        if resultado.documento_id is None:
            desenlace.estado = EstadoReferencia.EXCLUIDA
            desenlace.motivo = (resultado.motivos or [resultado.resultado.value])[0][:60]
            return desenlace
        desenlace.estado = EstadoReferencia.INCLUIDA
        desenlace.motivo = None
        desenlace.documento_id = resultado.documento_id
        if resultado.resultado in (Resultado.INDEXADO, Resultado.INCOMPLETO):
            await self._completar_documento(unidad, contexto, desenlace)
        return desenlace

    @staticmethod
    async def _completar_documento(
        unidad: UnidadDeTrabajo, contexto: ContextoAcceso, desenlace: Desenlace
    ) -> None:
        """Metadatos de Crossref y de acceso abierto en el documento recién indexado."""
        assert desenlace.documento_id is not None
        documento = await unidad.corpus.documento(contexto, desenlace.documento_id)
        assert documento is not None
        documento.origen = OrigenDocumento.IMPORTACION_O1
        metadatos = desenlace.metadatos
        if metadatos is not None:
            documento.doi = metadatos.doi or documento.doi
            documento.titulo = metadatos.titulo or documento.titulo
            autores = [
                {"nombres": a.nombres, "apellidos": apellidos}
                for a in metadatos.autores
                if (apellidos := a.apellidos_para_comparar())
            ]
            documento.autores = autores or documento.autores
            if metadatos.anio and 1500 <= metadatos.anio <= 2100:
                documento.anio = metadatos.anio
            documento.revista_editorial = metadatos.revista or documento.revista_editorial
        documento.licencia = (desenlace.licencia or "")[:80] or documento.licencia
        documento.url_acceso_abierto = desenlace.url_acceso_abierto or desenlace.url_pdf
        documento.estado_oa = _estado_oa(desenlace.estado_oa)
        await unidad.confirmar()

    async def _guardar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        coleccion: Coleccion,
        importacion: ImportacionReferencias,
        referencia: ReferenciaGrobid,
        desenlace: Desenlace,
    ) -> ReferenciaImportada:
        clave = clave_de(referencia)
        fila = await unidad.importacion.referencia_por_clave(contexto, coleccion.id, clave)
        if fila is None:
            fila = ReferenciaImportada(
                coleccion_id=coleccion.id, clave=clave, texto=referencia.texto, autores=[]
            )
        self._aplicar(fila, importacion, referencia, desenlace)
        await unidad.importacion.agregar_referencia(contexto, fila)
        motivo = desenlace.motivo
        if desenlace.estado is EstadoReferencia.EXCLUIDA and motivo in MOTIVOS_DE_REFERENCIA:
            await unidad.corpus.agregar_exclusion(
                contexto,
                ExclusionCorpus(
                    coleccion_id=coleccion.id,
                    objeto=ObjetoExclusion.REFERENCIA,
                    identificador=fila.doi or fila.texto,
                    motivo=MotivoExclusionCorpus(motivo),
                    registrado_por_id=contexto.cuenta_id,
                ),
            )
        return fila

    def _aplicar(
        self,
        fila: ReferenciaImportada,
        importacion: ImportacionReferencias,
        referencia: ReferenciaGrobid,
        desenlace: Desenlace,
    ) -> None:
        metadatos = desenlace.metadatos
        fila.importacion_id = importacion.id
        fila.estado = desenlace.estado
        fila.motivo = desenlace.motivo
        fila.documento_id = desenlace.documento_id
        fila.doi = (metadatos.doi if metadatos else None) or referencia.doi or fila.doi
        fila.titulo = (metadatos.titulo if metadatos else None) or referencia.titulo or fila.titulo
        apellidos = (
            [a for x in metadatos.autores if (a := x.apellidos_para_comparar())]
            if metadatos
            else []
        )
        fila.autores = apellidos or list(referencia.apellidos) or fila.autores
        anio = (metadatos.anio if metadatos else None) or referencia.anio
        fila.anio = anio if anio is not None else fila.anio
        fila.estado_oa = (desenlace.estado_oa or "")[:20] or fila.estado_oa
        fila.url_acceso_abierto = desenlace.url_acceso_abierto or fila.url_acceso_abierto
        fila.url_pdf = desenlace.url_pdf or fila.url_pdf
        fila.licencia = (desenlace.licencia or "")[:80] or fila.licencia
        fila.actualizada_en = self._reloj()

    async def subir_pdf(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        referencia_id: uuid.UUID,
        ruta: Path,
    ) -> ReferenciaImportada:
        """El investigador sube el PDF de una referencia pendiente; se indexa con T10."""
        fila = await unidad.importacion.referencia(contexto, referencia_id)
        if fila is None:
            raise RecursoInexistente()
        if fila.estado is not EstadoReferencia.PENDIENTE_PDF:
            raise EstadoNoPermite("Solo se sube el PDF de una referencia pendiente de PDF.")
        coleccion = await unidad.corpus.coleccion(contexto, fila.coleccion_id)
        assert coleccion is not None
        nombre = (fila.doi or str(fila.id)).replace("/", "_") + ".pdf"
        async with self._candado:
            resultado = await self._indexador.ingerir(unidad, contexto, coleccion, ruta, nombre)
        metadatos = MetadatosBibliograficos(
            doi=fila.doi, titulo=fila.titulo, anio=fila.anio, autores=[]
        )
        desenlace = Desenlace(
            EstadoReferencia.PENDIENTE_PDF,
            fila.motivo,
            metadatos=metadatos,
            estado_oa=fila.estado_oa,
            url_acceso_abierto=fila.url_acceso_abierto,
            url_pdf=fila.url_pdf,
            licencia=fila.licencia,
        )
        desenlace = await self._tras_ingerir(unidad, contexto, resultado, desenlace)
        fila = await unidad.importacion.referencia(contexto, referencia_id)
        assert fila is not None
        fila.estado = desenlace.estado
        fila.motivo = desenlace.motivo
        fila.documento_id = desenlace.documento_id
        fila.actualizada_en = self._reloj()
        await unidad.corpus.recontar(contexto, coleccion)
        await unidad.confirmar()
        _registro.info(
            "pdf de referencia subido",
            extra={
                "tipo_evento": "importacion",
                "referencia_id": str(referencia_id),
                "estado": fila.estado.value,
            },
        )
        return fila

    def _borrar_carpeta(self, importacion_id: uuid.UUID) -> None:
        shutil.rmtree(carpeta_de(self._directorio, importacion_id), ignore_errors=True)

    @staticmethod
    def _informar(importacion: ImportacionReferencias) -> None:
        _registro.info(
            "importacion de referencias",
            extra={
                "tipo_evento": "importacion",
                "importacion_id": str(importacion.id),
                "origen": importacion.origen.value,
                "estado": importacion.estado.value,
                "total": importacion.total,
                "procesadas": importacion.procesadas,
                "error": importacion.error,
            },
        )


def _estado_oa(valor: str | None) -> EstadoAccesoAbierto:
    try:
        return EstadoAccesoAbierto(valor or EstadoAccesoAbierto.DESCONOCIDO.value)
    except ValueError:
        return EstadoAccesoAbierto.DESCONOCIDO
