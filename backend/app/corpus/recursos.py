"""Recursos locales del canal de extracción, con revisión y huella fijadas (T09).

* Modelo de diseño de página de Docling (``docling-layout-heron``): títulos, párrafos,
  encabezados y orden de lectura. El OCR y la estructura de tablas no se usan.
* Tokenizador de bge-m3, en la misma revisión que el servicio de modelos (T08): la
  ventana de segmentación se cuenta en los tokens del modelo que embebe los fragmentos.

Se descargan una vez con ``python -m app.corpus.recursos [carpeta]`` y el canal trabaja
sin red. La carpeta sigue la convención de Docling (``<repositorio con -->/``).
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

VARIABLE_DIRECTORIO = "DIRECTORIO_RECURSOS_CORPUS"


@dataclass(frozen=True)
class ArchivoFijado:
    ruta: str
    tamano: int
    sha256: str


@dataclass(frozen=True)
class RecursoFijado:
    repositorio: str
    revision: str
    licencia: str
    archivos: tuple[ArchivoFijado, ...]

    def directorio(self, base: Path) -> Path:
        return base / self.repositorio.replace("/", "--")

    def url(self, archivo: ArchivoFijado) -> str:
        return f"https://huggingface.co/{self.repositorio}/resolve/{self.revision}/{archivo.ruta}"


# Consulta de la API de Hugging Face del 8 de noviembre de 2026.
DISENO_DE_PAGINA = RecursoFijado(
    repositorio="docling-project/docling-layout-heron",
    revision="8f39ad3c0b4c58e9c2d2c84a38465abf757272d8",
    licencia="Apache-2.0",
    archivos=(
        ArchivoFijado(
            "config.json",
            3268,
            "fdea30805ce2f5666b147fca941dcdd27ad468e27d6ed21902207d3da056a97d",
        ),
        ArchivoFijado(
            "preprocessor_config.json",
            444,
            "cd38cd59999e7a95d68e487fbe5132df3d4e5c32a0836add57e6126ba0c4eaf1",
        ),
        ArchivoFijado(
            "model.safetensors",
            171658996,
            "00333a43451945aaf89db8ca9c0a17e75d1537c17db60fdb91aa95f4c7929e0c",
        ),
    ),
)

# Misma revisión y huella que servicio_modelos/servicio/catalogo.py (BGE_M3).
TOKENIZADOR_BGE_M3 = RecursoFijado(
    repositorio="BAAI/bge-m3",
    revision="5617a9f61b028005a4858fdac845db406aefb181",
    licencia="MIT",
    archivos=(
        ArchivoFijado(
            "tokenizer.json",
            17098108,
            "21106b6d7dab2952c1d496fb21d5dc9db75c28ed361a05f5020bbba27810dd08",
        ),
    ),
)

RECURSOS = (DISENO_DE_PAGINA, TOKENIZADOR_BGE_M3)


class ErrorRecursos(RuntimeError):
    """Faltan recursos del canal o no coinciden con la huella fijada."""


def _sha256(ruta: Path) -> str:
    calculo = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for parte in iter(lambda: archivo.read(1 << 20), b""):
            calculo.update(parte)
    return calculo.hexdigest()


def problemas(base: Path) -> list[str]:
    """Lista lo que falta o no coincide; vacía si todo está en orden."""
    encontrados: list[str] = []
    for recurso in RECURSOS:
        for archivo in recurso.archivos:
            ruta = recurso.directorio(base) / archivo.ruta
            if not ruta.is_file():
                encontrados.append(f"falta {recurso.repositorio}/{archivo.ruta}")
            elif ruta.stat().st_size != archivo.tamano or _sha256(ruta) != archivo.sha256:
                encontrados.append(f"huella distinta en {recurso.repositorio}/{archivo.ruta}")
    return encontrados


def exigir(base: Path) -> None:
    faltan = problemas(base)
    if faltan:
        raise ErrorRecursos(
            "Recursos del canal incompletos en "
            f"{base}: {'; '.join(faltan)}. Descárguelos con: python -m app.corpus.recursos"
        )


def descargar(base: Path, *, cliente: httpx.Client | None = None) -> list[str]:
    """Descarga lo que falte y verifica tamaño y huella. Devuelve lo descargado."""
    http = cliente or httpx.Client(follow_redirects=True, timeout=httpx.Timeout(600, connect=10))
    descargados: list[str] = []
    try:
        for recurso in RECURSOS:
            destino = recurso.directorio(base)
            destino.mkdir(parents=True, exist_ok=True)
            for archivo in recurso.archivos:
                ruta = destino / archivo.ruta
                if ruta.is_file() and _sha256(ruta) == archivo.sha256:
                    continue
                temporal = ruta.with_suffix(ruta.suffix + ".parcial")
                respuesta = http.send(http.build_request("GET", recurso.url(archivo)), stream=True)
                try:
                    respuesta.raise_for_status()
                    with temporal.open("wb") as salida:
                        for parte in respuesta.iter_bytes(1 << 20):
                            salida.write(parte)
                finally:
                    respuesta.close()
                if temporal.stat().st_size != archivo.tamano or _sha256(temporal) != archivo.sha256:
                    temporal.unlink()
                    raise ErrorRecursos(f"huella distinta al descargar {recurso.url(archivo)}")
                temporal.replace(ruta)
                descargados.append(f"{recurso.repositorio}/{archivo.ruta}")
    finally:
        if cliente is None:
            http.close()
    return descargados


def directorio_por_defecto() -> Path | None:
    valor = os.environ.get(VARIABLE_DIRECTORIO, "").strip()
    return Path(valor) if valor else None


def main(argumentos: list[str]) -> int:
    base = Path(argumentos[0]) if argumentos else directorio_por_defecto()
    if base is None:
        print(f"Indique la carpeta o defina {VARIABLE_DIRECTORIO}.", file=sys.stderr)
        return 2
    for nombre in descargar(base):
        print(f"descargado: {nombre}")
    exigir(base)
    print(f"Recursos del canal verificados en {base}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
