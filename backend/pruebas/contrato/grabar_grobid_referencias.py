"""Graba las respuestas reales de GROBID para el artículo O1 ficticio (T15).

``python -m pruebas.contrato.grabar_grobid_referencias [URL_GROBID]`` (por defecto
http://127.0.0.1:8070). Guarda en ``pruebas/contrato/grobid/``:

* ``referencias_pdf.tei.xml``: ``processReferences`` de ``pruebas/datos/o1/articulo_o1.pdf``;
* ``referencias_docx.tei.xml``: ``processCitationList`` de las entradas de la lista de
  referencias de ``pruebas/datos/o1/articulo_o1.docx`` (detectadas con T12).

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

        parrafos = extraer_parrafos(DATOS / "o1" / "articulo_o1.docx").parrafos
        secciones = detectar_por_estilos(parrafos)
        if secciones is None or secciones.referencias is None:
            raise SystemExit("el .docx ficticio no tiene lista de referencias detectable")
        respuesta = cliente.post(
            "/api/processCitationList",
            data={
                "citations": secciones.referencias.entradas,
                "consolidateCitations": "0",
                "includeRawCitations": "1",
            },
            headers={"Accept": "application/xml"},
        )
        respuesta.raise_for_status()
        (DESTINO / "referencias_docx.tei.xml").write_text(respuesta.text, encoding="utf-8")
        print(f"referencias_docx: HTTP {respuesta.status_code}, {len(respuesta.text)} caracteres")


if __name__ == "__main__":
    principal(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8070")
