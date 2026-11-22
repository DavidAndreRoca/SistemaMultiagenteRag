"""Construcción de la cadena de modelos a partir de los ajustes y la configuración (T17).

* El orden y los proveedores habilitados salen de ``PROVEEDORES_MODELO`` (validado al
  arrancar); los modelos, límites y precios, de la configuración versionada.
* Defensa en profundidad de la regla de entorno: fuera de desarrollo no se admite un
  modelo marcado como alias (RN-24), y en producción solo los proveedores de la lista.
* Un proveedor sin clave se omite y queda registrado; si no queda ninguno, cada llamada
  falla con ``sin_proveedores``.
"""

from __future__ import annotations

from decimal import Decimal

import httpx

from app.administracion.parametros import ModeloConfigurado, ParametrosFuncionales
from app.bd.modelos import EventoTecnico
from app.comun.registro import obtener_registrador
from app.configuracion import Ajustes
from app.configuracion.ajustes import PROVEEDORES_DE_PRODUCCION, Entorno
from app.llm.cadena import CadenaModelos, Eslabon, EventoLlamada, Precio, Registrar
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import Proveedor
from app.llm.proveedores import (
    URL_DEEPSEEK,
    URL_GROQ,
    ProveedorCompatibleOpenAI,
    ProveedorGemini,
    ProveedorModelo,
    ProveedorSimulado,
)
from app.repositorios.unidad import FabricaUnidades

_registro = obtener_registrador("llm")


class ConfiguracionModelosInvalida(RuntimeError):
    pass


def _clave(ajustes: Ajustes, proveedor: str) -> str | None:
    secreto = {
        "groq": ajustes.clave_groq,
        "deepseek": ajustes.clave_deepseek,
        "gemini": ajustes.clave_gemini,
    }.get(proveedor)
    if secreto is None or not secreto.get_secret_value().strip():
        return None
    return secreto.get_secret_value().strip()


def _proveedor(
    configurado: ModeloConfigurado, clave: str, cliente: httpx.AsyncClient
) -> ProveedorModelo:
    if configurado.proveedor == "groq":
        return ProveedorCompatibleOpenAI(
            Proveedor.GROQ,
            configurado.modelo,
            clave,
            cliente,
            URL_GROQ,
            esquema_estricto=True,
            max_tokens_salida=configurado.max_tokens_salida,
        )
    if configurado.proveedor == "deepseek":
        return ProveedorCompatibleOpenAI(
            Proveedor.DEEPSEEK,
            configurado.modelo,
            clave,
            cliente,
            URL_DEEPSEEK,
            esquema_estricto=False,
            max_tokens_salida=configurado.max_tokens_salida,
        )
    return ProveedorGemini(
        configurado.modelo, clave, cliente, max_tokens_salida=configurado.max_tokens_salida
    )


def _precio(configurado: ModeloConfigurado) -> Precio:
    def decimal(valor: float | None) -> Decimal | None:
        return None if valor is None else Decimal(str(valor))

    return Precio(
        decimal(configurado.precio_entrada_usd_millon),
        decimal(configurado.precio_salida_usd_millon),
    )


def exigir_regla_de_entorno(ajustes: Ajustes, parametros: ParametrosFuncionales) -> None:
    for nombre in ajustes.cadena_modelos:
        if ajustes.entorno is Entorno.PRODUCCION and nombre not in PROVEEDORES_DE_PRODUCCION:
            raise ConfiguracionModelosInvalida(
                f"{nombre} no está en la lista de proveedores de producción"
            )
        configurado = parametros.modelo(nombre)
        if (
            configurado is not None
            and configurado.alias
            and ajustes.entorno is not Entorno.DESARROLLO
        ):
            raise ConfiguracionModelosInvalida(
                f"{nombre}: el modelo {configurado.modelo} es un alias y solo se admite en"
                " desarrollo (RN-24)"
            )


def crear_cadena(
    ajustes: Ajustes,
    parametros: ParametrosFuncionales,
    registrar: Registrar,
    *,
    cliente: httpx.AsyncClient | None = None,
    simulado: ProveedorSimulado | None = None,
) -> CadenaModelos:
    exigir_regla_de_entorno(ajustes, parametros)
    http = cliente or httpx.AsyncClient(
        timeout=httpx.Timeout(ajustes.tiempo_maximo_modelo_s, connect=10.0)
    )
    eslabones: list[Eslabon] = []
    for nombre in ajustes.cadena_modelos:
        if nombre == "simulado":
            proveedor: ProveedorModelo = simulado or ProveedorSimulado()
            eslabones.append(
                Eslabon(proveedor, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)
            )
            continue
        configurado = parametros.modelo(nombre)
        clave = _clave(ajustes, nombre)
        if configurado is None or clave is None:
            _registro.warning(
                "proveedor de modelo omitido",
                extra={
                    "tipo_evento": "modelo",
                    "proveedor": nombre,
                    "motivo": "sin_clave" if configurado else "sin_modelo_configurado",
                },
            )
            continue
        limites = configurado.limites
        eslabones.append(
            Eslabon(
                _proveedor(configurado, clave, http),
                LimitadorProveedor(
                    Proveedor(nombre),
                    Limites(limites.rpm, limites.rpd, limites.tpm, limites.tpd),
                    espera_maxima_s=ajustes.espera_maxima_limitador_s,
                ),
                _precio(configurado),
                configurado.max_tokens_salida,
            )
        )
    return CadenaModelos(eslabones, registrar)


def registrador_en_base(abrir: FabricaUnidades) -> Registrar:
    """Guarda cada intento en ``evento_tecnico``. Una falla de la base no corta la llamada."""

    async def registrar(evento: EventoLlamada) -> None:
        try:
            async with abrir() as unidad:
                await unidad.eventos_tecnicos.agregar(
                    EventoTecnico(
                        etapa=evento.etapa,
                        inicio=evento.inicio,
                        duracion_ms=evento.duracion_ms,
                        proveedor=evento.proveedor,
                        modelo=evento.modelo,
                        tokens_entrada=evento.tokens_entrada,
                        tokens_salida=evento.tokens_salida,
                        costo_estimado=evento.costo_estimado,
                        error=evento.error,
                    )
                )
                await unidad.confirmar()
        except Exception:
            _registro.exception(
                "no se pudo registrar el evento técnico",
                extra={"tipo_evento": "modelo", "proveedor": evento.proveedor},
            )

    return registrar
