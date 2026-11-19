"""Validación del alcance de una solicitud según su tipo (RF-02, CP-09; T12-01, apartado 6).

``validar_alcance`` comprueba que el alcance esté admitido por el tipo (insumos de T04,
tabla 3), que la sección o el párrafo existan en la versión y los límites (D3: un párrafo
de hasta ``limite_palabras_d3`` palabras). Devuelve el texto del alcance, que es lo único
del borrador que una solicitud enviará al proveedor del modelo (RNF-10). Crear y encolar
la solicitud es de las fases de orquestación.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from app.administracion.parametros import ParametrosFuncionales
from app.bd.enumeraciones import ALCANCES_ADMITIDOS, TipoAlcance, TipoSolicitud
from app.borradores.extraccion import ParrafoBorrador
from app.borradores.secciones import SeccionesVersion, descendientes
from app.comun.errores import ErrorAplicacion

MAX_CARACTERES_CONSULTA = 2000


class AlcanceInvalido(ErrorAplicacion):
    def __init__(self, motivo: str, mensaje: str, **detalle: object) -> None:
        super().__init__(motivo, mensaje, estado_http=422, detalle={"motivo": motivo, **detalle})
        self.motivo = motivo


class AlcanceResuelto(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: TipoSolicitud
    alcance_tipo: TipoAlcance
    alcance_ref: str | None
    parrafos: list[str]  # ids de los párrafos del alcance (vacío en una consulta)
    texto: str
    palabras: int


def validar_alcance(
    tipo: TipoSolicitud,
    alcance_tipo: TipoAlcance,
    alcance_ref: str | None,
    parrafos: Sequence[ParrafoBorrador],
    secciones: SeccionesVersion | None,
    parametros: ParametrosFuncionales,
) -> AlcanceResuelto:
    admitidos = ALCANCES_ADMITIDOS[tipo]
    if alcance_tipo not in admitidos:
        raise AlcanceInvalido(
            "alcance_no_admitido",
            "Este tipo de solicitud no admite ese alcance.",
            admitidos=sorted(a.value for a in admitidos),
        )
    ref = (alcance_ref or "").strip() or None
    if alcance_tipo in (TipoAlcance.HITO, TipoAlcance.VERSION):
        if ref is not None:
            raise AlcanceInvalido(
                "alcance_ref_no_admitido",
                "Este alcance toma la versión completa: no indique una sección ni un párrafo.",
            )
        return _resuelto(tipo, alcance_tipo, None, list(parrafos))
    if alcance_tipo is TipoAlcance.CONSULTA:
        return _consulta(tipo, ref)
    if ref is None:
        raise AlcanceInvalido("alcance_sin_referencia", "Indique la sección o el párrafo.")
    if alcance_tipo is TipoAlcance.SECCION:
        return _resuelto(tipo, alcance_tipo, ref, _de_seccion(ref, parrafos, secciones))

    parrafo = next((p for p in parrafos if p.id == ref), None)
    if parrafo is None:
        raise AlcanceInvalido(
            "parrafo_inexistente", "El párrafo indicado no existe en esta versión.", parrafo=ref
        )
    resuelto = _resuelto(tipo, alcance_tipo, ref, [parrafo])
    limite = parametros.limite_palabras_d3
    if tipo is TipoSolicitud.PROPUESTA_REDACCION and resuelto.palabras > limite:
        raise AlcanceInvalido(  # CP-09
            "alcance_demasiado_largo",
            f"El párrafo tiene {resuelto.palabras} palabras y la propuesta de redacción admite"
            f" hasta {limite}. Elija un párrafo más corto o divídalo en dos.",
            palabras=resuelto.palabras,
            limite=limite,
        )
    return resuelto


def _de_seccion(
    ref: str, parrafos: Sequence[ParrafoBorrador], secciones: SeccionesVersion | None
) -> list[ParrafoBorrador]:
    if secciones is None or not secciones.secciones:
        raise AlcanceInvalido(
            "sin_secciones",
            "Esta versión no tiene secciones detectadas. Marque los títulos de sus secciones"
            " para poder elegir una.",
        )
    if not any(s.id == ref for s in secciones.secciones):
        raise AlcanceInvalido(
            "seccion_inexistente", "La sección indicada no existe en esta versión.", seccion=ref
        )
    rama = descendientes(secciones.secciones, ref)
    ids = {s.parrafo_titulo for s in rama} | {pid for s in rama for pid in s.parrafos}
    return [p for p in parrafos if p.id in ids]


def _consulta(tipo: TipoSolicitud, ref: str | None) -> AlcanceResuelto:
    if ref is None:
        raise AlcanceInvalido("consulta_vacia", "Escriba la consulta.")
    if len(ref) > MAX_CARACTERES_CONSULTA:
        raise AlcanceInvalido(
            "consulta_demasiado_larga",
            f"La consulta admite hasta {MAX_CARACTERES_CONSULTA} caracteres.",
            limite=MAX_CARACTERES_CONSULTA,
        )
    return AlcanceResuelto(
        tipo=tipo,
        alcance_tipo=TipoAlcance.CONSULTA,
        alcance_ref=ref,
        parrafos=[],
        texto=ref,
        palabras=len(ref.split()),
    )


def _resuelto(
    tipo: TipoSolicitud,
    alcance_tipo: TipoAlcance,
    ref: str | None,
    parrafos: Sequence[ParrafoBorrador],
) -> AlcanceResuelto:
    texto = "\n\n".join(p.texto for p in parrafos)
    return AlcanceResuelto(
        tipo=tipo,
        alcance_tipo=alcance_tipo,
        alcance_ref=ref,
        parrafos=[p.id for p in parrafos],
        texto=texto,
        palabras=len(texto.split()),
    )
