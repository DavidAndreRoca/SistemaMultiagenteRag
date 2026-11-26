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

La ingesta es reanudable por documento: muestra el avance y el tiempo por etapa, se puede detener con Ctrl+C (el documento en curso se revierte) y se continúa con el mismo comando. La extracción de Docling queda en caché por huella del PDF (`/archivos/extraccion/`), así que volver a segmentar no relee los PDF:

```bash
docker compose -f docker-compose.yml -f docker-compose.corpus.yml run --rm --no-deps api python -m app.corpus.resegmentar --tema TEMA-01 --investigador INV-01            # simulación
docker compose -f docker-compose.yml -f docker-compose.corpus.yml run --rm --no-deps api python -m app.corpus.resegmentar --tema TEMA-01 --investigador INV-01 --aplicar
```

Flujo de desarrollo en un portátil (decisión T10-02):

- **Pruebas diarias:** el subconjunto de 3 PDF por tema, `python scripts/crear_subconjunto_desarrollo.py` (lo copia a `datos/corpus-desarrollo/<tema>/`).
- **Corpus completo:** solo en ejecuciones programadas, con `scripts/ingesta-programada.ps1` (registra la ingesta en `datos/corpus-provisional/` y respalda la base al terminar sin errores). El script explica cómo programarlo; no se registra solo.
- **Respaldo y restauración** de la base con el corpus ingerido y del volumen de archivos (con la caché):

```bash
python scripts/respaldo_corpus.py respaldar
python scripts/respaldo_corpus.py restaurar datos/respaldos/corpus-AAAAMMDD --confirmar
```

Decisiones: `docs/decisiones/T10-indexacion-y-gestion-del-corpus.md` y `docs/decisiones/T10-02-optimizacion-flujo-desarrollo.md`.

## Borradores del caso (T11)

El caso (A1) carga su borrador .docx por hito. Cada carga se valida y crea una versión nueva, vigente en su hito, sin borrar las anteriores. La validación rechaza, con su motivo, los archivos con macros, cifrados, dañados, de otro formato o con contenido comprimido anómalo. El archivo se guarda con nombre aleatorio en el volumen `archivos` y nunca se sirve. Sus párrafos quedan en la base con los identificadores `p1`, `p2`, etc.

Rutas del caso: `POST /caso/versiones` (formulario con `hito` y `archivo`), `GET /caso/versiones` (con `?hito=` opcional) y `GET /caso/versiones/{id}`. Los .docx de prueba de `backend/pruebas/datos/docx/` son ficticios y se regeneran con `python -m pruebas.datos.generar_docx_muestra`. Decisiones: `docs/decisiones/T11-borradores.md`.

Cada carga detecta las secciones por los estilos de título y separa la lista de referencias (T12). Sin estilos, la respuesta pide marcar los títulos a mano. Rutas: `GET /caso/versiones/{id}/secciones` (árbol, párrafos y referencias), `PUT /caso/versiones/{id}/secciones` (títulos marcados a mano) y `PUT /caso/versiones/{id}/referencias` (lista indicada a mano). La validación del alcance de una solicitud por tipo está en `app/borradores/alcance.py`. Decisiones: `docs/decisiones/T12-secciones-y-alcance.md`.

## Interfaz (T13)

Aplicación React con TypeScript y Vite en `frontend/`, con React Aria Components para los controles accesibles (WCAG 2.2 AA). Las herramientas corren en el contenedor de Node 24.22.2, igual que en la CI, porque piden un Node más nuevo que el del equipo de desarrollo.

```bash
docker compose up -d --wait bd api
docker compose --profile interfaz up -d interfaz      # http://127.0.0.1:5173, con /api reenviado a la API
```

Comandos del frontend (desde la raíz del repositorio, en el contenedor):

```bash
docker run --rm -v "$PWD:/repo" -w /repo/frontend node:24.22.2-bookworm-slim npm ci
docker run --rm -v "$PWD:/repo" -w /repo/frontend node:24.22.2-bookworm-slim sh -c "npm run tipos && npm run lint && npm run pruebas && npm run build"
```

- **Cliente de la API:** se genera del contrato y nunca se escribe a mano. Tras cambiar una ruta, ejecute `python -m app.contrato` (escribe `docs/api/openapi.json`) y luego `npm run generar:api` en `frontend/`.
- **Pruebas de extremo a extremo con Playwright y revisión de accesibilidad:** `scripts/e2e.ps1` las ejecuta en un proyecto de Compose aislado que se borra al terminar.

