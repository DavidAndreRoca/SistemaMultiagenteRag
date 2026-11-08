"""Contador de tokens con el tokenizador de bge-m3 (revisión fijada en ``recursos.py``).

La ventana de segmentación (18.4) se mide en los tokens del modelo que embebe los
fragmentos, sin los tokens especiales de inicio y fin.
"""

from __future__ import annotations

from pathlib import Path

from app.corpus.recursos import TOKENIZADOR_BGE_M3, exigir


class ContadorTokensBgeM3:
    def __init__(self, recursos: Path) -> None:
        exigir(recursos)
        from tokenizers import Tokenizer

        ruta = TOKENIZADOR_BGE_M3.directorio(recursos) / "tokenizer.json"
        self._tokenizador = Tokenizer.from_file(str(ruta))
        self._tokenizador.no_truncation()
        self._tokenizador.no_padding()

    def contar(self, texto: str) -> int:
        return len(self._tokenizador.encode(texto, add_special_tokens=False).ids)
