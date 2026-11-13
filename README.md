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

Este paso también aplica las migraciones de Alembic (servicio `migrar`) antes de arrancar la API.

Compruebe la API:

```bash
curl http://127.0.0.1:8000/salud
```

La respuesta esperada es `{"estado":"ok","version":"0.1.0","base_de_datos":true,"extension_vector":"..."}`. La documentación OpenAPI interactiva está en `http://127.0.0.1:8000/docs` fuera de producción.

Ejecute toda la suite (unitarias e integración con PostgreSQL real, con cobertura mínima del 70 %):

```bash
docker compose run --rm --build pruebas
```

Para detener los servicios:

```bash
docker compose down
```

Añada `-v` para borrar también el volumen de la base.

Las pruebas de integración crean su propia base temporal (`sma_prueba_...`) en el mismo servidor y la borran al terminar: no modifican la base de desarrollo.

## Base de datos, cuentas y datos ficticios

Esquema: modelos ORM en `backend/app/bd/modelos/` y migraciones en `backend/migraciones/versiones/`. El diccionario de datos `docs/diccionario-de-datos.md` se genera desde los modelos; tras cambiar un modelo, cree la migración y regenere el diccionario (una prueba falla si no coincide):

Desde `backend/`, con el entorno virtual y la base de Compose en marcha (use la clave de su `.env`):

```bash
URL_BD=postgresql+psycopg://sma:CLAVE@127.0.0.1:5432/sma alembic revision --autogenerate -m "descripcion"
```

```bash
python -m app.bd.diccionario
```

No hay registro abierto de usuarios. La primera cuenta de investigador (A2) se crea por línea de comandos; la contraseña inicial se muestra una sola vez y debe cambiarse al entrar:

```bash
docker compose run --rm --no-deps api python -m app.seguridad.crear_investigador INV-01
```

Para desarrollo, cargue datos ficticios (un investigador, un tema y dos casos; no funciona en producción):

```bash
docker compose run --rm --no-deps api python -m app.bd.semillas
```

Rutas principales (contrato completo en `/docs`): `POST /sesion` (iniciar), `GET /sesion`, `DELETE /sesion`, `POST /sesion/contrasena`, `GET /caso` y las rutas `/investigador/...` para colecciones científicas, casos, desactivación y norma de citación. Toda operación que modifica datos exige la cabecera `X-CSRF-Token` con el valor `csrf` que devuelve el inicio de sesión.

## Configuración

Toda la configuración sale de variables de entorno validadas al arrancar. Si falta una obligatoria, la aplicación no arranca y nombra la variable. Las variables y su obligatoriedad por entorno están en `.env.example`.

| Entorno | Obligatorias |
| --- | --- |
| `pruebas` | `ENTORNO`, `URL_BD`, `SECRETO_SESION` |
| `desarrollo` | las anteriores (secreto de 32 caracteres o más) y `CORREO_POLITE` |
| `produccion` | las de desarrollo y `CLAVE_OPENALEX` |

Los parámetros funcionales (umbrales, normas de citación, modelos) no son variables de entorno: vivirán en la configuración versionada (T04 y T35).

## Servicios compartidos: GROBID y modelos de embeddings y reranking (T08)

GROBID y el servicio de modelos (`servicio_modelos/`, con bge-m3 y bge-reranker-v2-m3 en CPU) corren una sola vez por servidor, en el proyecto de Compose `compartido`. La primera vez:

```bash
cp compartido/.env.example compartido/.env
```

```bash
docker compose -f compartido/docker-compose.yml --profile descarga run --rm --build descargar_modelos
```

La descarga baja unos 4,6 GB de pesos, con revisiones fijas y huellas verificadas, al volumen `sma_modelos`. Después:

```bash
docker compose -f compartido/docker-compose.yml up -d --wait
```

El servicio de modelos responde en `http://127.0.0.1:8001` (`/embeber`, `/reordenar`, `/salud`) y GROBID en `http://127.0.0.1:8070`. Necesitan unos 6 GB de memoria entre los dos. Las pruebas con los pesos reales (determinismo, memoria y tiempo) se ejecutan bajo demanda:

```bash
docker compose -f compartido/docker-compose.yml --profile pruebas run --rm --build pruebas_modelos
```

Las pruebas de la API contra los servicios en marcha también se ejecutan bajo demanda. Desde `backend/`, con el entorno virtual:

```bash
URL_SERVICIO_MODELOS_PRUEBAS=http://127.0.0.1:8001 URL_GROBID_PRUEBAS=http://127.0.0.1:8070 pytest -m servicios_compartidos
```

Decisiones y mediciones: `docs/decisiones/T08-servicios-compartidos.md`.

## Canal de extracción de PDF (T09)

`app/corpus/` convierte un PDF de artículo en fragmentos IMRaD con sección, título original, páginas y tokens, más los metadatos de cabecera de GROBID, sin tocar la base (`procesar_pdf` en `extraccion.py`). Docling y el tokenizador de bge-m3 van en el extra `corpus` de `backend/pyproject.toml`; la imagen de la API y la de pruebas lo instalan con el árbol fijado (`backend/restricciones-corpus.txt`, PyTorch en CPU).

Los recursos del canal (modelo de diseño de página de Docling y tokenizador) se descargan una vez, con revisión y huella verificadas, al volumen `recursos_corpus`:

```bash
docker compose --profile pruebas run --rm --no-deps pruebas python -m app.corpus.recursos /recursos
```

Con eso, `docker compose run --rm --build pruebas` incluye las pruebas del canal con Docling real (marca `corpus`). Los PDF de muestra de `backend/pruebas/datos/pdf/` son ficticios y se regeneran con `python -m pruebas.datos.generar_pdf_muestra`. Decisiones: `docs/decisiones/T09-extraccion-y-segmentacion.md`.

## Indexación del corpus científico (T10)

La API indexa PDF en la colección científica de un tema: los guarda con nombre aleatorio en el volumen `archivos` (nunca los sirve), los embebe con el servicio de modelos y registra con su motivo lo que excluye (escaneados, ilegibles, cifrados, duplicados). Para alcanzar GROBID y el servicio de modelos, la API se une a la red de los servicios compartidos con `docker-compose.corpus.yml`:

```bash
docker compose -f docker-compose.yml -f docker-compose.corpus.yml up -d --wait bd api
```

Rutas del investigador: `GET /investigador/colecciones` (con el `id` de cada colección), `GET` y `POST /investigador/colecciones/{id}/documentos` (subir un PDF), `GET /investigador/colecciones/{id}/exclusiones`, y `POST /investigador/documentos/{id}/confirmar` y `/retirar`.

Ingesta en lote de una carpeta (idempotente: puede repetirse) y reindexación si cambia el modelo de embeddings:

```bash
docker compose -f docker-compose.yml -f docker-compose.corpus.yml run --rm --no-deps -v /ruta/a/los/pdf:/entrada:ro api python -m app.corpus.ingesta /entrada --tema TEMA-01 --investigador INV-01
```

```bash
docker compose -f docker-compose.yml -f docker-compose.corpus.yml run --rm --no-deps api python -m app.corpus.reindexar --investigador INV-01
```

Decisiones: `docs/decisiones/T10-indexacion-y-gestion-del-corpus.md`.

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

`.github/workflows/ci.yml` ejecuta: análisis (Ruff), tipado (mypy estricto), pruebas con PostgreSQL con pgvector y cobertura mínima de 70 %, escaneo de dependencias (`pip-audit`), escaneo de secretos (gitleaks), el servicio de modelos (T08) y el canal de PDF con Docling real y su árbol fijado (T09).
