"""Pruebas con los pesos reales (marca ``modelos_locales``; solo bajo demanda).

Uso: ``docker compose -f docker-compose.compartido.yml --profile pruebas run --rm --build
pruebas_modelos``. Imprimen la memoria y el tiempo con un lote de prueba (T08).
Los textos son ficticios, redactados para la prueba.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from servicio.ajustes import cargar_ajustes
from servicio.aplicacion import crear_aplicacion
from servicio.catalogo import CATALOGO, DIMENSION_EMBEDDINGS, problemas

pytestmark = pytest.mark.modelos_locales

TEMAS = (
    "la ansiedad ante los exámenes en estudiantes universitarios",
    "el uso de redes sociales y el rendimiento académico",
    "la gestión de residuos sólidos en municipios costeros",
    "la satisfacción laboral del personal de salud",
    "la comprensión lectora en educación secundaria",
    "la calidad del agua de pozos en zonas rurales",
    "la adopción de banca móvil en pequeños comercios",
    "la actividad física y el estrés percibido",
)


def parrafo_ficticio(indice: int, oraciones: int = 9) -> str:
    """Párrafo de unos 300 a 400 tokens, distinto para cada índice."""
    tema = TEMAS[indice % len(TEMAS)]
    partes = [
        f"El estudio {indice} analiza {tema} con un diseño correlacional de corte transversal.",
        f"La muestra estuvo conformada por {120 + indice} participantes seleccionados por "
        "muestreo no probabilístico intencional en dos sedes de la región.",
        "Se aplicó un cuestionario validado por juicio de expertos, con una confiabilidad "
        f"alfa de Cronbach de 0.{80 + indice % 15}.",
        "Los datos se analizaron con la prueba de correlación de Spearman, porque las "
        "variables no siguieron una distribución normal según Kolmogorov-Smirnov.",
        f"Los resultados muestran una relación positiva moderada (rho = 0.{40 + indice % 30}) "
        "entre las variables de interés, con significancia estadística.",
        "Estos hallazgos coinciden con antecedentes nacionales e internacionales que reportan "
        "asociaciones de magnitud similar en poblaciones comparables.",
        "Entre las limitaciones se encuentra el tamaño de la muestra y el carácter "
        "autoinformado de los instrumentos, que puede introducir sesgo de deseabilidad social.",
        "Se recomienda replicar el estudio con un diseño longitudinal y muestreo probabilístico "
        "para fortalecer la validez externa de las conclusiones.",
        "Las implicancias prácticas apuntan a programas de intervención que consideren el "
        "contexto institucional y las características de los participantes.",
    ]
    return " ".join(partes[:oraciones])


@pytest.fixture(scope="module")
def cliente_real() -> Iterator[TestClient]:
    ajustes = cargar_ajustes()
    faltan = [p for modelo in CATALOGO for p in problemas(modelo, ajustes.directorio_modelos)]
    if faltan:
        pytest.skip(f"sin pesos en {ajustes.directorio_modelos}: {faltan[0]}")
    inicio = time.perf_counter()
    with TestClient(crear_aplicacion(ajustes)) as cliente:
        _informar("carga", {"segundos": round(time.perf_counter() - inicio, 1)})
        yield cliente


def _informar(etapa: str, datos: dict[str, object]) -> None:
    print(f"\nMEDICION {etapa} " + json.dumps(datos, ensure_ascii=False))


def _embeber(cliente: TestClient, textos: list[str]) -> list[list[float]]:
    respuesta = cliente.post("/embeber", json={"textos": textos})
    assert respuesta.status_code == 200, respuesta.text
    vectores: list[list[float]] = respuesta.json()["vectores"]
    return vectores


def _coseno(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_embeber_real_normalizado_y_con_sentido(cliente_real: TestClient) -> None:
    textos = [
        "La ansiedad ante los exámenes afecta el rendimiento de los estudiantes.",
        "Test anxiety affects student performance.",
        "La calidad del agua de los pozos rurales presenta coliformes.",
    ]
    vectores = _embeber(cliente_real, textos)
    for vector in vectores:
        assert len(vector) == DIMENSION_EMBEDDINGS
        assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, abs_tol=1e-5)
    # Multilingüe: la traducción se parece más que un tema distinto en el mismo idioma.
    assert _coseno(vectores[0], vectores[1]) > _coseno(vectores[0], vectores[2]) + 0.1


def test_el_mismo_texto_produce_siempre_el_mismo_vector(cliente_real: TestClient) -> None:
    """Criterio de T08: igualdad exacta entre solicitudes y sin importar el resto del lote."""
    texto = parrafo_ficticio(3)
    solo_1 = _embeber(cliente_real, [texto])[0]
    solo_2 = _embeber(cliente_real, [texto])[0]
    assert solo_1 == solo_2  # bit a bit
    acompanado = _embeber(
        cliente_real, [parrafo_ficticio(1, 2), texto, parrafo_ficticio(5), "Texto breve."]
    )[1]
    diferencia = max(abs(x - y) for x, y in zip(solo_1, acompanado, strict=True))
    _informar("determinismo", {"diferencia_maxima_en_lote": diferencia})
    assert acompanado == solo_1
    duplicado = _embeber(cliente_real, [texto, texto, "Otro texto."])  # mismo lote, sin relleno
    assert duplicado[0] == duplicado[1] == solo_1


def test_reordenar_real_prioriza_lo_pertinente(cliente_real: TestClient) -> None:
    consulta = "¿Qué prueba estadística se usa cuando las variables no son normales?"
    textos = [
        "La calidad del agua de los pozos rurales presenta coliformes totales.",
        "Cuando los datos no siguen una distribución normal se emplea la correlación de "
        "Spearman, una prueba no paramétrica.",
        "El liderazgo transformacional mejora el clima organizacional.",
    ]
    respuesta = cliente_real.post("/reordenar", json={"consulta": consulta, "textos": textos})
    assert respuesta.status_code == 200, respuesta.text
    puntajes = respuesta.json()["puntajes"]
    assert all(0.0 <= p <= 1.0 for p in puntajes)
    assert puntajes[1] == max(puntajes) and puntajes[1] > 0.5
    otra = cliente_real.post("/reordenar", json={"consulta": consulta, "textos": textos[1:2]})
    assert otra.json()["puntajes"][0] == puntajes[1]  # mismo par, mismo puntaje
    _informar("reordenar", {"puntajes": [round(p, 4) for p in puntajes]})


def test_medicion_de_memoria_y_tiempo_con_lote_de_prueba(cliente_real: TestClient) -> None:
    """Lote de prueba: 64 fragmentos de unos 350 tokens y un reranking de 30 candidatos,
    los valores iniciales de la recuperación (k = 30)."""
    fragmentos = [parrafo_ficticio(i) for i in range(64)]
    inicio = time.perf_counter()
    vectores = _embeber(cliente_real, fragmentos)
    segundos_embeber = time.perf_counter() - inicio
    assert len(vectores) == 64

    consulta = "relación entre ansiedad y rendimiento académico en universitarios"
    inicio = time.perf_counter()
    respuesta = cliente_real.post(
        "/reordenar", json={"consulta": consulta, "textos": fragmentos[:30]}
    )
    segundos_reordenar = time.perf_counter() - inicio
    assert respuesta.status_code == 200

    memoria = cliente_real.get("/salud").json()["memoria"]
    _informar(
        "lote",
        {
            "fragmentos": 64,
            "segundos_embeber": round(segundos_embeber, 2),
            "fragmentos_por_segundo": round(64 / segundos_embeber, 2),
            "candidatos_reordenados": 30,
            "segundos_reordenar": round(segundos_reordenar, 2),
            "memoria_mb": memoria,
        },
    )
    if memoria["pico_mb"] is not None:
        # Fase 1, 16: "RAM de unos 5 GB" para ambos modelos; margen para el lote.
        assert memoria["pico_mb"] < 7000
