"""Cliente HTTP del servicio compartido de modelos (``servicio_modelos/``, T08).

Implementa ``ProveedorEmbeddings`` y ``Reordenador``:

* Divide las listas largas en solicitudes de ``max_textos`` y une los resultados en orden.
* Valida cada respuesta con Pydantic: cantidad, dimensión de 1 024 y que todas las partes
  vengan del mismo modelo y revisión (mezclar revisiones obligaría a reindexar, RNF-21).
* Los textos van solo al servicio local, nunca a un proveedor externo (RNF-10).
* No registra textos: solo cantidades y duración (4.6).
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.bd.modelos.corpus import DIMENSION_EMBEDDINGS
from app.comun.errores import ErrorAplicacion
from app.comun.registro import obtener_registrador
from app.configuracion import Ajustes
from app.inferencia.interfaces import Embeddings, IdentidadModelo, Puntajes

M = TypeVar("M", bound=BaseModel)

MAX_TEXTOS_POR_SOLICITUD = 64
TIEMPO_MAXIMO_S = 300.0  # un lote de indexación en CPU puede tardar minutos

_registro = obtener_registrador("inferencia")


class ErrorServicioModelos(ErrorAplicacion):
    """El servicio de modelos no respondió o respondió algo fuera de contrato (503)."""

    def __init__(self, motivo: str, *, estado_http: int = 503, detalle: Any = None) -> None:
        super().__init__(
            "servicio_modelos_no_disponible",
            "El servicio de modelos no está disponible. Intente de nuevo en unos minutos.",
            estado_http=estado_http,
            detalle=detalle,
        )
        self.motivo = motivo


class _RespuestaEmbeber(BaseModel):
    modelo: str
    revision: str
    dimension: int
    vectores: list[list[float]]


class _RespuestaReordenar(BaseModel):
    modelo: str
    revision: str
    puntajes: list[float]


class ClienteServicioModelos:
    def __init__(
        self,
        url_base: str,
        *,
        cliente: httpx.AsyncClient | None = None,
        max_textos: int = MAX_TEXTOS_POR_SOLICITUD,
        tiempo_maximo_s: float = TIEMPO_MAXIMO_S,
    ) -> None:
        if max_textos < 1:
            raise ValueError("max_textos debe ser al menos 1")
        self._cliente = cliente or httpx.AsyncClient(
            base_url=url_base, timeout=httpx.Timeout(tiempo_maximo_s, connect=5.0)
        )
        self._max_textos = max_textos

    async def cerrar(self) -> None:
        await self._cliente.aclose()

    async def embeber(self, textos: Sequence[str]) -> Embeddings:
        identidad: IdentidadModelo | None = None
        vectores: list[list[float]] = []
        for parte in self._partes(textos):
            respuesta = await self._enviar("/embeber", {"textos": parte}, _RespuestaEmbeber)
            if respuesta.dimension != DIMENSION_EMBEDDINGS or len(respuesta.vectores) != len(parte):
                raise ErrorServicioModelos("respuesta de /embeber fuera de contrato")
            if any(len(v) != DIMENSION_EMBEDDINGS for v in respuesta.vectores):
                raise ErrorServicioModelos("vector con dimensión distinta de 1 024")
            identidad = self._misma_identidad(identidad, respuesta.modelo, respuesta.revision)
            vectores.extend(respuesta.vectores)
        assert identidad is not None
        return Embeddings(identidad=identidad, vectores=vectores)

    async def reordenar(self, consulta: str, textos: Sequence[str]) -> Puntajes:
        identidad: IdentidadModelo | None = None
        puntajes: list[float] = []
        for parte in self._partes(textos):
            respuesta = await self._enviar(
                "/reordenar", {"consulta": consulta, "textos": parte}, _RespuestaReordenar
            )
            if len(respuesta.puntajes) != len(parte) or any(
                not 0.0 <= p <= 1.0 for p in respuesta.puntajes
            ):
                raise ErrorServicioModelos("respuesta de /reordenar fuera de contrato")
            identidad = self._misma_identidad(identidad, respuesta.modelo, respuesta.revision)
            puntajes.extend(respuesta.puntajes)
        assert identidad is not None
        return Puntajes(identidad=identidad, puntajes=puntajes)

    def _partes(self, textos: Sequence[str]) -> list[list[str]]:
        if not textos:
            raise ValueError("se necesita al menos un texto")
        lista = list(textos)
        return [lista[i : i + self._max_textos] for i in range(0, len(lista), self._max_textos)]

    @staticmethod
    def _misma_identidad(
        actual: IdentidadModelo | None, modelo: str, revision: str
    ) -> IdentidadModelo:
        nueva = IdentidadModelo(modelo=modelo, revision=revision)
        if actual is not None and actual != nueva:
            raise ErrorServicioModelos("el modelo cambió entre partes de la misma solicitud")
        return nueva

    async def _enviar(self, ruta: str, cuerpo: dict[str, Any], esquema: type[M]) -> M:
        inicio = time.perf_counter()
        try:
            respuesta = await self._cliente.post(ruta, json=cuerpo)
        except httpx.HTTPError as error:
            raise ErrorServicioModelos(f"sin respuesta ({type(error).__name__})") from error
        duracion_ms = round((time.perf_counter() - inicio) * 1000)
        _registro.info(
            "servicio de modelos",
            extra={
                "tipo_evento": "inferencia",
                "ruta": ruta,
                "n_textos": len(cuerpo["textos"]),
                "estado_http": respuesta.status_code,
                "duracion_ms": duracion_ms,
            },
        )
        if respuesta.status_code == 422:
            # Entrada que el servicio no admite (por ejemplo, un texto demasiado largo):
            # es un error de quien llama, no una caída. Se pasa el código, nunca el texto.
            codigo = _codigo_error(respuesta)
            raise ErrorServicioModelos(
                f"entrada rechazada ({codigo})", estado_http=422, detalle={"codigo": codigo}
            )
        if respuesta.status_code != 200:
            raise ErrorServicioModelos(f"estado HTTP {respuesta.status_code}")
        try:
            return esquema.model_validate(respuesta.json())
        except (ValidationError, ValueError) as error:
            raise ErrorServicioModelos("respuesta no válida") from error


def cliente_desde_ajustes(ajustes: Ajustes) -> ClienteServicioModelos:
    if not ajustes.url_servicio_modelos:
        raise ErrorServicioModelos("URL_SERVICIO_MODELOS no está configurada")
    return ClienteServicioModelos(ajustes.url_servicio_modelos)


def _codigo_error(respuesta: httpx.Response) -> str:
    try:
        codigo = respuesta.json().get("codigo")
    except ValueError:
        return "desconocido"
    return codigo if isinstance(codigo, str) else "desconocido"
