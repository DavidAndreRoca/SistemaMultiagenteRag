"""Normalización de DOI y de texto para comparar metadatos (T09 y T14)."""

from __future__ import annotations

import re
import unicodedata

PATRON_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
PREFIJOS_DOI = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/")
_NO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def normalizar_doi(valor: str | None) -> str | None:
    """DOI en minúsculas, sin prefijo de URL ni ``doi:``; ``None`` si no tiene forma de DOI."""
    if not valor:
        return None
    doi = valor.strip().lower()
    for prefijo in PREFIJOS_DOI:
        doi = doi.removeprefix(prefijo)
    doi = doi.removeprefix("doi:").strip().rstrip(".")
    return doi if PATRON_DOI.fullmatch(doi) else None


def normalizar(texto: str | None) -> str:
    """Minúsculas, sin tildes ni puntuación y con espacios simples."""
    if not texto:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return _NO_ALFANUMERICO.sub(" ", sin_tildes.lower()).strip()
