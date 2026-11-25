"""Graba las respuestas reales de GROBID para los documentos ficticios de T15 y T20.

``python -m pruebas.contrato.grabar_grobid_referencias [URL_GROBID]`` (por defecto
http://127.0.0.1:8070). Guarda en ``pruebas/contrato/grobid/``:

* ``referencias_pdf.tei.xml``: ``processReferences`` de ``pruebas/datos/o1/articulo_o1.pdf``;
* ``referencias_docx.tei.xml``: ``processCitationList`` de las entradas de la lista de
  referencias de ``pruebas/datos/o1/articulo_o1.docx`` (detectadas con T12);
* ``referencias_t20_<norma>.tei.xml``: ``processCitationList`` de la lista de
  ``pruebas/datos/docx/referencias_<norma>.docx``, en IEEE y en APA 7 (T20).

Todo el contenido es ficticio.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

from app.borradores.extraccion import extraer_parrafos
from app.borradores.secciones import detectar_por_estilos

DATOS = Path(__file__).parents[1] / "datos"
DESTINO = Path(__file__).parent / "grobid"
NORMAS_T20 = ("ieee", "apa7")


def entradas(ruta: Path) -> list[str]:
    secciones = detectar_por_estilos(extraer_parrafos(ruta).parrafos)
    if secciones is None or secciones.referencias is None:
        raise SystemExit(f"{ruta.name} no tiene lista de referencias detectable")
    return secciones.referencias.entradas


def lista_de_citas(cliente: httpx.Client, ruta: Path, destino: str) -> None:
    respuesta = cliente.post(
        "/api/processCitationList",
        data={
            "citations": entradas(ruta),
            "consolidateCitations": "0",
            "includeRawCitations": "1",
        },
        headers={"Accept": "application/xml"},
    )
    respuesta.raise_for_status()
    (DESTINO / destino).write_text(respuesta.text, encoding="utf-8")
    print(f"{destino}: HTTP {respuesta.status_code}, {len(respuesta.text)} caracteres")


def principal(url: str) -> None:
    with httpx.Client(base_url=url, timeout=300) as cliente:
        with (DATOS / "o1" / "articulo_o1.pdf").open("rb") as pdf:
            respuesta = cliente.post(
                "/api/processReferences",
                files={"input": ("articulo.pdf", pdf, "application/pdf")},
                data={"consolidateCitations": "0", "includeRawCitations": "1"},
                headers={"Accept": "application/xml"},
            )
        respuesta.raise_for_status()
        (DESTINO / "referencias_pdf.tei.xml").write_text(respuesta.text, encoding="utf-8")
        print(f"referencias_pdf: HTTP {respuesta.status_code}, {len(respuesta.text)} caracteres")
        lista_de_citas(cliente, DATOS / "o1" / "articulo_o1.docx", "referencias_docx.tei.xml")
        for norma in NORMAS_T20:
            lista_de_citas(
                cliente,
                DATOS / "docx" / f"referencias_{norma}.docx",
                f"referencias_t20_{norma}.tei.xml",
            )


if __name__ == "__main__":
    principal(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8070")
