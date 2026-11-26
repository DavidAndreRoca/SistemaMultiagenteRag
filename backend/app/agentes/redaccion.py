"""Agente D3 estilístico: propuesta de redacción de un párrafo (T27; RF-07, CU-06, CP-09,
CP-10, RN-07).

* **Entrada:** un solo párrafo del cuerpo de la versión vigente, de hasta
  ``limite_palabras_d3`` (250) palabras. ``validar_alcance`` (T12) rechaza más de un párrafo o
  un párrafo más largo antes de crear la solicitud (CP-09). Los títulos y la lista de
  referencias no se admiten: una propuesta sobre una entrada de la lista sería una
  referencia escrita por el modelo (RN-17).
* **Recuperación:** las pautas de redacción de las guías (T22), con una consulta que nombra
  los tres indicadores y no lleva el texto del estudiante (lección de T23-01). El párrafo
  llega al modelo solo como alcance (RNF-10).
* **Salida:** ``PropuestaRedaccion``. El sistema reemplaza ``original`` por el párrafo
  guardado, para que las comprobaciones y la vista comparada partan del texto real.
* **Comprobaciones:** 1 (esquema), 3 (citas de las razones a los fragmentos recuperados) y
  2 para D3: hasta 1.2 veces el original, un solo párrafo, sin números ni citas nuevas y
  cada cambio presente en el original y en la propuesta (CP-10). La conservación del resto
  del contenido la juzga el evaluador en T30, que recibirá esta misma salida guardada.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from app.administracion.parametros import ParametrosFuncionales
from app.agentes.contrato import Agente, EstadoAgente
from app.agentes.seccion import AtencionPorAlcance
from app.bd.enumeraciones import TipoAlcance, TipoSolicitud
from app.bd.modelos import VersionBorrador
from app.borradores.alcance import AlcanceInvalido, contar_palabras, validar_alcance
from app.borradores.extraccion import ParrafoBorrador
from app.borradores.secciones import SeccionesVersion
from app.borradores.servicio import parrafos_de, secciones_de
from app.verificacion.comprobaciones import (
    Comprobacion,
    comprobar_citas,
    comprobar_esquema,
    comprobar_limites_propuesta,
)

TIPO = TipoSolicitud.PROPUESTA_REDACCION
PRELIMINARES = "Antes del primer título"


def _no_admitidos(parrafos: list[ParrafoBorrador], secciones: SeccionesVersion | None) -> set[str]:
    """Títulos, párrafos vacíos y la lista de referencias."""
    fuera = {p.id for p in parrafos if p.nivel is not None or not p.texto.strip()}
    lista = secciones.referencias if secciones else None
    if lista is not None:
        orden = [p.id for p in parrafos]
        if lista.desde in orden and lista.hasta in orden:
            fuera |= set(orden[orden.index(lista.desde) : orden.index(lista.hasta) + 1])
    return fuera


def _seccion_de_cada_parrafo(secciones: SeccionesVersion | None) -> dict[str, str]:
    if secciones is None:
        return {}
    return {pid: s.titulo for s in secciones.secciones for pid in s.parrafos}


def parrafos_redactables(version: VersionBorrador) -> list[tuple[str, str, str, int]]:
    """(id, sección, texto, palabras) de los párrafos del cuerpo que admiten una propuesta,
    en el orden del documento. Los que pasan del límite también se listan: la validación
    de la solicitud explica por qué no se procesan (CP-09)."""
    parrafos = parrafos_de(version)
    secciones = secciones_de(version)
    fuera = _no_admitidos(parrafos, secciones)
    seccion = _seccion_de_cada_parrafo(secciones)
    return [
        (p.id, seccion.get(p.id, PRELIMINARES), p.texto, contar_palabras(p.texto))
        for p in parrafos
        if p.id not in fuera
    ]


def parrafo_para_propuesta(
    version: VersionBorrador, referencia: str, parametros: ParametrosFuncionales
) -> str:
    """El texto del párrafo pedido; lanza ``AlcanceInvalido`` si no se admite."""
    parrafos = parrafos_de(version)
    secciones = secciones_de(version)
    resuelto = validar_alcance(
        TIPO, TipoAlcance.FRAGMENTO, referencia, parrafos, secciones, parametros
    )
    if resuelto.alcance_ref in _no_admitidos(parrafos, secciones):
        raise AlcanceInvalido(
            "parrafo_no_admitido",
            "Elija un párrafo del cuerpo del texto: los títulos y la lista de referencias no"
            " reciben propuestas de redacción.",
            parrafo=resuelto.alcance_ref,
        )
    return resuelto.texto


class AgenteRedaccion(Agente):
    tipos = frozenset({TIPO})
    instruccion = "redaccion"

    def consulta(self, estado: EstadoAgente) -> str:
        return (
            "Pautas de redacción académica para un párrafo de un artículo científico empírico:"
            " registro formal e impersonal; fluidez discursiva, conectores y precisión léxica;"
            " corrección gramatical, concordancia, puntuación y claridad sintáctica."
        )

    def tarea(self, estado: EstadoAgente) -> str:
        return (
            "Propón una versión mejorada del párrafo del estudiante (bloque alcance) en los tres"
            " indicadores de redacción, con el mismo contenido, y explica cada cambio con la"
            " pauta de los fragmentos que lo justifica."
        )


class AtencionRedaccion(AtencionPorAlcance):
    alcance_tipo = TipoAlcance.FRAGMENTO

    def resolver(
        self, version: VersionBorrador, referencia: str, parametros: ParametrosFuncionales
    ) -> str:
        return parrafo_para_propuesta(version, referencia, parametros)

    def ajustar(self, salida: dict[str, Any], texto: str) -> dict[str, Any]:
        return {**salida, "original": texto}

    def comprobaciones(
        self,
        salida: dict[str, Any],
        texto: str,
        parametros: ParametrosFuncionales,
        recuperados: Collection[str],
    ) -> list[Comprobacion]:
        return [
            comprobar_esquema(self.tipo, salida),
            comprobar_limites_propuesta(salida, parametros.factor_extension_d3),
            comprobar_citas(salida, recuperados),
        ]
