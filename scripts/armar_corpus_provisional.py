"""Arma el corpus provisional desde las referencias de los artículos base (apoyo a T10).

Script de apoyo, fuera de la aplicación, mientras no exista el importador de T15. Para
cada artículo base de ``datos/articulos-base/<tema>/``:

1. Extrae la lista de referencias con GROBID (``processReferences``, sin consolidar).
2. Resuelve el DOI de cada referencia con Crossref: si GROBID trae un DOI, lo comprueba;
   si no, busca por metadatos (``query.bibliographic``) y acepta el resultado solo si
   coinciden el título (similitud normalizada alta), el año y al menos un apellido
   (Fase 1, 18.9).
3. Consulta el acceso abierto con Unpaywall.
4. Descarga en ``datos/corpus-provisional/<tema>/`` los PDF con enlace directo, sin
   duplicados entre artículos del mismo tema (el nombre es el DOI).
5. Escribe ``datos/corpus-provisional/informe.csv``.

Estados de cada referencia:

* ``incluida``: PDF de acceso abierto descargado (o ya descargado desde otro artículo).
* ``pendiente_pdf``: tiene acceso abierto, pero no hay enlace directo al PDF o la
  descarga falló o no era un PDF válido; el investigador puede subirlo.
* ``cerrada``: sin versión de acceso abierto conocida (RN-14).
* ``no_localizada``: sin DOI confirmado en Crossref.
* ``articulo_base``: la referencia es otro artículo base; no entra al corpus.

Límites de tasa: una solicitud cada ``--pausa`` segundos por servicio (0,5 s por
defecto) y reintentos con espera ante 429 y 5xx. Crossref y Unpaywall reciben el correo
de ``CORREO_POLITE`` (variable de entorno o ``.env``), como piden sus condiciones de uso;
las descargas de PDF no lo llevan.

Uso, desde la raíz del repositorio y con GROBID en marcha::

    python scripts/armar_corpus_provisional.py
"""

from __future__ import annotations

import argparse
import csv
import difflib
import os
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx

TEI = "{http://www.tei-c.org/ns/1.0}"
CROSSREF = "https://api.crossref.org"
UNPAYWALL = "https://api.unpaywall.org/v2"
TAMANO_MAXIMO = 25 * 1024 * 1024  # RN-16
UMBRAL_TITULO = 0.88
AGENTE_DESCARGA = "SistemaMultiagenteRag/0.1 (corpus provisional de investigacion academica)"
PATRON_DOI = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)

CAMPOS = [
    "tema",
    "articulo_base",
    "n",
    "referencia",
    "doi",
    "estado",
    "nota",
    "archivo",
    "oa_status",
    "licencia",
    "url_pdf",
]


# ---------------------------------------------------------------------------- utilidades


def correo_polite(raiz: Path) -> str:
    valor = os.environ.get("CORREO_POLITE", "").strip()
    if not valor and (raiz / ".env").exists():
        for linea in (raiz / ".env").read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("CORREO_POLITE="):
                valor = linea.split("=", 1)[1].strip().strip("\"'")
    if "@" not in valor:
        sys.exit("ERROR: defina CORREO_POLITE (variable de entorno o .env)")
    return valor


def normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes.lower()).strip()


def normalizar_doi(valor: str | None) -> str | None:
    if not valor:
        return None
    coincidencia = PATRON_DOI.search(valor)
    if not coincidencia:
        return None
    return coincidencia.group(0).rstrip(".,;)]").lower()


