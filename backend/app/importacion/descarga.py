"""Descarga del PDF de acceso abierto de una referencia (T15-01, apartado 5).

Solo enlaces directos que devuelven un PDF de verdad (firma ``%PDF-``) y de hasta el
tamaño máximo de la configuración. Cualquier falla deja la referencia pendiente de PDF:
el investigador puede bajarla a mano desde la página de acceso abierto.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from app.comun.registro import obtener_registrador

FIRMA_PDF = b"%PDF-"
BYTES_CABECERA = 1024
_registro = obtener_registrador("importacion")


class Descargador:
    def __init__(self, cliente: httpx.AsyncClient) -> None:
        self._cliente = cliente

    async def descargar(self, url: str, destino: Path, limite_bytes: int) -> str | None:
        """Guarda el PDF en ``destino``. Devuelve ``None`` si salió bien o el motivo."""
        cabecera = b""
        try:
            respuesta = await self._cliente.send(
                self._cliente.build_request("GET", url), stream=True
            )
            try:
                if respuesta.status_code != 200:
                    return self._falla(f"http_{respuesta.status_code}")
                escritos = 0
                with destino.open("wb") as archivo:
                    async for parte in respuesta.aiter_bytes():
                        if len(cabecera) < BYTES_CABECERA:
                            cabecera += parte[: BYTES_CABECERA - len(cabecera)]
                        escritos += len(parte)
                        if escritos > limite_bytes:
                            return self._falla("excede_tamano")
                        archivo.write(parte)
            finally:
                await respuesta.aclose()
        except (httpx.HTTPError, httpx.InvalidURL) as error:
            return self._falla(type(error).__name__)
        if FIRMA_PDF not in cabecera:
            return self._falla("no_es_pdf")
        return None

    @staticmethod
    def _falla(detalle: str) -> str:
        _registro.info(
            "descarga de pdf fallida", extra={"tipo_evento": "importacion", "detalle": detalle}
        )
        return "descarga_fallida"
