"""T07: alta de casos, colecciones, cuentas, desactivación y norma de citación (CP-22)."""

from __future__ import annotations

import httpx
import pytest

from app.bd.semillas import sembrar
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.integracion.conftest import (
    Entorno,
    consultar,
    crear_caso,
    crear_tema,
    entrar_y_cambiar,
    iniciar_sesion,
    primera_credencial,
)

pytestmark = pytest.mark.integracion


async def test_alta_completa_de_un_caso(entorno: Entorno, investigador: httpx.AsyncClient) -> None:
    await crear_tema(investigador, "TEMA-01")
    caso = await crear_caso(investigador, "caso-01", "TEMA-01")
    assert caso["codigo"] == "CASO-01"
    assert caso["norma_citacion"] == "ieee"
    assert caso["estado"] == "habilitado"
    assert caso["tema"] == "TEMA-01"
    credenciales = caso["credenciales"]
    assert isinstance(credenciales, list) and len(credenciales) == 1
    assert credenciales[0]["cuenta"] == "CASO-01-1"
    assert len(credenciales[0]["contrasena_inicial"]) >= 16

    # Colección personal del caso y asociación con la científica del tema.
    filas = consultar(
        entorno.url_bd,
        "SELECT c.codigo, cc.tema, cp.tipo FROM caso c"
        " JOIN coleccion cc ON cc.id = c.coleccion_cientifica_id"
        " JOIN coleccion cp ON cp.caso_id = c.id",
    )
    assert filas == [("CASO-01", "TEMA-01", "personal")]
    # La contraseña inicial no se guarda en claro.
    hashes = consultar(entorno.url_bd, "SELECT hash_contrasena FROM cuenta WHERE rol = 'A1'")
    assert credenciales[0]["contrasena_inicial"] not in str(hashes)

    # El caso entra, cambia la contraseña y ve sus datos.
    cuenta, inicial = primera_credencial(caso)
    async with entorno.cliente() as estudiante:
        await entrar_y_cambiar(estudiante, cuenta, inicial)
        propio = await estudiante.get("/caso")
    assert propio.status_code == 200
    assert propio.json() == {
        "codigo": "CASO-01",
        "tipo_autoria": "individual",
        "tema": "TEMA-01",
        "norma_citacion": "ieee",
    }


async def test_caso_en_pareja_tiene_dos_cuentas(investigador: httpx.AsyncClient) -> None:
    await crear_tema(investigador, "TEMA-01")
    caso = await crear_caso(investigador, "CASO-P", "TEMA-01", autoria="pareja")
    credenciales = caso["credenciales"]
    assert isinstance(credenciales, list)
    assert [c["cuenta"] for c in credenciales] == ["CASO-P-1", "CASO-P-2"]
    assert credenciales[0]["contrasena_inicial"] != credenciales[1]["contrasena_inicial"]


async def test_cp22_codigo_de_caso_repetido(investigador: httpx.AsyncClient) -> None:
    await crear_tema(investigador, "TEMA-01")
    await crear_caso(investigador, "CASO-01", "TEMA-01")
    repetido = await investigador.post(
        "/investigador/casos",
        json={"codigo": "caso-01", "tipo_autoria": "pareja", "tema": "TEMA-01"},
    )
    assert repetido.status_code == 409
    assert repetido.json()["codigo"] == "codigo_repetido"
    assert "CASO-01" in repetido.json()["mensaje"]
    listado = await investigador.get("/investigador/casos")
    assert [c["codigo"] for c in listado.json()] == ["CASO-01"]


async def test_tema_inexistente_y_tema_repetido(investigador: httpx.AsyncClient) -> None:
    sin_tema = await investigador.post(
        "/investigador/casos",
        json={"codigo": "CASO-01", "tipo_autoria": "individual", "tema": "NO-HAY"},
    )
    assert sin_tema.status_code == 422
    assert sin_tema.json()["codigo"] == "tema_inexistente"
    await crear_tema(investigador, "TEMA-01")
    repetido = await investigador.post(
        "/investigador/colecciones/cientificas", json={"tema": "tema-01"}
    )
    assert repetido.status_code == 409
    colecciones = (await investigador.get("/investigador/colecciones")).json()
    assert colecciones == [
        {
            "tipo": "cientifica",
            "tema": "TEMA-01",
            "n_incluidas": 0,
            "n_excluidas": 0,
            "n_pendientes": 0,
        }
    ]


async def test_codigo_con_caracteres_no_permitidos(investigador: httpx.AsyncClient) -> None:
    await crear_tema(investigador, "TEMA-01")
    respuesta = await investigador.post(
        "/investigador/casos",
        json={"codigo": "Caso con espacios", "tipo_autoria": "individual", "tema": "TEMA-01"},
    )
    assert respuesta.status_code == 422


