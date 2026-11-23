"""Recuperación híbrida con reranking para una solicitud de un caso (T16-01, apartado 2).

``Recuperador.recuperar`` recibe el contexto del caso, el tipo y la consulta. Nunca una
colección: el repositorio las calcula con ``colecciones_permitidas`` (RN-03). Los
parámetros (k, constante de RRF, candidatos, número final y presupuesto) salen de la
configuración vigente.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from app.administracion.parametros import ParametrosFuncionales
from app.bd.enumeraciones import EstadoDocumento, TipoSolicitud
from app.comun.registro import obtener_registrador
from app.inferencia.interfaces import ProveedorEmbeddings, Reordenador
from app.llm.mensajes import estimar_tokens
from app.rag.fusion import fusionar, recortar_por_presupuesto
from app.rag.modelos import Candidato, FragmentoContexto, Recuperacion
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.recuperacion import FragmentoConDocumento
from app.repositorios.unidad import UnidadDeTrabajo

_registro = obtener_registrador("rag")


class Recuperador:
    def __init__(
        self,
        embeddings: ProveedorEmbeddings,
        reordenador: Reordenador,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._embeddings = embeddings
        self._reordenador = reordenador
        self._reloj = reloj

    async def recuperar(
        self,
        unidad: UnidadDeTrabajo,
        contexto: ContextoAcceso,
        tipo: TipoSolicitud,
        consulta: str,
        parametros: ParametrosFuncionales,
    ) -> Recuperacion:
        inicio = self._reloj()
        colecciones = await unidad.colecciones.permitidas(tipo, contexto)
        vacia = Recuperacion(
            consulta_tokens_estimados=estimar_tokens(consulta),
            colecciones=len(colecciones),
            candidatos_densos=0,
            candidatos_lexicos=0,
            reordenados=0,
            fragmentos=[],
            duracion_recuperacion_ms=0,
            duracion_reranking_ms=0,
        )
        if not colecciones or not consulta.strip():
            return vacia
        vector = (await self._embeddings.embeber([consulta])).vectores[0]
        densos = await unidad.recuperacion.buscar_denso(contexto, tipo, vector, parametros.k_denso)
        lexicos = await unidad.recuperacion.buscar_lexico(
            contexto, tipo, consulta, parametros.k_lexico
        )
        fusionados = fusionar(densos, lexicos, parametros.rrf_constante)[
            : parametros.candidatos_reranking
        ]
        datos = await unidad.recuperacion.fragmentos(
            contexto, tipo, [c.fragmento_id for c in fusionados]
        )
        fusionados = [c for c in fusionados if c.fragmento_id in datos]
        recuperado = self._reloj()
        if not fusionados:
            return vacia.model_copy(
                update={
                    "candidatos_densos": len(densos),
                    "candidatos_lexicos": len(lexicos),
                    "duracion_recuperacion_ms": round((recuperado - inicio) * 1000),
                }
            )

        puntajes = await self._reordenador.reordenar(
            consulta, [datos[c.fragmento_id].fragmento.texto for c in fusionados]
        )
        reordenados = sorted(
            (
                c.model_copy(update={"puntaje_reranking": p})
                for c, p in zip(fusionados, puntajes.puntajes, strict=True)
            ),
            key=lambda c: -(c.puntaje_reranking or 0.0),  # sorted es estable: empata por RRF
        )
        fin = self._reloj()
        mejores = reordenados[: parametros.n_reranking]
        cantidad = recortar_por_presupuesto(
            [datos[c.fragmento_id].fragmento.tokens for c in mejores],
            parametros.n_reranking,
            parametros.presupuesto_tokens_contexto,
        )
        fragmentos = [
            _contexto(posicion, candidato, datos[candidato.fragmento_id])
            for posicion, candidato in enumerate(mejores[:cantidad], start=1)
        ]
        resultado = Recuperacion(
            consulta_tokens_estimados=estimar_tokens(consulta),
            colecciones=len(colecciones),
            candidatos_densos=len(densos),
            candidatos_lexicos=len(lexicos),
            reordenados=len(reordenados),
            fragmentos=fragmentos,
            duracion_recuperacion_ms=round((recuperado - inicio) * 1000),
            duracion_reranking_ms=round((fin - recuperado) * 1000),
        )
        _registro.info(
            "recuperacion",
            extra={
                "tipo_evento": "rag",
                "tipo_solicitud": tipo.value,
                "colecciones": len(colecciones),
                "densos": len(densos),
                "lexicos": len(lexicos),
                "reordenados": len(reordenados),
                "contexto": len(fragmentos),
                "tokens_contexto": sum(f.tokens for f in fragmentos),
                "duracion_recuperacion_ms": resultado.duracion_recuperacion_ms,
                "duracion_reranking_ms": resultado.duracion_reranking_ms,
            },
        )
        return resultado


def _contexto(
    posicion: int, candidato: Candidato, dato: FragmentoConDocumento
) -> FragmentoContexto:
    fragmento, documento = dato.fragmento, dato.documento
    return FragmentoContexto(
        identificador=f"F{posicion}",
        posicion=posicion,
        candidato=candidato,
        texto=fragmento.texto,
        tokens=fragmento.tokens,
        documento_id=documento.id,
        titulo=documento.titulo,
        seccion=fragmento.seccion_normalizada.value,
        pagina_inicio=fragmento.pagina_inicio,
        pagina_fin=fragmento.pagina_fin,
        incompleto=documento.estado is EstadoDocumento.INCOMPLETO,
    )
