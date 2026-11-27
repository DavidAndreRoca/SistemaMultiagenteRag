"""Proveedores de modelos de lenguaje con httpx (T17-01, apartado 2).

* Groq y DeepSeek: API compatible con OpenAI (``/chat/completions``). Groq con esquema
  JSON estricto; DeepSeek solo con modo JSON, con el esquema escrito en la instrucción.
* Gemini: API de interacciones (``/v1beta/interactions``) con ``response_format``.
* Simulado: determinista, para pruebas y CI.

Cada proveedor convierte las fallas en ``ErrorDisponibilidad`` (se reintenta y pasa al
respaldo) o ``ErrorSolicitud`` (no). Nada de la entrada ni de la salida llega al registro.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from pydantic import BaseModel

from app.llm import mensajes
from app.llm.esquema import esquema_estricto, nombre_esquema
from app.llm.modelos import (
    EntradaModelo,
    ErrorDisponibilidad,
    ErrorSolicitud,
    Instruccion,
    MotivoError,
    Proveedor,
    RespuestaProveedor,
    Uso,
)

URL_GROQ = "https://api.groq.com/openai/v1"
URL_DEEPSEEK = "https://api.deepseek.com"
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta"
REVISION_GEMINI = "2026-05-20"


class ProveedorModelo(Protocol):
    proveedor: Proveedor
    modelo: str

    async def completar(
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[BaseModel]
    ) -> RespuestaProveedor: ...


def _espera(respuesta: httpx.Response) -> float | None:
    valor = respuesta.headers.get("retry-after")
    try:
        return float(valor) if valor else None
    except ValueError:
        return None


def _codigo_error(respuesta: httpx.Response) -> str:
    """El código de error del cuerpo (``error.code``), solo si es un identificador: nunca se
    registra el mensaje ni la generación fallida, que pueden traer contenido."""
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return ""
    error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
    codigo = error.get("code") if isinstance(error, dict) else None
    return codigo if isinstance(codigo, str) and re.fullmatch(r"[a-z0-9_]{1,40}", codigo) else ""


def clasificar(proveedor: Proveedor, respuesta: httpx.Response) -> None:
    """Lanza el error que corresponde a un estado distinto de 200.

    Un 400 ``json_validate_failed`` (Groq con esquema estricto) es una generación que no
    cumplió el esquema, por ejemplo cortada por el tope de salida: es ocasional, así que se
    trata como respuesta ilegible y se reintenta (T27-01).
    """
    estado = respuesta.status_code
    if estado == 200:
        return
    codigo = _codigo_error(respuesta)
    if estado == 400 and codigo == "json_validate_failed":
        raise ErrorDisponibilidad(MotivoError.RESPUESTA_ILEGIBLE, proveedor, f"http_400:{codigo}")
    if estado == 429:
        raise ErrorDisponibilidad(
            MotivoError.LIMITE_DE_TASA, proveedor, "http_429", _espera(respuesta)
        )
    if estado == 402:
        raise ErrorDisponibilidad(MotivoError.SALDO_INSUFICIENTE, proveedor, "http_402")
    if estado in (408, 504):
        raise ErrorDisponibilidad(MotivoError.TIEMPO_AGOTADO, proveedor, f"http_{estado}")
    if estado == 503:
        raise ErrorDisponibilidad(MotivoError.SOBRECARGA, proveedor, "http_503", _espera(respuesta))
    if estado >= 500:
        raise ErrorDisponibilidad(MotivoError.ERROR_DEL_SERVICIO, proveedor, f"http_{estado}")
    if estado in (401, 403):
        raise ErrorSolicitud(MotivoError.CLAVE_RECHAZADA, proveedor, f"http_{estado}")
    detalle = f"http_{estado}:{codigo}" if codigo else f"http_{estado}"
    raise ErrorSolicitud(MotivoError.SOLICITUD_RECHAZADA, proveedor, detalle)


async def _post(
    cliente: httpx.AsyncClient,
    proveedor: Proveedor,
    url: str,
    cuerpo: dict[str, Any],
    cabeceras: dict[str, str],
) -> dict[str, Any]:
    try:
        respuesta = await cliente.post(url, json=cuerpo, headers=cabeceras)
    except httpx.TimeoutException:
        raise ErrorDisponibilidad(MotivoError.TIEMPO_AGOTADO, proveedor) from None
    except httpx.HTTPError as error:
        raise ErrorDisponibilidad(
            MotivoError.SIN_CONEXION, proveedor, type(error).__name__
        ) from None
    clasificar(proveedor, respuesta)
    try:
        datos = respuesta.json()
    except ValueError:
        raise ErrorDisponibilidad(MotivoError.RESPUESTA_ILEGIBLE, proveedor) from None
    if not isinstance(datos, dict):
        raise ErrorDisponibilidad(MotivoError.RESPUESTA_ILEGIBLE, proveedor)
    return datos


def _diccionario(valor: Any) -> dict[str, Any]:
    return valor if isinstance(valor, dict) else {}


def _entero(valor: Any) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


@dataclass
class ProveedorCompatibleOpenAI:
    """Groq (esquema estricto) y DeepSeek (modo JSON)."""

    proveedor: Proveedor
    modelo: str
    clave: str
    cliente: httpx.AsyncClient
    url_base: str
    esquema_estricto: bool
    max_tokens_salida: int = 2048

    def cuerpo(
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[BaseModel]
    ) -> dict[str, Any]:
        estructura = esquema_estricto(esquema)
        if self.esquema_estricto:
            formato: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {
                    "name": nombre_esquema(esquema),
                    "strict": True,
                    "schema": estructura,
                },
            }
            sistema = mensajes.sistema(instruccion)
        else:
            formato = {"type": "json_object"}
            sistema = mensajes.sistema(instruccion, esquema_en_texto=estructura)
        return {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": mensajes.usuario(entrada)},
            ],
            "response_format": formato,
            "max_tokens": self.max_tokens_salida,
            "temperature": 0,
            "stream": False,
        }

    async def completar(
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[BaseModel]
    ) -> RespuestaProveedor:
        datos = await _post(
            self.cliente,
            self.proveedor,
            f"{self.url_base}/chat/completions",
            self.cuerpo(instruccion, entrada, esquema),
            {"Authorization": f"Bearer {self.clave}"},
        )
        try:
            eleccion = datos["choices"][0]
            texto = eleccion["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ErrorDisponibilidad(MotivoError.RESPUESTA_ILEGIBLE, self.proveedor) from None
        if not isinstance(texto, str) or not texto.strip():
            # DeepSeek reemplaza por espacios lo que no es JSON: se trata como falla transitoria.
            raise ErrorDisponibilidad(
                MotivoError.RESPUESTA_ILEGIBLE, self.proveedor, "contenido vacío"
            )
        uso = _diccionario(datos.get("usage"))
        return RespuestaProveedor(
            texto=texto,
            uso=Uso(
                tokens_entrada=_entero(uso.get("prompt_tokens")),
                tokens_salida=_entero(uso.get("completion_tokens")),
            ),
            version_informada=datos.get("model") if isinstance(datos.get("model"), str) else None,
        )


@dataclass
class ProveedorGemini:
    """API de interacciones de Gemini con esquema JSON."""

    modelo: str
    clave: str
    cliente: httpx.AsyncClient
    url_base: str = URL_GEMINI
    max_tokens_salida: int = 2048
    proveedor: Proveedor = Proveedor.GEMINI

    def cuerpo(
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[BaseModel]
    ) -> dict[str, Any]:
        return {
            "model": self.modelo,
            "input": mensajes.usuario(entrada),
            "system_instruction": mensajes.sistema(instruccion),
            "generation_config": {"max_output_tokens": self.max_tokens_salida},
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": esquema_estricto(esquema),
            },
            "store": False,
        }

    async def completar(
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[BaseModel]
    ) -> RespuestaProveedor:
        datos = await _post(
            self.cliente,
            self.proveedor,
            f"{self.url_base}/interactions",
            self.cuerpo(instruccion, entrada, esquema),
            {"x-goog-api-key": self.clave, "Api-Revision": REVISION_GEMINI},
        )
        if datos.get("status") not in ("completed", "incomplete"):
            raise ErrorDisponibilidad(
                MotivoError.RESPUESTA_ILEGIBLE, self.proveedor, f"estado {datos.get('status')}"
            )
        textos = [
            parte.get("text", "")
            for paso in datos.get("steps") or []
            if isinstance(paso, dict) and paso.get("type") == "model_output"
            for parte in paso.get("content") or []
            if isinstance(parte, dict) and parte.get("type") == "text"
        ]
        texto = "".join(t for t in textos if isinstance(t, str))
        if not texto.strip():
            raise ErrorDisponibilidad(MotivoError.RESPUESTA_ILEGIBLE, self.proveedor, "sin texto")
        uso = _diccionario(datos.get("usage"))
        return RespuestaProveedor(
            texto=texto,
            uso=Uso(
                tokens_entrada=_entero(uso.get("total_input_tokens")),
                tokens_salida=_entero(uso.get("total_output_tokens")),
            ),
            version_informada=datos.get("model") if isinstance(datos.get("model"), str) else None,
        )


@dataclass
class ProveedorSimulado:
    """Responde siempre lo mismo para cada esquema: lo que dé ``respuestas``, o un objeto
    armado con valores neutros. ``fallar`` permite simular un proveedor caído."""

    modelo: str = "simulado-determinista"
    respuestas: dict[str, Callable[[EntradaModelo], dict[str, Any]]] | None = None
    fallar: ErrorDisponibilidad | ErrorSolicitud | None = None
    proveedor: Proveedor = Proveedor.SIMULADO
    llamadas: int = 0

    async def completar(
        self, instruccion: Instruccion, entrada: EntradaModelo, esquema: type[BaseModel]
    ) -> RespuestaProveedor:
        self.llamadas += 1
        if self.fallar is not None:
            raise self.fallar
        fabrica = (self.respuestas or {}).get(esquema.__name__)
        datos = fabrica(entrada) if fabrica else valores_neutros(esquema_estricto(esquema))
        texto = json.dumps(datos, ensure_ascii=False)
        return RespuestaProveedor(
            texto=texto,
            uso=Uso(
                tokens_entrada=mensajes.estimar_tokens(
                    instruccion.texto, mensajes.usuario(entrada)
                ),
                tokens_salida=mensajes.estimar_tokens(texto),
            ),
            version_informada=self.modelo,
        )


def valores_neutros(esquema: dict[str, Any], defs: dict[str, Any] | None = None) -> Any:
    """Un valor válido y determinista para un esquema JSON estricto."""
    defs = defs if defs is not None else esquema.get("$defs", {})
    if "$ref" in esquema:
        return valores_neutros(defs[esquema["$ref"].split("/")[-1]], defs)
    if "anyOf" in esquema:
        return valores_neutros(esquema["anyOf"][0], defs)
    if "enum" in esquema:
        return esquema["enum"][0]
    if "const" in esquema:
        return esquema["const"]
    tipo = esquema.get("type")
    if tipo == "object":
        return {k: valores_neutros(v, defs) for k, v in esquema.get("properties", {}).items()}
    if tipo == "array":
        minimo = int(esquema.get("minItems", 0))
        return [valores_neutros(esquema.get("items", {}), defs) for _ in range(minimo)]
    if tipo == "string":
        if str(esquema.get("pattern", "")).startswith("^F[1-9]"):
            return "F1"  # identificador de fragmento citable (T18)
        return "x" * max(int(esquema.get("minLength", 0)), 1 if "minLength" in esquema else 0)
    if tipo in ("integer", "number"):
        return esquema.get("minimum", 0)
    return {"boolean": False, "null": None}.get(str(tipo))
