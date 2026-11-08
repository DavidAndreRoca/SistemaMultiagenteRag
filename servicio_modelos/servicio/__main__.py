"""Arranque: ``python -m servicio``. Escucha en 0.0.0.0 dentro del contenedor; Compose
publica el puerto solo en 127.0.0.1."""

import uvicorn

from servicio.ajustes import cargar_ajustes
from servicio.aplicacion import crear_aplicacion

if __name__ == "__main__":
    ajustes = cargar_ajustes()
    uvicorn.run(crear_aplicacion(ajustes), host="0.0.0.0", port=ajustes.puerto, access_log=False)
