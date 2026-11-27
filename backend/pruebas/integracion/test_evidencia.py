"""T19: agente D4 de evidencia por la ruta directa, con la base real (CP-05, CP-11).

Escenario compartido de T16 (``escenario_rag.py``). Embeddings de bolsa de palabras,
reordenador por coincidencia de palabras y modelo simulado. El umbral de pertinencia se
ajusta a esos embeddings ficticios; con bge-m3 el inicial es 0,55 (T19-01, apartado 3).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from app.agentes.evidencia import AgenteEvidencia, AtencionEvidencia
from app.bibliografia.referencias import ConstructorReferencias
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import EntradaModelo, ErrorDisponibilidad, MotivoError, Proveedor
from app.llm.proveedores import ProveedorSimulado
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.integracion.conftest import consultar, entrar_y_cambiar, esperar_orquestador
from pruebas.integracion.escenario_rag import CONSULTA, Escenario

pytestmark = pytest.mark.integracion

CERRADO = "Tema A, artículo 2"
ABIERTO = "Tema A, artículo 1"


class Modelo:
    """Responde con las citas que se le indiquen (por título del documento o F<n>)."""

    def __init__(self) -> None:
        self.entradas: list[EntradaModelo] = []
        self.citas: list[str] = ["F1"]
        self.caido = False

    def responder(self, entrada: EntradaModelo) -> dict[str, Any]:
        self.entradas.append(entrada)
        return {
            "respuesta": [{"afirmacion": "La tutoría reduce la ansiedad.", "citas": self.citas}],
            "evidencia_divergente": [],
            "notas_para_el_estudiante": ["Evidencia ficticia de prueba."],
        }

    def cadena(self) -> CadenaModelos:
        async def sin_espera(_: float) -> None:
            return None

        simulado = ProveedorSimulado(respuestas={"BusquedaEvidencia": self.responder})
        if self.caido:
            simulado.fallar = ErrorDisponibilidad(MotivoError.SOBRECARGA, Proveedor.SIMULADO)
        return CadenaModelos(
            [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
            dormir=sin_espera,
        )


@dataclass
class Evidencias:
    escenario: Escenario
    cliente: httpx.AsyncClient
    modelo: Modelo
    atencion: AtencionEvidencia

    async def pedir(self, consulta: str) -> httpx.Response:
        respuesta = await self.cliente.post("/caso/evidencias", json={"consulta": consulta})
        await esperar_orquestador(self.escenario.entorno)
        return respuesta

    async def ver(self, solicitud_id: str) -> dict[str, Any]:
        respuesta = await self.cliente.get(f"/caso/evidencias/{solicitud_id}")
        assert respuesta.status_code == 200, respuesta.text
        datos: dict[str, Any] = respuesta.json()
        return datos

    def identificador_de(self, solicitud_id: str, titulo: str) -> str:
        filas = consultar(
            self.escenario.entorno.url_bd,
            "SELECT r.identificador_visible FROM fragmento_recuperado r"
            " JOIN fragmento f ON f.id = r.fragmento_id JOIN documento d ON d.id = f.documento_id"
            " WHERE r.solicitud_id = %s AND d.titulo = %s ORDER BY r.posicion LIMIT 1",
            uuid.UUID(solicitud_id),
            titulo,
        )
        return str(filas[0][0])


def _umbral(escenario: Escenario, valor: float) -> None:
    consultar(
        escenario.entorno.url_bd,
        "UPDATE configuracion SET parametros = jsonb_set(parametros, '{pertinencia_umbral}',"
        " to_jsonb(%s::float)) WHERE vigente RETURNING id",
        valor,
    )


def _atencion(escenario: Escenario, modelo: Modelo) -> AtencionEvidencia:
    cadena = modelo.cadena()
    return AtencionEvidencia(
        AgenteEvidencia(escenario.servicio(), cadena, versiones=lambda: {"evidencia": "v1"}),
        EmbeddingsFicticios(),
        ConstructorReferencias(None),
        escenario.entorno.reloj,
    )


@pytest.fixture
async def evidencias(escenario: Escenario) -> AsyncIterator[Evidencias]:
    url = escenario.entorno.url_bd
    consultar(
        url,
        "UPDATE documento SET estado_oa = 'gold', url_acceso_abierto = 'https://repositorio.example/a1'"
        " WHERE titulo = %s RETURNING id",
        ABIERTO,
    )
    consultar(
        url, "UPDATE documento SET estado_oa = 'closed' WHERE titulo = %s RETURNING id", CERRADO
    )
    consultar(
        url,
        "UPDATE documento SET estado_oa = 'green' WHERE titulo = 'Aporte del caso A' RETURNING id",
    )
    _umbral(escenario, 0.3)  # embeddings de bolsa de palabras
    modelo = Modelo()
    atencion = _atencion(escenario, modelo)
    escenario.entorno.aplicacion.state.atencion_evidencia = atencion
    codigo, contrasena = escenario.credenciales["CASO-A"]
    async with escenario.entorno.cliente() as cliente:
        await entrar_y_cambiar(cliente, codigo, contrasena)
        yield Evidencias(escenario, cliente, modelo, atencion)


async def test_una_consulta_fuera_de_alcance_no_se_encola(evidencias: Evidencias) -> None:
    respuesta = await evidencias.pedir("Redacta la introducción completa de mi artículo")
    assert respuesta.status_code == 422
    datos = respuesta.json()
    assert datos["codigo"] == "consulta_rechazada"
    assert datos["detalle"]["motivo"] == "fuera_de_alcance" and "Por ejemplo" in datos["mensaje"]
    filas = consultar(
        evidencias.escenario.entorno.url_bd,
        "SELECT estado, motivo FROM solicitud WHERE id = %s",
        uuid.UUID(datos["detalle"]["solicitud_id"]),
    )
    assert filas == [("rechazada", "fuera_de_alcance")]
    assert evidencias.modelo.entradas == []  # no se consumió el modelo


async def test_una_consulta_ajena_al_tema_la_rechaza_el_clasificador(
    evidencias: Evidencias,
) -> None:
    respuesta = await evidencias.pedir(
        "Receta tradicional de ceviche peruano con limón y ají amarillo"
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"]["motivo"] == "fuera_de_alcance"
    assert evidencias.modelo.entradas == []


async def test_la_evidencia_se_entrega_con_citas_desplegables_y_fuentes_abiertas(
    evidencias: Evidencias,
) -> None:
    respuesta = await evidencias.pedir(CONSULTA)
    assert respuesta.status_code == 202, respuesta.text
    solicitud_id = respuesta.json()["id"]
    abierto = evidencias.identificador_de(solicitud_id, ABIERTO)
    # El modelo ya respondió con F1; se repite citando un fragmento del documento abierto.
    evidencias.modelo.citas = [abierto]
    vista = await evidencias.ver((await evidencias.pedir(CONSULTA)).json()["id"])
    assert vista["estado"] == "entregada" and not vista["abstencion"]
    assert vista["etiqueta"] is None and vista["advertencias"] == []
    (afirmacion,) = vista["respuesta"]
    (cita,) = afirmacion["citas"]
    assert cita["titulo"] == ABIERTO and cita["acceso_abierto"] is True
    assert cita["url_acceso_abierto"] == "https://repositorio.example/a1"
    assert cita["seccion"] == "resultados" and cita["pagina_inicio"] >= 1
    assert "tutoría" in cita["texto"]
    (fuente,) = vista["fuentes"]
    assert fuente["metodo"] == "csl_local" and ABIERTO in fuente["referencia"]
    assert {c["nombre"]: c["superada"] for c in vista["comprobaciones"]} == {
        "esquema": True,
        "citas": True,
        "acceso_abierto": True,
    }
    # Lo enviado al modelo: la consulta como alcance y los fragmentos como datos (RNF-10).
    entrada = evidencias.modelo.entradas[-1]
    assert entrada.datos[0].etiqueta == "alcance" and entrada.datos[0].contenido == CONSULTA


async def test_cp11_una_fuente_cerrada_no_se_recomienda_y_la_verificacion_falla(
    evidencias: Evidencias,
) -> None:
    primera = (await evidencias.pedir(CONSULTA)).json()["id"]
    cerrado = evidencias.identificador_de(primera, CERRADO)
    abierto = evidencias.identificador_de(primera, ABIERTO)
    evidencias.modelo.citas = [abierto, cerrado]
    vista = await evidencias.ver((await evidencias.pedir(CONSULTA)).json()["id"])
    assert vista["etiqueta"] == "con_advertencias"
    assert vista["advertencias"] == [f"cita a una fuente sin acceso abierto comprobado: {cerrado}"]
    titulos = [f["referencia"] for f in vista["fuentes"]]
    assert len(titulos) == 1 and ABIERTO in titulos[0]  # la cerrada no es fuente recomendada
    citas = {c["titulo"]: c for c in vista["respuesta"][0]["citas"]}
    assert (
        citas[CERRADO]["acceso_abierto"] is False and citas[CERRADO]["url_acceso_abierto"] is None
    )


async def test_una_cita_inventada_se_marca_con_advertencias(evidencias: Evidencias) -> None:
    evidencias.modelo.citas = ["F9"]  # solo hay F1 a F8
    vista = await evidencias.ver((await evidencias.pedir(CONSULTA)).json()["id"])
    assert vista["etiqueta"] == "con_advertencias"
    assert "cita a un fragmento no recuperado: F9" in vista["advertencias"]
    assert vista["fuentes"] == []


async def test_cp05_sin_evidencia_se_abstiene_e_invita_a_aportar(evidencias: Evidencias) -> None:
    _umbral(evidencias.escenario, 0.0)  # que pase la validación y decida la suficiencia
    respuesta = await evidencias.pedir(
        "Efectos de la política monetaria en la inflación de economías emergentes"
    )
    assert respuesta.status_code == 202
    vista = await evidencias.ver(respuesta.json()["id"])
    assert vista["estado"] == "entregada" and vista["abstencion"] is True
    assert vista["aviso"] == "Sin evidencia suficiente"
    assert vista["invitacion_aporte"] and vista["etiqueta"] == "sin_evidencia_suficiente"
    assert vista["respuesta"] == [] and evidencias.modelo.entradas == []
    # La abstención queda registrada en la base, con el caso de la solicitud.
    ((abstencion, etiqueta, caso_id, estado),) = consultar(
        evidencias.escenario.entorno.url_bd,
        "SELECT r.abstencion, r.etiqueta, r.caso_id, s.estado FROM resultado r"
        " JOIN solicitud s ON s.id = r.solicitud_id WHERE r.solicitud_id = %s",
        uuid.UUID(respuesta.json()["id"]),
    )
    assert (abstencion, etiqueta, estado) == (True, "sin_evidencia_suficiente", "entregada")
    assert caso_id == evidencias.escenario.a.caso_id


async def test_con_el_modelo_caido_la_solicitud_vuelve_a_la_cola(evidencias: Evidencias) -> None:
    """T28: una caída del proveedor deja la solicitud recuperable, de nuevo en la cola."""
    evidencias.modelo.caido = True
    evidencias.escenario.entorno.aplicacion.state.atencion_evidencia = _atencion(
        evidencias.escenario, evidencias.modelo
    )
    evidencias.atencion = evidencias.escenario.entorno.aplicacion.state.atencion_evidencia
    solicitud_id = (await evidencias.pedir(CONSULTA)).json()["id"]
    vista = await evidencias.ver(solicitud_id)
    assert (vista["estado"], vista["motivo"]) == ("recibida", "modelo:sobrecarga")
    assert vista["respuesta"] == []
    ((intentos, fragmentos),) = consultar(
        evidencias.escenario.entorno.url_bd,
        "SELECT s.intentos_tecnicos, (SELECT count(*) FROM fragmento_recuperado f"
        " WHERE f.solicitud_id = s.id) FROM solicitud s WHERE s.id = %s",
        uuid.UUID(solicitud_id),
    )
    assert intentos == 1 and fragmentos > 0  # el próximo intento los borra antes de recuperar


async def test_ver_una_solicitud_en_curso_no_la_marca_interrumpida(
    evidencias: Evidencias,
) -> None:
    url = evidencias.escenario.entorno.url_bd
    ((version_id, configuracion_id),) = consultar(
        url,
        "SELECT version_id, configuracion_id FROM solicitud WHERE id = %s",
        evidencias.escenario.solicitud_a,
    )
    ((solicitud_id,),) = consultar(
        url,
        "INSERT INTO solicitud (caso_id, version_id, tipo, alcance_tipo, alcance_ref,"
        " configuracion_id, estado) VALUES (%s, %s, 'busqueda_evidencia', 'consulta',"
        " 'consulta cortada', %s, 'recuperando') RETURNING id",
        evidencias.escenario.a.caso_id,
        version_id,
        configuracion_id,
    )
    # T28: la API no sabe si el trabajador la atiende; las huérfanas las recupera él.
    vista = await evidencias.ver(str(solicitud_id))
    assert (vista["estado"], vista["motivo"]) == ("recuperando", None)


async def test_otro_caso_no_ve_la_solicitud_ni_pide_sin_version(evidencias: Evidencias) -> None:
    solicitud_id = (await evidencias.pedir(CONSULTA)).json()["id"]
    codigo, contrasena = evidencias.escenario.credenciales["CASO-B"]
    async with evidencias.escenario.entorno.cliente() as otro:
        await entrar_y_cambiar(otro, codigo, contrasena)
        assert (await otro.get(f"/caso/evidencias/{solicitud_id}")).status_code == 404
        sin_version = await otro.post("/caso/evidencias", json={"consulta": CONSULTA})
        assert (sin_version.status_code, sin_version.json()["codigo"]) == (409, "sin_version")


async def test_el_registro_no_lleva_la_consulta_ni_la_salida(
    evidencias: Evidencias, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    with caplog.at_level(logging.INFO):
        await evidencias.pedir(CONSULTA)
        await evidencias.pedir("Redacta la introducción completa de mi artículo")
    registro = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert "evidencia registrada" in registro and "solicitud de evidencia" in registro
    assert (
        "tutoría entre pares reduce" not in registro and "Redacta la introducción" not in registro
    )
    assert "La tutoría reduce la ansiedad." not in registro


async def test_el_comando_completa_solo_el_acceso_abierto(escenario: Escenario) -> None:
    from app.bd.enumeraciones import Rol
    from app.corpus.acceso_abierto import completar
    from app.repositorios.contexto import ContextoAcceso
    from app.repositorios.unidad import UnidadDeTrabajo
    from pruebas.dobles_bibliografia import clientes, json_respuesta

    url = escenario.entorno.url_bd
    for titulo, doi in (
        ("Tema A, artículo 1", "10.5555/t19.abierto"),
        ("Tema A, artículo 2", "10.5555/t19.cerrado"),
        ("Tema A, otro asunto", "10.5555/t19.sin.registro"),
        ("Tema A, retirado", "10.5555/t19.retirado"),
    ):
        consultar(url, "UPDATE documento SET doi = %s WHERE titulo = %s RETURNING id", doi, titulo)
    antes = consultar(
        url, "SELECT md5(string_agg(texto || embedding::text, '' ORDER BY id)) FROM fragmento"
    )

    def unpaywall(peticion: httpx.Request) -> httpx.Response:
        doi = peticion.url.path.removeprefix("/v2/")
        if doi.endswith("abierto"):
            return json_respuesta(
                {"doi": doi, "is_oa": True, "oa_status": "gold",
                 "best_oa_location": {"url": "https://repositorio.example/oa", "license": "cc-by"}}
            )  # fmt: skip
        if doi.endswith("cerrado"):
            return json_respuesta({"doi": doi, "is_oa": False, "oa_status": "closed"})
        return json_respuesta({"error": True}, 404)

    servicios = clientes(httpx.MockTransport(unpaywall), intentos=1)
    ((cuenta_id,),) = consultar(url, "SELECT id FROM cuenta WHERE codigo = 'INV-01'")
    assert isinstance(cuenta_id, uuid.UUID)
    contexto = ContextoAcceso(cuenta_id=cuenta_id, rol=Rol.INVESTIGADOR, caso_id=None)
    ((coleccion_id,),) = consultar(url, "SELECT id FROM coleccion WHERE tema = 'TEMA-A'")
    assert isinstance(coleccion_id, uuid.UUID)
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        simulado = await completar(
            UnidadDeTrabajo(sesion), contexto, coleccion_id, servicios.unpaywall, aplicar=False
        )
    assert simulado == {"gold": 1, "closed": 1, "sin_registro": 1}  # el retirado no cuenta
    assert consultar(url, "SELECT count(*) FROM documento WHERE estado_oa <> 'desconocido'") == [
        (0,)
    ]
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        await completar(
            UnidadDeTrabajo(sesion), contexto, coleccion_id, servicios.unpaywall, aplicar=True
        )
    estados = dict(
        consultar(url, "SELECT titulo, estado_oa || '|' || coalesce(licencia, '-') FROM documento")
    )
    assert estados["Tema A, artículo 1"] == "gold|cc-by"
    assert estados["Tema A, artículo 2"] == "closed|-"
    assert estados["Tema A, otro asunto"] == "desconocido|-"
    # Los textos y los vectores no cambian.
    assert (
        consultar(
            url, "SELECT md5(string_agg(texto || embedding::text, '' ORDER BY id)) FROM fragmento"
        )
        == antes
    )
