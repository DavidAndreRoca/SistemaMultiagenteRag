"""Genera los .docx de muestra de T11 (válidos e inválidos) en ``pruebas/datos/docx/``.

``python -m pruebas.datos.generar_docx_muestra`` (desde ``backend/``, con python-docx).

Todo el contenido es ficticio. Los archivos inválidos reproducen cada motivo de rechazo de
la decisión T11-01, apartado 2. El cifrado es sintético: un contenedor OLE con el nombre
del flujo ``EncryptionInfo``, que es lo que la validación examina (no se descifra nada).
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

CARPETA = Path(__file__).parent / "docx"
TIPO_WORD = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
TIPO_MACROS = "application/vnd.ms-word.document.macroEnabled.main+xml"
TIPO_HOJA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"


def _valido() -> bytes:
    documento = Document()
    documento.add_heading("Ansiedad ante la estadística en estudiantes ficticios", level=0)
    documento.add_heading("Introducción", level=1)
    documento.add_paragraph(
        "La ansiedad ante la estadística afecta el rendimiento de los estudiantes de primer"
        " año. Este borrador ficticio sirve para probar la carga de versiones."
    )
    cita = documento.add_paragraph("Estudios previos lo confirman ")
    # Campo de un gestor bibliográfico: el código no se extrae; su resultado visible, sí.
    cita._p.append(parse_xml(f'<w:r {nsdecls("w")}><w:fldChar w:fldCharType="begin"/></w:r>'))
    cita._p.append(
        parse_xml(
            f'<w:r {nsdecls("w")}><w:instrText xml:space="preserve">'
            " ADDIN ZOTERO_ITEM CSL_CITATION {codigo-ficticio} </w:instrText></w:r>"
        )
    )
    cita._p.append(parse_xml(f'<w:r {nsdecls("w")}><w:fldChar w:fldCharType="separate"/></w:r>'))
    cita._p.append(parse_xml(f"<w:r {nsdecls('w')}><w:t>(Quispe, 2020)</w:t></w:r>"))
    cita._p.append(parse_xml(f'<w:r {nsdecls("w")}><w:fldChar w:fldCharType="end"/></w:r>'))
    cita.add_run(".")
    documento.add_heading("Método", level=1)
    cambio = documento.add_paragraph("Participaron 84 estudiantes")
    # Control de cambios: lo eliminado no se extrae; lo insertado, sí.
    cambio._p.append(
        parse_xml(
            f'<w:del {nsdecls("w")} w:id="1" w:author="Ficticio" w:date="2026-11-19T00:00:00Z">'
            '<w:r><w:delText xml:space="preserve"> de dos sedes</w:delText></w:r></w:del>'
        )
    )
    cambio._p.append(
        parse_xml(
            f'<w:ins {nsdecls("w")} w:id="2" w:author="Ficticio" w:date="2026-11-19T00:00:00Z">'
            '<w:r><w:t xml:space="preserve"> de una universidad ficticia</w:t></w:r></w:ins>'
        )
    )
    cambio.add_run(".")
    # Control de contenido (w:sdt) dentro del párrafo, como el de algunas citas de Word.
    control = documento.add_paragraph("El instrumento fue ")
    control._p.append(
        parse_xml(
            f"<w:sdt {nsdecls('w')}><w:sdtContent><w:r><w:t>validado por expertos</w:t>"
            "</w:r></w:sdtContent></w:sdt>"
        )
    )
    documento.add_paragraph("")  # vacío: no cuenta
    tabla = documento.add_table(rows=2, cols=2)
    for fila, (grupo, media) in enumerate((("Grupo", "Media"), ("Tutoría", "12,4"))):
        tabla.cell(fila, 0).text = grupo
        tabla.cell(fila, 1).text = media
    documento.add_heading("Referencias", level=1)
    documento.add_paragraph(
        "Quispe, R. (2020). Ansiedad ficticia. Revista Imaginaria, 3(2), 10-20."
    )
    salida = io.BytesIO()
    documento.save(salida)
    return salida.getvalue()


def _reescribir(origen: bytes, cambios: dict[str, bytes | None]) -> bytes:
    """Copia el ZIP cambiando, agregando (bytes) o quitando (None) partes."""
    salida = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(origen)) as entrada,
        zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as nuevo,
    ):
        for info in entrada.infolist():
            if info.filename in cambios:
                continue
            nuevo.writestr(info, entrada.read(info.filename))
        for nombre, datos in cambios.items():
            if datos is not None:
                nuevo.writestr(nombre, datos)
    return salida.getvalue()


def _tipos(valido: bytes, tipo_principal: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(valido)) as zip_:
        tipos = zip_.read("[Content_Types].xml")
    return tipos.replace(TIPO_WORD.encode(), tipo_principal.encode())


def _bomba(valido: bytes) -> bytes:
    """Agrega 200 MB de ceros, que comprimidos ocupan unos 200 KB."""
    salida = io.BytesIO(_reescribir(valido, {}))
    with (
        zipfile.ZipFile(salida, "a", zipfile.ZIP_DEFLATED) as zip_,
        zip_.open("word/media/relleno.bin", "w", force_zip64=True) as parte,
    ):
        bloque = bytes(1024 * 1024)
        for _ in range(200):
            parte.write(bloque)
    return salida.getvalue()


def _ole(con_cifrado: bool) -> bytes:
    """Contenedor OLE mínimo: firma y, si corresponde, el nombre ``EncryptionInfo``."""
    cabecera = bytes.fromhex("D0CF11E0A1B11AE1") + bytes(504)
    nombre = "EncryptionInfo" if con_cifrado else "WordDocument"
    return cabecera + nombre.encode("utf-16-le") + bytes(2048)


def _crc_alterado(valido: bytes) -> bytes:
    """Cambia un byte de los datos comprimidos de ``word/document.xml``."""
    datos = bytearray(valido)
    with zipfile.ZipFile(io.BytesIO(valido)) as zip_:
        info = zip_.getinfo("word/document.xml")
    inicio = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
    datos[inicio + info.compress_size // 2] ^= 0xFF
    return bytes(datos)


def generar() -> dict[str, bytes]:
    valido = _valido()
    with zipfile.ZipFile(io.BytesIO(valido)) as zip_:
        documento_xml = zip_.read("word/document.xml")
    con_dtd = documento_xml.replace(
        b"<w:document",
        b'<!DOCTYPE w:document [<!ENTITY a "aaaaaaaaaa">]><w:document',
        1,
    )
    vba = b"VBA ficticio: no es codigo ejecutable"
    return {
        "valido.docx": valido,
        "con_macros.docm": _reescribir(
            valido, {"[Content_Types].xml": _tipos(valido, TIPO_MACROS), "word/vbaProject.bin": vba}
        ),
        "macros_renombrado.docx": _reescribir(
            valido, {"[Content_Types].xml": _tipos(valido, TIPO_MACROS), "word/vbaProject.bin": vba}
        ),
        "vba_oculto.docx": _reescribir(valido, {"word/vbaProject.bin": vba}),
        "activex.docx": _reescribir(valido, {"word/activeX/activeX1.xml": b"<ax/>"}),
        "cifrado.docx": _ole(con_cifrado=True),
        "doc_antiguo.docx": _ole(con_cifrado=False),
        "truncado.docx": valido[: len(valido) // 2],
        "crc_alterado.docx": _crc_alterado(valido),
        "bomba.docx": _bomba(valido),
        "con_dtd.docx": _reescribir(valido, {"word/document.xml": con_dtd}),
        "hoja_renombrada.docx": _reescribir(
            valido, {"[Content_Types].xml": _tipos(valido, TIPO_HOJA)}
        ),
        "sin_documento.docx": _reescribir(valido, {"word/document.xml": None}),
        "pdf_renombrado.docx": b"%PDF-1.4\n% documento ficticio\n%%EOF\n",
    }


def main() -> None:
    CARPETA.mkdir(exist_ok=True)
    for nombre, datos in generar().items():
        (CARPETA / nombre).write_bytes(datos)
        print(f"{nombre}: {len(datos)} bytes")


if __name__ == "__main__":
    main()
