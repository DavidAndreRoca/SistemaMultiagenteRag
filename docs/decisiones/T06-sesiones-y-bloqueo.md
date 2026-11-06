# T06-01. Sesiones, límite de sesiones, bloqueo y CSRF

**Estado:** Vigente (decisión técnica nueva, fase T06)

## Decisiones

1. **Tercera sesión simultánea: se invalida la más antigua** (no se rechaza la nueva). Así un estudiante que olvidó cerrar sesión en otro equipo no queda bloqueado; la sesión cerrada queda con `motivo_cierre = 'limite'`.
2. **Duración del bloqueo: 15 minutos** tras 5 fallos dentro de una ventana de 15 minutos. La Fase 1 fija los 5 intentos en 15 minutos pero no la duración del bloqueo.
3. **Mensaje único de credenciales** ("Código o contraseña incorrectos. Si superó cinco intentos, espere 15 minutos.") para cuenta inexistente, contraseña errónea, cuenta bloqueada o caso desactivado; con cuenta inexistente se verifica contra un hash señuelo para igualar el tiempo de respuesta.
4. **Token de sesión** aleatorio de 256 bits en cookie `HttpOnly`, `Secure`, `SameSite=Lax`; en la base solo se guarda su SHA-256.
5. **CSRF por doble envío firmado**: cookie `sma_csrf` (legible por la interfaz) con `HMAC(SECRETO_SESION, token)`; toda operación que modifica datos exige la cabecera `X-CSRF-Token` con ese valor.
6. **Cambio de contraseña**: mínimo 12 caracteres, distinta del código y de la actual; cierra las demás sesiones de la cuenta (`motivo_cierre = 'contrasena'`).
7. **Primera cuenta de investigador** por línea de comandos (`python -m app.seguridad.crear_investigador CODIGO`), porque no hay registro abierto de usuarios (apartado 9).
