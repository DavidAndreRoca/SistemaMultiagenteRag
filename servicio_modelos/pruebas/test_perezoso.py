"""T10-02: el reordenador se carga al primer uso y una sola vez."""

from __future__ import annotations

import threading
from collections.abc import Sequence

from servicio.ajustes import cargar_ajustes
from servicio.catalogo import BGE_RERANKER_V2_M3
from servicio.motores import ReordenadorPerezoso


class ReordenadorDePrueba:
    modelo = BGE_RERANKER_V2_M3

    def contar_tokens(self, consulta: str, textos: Sequence[str]) -> list[int]:
        return [len(consulta.split()) + len(t.split()) for t in textos]

    def reordenar(self, consulta: str, textos: Sequence[str]) -> list[float]:
        return [0.5 for _ in textos]


def test_no_carga_hasta_el_primer_uso_y_carga_una_sola_vez() -> None:
    cargas: list[int] = []

    def cargar() -> ReordenadorDePrueba:
        cargas.append(1)
        return ReordenadorDePrueba()

    perezoso = ReordenadorPerezoso(cargar, BGE_RERANKER_V2_M3)
    assert perezoso.modelo is BGE_RERANKER_V2_M3
    assert not perezoso.cargado and cargas == []
    hilos = [
        threading.Thread(target=lambda: perezoso.reordenar("consulta", ["texto"])) for _ in range(8)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert perezoso.cargado and cargas == [1]
    assert perezoso.contar_tokens("una consulta", ["dos palabras"]) == [4]


def test_el_reordenador_perezoso_es_el_valor_por_defecto() -> None:
    assert cargar_ajustes({}).reordenador_perezoso is True
    assert cargar_ajustes({"REORDENADOR_PEREZOSO": "false"}).reordenador_perezoso is False
