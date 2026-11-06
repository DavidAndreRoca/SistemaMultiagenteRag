"""Valores fijados de la Fase 1 (Tabla 48 aceptada) para sesiones y bloqueo.

No son parámetros funcionales calibrables: son requisitos de seguridad (RN-15).
"""

from __future__ import annotations

from datetime import timedelta

DURACION_ABSOLUTA_SESION = timedelta(hours=8)
INACTIVIDAD_MAXIMA = timedelta(minutes=60)
MAXIMO_SESIONES_POR_CUENTA = 2

MAXIMO_FALLOS = 5
VENTANA_FALLOS = timedelta(minutes=15)
DURACION_BLOQUEO = timedelta(minutes=15)  # decisión T06-02: no fijado en la Fase 1

LONGITUD_MINIMA_CONTRASENA = 12

COOKIE_SESION = "sma_sesion"
COOKIE_CSRF = "sma_csrf"
CABECERA_CSRF = "X-CSRF-Token"
