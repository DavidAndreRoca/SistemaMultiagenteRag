"""T10: almacén de PDF con nombre aleatorio y nombres de archivo seguros."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.bd.enumeraciones import MotivoExclusionCorpus
from app.corpus.almacen import AlmacenArchivos
from app.corpus.indexacion import MENSAJE_DUPLICADO, mensaje_de_motivo, nombre_seguro


def test_guarda_con_nombre_aleatorio_y_borra(tmp_path: Path) -> None:
    origen = tmp_path / "Artículo de Pérez.pdf"
    origen.write_bytes(b"%PDF-1.4 ficticio")
    almacen = AlmacenArchivos(tmp_path / "archivos")
    primera, segunda = almacen.guardar(origen), almacen.guardar(origen)
    assert primera != segunda
    assert primera.startswith("corpus/") and primera.endswith(".pdf")
    assert "Pérez" not in primera
    assert almacen.ruta(primera).read_bytes() == b"%PDF-1.4 ficticio"
    almacen.borrar(primera)
    assert not almacen.ruta(primera).exists()
    almacen.borrar(primera)  # borrar lo que no existe no falla


def test_no_sale_del_almacen(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fuera"):
        AlmacenArchivos(tmp_path).ruta("../../etc/passwd")


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("articulo.pdf", "articulo.pdf"),
        ("C:\\Usuarios\\x\\tesis final.pdf", "tesis final.pdf"),
        ("../../secreto.pdf", "secreto.pdf"),
        ("", "documento.pdf"),
        (None, "documento.pdf"),
        ("a" * 300 + ".pdf", "a" * 255),
    ],
)
def test_nombre_seguro(nombre: str | None, esperado: str) -> None:
    assert nombre_seguro(nombre) == esperado


def test_hay_mensaje_para_cada_motivo_de_exclusion() -> None:
    for motivo in MotivoExclusionCorpus:
        assert mensaje_de_motivo(motivo)
    assert mensaje_de_motivo(MotivoExclusionCorpus.DUPLICADO) == MENSAJE_DUPLICADO
