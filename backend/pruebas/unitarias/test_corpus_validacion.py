"""T09: validación del PDF antes de procesarlo (RN-16) con los PDF ficticios de muestra."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.corpus.esquemas import MotivoExclusion
from app.corpus.validacion import LimitesPdf, huella, validar_pdf

PDF = Path(__file__).resolve().parents[1] / "datos" / "pdf"
LIMITES = LimitesPdf(tamano_max_mb=25, paginas_max=60)


@pytest.mark.parametrize(
    ("nombre", "paginas"),
    [("articulo_es.pdf", 4), ("articulo_en.pdf", 3), ("documento_corto.pdf", 1)],
)
def test_acepta_pdf_con_capa_de_texto(nombre: str, paginas: int) -> None:
    informe = validar_pdf(PDF / nombre, LIMITES)
    assert informe.valido
    assert (informe.num_paginas, informe.paginas_con_texto) == (paginas, paginas)
    assert informe.huella_archivo == huella((PDF / nombre).read_bytes())


def test_acepta_un_pdf_que_solo_restringe_permisos() -> None:
    assert validar_pdf(PDF / "solo_permisos.pdf", LIMITES).valido


def test_rechaza_un_pdf_con_contrasena_de_apertura() -> None:
    assert validar_pdf(PDF / "cifrado.pdf", LIMITES).motivo is MotivoExclusion.PDF_CIFRADO


def test_un_pdf_escaneado_se_excluye_con_motivo() -> None:
    informe = validar_pdf(PDF / "escaneado.pdf", LIMITES)
    assert informe.motivo is MotivoExclusion.SIN_CAPA_DE_TEXTO
    assert (informe.num_paginas, informe.paginas_con_texto) == (2, 0)


def test_el_tipo_real_manda_y_no_la_extension(tmp_path: Path) -> None:
    falso = tmp_path / "articulo.pdf"
    falso.write_bytes(b"PK\x03\x04 esto es un zip con extension pdf")
    assert validar_pdf(falso, LIMITES).motivo is MotivoExclusion.NO_ES_PDF


def test_un_pdf_danado_es_ilegible(tmp_path: Path) -> None:
    danado = tmp_path / "danado.pdf"
    danado.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nbasura sin xref\n")
    assert validar_pdf(danado, LIMITES).motivo is MotivoExclusion.PDF_ILEGIBLE


def test_tamano_maximo(tmp_path: Path) -> None:
    grande = tmp_path / "grande.pdf"
    grande.write_bytes(b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 1))
    informe = validar_pdf(grande, LimitesPdf(tamano_max_mb=1, paginas_max=60))
    assert informe.motivo is MotivoExclusion.EXCEDE_TAMANO
    assert informe.huella_archivo == huella(grande.read_bytes())


def test_paginas_maximas() -> None:
    informe = validar_pdf(PDF / "articulo_es.pdf", LimitesPdf(tamano_max_mb=25, paginas_max=2))
    assert (informe.motivo, informe.num_paginas) == (MotivoExclusion.EXCEDE_PAGINAS, 4)
