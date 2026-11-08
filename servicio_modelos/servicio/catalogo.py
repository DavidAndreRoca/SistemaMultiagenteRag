"""Modelos fijados: repositorio, revisión exacta y archivos con su tamaño y huella (RNF-21).

Cambiar una revisión obliga a reindexar todo el corpus (Fase 1, 18.5): por eso la
revisión viaja en cada respuesta y se guarda con los vectores (T10).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

DIMENSION_EMBEDDINGS = 1024


class TipoModelo(StrEnum):
    EMBEDDINGS = "embeddings"
    REORDENADOR = "reordenador"


@dataclass(frozen=True)
class Archivo:
    ruta: str
    tamano: int
    sha256: str | None = None  # solo los archivos LFS (pesos y tokenizador)


@dataclass(frozen=True)
class ModeloFijado:
    tipo: TipoModelo
    repositorio: str
    revision: str
    licencia: str
    archivos: tuple[Archivo, ...]

    def directorio(self, base: Path) -> Path:
        return base / self.repositorio.replace("/", "--") / self.revision


# Consulta de la API de Hugging Face del 6 de noviembre de 2026. Solo los archivos que
# usa la salida densa: se omiten colbert_linear.pt, sparse_linear.pt, onnx/ e imágenes.
BGE_M3 = ModeloFijado(
    tipo=TipoModelo.EMBEDDINGS,
    repositorio="BAAI/bge-m3",
    revision="5617a9f61b028005a4858fdac845db406aefb181",
    licencia="MIT",
    archivos=(
        Archivo("config.json", 687),
        Archivo("tokenizer_config.json", 444),
        Archivo("special_tokens_map.json", 964),
        Archivo(
            "sentencepiece.bpe.model",
            5069051,
            "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
        ),
        Archivo(
            "tokenizer.json",
            17098108,
            "21106b6d7dab2952c1d496fb21d5dc9db75c28ed361a05f5020bbba27810dd08",
        ),
        Archivo(
            "pytorch_model.bin",
            2271145830,
            "b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38",
        ),
    ),
)

BGE_RERANKER_V2_M3 = ModeloFijado(
    tipo=TipoModelo.REORDENADOR,
    repositorio="BAAI/bge-reranker-v2-m3",
    revision="953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e",
    licencia="Apache-2.0",
    archivos=(
        Archivo("config.json", 795),
        Archivo("tokenizer_config.json", 1173),
        Archivo("special_tokens_map.json", 964),
        Archivo(
            "sentencepiece.bpe.model",
            5069051,
            "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
        ),
        Archivo(
            "tokenizer.json",
            17098273,
            "69564b696052886ed0ac63fa393e928384e0f8caada38c1f4864a9bfbf379c15",
        ),
        Archivo(
            "model.safetensors",
            2271071852,
            "d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286",
        ),
    ),
)

CATALOGO: tuple[ModeloFijado, ...] = (BGE_M3, BGE_RERANKER_V2_M3)


def sha256_de(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def problemas(modelo: ModeloFijado, base: Path, *, con_huella: bool = False) -> list[str]:
    """Archivos que faltan o no coinciden. Sin ``con_huella`` solo compara tamaños (rápido)."""
    encontrados: list[str] = []
    directorio = modelo.directorio(base)
    for archivo in modelo.archivos:
        ruta = directorio / archivo.ruta
        if not ruta.is_file():
            encontrados.append(f"{modelo.repositorio}: falta {archivo.ruta}")
        elif ruta.stat().st_size != archivo.tamano:
            encontrados.append(f"{modelo.repositorio}: tamaño distinto en {archivo.ruta}")
        elif con_huella and archivo.sha256 and sha256_de(ruta) != archivo.sha256:
            encontrados.append(f"{modelo.repositorio}: huella distinta en {archivo.ruta}")
    return encontrados
