"""Genera los PDF ficticios de muestra de T09 en ``pruebas/datos/pdf/``.

Uso, desde ``backend/`` y con las dependencias de desarrollo (reportlab)::

    python -m pruebas.datos.generar_pdf_muestra

Los PDF se versionan; este script documenta cómo se hicieron y permite regenerarlos de
forma reproducible (``invariant=1``). Imitan lo que la limpieza debe resolver: encabezado
y pie repetidos con número de página, palabras cortadas con guion al final de línea,
párrafos que continúan en la página o columna siguiente, una tabla y dos columnas (el
artículo en inglés). Todo el contenido es ficticio (``textos_muestra.py``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from pruebas.datos import textos_muestra as t

DESTINO = Path(__file__).parent / "pdf"
ANCHO, ALTO = A4
MARGEN = 56.0
SEPARACION_COLUMNAS = 18.0
ARRIBA = ALTO - MARGEN - 8
ABAJO = MARGEN + 12


@dataclass(frozen=True)
class Estilo:
    fuente: str
    tamano: float
    interlineado: float
    antes: float = 0.0
    despues: float = 0.0
    cortar_palabras: bool = True


ESTILOS = {
    "titulo": Estilo("Helvetica-Bold", 15, 19, 0, 8, cortar_palabras=False),
    "autores": Estilo("Helvetica", 10, 13, 0, 2, cortar_palabras=False),
    "afiliacion": Estilo("Helvetica-Oblique", 9, 12, 0, 12, cortar_palabras=False),
    "seccion": Estilo("Helvetica-Bold", 11.5, 15, 10, 4, cortar_palabras=False),
    "subseccion": Estilo("Helvetica-Bold", 10, 13, 6, 3, cortar_palabras=False),
    "parrafo": Estilo("Times-Roman", 10.5, 13.5, 0, 6),
    "leyenda": Estilo("Times-Italic", 9.5, 12, 4, 3, cortar_palabras=False),
    "tabla": Estilo("Times-Roman", 9.5, 12.5, 0, 8, cortar_palabras=False),
    "referencia": Estilo("Times-Roman", 9, 11.5, 0, 3),
}
TITULOS = {"seccion", "subseccion"}


@dataclass
class Linea:
    x: float
    y: float
    estilo: Estilo
    piezas: list[tuple[float, str]]  # desplazamiento horizontal y texto


@dataclass
class Maquetador:
    """Coloca líneas en páginas y columnas. Las columnas empiezan en ``tope``."""

    paginas: list[list[Linea]] = field(default_factory=lambda: [[]])
    columnas: int = 1
    columna: int = 0
    tope: float = ARRIBA
    y: float = ARRIBA

    @property
    def ancho(self) -> float:
        total = ANCHO - 2 * MARGEN
        return (total - SEPARACION_COLUMNAS * (self.columnas - 1)) / self.columnas

    @property
    def x(self) -> float:
        return MARGEN + self.columna * (self.ancho + SEPARACION_COLUMNAS)

    def cambiar_columnas(self, columnas: int) -> None:
        self.columnas, self.columna, self.tope = columnas, 0, self.y

    def _siguiente_columna(self) -> None:
        if self.columna + 1 < self.columnas:
            self.columna += 1
        else:
            self.paginas.append([])
            self.columna, self.tope = 0, ARRIBA
        self.y = self.tope

    def _cabe(self, alto: float) -> bool:
        return self.y - alto >= ABAJO

    def agregar(self, tipo: str, texto: str) -> None:
        estilo = ESTILOS[tipo]
        if tipo == "tabla":
            self._tabla(estilo, texto)
            return
        lineas = cortar_en_lineas(texto, estilo, self.ancho)
        if self.y != self.tope:
            self.y -= estilo.antes
        # Un título no queda solo al pie: necesita espacio para él y dos líneas más.
        if tipo in TITULOS and not self._cabe(estilo.interlineado * len(lineas) + 30):
            self._siguiente_columna()
        for linea in lineas:
            if not self._cabe(estilo.interlineado):
                self._siguiente_columna()
            self.y -= estilo.interlineado
            self.paginas[-1].append(Linea(self.x, self.y, estilo, [(0.0, linea)]))
        self.y -= estilo.despues

    def _tabla(self, estilo: Estilo, texto: str) -> None:
        filas = [fila.split(";") for fila in texto.split("|")]
        anchos = [0.46, 0.27, 0.27]
        if not self._cabe(estilo.interlineado * len(filas)):
            self._siguiente_columna()
        for fila in filas:
            self.y -= estilo.interlineado
            piezas, desplazamiento = [], 0.0
            for celda, proporcion in zip(fila, anchos, strict=True):
                piezas.append((desplazamiento, celda))
                desplazamiento += proporcion * self.ancho
            self.paginas[-1].append(Linea(self.x, self.y, estilo, piezas))
        self.y -= estilo.despues


def cortar_en_lineas(texto: str, estilo: Estilo, ancho: float) -> list[str]:
    """Ajusta el texto al ancho; corta con guion las palabras largas que no caben."""

    def medida(cadena: str) -> float:
        return stringWidth(cadena, estilo.fuente, estilo.tamano)

    lineas: list[str] = []
    actual = ""
    for palabra in texto.split():
        candidata = f"{actual} {palabra}" if actual else palabra
        if medida(candidata) <= ancho:
            actual = candidata
            continue
        disponible = ancho - medida(f"{actual} ") if actual else ancho
        corte = _cortar_palabra(palabra, disponible, medida) if estilo.cortar_palabras else None
        if corte:
            izquierda, derecha = corte
            lineas.append(f"{actual} {izquierda}-" if actual else f"{izquierda}-")
            actual = derecha
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def _cortar_palabra(
    palabra: str, disponible: float, medida: Callable[[str], float]
) -> tuple[str, str] | None:
    nucleo = palabra.rstrip(",.;:)")
    if len(nucleo) < 9 or not nucleo.isalpha():
        return None
    for i in range(len(nucleo) - 4, 3, -1):
        if medida(palabra[:i] + "-") <= disponible:
            return palabra[:i], palabra[i:]
    return None


def maquetar(bloques: t.Bloques, *, dos_columnas: bool = False) -> list[list[Linea]]:
    maquetador = Maquetador()
    en_columnas = False
    for tipo, texto in bloques:
        if dos_columnas and not en_columnas and tipo == "seccion" and texto[0].isdigit():
            maquetador.y -= 6
            maquetador.cambiar_columnas(2)
            en_columnas = True
        maquetador.agregar(tipo, texto)
    return maquetador.paginas


def dibujar(
    ruta: Path,
    paginas: list[list[Linea]],
    encabezado: str,
    pie: str,
    cifrado: StandardEncryption | None = None,
) -> None:
    lienzo = Canvas(str(ruta), pagesize=A4, invariant=1, encrypt=cifrado)
    lienzo.setTitle("")
    total = len(paginas)
    for numero, lineas in enumerate(paginas, start=1):
        lienzo.setFont("Helvetica", 8)
        lienzo.drawString(MARGEN, ALTO - 34, encabezado)
        lienzo.drawRightString(ANCHO - MARGEN, 30, pie.format(n=numero, total=total))
        for linea in lineas:
            lienzo.setFont(linea.estilo.fuente, linea.estilo.tamano)
            for desplazamiento, texto in linea.piezas:
                lienzo.drawString(linea.x + desplazamiento, linea.y, texto)
        lienzo.showPage()
    lienzo.save()


def pagina_escaneada(lineas: list[str]) -> Image.Image:
    imagen = Image.new("L", (1240, 1754), color=250)
    lapiz = ImageDraw.Draw(imagen)
    fuente = ImageFont.load_default(size=34)
    y = 160
    for linea in lineas:
        lapiz.text((140, y), linea, fill=20, font=fuente)
        y += 60
    return imagen


def escaneado(ruta: Path) -> None:
    lienzo = Canvas(str(ruta), pagesize=A4, invariant=1)
    for numero in (1, 2):
        imagen = pagina_escaneada([*t.TEXTO_ESCANEADO, "", f"Página {numero}"])
        lienzo.drawImage(ImageReader(imagen), 0, 0, ANCHO, ALTO)
        lienzo.showPage()
    lienzo.save()


def generar() -> list[Path]:
    DESTINO.mkdir(exist_ok=True)
    revista = "Revista Ficticia de Educación Superior, 4(2), 2026. doi:10.5555/rfes.2026.0042"
    journal = "Fictitious Journal of Student Health, 2(1), 2026. doi:10.5555/fjsh.2026.0007"
    rutas = {
        "articulo_es.pdf": (maquetar(t.ARTICULO_ES), revista, "Página {n} de {total}"),
        "articulo_en.pdf": (
            maquetar(t.ARTICULO_EN, dos_columnas=True),
            journal,
            "Page {n} of {total}",
        ),
        "documento_corto.pdf": (maquetar(t.DOCUMENTO_CORTO), "Notas ficticias", "{n}"),
        "sin_secciones_imrad.pdf": (
            maquetar(t.documento_sin_secciones()),
            "Ensayos ficticios",
            "{n}",
        ),
    }
    creadas = []
    for nombre, (paginas, encabezado, pie) in rutas.items():
        dibujar(DESTINO / nombre, paginas, encabezado, pie)
        creadas.append(DESTINO / nombre)

    corto = maquetar(t.DOCUMENTO_CORTO)
    # Cifrado con contraseña de apertura (ficticia): no se puede leer y se rechaza (RN-16).
    con_clave = StandardEncryption("apertura-ficticia", "propietario-ficticio", strength=128)
    dibujar(DESTINO / "cifrado.pdf", corto, "Notas ficticias", "{n}", cifrado=con_clave)
    # Solo restricciones de permisos, sin contraseña de apertura: se puede leer.
    restringido = StandardEncryption("", "propietario-ficticio", canModify=0, strength=128)
    dibujar(DESTINO / "solo_permisos.pdf", corto, "Notas ficticias", "{n}", cifrado=restringido)
    escaneado(DESTINO / "escaneado.pdf")
    creadas += [DESTINO / n for n in ("cifrado.pdf", "solo_permisos.pdf", "escaneado.pdf")]
    return creadas


if __name__ == "__main__":
    for ruta in generar():
        print(f"{ruta.name}: {ruta.stat().st_size} bytes")
