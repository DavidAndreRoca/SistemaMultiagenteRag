"""T08: el cliente de la API contra el servicio de modelos real (marca ``servicios_compartidos``).

Se ejecuta solo si está definida ``URL_SERVICIO_MODELOS_PRUEBAS`` (por ejemplo,
``http://127.0.0.1:8001`` con ``docker-compose.compartido.yml`` en marcha).
"""

from __future__ import annotations

import math
import os

import pytest

from app.inferencia.servicio_modelos import ClienteServicioModelos

pytestmark = pytest.mark.servicios_compartidos

URL = os.environ.get("URL_SERVICIO_MODELOS_PRUEBAS", "")


@pytest.fixture
async def cliente() -> ClienteServicioModelos:
    if not URL:
        pytest.skip("URL_SERVICIO_MODELOS_PRUEBAS no está definida")
    return ClienteServicioModelos(URL, max_textos=2)


async def test_embeber_y_reordenar_contra_el_servicio_real(
    cliente: ClienteServicioModelos,
) -> None:
    textos = [
        "La prueba de Spearman se usa cuando los datos no son normales.",
        "El clima organizacional mejora con el liderazgo.",
        "Spearman's test is used for non-normal data.",
    ]
    embeddings = await cliente.embeber(textos)  # tres textos en dos partes
    assert embeddings.identidad.modelo == "BAAI/bge-m3"
    assert len(embeddings.vectores) == 3
    for vector in embeddings.vectores:
        assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, abs_tol=1e-5)
    otra_vez = await cliente.embeber(textos[:1])
    assert otra_vez.vectores[0] == embeddings.vectores[0]

    puntajes = await cliente.reordenar("¿Qué prueba uso con datos no normales?", textos)
    assert puntajes.identidad.modelo == "BAAI/bge-reranker-v2-m3"
    assert puntajes.puntajes[1] == min(puntajes.puntajes)
    await cliente.cerrar()
