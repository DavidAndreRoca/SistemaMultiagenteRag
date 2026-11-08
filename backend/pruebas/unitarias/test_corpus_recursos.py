"""T09: recursos del canal fijados por revisión y huella; descarga verificada sin red real."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import httpx
import pytest

from app.corpus import recursos as r


def contenido_falso(archivo: r.ArchivoFijado) -> bytes:
    return f"contenido ficticio de {archivo.ruta}".encode()


def catalogo_falso() -> tuple[r.RecursoFijado, ...]:
    """Catálogo con las rutas reales pero tamaños y huellas de contenido ficticio."""
    falsos = []
    for recurso in r.RECURSOS:
        archivos = tuple(
            r.ArchivoFijado(
                a.ruta,
                len(contenido_falso(a)),
                hashlib.sha256(contenido_falso(a)).hexdigest(),
            )
            for a in recurso.archivos
        )
        falsos.append(
            r.RecursoFijado(recurso.repositorio, recurso.revision, recurso.licencia, archivos)
        )
    return tuple(falsos)


@pytest.fixture
def catalogo(monkeypatch: pytest.MonkeyPatch) -> tuple[r.RecursoFijado, ...]:
    falso = catalogo_falso()
    monkeypatch.setattr(r, "RECURSOS", falso)
    return falso


def test_el_catalogo_fija_revisiones_completas_y_huellas() -> None:
    for recurso in r.RECURSOS:
        assert len(recurso.revision) == 40 and int(recurso.revision, 16) >= 0
        for archivo in recurso.archivos:
            assert len(archivo.sha256) == 64 and archivo.tamano > 0
    assert r.TOKENIZADOR_BGE_M3.revision == "5617a9f61b028005a4858fdac845db406aefb181"


def test_el_tokenizador_es_el_mismo_que_el_del_servicio_de_modelos() -> None:
    catalogo = Path(__file__).resolve().parents[3] / "servicio_modelos" / "servicio" / "catalogo.py"
    if not catalogo.exists():
        pytest.skip("servicio_modelos no está en este árbol")
    texto = catalogo.read_text(encoding="utf-8")
    (tokenizador,) = r.TOKENIZADOR_BGE_M3.archivos
    assert r.TOKENIZADOR_BGE_M3.revision in texto and tokenizador.sha256 in texto


def test_descarga_verifica_y_no_repite(
    tmp_path: Path, catalogo: tuple[r.RecursoFijado, ...]
) -> None:
    pedidas: list[str] = []
    por_url = {rec.url(a): contenido_falso(a) for rec in catalogo for a in rec.archivos}

    def responder(solicitud: httpx.Request) -> httpx.Response:
        pedidas.append(str(solicitud.url))
        return httpx.Response(200, content=por_url[str(solicitud.url)])

    http = httpx.Client(transport=httpx.MockTransport(responder))
    descargados = r.descargar(tmp_path, cliente=http)
    assert len(descargados) == len(por_url) == len(pedidas)
    assert all("/resolve/" in u and any(rec.revision in u for rec in catalogo) for u in pedidas)
    assert r.problemas(tmp_path) == []
    r.exigir(tmp_path)
    assert (tmp_path / "docling-project--docling-layout-heron" / "model.safetensors").is_file()
    assert r.descargar(tmp_path, cliente=http) == []  # ya estaban: no se piden otra vez
    assert len(pedidas) == len(por_url)


def test_una_huella_distinta_no_se_acepta(
    tmp_path: Path, catalogo: tuple[r.RecursoFijado, ...]
) -> None:
    http = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x")))
    with pytest.raises(r.ErrorRecursos, match="huella"):
        r.descargar(tmp_path, cliente=http)
    assert not list(tmp_path.rglob("*.parcial"))


def test_detecta_faltantes_y_archivos_alterados(
    tmp_path: Path, catalogo: tuple[r.RecursoFijado, ...]
) -> None:
    assert len(r.problemas(tmp_path)) == sum(len(rec.archivos) for rec in catalogo)
    with pytest.raises(r.ErrorRecursos, match=re.escape("python -m app.corpus.recursos")):
        r.exigir(tmp_path)
    recurso = catalogo[0]
    destino = recurso.directorio(tmp_path)
    destino.mkdir(parents=True)
    (destino / recurso.archivos[0].ruta).write_bytes(b"alterado")
    assert any("huella distinta" in p for p in r.problemas(tmp_path))


def test_main_sin_carpeta_falla_con_mensaje(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(r.VARIABLE_DIRECTORIO, raising=False)
    assert r.main([]) == 2
    assert r.VARIABLE_DIRECTORIO in capsys.readouterr().err


def test_main_descarga_en_la_carpeta_de_la_variable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    catalogo: tuple[r.RecursoFijado, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    por_url = {rec.url(a): contenido_falso(a) for rec in catalogo for a in rec.archivos}
    real = httpx.Client

    def cliente_falso(*_: object, **__: object) -> httpx.Client:
        return real(
            transport=httpx.MockTransport(
                lambda s: httpx.Response(200, content=por_url[str(s.url)])
            )
        )

    monkeypatch.setattr(r.httpx, "Client", cliente_falso)
    monkeypatch.setenv(r.VARIABLE_DIRECTORIO, str(tmp_path))
    assert r.main([]) == 0
    assert "verificados" in capsys.readouterr().out