def nombre_de_archivo(doi: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", doi.lower())[:150] + ".pdf"


class Limitador:
    """Pausa mínima entre solicitudes a un mismo servicio."""

    def __init__(self, pausa: float) -> None:
        self.pausa = pausa
        self.ultima: dict[str, float] = {}

    def esperar(self, servicio: str) -> None:
        espera = self.ultima.get(servicio, 0.0) + self.pausa - time.monotonic()
        if espera > 0:
            time.sleep(espera)
        self.ultima[servicio] = time.monotonic()


def pedir(
    cliente: httpx.Client, limitador: Limitador, servicio: str, url: str, **kwargs: object
) -> httpx.Response | None:
    """GET con límite de tasa y reintentos ante 429 y 5xx. ``None`` si no hay respuesta."""
    for intento in range(4):
        limitador.esperar(servicio)
        try:
            respuesta = cliente.get(url, **kwargs)  # type: ignore[arg-type]
        except httpx.HTTPError:
            time.sleep(2 * (intento + 1))
            continue
        if respuesta.status_code == 429 or respuesta.status_code >= 500:
            espera = respuesta.headers.get("Retry-After", "")
            time.sleep(float(espera) if espera.isdigit() else 5 * (intento + 1))
            continue
        return respuesta
    return None


# -------------------------------------------------------------------------------- GROBID


@dataclass
class Referencia:
    texto: str
    titulo: str | None
    anio: int | None
    apellidos: list[str]
    doi: str | None


def _texto(elemento: ET.Element | None) -> str | None:
    if elemento is None:
        return None
    texto = " ".join("".join(elemento.itertext()).split())
    return texto or None


def referencias_con_grobid(cliente: httpx.Client, url_grobid: str, pdf: Path) -> list[Referencia]:
    with pdf.open("rb") as archivo:
        respuesta = cliente.post(
            f"{url_grobid}/api/processReferences",
            files={"input": ("articulo.pdf", archivo, "application/pdf")},
            data={"consolidateCitations": "0", "includeRawCitations": "1"},
            headers={"Accept": "application/xml"},
            timeout=600,
        )
    if respuesta.status_code == 204:
        return []
    respuesta.raise_for_status()
    raiz = ET.fromstring(respuesta.text)
    referencias = []
    for biblio in raiz.iter(f"{TEI}biblStruct"):
        crudo = next(
            (_texto(n) for n in biblio.iter(f"{TEI}note") if n.get("type") == "raw_reference"),
            None,
        )
        titulo = _texto(biblio.find(f"{TEI}analytic/{TEI}title")) or _texto(
            biblio.find(f"{TEI}monogr/{TEI}title")
        )
        fecha = biblio.find(f"{TEI}monogr/{TEI}imprint/{TEI}date")
        anio = None
        if fecha is not None:
            coincidencia = re.match(r"(\d{4})", fecha.get("when") or _texto(fecha) or "")
            anio = int(coincidencia.group(1)) if coincidencia else None
        apellidos = [s for s in (_texto(x) for x in biblio.iter(f"{TEI}surname")) if s]
        doi = next(
            (
                normalizar_doi(_texto(i))
                for i in biblio.iter(f"{TEI}idno")
                if (i.get("type") or "").upper() == "DOI"
            ),
            None,
        ) or normalizar_doi(crudo)
        referencias.append(
            Referencia(
                texto=crudo or titulo or "(sin texto)",
                titulo=titulo,
                anio=anio,
                apellidos=apellidos,
                doi=doi,
            )
        )
    return referencias


def doi_de_cabecera(cliente: httpx.Client, url_grobid: str, pdf: Path) -> str | None:
    with pdf.open("rb") as archivo:
        respuesta = cliente.post(
            f"{url_grobid}/api/processHeaderDocument",
            files={"input": ("articulo.pdf", archivo, "application/pdf")},
            data={"consolidateHeader": "0"},
            headers={"Accept": "application/xml"},
            timeout=600,
        )
    if respuesta.status_code != 200:
        return None
    raiz = ET.fromstring(respuesta.text)
    return next(
        (
            normalizar_doi(_texto(i))
            for i in raiz.iter(f"{TEI}idno")
            if (i.get("type") or "").upper() == "DOI"
        ),
        None,
    )


# ------------------------------------------------------------------- Crossref y Unpaywall


@dataclass
class Servicios:
    cliente: httpx.Client
    limitador: Limitador
    correo: str
    cache_crossref: dict[str, bool] = field(default_factory=dict)
    cache_unpaywall: dict[str, dict[str, object] | None] = field(default_factory=dict)

    def doi_existe(self, doi: str) -> bool:
        if doi not in self.cache_crossref:
            respuesta = pedir(
                self.cliente,
                self.limitador,
                "crossref",
                f"{CROSSREF}/works/{quote(doi, safe='/')}",
                params={"mailto": self.correo},
            )
            self.cache_crossref[doi] = respuesta is not None and respuesta.status_code == 200
        return self.cache_crossref[doi]

    def buscar_doi(self, referencia: Referencia) -> str | None:
        """Busca por metadatos y acepta solo con título, año y apellido coincidentes."""
        if not referencia.titulo or len(normalizar(referencia.titulo)) < 15:
            return None
        respuesta = pedir(
            self.cliente,
            self.limitador,
            "crossref",
            f"{CROSSREF}/works",
            params={
                "query.bibliographic": referencia.texto[:500],
                "rows": "3",
                "select": "DOI,title,issued,author",
                "mailto": self.correo,
            },
        )
        if respuesta is None or respuesta.status_code != 200:
            return None
        titulo = normalizar(referencia.titulo)
        apellidos = {normalizar(a) for a in referencia.apellidos}
        for item in respuesta.json().get("message", {}).get("items", []):
            titulos = item.get("title") or [""]
            similitud = difflib.SequenceMatcher(None, titulo, normalizar(titulos[0])).ratio()
            partes = (item.get("issued", {}).get("date-parts") or [[None]])[0]
            anio = partes[0] if partes else None
            autores = {normalizar(a.get("family", "")) for a in item.get("author", []) or []}
            anio_ok = referencia.anio is None or anio is None or abs(anio - referencia.anio) <= 1
            autor_ok = (
                not apellidos
                or bool(apellidos & autores)
                or any(a and any(a in b or b in a for b in autores) for a in apellidos)
            )
            if similitud >= UMBRAL_TITULO and anio_ok and autor_ok:
                return str(item["DOI"]).lower()
        return None

    def unpaywall(self, doi: str) -> dict[str, object] | None:
        if doi not in self.cache_unpaywall:
            respuesta = pedir(
                self.cliente,
                self.limitador,
                "unpaywall",
                f"{UNPAYWALL}/{quote(doi, safe='/')}",
                params={"email": self.correo},
            )
            self.cache_unpaywall[doi] = (
                respuesta.json() if respuesta is not None and respuesta.status_code == 200 else None
            )
        return self.cache_unpaywall[doi]


def descargar_pdf(
    cliente: httpx.Client, limitador: Limitador, url: str, destino: Path
) -> str | None:
    """Descarga si es un PDF válido de hasta 25 MB. Devuelve ``None`` si salió bien."""
    temporal = destino.with_suffix(".parcial")
    servicio = urlparse(url).netloc or "descarga"
    limitador.esperar(servicio)
    try:
        with cliente.stream(
            "GET", url, headers={"User-Agent": AGENTE_DESCARGA}, timeout=90
        ) as respuesta:
            if respuesta.status_code != 200:
                return f"HTTP {respuesta.status_code}"
            escritos = 0
            with temporal.open("wb") as salida:
                for parte in respuesta.iter_bytes(1 << 16):
                    escritos += len(parte)
                    if escritos > TAMANO_MAXIMO:
                        raise ValueError("supera 25 MB")
                    salida.write(parte)
        with temporal.open("rb") as archivo:
            if b"%PDF-" not in archivo.read(1024):
                raise ValueError("no es un PDF")
    except (httpx.HTTPError, ValueError) as error:
        temporal.unlink(missing_ok=True)
        return str(error) or type(error).__name__
    temporal.replace(destino)
    return None


def urls_pdf(datos: dict[str, object]) -> list[str]:
    ubicaciones = [datos.get("best_oa_location"), *(datos.get("oa_locations") or [])]  # type: ignore[misc]
    urls: list[str] = []
    for ubicacion in ubicaciones:
        if isinstance(ubicacion, dict):
            url = ubicacion.get("url_for_pdf")
            if isinstance(url, str) and url not in urls:
                urls.append(url)
    return urls


def licencia(datos: dict[str, object]) -> str:
    mejor = datos.get("best_oa_location")
    return str(mejor.get("license") or "") if isinstance(mejor, dict) else ""


# ---------------------------------------------------------------------------- principal


def procesar_tema(
    tema: Path,
    destino: Path,
    url_grobid: str,
    servicios: Servicios,
    dois_base: set[str],
    escritor: csv.DictWriter[str],
) -> dict[str, int]:
    carpeta = destino / tema.name
    carpeta.mkdir(parents=True, exist_ok=True)
    descargados: dict[str, str] = {}  # doi -> artículo base que lo trajo primero
    conteo = {"referencias": 0, "incluida": 0, "pendiente_pdf": 0, "cerrada": 0,
              "no_localizada": 0, "articulo_base": 0}  # fmt: skip
    for pdf in sorted(tema.glob("*.pdf")):
        referencias = referencias_con_grobid(servicios.cliente, url_grobid, pdf)
        print(f"  {pdf.name}: {len(referencias)} referencias", flush=True)
        for n, referencia in enumerate(referencias, start=1):
            conteo["referencias"] += 1
            fila: dict[str, object] = {
                "tema": tema.name,
                "articulo_base": pdf.name,
                "n": n,
                "referencia": referencia.texto,
            }
            doi = (
                referencia.doi if referencia.doi and servicios.doi_existe(referencia.doi) else None
            )
            if doi is None:
                doi = servicios.buscar_doi(referencia)
            if doi is None:
                estado, nota = "no_localizada", "sin DOI confirmado en Crossref"
            elif doi in dois_base:
                estado, nota = "articulo_base", "es un artículo base; no entra al corpus"
            else:
                estado, nota = _acceso_abierto(servicios, doi, carpeta, descargados, pdf.name, fila)
            fila.update({"doi": doi or "", "estado": estado, "nota": nota})
            conteo[estado] += 1
            escritor.writerow(fila)
    conteo["pdf_en_carpeta"] = len(list(carpeta.glob("*.pdf")))
    return conteo


def _acceso_abierto(
    servicios: Servicios,
    doi: str,
    carpeta: Path,
    descargados: dict[str, str],
    articulo: str,
    fila: dict[str, object],
) -> tuple[str, str]:
    archivo = carpeta / nombre_de_archivo(doi)
    if doi in descargados or archivo.exists():
        fila["archivo"] = archivo.name
        origen = descargados.get(doi, "una ejecución anterior")
        return "incluida", f"PDF ya descargado ({origen})"
    datos = servicios.unpaywall(doi)
    if datos is None:
        return "cerrada", "sin registro en Unpaywall"
    fila["oa_status"] = datos.get("oa_status") or ""
    fila["licencia"] = licencia(datos)
    if not datos.get("is_oa"):
        return "cerrada", "sin versión de acceso abierto (Unpaywall)"
    candidatas = urls_pdf(datos)
    if not candidatas:
        return "pendiente_pdf", "acceso abierto sin enlace directo al PDF"
    motivos = []
    for url in candidatas:
        error = descargar_pdf(servicios.cliente, servicios.limitador, url, archivo)
        if error is None:
            descargados[doi] = articulo
            fila.update({"archivo": archivo.name, "url_pdf": url})
            return "incluida", "PDF descargado"
        motivos.append(error)
    fila["url_pdf"] = candidatas[0]
    return "pendiente_pdf", "descarga fallida: " + "; ".join(motivos)[:200]


def principal() -> int:
    raiz = Path(__file__).resolve().parents[1]
    lector = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    lector.add_argument("--base", type=Path, default=raiz / "datos" / "articulos-base")
    lector.add_argument("--destino", type=Path, default=raiz / "datos" / "corpus-provisional")
    lector.add_argument("--grobid", default="http://127.0.0.1:8070")
    lector.add_argument("--pausa", type=float, default=0.5, help="segundos entre solicitudes")
    lector.add_argument("--tema", action="append", help="solo estos temas (carpetas)")
    args = lector.parse_args()

    correo = correo_polite(raiz)
    temas = sorted(p for p in args.base.iterdir() if p.is_dir())
    if args.tema:
        temas = [t for t in temas if t.name in args.tema]
    args.destino.mkdir(parents=True, exist_ok=True)
    resumen: dict[str, dict[str, int]] = {}
    with httpx.Client(follow_redirects=True, timeout=60) as cliente:
        servicios = Servicios(cliente, Limitador(args.pausa), correo)
        dois_base = {
            d
            for tema in temas
            for pdf in tema.glob("*.pdf")
            if (d := doi_de_cabecera(cliente, args.grobid, pdf))
        }
        informe = args.destino / "informe.csv"
        with informe.open("w", encoding="utf-8-sig", newline="") as salida:
            escritor = csv.DictWriter(salida, fieldnames=CAMPOS, extrasaction="ignore")
            escritor.writeheader()
            for tema in temas:
                print(f"Tema {tema.name}", flush=True)
                resumen[tema.name] = procesar_tema(
                    tema, args.destino, args.grobid, servicios, dois_base, escritor
                )
    print("\nResumen por tema")
    for tema, conteo in resumen.items():
        print(f"  {tema}: " + ", ".join(f"{k}={v}" for k, v in conteo.items()))
    print(f"Informe: {informe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
