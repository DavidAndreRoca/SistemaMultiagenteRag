"""Aporte de fuentes con la base real (T32; CP-14 a CP-17, RN-18, aislamiento).

Reutiliza el escenario de evidencia de T19 (fixture ``evidencias``): el caso A pide una
consulta sobre política monetaria, que el corpus de tutoría no cubre, y el sistema se
abstiene. Las obras ficticias y los servicios están en ``pruebas/dobles_aportes.py``.
"""

# ruff: noqa: F811

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.bd.enumeraciones import TipoSolicitud
from app.llm.cadena import CadenaModelos, Eslabon, Precio
from app.llm.limitador import LimitadorProveedor, Limites
from app.llm.modelos import Proveedor
from app.llm.proveedores import ProveedorSimulado
from app.rag.recuperacion import Recuperador
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo
from pruebas.dobles_aportes import (
    OBRA_MONETARIA,
    OBRA_SIN_DOI,
    BibliografiaFicticia,
    bibliografia_ficticia,
    servicio_ficticio,
)
from pruebas.dobles_corpus import CanalFicticio, EmbeddingsFicticios, contenido
from pruebas.integracion.conftest import consultar, esperar_orquestador
from pruebas.integracion.test_evidencia import Evidencias, _umbral, evidencias  # noqa: F401

pytestmark = pytest.mark.integracion

CONSULTA_SIN_COBERTURA = "Efectos de la política monetaria en la inflación de economías emergentes"


def _coherencia() -> CadenaModelos:
    async def sin_espera(_: float) -> None:
        return None

    simulado = ProveedorSimulado(
        respuestas={
            "JuicioCoherencia": lambda _: {
                "coherencia": "coherente",
                "explicacion": "La fuente trata la inflación y la política monetaria.",
            }
        }
    )
    return CadenaModelos(
        [Eslabon(simulado, LimitadorProveedor(Proveedor.SIMULADO, Limites()), Precio(), 0)],
        dormir=sin_espera,
    )


@dataclass
class Aportes:
    evidencias: Evidencias
    crossref: BibliografiaFicticia
    openalex: BibliografiaFicticia
    canal: CanalFicticio
    abstencion: str

    @property
    def url(self) -> str:
        return self.evidencias.escenario.entorno.url_bd

    async def aportar(
        self,
        solicitud_id: str | None = None,
        *,
        titulo: str = OBRA_MONETARIA.titulo or "",
        autores: str = "Ficticia",
        anio: int = 2024,
        doi: str | None = OBRA_MONETARIA.doi,
        pdf: bytes | None = None,
    ) -> httpx.Response:
        datos: dict[str, Any] = {"titulo": titulo, "autores": autores, "anio": str(anio)}
        if doi is not None:
            datos["doi"] = doi
        archivos = {"archivo": ("cualquiera.pdf", pdf, "application/pdf")} if pdf else None
        respuesta = await self.evidencias.cliente.post(
            f"/caso/solicitudes/{solicitud_id or self.abstencion}/aporte",
            data=datos,
            files=archivos,
        )
        await esperar_orquestador(self.evidencias.escenario.entorno)
        return respuesta

    def aportados(self) -> list[tuple[Any, ...]]:
        """Documentos de origen aporte: (título, tipo de colección, caso de la colección)."""
        return consultar(
            self.url,
            "SELECT d.titulo, c.tipo, c.caso_id FROM documento d"
            " JOIN coleccion c ON c.id = d.coleccion_id WHERE d.origen = 'aporte'",
        )


@pytest.fixture
async def aportes(evidencias: Evidencias, tmp_path: Path) -> AsyncIterator[Aportes]:
    _umbral(evidencias.escenario, 0.0)  # que pase la validación y decida la suficiencia
    respuesta = await evidencias.pedir(CONSULTA_SIN_COBERTURA)
    assert (await evidencias.ver(respuesta.json()["id"]))["abstencion"] is True
    crossref, openalex = bibliografia_ficticia()
    servicio, canal = servicio_ficticio(
        crossref, openalex, tmp_path, evidencias.escenario.entorno.reloj, _coherencia()
    )
    evidencias.escenario.entorno.aplicacion.state.servicio_aportes = servicio
    yield Aportes(evidencias, crossref, openalex, canal, respuesta.json()["id"])


