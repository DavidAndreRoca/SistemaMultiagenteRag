"""Respalda y restaura la base con el corpus ya ingerido (flujo de desarrollo, T10).

Evita repetir horas de ingesta: una ejecución programada ingiere el corpus completo y lo
respalda; en el día a día se restaura el respaldo. Usa solo Docker (no necesita
PostgreSQL ni Python del proyecto en el equipo) y funciona en Windows y Linux.

Respaldo (en ``datos/respaldos/``, excluida de Git):

* ``<nombre>.dump``: ``pg_dump`` en formato comprimido de toda la base.
* ``<nombre>.archivos.tgz``: el volumen ``archivos`` (PDF guardados y caché de extracción
  de Docling), necesario para volver a segmentar sin repetir Docling.
* ``<nombre>.json``: manifiesto con la revisión de Alembic, los documentos y fragmentos
  por colección y la huella SHA-256 de cada archivo.

Uso, desde la raíz del repositorio::

    python scripts/respaldo_corpus.py respaldar [--nombre corpus-provisional]
    python scripts/respaldo_corpus.py restaurar datos/respaldos/corpus-provisional --confirmar

``restaurar`` reemplaza la base y el volumen de archivos del proyecto: por eso exige
``--confirmar``. Detiene la API mientras restaura y la vuelve a levantar.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "datos" / "respaldos"
COMPOSE = ["docker", "compose", "-f", "docker-compose.yml"]
PSQL = 'psql -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
CONTEOS = """
SELECT coalesce(c.tema, c.tipo::text) || '|' || count(DISTINCT d.id) || '|' || count(f.id)
FROM coleccion c LEFT JOIN documento d ON d.coleccion_id = c.id
LEFT JOIN fragmento f ON f.documento_id = d.id
GROUP BY c.id, c.tema, c.tipo ORDER BY 1;
"""


def compose(proyecto: str | None) -> list[str]:
    return [*COMPOSE, *(["-p", proyecto] if proyecto else [])]


def ejecutar(orden: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
    resultado = subprocess.run(orden, cwd=RAIZ, check=False, **kwargs)  # type: ignore[call-overload]
    if resultado.returncode != 0:
        detalle = (resultado.stderr or b"").decode(errors="replace").strip()[-500:]
        sys.exit(f"ERROR: falló {' '.join(orden[:6])} ...\n{detalle}")
    return resultado


def en_bd(proyecto: str | None, comando: str, entrada: bytes | None = None) -> bytes:
    return ejecutar(
        [*compose(proyecto), "exec", "-T", "bd", "sh", "-c", comando],
        input=entrada,
        capture_output=True,
    ).stdout


def sha256(ruta: Path) -> str:
    calculo = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for parte in iter(lambda: archivo.read(1 << 20), b""):
            calculo.update(parte)
    return calculo.hexdigest()


def respaldar(proyecto: str | None, nombre: str) -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    base = DESTINO / nombre
    volcado = base.with_name(f"{nombre}.dump")
    with volcado.open("wb") as salida:
        ejecutar(
            [
                *compose(proyecto),
                "exec",
                "-T",
                "bd",
                "sh",
                "-c",
                'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',
            ],
            stdout=salida,
            stderr=subprocess.PIPE,
        )
    archivos = base.with_name(f"{nombre}.archivos.tgz")
    ejecutar(
        [
            *compose(proyecto),
            "run",
            "--rm",
            "--no-deps",
            "-v",
            f"{DESTINO}:/respaldo",
            "--entrypoint",
            "tar",
            "api",
            "czf",
            f"/respaldo/{archivos.name}",
            "-C",
            "/archivos",
            ".",
        ],
        capture_output=True,
    )
    revision = en_bd(proyecto, f"{PSQL} -c 'SELECT version_num FROM alembic_version'")
    conteos = en_bd(proyecto, PSQL, CONTEOS.encode()).decode().split()
    manifiesto = {
        "creado": dt.datetime.now().isoformat(timespec="seconds"),
        "revision_alembic": revision.decode().strip(),
        "colecciones": [
            dict(zip(("coleccion", "documentos", "fragmentos"), fila.split("|"), strict=True))
            for fila in conteos
        ],
        "archivos": {
            p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in (volcado, archivos)
        },
    }
    base.with_name(f"{nombre}.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Respaldo en {DESTINO}: {volcado.name}, {archivos.name} y {nombre}.json")
    for fila in manifiesto["colecciones"]:
        coleccion, documentos, fragmentos = fila.values()
        print(f"  {coleccion}: {documentos} documentos, {fragmentos} fragmentos")
    return 0


def restaurar(proyecto: str | None, base: Path, confirmar: bool) -> int:
    base = base.resolve()  # Docker monta solo rutas absolutas
    volcado = base.with_name(f"{base.name}.dump")
    archivos = base.with_name(f"{base.name}.archivos.tgz")
    manifiesto = json.loads(base.with_name(f"{base.name}.json").read_text(encoding="utf-8"))
    for ruta in (volcado, archivos):
        esperado = manifiesto["archivos"][ruta.name]["sha256"]
        if sha256(ruta) != esperado:
            sys.exit(f"ERROR: {ruta.name} no coincide con la huella del manifiesto")
    if not confirmar:
        print(
            "La restauración reemplaza la base y el volumen de archivos del proyecto. "
            "Vuelva a ejecutar con --confirmar."
        )
        return 2
    ejecutar([*compose(proyecto), "stop", "api"], capture_output=True)
    en_bd(
        proyecto,
        'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner',
        volcado.read_bytes(),
    )
    ejecutar(
        [
            *compose(proyecto),
            "run",
            "--rm",
            "--no-deps",
            "--user",
            "root",
            "-v",
            f"{archivos.parent}:/respaldo:ro",
            "--entrypoint",
            "sh",
            "api",
            "-c",
            (
                f"find /archivos -mindepth 1 -delete && tar xzf /respaldo/{archivos.name}"
                " -C /archivos && chown -R 10001:10001 /archivos"
            ),
        ],
        capture_output=True,
    )
    ejecutar([*compose(proyecto), "up", "-d", "--wait", "api"], capture_output=True)
    revision = en_bd(proyecto, f"{PSQL} -c 'SELECT version_num FROM alembic_version'")
    print(f"Restaurado {base.name} (Alembic {revision.decode().strip()}).")
    for fila in en_bd(proyecto, PSQL, CONTEOS.encode()).decode().split():
        coleccion, documentos, fragmentos = fila.split("|")
        print(f"  {coleccion}: {documentos} documentos, {fragmentos} fragmentos")
    return 0


def principal() -> int:
    lector = argparse.ArgumentParser(description="Respalda o restaura la base con el corpus.")
    lector.add_argument("--proyecto", help="COMPOSE_PROJECT_NAME (por defecto, el de .env)")
    sub = lector.add_subparsers(dest="accion", required=True)
    r = sub.add_parser("respaldar")
    r.add_argument("--nombre", default=f"corpus-{dt.date.today():%Y%m%d}")
    s = sub.add_parser("restaurar")
    s.add_argument("base", type=Path, help="Ruta del respaldo sin extensión")
    s.add_argument("--confirmar", action="store_true")
    args = lector.parse_args()
    if args.accion == "respaldar":
        return respaldar(args.proyecto, args.nombre)
    return restaurar(args.proyecto, args.base, args.confirmar)


if __name__ == "__main__":
    raise SystemExit(principal())
