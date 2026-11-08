"""Motores de prueba que cumplen las interfaces sin cargar pesos (integración continua)."""

from __future__ import annotations

import hashlib
import math
import threading
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from servicio.ajustes import AjustesServicio
from servicio.aplicacion import crear_aplicacion
from servicio.catalogo import BGE_M3, BGE_RERANKER_V2_M3, DIMENSION_EMBEDDINGS, ModeloFijado


def _tokens(texto: str) -> int:
    return len(texto.split()) + 2  # aproximación: una palabra, un token, más [CLS] y [SEP]


class EmbeddingsDePrueba:
    def __init__(self) -> None:
        self.bloqueo: threading.Event | None = None
        self.en_curso = threading.Event()
        self.llamadas: list[int] = []

    @property
    def modelo(self) -> ModeloFijado:
        return BGE_M3

    def contar_tokens(self, textos: Sequence[str]) -> list[int]:
        return [_tokens(t) for t in textos]

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        self.en_curso.set()
        if self.bloqueo is not None:
            self.bloqueo.wait(timeout=5)
        self.llamadas.append(len(textos))
        vectores = []
        for texto in textos:
            semilla = hashlib.sha256(texto.encode()).digest()
            crudo = [semilla[i % 32] - 127.5 for i in range(DIMENSION_EMBEDDINGS)]
            norma = math.sqrt(sum(x * x for x in crudo))
            vectores.append([x / norma for x in crudo])
        return vectores


class ReordenadorDePrueba:
    @property
    def modelo(self) -> ModeloFijado:
        return BGE_RERANKER_V2_M3

    def contar_tokens(self, consulta: str, textos: Sequence[str]) -> list[int]:
        return [_tokens(consulta) + _tokens(t) for t in textos]

    def reordenar(self, consulta: str, textos: Sequence[str]) -> list[float]:
        palabras = set(consulta.lower().split())
        return [len(palabras & set(t.lower().split())) / max(len(palabras), 1) for t in textos]


@pytest.fixture
def motores() -> tuple[EmbeddingsDePrueba, ReordenadorDePrueba]:
    return EmbeddingsDePrueba(), ReordenadorDePrueba()


@pytest.fixture
def ajustes(tmp_path: Path) -> AjustesServicio:
    return AjustesServicio(
        directorio_modelos=tmp_path,
        max_textos=8,
        max_tokens=40,
        espera_maxima_s=0.3,
        max_concurrencia=1,
    )


@pytest.fixture
def cliente(
    ajustes: AjustesServicio, motores: tuple[EmbeddingsDePrueba, ReordenadorDePrueba]
) -> Iterator[TestClient]:
    with TestClient(crear_aplicacion(ajustes, motores)) as cliente:
        yield cliente
