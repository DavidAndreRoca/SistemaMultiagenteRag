"""T16: fusión por rangos recíprocos, presupuesto de contexto y suficiencia en dos pasos."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.administracion.parametros import ParametrosFuncionales, parametros_iniciales
from app.instrucciones import cargador
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.esquema import esquema_estricto
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, ErrorDisponibilidad, MotivoError, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.rag.fusion import fusionar, recortar_por_presupuesto
from app.rag.modelos import (
    AVISO_SIN_EVIDENCIA,
    Candidato,
    FragmentoContexto,
    JuicioSuficiencia,
    PasoSuficiencia,
    Recuperacion,
)
from app.rag.suficiencia import decidir, sobre_umbral

INSTRUCCION = cargador.cargar("suficiencia", "v1")


@dataclass(frozen=True)
class Hallazgo:
    fragmento_id: uuid.UUID
    puntaje: float


def ids(n: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=i + 1) for i in range(n)]


def test_rrf_suma_las_dos_listas_con_la_constante() -> None:
    a, b, c, d = ids(4)
    densos = [Hallazgo(a, 0.9), Hallazgo(b, 0.8), Hallazgo(c, 0.7)]
    lexicos = [Hallazgo(c, 3.0), Hallazgo(d, 2.0)]
    fusion = fusionar(densos, lexicos, constante=60)
    assert [x.fragmento_id for x in fusion] == [c, a, b, d]
    por_id = {x.fragmento_id: x for x in fusion}
    assert por_id[c].puntaje_fusionado == pytest.approx(1 / 63 + 1 / 61)
    assert por_id[a].puntaje_fusionado == pytest.approx(1 / 61)
    assert (por_id[c].puntaje_denso, por_id[c].puntaje_lexico) == (0.7, 3.0)
    assert (por_id[d].puntaje_denso, por_id[d].puntaje_lexico) == (None, 2.0)


def test_rrf_es_determinista_ante_empates() -> None:
    a, b = ids(2)
    primera = fusionar([Hallazgo(a, 1.0)], [Hallazgo(b, 1.0)], constante=60)
    segunda = fusionar([Hallazgo(a, 1.0)], [Hallazgo(b, 1.0)], constante=60)
    assert [x.fragmento_id for x in primera] == [x.fragmento_id for x in segunda] == [a, b]
    assert fusionar([], [], constante=60) == []


@pytest.mark.parametrize(
    ("tokens", "maximo", "presupuesto", "esperados"),
    [
        ([400] * 8, 8, 2400, 6),  # R-01: unos 6 fragmentos de 400 tokens
        ([365] * 8, 8, 2400, 6),
        ([300] * 10, 8, 2400, 8),  # nunca más de n_reranking
        ([3000, 100], 8, 2400, 1),  # el primero entra aunque solo él lo supere
        ([1000, 1500, 100], 8, 2400, 1),  # no se salta uno para meter otro más corto
        ([], 8, 2400, 0),
    ],
)
def test_presupuesto_de_contexto_sin_cortar_fragmentos(
    tokens: list[int], maximo: int, presupuesto: int, esperados: int
) -> None:
    assert recortar_por_presupuesto(tokens, maximo, presupuesto) == esperados


def test_parametros_iniciales_de_t16() -> None:
    parametros = parametros_iniciales()
    assert (parametros.candidatos_reranking, parametros.presupuesto_tokens_contexto) == (20, 2400)
    assert (parametros.k_denso, parametros.k_lexico, parametros.n_reranking) == (30, 30, 8)
    assert parametros.versiones_instrucciones["suficiencia"] == "v1"
    with pytest.raises(ValueError, match="candidatos_reranking"):
        ParametrosFuncionales(candidatos_reranking=5)  # menos que n_reranking
    with pytest.raises(ValueError, match="candidatos_reranking"):
        ParametrosFuncionales(candidatos_reranking=61)  # más que lo recuperado


def recuperacion(*puntajes: float) -> Recuperacion:
    return Recuperacion(
        consulta_tokens_estimados=10,
        colecciones=2,
        candidatos_densos=len(puntajes),
        candidatos_lexicos=0,
        reordenados=len(puntajes),
        fragmentos=[
            FragmentoContexto(
                identificador=f"F{i}",
                posicion=i,
                candidato=Candidato(
                    fragmento_id=uuid.UUID(int=i), puntaje_fusionado=0.01, puntaje_reranking=p
                ),
                texto=f"Fragmento ficticio número {i} sobre tutoría entre pares.",
                tokens=12,
                documento_id=uuid.UUID(int=100 + i),
                titulo="Documento ficticio",
                seccion="resultados",
                pagina_inicio=1,
                pagina_fin=1,
                incompleto=False,
            )
            for i, p in enumerate(puntajes, start=1)
        ],
        duracion_recuperacion_ms=5,
        duracion_reranking_ms=7,
    )


def cadena(simulado: ProveedorSimulado) -> CadenaModelos:
    async def sin_espera(_: float) -> None:
        return None

    return CadenaModelos(
        [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
        dormir=sin_espera,
    )


def juicio(suficiente: bool) -> ProveedorSimulado:
    return ProveedorSimulado(
        respuestas={
            "JuicioSuficiencia": lambda entrada: {
                "suficiente": suficiente,
                "motivo": f"Decisión ficticia con {len(entrada.datos)} fragmentos (F1).",
            }
        }
    )


async def test_paso_1_se_abstiene_sin_llamar_al_modelo() -> None:
    simulado = juicio(True)
    decision = await decidir(
        cadena(simulado),
        INSTRUCCION,
        "¿La tutoría reduce la ansiedad?",
        recuperacion(0.9, 0.2, 0.1),
        parametros_iniciales(),
    )
    assert (decision.suficiente, decision.paso, decision.sobre_umbral) == (
        False,
        PasoSuficiencia.UMBRAL,
        1,
    )
    assert decision.aviso == AVISO_SIN_EVIDENCIA
    assert simulado.llamadas == 0
    vacia = await decidir(
        cadena(simulado), INSTRUCCION, "x", recuperacion(), parametros_iniciales()
    )
    assert not vacia.suficiente and simulado.llamadas == 0


@pytest.mark.parametrize("suficiente", [True, False])
async def test_paso_2_decide_con_el_modelo(suficiente: bool) -> None:
    simulado = juicio(suficiente)
    decision = await decidir(
        cadena(simulado),
        INSTRUCCION,
        "¿La tutoría reduce la ansiedad?",
        recuperacion(0.9, 0.6, 0.1),
        parametros_iniciales(),
    )
    assert (decision.suficiente, decision.paso) == (suficiente, PasoSuficiencia.MODELO)
    assert decision.motivo == "Decisión ficticia con 3 fragmentos (F1)."
    assert (decision.instruccion, decision.proveedor) == ("suficiencia/v1", "simulado")
    assert decision.aviso == (None if suficiente else AVISO_SIN_EVIDENCIA)
    assert simulado.llamadas == 1


async def test_los_fragmentos_van_al_modelo_como_datos_etiquetados() -> None:
    recibidas: list[EntradaModelo] = []

    def responder(entrada: EntradaModelo) -> dict[str, object]:
        recibidas.append(entrada)
        return {"suficiente": True, "motivo": "F1 y F2 tratan la pregunta."}

    simulado = ProveedorSimulado(respuestas={"JuicioSuficiencia": responder})
    await decidir(
        cadena(simulado),
        INSTRUCCION,
        "¿La tutoría reduce la ansiedad?",
        recuperacion(0.9, 0.8),
        parametros_iniciales(),
    )
    (entrada,) = recibidas
    assert [d.etiqueta for d in entrada.datos] == ["F1", "F2"]
    assert "¿La tutoría reduce la ansiedad?" in entrada.tarea


async def test_con_el_modelo_caido_no_hay_abstencion_sino_error_tecnico() -> None:
    caido = ProveedorSimulado(
        fallar=ErrorDisponibilidad(MotivoError.SOBRECARGA, Proveedor.SIMULADO)
    )
    with pytest.raises(ErrorDisponibilidad):
        await decidir(
            cadena(caido), INSTRUCCION, "pregunta", recuperacion(0.9, 0.9), parametros_iniciales()
        )


def test_umbral_y_esquema_del_juicio() -> None:
    assert sobre_umbral(recuperacion(0.5, 0.49, 0.99), 0.5) == 2
    esquema = esquema_estricto(JuicioSuficiencia)
    assert esquema["required"] == ["suficiente", "motivo"]
    assert esquema["additionalProperties"] is False


def test_metricas_de_la_linea_base() -> None:
    from pathlib import Path

    from app.rag.evaluar import Conjunto, exhaustividad, precision_contextual

    assert precision_contextual([True, False, True]) == pytest.approx((1 + 2 / 3) / 2)
    assert precision_contextual([False, False]) == 0.0
    assert precision_contextual([False, True]) == pytest.approx(0.5)
    assert exhaustividad({"a", "b"}, {"a", "c"}) == 0.5
    assert exhaustividad(set(), {"a"}) == 0.0
    # El conjunto versionado se lee con su esquema: primera ronda de revisión del equipo, con
    # 13 consultas revisadas (las reescritas y las nuevas esperan la segunda ronda).
    ruta = Path(__file__).parents[3] / "evaluacion" / "conjuntos" / "recuperacion-t16.json"
    conjunto = Conjunto.model_validate_json(ruta.read_text(encoding="utf-8"))
    assert conjunto.estado == "revisado" and len(conjunto.consultas) == 13
    assert {c.tema for c in conjunto.consultas} == {
        "TEMA-1-IA-EDUCACION",
        "TEMA-2-TRANSFORMACION-DIGITAL-MYPES",
    }
    for consulta in conjunto.consultas:
        assert consulta.origen.doi in consulta.documentos_esperados
        titulo = consulta.origen.titulo.lower()
        # Sin copiar frases del título: ninguna secuencia de 4 palabras del título.
        palabras = titulo.split()
        for i in range(len(palabras) - 3):
            assert " ".join(palabras[i : i + 4]) not in consulta.consulta.lower(), consulta.id
