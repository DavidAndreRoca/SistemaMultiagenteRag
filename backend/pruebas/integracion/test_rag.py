"""T16: recuperación híbrida y suficiencia con la base real (RF-10, RN-03, RN-04, CP-05).

Embeddings de bolsa de palabras (``EmbeddingsFicticios``) y un reordenador por
coincidencia de palabras (``ReordenadorFicticio``); el juicio de suficiencia, con el
proveedor simulado. Todos los textos son ficticios.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from app.administracion.parametros import parametros_iniciales
from app.bd.enumeraciones import (
    EstadoDocumento,
    OrigenDocumento,
    Rol,
    SeccionNormalizada,
    TipoAlcance,
    TipoAutoria,
    TipoColeccion,
    TipoSolicitud,
)
from app.bd.modelos import Coleccion, Documento, Fragmento, Solicitud, VersionBorrador
from app.casos import servicio as casos
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.rag.recuperacion import Recuperador
from app.rag.servicio import Evidencia, ServicioEvidencia, SolicitudInexistente
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.dobles_rag import ReordenadorFicticio
from pruebas.integracion.conftest import Entorno, consultar

pytestmark = pytest.mark.integracion

CONSULTA = "Quiero sustentar que la tutoría entre pares reduce la ansiedad estadística"
SOBRE_TUTORIA = (
    "La tutoría entre pares reduce la ansiedad estadística de los estudiantes ficticios {marca}."
)
OTRO_ASUNTO = "El riego por goteo mejora el rendimiento de los cultivos de espárrago {marca}."


@dataclass
class Escenario:
    entorno: Entorno
    a: ContextoAcceso
    b: ContextoAcceso
    titulos: dict[str, str]  # documento -> colección de origen
    solicitud_a: uuid.UUID
    reordenador: ReordenadorFicticio
    simulado: ProveedorSimulado

    def servicio(self) -> ServicioEvidencia:
        async def sin_espera(_: float) -> None:
            return None

        modelo = CadenaModelos(
            [
                Eslabon(
                    self.simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0
                )
            ],
            dormir=sin_espera,
        )
        return ServicioEvidencia(
            Recuperador(EmbeddingsFicticios(), self.reordenador),
            modelo,
            lambda: datetime(2026, 11, 22, 12, tzinfo=UTC),
        )

    async def preparar(
        self, consulta: str = CONSULTA, contexto: ContextoAcceso | None = None
    ) -> Evidencia:
        async with self.entorno.aplicacion.state.fabrica_sesiones() as sesion:
            return await self.servicio().preparar(
                UnidadDeTrabajo(sesion), contexto or self.a, self.solicitud_a, consulta
            )


async def _documento(
    unidad: UnidadDeTrabajo,
    coleccion_id: uuid.UUID,
    titulo: str,
    textos: list[str],
    estado: EstadoDocumento = EstadoDocumento.ACTIVO,
    tokens: int = 300,
) -> None:
    embebidos = await EmbeddingsFicticios().embeber(textos)
    huella = hashlib.sha256(titulo.encode()).hexdigest()
    documento = Documento(
        coleccion_id=coleccion_id,
        titulo=titulo,
        huella_sha256=huella,
        estado=estado,
        origen=OrigenDocumento.INGESTA,
        retirado_en=datetime(2026, 11, 1, tzinfo=UTC)
        if estado is EstadoDocumento.RETIRADO
        else None,
    )
    unidad._sesion.add(documento)
    await unidad._sesion.flush()
    for orden, (texto, vector) in enumerate(zip(textos, embebidos.vectores, strict=True)):
        unidad._sesion.add(
            Fragmento(
                documento_id=documento.id,
                coleccion_id=coleccion_id,
                orden=orden,
                texto=texto,
                seccion_normalizada=SeccionNormalizada.RESULTADOS,
                seccion_original="3. Resultados",
                pagina_inicio=orden + 1,
                pagina_fin=orden + 1,
                tokens=tokens,
                embedding=vector,
            )
        )


@pytest.fixture
async def escenario(entorno: Entorno) -> Escenario:
    """Casos A y B en TEMA-A (cada uno con su colección personal), TEMA-B y guías, todos
    con fragmentos sobre tutoría; un documento retirado y uno de otro asunto en TEMA-A."""
    await entorno.crear_investigador()
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        inv = await unidad.autenticacion.cuenta_por_codigo("INV-01")
        assert inv is not None
        investigador = ContextoAcceso(inv.id, Rol.INVESTIGADOR, None)
        await casos.crear_coleccion_cientifica(unidad, investigador, "TEMA-A")
        await casos.crear_coleccion_cientifica(unidad, investigador, "TEMA-B")
        guias = await unidad.colecciones_investigador.agregar(
            investigador, Coleccion(tipo=TipoColeccion.GUIAS)
        )
        await unidad.confirmar()
        caso_a = await casos.crear_caso(
            unidad, investigador, "CASO-A", TipoAutoria.INDIVIDUAL, "TEMA-A"
        )
        caso_b = await casos.crear_caso(
            unidad, investigador, "CASO-B", TipoAutoria.INDIVIDUAL, "TEMA-A"
        )
        tema_b = (
            await casos.crear_caso(unidad, investigador, "CASO-C", TipoAutoria.INDIVIDUAL, "TEMA-B")
        ).caso.coleccion_cientifica_id
        contextos = {}
        for creado in (caso_a, caso_b):
            cuenta = await unidad.autenticacion.cuenta_por_codigo(creado.credenciales[0].codigo)
            assert cuenta is not None
            contextos[creado.caso.codigo] = ContextoAcceso(cuenta.id, Rol.CASO, creado.caso.id)

        origen = {
            "Tema A, artículo 1": "cientifica_A",
            "Tema A, artículo 2": "cientifica_A",
            "Aporte del caso A": "personal_A",
            "Aporte del caso B": "personal_B",
            "Tema B, artículo": "cientifica_B",
            "Guía del programa": "guias",
            "Tema A, retirado": "retirado",
            "Tema A, otro asunto": "otro_asunto",
        }
        colecciones = {
            "cientifica_A": caso_a.caso.coleccion_cientifica_id,
            "personal_A": caso_a.coleccion_personal.id,
            "personal_B": caso_b.coleccion_personal.id,
            "cientifica_B": tema_b,
            "guias": guias.id,
            "retirado": caso_a.caso.coleccion_cientifica_id,
            "otro_asunto": caso_a.caso.coleccion_cientifica_id,
        }
        for titulo, clave in origen.items():
            plantilla = OTRO_ASUNTO if clave == "otro_asunto" else SOBRE_TUTORIA
            textos = [plantilla.format(marca=f"{clave} {i}") for i in range(2)]
            estado = EstadoDocumento.RETIRADO if clave == "retirado" else EstadoDocumento.ACTIVO
            await _documento(unidad, colecciones[clave], titulo, textos, estado)
        configuracion, _ = await unidad.configuracion.vigente()
        version = await unidad.versiones.agregar(
            contextos["CASO-A"],
            VersionBorrador(
                hito="avance_1", ruta_archivo="/privado/x", huella_sha256="a" * 64, tamano_bytes=1
            ),
        )
        solicitud = await unidad.solicitudes.agregar(
            contextos["CASO-A"],
            Solicitud(
                version_id=version.id,
                tipo=TipoSolicitud.BUSQUEDA_EVIDENCIA,
                alcance_tipo=TipoAlcance.CONSULTA,
                alcance_ref="consulta ficticia",
                configuracion_id=configuracion.id,
            ),
        )
        await unidad.confirmar()
    simulado = ProveedorSimulado(
        respuestas={
            "JuicioSuficiencia": lambda _: {
                "suficiente": True,
                "motivo": "F1 y F2 tratan la consulta.",
            }
        }
    )
    return Escenario(
        entorno,
        contextos["CASO-A"],
        contextos["CASO-B"],
        origen,
        solicitud.id,
        ReordenadorFicticio(),
        simulado,
    )


async def _origenes(escenario: Escenario, evidencia: Evidencia) -> set[str]:
    filas = consultar(
        escenario.entorno.url_bd,
        "SELECT titulo FROM documento WHERE id = ANY(%s)",
        [f.documento_id for f in evidencia.recuperacion.fragmentos],
    )
    return {escenario.titulos[str(f[0])] for f in filas}


async def test_el_caso_a_solo_recupera_de_su_tema_y_su_coleccion_personal(
    escenario: Escenario,
) -> None:
    evidencia = await escenario.preparar()
    assert evidencia.recuperacion.colecciones == 2  # científica del tema y personal del caso
    assert await _origenes(escenario, evidencia) == {"cientifica_A", "personal_A", "otro_asunto"}
    # 4 documentos permitidos de 2 fragmentos de 300 tokens: 8, justo el presupuesto de 2 400.
    fragmentos = evidencia.recuperacion.fragmentos
    assert [f.identificador for f in fragmentos] == [f"F{i}" for i in range(1, 9)]
    # El reordenador deja al final lo que es de otro asunto, aunque sea del mismo tema.
    assert all("otro_asunto" in f.texto for f in fragmentos[6:])
    assert all("otro_asunto" not in f.texto for f in fragmentos[:6])
    puntajes = [f.candidato.puntaje_reranking for f in evidencia.recuperacion.fragmentos]
    assert puntajes == sorted(puntajes, reverse=True)
    # Nunca la colección personal de B, otro tema, las guías ni un documento retirado.
    textos = " ".join(f.texto for f in evidencia.recuperacion.fragmentos)
    for ajeno in ("personal_B", "cientifica_B", "guias", "retirado"):
        assert ajeno not in textos


async def test_el_tipo_decide_las_colecciones(escenario: Escenario) -> None:
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        recuperador = Recuperador(EmbeddingsFicticios(), escenario.reordenador)
        guias = await recuperador.recuperar(
            unidad, escenario.a, TipoSolicitud.REVISION_ESTRUCTURA, CONSULTA, parametros_iniciales()
        )
        assert {f.texto.split()[-2] for f in guias.fragmentos} == {"guias"}
        sin_colecciones = await recuperador.recuperar(
            unidad,
            escenario.a,
            TipoSolicitud.VERIFICACION_REFERENCIAS,
            CONSULTA,
            parametros_iniciales(),
        )
        assert (sin_colecciones.colecciones, sin_colecciones.fragmentos) == (0, [])


async def test_respeta_candidatos_numero_final_y_presupuesto(escenario: Escenario) -> None:
    parametros = parametros_iniciales().model_copy(
        update={"candidatos_reranking": 8, "n_reranking": 8, "presupuesto_tokens_contexto": 1000}
    )
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        recuperacion = await Recuperador(EmbeddingsFicticios(), escenario.reordenador).recuperar(
            UnidadDeTrabajo(sesion),
            escenario.a,
            TipoSolicitud.BUSQUEDA_EVIDENCIA,
            CONSULTA,
            parametros,
        )
    assert escenario.reordenador.llamadas[-1] <= 8
    assert len(recuperacion.fragmentos) == 3  # 3 de 300 tokens caben en 1 000


async def test_se_guardan_los_fragmentos_con_sus_puntajes_y_los_tiempos(
    escenario: Escenario,
) -> None:
    evidencia = await escenario.preparar()
    assert evidencia.suficiente
    url = escenario.entorno.url_bd
    filas = consultar(
        url,
        "SELECT identificador_visible, posicion, puntaje_denso, puntaje_lexico,"
        " puntaje_fusionado, puntaje_reranking, caso_id FROM fragmento_recuperado"
        " WHERE solicitud_id = %s ORDER BY posicion",
        escenario.solicitud_a,
    )
    assert [f[0] for f in filas] == [f"F{i}" for i in range(1, 9)]
    assert all(f[2] is not None and f[4] and f[5] is not None for f in filas)
    assert any(f[3] is not None for f in filas)  # la búsqueda léxica también aportó
    assert {f[6] for f in filas} == {escenario.a.caso_id}
    etapas = consultar(
        url,
        "SELECT etapa FROM evento_tecnico WHERE solicitud_id = %s ORDER BY etapa",
        escenario.solicitud_a,
    )
    assert [e[0] for e in etapas] == ["recuperacion", "reranking"]
    assert consultar(url, "SELECT count(*) FROM resultado") == [(0,)]  # sin abstención
    # El otro caso no puede preparar evidencia para la solicitud de A.
    with pytest.raises(SolicitudInexistente):
        await escenario.preparar(contexto=escenario.b)


async def test_cp05_sin_evidencia_no_se_genera_y_la_abstencion_queda_registrada(
    escenario: Escenario,
) -> None:
    generaciones: list[Any] = []

    async def generar(evidencia: Evidencia) -> str:
        generaciones.append(evidencia)
        return "propuesta"

    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        resultado = await escenario.servicio().atender(
            UnidadDeTrabajo(sesion),
            escenario.a,
            escenario.solicitud_a,
            "Efectos de la política monetaria en la inflación de economías emergentes",
            generar,
        )
    assert generaciones == []  # RNF-04: cero generaciones
    assert isinstance(resultado, Evidencia) and not resultado.suficiente
    assert resultado.decision.paso.value == "umbral" and escenario.simulado.llamadas == 0
    filas = consultar(
        escenario.entorno.url_bd,
        "SELECT abstencion, etiqueta, salida, intento, caso_id FROM resultado"
        " WHERE solicitud_id = %s",
        escenario.solicitud_a,
    )
    ((abstencion, etiqueta, salida, intento, caso_id),) = filas
    assert (abstencion, etiqueta, intento, caso_id) == (
        True,
        "sin_evidencia_suficiente",
        1,
        escenario.a.caso_id,
    )
    assert isinstance(salida, dict) and salida["aviso"] == "Sin evidencia suficiente"
    assert salida["paso"] == "umbral"


async def test_con_evidencia_y_juicio_favorable_si_se_genera(escenario: Escenario) -> None:
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        resultado = await escenario.servicio().atender(
            UnidadDeTrabajo(sesion), escenario.a, escenario.solicitud_a, CONSULTA, _propuesta
        )
    assert resultado == "propuesta con 8 fragmentos"


async def test_el_juicio_del_modelo_puede_decidir_abstencion(escenario: Escenario) -> None:
    escenario.simulado.respuestas = {
        "JuicioSuficiencia": lambda _: {
            "suficiente": False,
            "motivo": "Los fragmentos son generales.",
        }
    }
    evidencia = await escenario.preparar()
    assert (evidencia.suficiente, evidencia.decision.paso.value) == (False, "modelo")
    ((salida,),) = consultar(escenario.entorno.url_bd, "SELECT salida FROM resultado")
    assert isinstance(salida, dict) and salida["paso"] == "modelo"
    assert salida["motivo"] == "Los fragmentos son generales."


async def _propuesta(evidencia: Evidencia) -> str:
    return f"propuesta con {len(evidencia.recuperacion.fragmentos)} fragmentos"


async def test_un_documento_incompleto_solo_entra_si_esta_confirmado(escenario: Escenario) -> None:
    async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        caso = consultar(
            escenario.entorno.url_bd,
            "SELECT coleccion_cientifica_id FROM caso WHERE id = %s",
            escenario.a.caso_id,
        )[0][0]
        assert isinstance(caso, uuid.UUID)
        await _documento(
            unidad,
            caso,
            "Tema A, incompleto",
            [SOBRE_TUTORIA.format(marca="incompleto sin confirmar") + " tutoría tutoría"],
            EstadoDocumento.INCOMPLETO,
        )
        await unidad.confirmar()
    evidencia = await escenario.preparar()
    assert all("incompleto" not in f.texto for f in evidencia.recuperacion.fragmentos)
