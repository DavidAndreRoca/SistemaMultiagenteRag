"""Motores reales con transformers y PyTorch en CPU (decisión T08-01).

* bge-m3, salida densa: vector del token [CLS] de la última capa, normalizado (ficha del
  modelo y ``1_Pooling/config.json`` de su repositorio).
* bge-reranker-v2-m3: logit del clasificador para el par (consulta, texto), pasado por
  una sigmoide para quedar entre 0 y 1 (sobre esa escala se define tau, insumos de T04).

Los pesos se cargan solo desde ``DIRECTORIO_MODELOS`` (sin red): la revisión es siempre
la fijada en ``catalogo.py``.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

import torch
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer
from transformers.utils import logging as registro_transformers

from servicio.ajustes import AjustesServicio
from servicio.catalogo import (
    BGE_M3,
    BGE_RERANKER_V2_M3,
    DIMENSION_EMBEDDINGS,
    ModeloFijado,
)
from servicio.lotes import lotes_sin_relleno
from servicio.motores import MotorReordenador, ReordenadorPerezoso


def configurar_torch(hilos: int) -> None:
    torch.use_deterministic_algorithms(True)
    # 0: todos los procesadores del contenedor. PyTorch, por su cuenta, toma solo los
    # núcleos físicos (3 de 6 en el portátil de desarrollo); con 6 se embebe un 31 % más
    # rápido y los vectores son idénticos bit a bit (decisión T10-02).
    torch.set_num_threads(hilos or os.cpu_count() or 1)
    torch.set_grad_enabled(False)
    registro_transformers.disable_progress_bar()  # el registro queda en JSON


class _Base:
    _modelo_fijado: ModeloFijado

    def __init__(self, ajustes: AjustesServicio) -> None:
        self._lote = ajustes.tamano_lote
        self._directorio = str(self._modelo_fijado.directorio(ajustes.directorio_modelos))
        self._tokenizador: Any = AutoTokenizer.from_pretrained(
            self._directorio, local_files_only=True
        )

    @property
    def modelo(self) -> ModeloFijado:
        return self._modelo_fijado

    def _lotes(self, longitudes: Sequence[int]) -> list[list[int]]:
        # Sin relleno: cada texto da el mismo resultado sin importar su lote (lotes.py).
        return lotes_sin_relleno(longitudes, self._lote)


class EmbeddingsBgeM3(_Base):
    _modelo_fijado = BGE_M3

    def __init__(self, ajustes: AjustesServicio) -> None:
        super().__init__(ajustes)
        self._red: Any = AutoModel.from_pretrained(self._directorio, local_files_only=True)
        self._red.eval()

    def contar_tokens(self, textos: Sequence[str]) -> list[int]:
        codificados = self._tokenizador(list(textos), add_special_tokens=True, truncation=False)
        return [len(ids) for ids in codificados["input_ids"]]

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        resultado: list[list[float]] = [[] for _ in textos]
        with torch.inference_mode():
            for lote in self._lotes(self.contar_tokens(textos)):
                entrada = self._tokenizador(
                    [textos[i] for i in lote], padding=False, truncation=False, return_tensors="pt"
                )
                cls = self._red(**entrada).last_hidden_state[:, 0]
                vectores = torch.nn.functional.normalize(cls, p=2, dim=1)
                for posicion, indice in enumerate(lote):
                    resultado[indice] = vectores[posicion].tolist()
        assert all(len(v) == DIMENSION_EMBEDDINGS for v in resultado)
        return resultado


class ReordenadorBgeV2M3(_Base):
    _modelo_fijado = BGE_RERANKER_V2_M3

    def __init__(self, ajustes: AjustesServicio) -> None:
        super().__init__(ajustes)
        self._red: Any = AutoModelForSequenceClassification.from_pretrained(
            self._directorio, local_files_only=True
        )
        self._red.eval()

    def contar_tokens(self, consulta: str, textos: Sequence[str]) -> list[int]:
        codificados = self._tokenizador(
            [consulta] * len(textos), list(textos), add_special_tokens=True, truncation=False
        )
        return [len(ids) for ids in codificados["input_ids"]]

    def reordenar(self, consulta: str, textos: Sequence[str]) -> list[float]:
        resultado = [0.0] * len(textos)
        with torch.inference_mode():
            for lote in self._lotes(self.contar_tokens(consulta, textos)):
                entrada = self._tokenizador(
                    [consulta] * len(lote),
                    [textos[i] for i in lote],
                    padding=False,
                    truncation=False,
                    return_tensors="pt",
                )
                logits = self._red(**entrada).logits.view(-1).float()
                puntajes = torch.sigmoid(logits).tolist()
                for posicion, indice in enumerate(lote):
                    resultado[indice] = float(puntajes[posicion])
        return resultado


def cargar_motores(ajustes: AjustesServicio) -> tuple[EmbeddingsBgeM3, MotorReordenador]:
    configurar_torch(ajustes.hilos)
    reordenador: MotorReordenador = (
        ReordenadorPerezoso(lambda: ReordenadorBgeV2M3(ajustes), BGE_RERANKER_V2_M3)
        if ajustes.reordenador_perezoso
        else ReordenadorBgeV2M3(ajustes)
    )
    return EmbeddingsBgeM3(ajustes), reordenador