async def test_desactivacion_impide_iniciar_sesion_y_cierra_sesiones(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> None:
    await crear_tema(investigador, "TEMA-01")
    cuenta, inicial = primera_credencial(await crear_caso(investigador, "CASO-01", "TEMA-01"))
    async with entorno.cliente() as estudiante, entorno.cliente() as otro:
        await entrar_y_cambiar(estudiante, cuenta, inicial)
        assert (await estudiante.get("/caso")).status_code == 200
        desactivado = await investigador.post("/investigador/casos/CASO-01/desactivar")
        assert desactivado.json()["estado"] == "desactivado"
        assert (await estudiante.get("/caso")).status_code == 401
        nueva = await iniciar_sesion(otro, cuenta, "contrasena-ficticia-de-pruebas-01")
        assert nueva.status_code == 401
        reactivado = await investigador.post("/investigador/casos/CASO-01/reactivar")
        assert reactivado.json()["estado"] == "habilitado"
        assert (
            await iniciar_sesion(otro, cuenta, "contrasena-ficticia-de-pruebas-01")
        ).status_code == 200


async def test_norma_por_defecto_ieee_y_cambio_registrado(
    entorno: Entorno, investigador: httpx.AsyncClient
) -> None:
    await crear_tema(investigador, "TEMA-01")
    await crear_caso(investigador, "CASO-01", "TEMA-01")
    cambio = await investigador.put("/investigador/casos/CASO-01/norma", json={"norma": "APA7"})
    assert cambio.status_code == 200
    assert cambio.json()["norma_citacion"] == "apa7"
    igual = await investigador.put("/investigador/casos/CASO-01/norma", json={"norma": "APA7"})
    assert igual.status_code == 200  # sin cambio real, no se registra
    detalle = (await investigador.get("/investigador/casos/CASO-01")).json()
    assert [(c["norma_anterior"], c["norma_nueva"]) for c in detalle["cambios_norma"]] == [
        ("ieee", "apa7")
    ]
    assert detalle["cuentas"] == ["CASO-01-1"]
    registro = consultar(
        entorno.url_bd,
        "SELECT cn.norma_anterior, cn.norma_nueva, cu.codigo FROM cambio_norma cn"
        " JOIN cuenta cu ON cu.id = cn.cuenta_id",
    )
    assert registro == [("ieee", "apa7", "INV-01")]


@pytest.mark.parametrize(("escrita", "guardada"), [("Vancouver", "vancouver"), ("apa7", "apa7")])
async def test_lista_cerrada_de_normas_d12(
    investigador: httpx.AsyncClient, escrita: str, guardada: str
) -> None:
    """D-12, cerrada: IEEE (por defecto), APA 7 y Vancouver."""
    await crear_tema(investigador, "TEMA-01")
    await crear_caso(investigador, "CASO-01", "TEMA-01")
    respuesta = await investigador.put("/investigador/casos/CASO-01/norma", json={"norma": escrita})
    assert respuesta.status_code == 200
    assert respuesta.json()["norma_citacion"] == guardada


async def test_norma_fuera_de_la_lista_rechazada(investigador: httpx.AsyncClient) -> None:
    await crear_tema(investigador, "TEMA-01")
    await crear_caso(investigador, "CASO-01", "TEMA-01")
    respuesta = await investigador.put("/investigador/casos/CASO-01/norma", json={"norma": "MLA"})
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "norma_no_permitida"
    assert respuesta.json()["detalle"]["normas_permitidas"] == ["ieee", "apa7", "vancouver"]
    detalle = (await investigador.get("/investigador/casos/CASO-01")).json()
    assert detalle["norma_citacion"] == "ieee"
    assert detalle["cambios_norma"] == []


async def test_caso_inexistente_es_404(investigador: httpx.AsyncClient) -> None:
    for respuesta in (
        await investigador.get("/investigador/casos/NADA"),
        await investigador.post("/investigador/casos/NADA/desactivar"),
        await investigador.put("/investigador/casos/NADA/norma", json={"norma": "ieee"}),
    ):
        assert respuesta.status_code == 404
        assert respuesta.json()["codigo"] == "no_existe"


async def test_semillas_ficticias_son_idempotentes(entorno: Entorno) -> None:
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        primera = await sembrar(UnidadDeTrabajo(sesion))
    async with entorno.aplicacion.state.fabrica_sesiones() as sesion:
        segunda = await sembrar(UnidadDeTrabajo(sesion))
    assert [c for c, _ in primera] == ["INV-DEV", "CASO-DEV-01-1", "CASO-DEV-02-1", "CASO-DEV-02-2"]
    assert segunda == []
    assert consultar(entorno.url_bd, "SELECT count(*) FROM caso") == [(2,)]
