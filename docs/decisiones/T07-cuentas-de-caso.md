# T07-01. Códigos de cuenta de los casos

**Estado:** Vigente (decisión técnica nueva, fase T07)

* La cuenta de un caso individual es `<CODIGO>-1`; un caso en pareja tiene `<CODIGO>-1` y `<CODIGO>-2`.
* Los códigos se normalizan a mayúsculas y solo admiten mayúsculas, dígitos, guion y guion bajo (sin datos personales, RN-12).
* La contraseña inicial tiene 16 caracteres aleatorios (96 bits), se devuelve una sola vez en la respuesta del alta y se guarda solo como hash Argon2id.
* Desactivar un caso cierra de inmediato las sesiones abiertas de sus cuentas e impide iniciar sesión; reactivarlo no cambia sus contraseñas.
* Cambiar la norma a la misma que ya tiene no registra un cambio.
