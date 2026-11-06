"""Middleware ASGI: incidencia_id por petición, registro de acceso y cabeceras de seguridad.

Es ASGI puro (no ``BaseHTTPMiddleware``) para que el identificador de incidencia
llegue también a las respuestas de error 500, que este middleware construye él mismo
con el formato común.
"""

from __future__ import annotations

import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.comun.contexto import fijar_incidencia_id
from app.comun.errores import manejar_inesperado
from app.comun.registro import obtener_registrador

CABECERA_INCIDENCIA = "X-Incidencia-Id"

# Cabeceras de seguridad básicas desde T03; T41 las completa (CSP final, etc.).
CABECERAS_SEGURIDAD = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
CSP_API = "default-src 'none'; frame-ancestors 'none'"
HSTS = "max-age=31536000; includeSubDomains"
RUTAS_DOCUMENTACION = ("/docs", "/redoc", "/openapi.json")


class MiddlewareIncidencia:
    def __init__(self, aplicacion: ASGIApp, *, es_produccion: bool = False) -> None:
        self.aplicacion = aplicacion
        self.es_produccion = es_produccion

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.aplicacion(scope, receive, send)
            return

        incidencia_id = uuid.uuid4().hex
        fijar_incidencia_id(incidencia_id)
        inicio = time.perf_counter()
        ruta = scope["path"]
        estado = 500
        respuesta_iniciada = False

        async def enviar(mensaje: Message) -> None:
            nonlocal estado, respuesta_iniciada
            if mensaje["type"] == "http.response.start":
                estado = mensaje["status"]
                respuesta_iniciada = True
                cabeceras = MutableHeaders(scope=mensaje)
                cabeceras[CABECERA_INCIDENCIA] = incidencia_id
                for nombre, valor in CABECERAS_SEGURIDAD.items():
                    cabeceras.setdefault(nombre, valor)
                if not ruta.startswith(RUTAS_DOCUMENTACION):
                    cabeceras.setdefault("Content-Security-Policy", CSP_API)
                if self.es_produccion:
                    cabeceras.setdefault("Strict-Transport-Security", HSTS)
            await send(mensaje)

        try:
            await self.aplicacion(scope, receive, enviar)
        except Exception as error:
            if respuesta_iniciada:
                raise
            respuesta = await manejar_inesperado(Request(scope, receive), error)
            await respuesta(scope, receive, enviar)
        finally:
            obtener_registrador("acceso").info(
                "peticion",
                extra={
                    "tipo_evento": "acceso",
                    "metodo": scope["method"],
                    "ruta": ruta,
                    "estado_http": estado,
                    "duracion_ms": round((time.perf_counter() - inicio) * 1000, 1),
                },
            )
