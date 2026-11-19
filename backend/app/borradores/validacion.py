"""Validación del borrador .docx antes de crear una versión (RF-01, RN-16, CP-02).

Orden y motivos: decisión T11-01, apartado 2. Nada del archivo se ejecuta: se examinan
la firma, el índice del ZIP, los tipos de contenido y los CRC, y se abre con python-docx,
que analiza el XML sin expandir entidades. Un DTD se rechaza antes de analizar nada. El
tamaño del archivo (15 MB) se controla al recibirlo, antes de llegar aquí.
"""

from __future__ import annotations

import zipfile
import zlib
from enum import StrEnum
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.comun.errores import ErrorAplicacion

TIPO_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# Lo que declaran los navegadores para un .docx: su tipo, uno genérico o nada.
TIPOS_DECLARADOS_ADMITIDOS = frozenset({TIPO_DOCX, "application/octet-stream", ""})
TIPO_PRINCIPAL_WORD = f"{TIPO_DOCX}.main+xml"
TIPO_PRINCIPAL_MACROS = "application/vnd.ms-word.document.macroEnabled.main+xml"
FIRMA_ZIP = b"PK\x03\x04"
FIRMA_OLE = bytes.fromhex("D0CF11E0A1B11AE1")
FLUJO_CIFRADO = "EncryptionInfo".encode("utf-16-le")  # así cifra Word un .docx

# Límites de seguridad del contenido comprimido (T11-01, apartado 2, paso 5).
MAX_DESCOMPRIMIDO_BYTES = 150 * 1024 * 1024
MAX_PROPORCION = 100
MIN_BYTES_PARA_PROPORCION = 1024 * 1024
MAX_PARTES = 2000
BYTES_CABECERA_XML = 4096  # un DTD solo puede ir antes del elemento raíz

ERRORES_DE_LECTURA = (zipfile.BadZipFile, zlib.error, EOFError, OSError, KeyError, ValueError)
_CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"


class MotivoRechazo(StrEnum):
    FORMATO_NO_ADMITIDO = "formato_no_admitido"
    DOCX_CON_MACROS = "docx_con_macros"
    DOCX_CIFRADO = "docx_cifrado"
    DOCX_DANADO = "docx_danado"
    CONTENIDO_ANOMALO = "contenido_anomalo"


MENSAJES = {
    MotivoRechazo.FORMATO_NO_ADMITIDO: "El archivo no es un documento de Word (.docx). Si es"
    " un .doc antiguo o un PDF, ábralo en Word y guárdelo como .docx.",
    MotivoRechazo.DOCX_CON_MACROS: "El archivo contiene macros o controles ActiveX. Guárdelo"
    " en Word como documento .docx sin macros y vuelva a cargarlo.",
    MotivoRechazo.DOCX_CIFRADO: "El archivo está protegido con contraseña de apertura. Quite"
    " la contraseña en Word y vuelva a cargarlo.",
    MotivoRechazo.DOCX_DANADO: "El archivo está dañado o incompleto y no se puede leer."
    " Vuelva a guardarlo en Word y cárguelo de nuevo.",
    MotivoRechazo.CONTENIDO_ANOMALO: "El archivo tiene una estructura interna anómala y no se"
    " puede procesar con seguridad. Vuelva a guardarlo en Word y cárguelo de nuevo.",
}


class BorradorRechazado(ErrorAplicacion):
    def __init__(self, motivo: MotivoRechazo) -> None:
        super().__init__(
            motivo.value, MENSAJES[motivo], estado_http=422, detalle={"motivo": motivo.value}
        )
        self.motivo = motivo


def _rechazar(motivo: MotivoRechazo) -> BorradorRechazado:
    return BorradorRechazado(motivo)


