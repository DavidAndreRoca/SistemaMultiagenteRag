"""Verificación completa (T30): evaluador de fidelidad, existencia de fuentes y registro por
intento. Sin base ni red: el modelo es el simulado y Crossref es un doble."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.bd.enumeraciones import Etiqueta, MetodoComprobacionFuentes, TipoSolicitud
from app.bd.modelos import Documento
from app.bibliografia.modelos import Estado, Motivo, ResultadoBibliografico, Servicio
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, ErrorDisponibilidad, MotivoError, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.verificacion.comprobaciones import Comprobacion
from app.verificacion.evaluador import Evaluador, afirmaciones_de
from app.verificacion.fuentes import comprobar_existencia
from app.verificacion.registro import (
    etiqueta_de,
    motivos_para_reintento,
    verificacion_de,
)

SALIDA_EVIDENCIA = {
    "respuesta": [
        {"afirmacion": "La tutoría reduce la ansiedad.", "citas": ["F1"]},
        {"afirmacion": "El efecto fue grande.", "citas": ["F2"]},
    ],
    "evidencia_divergente": [],
    "notas_para_el_estudiante": [],
}
FRAGMENTOS = {"F1": "La tutoría redujo la ansiedad.", "F2": "Efecto moderado.", "F3": "Otro."}


def _evaluador(
    clasificaciones: list[str], fallar: bool = False
) -> tuple[Evaluador, list[EntradaModelo]]:
    entradas: list[EntradaModelo] = []

    def juicio(entrada: EntradaModelo) -> dict[str, Any]:
        entradas.append(entrada)
        return {
            "afirmaciones": [
                {"afirmacion": f"afirmación {i}", "clasificacion": c}
                for i, c in enumerate(clasificaciones, 1)
            ]
        }

    simulado = ProveedorSimulado(
        respuestas={"JuicioFidelidad": juicio},
        fallar=ErrorDisponibilidad(MotivoError.SOBRECARGA) if fallar else None,
    )

    async def sin_espera(_: float) -> None:
        return None

    cadena = CadenaModelos(
        [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
        dormir=sin_espera,
    )
    return Evaluador(cadena, versiones=lambda: {"evaluador": "v1"}), entradas


def test_las_afirmaciones_de_cada_tipo_llevan_sus_citas() -> None:
    assert afirmaciones_de(TipoSolicitud.BUSQUEDA_EVIDENCIA, SALIDA_EVIDENCIA) == [
        "La tutoría reduce la ansiedad. [F1]",
        "El efecto fue grande. [F2]",
    ]
    hallazgo = {"descripcion": "Falta el objetivo.", "recomendacion": "Revise.", "citas": ["F3"]}
    assert afirmaciones_de(TipoSolicitud.REVISION_ESTRUCTURA, {"hallazgos": [hallazgo]}) == [
        "Hallazgo: Falta el objetivo. Qué revisar: Revise. [F3]"
    ]
    assert afirmaciones_de(TipoSolicitud.VERIFICACION_REFERENCIAS, {"referencias": []}) == []


async def test_una_salida_respaldada_supera_la_fidelidad_y_solo_envia_lo_citado() -> None:
    evaluador, entradas = _evaluador(["respaldada", "respaldada"])
    comprobacion = await evaluador.fidelidad(
        None,  # type: ignore[arg-type]  # con versiones fijas no se usa la base
        TipoSolicitud.BUSQUEDA_EVIDENCIA,
        SALIDA_EVIDENCIA,
        FRAGMENTOS,
        0.9,
    )
    assert comprobacion.numero == 6 and comprobacion.superada
    assert comprobacion.datos["fidelidad"] == 1.0 and comprobacion.datos["total"] == 2
    (entrada,) = entradas
    assert [b.etiqueta for b in entrada.datos] == ["salida", "F1", "F2"]  # F3 no se citó


async def test_cp06_una_afirmacion_no_respaldada_baja_la_fidelidad_y_pide_reintento() -> None:
    evaluador, _ = _evaluador(["respaldada", "no_respaldada", "contradicha", "respaldada"])
    comprobacion = await evaluador.fidelidad(
        None,  # type: ignore[arg-type]
        TipoSolicitud.BUSQUEDA_EVIDENCIA,
        SALIDA_EVIDENCIA,
        FRAGMENTOS,
        0.9,
    )
    assert not comprobacion.superada and comprobacion.reintentable
    assert comprobacion.datos["fidelidad"] == 0.5
    assert comprobacion.motivos[0] == (
        "fidelidad 0.50 menor que el umbral 0.90: 1 afirmaciones no respaldadas y 1 contradichas"
    )
    assert comprobacion.motivos[1:] == ["sin respaldo: afirmación 2", "sin respaldo: afirmación 3"]


async def test_sin_afirmaciones_la_fidelidad_no_aplica() -> None:
    evaluador, entradas = _evaluador([])
    comprobacion = await evaluador.fidelidad(
        None,  # type: ignore[arg-type]
        TipoSolicitud.REVISION_ESTRUCTURA,
        {"hallazgos": []},
        FRAGMENTOS,
        0.9,
    )
    assert comprobacion.superada and comprobacion.datos["fidelidad"] is None
    assert entradas == []  # no se llama al modelo


async def test_si_el_evaluador_no_responde_no_se_supera_ni_se_reintenta() -> None:
    evaluador, _ = _evaluador(["respaldada"], fallar=True)
    comprobacion = await evaluador.conservacion(
        None,  # type: ignore[arg-type]
        "El original.",
        "La propuesta.",
        0.9,
    )
    assert comprobacion.nombre == "conservacion_del_contenido"
    assert not comprobacion.superada and not comprobacion.reintentable


async def test_la_conservacion_envia_el_original_y_la_propuesta() -> None:
    evaluador, entradas = _evaluador(["respaldada", "no_respaldada"])
    comprobacion = await evaluador.conservacion(
        None,  # type: ignore[arg-type]
        "El original.",
        "La propuesta con un dato nuevo.",
        0.9,
    )
    assert not comprobacion.superada and comprobacion.datos["no_respaldadas"] == 1
    assert [b.etiqueta for b in entradas[0].datos] == ["original", "propuesta"]


class CrossrefDoble:
    def __init__(self, estados: dict[str, Estado]) -> None:
        self.estados = estados

    async def por_doi(self, doi: str) -> ResultadoBibliografico:
        estado = self.estados[doi]
        if estado is Estado.NO_COMPROBABLE:
            return ResultadoBibliografico.no_comprobable(Servicio.CROSSREF, Motivo.TIEMPO_AGOTADO)
        return ResultadoBibliografico(servicio=Servicio.CROSSREF, estado=estado)


def _documento(doi: str | None, completo: bool = True) -> Documento:
    return Documento(
        id=uuid.uuid4(),
        titulo="Obra ficticia",
        autores=[{"nombres": "Ana", "apellidos": "Ficticia"}] if completo else [],
        anio=2024 if completo else None,
        doi=doi,
    )


async def test_la_existencia_se_confirma_por_doi_o_por_metadatos() -> None:
    crossref = CrossrefDoble({"10.1/a": Estado.ENCONTRADO, "10.1/b": Estado.NO_ENCONTRADO})
    comprobacion = await comprobar_existencia(
        [_documento("10.1/a"), _documento("10.1/b"), _documento(None)], crossref
    )
    assert comprobacion.superada
    assert comprobacion.datos == {
        "citadas": 3,
        "confirmadas": 3,
        "no_comprobables": 0,
        "metodo": MetodoComprobacionFuentes.MIXTO.value,
    }


async def test_una_fuente_sin_metadatos_falla_y_pide_reintento() -> None:
    comprobacion = await comprobar_existencia([_documento(None, completo=False)], None)
    assert not comprobacion.superada and comprobacion.reintentable
    assert comprobacion.motivos == ["fuente sin existencia comprobada: Obra ficticia"]


async def test_rn18_un_servicio_caido_da_no_comprobable_sin_reintento() -> None:
    crossref = CrossrefDoble({"10.1/a": Estado.NO_COMPROBABLE})
    comprobacion = await comprobar_existencia([_documento("10.1/a")], crossref)
    assert not comprobacion.superada and not comprobacion.reintentable
    assert comprobacion.datos["no_comprobables"] == 1 and comprobacion.datos["metodo"] is None


def test_la_verificacion_de_un_intento_lleva_cada_comprobacion_en_su_columna() -> None:
    comprobaciones = [
        Comprobacion(numero=1, nombre="esquema", superada=True),
        Comprobacion(numero=2, nombre="no_reescritura", superada=True),
        Comprobacion(numero=2, nombre="sin_datos_inventados", superada=False, motivos=["dato"]),
        Comprobacion(numero=3, nombre="citas", superada=True),
        Comprobacion(
            numero=6,
            nombre="fidelidad",
            superada=True,
            datos={
                "fidelidad": 0.95,
                "umbral": 0.9,
                "total": 20,
                "respaldadas": 19,
                "no_respaldadas": 1,
                "contradichas": 0,
                "modelo": "simulado:x",
            },
        ),
    ]
    fila = verificacion_de(uuid.uuid4(), 2, comprobaciones, datetime(2026, 11, 27, tzinfo=UTC))
    assert (fila.intento, fila.formato_ok, fila.limites_ok, fila.citas_ok) == (2, True, False, True)
    assert fila.acceso_abierto_ok is None and fila.n_fuentes_citadas == 0  # no aplican
    assert (fila.fidelidad, fila.umbral_fidelidad, fila.afirmaciones_total) == (0.95, 0.9, 20)
    assert fila.modelo_evaluador == "simulado:x"
    assert not fila.superada and fila.motivos_falla == ["dato"]
    assert etiqueta_de(comprobaciones) is Etiqueta.CON_ADVERTENCIAS
    assert etiqueta_de(comprobaciones[:2]) is Etiqueta.VERIFICADA


@pytest.mark.parametrize(("reintentable", "esperado"), [(True, ["motivo"]), (False, [])])
def test_solo_las_fallas_corregibles_dan_motivos_para_el_reintento(
    reintentable: bool, esperado: list[str]
) -> None:
    falla = Comprobacion(
        numero=4, nombre="existencia", superada=False, motivos=["motivo"], reintentable=reintentable
    )
    assert motivos_para_reintento([falla]) == esperado


def test_el_informe_de_latencias_compara_el_p95_con_el_objetivo() -> None:
    from app.orquestacion.latencias import percentil, resumir, texto
    from app.repositorios.tiempos import TiemposSolicitud

    assert percentil([10, 20, 30, 40], 50) == 20 and percentil([10, 20, 30, 40], 95) == 40
    assert percentil([], 95) is None
    tiempos = [
        TiemposSolicitud(TipoSolicitud.PLAN_TAREA, ms, {"orquestacion": ms - 1000})
        for ms in (20_000, 30_000, 90_000)
    ] + [TiemposSolicitud(TipoSolicitud.VERIFICACION_REFERENCIAS, 100_000, {})]
    plan, referencias = resumir(tiempos)
    assert (plan.n, plan.mediana_s, plan.p95_s, plan.cumple) == (3, 30.0, 90.0, False)
    assert plan.etapas_p95_s == {"orquestacion": 89.0}
    assert referencias.objetivo_s == 120 and referencias.cumple
    assert "plan_tarea | 3 | 30.0 | 90.0 | 60 | no" in texto([plan, referencias])
