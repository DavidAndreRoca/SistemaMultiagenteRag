"""T11: validación del .docx y extracción de párrafos (CP-02; decisión T11-01).

Los archivos de ``pruebas/datos/docx/`` son ficticios y se regeneran con
``python -m pruebas.datos.generar_docx_muestra``.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from app.borradores.extraccion import extraer_parrafos
from app.borradores.validacion import (
    MAX_PARTES,
    TIPO_DOCX,
    BorradorRechazado,
    MotivoRechazo,
    validar_docx,
)

DOCX = Path(__file__).parents[1] / "datos" / "docx"
M = MotivoRechazo


def _rechazo(ruta: Path, nombre: str | None = None, tipo: str | None = TIPO_DOCX) -> MotivoRechazo:
    with pytest.raises(BorradorRechazado) as error:
        validar_docx(ruta, nombre or ruta.name, tipo)
    return error.value.motivo


def test_un_docx_valido_pasa_la_validacion() -> None:
    for tipo in (TIPO_DOCX, "application/octet-stream", None, ""):
        validar_docx(DOCX / "valido.docx", "Mi artículo.DOCX", tipo)


@pytest.mark.parametrize(
    ("archivo", "motivo"),
    [
        ("con_macros.docm", M.DOCX_CON_MACROS),
        ("macros_renombrado.docx", M.DOCX_CON_MACROS),
        ("vba_oculto.docx", M.DOCX_CON_MACROS),
        ("activex.docx", M.DOCX_CON_MACROS),
        ("cifrado.docx", M.DOCX_CIFRADO),
        ("doc_antiguo.docx", M.FORMATO_NO_ADMITIDO),
        ("pdf_renombrado.docx", M.FORMATO_NO_ADMITIDO),
        ("hoja_renombrada.docx", M.FORMATO_NO_ADMITIDO),
        ("sin_documento.docx", M.FORMATO_NO_ADMITIDO),
        ("truncado.docx", M.DOCX_DANADO),
        ("crc_alterado.docx", M.DOCX_DANADO),
        ("bomba.docx", M.CONTENIDO_ANOMALO),
        ("con_dtd.docx", M.CONTENIDO_ANOMALO),
    ],
)
def test_cp02_rechaza_cada_archivo_malicioso_o_invalido(
    archivo: str, motivo: MotivoRechazo
) -> None:
    assert _rechazo(DOCX / archivo) is motivo


def test_rechaza_por_extension_y_por_tipo_declarado(tmp_path: Path) -> None:
    copia = tmp_path / "x"
    shutil.copyfile(DOCX / "valido.docx", copia)
    assert _rechazo(copia, "borrador.docm") is M.DOCX_CON_MACROS
    assert _rechazo(copia, "borrador.pdf") is M.FORMATO_NO_ADMITIDO
    assert _rechazo(copia, "borrador") is M.FORMATO_NO_ADMITIDO
    assert _rechazo(copia, "borrador.docx", "application/pdf") is M.FORMATO_NO_ADMITIDO
    # Un nombre con ruta solo aporta la extensión.
    validar_docx(copia, "C:\\carpeta\\..\\borrador.docx", TIPO_DOCX)


def test_rechaza_demasiadas_partes_o_una_proporcion_anomala(tmp_path: Path) -> None:
    muchas = tmp_path / "muchas.docx"
    shutil.copyfile(DOCX / "valido.docx", muchas)
    with zipfile.ZipFile(muchas, "a") as zip_:
        for n in range(MAX_PARTES):
            zip_.writestr(f"word/media/p{n}.txt", b"x")
    assert _rechazo(muchas) is M.CONTENIDO_ANOMALO

    comprimida = tmp_path / "comprimida.docx"
    shutil.copyfile(DOCX / "valido.docx", comprimida)
    with zipfile.ZipFile(comprimida, "a", zipfile.ZIP_DEFLATED) as zip_:
        zip_.writestr("word/media/ceros.bin", bytes(5 * 1024 * 1024))  # 5 MB a unos 5 KB
    assert _rechazo(comprimida) is M.CONTENIDO_ANOMALO


def test_el_rechazo_tiene_el_formato_unico_de_error() -> None:
    with pytest.raises(BorradorRechazado) as error:
        validar_docx(DOCX / "cifrado.docx", "a.docx", TIPO_DOCX)
    assert error.value.codigo == "docx_cifrado"
    assert error.value.estado_http == 422
    assert "contraseña" in error.value.mensaje
    assert error.value.detalle == {"motivo": "docx_cifrado"}


def test_extrae_los_parrafos_con_identificador_estilo_y_origen() -> None:
    texto = extraer_parrafos(DOCX / "valido.docx")
    parrafos = {p.id: p for p in texto.parrafos}
    assert [p.id for p in texto.parrafos] == [f"p{n}" for n in range(1, len(texto.parrafos) + 1)]
    assert parrafos["p1"].texto == "Ansiedad ante la estadística en estudiantes ficticios"
    assert parrafos["p1"].estilo == "Title"
    assert parrafos["p2"].texto == "Introducción" and parrafos["p2"].estilo == "Heading 1"
    textos = [p.texto for p in texto.parrafos]
    # El resultado visible del campo del gestor bibliográfico, sin su código.
    assert "Estudios previos lo confirman (Quispe, 2020)." in textos
    assert not any("ZOTERO" in t or "ADDIN" in t for t in textos)
    # Control de cambios: entra lo insertado, no lo eliminado.
    assert "Participaron 84 estudiantes de una universidad ficticia." in textos
    assert not any("dos sedes" in t for t in textos)
    assert "El instrumento fue validado por expertos" in textos  # dentro de w:sdt
    assert "" not in textos
    celdas = [p for p in texto.parrafos if p.origen == "tabla"]
    assert [p.texto for p in celdas] == ["Grupo", "Media", "Tutoría", "12,4"]
    assert textos.index("Grupo") < textos.index("Referencias")  # orden de lectura
    assert texto.palabras == sum(len(t.split()) for t in textos)


def test_la_extraccion_es_reproducible() -> None:
    assert extraer_parrafos(DOCX / "valido.docx") == extraer_parrafos(DOCX / "valido.docx")
