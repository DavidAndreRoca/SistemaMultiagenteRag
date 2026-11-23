"""Herramienta de las instrucciones versionadas (T17).

* ``python -m app.instrucciones listar``: cada archivo, su huella y si está registrada.
* ``python -m app.instrucciones registrar <agente>/<version>``: agrega la huella de una
  versión nueva a ``registro.json``. Una versión ya registrada no se puede cambiar.
"""

from __future__ import annotations

import json
import sys

from app.instrucciones.cargador import DIRECTORIO, REGISTRO, disponibles, registro


def principal(argumentos: list[str]) -> int:
    if not argumentos or argumentos[0] not in ("listar", "registrar"):
        print(__doc__)
        return 2
    actuales = disponibles()
    registradas = registro()
    if argumentos[0] == "listar":
        for identificador, firma in actuales.items():
            estado = (
                "registrada"
                if registradas.get(identificador) == firma
                else "SIN REGISTRAR"
                if identificador not in registradas
                else "MODIFICADA"
            )
            print(f"{identificador}  {firma[:12]}  {estado}")
        return 0
    if len(argumentos) != 2 or argumentos[1] not in actuales:
        print("Indique una instrucción existente: <agente>/<version>")
        return 2
    identificador = argumentos[1]
    if identificador in registradas:
        if registradas[identificador] == actuales[identificador]:
            print(f"{identificador} ya está registrada.")
            return 0
        print(f"{identificador} ya está registrada con otra huella: cree una versión nueva.")
        return 1
    nuevo = {**registradas, identificador: actuales[identificador]}
    # Siempre con LF, también en Windows: el archivo se versiona.
    (DIRECTORIO / REGISTRO).write_bytes(
        (json.dumps(dict(sorted(nuevo.items())), indent=2) + "\n").encode("utf-8")
    )
    print(f"{identificador} registrada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal(sys.argv[1:]))
