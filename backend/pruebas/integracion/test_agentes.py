"""T18: clase base de agente, comprobaciones con la base real y constructor de referencias.

Reutiliza el escenario de T16 (``test_rag.py``): casos A y B en TEMA-A, TEMA-B, guías y
documentos ficticios sobre tutoría. El modelo es el proveedor simulado y doi.org responde
por ``httpx.MockTransport``.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import pytest

from app.agentes.contrato import Agente, EstadoAgente, TipoNoAtendido
from app.agentes.esquemas import BusquedaEvidencia
from app.bd.enumeraciones import TipoAlcance, TipoSolicitud
from app.bd.modelos import Resultado, Solicitud
from app.bibliografia.referencias import ConstructorReferencias, MetodoReferencia
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.repositorios.unidad import UnidadDeTrabajo
from app.verificacion.comprobaciones import comprobar_citas, comprobar_esquema
from pruebas.dobles_bibliografia import clientes
from pruebas.integracion.conftest import consultar
from pruebas.integracion.escenario_rag import CONSULTA, Escenario

pytestmark = pytest.mark.integracion


class AgentePrueba(Agente):
    """Un agente mínimo de búsqueda de evidencia, solo para probar el contrato común."""

    tipos = frozenset({TipoSolicitud.BUSQUEDA_EVIDENCIA})
    instruccion = "contrato"

    def consulta(self, estado: EstadoAgente) -> str:
        return estado.alcance

    def tarea(self, estado: EstadoAgente) -> str:
        return "Responde con la evidencia de los fragmentos, citándolos."


class Modelo:
    """Simulado que responde con citas fijas y guarda lo que recibe."""

    def __init__(self, citas: list[str]) -> None:
        self.entradas: list[EntradaModelo] = []
        self.citas = citas

    def responder(self, entrada: EntradaModelo) -> dict[str, Any]:
        self.entradas.append(entrada)
        return {
            "respuesta": [{"afirmacion": "La tutoría reduce la ansiedad.", "citas": self.citas}],
            "evidencia_divergente": [],
            "notas_para_el_estudiante": [],
        }

    def cadena(self) -> CadenaModelos:
        simulado = ProveedorSimulado(respuestas={"BusquedaEvidencia": self.responder})
        return CadenaModelos(
            [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)]
        )


def _agente(escenario: Escenario, modelo: Modelo) -> AgentePrueba:
    return AgentePrueba(escenario.servicio(), modelo.cadena(), versiones=lambda: {"contrato": "v1"})


def _estado(
    escenario: Escenario, solicitud_id: uuid.UUID, alcance: str = CONSULTA, **extra: Any
) -> EstadoAgente:
    (version_id,) = consultar(
        escenario.entorno.url_bd, "SELECT version_id FROM solicitud WHERE id = %s", solicitud_id
    )[0]
    assert isinstance(version_id, uuid.UUID) and escenario.a.caso_id is not None
    return EstadoAgente(
        solicitud_id=solicitud_id,
        caso_id=escenario.a.caso_id,
        tipo=TipoSolicitud.BUSQUEDA_EVIDENCIA,
        alcance=alcance,
        version_id=version_id,
        **extra,
    )


async def _atender(escenario: Escenario, agente: Agente, estado: EstadoAgente) -> Any:
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        return await agente.atender(UnidadDeTrabajo(sesion), escenario.a, estado)


async def _recuperados(escenario: Escenario) -> set[str]:
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        return await UnidadDeTrabajo(sesion).fragmentos_recuperados.identificadores(
            escenario.a, escenario.solicitud_a
        )


async def test_el_agente_genera_con_el_contexto_cerrado_y_pasa_las_comprobaciones(
    escenario: Escenario,
) -> None:
    modelo = Modelo(["F1", "F2"])
    resultado = await _atender(
        escenario, _agente(escenario, modelo), _estado(escenario, escenario.solicitud_a)
    )
    assert not resultado.abstencion and isinstance(resultado.salida, BusquedaEvidencia)
    assert (resultado.instruccion, resultado.proveedor) == ("contrato/v1", "simulado")
    (entrada,) = modelo.entradas
    etiquetas = [d.etiqueta for d in entrada.datos]
    assert etiquetas == ["alcance", *[f"F{i}" for i in range(1, 9)]]
    assert entrada.datos[0].contenido == CONSULTA
    recuperados = await _recuperados(escenario)
    assert recuperados == {f"F{i}" for i in range(1, 9)}
    assert comprobar_esquema(TipoSolicitud.BUSQUEDA_EVIDENCIA, resultado.salida).superada
    assert comprobar_citas(resultado.salida, recuperados).superada


async def test_una_salida_que_cita_f9_se_rechaza(escenario: Escenario) -> None:
    """Criterio de T18: solo hay F1 a F8 recuperados para la solicitud."""
    modelo = Modelo(["F1", "F9"])
    resultado = await _atender(
        escenario, _agente(escenario, modelo), _estado(escenario, escenario.solicitud_a)
    )
    comprobacion = comprobar_citas(resultado.salida, await _recuperados(escenario))
    assert not comprobacion.superada
    assert comprobacion.motivos == ["cita a un fragmento no recuperado: F9"]


async def test_sin_evidencia_el_agente_se_abstiene_sin_llamar_al_modelo(
    escenario: Escenario,
) -> None:
    modelo = Modelo(["F1"])
    estado = _estado(
        escenario,
        escenario.solicitud_a,
        "Efectos de la política monetaria en la inflación de economías emergentes",
    )
    resultado = await _atender(escenario, _agente(escenario, modelo), estado)
    assert resultado.abstencion and resultado.salida is None
    assert modelo.entradas == []


async def test_en_el_intento_2_recibe_los_motivos_de_falla(escenario: Escenario) -> None:
    modelo = Modelo(["F1"])
    estado = _estado(
        escenario,
        escenario.solicitud_a,
        intento=2,
        motivos_falla=["cita a un fragmento no recuperado: F9"],
    )
    await _atender(escenario, _agente(escenario, modelo), estado)
    (entrada,) = modelo.entradas
    assert "cita a un fragmento no recuperado: F9" in entrada.tarea


async def test_sin_memoria_otra_solicitud_del_caso_no_cambia_lo_enviado(
    escenario: Escenario,
) -> None:
    """Una solicitud previa con su resultado no llega al modelo (n.° 8 del plan)."""
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        configuracion, _ = await unidad.configuracion.vigente()
        anterior = await unidad.solicitudes.obtener(escenario.a, escenario.solicitud_a)
        assert anterior is not None
        nueva = await unidad.solicitudes.agregar(
            escenario.a,
            Solicitud(
                version_id=anterior.version_id,
                tipo=TipoSolicitud.BUSQUEDA_EVIDENCIA,
                alcance_tipo=TipoAlcance.CONSULTA,
                alcance_ref="otra consulta ficticia",
                configuracion_id=configuracion.id,
            ),
        )
        await unidad.resultados.agregar(
            escenario.a,
            Resultado(
                solicitud_id=escenario.solicitud_a,
                intento=1,
                salida={"respuesta": [{"afirmacion": "MARCA-DE-LA-SOLICITUD-ANTERIOR"}]},
            ),
        )
        await unidad.confirmar()
        nueva_id = nueva.id
    primero, segundo = Modelo(["F1"]), Modelo(["F1"])
    await _atender(
        escenario, _agente(escenario, primero), _estado(escenario, escenario.solicitud_a)
    )
    await _atender(escenario, _agente(escenario, segundo), _estado(escenario, nueva_id))
    assert primero.entradas == segundo.entradas
    assert "MARCA-DE-LA-SOLICITUD-ANTERIOR" not in json.dumps(
        [e.model_dump() for e in segundo.entradas], ensure_ascii=False
    )


async def test_el_agente_no_atiende_otros_tipos_ni_otro_caso(escenario: Escenario) -> None:
    agente = _agente(escenario, Modelo(["F1"]))
    otro_tipo = _estado(escenario, escenario.solicitud_a).model_copy(
        update={"tipo": TipoSolicitud.REVISION_ESTRUCTURA}
    )
    with pytest.raises(TipoNoAtendido):
        await _atender(escenario, agente, otro_tipo)
    assert escenario.b.caso_id is not None
    ajeno = _estado(escenario, escenario.solicitud_a).model_copy(
        update={"caso_id": escenario.b.caso_id}
    )
    with pytest.raises(TipoNoAtendido):
        await _atender(escenario, agente, ajeno)


# --- Constructor de referencias ---


def _sembrar_metadatos(escenario: Escenario) -> None:
    """El artículo 1 del tema A con DOI; el aporte del caso A, sin DOI."""
    url = escenario.entorno.url_bd
    consultar(
        url,
        "UPDATE documento SET doi = %s, anio = 2021, idioma = 'es',"
        " revista_editorial = 'Revista Ficticia de Pedagogía', autores = %s::jsonb"
        " WHERE titulo = 'Tema A, artículo 1' RETURNING id",
        "10.5555/sma.t18.01",
        json.dumps([{"nombres": "Ana", "apellidos": "Quispe"}]),
    )
    consultar(
        url,
        "UPDATE documento SET anio = 2023, idioma = 'es', revista_editorial = 'Editorial Ficticia',"
        " autores = %s::jsonb WHERE titulo = 'Aporte del caso A' RETURNING id",
        json.dumps([{"nombres": "Luis", "apellidos": "Huamán"}]),
    )


class DoiOrg:
    """doi.org simulado: responde la cita en el estilo pedido o falla."""

    def __init__(self, disponible: bool = True) -> None:
        self.disponible = disponible
        self.estilos: list[str] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        aceptar = peticion.headers.get("accept", "")
        self.estilos.append(aceptar.split("style=")[1].split(";")[0])
        if not self.disponible:
            return httpx.Response(503)
        return httpx.Response(
            200,
            text="[1]A. Quispe, «Cita del registro del DOI», Revista Ficticia de Pedagogía,"
            " 2021.\n",
            headers={"content-type": "text/x-bibliography; charset=utf-8"},
        )


async def _referencias(
    escenario: Escenario,
    doi_org: DoiOrg,
    norma: str,
    identificadores: list[str],
    contexto: Any = None,
) -> Any:
    servicios = clientes(httpx.MockTransport(doi_org), intentos=1)
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        return await ConstructorReferencias(servicios.doi).construir(
            UnidadDeTrabajo(sesion),
            contexto or escenario.a,
            escenario.solicitud_a,
            identificadores,
            norma,
        )


@pytest.mark.parametrize(
    ("norma", "estilo"), [("ieee", "ieee"), ("apa7", "apa"), ("vancouver", "vancouver")]
)
async def test_las_referencias_salen_de_los_metadatos_guardados(
    escenario: Escenario, norma: str, estilo: str
) -> None:
    await escenario.preparar()  # guarda F1 a F8 de la solicitud de A
    _sembrar_metadatos(escenario)
    doi_org = DoiOrg()
    todos = [f"F{i}" for i in range(1, 9)] + ["F99"]  # F99 no existe: no arma nada
    referencias = await _referencias(escenario, doi_org, norma, todos)
    por_titulo = {
        str(t): uuid.UUID(str(i))
        for i, t in consultar(escenario.entorno.url_bd, "SELECT id, titulo FROM documento")
    }
    armadas = {r.documento_id: r for r in referencias}
    # Una referencia por documento citado, con los identificadores que lo citan.
    assert sum(len(r.identificadores) for r in referencias) == 8
    con_doi = armadas[por_titulo["Tema A, artículo 1"]]
    assert (con_doi.metodo, con_doi.norma, con_doi.doi) == (
        MetodoReferencia.DOI,
        norma,
        "10.5555/sma.t18.01",
    )
    assert (
        con_doi.texto
        == "A. Quispe, «Cita del registro del DOI», Revista Ficticia de Pedagogía, 2021."
    )
    assert estilo in doi_org.estilos  # pidió la cita en el estilo CSL de la norma
    sin_doi = armadas[por_titulo["Aporte del caso A"]]
    assert sin_doi.metodo is MetodoReferencia.CSL_LOCAL
    assert (
        "Huamán" in sin_doi.texto
        and "Aporte del caso A" in sin_doi.texto
        and "2023" in sin_doi.texto
    )


async def test_si_doi_org_no_responde_se_arma_en_local(escenario: Escenario) -> None:
    await escenario.preparar()
    _sembrar_metadatos(escenario)
    referencias = await _referencias(
        escenario, DoiOrg(disponible=False), "apa7", [f"F{i}" for i in range(1, 9)]
    )
    assert {r.metodo for r in referencias} == {MetodoReferencia.CSL_LOCAL}
    con_doi = next(r for r in referencias if r.doi)
    assert con_doi.texto.startswith(
        "Quispe, A. (2021). Tema A, artículo 1. Revista Ficticia de Pedagogía."
    )
    assert con_doi.texto.endswith("https://doi.org/10.5555/sma.t18.01")


async def test_otro_caso_no_obtiene_referencias_de_la_solicitud(escenario: Escenario) -> None:
    await escenario.preparar()
    assert await _referencias(escenario, DoiOrg(), "ieee", ["F1", "F2"], contexto=escenario.b) == []
