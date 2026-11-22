"""Cargador de instrucciones versionadas (T17-01, apartado 6; RNF-21).

Cada instrucción es un archivo ``backend/instrucciones/<agente>/<version>.md``:

    ---
    agente: suficiencia
    version: v1
    descripcion: Juicio de suficiencia de la evidencia recuperada.
    ---
    Texto de la instrucción.

El identificador es ``<agente>/<version>`` y la huella, el SHA-256 del archivo con finales
de línea normalizados. ``registro.json`` fija la huella de cada versión publicada: una
versión no se edita, se crea otra.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.llm.modelos import Instruccion

DIRECTORIO = Path(__file__).resolve().parents[2] / "instrucciones"
REGISTRO = "registro.json"
PATRON_AGENTE = re.compile(r"^[a-z0-9_]{1,40}$")
PATRON_VERSION = re.compile(r"^v[0-9]{1,4}$")
_CABECERA = re.compile(r"\A---\n(?P<campos>.*?)\n---\n(?P<texto>.*)\Z", re.DOTALL)


class InstruccionNoValida(ValueError):
    pass


@dataclass(frozen=True)
class Cabecera:
    agente: str
    version: str
    descripcion: str


def normalizar(contenido: bytes) -> str:
    return contenido.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def huella(texto_normalizado: str) -> str:
    return hashlib.sha256(texto_normalizado.encode("utf-8")).hexdigest()


def leer(ruta: Path) -> tuple[Cabecera, str, str]:
    """Cabecera, texto y huella de un archivo de instrucción."""
    contenido = normalizar(ruta.read_bytes())
    coincidencia = _CABECERA.match(contenido)
    if coincidencia is None:
        raise InstruccionNoValida(f"{ruta.name}: falta la cabecera entre líneas ---")
    campos: dict[str, str] = {}
    for linea in coincidencia["campos"].splitlines():
        clave, separador, valor = linea.partition(":")
        if not separador:
            raise InstruccionNoValida(f"{ruta.name}: línea de cabecera sin dos puntos")
        campos[clave.strip()] = valor.strip()
    faltan = {"agente", "version", "descripcion"} - set(campos)
    if faltan:
        raise InstruccionNoValida(f"{ruta.name}: faltan en la cabecera {sorted(faltan)}")
    texto = coincidencia["texto"].strip()
    if not texto:
        raise InstruccionNoValida(f"{ruta.name}: la instrucción está vacía")
    return (
        Cabecera(campos["agente"], campos["version"], campos["descripcion"]),
        texto,
        huella(contenido),
    )


def cargar(agente: str, version: str, directorio: Path = DIRECTORIO) -> Instruccion:
    if not PATRON_AGENTE.fullmatch(agente) or not PATRON_VERSION.fullmatch(version):
        raise InstruccionNoValida(f"identificador inválido: {agente}/{version}")
    ruta = directorio / agente / f"{version}.md"
    if not ruta.is_file():
        raise InstruccionNoValida(f"no existe la instrucción {agente}/{version}")
    cabecera, texto, firma = leer(ruta)
    if (cabecera.agente, cabecera.version) != (agente, version):
        raise InstruccionNoValida(
            f"{agente}/{version}: la cabecera dice {cabecera.agente}/{cabecera.version}"
        )
    registrada = registro(directorio).get(f"{agente}/{version}")
    if registrada != firma:
        raise InstruccionNoValida(
            f"{agente}/{version}: la huella no coincide con registro.json; una versión"
            " publicada no se edita, se crea una nueva"
        )
    return Instruccion(agente=agente, version=version, huella=firma, texto=texto)


@lru_cache(maxsize=8)
def _registro_en_cache(ruta: Path, modificado: float) -> dict[str, str]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise InstruccionNoValida("registro.json debe ser un objeto")
    return {str(k): str(v) for k, v in datos.items()}


def registro(directorio: Path = DIRECTORIO) -> dict[str, str]:
    ruta = directorio / REGISTRO
    if not ruta.is_file():
        return {}
    return _registro_en_cache(ruta, ruta.stat().st_mtime)


def disponibles(directorio: Path = DIRECTORIO) -> dict[str, str]:
    """Identificador y huella de cada archivo de instrucción presente."""
    resultado: dict[str, str] = {}
    for ruta in sorted(directorio.glob("*/v*.md")):
        cabecera, _, firma = leer(ruta)
        resultado[f"{cabecera.agente}/{cabecera.version}"] = firma
    return resultado


def vigente(agente: str, versiones: dict[str, str], directorio: Path = DIRECTORIO) -> Instruccion:
    """La versión que la configuración vigente elige para el agente."""
    version = versiones.get(agente)
    if version is None:
        raise InstruccionNoValida(f"la configuración no fija versión para {agente}")
    return cargar(agente, version, directorio)
