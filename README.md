# Sistema multiagente con RAG para artículos científicos empíricos

Proyecto de Taller de Investigación (UTP, Ica). Este repositorio sigue `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`; el avance verificado está en `docs/ESTADO_DESARROLLO.md`.

## Requisitos

- Docker con Compose v2 (en Windows, Docker Desktop en ejecución).
- Git.

No hace falta instalar Python: el código se ejecuta y se prueba dentro de contenedores con Python 3.12.

## Levantar los servicios y ejecutar las pruebas

Desde la raíz del repositorio:

```bash
cp .env.example .env
```

Edite `.env` y complete como mínimo `SECRETO_SESION` (32 caracteres o más) y `CORREO_POLITE`. Puede generar un secreto con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Si no tiene Python, use cualquier cadena aleatoria de 32 caracteres o más. Luego:

```bash
docker compose up -d --wait bd api
```

Compruebe la API:

```bash
curl http://127.0.0.1:8000/salud
```

La respuesta esperada es `{"estado":"ok","version":"0.1.0","base_de_datos":true,"extension_vector":"..."}`. La documentación OpenAPI interactiva está en `http://127.0.0.1:8000/docs` fuera de producción.

Ejecute toda la suite (unitarias e integración con PostgreSQL real, con cobertura mínima del 70 %):

```bash
docker compose run --rm pruebas
```

Para detener los servicios:

```bash
docker compose down
```

Añada `-v` para borrar también el volumen de la base.

## Configuración

Toda la configuración sale de variables de entorno validadas al arrancar. Si falta una obligatoria, la aplicación no arranca y nombra la variable. Las variables y su obligatoriedad por entorno están en `.env.example`.

| Entorno | Obligatorias |
| --- | --- |
| `pruebas` | `ENTORNO`, `URL_BD`, `SECRETO_SESION` |
| `desarrollo` | las anteriores (secreto de 32 caracteres o más) y `CORREO_POLITE` |
| `produccion` | las de desarrollo y `CLAVE_OPENALEX` |

Los parámetros funcionales (umbrales, normas de citación, modelos) no son variables de entorno: vivirán en la configuración versionada (T04 y T35).

## Diagnóstico de claves externas

Con las claves cargadas en el entorno, prueba con una llamada mínima Groq y OpenAlex sin imprimir ninguna clave:

```bash
docker compose run --rm --no-deps api python -m app.diagnostico
```

## Desarrollo local sin contenedores (opcional)

Desde `backend/`, con Python 3.12 o superior y un entorno virtual:

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy
pytest
```

Las pruebas de integración se omiten si no está definida `URL_BD_PRUEBAS` (en la integración continua su ausencia es un fallo).

## Servidor de desarrollo compartido

Ver `docs/operacion/servidor-desarrollo.md` (T01).

## Integración continua

`.github/workflows/ci.yml` ejecuta: análisis (Ruff), tipado (mypy estricto), pruebas con PostgreSQL con pgvector y cobertura mínima de 70 %, escaneo de dependencias (`pip-audit`) y escaneo de secretos (gitleaks).
