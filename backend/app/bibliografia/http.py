"""Cliente HTTP de los servicios bibliográficos (T14-01, apartado 3).

Tiempos de espera, limitador por servicio y reintentos con espera exponencial ante
errores transitorios (red, tiempo agotado, 429, 500, 502, 503 y 504). Si se agotan los
intentos, lanza ``FallaDeServicio`` con el motivo, que el cliente convierte en
``no_comprobable`` (RN-18). Un 404 u otro 4xx no se reintenta: es una respuesta.

El registro solo lleva el servicio, el motivo y los intentos: nunca la URL, que puede
contener el correo del proyecto o la clave de OpenAlex.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import httpx

from app.bibliografia.limitador import CubetaDeFichas, Dormir
from app.bibliografia.modelos import Motivo, Servicio
from app.comun.registro import obtener_registrador

ESTADOS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
_registro = obtener_registrador("bibliografia")


class FallaDeServicio(Exception):
    """El servicio no dio una respuesta utilizable: el resultado es ``no_comprobable``."""

    def __init__(self, motivo: Motivo) -> None:
        super().__init__(motivo.value)
        self.motivo = motivo


@dataclass(frozen=True)
class PoliticaReintentos:
    intentos: int = 3
    espera_base_s: float = 0.5
    espera_maxima_s: float = 10.0  # tope para Retry-After y para la espera exponencial


def _retry_after(respuesta: httpx.Response) -> float | None:
    valor = respuesta.headers.get("Retry-After")
    try:
        return float(valor) if valor is not None else None
    except ValueError:
        return None


class ClienteHttp:
    def __init__(
        self,
        servicio: Servicio,
        cliente: httpx.AsyncClient,
        limitador: CubetaDeFichas,
        politica: PoliticaReintentos | None = None,
        *,
        dormir: Dormir = asyncio.sleep,
        azar: Callable[[], float] = random.random,
    ) -> None:
        self.servicio = servicio
        self._cliente = cliente
        self._limitador = limitador
        self._politica = politica or PoliticaReintentos()
        self._dormir = dormir
        self._azar = azar

    def _espera(self, intento: int, sugerida: float | None) -> float:
        if sugerida is not None:
            return min(sugerida, self._politica.espera_maxima_s)
        exponencial = self._politica.espera_base_s * 2.0 ** (intento - 1)
        return min(exponencial * (1 + 0.25 * self._azar()), self._politica.espera_maxima_s)

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        limitador: CubetaDeFichas | None = None,
    ) -> httpx.Response:
        motivo = Motivo.ERROR_DEL_SERVICIO
        intentos = self._politica.intentos
        for intento in range(1, intentos + 1):
            await (limitador or self._limitador).adquirir()
            sugerida: float | None = None
            try:
                respuesta = await self._cliente.get(url, params=params, headers=headers)
            except httpx.TimeoutException:
                motivo = Motivo.TIEMPO_AGOTADO
            except httpx.HTTPError:
                motivo = Motivo.SIN_CONEXION
            else:
                if respuesta.status_code not in ESTADOS_TRANSITORIOS:
                    return respuesta
                motivo = (
                    Motivo.LIMITE_DE_TASA
                    if respuesta.status_code == 429
                    else Motivo.ERROR_DEL_SERVICIO
                )
                sugerida = _retry_after(respuesta)
            if intento < intentos:
                await self._dormir(self._espera(intento, sugerida))
        _registro.warning(
            "servicio bibliografico no disponible",
            extra={
                "tipo_evento": "bibliografia",
                "servicio": self.servicio.value,
                "motivo": motivo.value,
                "intentos": intentos,
            },
        )
        raise FallaDeServicio(motivo)


def json_de(respuesta: httpx.Response) -> object:
    """Cuerpo JSON o ``FallaDeServicio`` (respuesta ilegible)."""
    try:
        return respuesta.json()
    except ValueError:
        raise FallaDeServicio(Motivo.RESPUESTA_INVALIDA) from None
