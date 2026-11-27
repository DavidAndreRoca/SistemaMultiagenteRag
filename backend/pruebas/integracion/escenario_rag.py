"""Escenario de recuperación compartido por T16 y T18 (fixture ``escenario``).

Casos A y B en TEMA-A, cada uno con su colección personal, TEMA-B y guías, con
fragmentos ficticios sobre tutoría; un documento retirado y uno de otro asunto en TEMA-A.
Embeddings de bolsa de palabras, reordenador por coincidencia de palabras y juicio de
suficiencia con el proveedor simulado. ``conftest.py`` lo registra.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

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
from app.rag.servicio import Evidencia, ServicioEvidencia
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.dobles_corpus import EmbeddingsFicticios
from pruebas.dobles_rag import ReordenadorFicticio
from pruebas.integracion.conftest import Entorno

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
    # Código de cuenta y contraseña inicial de cada caso, para entrar por la API (T19).
    credenciales: dict[str, tuple[str, str]] = field(default_factory=dict)

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


async def sembrar_documento(
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
        # T30: con autor y año, la comprobación 4 confirma la fuente por metadatos.
        autores=[{"nombres": "Ana", "apellidos": "Ficticia"}],
        anio=2024,
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
        credenciales = {}
        for creado in (caso_a, caso_b):
            cuenta = await unidad.autenticacion.cuenta_por_codigo(creado.credenciales[0].codigo)
            assert cuenta is not None
            contextos[creado.caso.codigo] = ContextoAcceso(cuenta.id, Rol.CASO, creado.caso.id)
            credenciales[creado.caso.codigo] = (
                creado.credenciales[0].codigo,
                creado.credenciales[0].contrasena_inicial,
            )

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
            await sembrar_documento(unidad, colecciones[clave], titulo, textos, estado)
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
        credenciales,
    )
