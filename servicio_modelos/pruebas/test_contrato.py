"""Contrato de /embeber, /reordenar y /salud con motores de prueba."""

from __future__ import annotations

import math
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pruebas.conftest import EmbeddingsDePrueba, ReordenadorDePrueba
from servicio.ajustes import AjustesServicio, ErrorAjustes, cargar_ajustes
from servicio.aplicacion import crear_aplicacion
from servicio.catalogo import BGE_M3, BGE_RERANKER_V2_M3, DIMENSION_EMBEDDINGS
from servicio.memoria import memoria_actual


def test_embeber_devuelve_vectores_normalizados_con_modelo_y_revision(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post("/embeber", json={"textos": ["uno dos", "tres"]})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["modelo"] == "BAAI/bge-m3"
    assert cuerpo["revision"] == BGE_M3.revision
    assert cuerpo["dimension"] == DIMENSION_EMBEDDINGS
    assert len(cuerpo["vectores"]) == 2
    for vector in cuerpo["vectores"]:
        assert len(vector) == DIMENSION_EMBEDDINGS
        assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, rel_tol=1e-6)


def test_reordenar_devuelve_un_puntaje_por_texto_en_orden(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/reordenar",
        json={"consulta": "prueba t", "textos": ["nada que ver", "una prueba t", "prueba"]},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert (cuerpo["modelo"], cuerpo["revision"]) == (
        "BAAI/bge-reranker-v2-m3",
        BGE_RERANKER_V2_M3.revision,
    )
    assert cuerpo["puntajes"] == [0.0, 1.0, 0.5]


@pytest.mark.parametrize(
    ("ruta", "cuerpo", "codigo"),
    [
        ("/embeber", {"textos": []}, "entrada_invalida"),
        ("/embeber", {"textos": ["a"] * 9}, "demasiados_textos"),
        ("/embeber", {"textos": ["bien", "   "]}, "texto_vacio"),
        ("/embeber", {"textos": ["palabra " * 50]}, "texto_demasiado_largo"),
        ("/embeber", {"textos": ["x" * 641]}, "texto_demasiado_largo"),  # corte por caracteres
        ("/embeber", {"textos": ["a"], "extra": 1}, "entrada_invalida"),
        ("/reordenar", {"consulta": " ", "textos": ["a"]}, "consulta_vacia"),
        ("/reordenar", {"consulta": "q " * 20, "textos": ["t " * 20]}, "texto_demasiado_largo"),
        ("/reordenar", {"textos": ["a"]}, "entrada_invalida"),
    ],
)
def test_entradas_invalidas_se_rechazan_con_formato_de_error(
    cliente: TestClient, ruta: str, cuerpo: dict[str, object], codigo: str
) -> None:
    respuesta = cliente.post(ruta, json=cuerpo)
    assert respuesta.status_code == 422
    error = respuesta.json()
    assert error["codigo"] == codigo
    assert error["mensaje"]
    assert len(error["incidencia_id"]) == 32


def test_el_error_no_devuelve_el_texto_recibido(cliente: TestClient) -> None:
    secreto = "texto-del-estudiante-que-no-debe-volver"
    respuesta = cliente.post("/embeber", json={"textos": secreto})  # tipo inválido
    assert respuesta.status_code == 422
    assert secreto not in respuesta.text


def test_salud_informa_modelos_limites_y_memoria(cliente: TestClient) -> None:
    cuerpo = cliente.get("/salud").json()
    assert cuerpo["estado"] == "ok"
    assert [(m["tipo"], m["modelo"], m["revision"]) for m in cuerpo["modelos"]] == [
        ("embeddings", "BAAI/bge-m3", BGE_M3.revision),
        ("reordenador", "BAAI/bge-reranker-v2-m3", BGE_RERANKER_V2_M3.revision),
    ]
    assert (cuerpo["max_textos"], cuerpo["max_tokens"], cuerpo["max_concurrencia"]) == (8, 40, 1)
    assert set(cuerpo["memoria"]) == {"residente_mb", "pico_mb"}


def test_limite_de_concurrencia_responde_ocupado(
    ajustes: AjustesServicio, motores: tuple[EmbeddingsDePrueba, ReordenadorDePrueba]
) -> None:
    """Con MAX_CONCURRENCIA=1, una segunda inferencia espera y, pasado el plazo, recibe 503."""
    embeddings, _ = motores
    embeddings.bloqueo = threading.Event()
    with TestClient(crear_aplicacion(ajustes, motores)) as cliente:
        primera: dict[str, int] = {}
        hilo = threading.Thread(
            target=lambda: primera.update(
                estado=cliente.post("/embeber", json={"textos": ["a"]}).status_code
            )
        )
        hilo.start()
        try:
            assert embeddings.en_curso.wait(timeout=5)  # la primera ya tiene el turno
            segunda = cliente.post("/embeber", json={"textos": ["b"]})
        finally:
            embeddings.bloqueo.set()
            hilo.join()
    assert segunda.status_code == 503
    assert segunda.json()["codigo"] == "servicio_ocupado"
    assert primera["estado"] == 200


def test_sin_pesos_el_servicio_no_arranca_y_dice_como_descargarlos(tmp_path: Path) -> None:
    aplicacion = crear_aplicacion(AjustesServicio(directorio_modelos=tmp_path))
    with (
        pytest.raises(RuntimeError, match=r"python -m servicio\.descargar"),
        TestClient(aplicacion),
    ):
        pass


def test_ajustes_desde_el_entorno() -> None:
    ajustes = cargar_ajustes({"TAMANO_LOTE": "4", "MAX_CONCURRENCIA": "2", "MAX_TOKENS": "512"})
    assert (ajustes.tamano_lote, ajustes.max_concurrencia, ajustes.max_tokens) == (4, 2, 512)
    assert ajustes.max_caracteres == 512 * 16
    with pytest.raises(ErrorAjustes, match="TAMANO_LOTE"):
        cargar_ajustes({"TAMANO_LOTE": "0"})


def test_memoria_lee_proc_status(tmp_path: Path) -> None:
    estado = tmp_path / "status"
    estado.write_text("Name:\tpython\nVmHWM:\t  204800 kB\nVmRSS:\t  102400 kB\n", "ascii")
    memoria = memoria_actual(estado)
    assert (memoria.residente_mb, memoria.pico_mb) == (100.0, 200.0)
    assert memoria_actual(tmp_path / "no-existe").residente_mb is None
