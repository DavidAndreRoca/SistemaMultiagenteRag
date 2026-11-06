# T03-01. Validación de configuración por entorno

**Estado:** Vigente (decisión técnica nueva, fase T03)

## Contexto

La hoja de ruta (4.3) exige validar variables al arrancar y negarse a iniciar si falta una obligatoria, sin precisar cuáles lo son en cada entorno.

## Decisión

* Obligatorias siempre: `ENTORNO`, `URL_BD`, `SECRETO_SESION`.
* `desarrollo` y `produccion`: además `CORREO_POLITE`; secreto de al menos 32 caracteres.
* `produccion`: además `CLAVE_OPENALEX`.
* Las claves de modelos (`CLAVE_GROQ`, `CLAVE_DEEPSEEK`, `CLAVE_GEMINI`) son opcionales para arrancar. El comando `python -m app.diagnostico` exige y prueba Groq y OpenAlex. El rechazo de proveedores gratuitos en producción corresponde a T17.
* `Ajustes` es un modelo Pydantic y no `BaseSettings`: `cargar_ajustes` decide el origen (`os.environ` o un diccionario inyectado). Con `BaseSettings` las pruebas dejaban de ser herméticas (se detectó al ejecutarlas en contenedor).

## Consecuencias

Arrancar la API en desarrollo no requiere cuentas externas activas. Si la hoja de ruta exige más obligatorias en un entorno, se añaden en `Ajustes._validar_por_entorno`.
