"""T10-02: caché de la extracción, medición por etapa y avance de la ingesta."""

from __future__ import annotations

import gzip
from pathlib import Path

from app.corpus.bloques import Bloque, DocumentoExtraido, TipoBloque
from app.corpus.cache_extraccion import ExtractorEnCache
from app.corpus.indexacion import Resultado, ResultadoIngesta
from app.corpus.ingesta import Avance, _duracion, linea
from app.corpus.medicion import Etapas


class ExtractorContado:
    def __init__(self) -> None:
        self.llamadas = 0

    def extraer(self, ruta: Path) -> DocumentoExtraido:
        self.llamadas += 1
        return DocumentoExtraido(
            num_paginas=2,
            bloques=[
                Bloque(
                    tipo=TipoBloque.PARRAFO,
                    texto=f"Texto ficticio de {ruta.name}",
                    pagina_inicio=1,
                    pagina_fin=2,
                )
            ],
        )


def _pdf(carpeta: Path, nombre: str, datos: bytes = b"%PDF-1.4 ficticio") -> Path:
    ruta = carpeta / nombre
    ruta.write_bytes(datos)
    return ruta


def test_la_cache_extrae_una_sola_vez_por_huella(tmp_path: Path) -> None:
    interno = ExtractorContado()
    cache = ExtractorEnCache(interno, tmp_path / "cache", "docling=1;motor=a")
    primero = cache.extraer(_pdf(tmp_path, "a.pdf"))
    # Otro nombre con los mismos bytes: misma huella, no se vuelve a extraer.
    segundo = cache.extraer(_pdf(tmp_path, "copia.pdf"))
    assert segundo == primero
    assert (interno.llamadas, cache.aciertos, cache.fallos) == (1, 1, 1)
    cache.extraer(_pdf(tmp_path, "b.pdf", b"%PDF-1.4 otro"))
    assert interno.llamadas == 2
    guardados = list((tmp_path / "cache").rglob("*.json.gz"))
    assert len(guardados) == 2
    assert not list((tmp_path / "cache").rglob("*.parcial"))


def test_otra_firma_del_extractor_no_usa_la_entrada_anterior(tmp_path: Path) -> None:
    interno = ExtractorContado()
    ruta = _pdf(tmp_path, "a.pdf")
    ExtractorEnCache(interno, tmp_path / "cache", "docling=1").extraer(ruta)
    otra = ExtractorEnCache(interno, tmp_path / "cache", "docling=2")
    otra.extraer(ruta)
    assert (interno.llamadas, otra.fallos) == (2, 1)
    misma = ExtractorEnCache(interno, tmp_path / "cache", "docling=1")
    misma.extraer(ruta)
    assert (interno.llamadas, misma.aciertos) == (2, 1)


def test_una_entrada_danada_se_ignora_y_se_reemplaza(tmp_path: Path) -> None:
    interno = ExtractorContado()
    cache = ExtractorEnCache(interno, tmp_path / "cache", "firma")
    ruta = _pdf(tmp_path, "a.pdf")
    esperado = cache.extraer(ruta)
    (guardado,) = (tmp_path / "cache").rglob("*.json.gz")
    for danado in (b"no es gzip", gzip.compress(b'{"num_paginas": "x"}')):
        guardado.write_bytes(danado)
        assert cache.extraer(ruta) == esperado
    assert interno.llamadas == 3
    assert cache.extraer(ruta) == esperado and interno.llamadas == 3


def test_etapas_acumula_segundos_por_nombre() -> None:
    etapas = Etapas()
    for _ in range(2):
        with etapas.medir("extraccion"):
            pass
    with etapas.medir("base"):
        pass
    assert set(etapas.segundos) == {"extraccion", "base"}
    assert etapas.total >= 0


def _resultado(tipo: Resultado, tiempos: dict[str, float]) -> ResultadoIngesta:
    return ResultadoIngesta(
        archivo="a.pdf", resultado=tipo, fragmentos=3, tiempos_s=tiempos, memoria_mb={"base": 90}
    )


def test_el_avance_estima_el_restante_con_los_documentos_procesados() -> None:
    avance = Avance(total=4, inicio=0.0)
    assert avance.prefijo(0.0) == "[0/4   0 % | 0 s | estimando]"
    avance.registrar(_resultado(Resultado.INDEXADO, {"extraccion": 50, "base": 1}), 60)
    avance.registrar(_resultado(Resultado.YA_REGISTRADO, {}), 0.1)  # no cuenta en la media
    assert avance.prefijo(61) == "[2/4  50 % | 1 min 01 s | ~2 min 00 s restantes]"
    avance.registrar(None, 1)
    assert avance.conteo == {"indexado": 1, "ya_registrado": 1, "error": 1}
    assert avance.resumen_etapas() == "extraccion 50 s; base 1 s (90 MB)"
    assert Avance(total=0, inicio=0).resumen_etapas() == "sin documentos procesados"
    assert _duracion(3 * 3600 + 125) == "3 h 02 min"


def test_la_linea_muestra_las_etapas_sin_texto_del_documento() -> None:
    texto = linea(_resultado(Resultado.INDEXADO, {"extraccion": 12.34, "base": 0.5}), 13.0)
    assert texto.endswith("| 13.0 s (extraccion 12.3, base 0.5)")
    assert "s (" not in linea(_resultado(Resultado.INDEXADO, {}), 1.0)
