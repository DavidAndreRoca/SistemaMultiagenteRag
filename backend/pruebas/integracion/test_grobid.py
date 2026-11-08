"""T08 y T09: GROBID operativo y el cliente de la aplicación (marca ``servicios_compartidos``).

Se ejecuta solo si está definida ``URL_GROBID_PRUEBAS`` (por ejemplo,
``http://127.0.0.1:8070``).
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from app.corpus.esquemas import Autor
from app.corpus.grobid import ClienteGrobid

pytestmark = pytest.mark.servicios_compartidos

URL = os.environ.get("URL_GROBID_PRUEBAS", "")

TITULO = "Ansiedad ante los examenes y rendimiento academico en estudiantes universitarios"
LINEAS = [
    (16, TITULO),
    (11, "Maria Quispe Torres y Jose Ramos Huaman"),
    (10, "Universidad Ficticia del Sur, Ica, Peru"),
    (11, "Resumen"),
    (10, "Este estudio ficticio analiza la relacion entre la ansiedad y el rendimiento."),
    (11, "1. Introduccion"),
    (10, "La ansiedad ante los examenes es frecuente en la educacion superior."),
]


def pdf_ficticio() -> bytes:
    """PDF mínimo de una página con texto (fuente Helvetica), sin bibliotecas externas."""
    contenido = ["BT"]
    y = 760
    for tamano, linea in LINEAS:
        contenido.append(f"/F1 {tamano} Tf 1 0 0 1 60 {y} Tm ({linea}) Tj")
        y -= 28
    contenido.append("ET")
    flujo = "\n".join(contenido).encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(flujo)).encode() + b" >>\nstream\n" + flujo + b"\nendstream",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    posiciones = []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f"{numero} 0 obj\n".encode() + objeto + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    salida += b"".join(f"{p:010d} 00000 n \n".encode() for p in posiciones)
    salida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n"
    ).encode()
    return bytes(salida)


@pytest.fixture
def url() -> str:
    if not URL:
        pytest.skip("URL_GROBID_PRUEBAS no está definida")
    return URL


def test_grobid_esta_vivo(url: str) -> None:
    assert httpx.get(f"{url}/api/isalive", timeout=10).text.strip() == "true"
    assert httpx.get(f"{url}/api/version", timeout=10).json()["version"] == "0.9.1"


def test_grobid_extrae_la_cabecera_de_un_pdf(url: str) -> None:
    respuesta = httpx.post(
        f"{url}/api/processHeaderDocument",
        files={"input": ("ficticio.pdf", pdf_ficticio(), "application/pdf")},
        headers={"Accept": "application/xml"},
        timeout=600,  # la primera solicitud carga los modelos de GROBID
    )
    assert respuesta.status_code == 200, respuesta.status_code
    tei = respuesta.text
    assert "<TEI" in tei
    assert "Ansiedad ante los examenes" in tei
    assert "Quispe" in tei


def test_el_cliente_de_la_aplicacion_lee_la_cabecera_del_articulo_de_muestra(url: str) -> None:
    """T09: misma respuesta que la grabada en pruebas/contrato/grobid."""
    pdf = Path(__file__).resolve().parents[1] / "datos" / "pdf" / "articulo_es.pdf"
    cliente = ClienteGrobid(url, tiempo_maximo_s=600)
    try:
        metadatos = cliente.cabecera(pdf)
    finally:
        cliente.cerrar()
    assert metadatos.titulo is not None and metadatos.titulo.startswith("Tutoría entre pares")
    assert metadatos.autores[0] == Autor(nombres="Lucía", apellidos="Mendoza Vargas")
    assert (metadatos.doi, metadatos.idioma) == ("10.5555/rfes.2026.0042", "es")
