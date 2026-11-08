"""Segmentación por sección y párrafos con ventana de tokens (T09, actividad 5; 18.4).

Primero por sección (las subsecciones consecutivas de la misma sección normalizada
forman un tramo), después por párrafos: se agrupan párrafos consecutivos hasta la
ventana configurada (inicial 300 a 450 tokens) y cada fragmento empieza con la última
oración del anterior (solapamiento de una oración). Reglas (decisión T09-01, apartado 5):

* Un párrafo entero entra si cabe. Si no cabe y el fragmento ya alcanzó el mínimo, se
  cierra en el borde del párrafo; si no lo alcanzó, se completa oración por oración.
* Ningún fragmento supera el máximo: una oración más larga que el máximo se parte por
  palabras. El solapamiento se omite si no deja espacio para contenido nuevo.
* El último fragmento de una sección puede quedar por debajo del mínimo: no se une al
  anterior, porque si el anterior se cerró es que lo siguiente no cabía en él.
* Las secciones no se mezclan ni se solapan entre sí.
* Las páginas del fragmento son las de sus párrafos, incluida la oración de solapamiento.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import groupby
from typing import Protocol

from app.administracion.parametros import VentanaTokens
from app.corpus.esquemas import FragmentoProcesado
from app.corpus.secciones import SeccionTexto


class ContadorTokens(Protocol):
    """Cuenta tokens con el tokenizador del modelo de embeddings, sin tokens especiales."""

    def contar(self, texto: str) -> int: ...


ABREVIATURAS = frozenset(
    {
        "al", "e.g", "i.e", "etc", "fig", "figs", "tab", "eq", "eqs", "ec", "vs", "cf",
        "pp", "vol", "vols", "nos", "nro", "núm", "num", "sr", "sra", "srta", "dr", "dra",
        "prof", "lic", "ing", "mg", "aprox", "approx", "ca", "ed", "eds", "comp", "coord",
        "art", "cap", "pág", "págs", "pag", "inc", "ltd", "jr", "mr", "mrs", "ms", "u.s",
        "u.k", "ee.uu", "resp", "op", "cit", "ibid", "sec", "dept", "univ", "et",
    }
)  # fmt: skip
FRONTERA = re.compile(r"([.!?…]+)([\"”»')\]]*)\s+(?=[\"“«(\[¿¡]?[A-ZÁÉÍÓÚÑÜ0-9])")


def dividir_oraciones(texto: str) -> list[str]:
    """Divide en oraciones (español e inglés) sin cortar abreviaturas ni iniciales."""
    oraciones: list[str] = []
    inicio = 0
    for frontera in FRONTERA.finditer(texto):
        if frontera.group(1) == "." and _termina_en_abreviatura(texto[inicio : frontera.start()]):
            continue
        oraciones.append(texto[inicio : frontera.end(2)].strip())
        inicio = frontera.end()
    resto = texto[inicio:].strip()
    if resto:
        oraciones.append(resto)
    return [o for o in oraciones if o]


def _termina_en_abreviatura(previo: str) -> bool:
    palabras = previo.split()
    if not palabras:
        return False
    ultima = palabras[-1].lower().strip("\"'«“(")
    return ultima in ABREVIATURAS or (len(ultima) == 1 and ultima.isalpha())


@dataclass(frozen=True)
class _Oracion:
    texto: str
    tokens: int
    pagina_inicio: int
    pagina_fin: int
    parrafo: int
    titulo: str | None


def _partir_oracion(oracion: _Oracion, maximo: int, contador: ContadorTokens) -> list[_Oracion]:
    """Parte por palabras una oración que supera el máximo de tokens."""
    piezas: list[_Oracion] = []
    actual: list[str] = []
    for palabra in oracion.texto.split():
        candidata = " ".join([*actual, palabra])
        if actual and contador.contar(candidata) > maximo:
            texto = " ".join(actual)
            piezas.append(_reemplazar(oracion, texto, contador.contar(texto)))
            actual = [palabra]
        else:
            actual.append(palabra)
    texto = " ".join(actual)
    piezas.append(_reemplazar(oracion, texto, contador.contar(texto)))
    return piezas


def _reemplazar(oracion: _Oracion, texto: str, tokens: int) -> _Oracion:
    return _Oracion(
        texto, tokens, oracion.pagina_inicio, oracion.pagina_fin, oracion.parrafo, oracion.titulo
    )


def _tokens(oraciones: Sequence[_Oracion]) -> int:
    return sum(o.tokens for o in oraciones)


@dataclass
class _Fragmento:
    oraciones: list[_Oracion]
    solapadas: int  # cuántas oraciones iniciales vienen del fragmento anterior

    @property
    def nuevas(self) -> list[_Oracion]:
        return self.oraciones[self.solapadas :]


class _Empaquetador:
    def __init__(self, ventana: VentanaTokens, solapamiento: int) -> None:
        self.ventana = ventana
        self.solapamiento = solapamiento
        self.listos: list[_Fragmento] = []
        self.actual = _Fragmento([], 0)

    def _cabe(self, tokens: int) -> bool:
        return _tokens(self.actual.oraciones) + tokens <= self.ventana.maximo

    def _cerrar(self) -> None:
        if not self.actual.nuevas:
            return
        self.listos.append(self.actual)
        solape = self.actual.oraciones[-self.solapamiento :] if self.solapamiento else []
        if _tokens(solape) > self.ventana.maximo - self.ventana.minimo:
            solape = []
        self.actual = _Fragmento(list(solape), len(solape))

    def agregar_parrafo(self, oraciones: list[_Oracion]) -> None:
        total = _tokens(oraciones)
        if self._cabe(total):
            self.actual.oraciones += oraciones
            return
        if _tokens(self.actual.nuevas) >= self.ventana.minimo:
            self._cerrar()
            if self._cabe(total):
                self.actual.oraciones += oraciones
                return
        for oracion in oraciones:
            self._agregar_oracion(oracion)

    def _agregar_oracion(self, oracion: _Oracion) -> None:
        if self._cabe(oracion.tokens):
            self.actual.oraciones.append(oracion)
            return
        self._cerrar()
        if not self._cabe(oracion.tokens):
            self.actual = _Fragmento([], 0)  # sin solapamiento: no queda espacio
        self.actual.oraciones.append(oracion)

    def terminar(self) -> list[_Fragmento]:
        self._cerrar()
        return self.listos


def _texto(oraciones: Sequence[_Oracion]) -> str:
    """Oraciones del mismo párrafo separadas por espacio; párrafos, por salto de línea."""
    partes: list[str] = []
    for _, grupo in groupby(oraciones, key=lambda o: o.parrafo):
        partes.append(" ".join(o.texto for o in grupo))
    return "\n".join(partes)


def segmentar(
    secciones: Sequence[SeccionTexto],
    contador: ContadorTokens,
    ventana: VentanaTokens,
    solapamiento: int = 1,
) -> list[FragmentoProcesado]:
    if solapamiento < 0:
        raise ValueError("el solapamiento no puede ser negativo")
    fragmentos: list[FragmentoProcesado] = []
    indice_parrafo = 0
    for clase, tramo in groupby(secciones, key=lambda s: s.clase):
        empaquetador = _Empaquetador(ventana, solapamiento)
        for seccion in tramo:
            for parrafo in seccion.parrafos:
                oraciones: list[_Oracion] = []
                for texto in dividir_oraciones(parrafo.texto):
                    oracion = _Oracion(
                        texto,
                        contador.contar(texto),
                        parrafo.pagina_inicio,
                        parrafo.pagina_fin,
                        indice_parrafo,
                        seccion.titulo,
                    )
                    if oracion.tokens > ventana.maximo:
                        oraciones += _partir_oracion(oracion, ventana.maximo, contador)
                    else:
                        oraciones.append(oracion)
                indice_parrafo += 1
                if oraciones:
                    empaquetador.agregar_parrafo(oraciones)
        for fragmento in empaquetador.terminar():
            texto = _texto(fragmento.oraciones)
            fragmentos.append(
                FragmentoProcesado(
                    orden=len(fragmentos),
                    texto=texto,
                    seccion_normalizada=clase,
                    seccion_original=fragmento.nuevas[0].titulo,
                    pagina_inicio=min(o.pagina_inicio for o in fragmento.oraciones),
                    pagina_fin=max(o.pagina_fin for o in fragmento.oraciones),
                    tokens=max(1, contador.contar(texto)),
                )
            )
    return fragmentos