Decisiones: `docs/decisiones/T13-interfaz-base.md`.

## Servicios bibliográficos (T14)

`backend/app/bibliografia/` consulta Crossref, doi.org, Unpaywall y OpenAlex, con un limitador de tasa por servicio, reintentos con espera exponencial y caché en `cache_metadatos`.
- **Resultado:** cada consulta da `encontrado`, `no_encontrado` o `no_comprobable`. Una caída nunca se confunde con una inexistencia (RN-18).
- **Configuración:** el correo del proyecto (`CORREO_POLITE`) y la clave de OpenAlex (`CLAVE_OPENALEX`) van en `.env`. Las tasas, los tiempos y la vigencia de la caché tienen valores por defecto, que se pueden cambiar (ver `.env.example`).
- **Pruebas:** usan respuestas reales grabadas en `backend/pruebas/contrato/respuestas/`, sin el correo ni la clave. Se regraban con `python -m pruebas.contrato.grabar`.

Decisiones: `docs/decisiones/T14-clientes-bibliograficos.md`.

## Importador de referencias del artículo O1 (T15)

En la pantalla `/investigador/importacion`, el investigador elige el tema y sube el artículo O1 (PDF o .docx) o pega una lista de DOI. La importación sigue en segundo plano:
1. extrae las referencias con GROBID y **borra el artículo** en ese momento (RN-19);
2. localiza cada referencia en Crossref u OpenAlex y consulta su acceso abierto en Unpaywall;
3. descarga el PDF si hay un enlace directo y lo indexa con el canal de T09 y T10.

El resto queda pendiente de PDF (el investigador lo sube desde la misma pantalla) o excluido con su motivo. Lo que no se pudo comprobar se reintenta al importar de nuevo, y reimportar no duplica nada.
- **Requisitos:** los mismos de la ingesta del corpus (GROBID, el servicio de modelos y `docker-compose.corpus.yml`), más `CORREO_POLITE` y `CLAVE_OPENALEX`.
- **Pruebas:** usan las respuestas reales de GROBID grabadas en `backend/pruebas/contrato/grobid/` (`python -m pruebas.contrato.grabar_grobid_referencias`) y un artículo O1 ficticio con 24 referencias (`backend/pruebas/datos/articulo_o1.py`).

Decisiones: `docs/decisiones/T15-importador-referencias.md`.

## Adaptador de modelos de lenguaje (T17)

`backend/app/llm/` llama a los modelos detrás de una sola interfaz (`ModeloLenguaje.generar`), con salida estructurada validada localmente con Pydantic.
- **Proveedores:** Groq (`openai/gpt-oss-120b`, esquema estricto), DeepSeek (`deepseek-flash`, solo en desarrollo) y Gemini (`gemini-3.8-flash`) como respaldo, más uno simulado para las pruebas.
- **Respaldo y límites:** pasa al siguiente proveedor solo ante errores de disponibilidad, tras 2 reintentos. Un limitador respeta los límites de cada proveedor (riesgo R-01).
- **Registro:** cada intento queda en `evento_tecnico`, con tokens, duración y costo estimado.
- **Configuración:** las claves (`CLAVE_GROQ`, `CLAVE_DEEPSEEK`, `CLAVE_GEMINI`) y el orden (`PROVEEDORES_MODELO`) van en `.env`. Los modelos, límites y precios están en la configuración versionada. En producción solo se admiten los proveedores de producción (T25).
- **Instrucciones:** archivos versionados en `backend/instrucciones/<agente>/<version>.md` (plantilla en `plantilla.md`). Una versión publicada no se edita: `python -m app.instrucciones registrar <agente>/<version>` fija su huella en `registro.json`.
- **Pruebas de contrato:** respuestas reales grabadas con `python -m pruebas.contrato.grabar_modelos` (una llamada por proveedor con clave).

Decisiones: `docs/decisiones/T17-adaptador-modelos.md`.

## Recuperación y suficiencia (T16)

`backend/app/rag/` recupera la evidencia de una solicitud y decide si alcanza (RF-10):
1. busca solo en las colecciones que el tipo y el caso permiten;
2. combina la búsqueda densa (bge-m3) y la léxica con fusión por rangos recíprocos;
3. reordena los mejores 20 con bge-reranker-v2-m3;
4. toma hasta 8 fragmentos sin superar 2 400 tokens y los numera `F1` a `Fn`.

