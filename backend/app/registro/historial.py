"""Historial del caso y resumen para la declaración de herramientas (T33; RF-14, CU-13,
HU-12, CP-20). Sin acceso a la base: la API le pasa lo que leyó con el caso del contexto.

* ``armar_historial``: versiones cargadas, solicitudes, resultados con su etiqueta,
  decisiones y fuentes aportadas, en orden cronológico, con el hito de la versión sobre la
  que se pidió cada solicitud; se filtra por hito o por periodo (fechas de Lima).
* ``resumen_para_declaracion``: texto plano para que el estudiante redacte su declaración
  de herramientas. Nunca lleva el texto del borrador ni las salidas de los agentes; sí las
  consultas de evidencia, que escribió el propio estudiante.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from app.bd.enumeraciones import (
    EstadoSolicitud,
    Etiqueta,
    IndexacionAporte,
    OpcionDecision,
    TipoSolicitud,
)
from app.bd.modelos import Decision, FuenteAportada, Resultado, Solicitud, VersionBorrador

ZONA = ZoneInfo("America/Lima")
MAX_CONSULTA = 200

NOMBRES_TIPO: dict[TipoSolicitud, str] = {
    TipoSolicitud.BUSQUEDA_EVIDENCIA: "búsqueda de evidencia",
    TipoSolicitud.VERIFICACION_REFERENCIAS: "verificación de referencias",
    TipoSolicitud.REVISION_ESTRUCTURA: "revisión de estructura y coherencia",
    TipoSolicitud.PROPUESTA_REDACCION: "propuesta de redacción",
    TipoSolicitud.REVISION_METODOLOGICA: "revisión metodológica",
    TipoSolicitud.PLAN_TAREA: "plan de tarea",
}
NOMBRES_ETIQUETA: dict[Etiqueta, str] = {
    Etiqueta.VERIFICADA: "Verificada",
    Etiqueta.CON_ADVERTENCIAS: "Con advertencias",
    Etiqueta.SIN_EVIDENCIA_SUFICIENTE: "Sin evidencia suficiente",
}
NOMBRES_OPCION: dict[OpcionDecision, str] = {
    OpcionDecision.ACEPTAR: "la aceptó",
    OpcionDecision.MODIFICAR: "la usará con cambios",
    OpcionDecision.RECHAZAR: "no la usará",
    OpcionDecision.CONTINUAR: "continuó sin aportar una fuente",
    OpcionDecision.APORTAR: "aportó una fuente",
}
NOMBRES_ESTADO: dict[EstadoSolicitud, str] = {
    EstadoSolicitud.ENTREGADA: "entregada",
    EstadoSolicitud.NO_ATENDIDA: "no atendida",
    EstadoSolicitud.RECHAZADA: "no admitida por la validación previa",
}
NOMBRES_INDEXACION: dict[IndexacionAporte, str] = {
    IndexacionAporte.INDEXADA: "se guardó en su colección personal",
    IndexacionAporte.YA_INDEXADA: "ya estaba en su colección personal",
    IndexacionAporte.NO_INDEXADA: "no se guardó",
}


class ClaseEvento(StrEnum):
    VERSION = "version"
    SOLICITUD = "solicitud"
    RESULTADO = "resultado"
    DECISION = "decision"
    APORTE = "aporte"


class EventoHistorial(BaseModel):
    momento: datetime
    clase: ClaseEvento
    descripcion: str
    hito: str | None = None
    nombre_hito: str | None = None
    solicitud_id: uuid.UUID | None = None
    tipo: TipoSolicitud | None = None
    estado: EstadoSolicitud | None = None
    etiqueta: Etiqueta | None = None
    opcion: OpcionDecision | None = None
    vigente: bool | None = None  # de una versión o de una decisión


@dataclass(frozen=True)
class Filtro:
    hito: str | None = None
    desde: date | None = None
    hasta: date | None = None  # inclusive

    def admite(self, evento: EventoHistorial) -> bool:
        if self.hito is not None and evento.hito != self.hito:
            return False
        if self.desde is not None and evento.momento < datetime.combine(self.desde, time.min, ZONA):
            return False
        return self.hasta is None or evento.momento < datetime.combine(
            self.hasta + timedelta(days=1), time.min, ZONA
        )


def finales(resultados: Iterable[Resultado]) -> dict[uuid.UUID, Resultado]:
    """El resultado entregado de cada solicitud: el del último intento."""
    por_solicitud: dict[uuid.UUID, Resultado] = {}
    for resultado in resultados:
        actual = por_solicitud.get(resultado.solicitud_id)
        if actual is None or resultado.intento > actual.intento:
            por_solicitud[resultado.solicitud_id] = resultado
    return por_solicitud


def _consulta(solicitud: Solicitud) -> str | None:
    if solicitud.tipo is not TipoSolicitud.BUSQUEDA_EVIDENCIA or not solicitud.alcance_ref:
        return None
    texto = " ".join(solicitud.alcance_ref.split())
    return texto if len(texto) <= MAX_CONSULTA else texto[: MAX_CONSULTA - 3] + "..."


def armar_historial(
    *,
    versiones: Sequence[VersionBorrador],
    solicitudes: Sequence[Solicitud],
    resultados: Sequence[Resultado],
    decisiones: Sequence[Decision],
    aportes: Sequence[FuenteAportada],
    nombres_hito: dict[str, str],
    filtro: Filtro | None = None,
) -> list[EventoHistorial]:
    hito_de_version = {v.id: v.hito for v in versiones}
    por_id = {s.id: s for s in solicitudes}
    resultados_finales = finales(resultados)
    por_resultado = {r.id: r for r in resultados}
    reemplazadas = {d.decision_reemplazada_id for d in decisiones if d.decision_reemplazada_id}
    eventos: list[EventoHistorial] = []

    def de_solicitud(solicitud: Solicitud, **campos: Any) -> EventoHistorial:
        hito = hito_de_version.get(solicitud.version_id)
        return EventoHistorial(
            hito=hito,
            nombre_hito=nombres_hito.get(hito or ""),
            solicitud_id=solicitud.id,
            tipo=solicitud.tipo,
            **campos,
        )

    for version in versiones:
        eventos.append(
            EventoHistorial(
                momento=version.cargada_en,
                clase=ClaseEvento.VERSION,
                descripcion=f"Cargó una versión de su borrador ({version.palabras} palabras).",
                hito=version.hito,
                nombre_hito=nombres_hito.get(version.hito),
                vigente=version.vigente,
            )
        )
    for solicitud in solicitudes:
        consulta = _consulta(solicitud)
        descripcion = f"Pidió una {NOMBRES_TIPO[solicitud.tipo]}"
        descripcion += f": «{consulta}»." if consulta else "."
        if solicitud.estado in (EstadoSolicitud.NO_ATENDIDA, EstadoSolicitud.RECHAZADA):
            descripcion += f" Quedó {NOMBRES_ESTADO[solicitud.estado]}."
        eventos.append(
            de_solicitud(
                solicitud,
                momento=solicitud.creada_en,
                clase=ClaseEvento.SOLICITUD,
                descripcion=descripcion,
                estado=solicitud.estado,
            )
        )
        resultado = resultados_finales.get(solicitud.id)
        if resultado is not None and solicitud.estado is EstadoSolicitud.ENTREGADA:
            eventos.append(
                de_solicitud(
                    solicitud,
                    momento=solicitud.entregada_en or resultado.creado_en,
                    clase=ClaseEvento.RESULTADO,
                    # La etiqueta va aparte (la interfaz la muestra como insignia; el resumen
                    # la agrega al texto).
                    descripcion=f"Recibió el resultado de la {NOMBRES_TIPO[solicitud.tipo]}"
                    + (" tras un reintento." if resultado.intento > 1 else "."),
                    estado=solicitud.estado,
                    etiqueta=resultado.etiqueta,
                )
            )
    for decision in decisiones:
        resultado = por_resultado.get(decision.resultado_id)
        decidida = por_id.get(resultado.solicitud_id) if resultado else None
        if decidida is None:
            continue
        descripcion = f"Decidió sobre el resultado: {NOMBRES_OPCION[decision.opcion]}."
        if decision.decision_reemplazada_id:
            descripcion += " Reemplaza su decisión anterior."
        eventos.append(
            de_solicitud(
                decidida,
                momento=decision.decidida_en,
                clase=ClaseEvento.DECISION,
                descripcion=descripcion,
                opcion=decision.opcion,
                vigente=decision.id not in reemplazadas,
            )
        )
    for aporte in aportes:
        motivo = por_id.get(aporte.solicitud_id)
        if motivo is None:
            continue
        titulo = str((aporte.datos_bibliograficos or {}).get("titulo", "")).strip()
        eventos.append(
            de_solicitud(
                motivo,
                momento=aporte.aportada_en,
                clase=ClaseEvento.APORTE,
                descripcion=f"Aportó una fuente: «{titulo}»; "
                f"{NOMBRES_INDEXACION[aporte.indexacion]}.",
            )
        )
    orden = list(ClaseEvento)
    eventos.sort(key=lambda e: (e.momento, orden.index(e.clase)))
    return [e for e in eventos if filtro is None or filtro.admite(e)]


def modelos_usados(resultados: Iterable[Resultado]) -> list[str]:
    """Proveedor y modelo de cada resultado, tal como los guardó el agente."""
    vistos: set[str] = set()
    for resultado in resultados:
        modelo = (resultado.salida or {}).get("modelo")
        if isinstance(modelo, dict) and modelo.get("modelo"):
            proveedor = modelo.get("proveedor") or ""
            vistos.add(f"{modelo['modelo']} ({proveedor})" if proveedor else str(modelo["modelo"]))
    return sorted(vistos)


def _fecha(momento: datetime) -> str:
    return momento.astimezone(ZONA).strftime("%d/%m/%Y %H:%M")


def resumen_para_declaracion(
    *,
    codigo: str,
    tema: str,
    eventos: Sequence[EventoHistorial],
    modelos: Sequence[str],
    filtro: Filtro,
    generado_en: datetime,
) -> str:
    solicitudes = [e for e in eventos if e.clase is ClaseEvento.SOLICITUD]
    entregadas = [e for e in eventos if e.clase is ClaseEvento.RESULTADO]
    vigentes = [e for e in eventos if e.clase is ClaseEvento.DECISION and e.vigente]
    por_tipo = Counter(e.tipo for e in entregadas if e.tipo is not None)
    por_opcion = Counter(e.opcion for e in vigentes if e.opcion is not None)
    periodo = (
        f"{filtro.desde.strftime('%d/%m/%Y') if filtro.desde else 'el inicio'} a "
        f"{filtro.hasta.strftime('%d/%m/%Y') if filtro.hasta else 'hoy'}"
    )
    lineas = [
        "RESUMEN DE USO DEL SISTEMA DE ASISTENCIA",
        "Para preparar su declaración de herramientas. Revíselo y redáctela con sus palabras.",
        "",
        f"Caso: {codigo}",
        f"Tema: {tema}",
        f"Periodo: {periodo}" + (f"; hito: {filtro.hito}" if filtro.hito else ""),
        f"Generado: {_fecha(generado_en)} (hora de Lima)",
        "",
        "Herramienta: sistema multiagente con recuperación de fuentes (UTP, Ica). Revisa el"
        " borrador y busca evidencia en las fuentes del tema; no escribe el artículo. Las"
        " referencias las arma el sistema desde los metadatos, nunca un modelo de lenguaje.",
        "Modelos de lenguaje usados: " + (", ".join(modelos) if modelos else "ninguno registrado"),
        "",
        f"Solicitudes: {len(solicitudes)} pedidas, {len(entregadas)} entregadas.",
    ]
    lineas += [f"  {NOMBRES_TIPO[t].capitalize()}: {n}" for t, n in sorted(por_tipo.items())]
    lineas += ["", "Sus decisiones vigentes sobre los resultados:"]
    lineas += [f"  {NOMBRES_OPCION[o].capitalize()}: {n}" for o, n in sorted(por_opcion.items())]
    if not por_opcion:
        lineas.append("  Ninguna registrada.")
    lineas += ["", "Detalle cronológico:"]
    lineas += [
        f"  {_fecha(e.momento)}"
        + (f" [{e.nombre_hito or e.hito}]" if e.hito else "")
        + f" {e.descripcion}"
        + (f" Etiqueta: {NOMBRES_ETIQUETA[e.etiqueta]}." if e.etiqueta else "")
        for e in eventos
    ]
    if not eventos:
        lineas.append("  Sin registros en este periodo.")
    return "\n".join(lineas) + "\n"
