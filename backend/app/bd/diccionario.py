"""Generador del diccionario de datos.

Uso (desde ``backend/``): ``python -m app.bd.diccionario`` escribe
``../docs/diccionario-de-datos.md`` en UTF-8.

El diccionario se genera desde los modelos ORM (comentarios, tipos, nulidad, claves y
valores permitidos), de modo que no puede desalinearse del esquema; una prueba compara
el archivo versionado con la salida de este comando.
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import CheckConstraint, Column, Enum, ForeignKeyConstraint, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql.base import PGDialect

import app.bd.modelos as modelos
from app.bd.base import Base
from app.bd.metricas import CODIGOS, CONTADORES_DECISIONES, METRICAS, USO_MINIMO

ENCABEZADO = """# Diccionario de datos

> Generado con `python -m app.bd.diccionario` desde los modelos ORM. **No editar a mano**:
> cambie los modelos y regenere. Una prueba automática falla si este archivo no coincide.

Convenciones: identificadores UUID; fechas `timestamptz` en UTC; enumeraciones guardadas
como texto con restricción CHECK. No hay columnas de nombre, correo ni documento de
identidad (RNF-02, RN-12): los casos se identifican solo por código.

La columna **Alimenta** indica qué métrica de la ficha de registro (M1 a M6, tesis,
Tabla 22) o qué otro dato exportado usa la columna. Las métricas no se guardan como
columnas: se calculan a partir del registro exportado (RF-17). Cuando la alimentan todas
las columnas de una tabla, la tabla lo declara y se repite en cada columna. El índice
inverso, de métrica a columnas, está al final.
"""


def _tipo(columna: Column[object]) -> str:
    tipo = columna.type
    if isinstance(tipo, Enum):
        return "texto (enumeración)"
    nombre = tipo.compile(dialect=_dialecto()).lower()
    return nombre


def _dialecto() -> PGDialect:
    return PGDialect()  # type: ignore[no-untyped-call]


def _valores(columna: Column[object]) -> str:
    tipo = columna.type
    if isinstance(tipo, Enum):
        return ", ".join(f"`{v}`" for v in tipo.enums)
    return ""


def _claves(tabla: Table, columna: Column[object]) -> str:
    partes = []
    if columna.primary_key:
        partes.append("PK")
    for fk in columna.foreign_keys:
        if fk.constraint is not None and len(fk.constraint.columns) > 1:
            continue  # se informa abajo como clave compuesta
        partes.append(f"FK {fk.column.table.name}.{fk.column.name}")
    compuestas = sorted(
        f"FK compuesta ({', '.join(r.columns.keys())}) a {r.elements[0].column.table.name}"
        for r in tabla.constraints
        if isinstance(r, ForeignKeyConstraint) and len(r.columns) > 1 and columna.name in r.columns
    )
    partes.extend(compuestas)
    if columna.unique:
        partes.append("única")
    return "; ".join(partes)


def _limpiar(texto: str | None) -> str:
    return re.sub(r"\s+", " ", texto or "").replace("|", "/").strip()


def alimenta(tabla: Table, columna: Column[object]) -> str:
    """Lo que alimenta la columna: lo declarado por su tabla y lo declarado por ella."""
    partes = [p for p in (tabla.info.get("alimenta"), columna.info.get("alimenta")) if p]
    return "; ".join(partes)


def indice_de_metricas() -> dict[str, list[str]]:
    """Columnas (``tabla.columna``) que alimentan cada métrica M1 a M6."""
    _ = modelos
    indice: dict[str, list[str]] = {codigo: [] for codigo in CODIGOS}
    for tabla in sorted(Base.metadata.sorted_tables, key=lambda t: t.name):
        for columna in tabla.columns:
            for codigo in sorted(set(re.findall(r"\bM[1-6]\b", alimenta(tabla, columna)))):
                indice[codigo].append(f"{tabla.name}.{columna.name}")
    return indice


def _seccion_metricas() -> list[str]:
    indice = indice_de_metricas()
    lineas = [
        "\n## Ficha de métricas: columnas que alimentan cada una\n",
        "| Código | Métrica | Dimensión | Umbral | Columnas |",
        "| --- | --- | --- | --- | --- |",
    ]
    for metrica in METRICAS:
        columnas = ", ".join(f"`{c}`" for c in indice[metrica.codigo])
        lineas.append(
            f"| {metrica.codigo} | {metrica.nombre} | {metrica.dimension} | {metrica.umbral}"
            f" | {columnas} |"
        )
    lineas.extend(
        [
            "\nOtros datos exportados que no son métricas de la ficha:\n",
            f"- {CONTADORES_DECISIONES}: `decision.opcion` agrupada por `solicitud.tipo` y"
            " `decision.caso_id`.",
            f"- {USO_MINIMO}: `solicitud` unida a `version_borrador.hito`; se reporta, no bloquea.",
        ]
    )
    return lineas


def generar() -> str:
    _ = modelos  # registra todas las tablas
    lineas = [ENCABEZADO]
    for tabla in sorted(Base.metadata.sorted_tables, key=lambda t: t.name):
        lineas.append(f"\n## `{tabla.name}`\n")
        lineas.append(f"{_limpiar(tabla.comment)}\n")
        if tabla.name in modelos.TABLAS_DE_CASO or "caso_id" in tabla.c:
            lineas.append("Tabla con datos de caso: toda consulta filtra por `caso_id` (4.5).\n")
        lineas.append(
            "| Columna | Tipo | Nulo | Valores permitidos | Claves | Descripción | Alimenta |"
        )
        lineas.append("| --- | --- | --- | --- | --- | --- | --- |")
        for columna in tabla.columns:
            lineas.append(
                "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                    columna.name,
                    _tipo(columna),
                    "sí" if columna.nullable else "no",
                    _valores(columna),
                    _claves(tabla, columna),
                    _limpiar(columna.comment),
                    _limpiar(alimenta(tabla, columna)),
                )
            )
        restricciones = sorted(
            _limpiar(str(r.sqltext))
            if isinstance(r, CheckConstraint)
            else "única (" + ", ".join(r.columns.keys()) + ")"
            for r in tabla.constraints
            if (isinstance(r, CheckConstraint) and not _es_check_de_enum(r))
            or (isinstance(r, UniqueConstraint) and len(r.columns) > 1)
        )
        indices_parciales = sorted(
            f"{i.name}: {'único' if i.unique else 'índice'} en "
            f"({', '.join(c.name for c in i.columns)}) "
            f"donde {_limpiar(str(i.dialect_options['postgresql']['where']))}"
            for i in tabla.indexes
            if i.dialect_options["postgresql"]["where"] is not None
        )
        if restricciones or indices_parciales:
            lineas.append("\nRestricciones e índices parciales:\n")
            lineas.extend(f"- {r}" for r in restricciones + indices_parciales)
    lineas.extend(_seccion_metricas())
    return "\n".join(lineas) + "\n"


def _es_check_de_enum(restriccion: CheckConstraint) -> bool:
    """Las restricciones CHECK de las enumeraciones ya se listan como valores permitidos."""
    tabla = restriccion.table
    nombres = {str(c.type.name) for c in tabla.columns if isinstance(c.type, Enum) and c.type.name}
    return str(restriccion.name) in nombres or any(
        str(restriccion.name).endswith(f"_{n}") for n in nombres
    )


RUTA_DICCIONARIO = Path(__file__).resolve().parents[3] / "docs" / "diccionario-de-datos.md"

if __name__ == "__main__":
    with RUTA_DICCIONARIO.open("w", encoding="utf-8", newline="") as archivo:
        archivo.write(generar())
    print(f"Diccionario escrito en {RUTA_DICCIONARIO}")