La suficiencia se decide en dos pasos: primero un umbral (2 fragmentos con puntaje de 0,5 o más) y después el juicio del modelo, con el adaptador de T17. Si la evidencia no alcanza, no se genera nada y la abstención queda registrada (CP-05).
- **Línea base:** con el servicio de modelos y el corpus provisional, solo lectura:

  ```bash
  python -m app.rag.evaluar ../evaluacion/conjuntos/recuperacion-t16.json --salida ../evaluacion/resultados/linea-base-t16.json
  ```

- **Conjunto de consultas:** `evaluacion/conjuntos/recuperacion-t16.json` es un borrador que revisa el equipo.

Decisiones: `docs/decisiones/T16-recuperacion-suficiencia.md`.

## Contrato de agentes y referencias (T18)

- **Agentes:** todo agente (`backend/app/agentes/contrato.py`) recibe el mismo estado de la solicitud, sin historial del caso. Recupera la evidencia (T16), se abstiene si no alcanza y, si alcanza, genera con el adaptador (T17) y el esquema de su tipo (`esquemas.py`).
- **Comprobaciones:** las de esquema (1) y de citas (3) están en `backend/app/verificacion/comprobaciones.py`. Toda cita debe ser un fragmento recuperado para esa solicitud.
- **Referencias:** se arman desde los metadatos guardados, nunca desde el texto de un modelo (RN-17). Con DOI, en la norma del caso por doi.org; sin DOI o si doi.org no responde, con `citeproc-py` y los estilos CSL oficiales de IEEE, APA 7 y Vancouver (`backend/app/bibliografia/estilos/`).

Decisiones: `docs/decisiones/T18-contrato-agentes.md`.

## Búsqueda de evidencia (T19)

El caso escribe una consulta o una afirmación en `/panel/evidencia` y el agente D4 responde con afirmaciones citadas, o se abstiene con "Sin evidencia suficiente".
- **Validación previa:** reglas (longitud, pedidos de redacción completa, consultas vagas) y similitud con bge-m3 contra las fuentes del caso. Una consulta rechazada no se encola y explica qué se puede pedir.
- **Trabajo en segundo plano:** `POST /api/caso/evidencias` responde 202 y la interfaz consulta el avance.
- **Acceso abierto:** solo se recomiendan fuentes con estado OA comprobado (RN-14). Si se cita una que no lo tiene, la respuesta va "Con advertencias" (el reintento llega en T30). Para completar el estado OA del corpus desde Unpaywall, después de un respaldo:

  ```bash
  python -m app.corpus.acceso_abierto --tema TEMA --investigador INV-01 --aplicar
  ```

- **Comportamiento con el modelo real**, bajo demanda y sin escribir en la base:

  ```bash
  python -m app.agentes.evaluar_evidencia ../evaluacion/conjuntos/recuperacion-t16.json --limite 3
  ```

Decisiones: `docs/decisiones/T19-agente-evidencia.md`.

## Verificación de referencias (T20)

El caso pide en `/panel/referencias` la verificación de la lista de referencias de su versión vigente. El informe da el estado de cada referencia y el cruce de las citas del texto con la lista, según la norma del caso (IEEE, APA 7 o Vancouver).
- **Estados:** `verificada`, `con_discrepancias` (con el campo, su valor y el de la fuente), `no_localizada` y `no_comprobable` (un servicio no respondió; nunca se marca como inexistente).
- **Proceso:** GROBID estructura la lista, Crossref y OpenAlex buscan cada obra por DOI o por metadatos y se cruzan las citas. Es determinista: el modelo no decide estados. Solo si se enciende `explicar_discrepancias` en la configuración redacta una frase por discrepancia.
- **Con servicios reales**, bajo demanda y sin escribir en la base:

  ```bash
  python -m app.agentes.evaluar_referencias ../evaluacion/conjuntos/referencias-t20.json
  ```

Decisiones: `docs/decisiones/T20-verificacion-referencias.md`.

## Prototipo navegable

Recorrido de punta a punta del estudiante (entrar, cargar el borrador, buscar evidencia y verificar referencias) con el corpus provisional:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prototipo.ps1
```

Abre http://127.0.0.1:5173. Las cuentas quedan en `datos/demo/credenciales.txt` (fuera de Git) y el guion de 5 minutos está en `docs/demo/guion-prototipo.md`.

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
