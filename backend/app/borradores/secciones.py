"""Secciones del borrador, lista de referencias y ``estructura_borrador`` (T12-01).

Todo trabaja sobre los párrafos guardados de la versión (T11): no se vuelve a leer el
.docx. Los identificadores de sección (``s1``, ``s2``...) y de párrafo (``p1``...) son
estables dentro de la versión. Nada de aquí accede a la base ni a un modelo de lenguaje.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.borradores.extraccion import ParrafoBorrador
from app.comun.errores import ErrorAplicacion
from app.corpus.secciones import SeccionExcluida, clasificar_titulo

CLASE_REFERENCIAS = SeccionExcluida.REFERENCIAS.value
MAX_NIVEL = 9


class _Inmutable(BaseModel):
    model_config = ConfigDict(frozen=True)


class Seccion(_Inmutable):
    id: str  # s1, s2... dentro de la versión
    titulo: str
    nivel: int
    clase: str | None  # clase normalizada (IMRaD, otra, referencias), propia o heredada
    padre: str | None
    parrafo_titulo: str
    parrafos: list[str]  # los que siguen al título hasta el próximo título


class ListaReferencias(_Inmutable):
    metodo: Literal["automatica", "manual"]
    seccion: str | None
    desde: str
    hasta: str
    entradas: list[str]


class SeccionesVersion(_Inmutable):
    titulo_documento: str | None
    preliminares: list[str]  # párrafos anteriores al primer título
    secciones: list[Seccion]
    referencias: ListaReferencias | None


class TituloMarcado(_Inmutable):
    parrafo: str
    nivel: int = 1


class SeccionesInvalidas(ErrorAplicacion):
    def __init__(self, mensaje: str, detalle: dict[str, object] | None = None) -> None:
        super().__init__("secciones_invalidas", mensaje, estado_http=422, detalle=detalle)


# ---------------------------------------------------------------------------- detección


def detectar_por_estilos(parrafos: Sequence[ParrafoBorrador]) -> SeccionesVersion | None:
    """Secciones según los estilos de título; ``None`` si el documento no tiene títulos."""
    titulos = {
        p.id: p.nivel
        for p in parrafos
        if p.origen == "cuerpo" and p.nivel is not None and 1 <= p.nivel <= MAX_NIVEL
    }
    if not titulos:
        return None
    titulo_documento = next((p.texto for p in parrafos if p.nivel == 0), None)
    return _construir(parrafos, titulos, titulo_documento)


def marcar_a_mano(
    parrafos: Sequence[ParrafoBorrador], titulos: Sequence[TituloMarcado]
) -> SeccionesVersion:
    """Secciones con los títulos que indicó el caso (respaldo sin estilos, F-05)."""
    if not titulos:
        raise SeccionesInvalidas("Indique al menos un párrafo como título de sección.")
    por_id = {p.id: p for p in parrafos}
    marcados: dict[str, int] = {}
    for titulo in titulos:
        parrafo = por_id.get(titulo.parrafo)
        if parrafo is None:
            raise SeccionesInvalidas(
                "El párrafo indicado no existe en esta versión.", {"parrafo": titulo.parrafo}
            )
        if parrafo.origen != "cuerpo":
            raise SeccionesInvalidas(
                "Un párrafo de una tabla no puede ser título.", {"parrafo": titulo.parrafo}
            )
        if not 1 <= titulo.nivel <= MAX_NIVEL:
            raise SeccionesInvalidas(
                f"El nivel de un título va de 1 a {MAX_NIVEL}.", {"parrafo": titulo.parrafo}
            )
        if titulo.parrafo in marcados:
            raise SeccionesInvalidas(
                "Un párrafo está marcado dos veces.", {"parrafo": titulo.parrafo}
            )
        marcados[titulo.parrafo] = titulo.nivel
    return _construir(parrafos, marcados, titulo_documento=None)


@dataclass
class _Abierta:
    """Sección en construcción."""

    id: str
    titulo: str
    nivel: int
    clase: str | None
    padre: str | None
    parrafo_titulo: str
    parrafos: list[str] = field(default_factory=list)


def _construir(
    parrafos: Sequence[ParrafoBorrador], titulos: dict[str, int], titulo_documento: str | None
) -> SeccionesVersion:
    abiertas: list[_Abierta] = []
    pila: list[_Abierta] = []
    preliminares: list[str] = []
    for parrafo in parrafos:
        nivel = titulos.get(parrafo.id)
        if nivel is None:
            if pila:
                pila[-1].parrafos.append(parrafo.id)
            elif parrafo.nivel != 0:  # el título del documento no es un preliminar
                preliminares.append(parrafo.id)
            continue
        while pila and pila[-1].nivel >= nivel:
            pila.pop()
        padre = pila[-1] if pila else None
        propia = clasificar_titulo(parrafo.texto)
        seccion = _Abierta(
            id=f"s{len(abiertas) + 1}",
            titulo=" ".join(parrafo.texto.split()),
            nivel=nivel,
            clase=propia.value if propia is not None else (padre.clase if padre else None),
            padre=padre.id if padre else None,
            parrafo_titulo=parrafo.id,
        )
        abiertas.append(seccion)
        pila.append(seccion)
    secciones = [Seccion.model_validate(asdict(s)) for s in abiertas]
    return SeccionesVersion(
        titulo_documento=titulo_documento,
        preliminares=preliminares,
        secciones=secciones,
        referencias=_referencias_automaticas(secciones, parrafos),
    )


# ---------------------------------------------------------------------------- referencias


def descendientes(secciones: Sequence[Seccion], seccion_id: str) -> list[Seccion]:
    """La sección y todas sus subsecciones, en orden del documento."""
    incluidas = {seccion_id}
    resultado: list[Seccion] = []
    for seccion in secciones:
        if seccion.id == seccion_id or seccion.padre in incluidas:
            incluidas.add(seccion.id)
            resultado.append(seccion)
    return resultado


def _entradas(parrafos: Iterable[ParrafoBorrador]) -> list[str]:
    return [linea.strip() for p in parrafos for linea in p.texto.split("\n") if linea.strip()]


def _referencias_automaticas(
    secciones: Sequence[Seccion], parrafos: Sequence[ParrafoBorrador]
) -> ListaReferencias | None:
    seccion = next((s for s in secciones if s.clase == CLASE_REFERENCIAS), None)
    if seccion is None:
        return None
    rama = descendientes(secciones, seccion.id)
    ids = {pid for s in rama for pid in s.parrafos}
    contenido = [p for p in parrafos if p.id in ids]
    if not contenido:
        return None
    return ListaReferencias(
        metodo="automatica",
        seccion=seccion.id,
        desde=contenido[0].id,
        hasta=contenido[-1].id,
        entradas=_entradas(contenido),
    )


def referencias_a_mano(
    actuales: SeccionesVersion | None,
    parrafos: Sequence[ParrafoBorrador],
    desde: str,
    hasta: str | None,
) -> SeccionesVersion:
    """Indica a mano dónde está la lista de referencias (de ``desde`` a ``hasta``)."""
    orden = {p.id: i for i, p in enumerate(parrafos)}
    final = hasta or (parrafos[-1].id if parrafos else desde)
    for pid in (desde, final):
        if pid not in orden:
            raise SeccionesInvalidas(
                "El párrafo indicado no existe en esta versión.", {"parrafo": pid}
            )
    if orden[desde] > orden[final]:
        raise SeccionesInvalidas("El primer párrafo de la lista va antes que el último.")
    contenido = list(parrafos[orden[desde] : orden[final] + 1])
    base = actuales or SeccionesVersion(
        titulo_documento=None, preliminares=[], secciones=[], referencias=None
    )
    seccion = next(
        (s.id for s in base.secciones if desde in s.parrafos or s.parrafo_titulo == desde), None
    )
    lista = ListaReferencias(
        metodo="manual", seccion=seccion, desde=desde, hasta=final, entradas=_entradas(contenido)
    )
    return base.model_copy(update={"referencias": lista})


# ---------------------------------------------------------------- estructura_borrador


class NodoSeccion(_Inmutable):
    id: str
    titulo: str
    nivel: int
    clase: str | None
    hijos: list[NodoSeccion]


Elemento = Literal["problema", "objetivos", "hipotesis"]


class Ubicacion(_Inmutable):
    elemento: Elemento
    seccion: str | None
    parrafo: str
    por: Literal["titulo", "texto"]


class EstructuraBorrador(_Inmutable):
    titulo_documento: str | None
    metodo: str | None
    arbol: list[NodoSeccion]
    seccion_referencias: str | None
    ubicaciones: list[Ubicacion]


# Pistas en español y en inglés (decisión T12-01, apartado 5).
_POR_TITULO: dict[Elemento, re.Pattern[str]] = {
    "problema": re.compile(
        r"\b(planteamiento del problema|problema de investigaci[oó]n|problem statement"
        r"|research problem|preguntas? de investigaci[oó]n|research questions?)\b",
        re.IGNORECASE,
    ),
    "objetivos": re.compile(r"\b(objetivos?|aims?|objectives?)\b", re.IGNORECASE),
    "hipotesis": re.compile(r"\b(hip[oó]tesis|hypothes[ie]s)\b", re.IGNORECASE),
}
_POR_TEXTO: dict[Elemento, re.Pattern[str]] = {
    "problema": re.compile(
        r"(¿[^?¿]{10,}\?|\bproblema de investigaci[oó]n\b|\bpregunta de investigaci[oó]n\b"
        r"|\bresearch (?:problem|question)\b|\bproblem statement\b)",
        re.IGNORECASE,
    ),
    "objetivos": re.compile(
        r"\b(el objetivo (?:general |principal )?(?:de|del|fue|es)\b|los objetivos\b"
        r"|objetivo general\b|objetivos espec[ií]ficos\b|se (?:propuso|planteó como objetivo)"
        r"|tuvo como (?:objetivo|propósito)|el propósito de (?:este|esta|la|el)\b"
        r"|the (?:aim|objective|purpose) of (?:this|the)\b|this study aim)",
        re.IGNORECASE,
    ),
    "hipotesis": re.compile(
        r"(\bH[0-9]+\s*[:.)]|\bH[ao]\s*[:.)]|\bla hip[oó]tesis\b|\bse hipotetiz"
        r"|\bhypothes[ie]s\b|\bwe hypothesi[sz]ed\b)",
        re.IGNORECASE,
    ),
}


def estructura_borrador(
    parrafos: Sequence[ParrafoBorrador],
    secciones: SeccionesVersion | None,
    metodo: str | None,
) -> EstructuraBorrador:
    """Árbol de títulos y ubicación de problema, objetivos e hipótesis (herramienta de D1
    y D2). Las ubicaciones son pistas para el agente, que lee el texto."""
    lista = list(secciones.secciones) if secciones else []
    referencias = secciones.referencias if secciones else None
    excluidos: set[str] = set()
    if referencias is not None:
        orden = [p.id for p in parrafos]
        if referencias.desde in orden and referencias.hasta in orden:
            primero, ultimo = orden.index(referencias.desde), orden.index(referencias.hasta)
            excluidos = set(orden[primero : ultimo + 1])
    seccion_de = {pid: s.id for s in lista for pid in s.parrafos}
    ramas_excluidas = (
        {s.id for s in descendientes(lista, referencias.seccion)}
        if referencias is not None and referencias.seccion
        else set()
    )
    ubicaciones: list[Ubicacion] = []
    for seccion in lista:
        if seccion.id in ramas_excluidas:
            continue
        for elemento, patron in _POR_TITULO.items():
            if patron.search(seccion.titulo):
                ubicaciones.append(
                    Ubicacion(
                        elemento=elemento,
                        seccion=seccion.id,
                        parrafo=seccion.parrafo_titulo,
                        por="titulo",
                    )
                )
    titulos = {s.parrafo_titulo for s in lista}
    for parrafo in parrafos:
        if (
            parrafo.origen != "cuerpo"
            or parrafo.id in excluidos
            or parrafo.id in titulos
            or seccion_de.get(parrafo.id) in ramas_excluidas
        ):
            continue
        for elemento, patron in _POR_TEXTO.items():
            if patron.search(parrafo.texto):
                ubicaciones.append(
                    Ubicacion(
                        elemento=elemento,
                        seccion=seccion_de.get(parrafo.id),
                        parrafo=parrafo.id,
                        por="texto",
                    )
                )
    return EstructuraBorrador(
        titulo_documento=secciones.titulo_documento if secciones else None,
        metodo=metodo,
        arbol=_arbol(lista, None),
        seccion_referencias=referencias.seccion if referencias else None,
        ubicaciones=ubicaciones,
    )


def _arbol(secciones: Sequence[Seccion], padre: str | None) -> list[NodoSeccion]:
    return [
        NodoSeccion(
            id=s.id,
            titulo=s.titulo,
            nivel=s.nivel,
            clase=s.clase,
            hijos=_arbol(secciones, s.id),
        )
        for s in secciones
        if s.padre == padre
    ]
