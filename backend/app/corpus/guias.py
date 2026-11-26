"""Corpus de guías (T22; RF-15, RN-11, D-13): ``python -m app.corpus.guias``.

``python -m app.corpus.guias --investigador I --carpeta DIR [--aplicar]``

Indexa en la colección ``guias`` (una sola, compartida por todos los casos) los documentos
que sustentan a D1, D2 y D3: instrucciones del programa por hito, guías de investigación y
de redacción y listas de comprobación por diseño.

* **Formatos:** Markdown con cabecera (``titulo``, ``tipo``, ``procedencia``, ``licencia``) y
  apartados ``## ...``, o .docx con títulos con estilo (T11 y T12).
* **Segmentación por apartado,** no por IMRaD: cada fragmento registra su apartado en
  ``seccion_original``. Un apartado largo se divide por párrafos.
* **La rúbrica nunca se indexa** (RN-11): se rechaza por nombre (archivo o título con
  "rúbrica") o por huella SHA-256 registrada en ``guias/rubricas-bloqueadas.txt``.
* **Procedencia y licencia** de cada guía quedan en el documento.

Sin ``--aplicar`` solo informa. Una guía ya indexada (mismo texto) no se duplica.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.bd.enumeraciones import EstadoDocumento, OrigenDocumento, SeccionNormalizada, TipoColeccion
from app.bd.modelos import Coleccion, Documento, Fragmento
from app.bd.sesion import crear_fabrica_sesiones, crear_motor
from app.bibliografia.normalizacion import normalizar
from app.borradores.extraccion import extraer_parrafos
from app.comun.errores import ErrorAplicacion
from app.configuracion import cargar_ajustes
from app.inferencia.interfaces import ProveedorEmbeddings
from app.inferencia.servicio_modelos import cliente_desde_ajustes
from app.llm.mensajes import estimar_tokens
from app.repositorios.contexto import ContextoAcceso
from app.repositorios.unidad import UnidadDeTrabajo, fabrica_de_unidades
from app.seguridad.consola import CuentaNoValida, contexto_de_investigador

MAX_TOKENS_FRAGMENTO = 450
EXTENSIONES = (".md", ".docx")
BLOQUEADAS = Path(__file__).resolve().parents[2] / "guias" / "rubricas-bloqueadas.txt"
_CABECERA = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class RubricaNoIndexable(ErrorAplicacion):
    def __init__(self, nombre: str) -> None:
        super().__init__(
            "rubrica_no_indexable",
            "La rúbrica de evaluación no se indexa en el corpus de guías (RN-11).",
            estado_http=422,
            detalle={"archivo": nombre},
        )


class Apartado(BaseModel):
    model_config = ConfigDict(frozen=True)

    titulo: str
    texto: str


class Guia(BaseModel):
    model_config = ConfigDict(frozen=True)

    archivo: str
    titulo: str
    tipo: str
    procedencia: str
    licencia: str
    apartados: list[Apartado]
    huella_archivo: str

    @property
    def huella_texto(self) -> str:
        texto = "\n".join(f"{a.titulo}\n{a.texto}" for a in self.apartados)
        return hashlib.sha256(normalizar(texto).encode("utf-8")).hexdigest()


def _leer_markdown(nombre: str, contenido: bytes) -> Guia:
    texto = contenido.decode("utf-8-sig")
    cabecera: dict[str, str] = {}
    if coincidencia := _CABECERA.match(texto):
        for linea in coincidencia.group(1).splitlines():
            clave, _, valor = linea.partition(":")
            if valor:
                cabecera[clave.strip()] = valor.strip()
        texto = texto[coincidencia.end() :]
    apartados: list[Apartado] = []
    for bloque in re.split(r"^##\s+", texto, flags=re.MULTILINE)[1:]:
        titulo, _, cuerpo = bloque.partition("\n")
        cuerpo = cuerpo.strip()
        if cuerpo:
            apartados.append(Apartado(titulo=titulo.strip(), texto=cuerpo))
    return Guia(
        archivo=nombre,
        titulo=cabecera.get("titulo", Path(nombre).stem),
        tipo=cabecera.get("tipo", "guia_investigacion"),
        procedencia=cabecera.get("procedencia", "Sin declarar"),
        licencia=cabecera.get("licencia", "Sin declarar"),
        apartados=apartados,
        huella_archivo=hashlib.sha256(contenido).hexdigest(),
    )


def _leer_docx(ruta: Path) -> Guia:
    parrafos = extraer_parrafos(ruta).parrafos
    titulo = next((p.texto for p in parrafos if p.nivel == 0), ruta.stem)
    apartados: list[Apartado] = []
    actual: str | None = None
    lineas: list[str] = []
    for parrafo in parrafos:
        if parrafo.nivel is not None and parrafo.nivel >= 1:
            if actual and lineas:
                apartados.append(Apartado(titulo=actual, texto="\n\n".join(lineas)))
            actual, lineas = parrafo.texto, []
        elif parrafo.nivel is None and actual is not None:
            lineas.append(parrafo.texto)
    if actual and lineas:
        apartados.append(Apartado(titulo=actual, texto="\n\n".join(lineas)))
    return Guia(
        archivo=ruta.name,
        titulo=titulo,
        tipo="guia_investigacion",
        procedencia="Sin declarar",
        licencia="Sin declarar",
        apartados=apartados,
        huella_archivo=hashlib.sha256(ruta.read_bytes()).hexdigest(),
    )


def leer_guia(ruta: Path) -> Guia:
    if ruta.suffix.lower() == ".docx":
        return _leer_docx(ruta)
    return _leer_markdown(ruta.name, ruta.read_bytes())


def huellas_bloqueadas(ruta: Path = BLOQUEADAS) -> frozenset[str]:
    if not ruta.exists():
        return frozenset()
    return frozenset(
        linea.split("#", 1)[0].strip().lower()
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.split("#", 1)[0].strip()
    )


def exigir_no_rubrica(guia: Guia, bloqueadas: frozenset[str]) -> None:
    """RN-11: ni por nombre ni por huella registrada."""
    nombres = normalizar(f"{guia.archivo} {guia.titulo}")
    if "rubrica" in nombres.split() or "rubrica" in nombres or guia.huella_archivo in bloqueadas:
        raise RubricaNoIndexable(guia.archivo)


def segmentar(guia: Guia, maximo: int = MAX_TOKENS_FRAGMENTO) -> list[tuple[str, str, int]]:
    """(apartado, texto, tokens) por fragmento; un apartado largo se divide por párrafos."""
    fragmentos: list[tuple[str, str, int]] = []
    for apartado in guia.apartados:
        actual: list[str] = []
        for parrafo in [p.strip() for p in apartado.texto.split("\n\n") if p.strip()]:
            candidato = "\n\n".join([*actual, parrafo])
            if actual and estimar_tokens(candidato) > maximo:
                texto = "\n\n".join(actual)
                fragmentos.append((apartado.titulo, texto, estimar_tokens(texto)))
                actual = [parrafo]
            else:
                actual.append(parrafo)
        if actual:
            texto = "\n\n".join(actual)
            fragmentos.append((apartado.titulo, texto, estimar_tokens(texto)))
    return fragmentos


async def coleccion_guias(unidad: UnidadDeTrabajo, contexto: ContextoAcceso) -> Coleccion:
    existente = await unidad.colecciones_investigador.guias(contexto)
    if existente is not None:
        return existente
    return await unidad.colecciones_investigador.agregar(
        contexto, Coleccion(tipo=TipoColeccion.GUIAS)
    )


async def indexar_guia(
    unidad: UnidadDeTrabajo,
    contexto: ContextoAcceso,
    coleccion: Coleccion,
    guia: Guia,
    embeddings: ProveedorEmbeddings,
    bloqueadas: frozenset[str] = frozenset(),
) -> tuple[str, uuid.UUID | None]:
    """("indexada" o "duplicada", id del documento). Lanza ``RubricaNoIndexable``."""
    exigir_no_rubrica(guia, bloqueadas)
    original = await unidad.corpus.duplicado(contexto, coleccion.id, guia.huella_texto, None)
    if original is not None:
        return "duplicada", original.id
    partes = segmentar(guia)
    embebidos = await embeddings.embeber([texto for _, texto, _ in partes])
    documento = Documento(
        id=uuid.uuid4(),
        coleccion_id=coleccion.id,
        titulo=guia.titulo,
        autores=[],
        revista_editorial=guia.procedencia[:500],
        licencia=guia.licencia[:80],
        idioma="es",
        huella_sha256=guia.huella_texto,
        estado=EstadoDocumento.ACTIVO,
        origen=OrigenDocumento.INGESTA,
        huella_archivo=guia.huella_archivo,
        archivo_original=guia.archivo,
        motivo_estado=f"guia:{guia.tipo}",
        indexado_por_id=contexto.cuenta_id,
        modelo_embeddings=embebidos.identidad.modelo,
        revision_embeddings=embebidos.identidad.revision,
    )
    fragmentos = [
        Fragmento(
            orden=orden,
            texto=texto,
            seccion_normalizada=SeccionNormalizada.OTRA,
            seccion_original=apartado[:300],
            tokens=tokens,
            embedding=vector,
        )
        for orden, ((apartado, texto, tokens), vector) in enumerate(
            zip(partes, embebidos.vectores, strict=True), start=1
        )
    ]
    await unidad.corpus.agregar_documento(contexto, documento, fragmentos)
    await unidad.corpus.recontar(contexto, coleccion)
    return "indexada", documento.id


def archivos(carpeta: Path) -> Sequence[Path]:
    return sorted(p for p in carpeta.iterdir() if p.suffix.lower() in EXTENSIONES)


async def _ejecutar(investigador: str, carpeta: Path, aplicar: bool) -> int:
    ajustes = cargar_ajustes()
    motor = crear_motor(ajustes)
    abrir = fabrica_de_unidades(crear_fabrica_sesiones(motor))
    modelos = cliente_desde_ajustes(ajustes)
    bloqueadas = huellas_bloqueadas()
    try:
        async with abrir() as unidad:
            try:
                contexto = await contexto_de_investigador(unidad, investigador)
            except CuentaNoValida as error:
                print(error)
                return 2
            coleccion = await coleccion_guias(unidad, contexto)
            for ruta in archivos(carpeta):
                guia = leer_guia(ruta)
                try:
                    if aplicar:
                        estado, _ = await indexar_guia(
                            unidad, contexto, coleccion, guia, modelos, bloqueadas
                        )
                    else:
                        exigir_no_rubrica(guia, bloqueadas)
                        estado = "por indexar"
                except RubricaNoIndexable:
                    estado = "rechazada (rúbrica)"
                print(f"  {ruta.name}: {estado}, {len(segmentar(guia))} fragmentos")
            if aplicar:
                await unidad.confirmar()
    finally:
        await modelos.cerrar()
        await motor.dispose()
    print("aplicado" if aplicar else "simulación (use --aplicar para guardar)")
    return 0


def principal() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--investigador", required=True)
    argumentos.add_argument("--carpeta", type=Path, required=True)
    argumentos.add_argument("--aplicar", action="store_true")
    leidos = argumentos.parse_args()
    fabrica = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    codigo = asyncio.run(
        _ejecutar(leidos.investigador, leidos.carpeta, leidos.aplicar), loop_factory=fabrica
    )
    raise SystemExit(codigo)


if __name__ == "__main__":
    principal()