async def test_cp14_fuente_con_doi_se_indexa_y_se_recupera_de_nuevo(aportes: Aportes) -> None:
    cientificas_antes = consultar(
        aportes.url,
        "SELECT count(*) FROM documento d JOIN coleccion c ON c.id = d.coleccion_id"
        " WHERE c.tipo <> 'personal'",
    )
    respuesta = await aportes.aportar()
    assert respuesta.status_code == 201, respuesta.text
    aporte = respuesta.json()
    assert (aporte["existencia"], aporte["metodo_existencia"]) == ("confirmada", "doi")
    assert (aporte["coherencia"], aporte["indexacion"]) == ("coherente", "indexada")
    assert aporte["texto_indexado"] == "resumen" and aporte["explicacion_coherencia"]
    assert "Ficticia" in aporte["cita_propuesta"] and "2024" in aporte["cita_propuesta"]
    # Solo en la colección personal del caso A; nada en las compartidas.
    caso_a = aportes.evidencias.escenario.a.caso_id
    assert aportes.aportados() == [(OBRA_MONETARIA.titulo, "personal", caso_a)]
    assert (
        consultar(
            aportes.url,
            "SELECT count(*) FROM documento d JOIN coleccion c ON c.id = d.coleccion_id"
            " WHERE c.tipo <> 'personal'",
        )
        == cientificas_antes
    )
    # Nueva búsqueda con la misma consulta, enlazada a la abstención, que ahora recupera y
    # recomienda la fuente aportada (RN-14 no se le aplica).
    nueva = await aportes.evidencias.ver(aporte["nueva_solicitud_id"])
    assert nueva["estado"] == "entregada" and nueva["abstencion"] is False
    ((origen, consulta),) = consultar(
        aportes.url,
        "SELECT solicitud_origen_id, alcance_ref FROM solicitud WHERE id = %s",
        uuid.UUID(aporte["nueva_solicitud_id"]),
    )
    assert str(origen) == aportes.abstencion and consulta == CONSULTA_SIN_COBERTURA
    identificador = aportes.evidencias.identificador_de(
        aporte["nueva_solicitud_id"], OBRA_MONETARIA.titulo or ""
    )
    assert identificador == "F1"
    # RF-21: la cita de la fuente propia muestra el documento y los datos que aportó.
    cita = nueva["respuesta"][0]["citas"][0]
    assert (cita["titulo"], cita["autores"], cita["anio"]) == (
        OBRA_MONETARIA.titulo,
        "Ficticia",
        2024,
    )
    assert cita["aporte"]["doi"] == OBRA_MONETARIA.doi and cita["aporte"]["autores"] == ["Ficticia"]
    ((documento_id,),) = consultar(aportes.url, "SELECT id FROM documento WHERE origen = 'aporte'")
    assert [f["documento_id"] for f in nueva["fuentes"]] == [str(documento_id)]
    # La decisión sobre la abstención quedó como "aportar".
    decision = await aportes.evidencias.cliente.get(
        f"/caso/solicitudes/{aportes.abstencion}/decision"
    )
    assert decision.json()["vigente"]["opcion"] == "aportar"


async def test_cp15_sin_doi_se_confirma_por_metadatos_e_indexa_el_resumen(
    aportes: Aportes,
) -> None:
    respuesta = await aportes.aportar(
        titulo=OBRA_SIN_DOI.titulo or "", autores="Prueba, Luis", anio=2023, doi=None
    )
    assert respuesta.status_code == 201, respuesta.text
    aporte = respuesta.json()
    assert (aporte["existencia"], aporte["metodo_existencia"]) == ("confirmada", "metadatos")
    assert (aporte["indexacion"], aporte["texto_indexado"]) == ("indexada", "resumen")
    # El resumen vino de OpenAlex por el DOI del registro (la búsqueda no lo trae).
    ((texto,),) = consultar(
        aportes.url,
        "SELECT f.texto FROM fragmento f JOIN documento d ON d.id = f.documento_id"
        " WHERE d.origen = 'aporte'",
    )
    assert "tasas de interés altas" in str(texto)


async def test_cp16_existencia_no_confirmada_no_indexa_y_registra_el_intento(
    aportes: Aportes,
) -> None:
    respuesta = await aportes.aportar(doi="10.5555/no-existe")
    assert respuesta.status_code == 201, respuesta.text
    aporte = respuesta.json()
    assert (aporte["existencia"], aporte["indexacion"]) == ("no_localizada", "no_indexada")
    assert aporte["motivo_indexacion"] == "existencia_no_confirmada"
    assert aporte["nueva_solicitud_id"] is None and aporte["cita_propuesta"] is None
    assert aportes.aportados() == []
    assert consultar(
        aportes.url,
        "SELECT existencia, indexacion, documento_id FROM fuente_aportada WHERE solicitud_id = %s",
        uuid.UUID(aportes.abstencion),
    ) == [("no_localizada", "no_indexada", None)]
    # Sin DOI, unos datos que no se localizan tampoco se indexan.
    otra = await aportes.aportar(titulo="Una obra que nadie registró", doi=None)
    assert otra.json()["existencia"] == "no_localizada" and aportes.aportados() == []


