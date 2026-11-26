"""Genera el borrador de demostración del prototipo: ``docs/demo/borrador-demostracion.docx``.

``python scripts/generar_borrador_demo.py`` (con el entorno del backend, que trae python-docx).

El texto es ficticio, como lo escribiría un estudiante del tema TEMA-1-IA-EDUCACION, sin
datos de participantes. La lista va en IEEE y usa obras reales del conjunto revisado de
T20 (``evaluacion/conjuntos/referencias-t20.json``), con errores puestos a propósito para
que la verificación tenga algo que mostrar:

- [1] a [3]: correctas (dos con DOI y una sin DOI);
- [4]: año equivocado (la fuente registra 2023);
- [5]: inventada (no existe);
- [6]: inventada con el DOI real de otra obra;
- [7]: correcta, pero el texto no la cita;
- el texto cita [8], que no está en la lista.

Provisional, sin revisión humana (ESTADO, apartado 24).
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document

RAIZ = Path(__file__).resolve().parents[1]
CONJUNTO = RAIZ / "evaluacion" / "conjuntos" / "referencias-t20.json"
DESTINO = RAIZ / "docs" / "demo" / "borrador-demostracion.docx"

# (id en el conjunto, cambios sobre la referencia)
LISTA = [
    ("R-02", {}),
    ("R-03", {}),
    ("R-07", {}),
    ("R-04", {"anio": 2021}),
    ("R-15", {}),
    ("R-17", {}),
    ("R-06", {}),
]

TITULO = "Percepciones de estudiantes universitarios sobre el uso de ChatGPT en la escritura académica"
INTRODUCCION = [
    "La llegada de la inteligencia artificial generativa cambió la forma en que los estudiantes"
    " universitarios redactan sus trabajos. Herramientas como ChatGPT se usan para buscar ideas,"
    " corregir el estilo y resumir lecturas, y los estudiantes valoran su rapidez aunque"
    " reconocen que puede equivocarse [1]-[2].",
    "En el contexto latinoamericano, el uso de estos asistentes en los entornos personales de"
    " aprendizaje plantea la necesidad de orientar a los estudiantes sobre un uso adecuado de"
    " los recursos tecnológicos [3]. Las revisiones recientes coinciden en que la discusión ya no"
    " es si usarlos, sino cómo integrarlos en la enseñanza [4].",
]
METODO = [
    "El estudio propuesto es de enfoque cuantitativo, con un cuestionario aplicado a estudiantes"
    " de pregrado de una universidad privada. El instrumento se adaptará de estudios previos"
    " sobre percepción de herramientas de inteligencia artificial en escolares [5].",
]
DISCUSION = [
    "Se espera que los estudiantes reporten beneficios en la organización de sus ideas y"
    " preocupación por la integridad académica, como señalan trabajos sobre evaluación"
    " formativa en posgrado [6]. También se espera que la carga académica explique parte del"
    " uso intensivo de estas herramientas [8].",
]


def entrada_ieee(numero: int, r: dict[str, object]) -> str:
    autores_lista = [f"{i} {a}".strip() for a, i in r["autores"]]  # type: ignore[attr-defined]
    if len(autores_lista) > 6:
        autores = f"{autores_lista[0]} et al."
    elif len(autores_lista) < 3:
        autores = " and ".join(autores_lista)
    else:
        autores = ", ".join(autores_lista[:-1]) + ", and " + autores_lista[-1]
    partes = [f"[{numero}] {autores}, “{r['titulo']},” {r['revista']}"]
    if r.get("volumen"):
        partes.append(f", vol. {r['volumen']}")
    if r.get("numero"):
        partes.append(f", no. {r['numero']}")
    if r.get("paginas"):
        partes.append(f", pp. {r['paginas']}")
    partes.append(f", {r['anio']}")
    if r.get("doi"):
        partes.append(f", doi: {r['doi']}")
    return "".join(partes) + "."


def main() -> None:
    referencias = {r["id"]: r for r in json.loads(CONJUNTO.read_text(encoding="utf-8"))["referencias"]}
    documento = Document()
    documento.add_heading(TITULO, level=0)
    documento.add_paragraph("Borrador ficticio de demostración. Estudiante: DEMO-01.")
    for titulo, parrafos in (
        ("1. Introducción", INTRODUCCION),
        ("2. Método", METODO),
        ("3. Discusión", DISCUSION),
    ):
        documento.add_heading(titulo, level=1)
        for parrafo in parrafos:
            documento.add_paragraph(parrafo)
    documento.add_heading("Referencias", level=1)
    for numero, (ident, cambios) in enumerate(LISTA, start=1):
        documento.add_paragraph(entrada_ieee(numero, {**referencias[ident], **cambios}))
    DESTINO.parent.mkdir(exist_ok=True)
    documento.save(str(DESTINO))
    print(f"{DESTINO.relative_to(RAIZ)}: {DESTINO.stat().st_size} bytes")


if __name__ == "__main__":
    main()
