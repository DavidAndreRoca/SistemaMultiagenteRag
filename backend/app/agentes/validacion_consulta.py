"""Validación previa de la consulta de evidencia (T19-01, apartado 3; Fase 1, 7.2).

Antes de encolar, sin modelo de lenguaje:

1. **Reglas:** longitud (``muy_corta``, ``muy_larga``), pedidos fuera de lo que el sistema
   hace (redactar, escribir, corregir o traducir partes del artículo: ``fuera_de_alcance``)
   y consultas sin una afirmación o pregunta concreta (``ambigua``).
2. **Pertinencia:** la similitud coseno máxima entre la consulta (bge-m3) y los fragmentos
   de las colecciones permitidas del caso debe alcanzar ``pertinencia_umbral``; si no, es
   ``fuera_de_alcance``. Es una sola búsqueda densa, sin reranking.

Una consulta rechazada no se encola: se responde qué se puede pedir, con un ejemplo, y el
motivo queda en la solicitud. El registro guarda el motivo, nunca la consulta (4.6).
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.administracion.parametros import ParametrosFuncionales
from app.bd.enumeraciones import TipoSolicitud
from app.inferencia.interfaces import ProveedorEmbeddings
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.recuperacion import PALABRAS_VACIAS
from app.repositorios.unidad import UnidadDeTrabajo

EJEMPLO = (
    "Por ejemplo: «Quiero sustentar que la tutoría entre pares reduce la ansiedad ante la"
    " estadística» o «¿Qué evidencia hay sobre el uso de ChatGPT en la retroalimentación"
    " académica?»."
)


class MotivoRechazo(StrEnum):
    MUY_CORTA = "muy_corta"
    MUY_LARGA = "muy_larga"
    AMBIGUA = "ambigua"
    FUERA_DE_ALCANCE = "fuera_de_alcance"


MENSAJES = {
    MotivoRechazo.MUY_CORTA: "La consulta es muy breve. Escriba la afirmación que quiere"
    " sustentar o la pregunta que quiere responder, en una oración completa. " + EJEMPLO,
    MotivoRechazo.MUY_LARGA: "La consulta es muy larga. Resuma en una o dos oraciones la"
    " afirmación o la pregunta para la que busca evidencia. " + EJEMPLO,
    MotivoRechazo.AMBIGUA: "No se entiende qué evidencia busca. Indique una afirmación"
    " concreta que quiera sustentar o una pregunta precisa sobre su tema. " + EJEMPLO,
    MotivoRechazo.FUERA_DE_ALCANCE: "Esta solicitud está fuera de lo que el sistema puede"
    " hacer en la búsqueda de evidencia: el sistema busca evidencia en las fuentes de su tema"
    " para una afirmación o una pregunta, pero no redacta ni corrige partes del artículo ni"
    " responde consultas ajenas a su tema. " + EJEMPLO,
}

# Pedidos de redactar o transformar texto (Fase 1, 7.2: «redacta», «escribe la sección»).
_VERBOS = (
    r"redact\w*|escrib\w*|hazme|haz|haga|hag\w*|gener\w*|elabor\w*|corrig\w*|correg\w*"
    r"|parafrase\w*|reescrib\w*|traduc\w*|resum\w*|complet\w*|termin\w*"
)
_PIEZAS = (
    r"introduccion|seccion|articulo|parrafo|texto|tesis|conclusion\w*|resumen|abstract"
    r"|discusion|marco teorico|metodologia|antecedentes|trabajo|tarea|ensayo|borrador|todo"
)
_FUERA = re.compile(rf"\b({_VERBOS})\b(?:\W+\w+){{0,6}}?\W+\b({_PIEZAS})\b")
_AMBIGUAS = re.compile(
    r"^(que opinas|que piensas|ayudame|ayuda|dime algo|tengo una duda|no se|que hago"
    r"|cualquier cosa|lo que sea|informacion|algo sobre)\b"
)
MIN_PALABRAS_CON_CONTENIDO = 3
# Palabras que no dicen de qué trata la consulta: no cuentan como contenido.
_VAGAS = frozenset(
    [
        "algo",
        "esto",
        "eso",
        "aquello",
        "cosa",
        "cosas",
        "tema",
        "temas",
        "trabajo",
        "saber",
        "sobre",
        "tener",
        "hacer",
        "quiero",
        "necesito",
        "favor",
        "ayuda",
        "ayudame",
        "dime",
        "puedes",
        "podrias",
        "gracias",
        "informacion",
    ]
)


class Rechazo(BaseModel):
    model_config = ConfigDict(frozen=True)

    motivo: MotivoRechazo
    mensaje: str
    similitud: float | None = None  # del clasificador de pertinencia, si llegó a él


def _normalizada(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.split())


def _rechazo(motivo: MotivoRechazo, similitud: float | None = None) -> Rechazo:
    return Rechazo(motivo=motivo, mensaje=MENSAJES[motivo], similitud=similitud)


def por_reglas(consulta: str, parametros: ParametrosFuncionales) -> Rechazo | None:
    texto = consulta.strip()
    if len(texto) > parametros.consulta_max_caracteres:
        return _rechazo(MotivoRechazo.MUY_LARGA)
    palabras = re.findall(r"\w+", texto)
    if len(palabras) < parametros.consulta_min_palabras:
        return _rechazo(MotivoRechazo.MUY_CORTA)
    normal = _normalizada(texto)
    if _FUERA.search(normal):
        return _rechazo(MotivoRechazo.FUERA_DE_ALCANCE)
    con_contenido = [
        p
        for p in re.findall(r"\w+", normal)
        if len(p) > 3 and p not in PALABRAS_VACIAS and p not in _VAGAS
    ]
    if _AMBIGUAS.match(normal.lstrip("¿¡ ")) or len(con_contenido) < MIN_PALABRAS_CON_CONTENIDO:
        return _rechazo(MotivoRechazo.AMBIGUA)
    return None


async def validar(
    unidad: UnidadDeTrabajo,
    contexto: ContextoAcceso,
    consulta: str,
    parametros: ParametrosFuncionales,
    embeddings: ProveedorEmbeddings,
) -> Rechazo | None:
    """``None`` si la consulta se puede encolar; si no, el rechazo con su mensaje."""
    rechazo = por_reglas(consulta, parametros)
    if rechazo is not None:
        return rechazo
    vector = (await embeddings.embeber([consulta.strip()])).vectores[0]
    mejores = await unidad.recuperacion.buscar_denso(
        contexto, TipoSolicitud.BUSQUEDA_EVIDENCIA, vector, 1
    )
    similitud = mejores[0].puntaje if mejores else 0.0
    if similitud < parametros.pertinencia_umbral:
        return _rechazo(MotivoRechazo.FUERA_DE_ALCANCE, round(similitud, 4))
    return None