async def test_servicio_caido_no_indexa_ni_declara_inexistente(aportes: Aportes) -> None:
    aportes.crossref.caido = aportes.openalex.caido = True
    aporte = (await aportes.aportar()).json()
    assert (aporte["existencia"], aporte["indexacion"]) == ("no_comprobable", "no_indexada")
    assert aporte["motivo_indexacion"] == "servicio_no_disponible"
    assert aportes.aportados() == []


async def test_cp17_una_fuente_ya_indexada_no_se_duplica_y_continua(aportes: Aportes) -> None:
    primera = (await aportes.aportar()).json()
    segunda_respuesta = await aportes.aportar()
    assert segunda_respuesta.status_code == 201, segunda_respuesta.text
    segunda = segunda_respuesta.json()
    assert segunda["indexacion"] == "ya_indexada" and segunda["existencia"] == "confirmada"
    assert segunda["nueva_solicitud_id"] not in (None, primera["nueva_solicitud_id"])
    assert len(aportes.aportados()) == 1
    documentos = consultar(
        aportes.url,
        "SELECT DISTINCT documento_id FROM fuente_aportada WHERE solicitud_id = %s",
        uuid.UUID(aportes.abstencion),
    )
    assert len(documentos) == 1
    listado = await aportes.evidencias.cliente.get(
        f"/caso/solicitudes/{aportes.abstencion}/aportes"
    )
    # Mismo instante en las pruebas (reloj fijo): se compara sin orden.
    assert sorted(a["indexacion"] for a in listado.json()) == ["indexada", "ya_indexada"]


async def test_un_pdf_aportado_se_procesa_con_el_canal(aportes: Aportes) -> None:
    respuesta = await aportes.aportar(pdf=contenido("TUTORIA", "VARIANTE=aporte"))
    aporte = respuesta.json()
    assert aporte["indexacion"] == "indexada" and aporte["texto_indexado"] == "pdf"
    assert aporte["con_pdf"] is True and aportes.canal.procesados == 1
    ((ruta, archivo, fragmentos),) = consultar(
        aportes.url,
        "SELECT d.ruta_archivo, d.archivo_original, count(f.id) FROM documento d"
        " JOIN fragmento f ON f.documento_id = d.id WHERE d.origen = 'aporte'"
        " GROUP BY d.id",
    )
    assert ruta is not None and archivo is None and fragmentos == 3  # sin el nombre original
    # Un PDF sin capa de texto cae al resumen del registro.
    otra_abstencion = await aportes.evidencias.pedir(CONSULTA_SIN_COBERTURA + " recientes")
    escaneado = await aportes.aportar(
        otra_abstencion.json()["id"],
        titulo=OBRA_SIN_DOI.titulo or "",
        autores="Prueba",
        anio=2023,
        doi=None,
        pdf=contenido("ESCANEADO"),
    )
    assert escaneado.json()["texto_indexado"] == "resumen"


async def test_solo_tras_una_abstencion_de_evidencia_y_del_propio_caso(
    aportes: Aportes,
) -> None:
    entregada = await aportes.evidencias.pedir("tutoría entre pares y ansiedad estadística")
    no_admitido = await aportes.aportar(entregada.json()["id"])
    assert no_admitido.status_code == 409
    assert no_admitido.json()["codigo"] == "aporte_no_admitido"
    assert (await aportes.aportar(str(uuid.uuid4()))).status_code == 404
    invalido = await aportes.aportar(autores=",", doi="no es un doi")
    assert invalido.status_code == 422
    assert set(invalido.json()["detalle"]["campos"]) == {"autores", "doi"}
    assert aportes.crossref.consultas == 0  # nada se consultó ni se registró
    assert consultar(aportes.url, "SELECT count(*) FROM fuente_aportada") == [(0,)]


async def test_la_fuente_del_caso_a_no_aparece_para_el_caso_b(aportes: Aportes) -> None:
    await aportes.aportar()
    escenario = aportes.evidencias.escenario

    async def titulos(contexto: ContextoAcceso) -> set[str | None]:
        async with escenario.entorno.aplicacion.state.fabrica_sesiones() as sesion:
            unidad = UnidadDeTrabajo(sesion)
            _, parametros = await unidad.configuracion.vigente()
            recuperacion = await Recuperador(
                EmbeddingsFicticios(), escenario.reordenador
            ).recuperar(
                unidad,
                contexto,
                TipoSolicitud.BUSQUEDA_EVIDENCIA,
                CONSULTA_SIN_COBERTURA,
                parametros,
            )
        return {f.titulo for f in recuperacion.fragmentos}

    assert OBRA_MONETARIA.titulo in await titulos(escenario.a)
    assert OBRA_MONETARIA.titulo not in await titulos(escenario.b)
