"""Aporte de una fuente tras una abstención (T32; RF-13, CU-12, CP-14 a CP-17).

``ServicioAportes.aportar`` sigue el flujo de CU-12:

1. comprueba la existencia por DOI o por metadatos (``existencia.py``). Sin confirmación,
   no indexa y registra el intento (CP-16); un servicio caído da "no comprobable", nunca
   inexistente (RN-18);
2. si la colección personal ya tiene la obra (mismo DOI o mismo texto), no la duplica y
   sigue (CP-17);
3. toma el texto: el PDF procesado con el canal de T09 o, sin PDF (o si el PDF se excluye),
   el resumen de Crossref u OpenAlex (CP-15). Sin texto, no indexa;
4. evalúa la coherencia con la afirmación (informativa, ``coherencia.py``);
5. propone la cita en la norma del caso, del registro del DOI o del formateador CSL
   (RN-17: nunca de un modelo);
6. indexa solo en la colección personal del caso (``RepositorioColeccionPersonal``);
7. crea una nueva búsqueda de evidencia con la misma consulta, enlazada a la original; la
   API la encola.

RN-14 (acceso abierto) no se aplica a las fuentes aportadas. El registro guarda el
desenlace y cantidades, nunca los datos de la obra ni la afirmación (4.6).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.aportes.coherencia import NO_EVALUADA, Coherencia, evaluar_coherencia
from app.aportes.existencia import DatosAporte, comprobar_existencia, resumen_de
from app.bd.enumeraciones import (
    CoherenciaFuente,
    EstadoDocumento,
    EstadoSolicitud,
    ExistenciaFuente,
    IndexacionAporte,
    OrigenDocumento,
    SeccionNormalizada,
    TipoAlcance,
    TipoSolicitud,
)
from app.bd.modelos import Documento, Fragmento, FuenteAportada, Solicitud
from app.bibliografia.interfaces import BuscadorBibliografico
from app.bibliografia.modelos import MetadatosBibliograficos
from app.bibliografia.normalizacion import normalizar
from app.bibliografia.referencias import ConstructorReferencias
from app.comun.registro import obtener_registrador
from app.corpus.esquemas import EstadoProcesamiento
from app.corpus.indexacion import Indexador
from app.corpus.validacion import huella
from app.llm.interfaces import ModeloLenguaje
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo

PALABRAS_POR_FRAGMENTO = 60
TOKENS_POR_PALABRA = 1.4  # aproximación para el presupuesto de contexto (sin tokenizador)
_registro = obtener_registrador("aportes")


class MotivoNoIndexada:
    EXISTENCIA_NO_CONFIRMADA = "existencia_no_confirmada"
    SERVICIO_NO_DISPONIBLE = "servicio_no_disponible"
    SIN_TEXTO = "sin_texto"


class TextoDeLaFuente(BaseModel):
    model_config = ConfigDict(frozen=True)

    fragmentos: list[str]
    huella: str
    secciones: list[SeccionNormalizada]
    paginas: list[tuple[int | None, int | None]]
    tokens: list[int]
    huella_archivo: str | None = None
    num_paginas: int | None = None
    desde_pdf: bool = False


@dataclass(frozen=True)
class DesenlaceAporte:
    """Lo que la API devuelve del aporte; la fila guardada es ``FuenteAportada``."""

    aporte: FuenteAportada
    coherencia: Coherencia
    texto_indexado: str | None  # "pdf" o "resumen"
    nueva_solicitud: Solicitud | None


def _tokens(texto: str) -> int:
    return max(1, round(len(texto.split()) * TOKENS_POR_PALABRA))


def trozos_del_resumen(resumen: str) -> list[str]:
    """Oraciones completas agrupadas hasta unas ``PALABRAS_POR_FRAGMENTO`` palabras: un
    resumen es corto y denso, y en un solo fragmento nunca llegaría a los
    ``suficiencia_n`` fragmentos pertinentes de RN-04."""
    trozos: list[str] = []
    actual: list[str] = []
    for oracion in re.split(r"(?<=[.!?])\s+", " ".join(resumen.split())):
        if actual and len(" ".join([*actual, oracion]).split()) > PALABRAS_POR_FRAGMENTO:
            trozos.append(" ".join(actual))
            actual = []
        actual.append(oracion)
    if actual:
        trozos.append(" ".join(actual))
    return [t for t in trozos if t.strip()]


def texto_del_resumen(resumen: str) -> TextoDeLaFuente:
    trozos = trozos_del_resumen(resumen)
    return TextoDeLaFuente(
        fragmentos=trozos,
        huella=huella(normalizar(resumen).encode("utf-8")),
        secciones=[SeccionNormalizada.RESUMEN] * len(trozos),
        paginas=[(None, None)] * len(trozos),
        tokens=[_tokens(t) for t in trozos],
    )


def documento_de(
    metadatos: MetadatosBibliograficos, datos: DatosAporte, contexto: ContextoAcceso
) -> Documento:
    """Documento con los metadatos del registro (los declarados solo si el registro no los
    trae). Sin colección: el repositorio pone la personal del caso."""
    autores = [a.model_dump(exclude_none=True) for a in metadatos.autores] or [
        {"apellidos": a} for a in datos.autores
    ]
    return Documento(
        id=uuid.uuid4(),
        titulo=metadatos.titulo or datos.titulo,
        autores=autores,
        anio=metadatos.anio or datos.anio,
        doi=metadatos.doi or datos.doi,
        revista_editorial=metadatos.revista or metadatos.editorial,
        estado=EstadoDocumento.ACTIVO,
        origen=OrigenDocumento.APORTE,
        indexado_por_id=contexto.cuenta_id,
    )


class ServicioAportes:
    def __init__(
        self,
        *,
        servicios: Sequence[BuscadorBibliografico],
        citas: ConstructorReferencias,
        modelo: ModeloLenguaje | None,
        embebedor: Callable[[], Awaitable[Indexador]],
        canal_pdf: Callable[[], Awaitable[Indexador]],
        reloj: Callable[[], datetime],
    ) -> None:
        """``embebedor`` da un indexador con el servicio de modelos (sin Docling); ``canal_pdf``,
        uno con el canal de T09, que se carga solo si llega un PDF."""
        self._servicios = servicios
        self._citas = citas
        self._modelo = modelo
        self._embebedor = embebedor
        self._canal_pdf = canal_pdf
        self._reloj = reloj

    def usar_modelo(self, modelo: ModeloLenguaje) -> None:
        """El modelo de la coherencia (la cadena se crea con la configuración vigente)."""
        self._modelo = modelo

    async def aportar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        solicitud: Solicitud,
        datos: DatosAporte,
        pdf: Path | None,
        norma: str,
    ) -> DesenlaceAporte:
        aporte = FuenteAportada(
            solicitud_id=solicitud.id,
            datos_bibliograficos={
                "titulo": datos.titulo,
                "autores": datos.autores,
                "anio": datos.anio,
                "con_pdf": pdf is not None,
            },
            doi=datos.doi,
            coherencia=CoherenciaFuente.NO_EVALUADA,
            indexacion=IndexacionAporte.NO_INDEXADA,
            aportada_en=self._reloj(),
        )
        existencia = await comprobar_existencia(datos, self._servicios)
        aporte.existencia = existencia.estado
        aporte.metodo_existencia = existencia.metodo
        if existencia.estado is not ExistenciaFuente.CONFIRMADA or existencia.metadatos is None:
            aporte.motivo_indexacion = (
                MotivoNoIndexada.SERVICIO_NO_DISPONIBLE
                if existencia.estado is ExistenciaFuente.NO_COMPROBABLE
                else MotivoNoIndexada.EXISTENCIA_NO_CONFIRMADA
            )
            return await self._guardar(unidad, contexto, aporte, NO_EVALUADA, None, None)

        metadatos = existencia.metadatos
        documento = documento_de(metadatos, datos, contexto)
        previo = await unidad.coleccion_personal.duplicado(contexto, None, documento.doi)
        texto: TextoDeLaFuente | None = None
        if previo is None:
            texto = await self._texto(unidad, metadatos, pdf)
            if texto is not None:
                previo = await unidad.coleccion_personal.duplicado(
                    contexto, texto.huella, documento.doi
                )
        coherencia = NO_EVALUADA
        if texto is not None:
            _, parametros = await unidad.configuracion.vigente()
            coherencia = await evaluar_coherencia(
                self._modelo,
                lambda: parametros.versiones_instrucciones,
                solicitud.alcance_ref or "",
                texto.fragmentos,
            )
        aporte.coherencia = coherencia.valor

        if previo is not None:  # CP-17: no se duplica y se continúa
            aporte.indexacion = IndexacionAporte.YA_INDEXADA
            aporte.documento_id = previo.id
            aporte.cita_propuesta = await self._cita(previo, norma)
            nueva = await self._nueva_busqueda(unidad, contexto, solicitud)
            return await self._guardar(unidad, contexto, aporte, coherencia, None, nueva)

        aporte.cita_propuesta = await self._cita(documento, norma)
        if texto is None:
            aporte.motivo_indexacion = MotivoNoIndexada.SIN_TEXTO
            return await self._guardar(unidad, contexto, aporte, coherencia, None, None)

        guardado = await self._indexar(unidad, contexto, documento, texto, pdf)
        aporte.indexacion = IndexacionAporte.INDEXADA
        aporte.documento_id = documento.id
        nueva = await self._nueva_busqueda(unidad, contexto, solicitud)
        try:
            return await self._guardar(
                unidad,
                contexto,
                aporte,
                coherencia,
                "pdf" if texto.desde_pdf else "resumen",
                nueva,
            )
        except BaseException:
            if guardado is not None:
                (await self._canal_pdf()).borrar_archivo(guardado)
            raise

    async def _texto(
        self, unidad: UnidadDeTrabajo, metadatos: MetadatosBibliograficos, pdf: Path | None
    ) -> TextoDeLaFuente | None:
        if pdf is not None:
            procesado = await (await self._canal_pdf()).procesar(unidad, pdf)
            if (
                procesado.estado is not EstadoProcesamiento.EXCLUIDO
                and procesado.fragmentos
                and procesado.huella_texto is not None
            ):
                return TextoDeLaFuente(
                    fragmentos=[f.texto for f in procesado.fragmentos],
                    huella=procesado.huella_texto,
                    secciones=[f.seccion_normalizada for f in procesado.fragmentos],
                    paginas=[(f.pagina_inicio, f.pagina_fin) for f in procesado.fragmentos],
                    tokens=[f.tokens for f in procesado.fragmentos],
                    huella_archivo=procesado.huella_archivo,
                    num_paginas=procesado.num_paginas,
                    desde_pdf=True,
                )
            _registro.info(
                "pdf aportado sin texto indexable",
                extra={
                    "tipo_evento": "aportes",
                    "estado": procesado.estado.value,
                    "motivo": procesado.motivo_exclusion.value
                    if procesado.motivo_exclusion
                    else None,
                },
            )
        resumen = await resumen_de(metadatos, self._servicios)
        return texto_del_resumen(resumen) if resumen else None

    async def _indexar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        documento: Documento,
        texto: TextoDeLaFuente,
        pdf: Path | None,
    ) -> str | None:
        vectores, identidad = await (await self._embebedor()).embeber(texto.fragmentos)
        documento.huella_sha256 = texto.huella
        documento.modelo_embeddings = identidad.modelo
        documento.revision_embeddings = identidad.revision
        guardado: str | None = None
        if texto.desde_pdf and pdf is not None:
            documento.huella_archivo = texto.huella_archivo
            documento.num_paginas = texto.num_paginas
            guardado = (await self._canal_pdf()).guardar_archivo(pdf)
            documento.ruta_archivo = guardado
        fragmentos = [
            Fragmento(
                orden=i,
                texto=t,
                seccion_normalizada=texto.secciones[i],
                pagina_inicio=texto.paginas[i][0],
                pagina_fin=texto.paginas[i][1],
                tokens=texto.tokens[i],
                embedding=vectores[i],
            )
            for i, t in enumerate(texto.fragmentos)
        ]
        await unidad.coleccion_personal.agregar_documento(contexto, documento, fragmentos)
        return guardado

    async def _cita(self, documento: Documento, norma: str) -> str:
        return (await self._citas.de_documento(documento, norma)).texto

    async def _nueva_busqueda(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, original: Solicitud
    ) -> Solicitud:
        """La misma consulta, de nuevo, ahora con la fuente en la colección personal."""
        configuracion, _ = await unidad.configuracion.vigente()
        ahora = self._reloj()
        return await unidad.solicitudes.agregar(
            contexto,
            Solicitud(
                version_id=original.version_id,
                tipo=TipoSolicitud.BUSQUEDA_EVIDENCIA,
                alcance_tipo=TipoAlcance.CONSULTA,
                alcance_ref=original.alcance_ref,
                configuracion_id=configuracion.id,
                estado=EstadoSolicitud.RECIBIDA,
                solicitud_origen_id=original.id,
                creada_en=ahora,
                actualizada_en=ahora,
            ),
        )

    async def _guardar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        aporte: FuenteAportada,
        coherencia: Coherencia,
        texto_indexado: str | None,
        nueva: Solicitud | None,
    ) -> DesenlaceAporte:
        aporte.solicitud_recuperacion_id = nueva.id if nueva else None
        await unidad.fuentes_aportadas.agregar(contexto, aporte)
        await unidad.confirmar()
        _registro.info(
            "fuente aportada",
            extra={
                "tipo_evento": "aportes",
                "solicitud_id": str(aporte.solicitud_id),
                "existencia": aporte.existencia.value,
                "metodo": aporte.metodo_existencia.value if aporte.metodo_existencia else None,
                "indexacion": aporte.indexacion.value,
                "motivo": aporte.motivo_indexacion,
                "coherencia": aporte.coherencia.value,
                "texto": texto_indexado,
                "nueva_solicitud_id": str(nueva.id) if nueva else None,
            },
        )
        return DesenlaceAporte(
            aporte=aporte,
            coherencia=coherencia,
            texto_indexado=texto_indexado,
            nueva_solicitud=nueva,
        )
