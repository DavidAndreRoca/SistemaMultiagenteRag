"""T05: aislamiento por caso en los repositorios y colecciones permitidas por tipo."""

from __future__ import annotations

import uuid

import pytest

from app.bd.enumeraciones import Rol, TipoAlcance, TipoAutoria, TipoColeccion, TipoSolicitud
from app.bd.modelos import Coleccion, Solicitud, VersionBorrador
from app.casos import servicio
from app.repositorios.contexto import ContextoAcceso, ErrorContexto
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.integracion.conftest import Entorno

pytestmark = pytest.mark.integracion


async def _preparar(entorno: Entorno) -> dict[str, object]:
    """Dos temas, dos casos (A en TEMA-A, B en TEMA-B) y la colección de guías."""
    await entorno.crear_investigador()
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        inv = await unidad.autenticacion.cuenta_por_codigo("INV-01")
        assert inv is not None
        investigador = ContextoAcceso(inv.id, Rol.INVESTIGADOR, None)
        await servicio.crear_coleccion_cientifica(unidad, investigador, "TEMA-A")
        await servicio.crear_coleccion_cientifica(unidad, investigador, "TEMA-B")
        guias = await unidad.colecciones_investigador.agregar(
            investigador, Coleccion(tipo=TipoColeccion.GUIAS)
        )
        await unidad.confirmar()
        caso_a = await servicio.crear_caso(
            unidad, investigador, "CASO-A", TipoAutoria.INDIVIDUAL, "TEMA-A"
        )
        caso_b = await servicio.crear_caso(
            unidad, investigador, "CASO-B", TipoAutoria.INDIVIDUAL, "TEMA-B"
        )
        cuentas = {}
        for creado in (caso_a, caso_b):
            cuenta = await unidad.autenticacion.cuenta_por_codigo(creado.credenciales[0].codigo)
            assert cuenta is not None
            cuentas[creado.caso.codigo] = ContextoAcceso(cuenta.id, Rol.CASO, creado.caso.id)
        return {
            "investigador": investigador,
            "A": cuentas["CASO-A"],
            "B": cuentas["CASO-B"],
            "guias": guias.id,
            "cientifica_A": caso_a.caso.coleccion_cientifica_id,
            "cientifica_B": caso_b.caso.coleccion_cientifica_id,
            "personal_A": caso_a.coleccion_personal.id,
            "personal_B": caso_b.coleccion_personal.id,
        }


def _version(huella: str) -> VersionBorrador:
    return VersionBorrador(
        hito="avance_1", ruta_archivo="/privado/x", huella_sha256=huella, tamano_bytes=1
    )


async def test_un_caso_no_lee_ni_lista_datos_de_otro(entorno: Entorno) -> None:
    datos = await _preparar(entorno)
    a, b = datos["A"], datos["B"]
    assert isinstance(a, ContextoAcceso) and isinstance(b, ContextoAcceso)
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        version_a = await unidad.versiones.agregar(a, _version("a" * 64))
        await unidad.versiones.agregar(b, _version("b" * 64))
        await unidad.confirmar()

        assert await unidad.versiones.obtener(a, version_a.id) is not None
        assert await unidad.versiones.obtener(b, version_a.id) is None  # igual que "no existe"
        assert [v.huella_sha256 for v in await unidad.versiones.listar(a)] == ["a" * 64]
        assert [v.huella_sha256 for v in await unidad.versiones.listar(b)] == ["b" * 64]


async def test_agregar_asigna_siempre_el_caso_del_contexto(entorno: Entorno) -> None:
    datos = await _preparar(entorno)
    a, b = datos["A"], datos["B"]
    assert isinstance(a, ContextoAcceso) and isinstance(b, ContextoAcceso)
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        intruso = _version("c" * 64)
        intruso.caso_id = a.caso_id  # B intenta escribir en A
        guardada = await unidad.versiones.agregar(b, intruso)
        await unidad.confirmar()
        assert guardada.caso_id == b.caso_id
        assert await unidad.versiones.listar(a) == []


async def test_registros_hijos_tambien_quedan_aislados(entorno: Entorno) -> None:
    datos = await _preparar(entorno)
    a, b = datos["A"], datos["B"]
    assert isinstance(a, ContextoAcceso) and isinstance(b, ContextoAcceso)
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        configuracion, _ = await unidad.configuracion.vigente()
        version = await unidad.versiones.agregar(a, _version("d" * 64))
        solicitud = await unidad.solicitudes.agregar(
            a,
            Solicitud(
                version_id=version.id,
                tipo=TipoSolicitud.BUSQUEDA_EVIDENCIA,
                alcance_tipo=TipoAlcance.CONSULTA,
                alcance_ref="pregunta ficticia",
                configuracion_id=configuracion.id,
            ),
        )
        await unidad.confirmar()
        assert await unidad.solicitudes.obtener(b, solicitud.id) is None
        assert len(await unidad.solicitudes.listar(a)) == 1
        assert await unidad.solicitudes.listar(b) == []


async def test_contexto_de_investigador_no_sirve_para_datos_de_caso(entorno: Entorno) -> None:
    datos = await _preparar(entorno)
    investigador, a = datos["investigador"], datos["A"]
    assert isinstance(investigador, ContextoAcceso) and isinstance(a, ContextoAcceso)
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        with pytest.raises(ErrorContexto):
            await unidad.versiones.listar(investigador)
        with pytest.raises(ErrorContexto):
            await unidad.casos_investigador.listar(a)  # y un caso no usa repositorios de A2


@pytest.mark.parametrize(
    ("tipo", "esperadas"),
    [
        (TipoSolicitud.REVISION_ESTRUCTURA, {"guias"}),
        (TipoSolicitud.PLAN_TAREA, {"guias"}),
        (TipoSolicitud.REVISION_METODOLOGICA, {"guias"}),
        (TipoSolicitud.PROPUESTA_REDACCION, {"guias"}),
        (TipoSolicitud.BUSQUEDA_EVIDENCIA, {"cientifica", "personal"}),
        (TipoSolicitud.VERIFICACION_REFERENCIAS, set()),
    ],
)
async def test_colecciones_permitidas_por_tipo(
    entorno: Entorno, tipo: TipoSolicitud, esperadas: set[str]
) -> None:
    datos = await _preparar(entorno)
    a, b = datos["A"], datos["B"]
    assert isinstance(a, ContextoAcceso) and isinstance(b, ContextoAcceso)
    nombres = {
        datos["guias"]: "guias",
        datos["cientifica_A"]: "cientifica",
        datos["personal_A"]: "personal",
    }
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        unidad = UnidadDeTrabajo(sesion)
        permitidas_a = await unidad.colecciones.permitidas(tipo, a)
        permitidas_b = await unidad.colecciones.permitidas(tipo, b)
    assert {nombres[c] for c in permitidas_a} == esperadas
    assert len(permitidas_a) == len(esperadas)
    # Nunca aparecen la científica de otro tema ni la personal de otro caso.
    assert datos["cientifica_B"] not in permitidas_a
    assert datos["personal_B"] not in permitidas_a
    assert datos["personal_A"] not in permitidas_b
    assert datos["cientifica_A"] not in permitidas_b


async def test_contexto_mal_formado_se_rechaza() -> None:
    with pytest.raises(ErrorContexto):
        ContextoAcceso(uuid.uuid4(), Rol.CASO, None)
    with pytest.raises(ErrorContexto):
        ContextoAcceso(uuid.uuid4(), Rol.INVESTIGADOR, uuid.uuid4())
