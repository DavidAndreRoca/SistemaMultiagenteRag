"""Citas en el texto por norma y su cruce con la lista de referencias (T20, actividades 2 y 5).

Sin acceso a la base ni a la red: trabaja sobre los párrafos guardados de la versión (T11).

* **Numéricas** (``ieee`` y ``vancouver``): ``[1]``, ``[1], [3]``, ``[1]-[3]``, ``[2-4]``
  (con guion o raya corta) y ``[1, 3]``. En Vancouver también ``(1)``, ``(2,3)`` y
  ``(1-3)``, con a lo sumo tres cifras para no confundir años. Los superíndices no se
  detectan: los párrafos guardados no conservan el formato (decisión T20-01).
* **Autor y año** (``apa7``): entre paréntesis, ``(García, 2020)``, ``(García & López,
  2021)``, ``(García y López, 2021)``, ``(Kasneci et al., 2023)``, varias obras con ``;``,
  varios años del mismo autor, letras ``2020a`` y ``s. f.``; y narrativas, ``García
  (2020)``, ``Kasneci et al. (2023)`` y ``García y López (2021)``.

El cruce asigna cada cita a las entradas de la lista: por número en las numéricas y por
primer apellido y año en APA. Lo que no encuentra entrada se informa como "cita sin
entrada" y lo que ninguna cita alcanza, como "entrada no citada".
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict

from app.bibliografia.normalizacion import normalizar
from app.borradores.extraccion import ParrafoBorrador

NUMERICAS = frozenset({"ieee", "vancouver"})
AUTOR_ANIO = frozenset({"apa7"})
MAX_RANGO = 50  # un rango más largo es casi seguro un error de escritura: no se expande
SIN_FECHA = "s. f."

_GUION = "[\u2013\u2014-]"  # guion, raya corta o raya
_NUM = r"\d{1,4}"
_LISTA = rf"{_NUM}(?:\s*{_GUION}\s*{_NUM})?(?:\s*,\s*{_NUM}(?:\s*{_GUION}\s*{_NUM})?)*"
_CORCHETES_RANGO = rf"\[\s*(?P<desde>{_NUM})\s*\]\s*{_GUION}\s*\[\s*(?P<hasta>{_NUM})\s*\]"
_CORCHETES = rf"\[\s*(?P<corchetes>{_LISTA})\s*\]"
_NUM_PAR = r"\d{1,3}"
_LISTA_PAR = (
    rf"{_NUM_PAR}(?:\s*{_GUION}\s*{_NUM_PAR})?(?:\s*,\s*{_NUM_PAR}(?:\s*{_GUION}\s*{_NUM_PAR})?)*"
)
_PARENTESIS_NUM = rf"\(\s*(?P<parentesis>{_LISTA_PAR})\s*\)"
_IEEE = re.compile(rf"{_CORCHETES_RANGO}|{_CORCHETES}")
_VANCOUVER = re.compile(rf"{_CORCHETES_RANGO}|{_CORCHETES}|{_PARENTESIS_NUM}")

_ANIO = r"\d{4}[a-z]?|s\.\s?f\.|n\.\s?d\."
_ANIO_SUELTO = re.compile(rf"(?<![\d\w])({_ANIO})(?![\d])")
_PARENTETICA = re.compile(r"\(([^()]{2,400})\)")
_LETRA = r"[A-ZÁÉÍÓÚÑÜ][\wáéíóúñüÁÉÍÓÚÑÜ'" + "\u2019" + r"\-]+"
_PARTICULA = r"(?:de la|de|del|van der|van|von|da|di|le|la)"
_NOMBRE = rf"{_LETRA}(?:\s+(?:{_PARTICULA}\s+)?{_LETRA})*"
_NARRATIVA = re.compile(
    rf"(?P<autor>{_NOMBRE})(?P<resto>\s+et\s+al\.|\s+(?:y|e|&|and)\s+{_NOMBRE})?"
    rf"\s+\(\s*(?P<anios>(?:{_ANIO})(?:\s*,\s*(?:\d{{4}}[a-z]?))*)"
    r"(?:\s*,\s*pp?\.\s*[\d" + "\u2013" + r"\-]+)?\s*\)"
)
# Palabras que pueden quedar delante del apellido en una cita narrativa ("Según García").
_ENLACES = frozenset(
    (  # noqa: SIM905 (lista larga de palabras)
        "según como en la el los las lo para por de del desde durante entre con sin también"
        " además así sobre tras ante hacia hasta mientras aunque cuando donde pero porque"
        " pues que quien este esta estos estas ese esa aquel aquella luego finalmente"
        " asimismo igualmente incluso solo sólo una uno unos unas al"
    ).split()
)
_PREFIJOS = re.compile(r"^(?:véase|vease|ver|cf\.|p\.\s?ej\.,?|e\.\s?g\.,?)\s+", re.IGNORECASE)
_SEPARADOR_AUTORES = re.compile(r",|&|\s+y\s+|\s+e\s+|\s+and\s+")


class _Inmutable(BaseModel):
    model_config = ConfigDict(frozen=True)


class ObraCitada(_Inmutable):
    apellido: str  # primer apellido, normalizado (sin tildes ni mayúsculas)
    anio: str | None  # "2020", "2020a" o "s. f."
    texto: str  # como se informa si no tiene entrada: "(Pérez, 2021)"


class CitaEnTexto(_Inmutable):
    texto: str  # tal como aparece en el borrador
    parrafo: str  # id del párrafo (p1, p2...)
    numeros: list[int] = []  # normas numéricas
    obras: list[ObraCitada] = []  # autor y año


class EntradaLista(_Inmutable):
    indice: int  # 1, 2... en el orden de la lista
    texto: str
    apellido: str | None = None  # normalizado
    anio: str | None = None


class CitaCruzada(_Inmutable):
    texto: str
    parrafo: str
    destinos: list[int]  # entradas a las que apunta
    sin_entrada: list[str]


class Cruce(_Inmutable):
    citas: list[CitaCruzada]
    citas_sin_entrada: list[str]
    entradas_no_citadas: list[int]


def _exigir_norma(norma: str) -> None:
    if norma not in NUMERICAS | AUTOR_ANIO:
        raise ValueError(f"norma de citación no admitida: {norma}")


# --------------------------------------------------------------------------- numéricas


def _expandir(lista: str) -> list[int]:
    numeros: list[int] = []
    for parte in lista.split(","):
        extremos = [int(n) for n in re.split(_GUION, parte) if n.strip()]
        if len(extremos) == 2 and extremos[0] <= extremos[1] <= extremos[0] + MAX_RANGO:
            numeros.extend(range(extremos[0], extremos[1] + 1))
        else:
            numeros.extend(extremos)
    return numeros


def _numericas(parrafo: ParrafoBorrador, patron: re.Pattern[str]) -> Iterable[CitaEnTexto]:
    for coincidencia in patron.finditer(parrafo.texto):
        grupos = coincidencia.groupdict()
        if grupos.get("desde"):
            numeros = _expandir(f"{grupos['desde']}-{grupos['hasta']}")
        else:
            numeros = _expandir(grupos.get("corchetes") or grupos.get("parentesis") or "")
        numeros = [n for n in numeros if n > 0]
        if numeros:
            yield CitaEnTexto(texto=coincidencia.group(0), parrafo=parrafo.id, numeros=numeros)


# ------------------------------------------------------------------------- autor y año


def anio_normalizado(valor: str) -> str:
    valor = valor.strip().lower()
    return SIN_FECHA if valor.startswith(("s", "n")) else valor


def _primer_autor(autores: str) -> str | None:
    autores = _PREFIJOS.sub("", autores.strip(" ,;")).replace("et al.", "").strip(" ,")
    if not autores or any(c.isdigit() for c in autores):
        return None
    primero = _SEPARADOR_AUTORES.split(autores)[0].strip()
    return primero or None


def _parenteticas(texto: str) -> Iterable[tuple[int, str, list[ObraCitada]]]:
    for coincidencia in _PARENTETICA.finditer(texto):
        obras: list[ObraCitada] = []
        for parte in coincidencia.group(1).split(";"):
            anios = list(_ANIO_SUELTO.finditer(parte))
            if not anios:
                continue
            autor = _primer_autor(parte[: anios[0].start()])
            if autor is None:
                continue
            # Los años de esta obra: los que siguen al autor, antes de la página.
            fin = re.search(r",\s*pp?\.", parte)
            for anio in anios:
                if fin and anio.start() > fin.start():
                    break
                obras.append(
                    ObraCitada(
                        apellido=normalizar(autor),
                        anio=anio_normalizado(anio.group(1)),
                        texto=f"({autor}, {anio.group(1).strip()})",
                    )
                )
        if obras:
            yield coincidencia.start(), coincidencia.group(0), obras


def _sin_enlaces(nombre: str) -> str | None:
    palabras = nombre.split()
    while palabras and palabras[0].lower() in _ENLACES:
        palabras = palabras[1:]
    return " ".join(palabras) or None


def _narrativas(texto: str) -> Iterable[tuple[int, str, list[ObraCitada]]]:
    for coincidencia in _NARRATIVA.finditer(texto):
        autor = _sin_enlaces(coincidencia.group("autor"))
        if autor is None:
            continue
        anios = [a.strip() for a in coincidencia.group("anios").split(",")]
        inicio = coincidencia.start("autor") + coincidencia.group("autor").index(autor)
        yield (
            inicio,
            texto[inicio : coincidencia.end()],
            [
                ObraCitada(
                    apellido=normalizar(autor), anio=anio_normalizado(a), texto=f"{autor} ({a})"
                )
                for a in anios
            ],
        )


def _autor_anio(parrafo: ParrafoBorrador) -> Iterable[CitaEnTexto]:
    halladas = sorted(
        [*_parenteticas(parrafo.texto), *_narrativas(parrafo.texto)], key=lambda h: h[0]
    )
    for _, texto, obras in halladas:
        yield CitaEnTexto(texto=texto, parrafo=parrafo.id, obras=obras)


def extraer_citas(parrafos: Sequence[ParrafoBorrador], norma: str) -> list[CitaEnTexto]:
    """Las citas de los párrafos dados, en orden de aparición."""
    _exigir_norma(norma)
    citas: list[CitaEnTexto] = []
    for parrafo in parrafos:
        if norma == "ieee":
            citas.extend(_numericas(parrafo, _IEEE))
        elif norma == "vancouver":
            citas.extend(_numericas(parrafo, _VANCOUVER))
        else:
            citas.extend(_autor_anio(parrafo))
    return citas


# ---------------------------------------------------------------------------- entradas

_ANIO_ENTRADA = re.compile(rf"\(\s*({_ANIO})\s*[,).]")
_NUMERO_LISTA = re.compile(r"^\s*(?:\[\d+\]|\d+[.)])\s*")
# "Apellido(s), I." al inicio de la entrada: la forma de APA 7.
_APELLIDO_APA = re.compile(r"^\s*([^,()\[\]]+?),\s*[A-ZÁÉÍÓÚÑ]\.")


def entrada_desde_texto(
    indice: int, texto: str, *, apellido: str | None = None, anio: int | None = None
) -> EntradaLista:
    """Primer apellido y año de una entrada de la lista.

    Si la entrada empieza como en APA (``Alarcón Llontop, L. R.``), el apellido sale del
    texto: GROBID parte los apellidos compuestos y daría solo ``Llontop``. Si no, el de
    GROBID. El año del texto tiene prioridad si coincide, porque conserva la letra
    (``2020b``)."""
    limpio = _NUMERO_LISTA.sub("", texto)
    propio = None
    if forma_apa := _APELLIDO_APA.match(limpio):
        propio = normalizar(forma_apa.group(1)) or None
    elif apellido:
        propio = normalizar(apellido)
    else:
        cabeza = (
            limpio.split(",", 1)[0] if "," in limpio.split("(", 1)[0] else limpio.split("(", 1)[0]
        )
        propio = normalizar(cabeza.strip(" .")) or None
    del_texto = _ANIO_ENTRADA.search(limpio)
    anio_texto = anio_normalizado(del_texto.group(1)) if del_texto else None
    if anio_texto and (anio is None or anio_texto[:4] == str(anio)):
        anio_final: str | None = anio_texto
    else:
        anio_final = str(anio) if anio is not None else anio_texto
    return EntradaLista(indice=indice, texto=texto, apellido=propio, anio=anio_final)


# ------------------------------------------------------------------------------ cruce


def _mismo_autor(citado: str, entrada: str | None) -> bool:
    if not entrada:
        return False
    return citado == entrada or citado.split()[0] == entrada.split()[0]


def _mismo_anio(citado: str | None, entrada: str | None) -> bool:
    if citado is None or entrada is None:
        return False
    if citado == entrada:
        return True
    # "(García, 2020)" alcanza a "2020a" y "2020b" si la lista usa letras y la cita no.
    return citado[:4] == entrada[:4] and len(citado) == 4 and citado.isdigit()


def _sin_repetir(valores: Iterable[str]) -> list[str]:
    vistos: list[str] = []
    for valor in valores:
        if valor not in vistos:
            vistos.append(valor)
    return vistos


def cruzar(citas: Sequence[CitaEnTexto], entradas: Sequence[EntradaLista], norma: str) -> Cruce:
    _exigir_norma(norma)
    indices = {e.indice for e in entradas}
    cruzadas: list[CitaCruzada] = []
    for cita in citas:
        destinos: list[int] = []
        faltan: list[str] = []
        if norma in NUMERICAS:
            abre, cierra = ("(", ")") if cita.texto.startswith("(") else ("[", "]")
            for numero in cita.numeros:
                if numero in indices:
                    destinos.append(numero)
                else:
                    faltan.append(f"{abre}{numero}{cierra}")
        else:
            for obra in cita.obras:
                alcanzadas = [
                    e.indice
                    for e in entradas
                    if _mismo_autor(obra.apellido, e.apellido) and _mismo_anio(obra.anio, e.anio)
                ]
                if alcanzadas:
                    destinos.extend(i for i in alcanzadas if i not in destinos)
                else:
                    faltan.append(obra.texto)
        cruzadas.append(
            CitaCruzada(
                texto=cita.texto, parrafo=cita.parrafo, destinos=destinos, sin_entrada=faltan
            )
        )
    citadas = {d for c in cruzadas for d in c.destinos}
    return Cruce(
        citas=cruzadas,
        citas_sin_entrada=_sin_repetir(f for c in cruzadas for f in c.sin_entrada),
        entradas_no_citadas=sorted(indices - citadas),
    )
