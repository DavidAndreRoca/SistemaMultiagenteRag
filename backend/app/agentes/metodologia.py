"""Agente D2 metodológico: diagnóstico de una sección (T26; RF-06, CU-05, CP-03, CP-08).

* **Diseño:** ``identificar_diseno`` lo reconoce en el texto de la sección por su nombre
  (experimental, cuasiexperimental, correlacional o descriptivo). Si no es identificable,
  la tarea pide preguntarlo en ``preguntas_al_estudiante`` y no suponerlo.
* **Herramienta ``lista_de_comprobacion(diseno)``:** lee del corpus de guías (T22) los
  criterios del apartado del diseño y los comunes a todos los diseños. Esos criterios,
  abreviados, son la consulta de recuperación, así que la lista llega al modelo como
  fragmentos citables (con una consulta abstracta, el reordenador no la traía; con el texto
  completo, solo la del diseño superaba el umbral: pruebas de T26-01).
* **Comprobaciones** (``AtencionMetodologia``): 1 (esquema), 3 (citas) y 2 para D2, que son
  dos: no reescritura (CP-08) y ningún número que no esté en el texto del estudiante o en
  un fragmento citado (D2 no inventa datos ni valores estadísticos).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from app.administracion.parametros import ParametrosFuncionales
from app.agentes.contrato import Agente, EstadoAgente
from app.agentes.estructura import titulo_de_seccion
from app.agentes.seccion import AtencionSeccion
from app.bd.enumeraciones import TipoSolicitud
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import (
    Comprobacion,
    comprobar_citas,
    comprobar_esquema,
    comprobar_no_reescritura,
    comprobar_numeros,
)

TIPO = TipoSolicitud.REVISION_METODOLOGICA
APARTADO_COMUN = "Elementos comunes a todos los diseños"
MAX_CARACTERES_CONSULTA = 2000
PALABRAS_POR_CRITERIO = 9
_CODIGO_CRITERIO = re.compile(r"\b[A-Z]{2,5}-\d+\.\s*")


class Diseno(StrEnum):
    EXPERIMENTAL = "experimental"
    CUASIEXPERIMENTAL = "cuasiexperimental"
    CORRELACIONAL = "correlacional"
    DESCRIPTIVO = "descriptivo"


APARTADOS = {d: f"Diseño {d.value}" for d in Diseno}


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def identificar_diseno(texto: str) -> Diseno | None:
    """El diseño que declara el texto, o ``None`` si no se nombra.

    Si nombra varios (por ejemplo, "descriptivo correlacional"), gana el más exigente:
    cuasiexperimental, experimental, correlacional y descriptivo. "No experimental" no
    cuenta como experimental.
    """
    normal = _normalizar(texto).replace("-", " ")
    if re.search(r"\bcuasi ?experimental", normal):
        return Diseno.CUASIEXPERIMENTAL
    sin_negacion = re.sub(r"\bno experimental", " ", normal)
    if re.search(r"\bexperiment(al|o)\b", sin_negacion):
        return Diseno.EXPERIMENTAL
    if re.search(r"\bcorrelacional", normal):
        return Diseno.CORRELACIONAL
    if re.search(r"\bdescriptiv[oa]", normal):
        return Diseno.DESCRIPTIVO
    return None


async def lista_de_comprobacion(
    unidad: UnidadDeTrabajo, contexto: ContextoAcceso, diseno: Diseno | None
) -> list[str]:
    """Criterios mínimos del diseño (y los comunes) tal como están en el corpus de guías."""
    apartados = [APARTADO_COMUN] if diseno is None else [APARTADOS[diseno], APARTADO_COMUN]
    fragmentos = await unidad.recuperacion.por_apartado(contexto, TIPO, apartados)
    return [f.texto for f in fragmentos]


def comprimir_criterios(textos: list[str], palabras: int = PALABRAS_POR_CRITERIO) -> str:
    """Las primeras palabras de cada criterio, sin su código (``COR-6.``), separadas por
    punto y coma. Con el texto completo, el reordenador puntuaba alto solo la lista del
    diseño y no la de elementos comunes (T26-01)."""
    partes: list[str] = []
    for texto in textos:
        for criterio in _CODIGO_CRITERIO.split(texto):
            limpio = " ".join(criterio.split()).rstrip(".")
            if limpio:
                partes.append(" ".join(limpio.split()[:palabras]))
    return "; ".join(partes)


def consulta_de_lista(diseno: Diseno | None, criterios: list[str]) -> str:
    """La consulta de recuperación a partir de la lista de comprobación del corpus."""
    if diseno is None:
        inicio = (
            "Criterios mínimos que debe informar la sección de método de un artículo empírico,"
            " sea cual sea su diseño: "
        )
    else:
        inicio = (
            f"Criterios mínimos del diseño {diseno.value} y elementos comunes a todos los diseños: "
        )
    return (inicio + comprimir_criterios(criterios) + ".")[:MAX_CARACTERES_CONSULTA]


class AgenteMetodologia(Agente):
    tipos = frozenset({TIPO})
    instruccion = "metodologia"

    def consulta(self, estado: EstadoAgente) -> str:
        """Sin lista en el corpus: una consulta general sobre el método."""
        diseno = identificar_diseno(estado.alcance)
        nombre = f"del diseño {diseno.value}" if diseno else "de cualquier diseño"
        return (
            f"Criterios mínimos que debe informar la metodología {nombre}: diseño, muestra,"
            " instrumentos y su validez, y análisis de datos."
        )

    async def consulta_con_herramientas(
        self, unidad: UnidadDeTrabajo, contexto: ContextoAcceso, estado: EstadoAgente
    ) -> str:
        diseno = identificar_diseno(estado.alcance)
        criterios = await lista_de_comprobacion(unidad, contexto, diseno)
        if not criterios:
            return self.consulta(estado)
        return consulta_de_lista(diseno, criterios)

    def tarea(self, estado: EstadoAgente) -> str:
        diseno = identificar_diseno(estado.alcance)
        seccion = titulo_de_seccion(estado.alcance)
        if diseno is None:
            sobre_diseno = (
                " La sección no nombra su diseño de investigación: no lo supongas; pregunta en"
                " preguntas_al_estudiante cuál es y revisa solo los elementos comunes."
            )
        else:
            sobre_diseno = (
                f" La sección declara un diseño {diseno.value}: revisa con su lista de"
                " comprobación y con los elementos comunes."
            )
        return (
            f"Diagnostica la sección «{seccion}» del estudiante (bloque alcance) en los tres"
            " indicadores metodológicos, usando como criterio los fragmentos de las guías."
            + sobre_diseno
            + " Pregunta lo que falta en lugar de inventarlo. No la reescribas."
        )


class AtencionMetodologia(AtencionSeccion):
    def comprobaciones(
        self,
        salida: dict[str, Any],
        texto: str,
        parametros: ParametrosFuncionales,
        recuperados: Mapping[str, str],
    ) -> list[Comprobacion]:
        return [
            comprobar_esquema(self.tipo, salida),
            comprobar_no_reescritura(salida, texto, parametros.limite_reescritura_palabras),
            comprobar_numeros(salida, texto, recuperados),
            comprobar_citas(salida, recuperados),
        ]
