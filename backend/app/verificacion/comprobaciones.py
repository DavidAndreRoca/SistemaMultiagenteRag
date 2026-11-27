"""Comprobaciones deterministas 1, 2, 3 y 5 del módulo de verificación (6.7; D-07; T18-01).

Viven fuera de los agentes para que el módulo de integración y verificación (T30) las
reutilice sobre la salida guardada de cualquier tipo.

1. **Esquema del tipo:** la salida cumple el esquema Pydantic de su tipo.
2. **Límites del tipo:** D1 y D2 no reescriben (T23, CP-08); D2 no da números que no estén
   en el texto del estudiante o en un fragmento citado (T26); la propuesta de D3 no pasa de
   1.2 veces el original ni agrega datos o citas (T27, CP-10).
3. **Citas:** todo identificador ``F<n>`` de la salida, en los campos ``citas`` o dentro de
   un texto, está entre los fragmentos recuperados para esa solicitud.

Los motivos nombran campos e identificadores, nunca el contenido (4.6).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterator, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.agentes.esquemas import ESQUEMAS
from app.bd.enumeraciones import TipoSolicitud
from app.borradores.alcance import contar_palabras

_IDENTIFICADOR = re.compile(r"\bF[1-9][0-9]*\b")


class Comprobacion(BaseModel):
    model_config = ConfigDict(frozen=True)

    numero: int
    nombre: str
    superada: bool
    motivos: list[str] = []


def comprobar_esquema(tipo: TipoSolicitud, salida: Any) -> Comprobacion:
    """Comprobación 1: la salida (``dict`` o modelo) cumple el esquema de su tipo."""
    esquema = ESQUEMAS[tipo]
    datos = salida.model_dump(mode="json") if isinstance(salida, BaseModel) else salida
    try:
        esquema.model_validate(datos)
    except ValidationError as error:
        motivos = [
            f"{'.'.join(str(p) for p in e['loc']) or '(raíz)'}: {e['type']}"
            for e in error.errors(include_input=False, include_url=False)
        ]
        return Comprobacion(numero=1, nombre="esquema", superada=False, motivos=motivos[:20])
    return Comprobacion(numero=1, nombre="esquema", superada=True)


def identificadores_citados(salida: Any) -> list[str]:
    """Todos los ``F<n>`` de la salida, en el orden en que aparecen y sin repetir."""
    datos = salida.model_dump(mode="json") if isinstance(salida, BaseModel) else salida
    return list(dict.fromkeys(_recorrer(datos)))


def _recorrer(valor: Any) -> Iterator[str]:
    if isinstance(valor, str):
        yield from _IDENTIFICADOR.findall(valor)
    elif isinstance(valor, dict):
        for sub in valor.values():
            yield from _recorrer(sub)
    elif isinstance(valor, list | tuple):
        for sub in valor:
            yield from _recorrer(sub)


def comprobar_citas(salida: Any, recuperados: Collection[str]) -> Comprobacion:
    """Comprobación 3: cada cita existe entre los fragmentos recuperados de la solicitud."""
    disponibles = set(recuperados)
    inexistentes = [i for i in identificadores_citados(salida) if i not in disponibles]
    if inexistentes:
        return Comprobacion(
            numero=3,
            nombre="citas",
            superada=False,
            motivos=[f"cita a un fragmento no recuperado: {i}" for i in inexistentes],
        )
    return Comprobacion(numero=3, nombre="citas", superada=True)


# Estados de Unpaywall que comprueban el acceso abierto (RN-14). ``closed`` y
# ``desconocido`` no: una fuente sin acceso abierto comprobado no se recomienda.
ACCESO_ABIERTO_COMPROBADO = frozenset({"gold", "green", "hybrid", "bronze"})


def comprobar_acceso_abierto(estado_oa_por_cita: Mapping[str, str | None]) -> Comprobacion:
    """Comprobación 5 (CP-11): toda cita es de un documento con acceso abierto comprobado.

    ``estado_oa_por_cita`` da, para cada identificador citado, el estado de acceso
    abierto del documento al que pertenece.
    """
    sin_acceso = [
        i for i, estado in estado_oa_por_cita.items() if estado not in ACCESO_ABIERTO_COMPROBADO
    ]
    if sin_acceso:
        return Comprobacion(
            numero=5,
            nombre="acceso_abierto",
            superada=False,
            motivos=[f"cita a una fuente sin acceso abierto comprobado: {i}" for i in sin_acceso],
        )
    return Comprobacion(numero=5, nombre="acceso_abierto", superada=True)


# --- Comprobación 2 para D1 y D2: no reescritura (T23; CP-08) -----------------------------

CAMPOS_DE_TEXTO = (
    "descripcion",
    "recomendacion",
    "fortalezas",
    "preguntas_al_estudiante",
    "notas_para_el_estudiante",
    "tarea",
    "criterio_de_logro",
)
_COMILLAS = re.compile(r"[\"“”«»]([^\"“”«»]+)[\"“”«»]")


def _palabras(texto: str) -> list[str]:
    return re.findall(r"\w+", texto.lower())


def _textos_con_ruta(valor: Any, ruta: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(valor, str):
        yield ruta, valor
    elif isinstance(valor, dict):
        for clave, contenido in valor.items():
            yield from _textos_con_ruta(contenido, f"{ruta}.{clave}" if ruta else clave)
    elif isinstance(valor, list):
        for indice, contenido in enumerate(valor):
            yield from _textos_con_ruta(contenido, f"{ruta}[{indice}]")


def comprobar_no_reescritura(salida: Any, texto_estudiante: str, limite: int) -> Comprobacion:
    """Comprobación 2 (D1 y D2): ningún texto de la salida tiene más de ``limite`` palabras
    propias, sin contar lo que cita entre comillas del propio estudiante. Un texto más largo
    sería una versión reescrita de la sección, que estos agentes no entregan (CP-08)."""
    datos = salida.model_dump(mode="json") if isinstance(salida, BaseModel) else salida
    estudiante = " ".join(_palabras(texto_estudiante))
    motivos: list[str] = []
    for ruta, texto in _textos_con_ruta(datos):
        campo = re.sub(r"\[\d+\]", "", ruta.split(".")[-1])
        if campo not in CAMPOS_DE_TEXTO:
            continue
        propio = texto
        for cita in _COMILLAS.findall(texto):
            if " ".join(_palabras(cita)) in estudiante:
                propio = propio.replace(cita, " ")
        cantidad = len(_palabras(propio))
        if cantidad > limite:
            motivos.append(f"posible reescritura en {ruta}: {cantidad} palabras (límite {limite})")
    return Comprobacion(
        numero=2, nombre="no_reescritura", superada=not motivos, motivos=motivos[:20]
    )


# --- Comprobación 2 para D3: límites de la propuesta (T27; CP-10, RN-07) -------------------

_PARRAFOS = re.compile(r"\n\s*\n")
_NUMERO = re.compile(r"\d+(?:[.,]\d+)*")
_CITA_EN_TEXTO = re.compile(r"\[[^\[\]]*\d[^\[\]]*\]|\([^()]*\d[^()]*\)")


def _marcas(texto: str) -> set[str]:
    """Números y citas entre corchetes o paréntesis, sin espacios, para compararlos."""
    return {re.sub(r"\s+", "", m) for m in _NUMERO.findall(texto)} | {
        re.sub(r"\s+", "", m) for m in _CITA_EN_TEXTO.findall(texto)
    }


def _contiene(texto: str, parte: str) -> bool:
    return " ".join(_palabras(parte)) in " ".join(_palabras(texto))


def comprobar_limites_propuesta(salida: Any, factor: float) -> Comprobacion:
    """Comprobación 2 (D3) sobre una salida cuyo ``original`` es el párrafo del estudiante:

    * la propuesta tiene hasta ``factor`` veces las palabras del original (CP-10);
    * es un solo párrafo;
    * no agrega números ni citas que el original no tenga (D3 no añade datos ni citas;
      la conservación del resto del contenido la juzga el evaluador de T30);
    * cada cambio explicado está en el original (``antes``) y en la propuesta (``despues``).
    """
    datos = salida.model_dump(mode="json") if isinstance(salida, BaseModel) else salida
    original = str(datos.get("original", ""))
    propuesta = str(datos.get("propuesta", ""))
    motivos: list[str] = []
    palabras_original = contar_palabras(original)
    palabras_propuesta = contar_palabras(propuesta)
    limite = int(palabras_original * factor)
    if palabras_propuesta > limite:
        motivos.append(
            f"la propuesta tiene {palabras_propuesta} palabras y el límite es {limite}"
            f" ({factor:g} veces las {palabras_original} del original)"
        )
    if _PARRAFOS.search(propuesta.strip()):
        motivos.append("la propuesta tiene más de un párrafo")
    nuevas = sorted(_marcas(propuesta) - _marcas(original))
    if nuevas:
        motivos.append(
            f"la propuesta agrega {len(nuevas)} números o citas que no están en el original"
        )
    for indice, cambio in enumerate(datos.get("cambios", [])):
        if not isinstance(cambio, dict):
            continue
        if not _contiene(original, str(cambio.get("antes", ""))):
            motivos.append(f"cambios[{indice}].antes no está en el original")
        if not _contiene(propuesta, str(cambio.get("despues", ""))):
            motivos.append(f"cambios[{indice}].despues no está en la propuesta")
    return Comprobacion(
        numero=2, nombre="limites_propuesta", superada=not motivos, motivos=motivos[:20]
    )


# --- Comprobación 2 para D2: ningún dato inventado (T26) -----------------------------------

# Números sueltos: no los que siguen a una letra o a un guion, como "p12", "H1" o "COR-6",
# que son identificadores de párrafo, hipótesis o criterio.
_NUMERO_SUELTO = re.compile(r"(?<![\w-])\d+(?:[.,]\d+)?")


def numeros(texto: str) -> set[str]:
    """Números del texto, con la coma decimal como punto."""
    return {m.replace(",", ".") for m in _NUMERO_SUELTO.findall(texto)}


def comprobar_numeros(
    salida: Any, texto_estudiante: str, textos_recuperados: Mapping[str, str]
) -> Comprobacion:
    """Comprobación 2 (D2): cada número de los textos de la salida está en la sección del
    estudiante o en un fragmento que la salida cita. Un tamaño de muestra, un coeficiente o
    un valor p que no está en ninguno sería un dato inventado."""
    datos = salida.model_dump(mode="json") if isinstance(salida, BaseModel) else salida
    citados = set(identificadores_citados(datos))
    permitidos = numeros(texto_estudiante)
    for identificador, texto in textos_recuperados.items():
        if identificador in citados:
            permitidos |= numeros(texto)
    motivos: list[str] = []
    for ruta, texto in _textos_con_ruta(datos):
        campo = re.sub(r"\[\d+\]", "", ruta.split(".")[-1])
        if campo not in CAMPOS_DE_TEXTO:
            continue
        ajenos = sorted(numeros(texto) - permitidos)
        if ajenos:
            motivos.append(
                f"dato posiblemente inventado en {ruta}: {len(ajenos)} números que no están en"
                " el texto del estudiante ni en un fragmento citado"
            )
    return Comprobacion(
        numero=2, nombre="sin_datos_inventados", superada=not motivos, motivos=motivos[:20]
    )