def validar_docx(ruta: Path, nombre: str | None, tipo_declarado: str | None) -> None:
    """Valida el archivo recibido; lanza ``BorradorRechazado`` con el motivo si no es apto."""
    # El nombre solo aporta la extensión; puede traer una ruta de Windows.
    extension = PureWindowsPath(nombre or "").suffix.lower()
    if extension == ".docm":
        raise _rechazar(MotivoRechazo.DOCX_CON_MACROS)
    if extension != ".docx":
        raise _rechazar(MotivoRechazo.FORMATO_NO_ADMITIDO)
    if (tipo_declarado or "").split(";")[0].strip().lower() not in TIPOS_DECLARADOS_ADMITIDOS:
        raise _rechazar(MotivoRechazo.FORMATO_NO_ADMITIDO)

    with ruta.open("rb") as archivo:
        firma = archivo.read(len(FIRMA_OLE))
    if firma.startswith(FIRMA_OLE):
        cifrado = FLUJO_CIFRADO in ruta.read_bytes()  # acotado: ya pasó el límite de tamaño
        raise _rechazar(
            MotivoRechazo.DOCX_CIFRADO if cifrado else MotivoRechazo.FORMATO_NO_ADMITIDO
        )
    if not firma.startswith(FIRMA_ZIP):
        raise _rechazar(MotivoRechazo.FORMATO_NO_ADMITIDO)

    try:
        with zipfile.ZipFile(ruta) as paquete:
            _validar_paquete(paquete)
        Document(str(ruta))
    except BorradorRechazado:
        raise
    # SyntaxError cubre los errores de XML de lxml (python-docx) y de ElementTree.
    except (*ERRORES_DE_LECTURA, PackageNotFoundError, SyntaxError):
        raise _rechazar(MotivoRechazo.DOCX_DANADO) from None


def _validar_paquete(paquete: zipfile.ZipFile) -> None:
    partes = paquete.infolist()
    if len(partes) > MAX_PARTES:
        raise _rechazar(MotivoRechazo.CONTENIDO_ANOMALO)
    if sum(p.file_size for p in partes) > MAX_DESCOMPRIMIDO_BYTES:
        raise _rechazar(MotivoRechazo.CONTENIDO_ANOMALO)
    for parte in partes:
        if parte.file_size > MIN_BYTES_PARA_PROPORCION and parte.file_size > MAX_PROPORCION * max(
            parte.compress_size, 1
        ):
            raise _rechazar(MotivoRechazo.CONTENIDO_ANOMALO)

    nombres = {p.filename for p in partes}
    _validar_tipos(paquete, nombres)
    minusculas = [n.lower() for n in nombres]
    if any(n.endswith("vbaproject.bin") or "/activex/" in f"/{n}" for n in minusculas):
        raise _rechazar(MotivoRechazo.DOCX_CON_MACROS)

    if paquete.testzip() is not None:  # CRC de cada parte
        raise _rechazar(MotivoRechazo.DOCX_DANADO)
    for nombre in nombres:
        if nombre.lower().endswith((".xml", ".rels")):
            with paquete.open(nombre) as parte_xml:
                if b"<!DOCTYPE" in parte_xml.read(BYTES_CABECERA_XML).upper():
                    raise _rechazar(MotivoRechazo.CONTENIDO_ANOMALO)


def _validar_tipos(paquete: zipfile.ZipFile, nombres: set[str]) -> None:
    """Tipo MIME real: la parte principal declarada en ``[Content_Types].xml``."""
    if "[Content_Types].xml" not in nombres:
        raise _rechazar(MotivoRechazo.FORMATO_NO_ADMITIDO)
    with paquete.open("[Content_Types].xml") as parte:
        crudo = parte.read(MIN_BYTES_PARA_PROPORCION)
    if b"<!DOCTYPE" in crudo[:BYTES_CABECERA_XML].upper():
        raise _rechazar(MotivoRechazo.CONTENIDO_ANOMALO)
    # Sin DTD (comprobado arriba), ElementTree no tiene entidades que expandir.
    tipos = ElementTree.fromstring(crudo)
    principales = {
        (o.get("PartName") or "").lstrip("/"): o.get("ContentType")
        for o in tipos.iter(f"{_CT}Override")
    }
    if TIPO_PRINCIPAL_MACROS in principales.values():
        raise _rechazar(MotivoRechazo.DOCX_CON_MACROS)
    documento = [nombre for nombre, tipo in principales.items() if tipo == TIPO_PRINCIPAL_WORD]
    if len(documento) != 1 or documento[0] not in nombres:
        raise _rechazar(MotivoRechazo.FORMATO_NO_ADMITIDO)
