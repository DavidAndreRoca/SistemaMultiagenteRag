"""Verificación de referencias con los servicios reales sobre el conjunto de prueba (T20).

``python -m app.agentes.evaluar_referencias <conjunto.json> [--salida informe.json]``

Bajo demanda, nunca en la CI. Por cada borrador del conjunto lee el .docx por el mismo
camino que una versión cargada (T11 y T12), estructura la lista con GROBID
(``URL_GROBID``), verifica cada referencia en Crossref y OpenAlex sin caché y cruza las
citas del texto. Compara con la clave del borrador:

* estado de cada entrada (acuerdo con lo esperado);
* fabricadas que quedan como verificadas (debe ser 0: criterio de aceptación de T20);
* citas sin entrada y entradas no citadas.

No usa la base de datos ni el modelo de lenguaje.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from app.agentes.citas import cruzar, extraer_citas
from app.agentes.referencias import alinear, cuerpo, lista_para_cruce
from app.agentes.verificacion_referencias import Verificador
from app.bibliografia.fabrica import crear_servicios
from app.borradores.extraccion import extraer_parrafos
from app.borradores.secciones import detectar_por_estilos
from app.configuracion import cargar_ajustes
from app.corpus.grobid import ClienteGrobid


async def evaluar(ruta: Path, conjunto: dict[str, Any]) -> dict[str, Any]:
    ajustes = cargar_ajustes()
    if not ajustes.url_grobid:
        raise SystemExit("falta URL_GROBID")
    servicios = crear_servicios(ajustes)  # sin caché: no escribe en la base
    grobid = ClienteGrobid(ajustes.url_grobid)
    verificador = Verificador(servicios.crossref, servicios.openalex)
    tipos = {r["id"]: r["tipo"] for r in conjunto["referencias"]}
    informes = []
    try:
        for borrador in conjunto["borradores"]:
            norma = borrador["norma"]
            parrafos = (
                await asyncio.to_thread(extraer_parrafos, ruta.parent / borrador["archivo"])
            ).parrafos
            secciones = detectar_por_estilos(parrafos)
            if secciones is None or secciones.referencias is None:
                raise SystemExit(f"no se detectó la lista de {borrador['archivo']}")
            entradas = secciones.referencias.entradas
            referencias = alinear(
                entradas, await asyncio.to_thread(grobid.referencias_de_texto, list(entradas))
            )
            filas = []
            for indice, referencia in enumerate(referencias, start=1):
                verificada = await verificador.verificar(indice, referencia)
                esperada = borrador["clave"]["estados"][str(indice)]
                ident = borrador["lista"][indice - 1]["id"]
                filas.append(
                    {
                        "indice": indice,
                        "id": ident,
                        "tipo": tipos[ident],
                        "esperado": esperada,
                        "obtenido": verificada.estado.value,
                        "acierto": verificada.estado.value == esperada,
                        "metodo": verificada.metodo,
                        "campos": [d.campo for d in verificada.discrepancias],
                    }
                )
                print(json.dumps({"norma": norma, **filas[-1]}, ensure_ascii=False), flush=True)
            cruce = cruzar(
                extraer_citas(cuerpo(parrafos, secciones), norma),
                lista_para_cruce(referencias, norma),
                norma,
            )
            clave = borrador["clave"]
            informes.append(
                {
                    "norma": norma,
                    "referencias": len(filas),
                    "aciertos_estado": sum(f["acierto"] for f in filas),
                    "fabricadas_verificadas": sum(
                        1
                        for f in filas
                        if f["tipo"] == "fabricada" and f["obtenido"] == "verificada"
                    ),
                    "estados": dict(Counter(f["obtenido"] for f in filas)),
                    "citas_sin_entrada": cruce.citas_sin_entrada,
                    "citas_sin_entrada_ok": cruce.citas_sin_entrada == clave["citas_sin_entrada"],
                    "entradas_no_citadas": cruce.entradas_no_citadas,
                    "entradas_no_citadas_ok": cruce.entradas_no_citadas
                    == clave["entradas_no_citadas"],
                    "citas_extraidas": len(cruce.citas),
                    "citas_esperadas": len(clave["citas"]),
                    "detalle": filas,
                }
            )
    finally:
        grobid.cerrar()
        await servicios.cerrar()
    return {
        "conjunto": {"nombre": conjunto["nombre"], "version": conjunto["version"]},
        "fabricadas_verificadas": sum(i["fabricadas_verificadas"] for i in informes),
        "borradores": informes,
    }


def principal() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("conjunto", type=Path)
    argumentos.add_argument("--salida", type=Path)
    leidos = argumentos.parse_args()
    fabrica = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    conjunto = json.loads(leidos.conjunto.read_text(encoding="utf-8-sig"))
    informe = asyncio.run(evaluar(leidos.conjunto, conjunto), loop_factory=fabrica)
    texto = json.dumps(informe, ensure_ascii=False, indent=2) + "\n"
    if leidos.salida:
        leidos.salida.write_bytes(texto.encode("utf-8"))
    resumen = {
        "fabricadas_verificadas": informe["fabricadas_verificadas"],
        "borradores": [
            {k: v for k, v in b.items() if k != "detalle"} for b in informe["borradores"]
        ],
    }
    print(json.dumps(resumen, ensure_ascii=False))


if __name__ == "__main__":
    principal()
