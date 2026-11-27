# Estado del desarrollo

Registro del avance **verificado** frente a `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`. Solo se marca como cumplido lo que se comprobó con una prueba o un comando cuyo resultado se anota aquí.

**Última actualización:** 26 de noviembre de 2026. Prototipo navegable (apartado 24). T20 integrada en `main` (solicitud de cambio #16, apartado 23.7). T19 integrada en `main` (solicitud de cambio #15, apartado 22.7). T18 integrada en `main` (solicitud de cambio #14, apartado 21.7). T16 integrada en `main` (solicitud de cambio #13, apartado 20.7). T17 integrada en `main` (solicitud de cambio #12, apartado 19.7). T15 integrada en `main` (solicitud de cambio #11, apartado 18.7). T11 y T12 integradas en `main` (solicitudes de cambio #7 y #8, apartados 14.7 y 15.7). T13 integrada en `main` (solicitud de cambio #9, apartado 16.7). T14 integrada en `main` (solicitud de cambio #10, apartado 17.7). Fase 2 (T04 a T07) integrada en `main` (solicitud de cambio #1, apartado 10.10). T08 integrada en `main` (solicitud de cambio #2, apartado 11.7). T09 integrada en `main` (solicitud de cambio #4, apartado 12.8). T10 integrada en `main` (solicitud de cambio #5, apartado 13.7); su actividad 7, el corpus provisional (apartado 13.8), y la optimización del flujo de desarrollo (apartado 13.9, decisión T10-02), integradas en `main` (solicitud de cambio #6, apartado 13.10).

## Resumen

| Fase | Nombre | Estado |
| --- | --- | --- |
| T00 (F0) | Cuentas, accesos y secretos | Fuera de esta sesión: lo realizan los integrantes. Sin verificar |
| **T01 (F1)** | Servidor de desarrollo en Oracle | **Parcial**: documentación y verificación de imágenes ARM hechas; la instancia no existe aún |
| **T02 (F1)** | Repositorio, calidad de código e integración continua | **Implementada**; el repositorio está en GitHub (`DavidAndreRoca/SistemaMultiagenteRag`). La CI de `84f444c` terminó en verde (ejecución 42281717057). Falta la protección de la rama principal (T00) |
| **T03 (F1)** | Infraestructura base de la aplicación (H0) | **Completa y verificada** (criterios de aceptación cumplidos) |
| **T04 (F2)** | Modelo de datos, diccionario y migraciones | **Completa y verificada**. Contrastada con la especificación de la Fase 1 y la ficha de métricas (migraciones 0005 y 0006, apartado 10.9). Queda provisional tau = 0.5 hasta T34 |
| **T05 (F2)** | Repositorios con aislamiento por caso | **Completa y verificada** |
| **T06 (F2)** | Autenticación, roles y sesiones | **Completa y verificada** |
| **T07 (F2)** | Casos, temas, colecciones y cuentas | **Completa y verificada** (CP-22 superado) |
| **T08 (F3)** | Servicios de procesamiento compartidos | **Implementada, verificada en local e integrada en `main`** (solicitud de cambio #2, apartado 11.7). Criterio "responden en ARM": GROBID sí en emulación; el servicio de modelos queda pendiente de la instancia real por una limitación del emulador (apartado 11) |
| **T09 (F3)** | Extracción y segmentación de documentos | **Implementada, verificada e integrada en `main`** (solicitud de cambio #4, apartado 12.8), con Docling y GROBID reales; criterios de aceptación cumplidos (apartado 12). La lectura de RN-16 sobre PDF que solo restringen permisos quedó confirmada el 19 de noviembre de 2026 (apartado 12.7) |
| **T10 (F3)** | Indexación y gestión del corpus | **Integrada en `main`** (apartado 13.7). **Actividad 7 cumplida e integrada** (solicitud de cambio #6, apartado 13.10): corpus provisional de 2 temas ingerido (99 documentos indexados), sin referencias en los fragmentos y sin fragmentos ajenos al tema en las consultas de prueba (apartado 13.8). Flujo de desarrollo optimizado (apartado 13.9) |
| **T11 (F3)** | Borradores: carga, validación y versiones | **Integrada en `main`** (solicitud de cambio #7, apartado 14.7). CP-01 y CP-02 superados y contrastados con la Tabla 20 de la tesis (apartado 14) |
| **T12 (F3)** | Secciones del borrador y alcance | **Integrada en `main`** (solicitud de cambio #8, apartado 15.7); criterios cumplidos y CP-09 contrastado con la tesis (apartado 15) |
| **T13 (F3)** | Interfaz base | **Integrada en `main`** (solicitud de cambio #9, apartado 16.7): criterios cumplidos con Playwright frente a la API real, también en la CI (apartado 16). Prueba manual con teclado y NVDA superada según el equipo (apartado 16.5) |
| **T14 (F3)** | Clientes bibliográficos con limitador y caché | **Integrada en `main`** (solicitud de cambio #10, apartado 17.7), con respuestas reales grabadas de los cuatro servicios; criterios cumplidos (apartado 17) |
| **T15 (F3)** | Importador de referencias del artículo O1 | **Integrada en `main`** (solicitud de cambio #11, apartado 18.7), verificada con servicios simulados y con un artículo base real en un proyecto aislado; criterios cumplidos y RN-19 comprobado en disco y en la base (apartado 18) |
| **T17 (F3)** | Adaptador de modelos de lenguaje e instrucciones versionadas | **Integrada en `main`** (solicitud de cambio #12, apartado 19.7), verificada con proveedores simulados; criterios cumplidos (apartado 19). Faltan las grabaciones de contrato reales, que esperan las claves (apartado 19.5) |
| **T16 (F3)** | Recuperación híbrida y suficiencia | **Integrada en `main`** (solicitud de cambio #13, apartado 20.7); criterios cumplidos y línea base registrada: precisión contextual 0,68 y exhaustividad 0,80 (apartado 20). El conjunto de consultas está en borrador, a revisar por el equipo |
| **T18 (F3)** | Contrato común de agentes y comprobaciones deterministas | **Integrada en `main`** (solicitud de cambio #14, apartado 21.7); criterios cumplidos (apartado 21) |
| **T19 (F3)** | Agente D4: búsqueda de evidencia | **Integrada en `main`** (solicitud de cambio #15, apartado 22.7), verificada con modelo simulado y una ejecución con Groq; criterios cumplidos (apartado 22). Los conjuntos del equipo siguen pendientes |
| **T20 (F3)** | Agente D4: verificación de referencias | **Integrada en `main`** (solicitud de cambio #16, apartado 23.7), verificada con servicios simulados y con GROBID, Crossref y OpenAlex reales; criterios cumplidos (apartado 23). El conjunto de prueba está en borrador, a revisar por el equipo |
| **Prototipo** | Recorrido demostrable de punta a punta | **Hecho en local** (apartado 24): `scripts/prototipo.ps1` y guion en `docs/demo/guion-prototipo.md`. Datos de demostración provisionales, sin revisión humana |
| T21 | Ensayo de despliegue en Oracle | Pospuesta: la demostración es local (apartado 24) |
| **T22 y T23** | Corpus de guías y agente de estructura (D1) | **Hechas** (apartado 25), con guías provisionales |
| T24 a T33 | Plan de tarea, agentes D2 y D3, orquestador, verificador, decisiones, aportes e historial | Reactivadas, pendientes |
| T34 en adelante | | No iniciadas; T34 y T38 al final, con revisión del equipo |

**Interpretación de las fases:** la hoja de ruta (apartado 5) hace corresponder F1 con T01 a T03 y F2 con T04 a T07. T00 (F0) es administrativa y no la puede hacer el asistente. El detalle de la Fase 2 está en el apartado 10.

---

## 1. Inventario inicial (T02, actividad 1)

Al comenzar, la carpeta del proyecto solo contenía `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`. No había código, ni repositorio Git, ni `ESTADO_DESARROLLO.md`. No hubo implementación previa que reutilizar.

Entorno de la máquina de trabajo: Windows 11, Docker 27.5.1 (amd64), Git 2.46, Node.js 22.13.1, Python 3.13 en el anfitrión. Por eso **todo se ejecuta y se prueba en contenedores con Python 3.12**, igual que la integración continua.

---

## 2. T01. Servidor de desarrollo en Oracle

### Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Crear la instancia ARM | **Pendiente**: en trámite con Oracle (incidente 261107-001540) | |
| 2. Endurecer SSH (solo llave) | **Pendiente**; procedimiento documentado | `docs/operacion/servidor-desarrollo.md`, apartado 2 |
| 3. Usuarios Linux por integrante | **Pendiente**; procedimiento documentado | idem, apartado 3 |
| 4. Instalar Docker, Compose, Git, Python 3.12, Node LTS, Claude Code | **Pendiente**; script de verificación listo | `scripts/verificar-herramientas.sh` |
| 5. Documentar conexión e inactividad | **Hecha** | `docs/operacion/servidor-desarrollo.md` |
| Tarea: verificar imágenes ARM | **Hecha** | `scripts/verificar-imagenes-arm.sh` |
| Tarea: Compose `compartido` y bases por integrante | Documentado; el `docker-compose.yml` admite nombre de proyecto y puertos por integrante | `.env.example` (`COMPOSE_PROJECT_NAME`, `PUERTO_BD`, `PUERTO_API`) |

### Hallazgo: GROBID sin arm64 en la serie 0.8.x (riesgo R-03)

La consulta de manifiestos mostró que `grobid/grobid:0.8.x` (todas sus variantes), `0.9.0` y `0.9.1-full` son **solo amd64**. Solo `grobid/grobid:0.9.0-crf` y `0.9.1-crf` publican arm64. Quedó registrado en `docs/decisiones/T01-grobid-arm64.md`. Los autores **confirmaron** usar `0.9.1-crf` el 6 de noviembre de 2026, y su calidad se mide en T09.

### Criterios de aceptación

| Criterio | Estado |
| --- | --- |
| Ambos integrantes entran por SSH con su usuario | Pendiente |
| `docker run` de PostgreSQL con pgvector en ARM | Pendiente en ARM. La imagen publica arm64 (verificado) y funciona en amd64 local |
| Claude Code se inicia en la carpeta de cada usuario | Pendiente |
| (De T08) GROBID 0.9.1-crf y el servicio de modelos responden en la instancia ARM, y la memoria de los servicios compartidos más dos bases cabe sin intercambio | Pendiente. En emulación arm64, GROBID respondió y el servicio de modelos falló por una limitación del emulador (`docs/decisiones/T08-emulacion-arm64.md`). Se comprueba en cuanto Oracle entregue la instancia (incidente 261107-001540) |

---

## 3. T02. Repositorio, calidad de código e integración continua

### Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Inventario del repositorio | Hecha | Apartado 1 de este documento |
| 2. Estructura de primer nivel y README | Hecha | `backend/`, `frontend/`, `servicio_modelos/`, `evaluacion/`, `datos/` (excluida de Git), `docs/`, `README.md` |
| 3. `CLAUDE.md` | Hecha | `CLAUDE.md` |
| 4. Copiar especificaciones, `ESTADO`, decisiones D-01 a D-15 | **Parcial** | Hechos: este archivo y `docs/decisiones/D-01.md` a `D-15.md`. Faltan: la *Especificación técnica de la Fase 1* y la *Fase 2* no están en la carpeta del proyecto (carpetas `docs/especificacion-fase1/` y `docs/hoja-de-ruta-fase2/` listas). D-11 y D-13 quedan "pendientes de transcripción" porque la hoja de ruta no reproduce su contenido |
| 5. `pyproject.toml` con Ruff, mypy, pytest y cobertura | Hecha | `backend/pyproject.toml` |
| 6. Flujo de integración continua | Hecha | `.github/workflows/ci.yml` |
| Plantilla de solicitud de cambio con la definición de terminado | Hecha | `.github/pull_request_template.md` |
| `.gitignore` (`.env`, `datos/`, cachés de modelos, artefactos) | Hecha | `.gitignore` |
| Protección de rama principal | **Pendiente** (requiere el repositorio en GitHub, T00) | |

**Trabajos de la integración continua:** análisis (Ruff check y format), tipado (mypy estricto), pruebas con servicio PostgreSQL con pgvector y cobertura mínima de 70 %, escaneo de dependencias (`pip-audit`) y escaneo de secretos (gitleaks por imagen oficial, ver `docs/decisiones/T02-escaneo-de-secretos-con-imagen.md`).

### Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Una solicitud de cambio con una prueba que falla queda bloqueada | **Verificado en local; pendiente en GitHub** | Con una prueba `assert 1 == 2` añadida, pytest sale con código 1, lo que hace fallar el trabajo `pruebas`. El bloqueo efectivo requiere la protección de rama con verificaciones obligatorias |
| Una solicitud de cambio con un secreto simulado es detectada | **Verificado en local; pendiente en GitHub** | gitleaks v8.21.2 sobre una copia con una clave AWS de ejemplo: `leaks found: 1`, código 1. Sobre el repositorio real: `no leaks found`, código 0 |
| La integración continua termina en verde con el repositorio vacío | **Cumplido en GitHub** | Los cinco trabajos pasan en GitHub Actions: en la publicación de `84f444c` en `main` (ejecución 42281717057) y en la solicitud de cambio #1 (ejecuciones 42308914645 y 42309565158) |

---

## 4. T03. Infraestructura base de la aplicación (H0)

### Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. `docker-compose.yml` con PostgreSQL 16 con pgvector y volumen | Hecha | Servicio `bd` (`pgvector/pgvector:pg16`, volumen `datos_bd`, extensión creada al iniciar) |
| 2. FastAPI con `configuracion/`, `comun/errores.py`, `comun/registro.py` | Hecha | `backend/app/` |
| 3. `GET /salud` (base, extensión `vector`, versión) | Hecha | `backend/app/api/salud.py` |
| 4. Formato único de error y manejadores globales | Hecha | `backend/app/comun/errores.py`, `middleware.py` |
| 5. OpenAPI en desarrollo | Hecha | `/docs` y `/openapi.json` fuera de producción; ocultos en `produccion` |
| 6. Comando de diagnóstico de claves de Groq y OpenAlex | Hecha | `python -m app.diagnostico` |
| Configuración validada por `ENTORNO` | Hecha | `docs/decisiones/T03-configuracion-por-entorno.md` |
| Sesión asíncrona (SQLAlchemy 2 + psycopg 3) creada al arrancar y cerrada al apagar | Hecha | `backend/app/bd/sesion.py`, `lifespan` en `main.py` |
| Middleware con `incidencia_id` en registro y respuestas de error | Hecha | Cabecera `X-Incidencia-Id` |
| Cabeceras de seguridad básicas | Hecha | `nosniff`, `DENY`, `no-referrer`, `Permissions-Policy`, `COOP`, CSP de API; HSTS en producción |

### Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Siguiendo solo el README, en una copia limpia, se levantan los servicios y pasan las pruebas | **Cumplido** | Copia limpia de los archivos versionables en una carpeta temporal; se siguieron los pasos del README: `/salud` respondió HTTP 200 `{"estado":"ok",...,"extension_vector":"0.8.7"}` y `docker compose run --rm pruebas` dio 31 pruebas superadas |
| Sin una variable obligatoria, la aplicación no arranca y lo informa | **Cumplido** | `docker compose run -e SECRETO_SESION= api` muestra `faltan variables obligatorias para el entorno desarrollo: SECRETO_SESION` y sale con código 1 (igual con `CORREO_POLITE`). Más pruebas unitarias |
| `GET /salud` responde con la base conectada y la extensión vectorial | **Cumplido** | Prueba de integración y `curl` contra la API en Compose |

**Pendiente de T03 que depende de T00:** comprobar con claves reales que Groq y OpenAlex responden. El comando funciona y sin claves informa `[FALLA] ... no está configurada` con código 1, pero en esta sesión no hay claves (y no deben estar aquí).

---

## 5. Pruebas ejecutadas

Suite: `docker compose run --rm pruebas` (Python 3.12.16, PostgreSQL 16 con pgvector 0.8.7).

| Archivo | Qué cubre | Resultado |
| --- | --- | --- |
| `unitarias/test_configuracion.py` | Obligatorias por entorno, secretos fuera de `repr` y mensajes, entorno inválido | Superadas |
| `unitarias/test_arranque.py` | La fábrica y `python -m app` no arrancan sin variables | Superadas |
| `unitarias/test_errores_y_middleware.py` | Formato común en 500 (ruta que falla a propósito), 404, 403, 409 y 422; `incidencia_id`; cabeceras de seguridad; OpenAPI solo fuera de producción; registro JSON sin contenido | Superadas |
| `unitarias/test_diagnostico.py` | Groq y OpenAlex simulados (válida, rechazada, ausente, sin red); la clave nunca se imprime | Superadas |
| `unitarias/test_salud_sin_base.py` | `/salud` con base inalcanzable devuelve 503 sin filtrar la URL | Superada |
| `integracion/test_salud.py` | `/salud` con base real; `vector(1024)` y distancia coseno | Superadas |

**Total: 31 superadas, 0 fallidas. Cobertura de `app/`: 93,5 %** (mínimo 70 %).

Otras verificaciones: `ruff check` y `ruff format --check` sin errores; `mypy` estricto sin errores (15 archivos); `pip-audit` sin vulnerabilidades conocidas; gitleaks sin hallazgos; `actionlint` sin errores; `scripts/verificar-imagenes-arm.sh` con código 0.

---

## 6. Problemas encontrados y soluciones

| Problema | Solución |
| --- | --- |
| La traza del registro de errores incluía la línea de código fuente y, con ella, literales con datos (lo detectó una prueba) | La traza registra solo archivo, línea y función, nunca el mensaje de la excepción |
| Con `BaseSettings`, las pruebas que inyectan variables leían también las del contenedor (3 fallos solo en Docker) | `Ajustes` pasa a ser un modelo Pydantic; `cargar_ajustes` decide el origen. Se retira la dependencia `pydantic-settings` |
| `pip-audit`: pytest 8.4.2 con PYSEC-2026-1845 | Cota a `pytest>=9.0.3,<10` |
| `pip-audit`: el `pip` 25.0.1 de la imagen base tenía 6 avisos distintos | La imagen y la CI actualizan `pip>=26.2` antes de instalar |
| Ruff clasificaba `app` como paquete externo | `src = ["."]` en `pyproject.toml` |
| `docker compose up --wait` volvía antes de que la API escuchara | Healthcheck de `api` contra `/salud` |
| GROBID sin arm64 en 0.8.x | Decisión propuesta `docs/decisiones/T01-grobid-arm64.md` (a confirmar) |
| `gitleaks-action` exige licencia en organizaciones | Imagen oficial de gitleaks con versión fijada |

---

## 7. Desviaciones respecto de la hoja de ruta (registradas, no arbitrarias)

* **Ubicación de este archivo:** la hoja de ruta lo nombra `docs/hoja-de-ruta-tecnica/ESTADO.md`. Se usa `docs/ESTADO_DESARROLLO.md` por indicación expresa de los autores, y la hoja de ruta se dejó en su ubicación actual sin modificarla.
* **Python del anfitrión:** 3.13 en Windows; la ejecución oficial (contenedores y CI) usa 3.12, como fija D-01.
* **Commit y repositorio remoto:** se inicializó Git localmente (rama `main`) **sin confirmaciones**; la publicación en la organización de GitHub depende de T00.

## 8. Pendientes para cerrar formalmente F1 (T01 a T03)

1. T00: organización y repositorio en GitHub, claves de Groq y OpenAlex, cuentas de Oracle.
2. Primera confirmación, envío a GitHub, protección de `main` con los cinco trabajos de CI obligatorios, y las dos solicitudes de cambio de control (prueba que falla y secreto simulado).
3. T01 en la instancia: crearla, endurecer SSH, crear usuarios, instalar herramientas y ejecutar `scripts/verificar-herramientas.sh` como cada integrante.
4. Ejecutar `python -m app.diagnostico` con las claves reales.
5. Confirmar la decisión de GROBID para ARM (`docs/decisiones/T01-grobid-arm64.md`).
6. Copiar la Especificación de la Fase 1 y la Fase 2 a `docs/`, y transcribir D-11 y D-13.

## 9. Archivos creados

Raíz: `CLAUDE.md`, `README.md`, `docker-compose.yml`, `.env.example`, `.gitignore`, `.gitattributes`, `.github/workflows/ci.yml`, `.github/pull_request_template.md`, `docker/postgres/01-extension-vector.sql`, `scripts/verificar-imagenes-arm.sh`, `scripts/verificar-herramientas.sh`, y `.gitkeep` en `frontend/`, `servicio_modelos/`, `evaluacion/`, `docs/api/`, `docs/especificacion-fase1/` y `docs/hoja-de-ruta-fase2/`.

Backend: `backend/pyproject.toml`, `backend/Dockerfile`, `backend/.dockerignore`, `backend/app/{__init__,__main__,main,diagnostico}.py`, `backend/app/configuracion/{__init__,ajustes}.py`, `backend/app/comun/{__init__,contexto,errores,middleware,registro}.py`, `backend/app/bd/{__init__,sesion}.py`, `backend/app/api/{__init__,salud}.py`, `backend/pruebas/conftest.py` y los seis archivos de prueba del apartado 5.

Documentación: `docs/ESTADO_DESARROLLO.md`, `docs/operacion/servidor-desarrollo.md`, `docs/decisiones/D-01.md` a `D-15.md`, `T01-grobid-arm64.md`, `T02-escaneo-de-secretos-con-imagen.md`, `T03-configuracion-por-entorno.md`, `T03-estado-de-salud-y-errores.md`.

Archivos modificados: ninguno preexistente (`docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md` sin cambios).

---

## 10. Fase 2 (F2): T04 a T07

Integrado en `main` (confirmación `9b18700`, integración `7a569a0`) mediante la solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#1, con la CI en verde (apartado 10.10). Verificación local en un contenedor con Python 3.12.16 y PostgreSQL 16 con pgvector 0.8.7.

### 10.1. T04. Modelo de datos, diccionario y migraciones

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Diccionario de datos | Hecha | `docs/diccionario-de-datos.md`, generado desde los modelos con `python -m app.bd.diccionario`; una prueba falla si se desalinea |
| 2. Revisión contra la ficha de métricas, RF-17 y RNF-02 | Hecha (10.9) | RNF-02 verificado (prueba de columnas prohibidas). La columna "Alimenta" usa los códigos M1 a M6 de la ficha, y el diccionario termina con el índice de métrica a columnas |
| 3. Modelos ORM | Hecha | `backend/app/bd/modelos/`: las 15 tablas de T04, más `sesion` (T06) y `cambio_norma` (T07) |
| 4. Migración inicial y semilla de configuración | Hecha | `0001_modelo_de_datos_inicial.py` (con `CREATE EXTENSION vector`) y `0002_semilla_configuracion.py` |
| 5. Semillas ficticias de desarrollo | Hecha | `python -m app.bd.semillas` (idempotente; se niega a ejecutarse en producción) |
| Índices por `caso_id` en las tablas de caso y por `coleccion_id` en fragmento | Hecha | `test_tablas_de_caso_tienen_caso_id_indexado`, `test_fragmento_indexado_por_coleccion` |
| Índice parcial de la cola sobre `solicitud.estado` | Hecha | `ix_solicitud_cola` |
| Índices HNSW y GIN | No corresponde | T10 |

| Criterio de aceptación | Estado | Cómo se comprobó |
| --- | --- | --- |
| La migración se aplica en una base vacía y se revierte sin errores | **Cumplido** | `test_migracion_asciende_y_desciende_sin_errores`: sube a 0002 (15 tablas), sube a la cabeza, baja a la base y vuelve a subir. `alembic check` informa "No new upgrade operations detected" |
| No hay columnas de nombre, correo o documento de identidad | **Cumplido** | `test_sin_columnas_de_datos_personales`; otra prueba confirma que el patrón detecta `nombre`, `correo`, `dni` y `email` |
| Cada dato que exige la ficha de métricas tiene columna identificada | **Cumplido** (10.9) | `test_alimenta_cubre_la_ficha_de_metricas` (una prueba por métrica, con las columnas de la tabla 1 de los insumos) y `test_los_juicios_de_evaluacion_existen` |

### 10.2. T05. Repositorios con aislamiento por caso

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. `ContextoAcceso` construido desde la sesión | Hecha | `app/repositorios/contexto.py`; solo lo construye `app/seguridad/dependencias.py` |
| 2. Repositorios por entidad que exigen el contexto | Hecha | `app/repositorios/base.py` (filtro `caso_id` en toda consulta), `caso.py` e `investigador.py` |
| 3. `colecciones_permitidas(tipo, contexto)` | Hecha | `app/repositorios/colecciones.py` |
| 4. Matriz automática de autorización | Hecha | `pruebas/matriz_autorizacion.py` y `test_matriz_de_autorizacion` |
| Repositorios del investigador separados | Hecha | Exigen un contexto A2; con un contexto A1 fallan |
| Prueba estática de consultas fuera de `repositorios/` | Hecha | `test_no_hay_consultas_fuera_de_repositorios`; la consulta de `/salud` pasó a `RepositorioSalud` |

| Criterio de aceptación | Estado | Cómo se comprobó |
| --- | --- | --- |
| Ningún método de repositorio de datos de caso se invoca sin contexto | **Cumplido** | `test_todo_metodo_de_repositorio_exige_contexto` inspecciona cada método público: el primer parámetro es `contexto: ContextoAcceso`, sin valor por defecto |
| La matriz de autorización no encuentra accesos cruzados | **Cumplido** | `test_matriz_de_autorizacion`: sin sesión 401, rol cruzado 403 y el caso B no ve datos del A. **Prueba de mutación:** al quitar el filtro `caso_id` del repositorio base fallan las 3 pruebas de aislamiento |
| `colecciones_permitidas` devuelve lo especificado para los seis tipos | **Cumplido** | `test_colecciones_permitidas_por_tipo`, con 6 casos: D1, D2 y D3 van a `guias`; evidencia, a la científica del tema y la personal del caso; referencias, a ninguna. Nunca aparecen colecciones de otro caso ni de otro tema |

Segunda barrera en la base: claves foráneas compuestas `(padre_id, caso_id)` (`test_clave_compuesta_impide_colgar_datos_de_otro_caso`).

### 10.3. T06. Autenticación, roles y sesiones

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Hash con Argon2 | Hecha | Argon2id con `argon2-cffi` |
| 2. Inicio y cierre con cookie `HttpOnly`, `Secure` y `SameSite` | Hecha | `POST /sesion`, `DELETE /sesion` |
| 3. Expiración absoluta de 8 h, inactividad de 60 min y dos sesiones por cuenta | Hecha | `app/seguridad/servicio.py` |
| 4. Bloqueo tras 5 fallos en 15 minutos | Hecha | Bloqueo de 15 minutos (decisión T06-01) |
| 5. Cambio obligatorio de la contraseña inicial | Hecha | `POST /sesion/contrasena`; hasta cambiarla, las rutas de rol responden 403 `cambio_contrasena_requerido` |
| 6. Dependencias `requiere_caso` y `requiere_investigador` | Hecha | `app/seguridad/dependencias.py` |
| 7. Protección CSRF | Hecha | Doble envío firmado con HMAC; cabecera `X-CSRF-Token` |
| Sesiones en PostgreSQL, mensajes que no revelan la cuenta y eventos de seguridad | Hecha | Tabla `sesion`; mensaje único; eventos `inicio`, `fallo`, `bloqueo`, `cierre`, entre otros |

| Criterio de aceptación | Estado | Cómo se comprobó |
| --- | --- | --- |
| La contraseña nunca aparece en la base ni en el registro | **Cumplido** | `test_la_contrasena_no_aparece_en_la_base_ni_en_el_registro` revisa la tabla `cuenta` y toda la salida del registro |
| Tras 5 fallos en 15 minutos, la cuenta queda bloqueada temporalmente | **Cumplido** | `test_bloqueo_tras_cinco_fallos_en_quince_minutos` (con reloj simulado: sigue bloqueada a los 14 minutos y se libera a los 16) y `test_fallos_fuera_de_la_ventana_no_bloquean` |
| Una sesión inactiva 60 minutos deja de valer; una tercera sesión invalida la más antigua, comportamiento documentado | **Cumplido** | `test_sesion_inactiva_60_minutos_deja_de_valer`, `test_expiracion_absoluta_de_8_horas` y `test_tercera_sesion_cierra_la_mas_antigua`; `docs/decisiones/T06-sesiones-y-bloqueo.md` |
| Una cuenta A1 no accede a rutas de A2 | **Cumplido** | Matriz de autorización y recorrido con `curl` (A1 en `/investigador/casos`: 403) |

### 10.4. T07. Casos, temas, colecciones y cuentas

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Colección científica de un tema | Hecha | `POST /investigador/colecciones/cientificas` |
| 2. Alta de caso con su colección personal y una o dos cuentas | Hecha | `POST /investigador/casos`; contraseña inicial aleatoria mostrada una sola vez |
| 3. Desactivación y reactivación | Hecha | `POST /investigador/casos/{codigo}/desactivar` y `/reactivar`; desactivar cierra las sesiones abiertas |
| 4. Norma de citación por caso, IEEE por defecto y registro de cambios | Hecha | `PUT /investigador/casos/{codigo}/norma`; tabla `cambio_norma` |
| 5. Rutas del investigador | Hecha | Además, `GET /investigador/colecciones`, `GET /investigador/casos` y `GET /investigador/casos/{codigo}` |
| Primera cuenta de investigador | Hecha | `python -m app.seguridad.crear_investigador CODIGO` |

| Criterio de aceptación | Estado | Cómo se comprobó |
| --- | --- | --- |
| CP-22 superado (código repetido rechazado con mensaje) | **Cumplido** | `test_cp22_codigo_de_caso_repetido` (409 `codigo_repetido`, también si se escribe en minúsculas) y recorrido con `curl` |
| Al crear un caso existen su colección personal y sus cuentas, y el caso queda asociado a la científica de su tema | **Cumplido** | `test_alta_completa_de_un_caso`, `test_caso_en_pareja_tiene_dos_cuentas` |
| La norma por defecto es IEEE y un cambio queda registrado | **Cumplido** | `test_norma_por_defecto_ieee_y_cambio_registrado` (el registro guarda la cuenta del investigador) |
| La desactivación impide iniciar sesión; una norma fuera de la lista se rechaza | **Cumplido** | `test_desactivacion_impide_iniciar_sesion_y_cierra_sesiones`, `test_norma_fuera_de_la_lista_rechazada` |

### 10.5. Pendientes y puntos provisionales de la Fase 2

1. ~~Falta la especificación de la Fase 1.~~ **Resuelto en 10.9**: `verificacion`, `documento` y los tipos de alcance se corrigieron con la migración 0005.
2. ~~Falta la ficha de métricas.~~ **Resuelto en 10.9**: la columna "Alimenta" está completa.
3. ~~Catálogo de hitos vacío, y tau y N en `null`.~~ **Resuelto en 10.9**: la migración 0006 carga los ocho hitos, N = 2 y tau = 0.5. Tau sigue provisional hasta T34.
4. ~~Normas `ieee` y `apa7`, a confirmar.~~ **Cerrado**: los autores confirmaron la lista `ieee` (por defecto), `apa7` y `vancouver` (D-12, migración 0007). Los códigos van en minúsculas desde 0006.
5. ~~CI en GitHub.~~ **Resuelto**: la Fase 2 pasó la CI en la solicitud de cambio #1 (apartado 10.10).

### 10.6. Pruebas ejecutadas

Comando: `docker compose run --rm --build pruebas` (Python 3.12.16, PostgreSQL 16 con pgvector 0.8.7). **118 superadas y 0 fallidas: 87 nuevas y las 31 de la Fase 1. Cobertura de `app/`: 97,13 %** (mínimo 70 %). Repetido en una copia limpia siguiendo el README, con el mismo resultado.

| Archivo | Pruebas | Qué cubre |
| --- | --- | --- |
| `unitarias/test_arquitectura.py` | 20 | Consultas solo en repositorios (prueba estática), columnas prohibidas, índices por caso, descripción de cada columna, diccionario al día, contexto obligatorio en cada repositorio y matriz de rutas completa |
| `unitarias/test_seguridad_y_parametros.py` | 14 | Argon2id, tokens, CSRF firmado, valores fijados de sesión y esquema de parámetros |
| `integracion/test_migraciones.py` | 14 | Subida y bajada, semilla, unicidad, valores permitidos, claves compuestas, versión vigente por hito y `vector(1024)` |
| `integracion/test_repositorios.py` | 11 | Aislamiento en lectura, escritura y registros hijos; colecciones permitidas para los seis tipos; contextos mal formados |
| `integracion/test_sesion.py` | 13 | Cookies, mensaje único, contraseña ausente de la base y del registro, bloqueo, ventana de fallos, inactividad, 8 h, tercera sesión, cambio de contraseña, CSRF y eventos |
| `integracion/test_casos.py` | 10 | Alta completa, pareja, CP-22, temas, formato de códigos, desactivación, norma, 404 y semillas |
| `integracion/test_comandos.py` | 4 | Comandos `crear_investigador` y `semillas` |
| `integracion/test_matriz_autorizacion.py` | 1 | Recorrido de toda la matriz con cada rol y con otro caso |

Otras verificaciones:
* Sin errores: `ruff check`, `ruff format --check` y `mypy` estricto (49 archivos), `alembic check`, `pip-audit`, gitleaks y `actionlint`.
* Recorrido manual con `curl` contra la API en Compose: alta del investigador por comando, inicio de sesión, cambio de contraseña, tema, caso en pareja, código repetido (409), PUT sin CSRF (403), cambio de norma, caso con contraseña pendiente (403) y A1 en una ruta de A2 (403).

### 10.7. Problemas encontrados y soluciones

| Problema | Solución |
| --- | --- |
| La migración autogenerada perdía la clave circular entre `coleccion.caso_id` y `caso` (`use_alter` dentro de `create_table`) | La migración crea esa clave con `op.create_foreign_key` después de la tabla `caso` y la borra antes al revertir |
| Las seis columnas de comprobación compartían el nombre de su restricción CHECK | Cada columna usa una enumeración con nombre propio |
| El manejador de registro conservaba el `sys.stdout` del momento de configurarlo, y las pruebas que revisan el registro no veían nada (pasaban sin comprobar) | El manejador escribe en el `sys.stdout` vigente en cada evento; la prueba de la contraseña ahora sí revisa el registro |
| El orden de las restricciones (un conjunto) hacía no determinista el diccionario | Se ordenan las claves compuestas |
| FastAPI 0.162 anida las rutas incluidas y la prueba de la matriz no las veía | La lista de rutas sale del contrato OpenAPI |
| El generador del diccionario escribía con la codificación de la consola de Windows | Escribe el archivo directamente en UTF-8 |
| La cobertura no seguía el código asíncrono de SQLAlchemy (servicio de sesión en 60 %) | `concurrency = ["greenlet", "thread"]` en la configuración de coverage |
| Al contenedor de pruebas le faltaba `docs/` | El servicio `pruebas` monta `./docs` en solo lectura |
| `docker compose run --rm pruebas` reutilizaba una imagen antigua tras actualizar el código | README, CLAUDE.md y Compose indican `run --rm --build pruebas` |

### 10.8. Archivos de la Fase 2

**Creados:**
* Backend:
  * Datos: `alembic.ini`, `migraciones/env.py`, `migraciones/script.py.mako`, las migraciones `0001` a `0004` en `migraciones/versiones/`, `app/bd/{base,enumeraciones,diccionario,semillas}.py`, `app/bd/modelos/{__init__,_columnas,casos,corpus,borradores,solicitudes,seguridad,administracion}.py` y `app/administracion/{__init__,parametros}.py`.
  * Acceso y seguridad: `app/repositorios/{__init__,contexto,base,caso,colecciones,investigador,autenticacion,sistema,unidad}.py` y `app/seguridad/{__init__,politica,credenciales,servicio,dependencias,crear_investigador}.py`.
  * Casos y API: `app/casos/{__init__,servicio}.py` y `app/api/{sesion,caso,investigador}.py`.
* Pruebas: `pruebas/matriz_autorizacion.py`, `pruebas/integracion/{conftest,test_migraciones,test_repositorios,test_sesion,test_casos,test_comandos,test_matriz_autorizacion}.py` y `pruebas/unitarias/{test_arquitectura,test_seguridad_y_parametros}.py`.
* Documentación: `docs/diccionario-de-datos.md` y, en `docs/decisiones/`, `T04-modelo-de-datos.md`, `T06-sesiones-y-bloqueo.md` y `T07-cuentas-de-caso.md`.

**Modificados:**
* Backend: `pyproject.toml` (alembic, argon2-cffi, pgvector y cobertura con greenlet), `Dockerfile` (copia de Alembic), `app/main.py` (rutas nuevas), `app/api/salud.py` (consulta movida a `RepositorioSalud`), `app/bd/sesion.py` y `app/comun/registro.py`.
* Infraestructura: `docker-compose.yml` (servicio `migrar` y `docs` montado en el servicio de pruebas) y `.github/workflows/ci.yml` (paso `alembic upgrade head && alembic check`).
* Documentación: `README.md`, `CLAUDE.md` y este archivo.

`docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md` no se modificó.

### 10.9. Contraste de T04 con la especificación de la Fase 1 y la ficha de métricas

Fuentes:
- `docs/especificacion-fase1/` (6.7, 18.2, 18.4, 18.6, RF-02, RF-25 y RN-18).
- `docs/insumos/insumos-modelo-de-datos-y-configuracion.md`.

Detalle de cada diferencia y su justificación en `docs/decisiones/T04-contraste-especificacion-fase1.md`. Integrado en la solicitud de cambio #1. Las migraciones 0001 a 0004 no se tocaron.

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| Contrastar `verificacion` con 6.7 | Hecha; difería | Migración 0005: `formato_ok`, `limites_ok`, `citas_ok`, `n_fuentes_citadas`, `n_fuentes_confirmadas`, `metodo`, `acceso_abierto_ok`, `fidelidad` y `superada` reemplazan a `c1` a `c6` y `aprobada`. Se añaden `n_fuentes_no_comprobables` (RN-18) y `resultado.advertencias` |
| Contrastar `documento` y `fragmento` con 18.2 | Hecha; difería | Nuevas: `isbn` y `ruta_archivo`. `fuente` pasa a `revista_editorial`. La huella es del texto normalizado (18.9). `texto_lexico` es una columna generada con `to_tsvector('simple', texto)` |
| Contrastar tipos y alcances con RF-02 y la tabla 3 | Hecha; difería | Códigos de tipo de la tabla 3; alcances `seccion`, `hito`, `fragmento`, `consulta` y `version`; `alcance_contenido` pasa a `alcance_ref`; CHECK de alcance admitido por tipo |
| Columnas para los juicios de M2, M3 y M5 | Hecha | Par evaluador y humano en `fragmento_recuperado`, `solicitud` y `resultado`, para calcular la concordancia de RF-25 |
| Completar "Alimenta" | Hecha | `app/bd/metricas.py` (M1 a M6) e índice inverso al final de `docs/diccionario-de-datos.md`. Se corrigieron tres indicaciones de T04 que no coincidían con la ficha |
| Cargar los hitos y la configuración inicial como versión 1 | Hecha | Migración 0006: reemplaza los parámetros de la versión 1 con los nombres y valores de la tabla 4 y los ocho hitos. Se detiene si la versión 1 está congelada o la usan solicitudes |
| Normas en minúsculas | Hecha | `ieee` y `apa7` en la configuración, `caso` y `cambio_norma`. La ruta normaliza `APA7` a `apa7` |
| Registrar las diferencias | Hecha | `docs/decisiones/T04-contraste-especificacion-fase1.md`; `T04-modelo-de-datos.md` remite a ella |

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Las migraciones nuevas suben y bajan sin errores | **Cumplido** | Base de desarrollo: 0004 a 0006, de nuevo a 0004 y otra vez a 0006. `test_migracion_asciende_y_desciende_sin_errores` en base vacía. `alembic check`: "No new upgrade operations detected" |
| Las restricciones de las migraciones coinciden con los modelos | **Cumplido** | `test_restricciones_de_las_migraciones_iguales_a_los_modelos`: compara todas las CHECK y las columnas generadas de la base migrada con las de `Base.metadata.create_all`. Hace falta porque Alembic no compara CHECK |
| La base impone la tabla de tipos y alcances | **Cumplido** | `test_alcances_admitidos_por_tipo` (7 combinaciones válidas) y `test_alcances_no_admitidos_se_rechazan` (9 inválidas, incluidos los códigos viejos) |
| La verificación guarda la salida de 6.7 y rechaza combinaciones incoherentes | **Cumplido** | `test_verificacion_con_los_campos_de_6_7`, `test_verificacion_incoherente_se_rechaza` (10 casos) y `test_no_comprobable_no_hace_fallar_el_conteo` |
| El vector léxico usa la configuración `simple` | **Cumplido** | `test_vector_lexico_generado_con_configuracion_simple`: conserva palabras vacías y siglas, y rechaza escrituras a mano |
| La versión 1 es la tabla 4 con los ocho hitos | **Cumplido** | `test_parametros_iniciales_son_los_de_los_insumos`, `test_catalogo_de_hitos` y `test_la_semilla_es_la_configuracion_inicial_del_codigo` (la base validada es igual a `parametros_iniciales()`) |
| Las migraciones no pisan datos | **Cumplido** | `test_la_migracion_0005_no_pisa_solicitudes_existentes`, `test_la_migracion_0006_respeta_una_version_1_congelada` y `test_la_migracion_0006_pasa_las_normas_a_minusculas_y_vuelve`. En la base de desarrollo, el caso con `APA7` quedó en `apa7` |
| Cada columna de la ficha declara su métrica | **Cumplido** | `test_alimenta_cubre_la_ficha_de_metricas` (6) y `test_ninguna_columna_alimenta_una_metrica_inexistente` |

**Pruebas.** Comando: `docker compose run --rm --build pruebas`. **176 superadas y 0 fallidas, 58 de ellas nuevas. Cobertura de `app/`: 97,16 %.**

| Archivo | Antes | Ahora |
| --- | --- | --- |
| `integracion/test_migraciones.py` | 14 | 56 |
| `unitarias/test_arquitectura.py` | 20 | 28 |
| `unitarias/test_seguridad_y_parametros.py` | 14 | 22 |

Otras verificaciones:
- Sin errores: `ruff check`, `ruff format --check` y `mypy` estricto (50 archivos).
- Recorrido contra la API reconstruida en Compose, como `INV-DEV` de las semillas:
  - `PUT .../norma` con `APA7`: 200, guarda `apa7`.
  - Con `mla`: 422, permitidas `["ieee", "apa7"]`.
  - El registro de cambios guarda `("ieee", "apa7")`.
- Las semillas crean los casos con `ieee`.

**Problemas y soluciones.**

| Problema | Solución |
| --- | --- |
| Alembic aplicaba otra vez la convención de nombres a los nombres ya completos (`ck_solicitud_ck_solicitud_...`) y 0005 fallaba (se revirtió sola por ser transaccional) | Todos los nombres de restricción de 0005 van con `op.f()` |
| `alembic check` no detecta restricciones CHECK ni columnas generadas, así que no basta para saber si la migración coincide con el modelo | Prueba nueva que compara `pg_constraint` y `pg_attrdef` entre la base migrada y la creada desde los modelos |
| Una prueba de ISBN con guiones fallaba por la longitud de la columna, no por la CHECK | Valores de prueba de 13 caracteres o menos |
| El intérprete `python` no está en el PATH del anfitrión, y los heredocs largos de Bash fallaban al analizarse | Se usa `backend/.venv/Scripts/python.exe` y los scripts de edición van en archivos aparte |

**Archivos.**
- Creados:
  - `backend/app/bd/metricas.py`.
  - `backend/migraciones/versiones/0005_contraste_especificacion_fase1.py` y `0006_configuracion_v1_y_hitos.py`.
  - `docs/decisiones/T04-contraste-especificacion-fase1.md`.
- Modificados:
  - Backend: `app/bd/enumeraciones.py`, `app/bd/modelos/{solicitudes,corpus,casos,borradores}.py`, `app/bd/diccionario.py`, `app/administracion/parametros.py`, `app/repositorios/colecciones.py`, `app/casos/servicio.py` y `app/api/investigador.py` (ejemplo `apa7`).
  - Pruebas: `pruebas/integracion/{test_migraciones,test_repositorios,test_casos}.py`, `pruebas/unitarias/{test_arquitectura,test_seguridad_y_parametros}.py` y `pruebas/matriz_autorizacion.py`.
  - Documentación: `docs/diccionario-de-datos.md` (regenerado), `docs/decisiones/T04-modelo-de-datos.md` y este archivo.

**Sigue pendiente:**
- tau = 0.5 es provisional hasta T34.
- ~~La lista de normas queda pendiente de confirmación antes de T20 (D-12).~~ Cerrada en 10.10.
- Las instrucciones oficiales de cada hito llegan en T22.
- La deduplicación por DOI y la confirmación de documentos incompletos se dejan para T09, T10 y T15, sin adelantarlas.

### 10.10. Decisiones aceptadas, D-12 cerrada e integración en `main`

**Decisiones aceptadas por los autores** (6 de noviembre de 2026), cada una en su archivo:
- `docs/decisiones/T04-juicios-evaluador-y-humano.md`: dos columnas por juicio (evaluador y humano) para M2, M3 y M5.
- `docs/decisiones/T04-fuentes-no-comprobables.md`: `verificacion.n_fuentes_no_comprobables` (RN-18).
- `docs/decisiones/T04-metodo-mixto.md`: valor `mixto` en `verificacion.metodo`.

**D-12 cerrada:** lista cerrada `ieee` (por defecto), `apa7` y `vancouver`.
- Migración `0007_normas_d12_cerrada.py`: añade `vancouver` a la versión 1. Su descenso se detiene si algún caso usa `vancouver`.
- `NORMAS_INICIALES` en `app/administracion/parametros.py`.
- Pruebas: `test_la_migracion_0007_cierra_la_lista_de_normas_d12` y `test_lista_cerrada_de_normas_d12` (`Vancouver` se guarda como `vancouver`).
- Consecuencia: el corpus de guías necesita también el manual de Vancouver (T22), y T20 debe cubrir las tres normas.

**Sin cambios, por indicación de los autores:** tau = 0.5 sigue provisional hasta T34, y las instrucciones de cada hito llegan en T22.

**Contraseñas iniciales impresas por las semillas.**
- No están en ningún archivo del repositorio (búsqueda en todo el árbol, incluidos los archivos ignorados) ni en los registros de los contenedores.
- Se borró un script temporal, fuera del repositorio, que contenía la contraseña nueva de `INV-DEV`.
- Las cuentas ficticias de la base de desarrollo local conservan esas contraseñas.

**Verificación local:**
- `docker compose run --rm --build pruebas`: 179 superadas, cobertura del 97,16 %.
- Ruff, mypy estricto y `alembic check` sin diferencias.
- gitleaks sobre el árbol de trabajo: `no leaks found`.
- 0007 sube, baja y vuelve a subir en la base de desarrollo.

**Integración:**

| Paso | Resultado |
| --- | --- |
| Rama y confirmación | `t04-contraste-especificacion`, confirmación `9b18700` (`T04-T07: implementar la Fase 2 y ajustar T04 a la especificación de la Fase 1`), sin línea de coautoría. Reemplaza a `d9254af`, que la llevaba |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#1 |
| CI de la solicitud | **Verde**: análisis, tipado, pruebas con cobertura, `pip-audit` y gitleaks. Ejecuciones 42308914645 (`d9254af`) y 42309565158 (`9b18700`) |
| Integración en `main` | Commit de integración `7a569a0` |
| CI de `main` tras integrar | Ejecución 42310241343: **verde** |

**Pendiente:**
- Protección de la rama principal con verificaciones obligatorias (T00, la configuran los integrantes).
- Hasta que exista, el criterio "una solicitud de cambio con una prueba que falla queda bloqueada" de T02 sigue verificado solo en local.

---

## 11. Fase 3 (F3): T08. Servicios de procesamiento compartidos

Rama `t08-servicios-compartidos`. La verificación se hizo en el equipo de desarrollo: Windows 11, Docker Desktop amd64 con 8 GB y 16 CPU, y emulación arm64 con QEMU. La instancia ARM real está en trámite con Oracle (incidente 261107-001540). Decisiones:
- `docs/decisiones/T08-servicios-compartidos.md`: inferencia, revisiones, determinismo, despliegue y mediciones.
- `docs/decisiones/T08-emulacion-arm64.md`.
- `docs/decisiones/T01-grobid-arm64.md`, confirmada.

### 11.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. GROBID en el proyecto de Compose compartido y su funcionamiento en ARM | Hecha; ARM real pendiente | `compartido/docker-compose.yml` con `grobid/grobid:0.9.1-crf`. Responde y extrae la cabecera de un PDF ficticio en amd64 y en arm64 emulado (`test_grobid.py`, 2 pruebas) |
| 2. `servicio_modelos/` con `/embeber` y `/reordenar` | Hecha | Paquete `servicio/` con FastAPI. Además expone `/salud` con los modelos, las revisiones y la memoria |
| 3. Biblioteca de inferencia elegida y registrada | Hecha | transformers 5.20.2 con PyTorch 2.14.1 en CPU; árbol fijado en `servicio_modelos/restricciones.txt` (decisión T08-01, apartado 1) |
| 4. Revisiones exactas y descarga a un volumen persistente | Hecha | `servicio/catalogo.py`: commits, tamaños y SHA-256. `python -m servicio.descargar` baja a `sma_modelos` y verifica las huellas. Probado dos veces desde un volumen vacío |
| 5. Clientes en `app/` detrás de `ProveedorEmbeddings` y `Reordenador` | Hecha | `app/inferencia/interfaces.py` y `app/inferencia/servicio_modelos.py`; `URL_SERVICIO_MODELOS` opcional en los ajustes |
| Tarea: lotes de tamaño configurable | Hecha | `TAMANO_LOTE`. Cada lote agrupa solo textos de igual longitud en tokens, sin relleno, para el determinismo (`servicio/lotes.py`) |
| Tarea: identificador y revisión del modelo en cada respuesta | Hecha | Campos `modelo` y `revision`; el cliente rechaza mezclas de revisiones |
| Tarea: límite de concurrencia | Hecha | `MAX_CONCURRENCIA` (1); en cola hasta `ESPERA_MAXIMA_S` y luego 503 `servicio_ocupado` |
| Entregable: registro de memoria usada | Hecho | Mediciones en la decisión T08-01, apartado 7; `/salud` informa la memoria residente y el pico |

### 11.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Ambos servicios responden en ARM | **Parcial**: GROBID sí en emulación; el servicio de modelos queda pendiente de la instancia real | En arm64 emulado, GROBID respondió y extrajo la cabecera. La imagen arm64 del servicio de modelos se construye, pero bajo QEMU oneDNN falla al leer `MIDR_EL1`, que el emulador no expone. Es una limitación del emulador, no de la imagen (decisión T08-02). Se confirma en la instancia real; pendiente añadido a T01 |
| El mismo texto produce siempre el mismo vector | **Cumplido** | `test_el_mismo_texto_produce_siempre_el_mismo_vector`, con los pesos reales: igualdad bit a bit entre solicitudes, dentro de un lote con textos de otras longitudes y con el texto repetido en el mismo lote (diferencia máxima 0,0). `test_servicio_modelos.py` lo repite desde el cliente de la API |
| La memoria de los servicios compartidos y dos bases cabe en la instancia sin intercambio a disco | **Medido en amd64; pendiente en la instancia** | Pico del servicio de modelos: 3,6 GB. GROBID: 2,2 a 2,5 GB. Cada base: unos 50 MB vacía. Estimación para la instancia de 12 GB: unos 9,5 GB en total, con 2,5 GB de margen (decisión T08-01, apartado 7). Falta medirlo con `free -m` en la instancia |

### 11.3. Pruebas

| Suite | Resultado |
| --- | --- |
| API (`docker compose run --rm --build pruebas`) | **195 superadas**, 3 omitidas (las de `servicios_compartidos`, que necesitan los servicios en marcha); cobertura de `app/` **97,12 %** |
| `unitarias/test_inferencia.py` (nueva) | 16: cliente contra un servicio simulado (partes, orden, identidad, errores 503 y 422, revisión mezclada, registro sin textos, ajustes) |
| `integracion/test_servicio_modelos.py` y `test_grobid.py` (nuevas, `servicios_compartidos`) | 3 superadas contra los servicios reales en amd64. GROBID también contra arm64 emulado |
| `servicio_modelos` sin pesos (CI) | **26 superadas**: contrato, límites, 503 por concurrencia, arranque sin pesos, catálogo y lotes. Cobertura **97,58 %** |
| `servicio_modelos` con pesos reales (`modelos_locales`, bajo demanda) | **4 superadas**: vectores normalizados y multilingües, determinismo, reordenamiento con sentido y medición |

**Medición con un lote de prueba** (64 párrafos de unos 350 tokens y reranking de 30 candidatos, amd64, 8 hilos):

| Medida | Valor |
| --- | --- |
| Embeber | 37,8 s (1,69 párrafos por segundo) |
| Reordenar 30 candidatos | **18,6 s** |
| Pico de memoria del proceso | 3,7 GB |
| Carga de los dos modelos | 9 s |

**Integración continua:** trabajo nuevo `servicio_modelos`, con Ruff, mypy, pruebas con cobertura, `pip-audit` del entorno y `pip-audit` de `restricciones.txt`, que audita también torch sin la etiqueta `+cpu`.

**Otras verificaciones:**
- Sin errores: Ruff, `ruff format --check` y mypy estricto en `backend/` (53 archivos) y en `servicio_modelos/` (12 archivos).
- `pip-audit` sin vulnerabilidades, en ambos paquetes y en el árbol fijado.
- `actionlint` sin errores y `docker compose config` válido.

### 11.4. Problemas encontrados y soluciones

| Problema | Solución |
| --- | --- |
| Un texto procesado en un lote con relleno difería en torno a 1,2e-7 del mismo texto procesado solo | Lotes solo de textos con igual cantidad de tokens. En CPU agrupar casi no acelera (1,49 textos por segundo de uno en uno frente a 1,60 en lotes de 4), así que no se pierde rendimiento |
| La descarga fallaba con "Permission denied": el usuario sin privilegios no tiene carpeta personal para la caché de Hugging Face | `HF_HOME=/modelos/.cache-hf` dentro del volumen |
| El `COMPOSE_PROJECT_NAME` del `.env` de la raíz tiene prioridad sobre `name:` y el proyecto compartido quedaba como `sma_rag` | El Compose compartido vive en `compartido/` con su propio `.env.example` |
| La rueda de torch de PyPI para amd64 trae CUDA (varios GB) | Índice de CPU de PyTorch (`--extra-index-url`) |
| `pip-audit` no audita `torch==2.14.1+cpu` porque PyPI no conoce la etiqueta local | La CI audita una copia de `restricciones.txt` sin `+cpu` |
| Bajo emulación, la primera solicitud a GROBID superó 120 s | Plazo de 600 s en la prueba para la primera solicitud |
| El servicio de modelos no arranca en arm64 emulado (oneDNN y `MIDR_EL1` con QEMU) | Limitación del emulador; no se sigue diagnosticando (decisión T08-02). Pendiente en la instancia real |
| `pytest --cov` en el contenedor de pruebas del servicio fallaba al escribir `.coverage` (usuario sin permisos en `/srv`) | `COVERAGE_FILE=/tmp/.coverage` en el comando |

### 11.5. Riesgos para fases posteriores

- **T16, latencia del reordenamiento:** 18,6 s para 30 candidatos con 8 hilos x86. En 2 OCPU ARM será previsiblemente mayor. Opciones a evaluar en T16 y T34, sin adelantarlas: menos candidatos, menos tokens por par, cuantización int8 o la contingencia de R-02.
- **T10, tiempo de indexación:** a 1,7 fragmentos por segundo, unos 50 000 fragmentos tardan unas 8 h en este equipo. La indexación es fuera de línea (18.5), pero hay que medirla en la instancia.
- **T10:** la API se une a la red `sma_compartido` y fija `URL_SERVICIO_MODELOS`. En T08 aún no se conecta, porque nada la usa.

### 11.6. Archivos

**Creados:**
- `servicio_modelos/`: `pyproject.toml`, `Dockerfile`, `.dockerignore`, `restricciones.txt`, `servicio/` (`ajustes`, `aplicacion`, `catalogo`, `descargar`, `esquemas`, `lotes`, `memoria`, `motores`, `motor_transformers`, `registro`, `__main__`) y `pruebas/` (`conftest`, `test_contrato`, `test_catalogo`, `test_lotes`, `test_modelos_reales`).
- `compartido/docker-compose.yml` y `compartido/.env.example`.
- `backend/app/inferencia/` (`interfaces`, `servicio_modelos`).
- `backend/pruebas/unitarias/test_inferencia.py`, `backend/pruebas/integracion/test_servicio_modelos.py` y `test_grobid.py`.
- `docs/decisiones/T08-servicios-compartidos.md` y `T08-emulacion-arm64.md`.

**Modificados:**
- `backend/app/configuracion/ajustes.py` (`URL_SERVICIO_MODELOS`) y `backend/pyproject.toml` (marca `servicios_compartidos`).
- `.github/workflows/ci.yml` (trabajo `servicio_modelos`) y `.env.example`.
- `README.md`, `CLAUDE.md`, `docs/operacion/servidor-desarrollo.md`, `docs/decisiones/T01-grobid-arm64.md` y este archivo.

**Pendiente de T08, ligado a T01:** comprobar en la instancia ARM real que el servicio de modelos responde, repetir allí las pruebas `pruebas_modelos` y medir la memoria sin intercambio.

### 11.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmación | `t08-servicios-compartidos`, confirmación `aa93a69` (`T08: agregar servicios de procesamiento compartidos`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#2 |
| CI de la solicitud | **Verde**, ejecución 42522009898: análisis, tipado, pruebas con cobertura, `pip-audit`, gitleaks y el trabajo nuevo `servicio_modelos` |
| Integración en `main` | Commit de integración `b7dcd69` |
| CI de `main` tras integrar | Ejecución 42527989955: **verde** (6 de 6 trabajos) |

---

## 12. Fase 3 (F3): T09. Extracción y segmentación de documentos

Rama `t09-extraccion-segmentacion`, desde `main` con T08 (`b7dcd69`). Decisión: `docs/decisiones/T09-extraccion-y-segmentacion.md` (T09-01). La verificación se hizo en el equipo de desarrollo (amd64), en contenedores con Python 3.12. Se usaron Docling y el tokenizador de bge-m3 reales y el GROBID 0.9.1 del proyecto compartido.

### 12.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Extracción con Docling: texto, títulos, orden de lectura y páginas | Hecha | `app/corpus/extractor_docling.py`. `docling-slim` 2.149.0 sin OCR ni tablas, con el modelo de diseño de página fijado por revisión y huella (`app/corpus/recursos.py`) |
| 2. Metadatos de cabecera con GROBID | Hecha | `app/corpus/grobid.py`: título, autores (nombres y apellidos), año, DOI, revista e idioma, sin consolidación externa |
| 3. Limpieza | Hecha | `app/corpus/limpieza.py`: Unicode (NFC, ligaduras, invisibles), encabezados y pies repetidos aunque estén mal etiquetados o pegados dentro de un párrafo, números de página, guiones de corte, párrafos partidos por salto de página o columna |
| 4. Normalización de secciones a IMRaD | Hecha | `app/corpus/secciones.py`: títulos en español e inglés, subsecciones que heredan su sección, títulos que el extractor dejó dentro de un párrafo |
| 5. Segmentación por sección y párrafos con ventana y una oración de solapamiento | Hecha | `app/corpus/segmentacion.py`; ventana y solapamiento leídos de la configuración versionada; tokens contados con el tokenizador de bge-m3 |
| 6. Exclusión de referencias y agradecimientos | Hecha | Por título y por la etiqueta `reference` de Docling |
| 7. Regla de documento incompleto | Hecha | Menos de `palabras_minimas_articulo` (1 500, migración 0008) o sin introducción, métodos, resultados, discusión ni conclusiones |
| 8. Detección y exclusión de PDF escaneado | Hecha | `app/corpus/validacion.py`: menos de la mitad de las páginas con texto extraíble produce `sin_capa_de_texto` |
| Tarea: función pura `procesar_pdf(ruta) -> DocumentoProcesado` sin acceso a la base | Hecha | `CanalPdf.procesar_pdf` en `app/corpus/extraccion.py`; prueba de arquitectura `test_el_canal_de_extraccion_no_accede_a_la_base` |
| Tarea: validación previa (tipo real, 25 MB, 60 páginas; RN-16) | Hecha | Firma `%PDF-`, tamaño antes de leer, cifrado con contraseña de apertura, páginas; límites de la configuración |
| Tarea: el contenido del PDF es dato (RN-23) | Hecha | Nada se interpreta; el registro guarda estados y cantidades, nunca texto (probado) |
| Entregable: `corpus/extraccion.py` y `corpus/segmentacion.py` | Hecho | Más `bloques`, `esquemas`, `limpieza`, `secciones`, `validacion`, `grobid`, `recursos`, `tokenizador` y `extractor_docling` |
| Entregable: PDF de muestra en `pruebas/datos/` | Hecho | Siete PDF ficticios generados con `pruebas/datos/generar_pdf_muestra.py`: artículo en español (una columna) y en inglés (dos columnas), corto, sin secciones IMRaD, escaneado, cifrado y con solo restricción de permisos |

### 12.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Cada fragmento lleva sección normalizada, título original y páginas | **Cumplido** | `test_canal_pdf.py` (`comprobar_fragmentos`) sobre los dos artículos con Docling real; el esquema `FragmentoProcesado` lo exige |
| Un PDF escaneado o con texto insuficiente produce estado y motivo, no fragmentos silenciosos | **Cumplido** | Escaneado: `excluido` con `sin_capa_de_texto` y sin fragmentos. Corto: `incompleto` con `texto_insuficiente`. Sin secciones: `incompleto` con `sin_secciones_imrad`. El esquema `DocumentoProcesado` rechaza estados sin motivo |
| La sección de referencias no aparece en ningún fragmento | **Cumplido** | Frases que solo existen en las referencias y en los agradecimientos de cada artículo no aparecen en ningún fragmento, incluido el caso en que Docling dejó el título "Referencias" dentro de un párrafo |

### 12.3. Pruebas

| Suite | Resultado |
| --- | --- |
| API completa (`docker compose run --rm --build pruebas`, con recursos del canal) | **363 superadas**, 5 omitidas (servicios compartidos y una comparación que necesita el árbol completo del repositorio); cobertura de `app/` **97,21 %** |
| Unitarias nuevas del canal | 159: limpieza (37), secciones (50), segmentación (22), validación (10), GROBID con respuestas grabadas (16), canal con dobles (17), recursos (7) |
| `integracion/test_canal_pdf.py` (marca `corpus`, Docling real) | **8 superadas**: los dos artículos, corto, sin IMRaD, solo permisos, escaneado, cifrado y determinismo |
| `integracion/test_grobid.py` contra el GROBID real | 3 superadas (incluye el cliente de T09) |
| `integracion/test_migraciones.py` | La configuración guardada tiene exactamente los parámetros del esquema; 0008 sube, baja y se niega con la versión 1 congelada |

**Integración continua:** trabajo nuevo `corpus`. Instala el extra con el árbol fijado, descarga y verifica los recursos (en caché), corre las pruebas con Docling real y audita el árbol fijado con `pip-audit`, incluido torch.

**Otras verificaciones:**
- Ruff, `ruff format --check` y mypy estricto sin errores (65 archivos).
- `pip-audit` sin vulnerabilidades en el árbol fijado y en el entorno instalado.
- `actionlint` sin errores y `docker compose config` válido.
- La descarga de recursos (4 archivos, 13 s) se verificó dos veces; la segunda no descargó nada.

**Revisión manual de la segmentación** (artículo de muestra en español, 4 páginas, 1 718 palabras):

| # | Sección | Título original | Páginas | Tokens | Observación |
| --- | --- | --- | --- | --- | --- |
| 0 | resumen | Resumen | 1 | 225 | Título separado del párrafo; incluye las palabras clave |
| 1 | introduccion | 1. Introducción | 1 | 441 | Cuatro párrafos completos |
| 2 | metodos | 2.1. Diseño y participantes | 1 y 2 | 417 | Une 2.1 a 2.3; el párrafo partido al pie de la página 1 quedó entero |
| 3 | metodos | 2.4. Análisis de datos | 2 | 155 | Empieza con la última oración del fragmento anterior |
| 4 y 5 | resultados | 3. Resultados | 2 a 4 | 337 y 157 | Título recuperado de dentro de un bloque; páginas amplias (apartado 12.4) |
| 6 y 7 | discusion | 4. Discusión | 3 y 4 | 432 y 127 | |
| 8 | conclusiones | 5. Conclusiones | 3 y 4 | 102 | |

Sin preliminares (título, autores, afiliación), encabezados, pies, agradecimientos ni referencias. El artículo en inglés, a dos columnas, dio 8 fragmentos de 65 a 442 tokens y respetó el orden de lectura.

**Mediciones** (amd64):

| Medida | Valor |
| --- | --- |
| Carga del extractor y del tokenizador | 3,5 s |
| Artículo de 4 páginas | 8,8 s |
| Artículo de 3 páginas a dos columnas | 3,3 s |
| Documento de 5 páginas | 5,7 s |
| Pico de memoria de Docling | 1,1 GB |
| Árbol de dependencias instalado | 1,6 GB |

### 12.4. Problemas encontrados y soluciones

| Problema | Solución |
| --- | --- |
| Docling marcó el encabezado de la revista como mobiliario en unas páginas y como título de sección en otra | Se quita todo texto igual a un encabezado o pie (con los números reemplazados) o repetido en la mitad de las páginas |
| Docling pegó el encabezado de la página siguiente al final de un párrafo que continúa en ella | El texto del mobiliario se quita también de dentro de los párrafos |
| Docling partió un párrafo en una pieza por línea al pie de la página y tomó por título la última línea de un párrafo que pasaba de columna | Se unen los bloques que continúan una oración; un "título" en minúscula vuelve a ser texto |
| Al alargar el artículo de muestra, el modelo de diseño de página tomó casi dos páginas como un solo párrafo, con los títulos y las referencias dentro | Se separan los títulos completos reconocibles que quedaron dentro de un párrafo. Las páginas de ese tramo quedan amplias; registrado como límite en T09-01 |
| Los textos ficticios de muestra no llegaban a 1 500 palabras, y el canal marcó correctamente "incompleto" un artículo | Se alargaron los textos; los PDF y las cabeceras grabadas de GROBID se regeneraron |
| El `.gitignore` excluía toda carpeta `datos/`, también `backend/pruebas/datos/` | Se ancló a la raíz (`/datos/`), como dice la hoja de ruta (4.1) |
| La prueba de arquitectura marcó `httpx.Client.stream()` como consulta a la base | Se usó `send(..., stream=True)` y la prueba sigue estricta |
| La regla para unir un último fragmento corto con el anterior nunca se ejecutaba | Se quitó; el último fragmento de una sección puede quedar corto |

### 12.5. Riesgos para fases posteriores

- **T10, memoria en la instancia:** Docling suma un pico de 1,1 GB a los servicios de T08. La estimación de unos 10,6 GB durante la ingesta, sobre 12 GB, deja poco margen. Hay que medirla en la instancia.
- **T10, imagen de la API:** la imagen crece con PyTorch y Docling (1,6 GB de paquetes). Si en T10 la ingesta corre en un proceso aparte, puede evaluarse una imagen sin el extra para la API.
- **T10 y T34, calidad de la extracción en artículos reales:** los PDF de muestra son ficticios. La primera ingesta del corpus provisional (T10, actividad 7) debe revisar cuántos documentos quedan incompletos y por qué, y si aparecen referencias en los fragmentos.
- **T14 y T15:** GROBID partió mal un nombre con dos apellidos y no halló el año. Los metadatos de cabecera deben completarse con Crossref y OpenAlex.

### 12.6. Archivos

**Creados:**
- `backend/app/corpus/` (`bloques`, `esquemas`, `extraccion`, `extractor_docling`, `grobid`, `limpieza`, `recursos`, `secciones`, `segmentacion`, `tokenizador`, `validacion`).
- `backend/migraciones/versiones/0008_umbral_documento_incompleto.py`.
- `backend/restricciones-corpus.txt`.
- `backend/pruebas/datos/` (generador, textos y siete PDF ficticios) y `backend/pruebas/contrato/grobid/` (tres cabeceras grabadas de GROBID 0.9.1 y una construida a mano).
- `backend/pruebas/unitarias/test_corpus_*.py` (7) y `backend/pruebas/integracion/test_canal_pdf.py`.
- `docs/decisiones/T09-extraccion-y-segmentacion.md`.

**Modificados:**
- `backend/app/administracion/parametros.py` (`palabras_minimas_articulo`) y `backend/app/configuracion/ajustes.py` (`URL_GROBID`, `DIRECTORIO_RECURSOS_CORPUS`).
- `backend/pyproject.toml` (pypdf, extra `corpus`, reportlab, marca `corpus`, mypy), `backend/Dockerfile` (árbol fijado, sin red para modelos) y `docker-compose.yml` (volumen `recursos_corpus` para las pruebas).
- `.github/workflows/ci.yml` (trabajo `corpus`), `.env.example` y `.gitignore`.
- `backend/pruebas/integracion/test_grobid.py`, `test_migraciones.py` y `backend/pruebas/unitarias/test_arquitectura.py`.
- `README.md`, `CLAUDE.md` y este archivo.

### 12.7. Pendiente

- **Lectura de RN-16: confirmada** por el equipo el 19 de noviembre de 2026 (decisión T09-01, apartado 3.2, ya cerrada). Se rechaza el PDF con contraseña de apertura y se admite el que solo restringe permisos.
- La base de desarrollo recibe la migración 0008 al levantar el proyecto (`migrar`); no se aplicó a mano.

### 12.8. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmación | `t09-extraccion-segmentacion`, confirmación `69d1ffa` (`T09: implementar el canal de extracción y segmentación de PDF`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#4 |
| CI de la solicitud | **Verde**, ejecución 42532738205: 7 de 7 trabajos. El trabajo nuevo `corpus` verificó los recursos, pasó las 8 pruebas con Docling real y no encontró vulnerabilidades en el árbol fijado |
| Integración en `main` | Commit de integración `3bfd8e1` |
| CI de `main` tras integrar | Ejecución 42534017010: **verde** |

---

## 13. Fase 3 (F3): T10. Indexación y gestión del corpus

Rama `t10-indexacion-corpus`, desde `main` con T09 (`3bfd8e1`). Decisión: `docs/decisiones/T10-indexacion-y-gestion-del-corpus.md` (T10-01).

Decisiones del equipo del 12 de noviembre de 2026:
- El corpus provisional lo entrega el equipo después; T10 se implementa y prueba con los PDF ficticios de muestra.
- Las exclusiones se registran en una tabla de detalle, no solo en contadores.

### 13.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Migración de índices HNSW (coseno), GIN sobre `tsvector` y compuesto por colección | Hecha | `0009_indices_y_exclusiones_del_corpus.py`; `alembic check` sin diferencias; 0009 baja y vuelve a subir |
| 2. `indexar(documento_procesado, coleccion)`: deduplica por huella, guarda documento y fragmentos, pide vectores al servicio de modelos y guarda el `tsvector` | Hecha | `Indexador.indexar` e `Indexador.ingerir` en `app/corpus/indexacion.py`. El `tsvector` es una columna generada (T04). Deduplica por huella del archivo, del texto normalizado y por DOI |
| 3. Retiro de documentos | Hecha | `POST /investigador/documentos/{id}/retirar`: deja de recuperarse y conserva los fragmentos |
| 4. Comando de ingesta en lote, idempotente, con informe | Hecha | `python -m app.corpus.ingesta`. Una línea por archivo y un resumen, sin texto de los documentos |
| 5. Rutas del investigador (listar, subir, confirmar incompleto, retirar) | Hecha | `app/api/corpus.py`: cinco rutas nuevas en la matriz de autorización. `GET /investigador/colecciones` muestra ahora el `id` |
| 6. Registrar por tema las referencias excluidas por no tener acceso abierto | Hecha la estructura | Tabla `exclusion_corpus` con el motivo `sin_acceso_abierto`, contadores y `GET /investigador/colecciones/{id}/exclusiones`. Quien detecta la falta de acceso abierto es el importador de T15 (Unpaywall, T14) |
| 7. Ingerir el corpus provisional del carril de insumos | **Hecha** (19 de noviembre de 2026) | Apartado 13.8: 99 documentos indexados en 2 temas, sin fragmentos ajenos al tema |
| Tarea: reindexación completa si cambia el modelo de embeddings | Hecha | `python -m app.corpus.reindexar [--forzar]`. Cada documento guarda modelo y revisión de sus vectores |
| Tarea: el documento guarda la URL de acceso abierto y la licencia; fragmentos breves con enlace | Parcial | Las columnas existen desde T04 y ninguna ruta sirve el PDF. Los valores los obtiene T15 con Unpaywall; los fragmentos breves se muestran desde T16 y T19 |

### 13.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| CP-21 superado (documento ilegible, escaneado sin texto o duplicado: rechazo con motivo) | **Cumplido** | `test_corpus.py` con la base real: escaneado e ilegible se rechazan con su motivo una sola vez; duplicado por texto y por DOI. `test_corpus_real.py` con Docling real sobre los siete PDF de muestra: cifrado y escaneado excluidos, y el PDF con solo restricción de permisos detectado como duplicado del documento corto |
| Reingerir el mismo PDF no duplica documentos ni fragmentos | **Cumplido** | Por la ruta (`ya_registrado`, sin volver a procesar) y por el comando: la segunda pasada sobre la misma carpeta da `ya_registrado` en los 7 archivos, con la base real y Docling real |
| Una consulta densa y una léxica de prueba devuelven fragmentos con sección y páginas de la colección indicada | **Cumplido** | `test_corpus.py` con dos temas: solo fragmentos del tema consultado, con sección, título original y páginas. Verificado también con bge-m3 real (apartado 13.3) |

### 13.3. Pruebas y verificación

| Suite | Resultado |
| --- | --- |
| API completa (`docker compose run --rm --build pruebas`, con recursos del canal) | **391 superadas**, 5 omitidas (servicios compartidos y una comparación que necesita el árbol completo); cobertura de `app/` **97,02 %** |
| `integracion/test_corpus.py` (nueva) | 14: indexación con trazabilidad, idempotencia, duplicados, exclusiones, incompletos y confirmación, retiro, consultas densa y léxica por colección, reindexación, colecciones admitidas, límite de tamaño, ingesta sin configurar (503), comando y contexto de consola |
| `integracion/test_corpus_real.py` (nueva, marcas `corpus` e `integracion`) | 1: CP-21 con Docling real y la base real sobre los siete PDF de muestra |
| `integracion/test_comandos_corpus.py` (nueva) | 3: comandos de ingesta y reindexación de punta a punta, errores y fábrica |
| `unitarias/test_corpus_almacen.py` (nueva) | 9: almacén con nombre aleatorio, nombres seguros y mensajes de los motivos |
| `alembic check` y ciclo de 0009 | Sin diferencias entre modelos y migraciones; 0009 baja y sube |

**Verificación de punta a punta con los servicios reales**, en un proyecto de Compose aislado (`sma_verif`), borrado al terminar, y con el GROBID y el servicio de modelos del proyecto compartido:

| Paso | Resultado |
| --- | --- |
| Ingesta de los siete PDF de muestra con el comando | 2 indexados (8 y 9 fragmentos), 2 incompletos, 2 excluidos (cifrado y escaneado) y 1 duplicado, en 62 s (incluye cargar Docling y los modelos) |
| Segunda pasada | 7 `ya_registrado` en 10 s |
| Consulta densa con bge-m3: "¿La tutoría entre pares reduce la ansiedad ante la estadística?" | Resumen (0,858), conclusiones (0,843) y discusión (0,802) del artículo en español, con sección, título y páginas, en 0,3 s |
| Consulta densa: "Does short sleep before an exam lower statistics scores?" | Discusión, introducción y conclusión del artículo en inglés |
| Consulta densa en español: "cuántos estudiantes participaron en el estudio" | Métodos de los dos artículos ("2.1. Diseño y participantes" y "2.1. Participants"): la búsqueda funciona entre idiomas |
| Consultas léxicas "covarianza", "Cronbach" y "actigraphy" | El fragmento exacto de métodos o discusión |

**Integración continua:** el trabajo `corpus` suma PostgreSQL con pgvector y corre también `test_corpus_real.py`. Las pruebas con dobles corren en el trabajo de pruebas.

**Otras verificaciones:**
- Ruff, `ruff format --check` y mypy estricto sin errores (73 archivos).
- Diccionario de datos regenerado.

### 13.4. Problemas encontrados y soluciones

| Problema | Solución |
| --- | --- |
| Docling se carga una sola vez, pero los parámetros del canal salen de la configuración vigente, que puede cambiar | `CanalPdf.con_parametros` aplica en cada ingesta los parámetros vigentes sobre el mismo extractor |
| La prueba de arquitectura no permite `AsyncSession` fuera de `repositorios/` | La fábrica de unidades para los comandos vive en `repositorios/unidad.py` |
| La red `sma_compartido` solo existe si los servicios compartidos están levantados | La API se une a ella con `docker-compose.corpus.yml`, aparte, para no romper `docker compose up` |
| La prueba del límite de tamaño cambiaba la configuración versión 1 y la limpieza entre pruebas no la restaura | La prueba restaura el valor |
| Una prueba de T07 comparaba la lista de colecciones sin `id` | Se actualizó |

### 13.5. Riesgos para fases posteriores

- **Memoria en la instancia:** la primera subida de un PDF carga Docling en la API (pico de 1,1 GB). En el equipo de desarrollo, GROBID ocupó 2,6 a 3,2 GB y el servicio de modelos 1,7 GB durante la verificación. Si en la instancia no alcanza, la ingesta puede quedar solo en el comando.
- **T15:** el importador debe registrar las referencias sin acceso abierto en `exclusion_corpus` (`objeto = referencia`, motivo `sin_acceso_abierto`) y llevar `n_pendientes`.
- **T16:** la recuperación debe filtrar por documentos recuperables (`repositorios/corpus.recuperable`) y por las colecciones permitidas al caso (RN-03). Las consultas de prueba de T10 no reemplazan esa recuperación.
- **T22:** abrir la ingesta al corpus de guías con su segmentación por apartado y revisar RN-11.

### 13.6. Archivos

**Creados:**
- `backend/app/corpus/` (`almacen`, `fabrica`, `indexacion`, `ingesta`, `reindexar`), `backend/app/api/corpus.py`, `backend/app/repositorios/corpus.py` y `backend/app/seguridad/consola.py`.
- `backend/migraciones/versiones/0009_indices_y_exclusiones_del_corpus.py`.
- `backend/pruebas/dobles_corpus.py`, `backend/pruebas/unitarias/test_corpus_almacen.py` y `backend/pruebas/integracion/` (`test_corpus`, `test_corpus_real`, `test_comandos_corpus`).
- `docker-compose.corpus.yml`.
- `docs/decisiones/T10-indexacion-y-gestion-del-corpus.md`.

**Modificados:**
- `backend/app/bd/modelos/corpus.py` y `enumeraciones.py` (tabla `exclusion_corpus`, columnas de `documento` e índices).
- `backend/app/api/investigador.py` (`id` en las colecciones), `backend/app/main.py`, `backend/app/repositorios/unidad.py`, `backend/app/corpus/extraccion.py` (`con_parametros`) y `backend/app/configuracion/ajustes.py` (`DIRECTORIO_ARCHIVOS`).
- `backend/pyproject.toml` y `backend/restricciones-corpus.txt` (`python-multipart`), `backend/Dockerfile` (carpeta `/archivos`) y `docker-compose.yml` (volúmenes de la API).
- `.github/workflows/ci.yml` (base en el trabajo `corpus`) y `.env.example`.
- `backend/pruebas/matriz_autorizacion.py`, `unitarias/test_arquitectura.py` e `integracion/test_casos.py`.
- `docs/diccionario-de-datos.md`, `README.md`, `CLAUDE.md` y este archivo.

### 13.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmación | `t10-indexacion-corpus`, confirmación `8b9db98` (`T10: indexar y gestionar el corpus científico`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#5 |
| CI de la solicitud | **Verde**, ejecución 43351749127: 7 de 7 trabajos. El trabajo `corpus` pasó 9 pruebas con Docling real (incluida la de CP-21 con la base real) y no encontró vulnerabilidades |
| Integración en `main` | Commit de integración `f11a403` |
| CI de `main` tras integrar | Ejecución 43352375288: **verde** |

### 13.8. Corpus provisional (actividad 7) e insumos de prueba

Rama `t10-corpus-provisional`. Insumos entregados por el equipo el 12 de noviembre de 2026 en `datos/` (excluida de Git: no se versiona ningún PDF):

- **Artículos base** (`datos/articulos-base/<tema>/`): 5 por tema, empíricos, en español y de acceso abierto. De ellos saldrán los borradores de prueba. **No se ingieren al corpus**: contaminarían la recuperación, igual que RN-19 lo prohíbe con el artículo O1.
- **Corpus provisional** (`datos/corpus-provisional/<tema>/`): las referencias de acceso abierto de los artículos base.
- **Temas:** `tema-1-ia-educacion` y `tema-2-transformacion-digital-mypes`, con colecciones científicas `TEMA-1-IA-EDUCACION` y `TEMA-2-TRANSFORMACION-DIGITAL-MYPES` en la base de desarrollo.

**Pendiente del carril de insumos antes de T19:** los borradores de prueba elaborados desde los artículos base, con su hoja de errores introducidos a propósito (especificación de la Fase 1, 7: estructura, método, redacción y referencias).

#### Armado del corpus

Como el importador de T15 todavía no existe, el corpus se armó con un script de apoyo fuera de la aplicación, `scripts/armar_corpus_provisional.py`. Por cada referencia de cada artículo base:

1. Extrae la lista de referencias con GROBID (`processReferences`, sin consolidar).
2. Resuelve el DOI con Crossref. Si GROBID trae un DOI, lo comprueba. Si no, busca por metadatos y acepta el resultado solo si coinciden el título (similitud de 0,88 o más), el año (con un año de tolerancia) y al menos un apellido (18.9).
3. Consulta el acceso abierto con Unpaywall.
4. Descarga los PDF con enlace directo. Solo acepta PDF válidos de hasta 25 MB y no repite un DOI dentro del tema.

El script hace una solicitud cada 0,5 s por servicio, reintenta con espera ante los errores 429 y 5xx, y usa el correo de `CORREO_POLITE` en Crossref y Unpaywall. El informe por referencia queda en `datos/corpus-provisional/informe.csv`.

Estados del informe: los tres pedidos (incluida, cerrada y no localizada) más dos necesarios:
- `pendiente_pdf`: tiene acceso abierto, pero no hay enlace directo o la descarga falló. Es lo que la especificación llama "pendiente de PDF", que sube el investigador.
- `articulo_base`: la referencia es otro artículo base y no entra al corpus.

| Tema | Referencias | Incluidas | Pendientes de PDF | Cerradas | No localizadas | Artículo base | PDF únicos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tema-1-ia-educacion | 194 | 79 | 28 | 16 | 70 | 1 | **72** |
| tema-2-transformacion-digital-mypes | 279 | 38 | 64 | 72 | 105 | 0 | **35** |

"Incluidas" cuenta las referencias; varias apuntan al mismo PDF desde distintos artículos base, por eso los PDF únicos son menos. Ningún tema quedó por debajo de 20 PDF.

**Desglose por artículo base** (referencias, incluidas, pendientes, cerradas y no localizadas):

| Tema | Artículo base | Ref. | Incl. | Pend. | Cerr. | No loc. |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ChatGPT como fuente de información en la Educación | 53 | 17 | 7 | 6 | 23 |
| 1 | El impacto del ChatGPT en el aprendizaje activo | 41 | 18 | 5 | 1 | 17 |
| 1 | Inteligencia artificial generativa en ingresantes | 40 | 20 | 7 | 8 | 5 |
| 1 | Perspectivas del uso de IA generativa ChatGPT (1 referencia es otro artículo base) | 30 | 15 | 6 | 1 | 7 |
| 1 | Validación del cuestionario para docentes | 30 | 9 | 3 | 0 | 18 |
| 2 | Adopción de e-marketing en mipymes mexicanas | 70 | 9 | 24 | 26 | 11 |
| 2 | Factores críticos para la adopción de las TIC | 26 | 1 | 8 | 7 | 10 |
| 2 | Factores tecnológicos y comercio electrónico en León | 68 | 5 | 5 | 6 | 52 |
| 2 | Adopción del e-commerce con el modelo TOE en Paraguay | 58 | 6 | 4 | 24 | 24 |
| 2 | Transformación digital y rentabilidad en MYPES peruanas | 57 | 17 | 23 | 9 | 8 |

**Observaciones:**
- **Pendientes de PDF (92):** 42 no tienen enlace directo al PDF. Las demás fallaron por respuestas HTTP del sitio, documentos que no eran PDF, tiempos de espera o certificados. Pueden subirse a mano.
- **No localizadas:** son más en el tema 2, sobre todo en el artículo de León (52 de 68), con muchas referencias a libros, informes y fuentes sin DOI.
- **Licencias** de los PDF descargados según Unpaywall: CC BY (43), CC BY-NC-SA (16), CC BY-NC (15), CC BY-NC-ND (15), CC BY-SA (3), CC BY-ND (1) y 14 sin licencia declarada. El sistema muestra fragmentos breves con enlace y no redistribuye los PDF (18.10).

#### Ingesta (actividad 7)

Se ingirió cada carpeta con `python -m app.corpus.ingesta` en la base de desarrollo, con la cuenta `INV-DEV` (registro en `datos/corpus-provisional/ingesta-20261113.log`):

| Colección | PDF | Indexados | Incompletos | Excluidos | Ya registrados | Fragmentos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TEMA-1-IA-EDUCACION | 72 | 66 | 3 | 3 | 0 | 1 889 |
| TEMA-2-TRANSFORMACION-DIGITAL-MYPES | 35 | 33 | 0 | 1 | 1 | 896 |

- **Excluidos (4), con su motivo en `exclusion_corpus`:** 3 superan el límite de páginas (`excede_paginas`) y 1 no tiene capa de texto (`sin_capa_de_texto`).
- **Incompletos (3):** uno sin secciones IMRaD, uno con texto insuficiente y uno con ambos motivos. Sus 26 fragmentos no tienen vector ni se recuperan hasta que el investigador los confirme (RN-14).
- **Ya registrado (1):** el preprint de OSF es el mismo archivo que otro de la carpeta; no se duplicó.

**Referencias en los fragmentos.** La primera ingesta dejó 44 fragmentos con forma de lista de referencias en 8 documentos. Se corrigió la segmentación (decisión T09-01, apartado 10) y se volvió a segmentar el corpus el 19 de noviembre de 2026 con `python -m app.corpus.resegmentar --aplicar` (registros `resegmentacion-20261119*.log`):

| Pasada | Documentos actualizados | Tiempo |
| --- | --- | --- |
| Primera, con Docling (llena la caché) | 33 del tema 1 y 5 del tema 2 | 1 639 s y 908 s la simulación; 240 s y 77 s al aplicar, desde la caché |
| Tras auditar la regla (apartado 10: 19 párrafos de prosa recuperados) | 6 y 4 | 19 s y 13 s la simulación; 45 s y 67 s al aplicar |

En cada documento actualizado se conservó el vector de los fragmentos que no cambiaron y solo se embebieron los nuevos. Resultado: los fragmentos con 3 DOI o más pasaron de 44 a **1** de 2 785, y ningún fragmento indexado quedó sin vector.

**Consulta de prueba por tema** (densa con bge-m3 real y léxica, en cada colección con su propia pregunta y con la del otro tema): **0 fragmentos ajenos** al tema en las 6 consultas. Por ejemplo, "uso de ChatGPT e inteligencia artificial generativa por estudiantes universitarios" en el tema 1 devuelve fragmentos sobre ChatGPT en la educación superior (similitud de 0,80 a 0,82). La misma pregunta en el tema 2 devuelve, con similitud de 0,50 a 0,52, solo documentos del tema 2 (adopción de IA en pymes).

**Respaldo:** `datos/respaldos/corpus-provisional-20261119` (base, 15,5 MB, y archivos con la caché, 78,8 MB). Se restaura en minutos con `python scripts/respaldo_corpus.py restaurar datos/respaldos/corpus-provisional-20261119 --confirmar`.

**Actividad 7: cumplida.**

### 13.9. Optimización del flujo de desarrollo (antes de cerrar la actividad 7)

La primera ingesta completa del corpus provisional tardó más de 2 horas en el portátil de desarrollo y se detuvo a mano. Antes de cerrar la actividad 7 se optimizó el flujo **sin cambiar los modelos** (bge-m3, bge-reranker-v2-m3 y el modelo de diseño de página de Docling). Decisión: `docs/decisiones/T10-02-optimizacion-flujo-desarrollo.md` (T10-02).

**Medición antes y después** con los mismos 3 PDF reales (89 páginas, 192 fragmentos), en un proyecto aislado con la base vacía:

| Etapa | Antes | Después |
| --- | ---: | ---: |
| Validación | 21 s | 7 s |
| Extracción con Docling | 143 s | 137 s |
| Segmentación | 2 s | 2 s |
| Cabecera (GROBID) | 19 s | 42 s (37 s de carga del modelo en el primer PDF) |
| Embeddings | 385 s | 321 s |
| Escritura en la base | 1 s | 1 s |
| **Total** | **589 s** | **524 s (11 % menos)** |
| Pico de GROBID | 3,48 GB | 3,42 GB (0,32 GB en reposo, antes 3,1 GB) |
| Pico del servicio de modelos | 1,99 GB | 1,52 GB |
| Pico del proceso de ingesta | 3,37 GB | 2,29 GB |
| **Suma de picos** (máquina virtual de 7,76 GB) | **8,9 GB** | **7,4 GB** |

**Dónde se iba el tiempo:** en los embeddings (65 %) y en Docling (24 %). Los dos dependen de modelos que no cambian, así que el cómputo baja poco. Lo que explicaba las más de 2 horas era la memoria: la suma de picos superaba la de la máquina virtual y el sistema paginaba. Ahora queda debajo de 8 GB.

**Cambios (todos verificados):**

| Punto del pedido | Qué se hizo | Verificación |
| --- | --- | --- |
| 1. Medición por etapa | `app/corpus/medicion.py`: tiempo y pico de memoria por etapa en cada línea de la ingesta y en el resumen | Tabla anterior |
| 2. Caché de Docling | `app/corpus/cache_extraccion.py`, por huella del PDF y firma del extractor, en `/archivos/extraccion/`. Comando `python -m app.corpus.resegmentar`, que reutiliza los vectores del texto que no cambia | Re-segmentar los 3 PDF: 12 s, 3 aciertos y ninguna extracción. Pruebas unitarias y de integración |
| 3. Docling liviano | Ya sin OCR ni tablas (T09-01). Se agregaron lote 1 y cola 4: mismo texto, 0,9 GB menos. Se descartó el lector pypdfium2 porque duplicaba texto (+16,8 % de palabras). Validación de capa de texto con una muestra de 12 páginas | Comparación fragmento por fragmento con la configuración anterior |
| 4. Ingesta reanudable | Por documento, con avance (posición, porcentaje, transcurrido, restante) y mensaje de reanudación ante Ctrl+C | Prueba de integración: detenida tras el primer documento, la segunda pasada procesa solo el que faltaba |
| 5. Subconjunto de desarrollo | `scripts/crear_subconjunto_desarrollo.py`: 3 PDF de 10 páginas por tema en `datos/corpus-desarrollo/`. Corpus completo solo con `scripts/ingesta-programada.ps1` (no se registró ninguna tarea programada) | Subconjunto creado: 6 PDF |
| 6. Respaldo y restauración | `scripts/respaldo_corpus.py respaldar` y `restaurar --confirmar`: base, volumen de archivos con la caché y manifiesto con huellas | En el proyecto aislado: tras borrar los fragmentos y la caché, la restauración devolvió 3 documentos, 192 fragmentos con vector y 3 entradas de caché |
| 7. Memoria en 8 GB | Reordenador cargado al primer uso; PyTorch con los 6 procesadores (antes 3, vectores idénticos); GROBID con `modelPreload: false` y 2 solicitudes simultáneas (`compartido/grobid/grobid.yaml`); 1 PDF a la vez, lote de 16 textos y 1 inferencia simultánea | Suma de picos de 7,4 GB |

**Pruebas:** backend con 422 pruebas superadas y 5 omitidas (incluidas las de la regla de referencias ajustada), cobertura del 94,46 %; servicio de modelos con 28 superadas. Ruff y mypy sin observaciones.

**Proyección del corpus completo** (unas 2 500 páginas y 2 850 fragmentos): unas 2,5 horas sin paginación, según las velocidades medidas. Es una estimación.

**Archivos:**
- Creados: `backend/app/corpus/` (`medicion.py`, `cache_extraccion.py`, `resegmentar.py`), `backend/pruebas/unitarias/test_corpus_cache_y_avance.py`, `servicio_modelos/pruebas/test_perezoso.py`, `compartido/grobid/grobid.yaml`, `scripts/` (`respaldo_corpus.py`, `crear_subconjunto_desarrollo.py`, `ingesta-programada.ps1`) y `docs/decisiones/T10-02-optimizacion-flujo-desarrollo.md`.
- Modificados: `backend/app/corpus/` (`extraccion.py`, `extractor_docling.py`, `fabrica.py`, `indexacion.py`, `ingesta.py`, `validacion.py`), `backend/app/repositorios/corpus.py`, `backend/app/configuracion/ajustes.py` (`HILOS_DOCLING`), `servicio_modelos/servicio/` (`ajustes.py`, `aplicacion.py`, `esquemas.py`, `motores.py`, `motor_transformers.py`), `compartido/docker-compose.yml`, `.env.example`, `compartido/.env.example`, pruebas de integración del corpus, `README.md` y `CLAUDE.md`.

### 13.10. Integración de la actividad 7 y de la optimización

| Paso | Resultado |
| --- | --- |
| Rama y confirmación | `t10-corpus-provisional`, confirmación `320f478` (`T10: ingerir el corpus provisional y optimizar el flujo de desarrollo`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#6 |
| CI de la solicitud | **Verde**, ejecución 44602405220: 7 de 7 trabajos, incluidos el canal de PDF con Docling real y el servicio de modelos |
| Integración en `main` | Commit de integración `a03e359` |
| CI de `main` tras integrar | Ejecución 44609405880: **verde** |

**Demostración para el asesor** (DavidAndreRoca/SistemaMultiagenteRag#3, rama `demo-asesor`): integrada en `main` el 19 de noviembre de 2026, con el commit de integración `cf9afa3`. Agrega `docs/demo/guia-demostracion.md` y `scripts/demo.ps1`, `demo-funciones.ps1` y `demo-detener.ps1`, sin código de la aplicación. Su CI (ejecución 42528177792, 6 de 6 trabajos) es anterior a T09 y T10. Como solo agrega una guía y guiones de PowerShell que la CI no ejecuta, antes de integrarla se comprobó a mano que:
- todo lo que usan sigue existiendo en `main`: los servicios `bd`, `migrar` y `api`, el perfil `descarga` y los módulos `app.bd.semillas` y `app.seguridad.crear_investigador`;
- los tres guiones no tienen errores de sintaxis.

La demostración no se volvió a ejecutar de punta a punta.

---

## 14. Fase 3 (F3): T11. Borradores: carga, validación y versiones

Rama `t11-borradores`, desde `main` con T10 y la demostración (`cf9afa3`). Decisión: `docs/decisiones/T11-borradores.md` (T11-01).

**CP-01 y CP-02, contrastados con el texto oficial de la tesis** (Tabla 20, copiada en `docs/especificacion-fase1/casos-de-prueba-tesis.md`):
- **CP-01 (CU-01):** un .docx de un caso registrado registra una versión nueva con fecha y hora, y las versiones anteriores se conservan.
- **CP-02 (CU-01, E1):** un archivo de formato distinto de .docx o dañado se rechaza, se informa el motivo y no se registra ninguna versión.

La primera versión de las pruebas se basó en la especificación y difería en dos puntos, ya corregidos:
- **CP-01** comprobaba una sola carga; la conservación de las anteriores estaba en otra prueba. Ahora la misma prueba hace dos cargas y comprueba que la primera se conserva entera (registro, párrafos y archivo).
- **CP-02** incluía macros, cifrado y contenido anómalo, que vienen de RN-16. Le faltaban archivos con otra extensión. Ahora CP-02 prueba 10 casos de formato distinto (.pdf, .doc, .odt, .txt, sin extensión, renombrados) o dañados. Los de RN-16 quedan en una prueba aparte, con las mismas garantías.

### 14.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Validación: extensión, tipo MIME, firma del contenedor, tamaño (15 MB), tamaño descomprimido; rechazo de `.docm`, cifrados y dañados | Hecha | `app/borradores/validacion.py`, en 9 pasos y con 5 motivos (T11-01, apartado 2). También rechaza controles ActiveX y DTD (bombas XML). El tipo MIME real se lee de `[Content_Types].xml` |
| 2. Almacenamiento con nombre aleatorio fuera de la carpeta pública y huella SHA-256 | Hecha | `DIRECTORIO_ARCHIVOS/borradores/<uuid>.docx`, con el almacén generalizado en `app/comun/almacen.py`. El nombre original no se guarda ni se registra: suele llevar el nombre del estudiante |
| 3. Versión por hito: la nueva queda vigente sin borrar las anteriores | Hecha | `RepositorioVersiones.registrar_vigente`, con la fila del caso bloqueada. El índice único parcial de T04 garantiza una vigente por caso y hito |
| 4. Texto y párrafos con identificador estable | Hecha | `app/borradores/extraccion.py`: `p1`, `p2`, etc., con texto, estilo y origen (cuerpo o tabla). Incluye las citas de los gestores bibliográficos como se ven y el control de cambios aceptado. Se guardan en `version_borrador.parrafos` (migración 0010) |
| 5. Rutas del caso: cargar, listar y ver metadatos | Hecha | `POST /caso/versiones`, `GET /caso/versiones` (con `?hito=`) y `GET /caso/versiones/{id}`, en la matriz de autorización |
| Tarea: el texto se guarda para servir alcances; el archivo no va al proveedor | Hecha | Ninguna ruta devuelve el archivo ni el texto; el texto queda en la base para T12 y T13 |
| Tarea: primera versión de un hito, respuesta informativa | Hecha | `primera_del_hito` y un mensaje en la respuesta |

### 14.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| CP-01 superado | **Cumplido** | `test_cp01_carga_valida_registra_la_version_y_conserva_las_anteriores` (integración, base real). La carga válida responde 201 con la versión, el hito, la fecha y hora del reloj, la huella y el tamaño. Una segunda carga crea otra versión con su propia fecha y hora, y la primera se conserva entera (registro, párrafos y archivo) |
| CP-02 superado | **Cumplido** | `test_cp02_formato_distinto_o_danado_se_rechaza_sin_registrar_version` (integración), con 10 archivos de formato distinto de .docx o dañados. En cada uno, la carga se rechaza con el formato único de error y el motivo, no queda versión ni archivo, y se registra un evento `validacion_borrador` sin el nombre del archivo. Aparte, RN-16: macros, cifrado, contenido anómalo y más de 15 MB. Cada motivo tiene además su prueba unitaria |
| Un caso no ve ni descarga versiones de otro | **Cumplido** | La versión del caso A responde 404 al caso B, y su lista no la incluye. La matriz de autorización lo comprueba en las tres rutas con una versión real. No hay ruta de descarga |
| Cada carga crea una versión nueva con fecha, hora e hito | **Cumplido** | Tres cargas (dos del mismo hito, con el mismo archivo) dejan tres versiones y una sola vigente por hito. Tres cargas simultáneas dejan una sola vigente |

### 14.3. Pruebas

- **Backend en contenedor:** 462 pruebas superadas y 5 omitidas; cobertura del 94,59 %. Ruff y mypy sin observaciones.
- **Migración 0010:** aplicada a la base de desarrollo (0009 a 0010); `alembic check` no encuentra diferencias. El ascenso y descenso completos se prueban en `test_migraciones.py`.
- **Nuevas:**
  - `unitarias/test_borradores.py` (19): validación con cada archivo malicioso, extensión, tipo declarado, proporción y número de partes, y extracción (campos, control de cambios, controles de contenido, tablas).
  - `integracion/test_borradores.py` (21): CP-01, CP-02 (10 casos), RN-16 (4 casos), versiones, concurrencia, límite de tamaño, hito desconocido, aislamiento y servidor sin configurar.
  - La matriz de autorización ahora envía formularios con archivo y usa una versión real del caso A.

### 14.4. Problemas encontrados y soluciones

- **Celdas combinadas repetidas:** python-docx devuelve la misma celda combinada varias veces. Deduplicarlas por `id()` fallaba porque lxml recicla esos identificadores. Se deduplican guardando los elementos en un conjunto.
- **Dependencia en la imagen:** la imagen instala el árbol fijado de `restricciones-corpus.txt`, así que python-docx 1.2.0 (MIT) se agregó allí además de en `pyproject.toml`. Sus dependencias ya estaban en el árbol.

### 14.5. Pendientes y riesgos

- **CP-01 y CP-02:** contrastados con la Tabla 20 y ajustados (inicio de este apartado).
- **Tabla 20:** completa desde el 19 de noviembre de 2026 (CP-01 a CP-23 y PI-01 a PI-09).
- **Notas al pie y cuadros de texto:** python-docx no los lee, así que no se extraen (T11-01, apartado 7).
- **Borradores reales de prueba:** siguen pendientes del carril de insumos (apartado 13.8). La extracción se probó solo con documentos ficticios generados.

### 14.6. Archivos

- **Creados:**
  - `backend/app/borradores/` (`validacion.py`, `extraccion.py`, `servicio.py`), `backend/app/api/borradores.py` y `backend/app/comun/almacen.py`;
  - `backend/migraciones/versiones/0010_parrafos_del_borrador.py`;
  - `backend/pruebas/datos/generar_docx_muestra.py` y `backend/pruebas/datos/docx/` (14 archivos ficticios), `backend/pruebas/unitarias/test_borradores.py` y `backend/pruebas/integracion/test_borradores.py`;
  - `docs/decisiones/T11-borradores.md` y `docs/especificacion-fase1/casos-de-prueba-tesis.md` (Tabla 20, por ahora con CP-01 y CP-02).
- **Modificados:**
  - `backend/app/bd/modelos/borradores.py`, `backend/app/repositorios/caso.py`, `backend/app/corpus/almacen.py` y `backend/app/main.py`;
  - `backend/pyproject.toml` y `backend/restricciones-corpus.txt`;
  - `backend/pruebas/matriz_autorizacion.py`, `integracion/test_matriz_autorizacion.py` e `integracion/conftest.py` (`DIRECTORIO_ARCHIVOS` en las pruebas);
  - `docs/diccionario-de-datos.md`, `README.md`, `CLAUDE.md` y este archivo.

### 14.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t11-borradores`: `6ba6b18` (`T11: cargar, validar y versionar el borrador .docx`) y `09e40dc` (contraste de CP-01 y CP-02 con la Tabla 20 y cierre de T09-01), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#7 |
| CI de la solicitud | **Verde** en las dos confirmaciones: ejecuciones 44621189670 y 44627359546 (la de `09e40dc`), 7 de 7 trabajos cada una |
| Integración en `main` | Commit de integración `be91006` |
| CI de `main` tras integrar | Ejecución 44630084125: **verde** |

---

## 15. Fase 3 (F3): T12. Secciones del borrador y alcance

Rama `t12-secciones-alcance`, desde el último commit de T11 (`09e40dc`, ya integrado en `be91006`). Decisión: `docs/decisiones/T12-secciones-y-alcance.md` (T12-01).

**CP-09, contrastado con la tesis** (`docs/especificacion-fase1/casos-de-prueba-tesis.md`, ya completa, entregada por el equipo el 19 de noviembre de 2026). Pide que un fragmento de más de un párrafo o de más de unas 250 palabras haga que el sistema pida uno más corto y no procese la solicitud. La primera versión de la fase solo validaba las palabras. Una selección de varios párrafos (`p3-p5`) se rechazaba como `parrafo_inexistente`, sin pedir un fragmento más corto. Se agregó el rechazo `fragmento_de_varios_parrafos` con sus pruebas, en la misma solicitud de cambio.

### 15.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Detectar secciones por estilos de título | Hecha | `app/borradores/secciones.py`. El nivel sale del esquema del párrafo, del nombre del estilo ("Heading N", "Título N", "Encabezado N") o del esquema de sus estilos base. Árbol `s1`, `s2`… con nivel, padre, clase (clasificador del corpus) y párrafos. Se ejecuta en cada carga |
| 2. Selección manual de respaldo sin estilos | Hecha | Sin títulos, la carga lo informa y pide marcarlos. `PUT /caso/versiones/{id}/secciones` guarda los títulos marcados con el método `manual` |
| 3. Sección de referencias y sus entradas; indicarla a mano | Hecha | Automática por la clase del título. `PUT /caso/versiones/{id}/referencias` marca a mano un rango de párrafos. Una entrada por línea no vacía, sin interpretar nada (RN-17) |
| 4. `estructura_borrador(version)` | Hecha | Árbol de títulos, método, sección de referencias y ubicaciones del problema, los objetivos y las hipótesis, por el título o por el texto, en español e inglés. Excluye las referencias y las tablas |
| 5. Validación de alcance por tipo; límite de 250 palabras para D3 (CP-09) | Hecha | `app/borradores/alcance.py`: alcances admitidos por tipo, existencia de la sección o del párrafo, límite de D3 desde la configuración (`limite_palabras_d3`) y límites de la consulta. Devuelve el texto del alcance |
| Tarea: identificadores estables de sección y párrafo por versión | Hecha | `p1`… (T11) y `s1`…. Mientras una solicitud use la versión, sus secciones no se pueden cambiar (409 `version_en_uso`) |
| Tarea: tolerancia a campos de gestores bibliográficos | Hecha | La extracción recorre los controles de contenido de bloque, donde Mendeley y Word ponen la bibliografía, y conserva los saltos de línea. Las citas de Mendeley (campo y control de contenido) y de Zotero quedan como se ven, sin su código |

### 15.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Un .docx con estilos produce sus secciones; uno sin estilos pide selección manual y la guarda | **Cumplido** | `integracion/test_secciones_borrador.py`, con la base real. `estructura.docx` da 11 secciones con estilos integrados, propios y por nivel de esquema, y 3 referencias. `sin_estilos.docx` responde con el pedido de marcar las secciones; tras marcarlas, quedan guardadas con el método `manual` y el detalle de la versión lo refleja |
| CP-09: un fragmento de más de un párrafo o de más de unas 250 palabras se rechaza pidiendo uno más corto | **Cumplido** | `unitarias/test_secciones_borrador.py`. **Palabras:** 251 se rechazan con `alcance_demasiado_largo` y un mensaje que dice cuántas tiene, el límite y "Seleccione un fragmento más corto"; 250 se admiten y el límite sale de la configuración. **Varios párrafos:** 8 formas de selección (lista, rango, con semirraya) se rechazan con `fragmento_de_varios_parrafos` para D3 y para la búsqueda de evidencia; `p7-p7` y un párrafo con saltos de línea son uno solo. También se comprueba sobre una versión guardada en la base |

### 15.3. Pruebas

- **Backend en contenedor:** 540 pruebas superadas y 5 omitidas; cobertura del 95,01 %. Ruff y mypy sin observaciones.
- **Nuevas:**
  - `unitarias/test_secciones_borrador.py` (67): secciones con .docx variados (con y sin estilos, Mendeley, Zotero, tablas), referencias automáticas y manuales, selección manual y sus validaciones, `estructura_borrador`, y validación de alcance para los seis tipos con los cinco alcances (30 combinaciones), más CP-09.
  - `integracion/test_secciones_borrador.py` (11): las rutas nuevas, la versión en uso y el aislamiento.
  - La matriz de autorización incluye las tres rutas nuevas.
- **Archivos de muestra nuevos:** `estructura.docx`, `sin_estilos.docx`, `mendeley.docx` y `zotero.docx` (ficticios).

### 15.4. Problemas encontrados y soluciones

- **La bibliografía de Mendeley se perdía:** python-docx no recorre los controles de contenido de bloque. Se corrigió la extracción de T11 (T12-01, apartado 2).
- **Las referencias en un solo párrafo no se podían separar:** los saltos de línea se convertían en espacios. Ahora se conservan.

### 15.5. Pendientes

- **Pistas de problema, objetivos e hipótesis:** se calibrarán con los borradores reales de prueba, que siguen pendientes del carril de insumos.

### 15.6. Archivos

- **Creados:** `backend/app/borradores/secciones.py` y `alcance.py`, `backend/pruebas/unitarias/test_secciones_borrador.py`, `backend/pruebas/integracion/test_secciones_borrador.py`, cuatro .docx de muestra y `docs/decisiones/T12-secciones-y-alcance.md`.
- **Modificados:** `backend/app/borradores/extraccion.py` y `servicio.py`, `backend/app/api/borradores.py`, `backend/app/repositorios/caso.py` (`hay_de_version`), `backend/pruebas/datos/generar_docx_muestra.py`, `backend/pruebas/matriz_autorizacion.py`, `docs/decisiones/T11-borradores.md`, `README.md`, `CLAUDE.md` y este archivo.

### 15.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t12-secciones-alcance`: `fe9f35c` (`T12: detectar secciones del borrador, separar referencias y validar el alcance`) y `e3d848f` (rechazo de fragmentos de más de un párrafo, CP-09), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#8 |
| CI de la solicitud | **Verde** en las dos confirmaciones: ejecuciones 44630350926 y 44637373011 (la de `e3d848f`), 7 de 7 trabajos |
| Integración en `main` | Commit de integración `f534de0` |
| CI de `main` tras integrar | Ejecución 44639715850: **verde** |

---

## 16. Fase 3 (F3): T13. Interfaz base

Rama `t13-interfaz-base`, desde `main` con T12 (`f534de0`). Decisión: `docs/decisiones/T13-interfaz-base.md` (T13-01). El equipo eligió React Aria Components como biblioteca de componentes el 19 de noviembre de 2026.

### 16.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Aplicación React con TypeScript y Vite en `frontend/` | Hecha | React 19.3.1, TypeScript 5.9.3 estricto, Vite 8.3.6 y React Router 8.5.1, todo con versión exacta y árbol fijado. Herramientas en Node 24.22.2 (contenedor), porque el Node del equipo es demasiado antiguo |
| 2. Biblioteca de componentes accesible, con su criterio | Hecha | React Aria Components 1.22.1, elegida por el equipo. Criterio y opciones en T13-01, apartado 2 |
| 3. Cliente tipado generado del contrato OpenAPI | Hecha | `python -m app.contrato` escribe `docs/api/openapi.json` y `npm run generar:api` genera los tipos. Una prueba del backend y la CI fallan si quedan desfasados |
| 4. Pantallas: inicio de sesión, cambio de contraseña inicial, panel del caso, carga y lista de versiones, y casos y colecciones del investigador | Hecha | `src/paginas/`. El panel muestra la versión vigente por hito y la invitación a cargar la primera. La pantalla del investigador permite crear temas y registrar casos, con las credenciales iniciales mostradas una sola vez |
| 5. Playwright y revisión automática de accesibilidad | Hecha | `e2e/flujo.spec.ts` con axe-core (WCAG 2.2 A y AA); `scripts/e2e.ps1` en local y el trabajo `interfaz_e2e` en la CI |
| 6. La aplicación detrás del mismo dominio que la API en desarrollo | Hecha | La interfaz llama a `/api/...` y Vite lo reenvía a la API. Servicio `interfaz` de Compose (perfil `interfaz`) |
| Tarea: manejo uniforme de errores del formato común | Hecha | `ErrorApi` en `src/api/cliente.ts` y `AvisoError`, con el mensaje y el identificador de incidencia |
| Tarea: rutas protegidas por rol | Hecha | `Protegida` en `src/App.tsx`. Con contraseña inicial pendiente, solo se puede cambiarla |
| Tarea: CI ampliada | Hecha | Trabajos `interfaz` (cliente al día, tipos, ESLint, formato, pruebas, compilación y `npm audit`) e `interfaz_e2e` |

### 16.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Playwright recorre inicio de sesión, carga y versión visible | **Cumplido** | El caso A ingresa, cambia su contraseña, elige el hito con el selector, elige `valido.docx` con el diálogo de archivo, la carga y ve "Es la primera versión del hito Avance 1." Su versión aparece "Vigente" en la lista y en la tabla por hito. Además, un archivo que no es .docx se rechaza con su motivo, sin crear versión |
| La revisión automática no encuentra errores de accesibilidad graves en estas pantallas | **Cumplido** | axe-core sin infracciones graves ni críticas en: inicio de sesión, casos y colecciones, panel sin versiones y panel con una versión. El recorrido con el tabulador del inicio de sesión sigue el orden visual, y el enlace para saltar al contenido aparece al recibir el foco |
| Un caso no ve datos de otro desde la interfaz | **Cumplido** | El caso B, registrado en el mismo tema, ve su panel sin versiones y nada del caso A. Al abrir `/investigador`, vuelve a su panel |

### 16.3. Pruebas

- **Extremo a extremo en local** (`scripts/e2e.ps1`, proyecto aislado `sma_e2e`): **4 de 4 superadas**.
- **Frontend:** 9 pruebas unitarias superadas (cliente y rutas protegidas). Tipos, ESLint (con jsx-a11y estricto) y Prettier sin observaciones. La compilación ocupa 146 KB comprimidos.
- **Backend en contenedor:** 541 pruebas superadas y 5 omitidas, cobertura del 94,97 %, con la prueba nueva del contrato al día y la de `GET /caso` con los hitos. Ruff y mypy sin observaciones.

### 16.4. Problemas encontrados y soluciones

- **npm 10 falla al resolver Vitest** con un error interno. Se resolvió con npm 11, que trae Node 24.
- **Node del equipo (22.13.1) más antiguo** del que piden jsdom y React Router. Las herramientas corren en un contenedor de Node 24.22.2.
- **Dos copias de `playwright-core`** con tipos incompatibles. Se resolvió con un `overrides` a 1.65.0.
- **La CI no arrancaba (ejecución 44649813265, `27f7196`):** GitHub rechazó `.github/workflows/ci.yml` en 0 segundos, con el mensaje "This workflow graph cannot be shown". **Causa:** el trabajo `interfaz_e2e` usaba `${{ runner.temp }}` en su `env`, y a nivel de trabajo el contexto `runner` no existe (solo `github`, `inputs`, `matrix`, `needs`, `secrets`, `strategy` y `vars`). Un archivo con una expresión inválida no ejecuta ningún trabajo. **Solución:** `DIRECTORIO_ARCHIVOS` pasó al `env` del paso que levanta la API. **Lección:** antes se había comprobado solo que el YAML se leía bien. Ahora el flujo se valida con `actionlint` 1.7.12 (`docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12`), que encontró el error y no informa ninguno tras la corrección.
- **El contrato cambiaba según la versión de Python:** Python 3.13 nombra distinto los estados 413 y 422. El generador fija los nombres de la RFC 9110, y la prueba pasa con 3.12 (contenedor) y con 3.13.
- **En las pruebas unitarias,** openapi-fetch guardaba la referencia a `fetch` al importar, y el `fetch` de Node no acepta URL relativas. El cliente usa ahora una URL absoluta del mismo origen y resuelve `fetch` en cada petición.

### 16.5. Pendientes

- **Prueba manual con teclado y lector de pantalla (NVDA): superada según el equipo** (20 de noviembre de 2026). La hizo el equipo en la interfaz de desarrollo (`http://127.0.0.1:5173`), con dos cuentas ficticias de la base de desarrollo (`INV-PRUEBA-NVDA` y `CASO-PRUEBA-NVDA-1`, tema `TEMA-PRUEBA-NVDA`), creadas con la contraseña inicial ya cambiada. El archivo con sus credenciales, fuera del repositorio, se borró al terminar. Las cuentas quedan en la base de desarrollo.
- **RNF-17 (usabilidad, menos de 3 minutos para cargar y pedir una revisión):** se mide en la prueba piloto, cuando exista la formulación de solicitudes (T29).

### 16.6. Archivos

- **Creados:**
  - `frontend/` (configuración, `src/`, `e2e/`, `package.json` y `package-lock.json`);
  - `backend/app/contrato.py` y `docs/api/openapi.json`;
  - `scripts/e2e.ps1`;
  - `docs/decisiones/T13-interfaz-base.md`.
- **Modificados:**
  - `backend/app/api/caso.py` (hitos en `GET /caso`), `backend/pruebas/unitarias/test_arquitectura.py` (contrato al día) y `backend/pruebas/integracion/test_casos.py`;
  - `.github/workflows/ci.yml` y `docker-compose.yml` (servicio `interfaz`);
  - `README.md`, `CLAUDE.md` y este archivo.

### 16.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t13-interfaz-base`: `27f7196` (`T13: crear la interfaz base con React, TypeScript y React Aria Components`) y `295c206` (corrección del flujo de CI), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#9 |
| CI de la solicitud | La primera ejecución (44649813265) no arrancó por el error del flujo (apartado 16.4). Tras corregirlo: **verde**, ejecución 44671874090, 9 de 9 trabajos. Incluye `interfaz` y `interfaz_e2e`: las pruebas de extremo a extremo y la revisión de accesibilidad pasan también en la CI |
| Integración en `main` | Commit de integración `78c1cd5` |
| CI de `main` tras integrar | Ejecución 44673300029: **verde** |

---

## 17. Fase 3 (F3): T14. Clientes bibliográficos con limitador y caché

Rama `t14-clientes-bibliograficos`, desde `main` con T13 (`78c1cd5`). Decisión: `docs/decisiones/T14-clientes-bibliograficos.md` (T14-01).

### 17.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Interfaz `ServicioBibliografico` y resultado común | Hecha | `app/bibliografia/interfaces.py` (`ServicioBibliografico`, `BuscadorBibliografico` y `FormateadorDeCitas`) y `modelos.py` (`ResultadoBibliografico`: estado `encontrado`, `no_encontrado` o `no_comprobable`, metadatos normalizados, acceso abierto, cita, candidatos y motivo) |
| 2. Limitador de tasa por servicio (cubeta de fichas), configurable | Hecha | `limitador.py`. Valores de la documentación de cada servicio: Crossref 10 y 3 por segundo, doi.org 5, Unpaywall 1,15 (100 000 por día) y OpenAlex 10. Variables `TASA_*` |
| 3. Caché en `cache_metadatos` con vigencia configurable | Hecha | `cache.py` y `RepositorioCacheMetadatos`. Lo encontrado dura 30 días y lo no encontrado, 24 horas. Un `no_comprobable` nunca se guarda. Si la base falla, la caché se omite y la consulta sigue |
| 4. Crossref por DOI y por metadatos, con el correo del proyecto | Hecha | `crossref.py`: `mailto` y `User-Agent`, con limitadores separados para registro y búsqueda |
| 5. doi.org por negociación de contenido: CSL-JSON y cita formateada | Hecha | `doi.py`. Estilos de las normas de la configuración (`apa`, `ieee` y `vancouver`). Una respuesta HTML no se acepta como cita |
| 6. Unpaywall: estado y mejor ubicación de acceso abierto | Hecha | `unpaywall.py` |
| 7. OpenAlex con clave, como respaldo de metadatos | Hecha | `openalex.py`, probado con sus respuestas reales. Sin `CLAVE_OPENALEX` da `no_comprobable` (`no_configurado`). Busca solo por el título (apartado 17.4) |
| 8. Comparación de metadatos con tolerancias documentadas | Hecha | `comparador.py`: título con similitud de 0,88 o más (normalizado y también sin subtítulo), al menos un apellido (también en apellidos compuestos) y año con un año de tolerancia. Sin uno de los tres datos, no se confirma |
| Tarea: tiempos de espera y reintentos con espera exponencial | Hecha | `http.py`: 3 intentos ante red, tiempo agotado, 429 y 5xx; esperas de 0,5 s y 1 s; respeta `Retry-After` |
| Tarea: toda excepción de red o límite da `no_comprobable` | Hecha | `FallaDeServicio` se convierte en `no_comprobable` en la base común de los clientes (`base.py`) |
| Tarea: respuestas reales grabadas en `pruebas/contrato/` | Hecha | 11 respuestas de los cuatro servicios con `python -m pruebas.contrato.grabar`, sin el correo ni la clave (el script lo comprueba, y se volvió a comprobar en los 11 archivos) |

### 17.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Con el servicio simulado caído, el resultado es `no_comprobable` y nunca `no_encontrado` (base de CP-13) | **Cumplido** | Las 7 consultas de los cuatro clientes (por DOI, búsqueda y cita) con 6 fallas simuladas: sin conexión, tiempo agotado, 503, 429, respuesta ilegible y 403. Siempre `no_comprobable`, con su motivo, y los reintentos que corresponden a cada falla |
| Una segunda consulta del mismo DOI se resuelve desde la caché | **Cumplido** | Con la base real: la segunda consulta (con el DOI escrito de otra forma) sale de `cache_metadatos` sin pedir nada al servicio. Vencida la vigencia, se vuelve a consultar y la entrada se reemplaza. Lo no encontrado vence a las 24 horas |
| El limitador impide superar la tasa configurada en una ráfaga de prueba | **Cumplido** | Ráfaga de 30 consultas a 3 por segundo con reloj simulado: en ninguna ventana se superan la ráfaga inicial más 3 por segundo, y la última sale a los 9 s. También con 25 consultas concurrentes |

### 17.3. Pruebas

- **Backend en contenedor:** 587 pruebas superadas y 5 omitidas (las que necesitan GROBID o el servicio de modelos), cobertura del 94,87 %. Ruff y mypy sin observaciones.
- **Nuevas:**
  - `unitarias/test_bibliografia.py` (43): limitador, comparador, contrato con las respuestas grabadas de los cuatro servicios, fallas simuladas, reintentos, `Retry-After`, servicio sin configurar, DOI inválido, caché en memoria, fábrica e interfaces, y un registro sin el correo ni la clave.
  - `integracion/test_bibliografia_cache.py` (3): caché sobre la base real.
- **Sin red en la CI:** ninguna prueba consulta los servicios reales.

### 17.4. Problemas encontrados y soluciones

- **Una página HTML pasaba como cita:** las pruebas de fallas mostraron que doi.org aceptaba como cita cualquier respuesta 200. Ahora solo se acepta `text/x-bibliography` o `text/plain`, que es lo que devuelve doi.org (comprobado en la grabación).
- **La búsqueda de OpenAlex con la referencia completa no encontraba la obra.** Al grabar OpenAlex, la prueba del comparador falló: con título, apellido y año, el artículo no estaba entre los 5 primeros resultados (el comparador hizo bien en no aceptar ninguno). Comprobado con dos consultas reales: solo con el título, el artículo sale primero. OpenAlex busca ahora solo por el título; el comparador sigue exigiendo título, autor y año.
- **La normalización de DOI estaba en el cliente de GROBID.** Pasó a `app/bibliografia/normalizacion.py`, y GROBID la reutiliza.

### 17.5. Pendientes

- Ninguno de esta fase. La grabación de OpenAlex se hizo el 20 de noviembre de 2026, cuando el equipo puso `CLAVE_OPENALEX` en `.env`.

### 17.6. Archivos

- **Creados:**
  - `backend/app/bibliografia/` (`modelos.py`, `interfaces.py`, `normalizacion.py`, `limitador.py`, `comparador.py`, `http.py`, `cache.py`, `base.py`, `crossref.py`, `doi.py`, `unpaywall.py`, `openalex.py` y `fabrica.py`);
  - `backend/pruebas/contrato/` (`grabar.py` y `respuestas/`, con 11 respuestas reales), `backend/pruebas/dobles_bibliografia.py`, `unitarias/test_bibliografia.py` e `integracion/test_bibliografia_cache.py`;
  - `docs/decisiones/T14-clientes-bibliograficos.md`.
- **Modificados:**
  - `backend/app/repositorios/sistema.py` (`RepositorioCacheMetadatos`) y `unidad.py`;
  - `backend/app/configuracion/ajustes.py` (tasas, tiempo, reintentos y vigencias) y `.env.example`;
  - `backend/app/corpus/grobid.py` (normalización de DOI compartida);
  - `README.md`, `CLAUDE.md` y este archivo.

### 17.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t14-clientes-bibliograficos`: `220a95f` (`T14: agregar los clientes bibliográficos con limitador y caché`), `724aca5` (línea larga del paquete de contrato) y `6ca815f` (grabación de OpenAlex y búsqueda por título), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#10 |
| CI de la solicitud | **Verde**, ejecución 44837538462 (la de `6ca815f`), 9 de 9 trabajos |
| Integración en `main` | Commit de integración `f3e343f` |
| CI de `main` tras integrar | Ejecución 44839306862: **verde** |

---

## 18. Fase 3 (F3): T15. Importador de referencias del artículo O1

Rama `t15-importador-referencias`, desde `main` con T14 (`f3e343f`). Decisión: `docs/decisiones/T15-importador-referencias.md` (T15-01). Formatos y prueba real decididos por el equipo el 20 de noviembre de 2026: PDF, .docx y lista de DOI (amplía RF-20), y un artículo base importado de punta a punta.

### 18.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Carga del artículo O1 (.docx) o de una lista de DOI para un tema | Hecha, también PDF | `POST /investigador/colecciones/{id}/importaciones` responde 202. El .docx se valida con T11 y el PDF con T09. En la lista de DOI, las líneas sin forma de DOI se excluyen con `doi_invalido` |
| 2. Referencias con GROBID y descarte del artículo (RN-19) | Hecha | `app/importacion/extraccion.py` y `ClienteGrobid.referencias` y `referencias_de_texto` (`processReferences` y `processCitationList`, sin consolidar). El .docx pasa por la detección de referencias de T12. El artículo vive solo en `/archivos/importacion/<id>/` y se borra en cuanto se extraen las referencias, también si la extracción falla. Al arrancar, la API borra cualquier resto |
| 3. Resolución por DOI o por metadatos con T14 | Hecha | `resolucion.py` (`Localizador`): Crossref por DOI, OpenAlex por DOI si Crossref no lo conoce (DOI de DataCite) y, si nadie lo encuentra, búsqueda en Crossref y luego en OpenAlex con el comparador de T14. Sin respuesta de algún servicio, `no_comprobable` (RN-18) |
| 4. Acceso abierto en Unpaywall | Hecha | Sin registro en Unpaywall vale el acceso abierto de OpenAlex, si localizó la obra por DOI. Sin ninguno o con `is_oa = false`: excluida con `sin_acceso_abierto` (RN-14). Se guardan el estado, la página, el enlace al PDF y la licencia |
| 5. Descarga del PDF con enlace directo y proceso con T09 y T10 | Hecha | `descarga.py`: hasta el tamaño máximo de la configuración y con la firma `%PDF-`. Después, `Indexador.ingerir` de T10. El documento recibe los metadatos de Crossref y de Unpaywall y el origen `importacion_o1` |
| 6. Pendiente de PDF y carga manual | Hecha | `pendiente_pdf` con `sin_enlace_directo` o `descarga_fallida`. `POST /investigador/referencias/{id}/pdf` la indexa con T10: queda incluida, o excluida con el motivo del canal |
| 7. Exclusión con motivo | Hecha | `no_localizada`, `sin_doi`, `sin_acceso_abierto` y `doi_invalido` (migración 0011) en `exclusion_corpus` con `objeto = referencia`. Un PDF que el canal rechaza deja su propia exclusión de archivo |
| 8. Informe por tema | Hecha | `GET /investigador/colecciones/{id}/informe`: referencias totales, de acceso abierto, incluidas, pendientes, no comprobables y excluidas por motivo. `recontar` lleva ahora también `n_pendientes` |
| 9. Pantallas del investigador | Hecha | `/investigador/importacion` (`frontend/src/paginas/Importacion.tsx`): tema, artículo o DOI con el avance, informe y pendientes con enlace a su página de acceso abierto y subida del PDF |
| Tarea: proceso en segundo plano con estado consultable | Hecha | Tarea `asyncio`, una importación a la vez por proceso. `GET /investigador/importaciones/{id}` da estado y avance. Una importación cortada por un reinicio queda `interrumpida` en la siguiente consulta |
| Tarea: idempotencia | Hecha | Cada referencia es única por colección (`clave`: DOI o huella del texto). Las incluidas y excluidas no se reprocesan; las no comprobables y las pendientes se reintentan, y un DOI que ya tiene documento no se descarga otra vez |
| Tarea: prueba explícita de RN-19 | Hecha | Apartado 18.3 |

### 18.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Un .docx de prueba con al menos 20 referencias se importa y el informe lista incluidas, excluidas y pendientes con motivo | **Cumplido** | `test_importar_el_docx_arma_el_informe_con_cada_resultado`: el artículo O1 ficticio (`pruebas/datos/o1/articulo_o1.docx`, 24 referencias, una por escenario) da 9 incluidas, 5 pendientes (3 `sin_enlace_directo` y 2 `descarga_fallida`), 8 excluidas (`sin_acceso_abierto` 4, `no_localizada` 2, `sin_doi` 1 y `sin_capa_de_texto` 1) y 2 no comprobables (Crossref caído). Cada referencia queda con el estado y el motivo de su escenario, y los contadores de la colección son 9, 8 y 5 |
| Tras la importación no existe copia del artículo O1 | **Cumplido** | Con servicios simulados (`test_rn19_...`, .docx y PDF): al resolver la primera referencia, la carpeta del artículo ya está vacía. Al terminar no queda ningún archivo en `importacion/`, y en el almacén solo están los 9 PDF de las referencias. Ninguna fila de ninguna tabla contiene frases del cuerpo, el título del artículo ni el nombre del archivo, y el registro tampoco. Con el artículo base real, en el proyecto aislado `sma_t15`: apartado 18.3 |
| Un PDF subido desde "pendientes" queda indexado en la colección del tema | **Cumplido** | Con el canal simulado (`test_subir_el_pdf_de_una_pendiente_la_incluye`): la referencia queda incluida, con documento de origen `importacion_o1` y su DOI, y los pendientes bajan de 5 a 4. Un escaneado queda excluido con `sin_capa_de_texto` y una referencia que ya no está pendiente responde 409. Con el canal real (Docling, GROBID y bge-m3): apartado 18.3 |

### 18.3. Pruebas

- **Backend en contenedor (Python 3.12):** 594 pruebas superadas y 5 omitidas (las que necesitan GROBID o el servicio de modelos), cobertura del 94,13 %. Ruff y mypy sin observaciones.
- **Integración (`integracion/test_importacion.py`, 7 pruebas):**
  - el informe del .docx;
  - RN-19;
  - la reimportación, que no duplica y solo reintenta las 2 descargas fallidas;
  - la lista de DOI: normalización, `doi_invalido`, DOI de DataCite con el acceso abierto de OpenAlex y avance completo, y un DOI con documento que no se vuelve a descargar;
  - el artículo inválido, que falla y también se borra, más los rechazos 422 y 404;
  - la subida desde pendientes;
  - la importación cortada, que queda `interrumpida`.

  GROBID responde con sus respuestas reales grabadas (`pruebas/contrato/grobid/`: 23 referencias del PDF y 24 del .docx, con los 19 DOI correctos en ambos casos).
- **Interfaz:**
  - `src/pruebas/importacion.test.tsx` (4): lista de DOI con avance hasta terminar, archivo y DOI a la vez rechazados, informe con motivos, enlace de acceso abierto y subida de un pendiente, y textos de los motivos. En total, 13 pruebas unitarias superadas, con tipos, lint, formato y compilación sin observaciones.
  - **Extremo a extremo** (`scripts/e2e.ps1`): 5 de 5 superadas. La nueva abre la importación de un tema y revisa su accesibilidad sin infracciones graves.
- **Prueba real con un artículo base** (decisión del equipo), en el proyecto aislado `sma_t15` (puertos 5438 y 8040), sin tocar el corpus provisional de `sma_rag`:
  - **Artículo:** `ChatGPT_como_fuente_de_informacion_en_la_Educacion.pdf` (22 páginas), con GROBID, Crossref, Unpaywall, OpenAlex, descargas, Docling y bge-m3 reales.
  - **Tiempo y extracción:** 1 059 s en total; GROBID extrajo 53 referencias en unos 40 s.
  - **Informe:**
    - 14 referencias incluidas, con 13 documentos (12 activos y uno incompleto sin confirmar);
    - 9 pendientes de PDF (7 por descarga fallida y 2 sin enlace directo);
    - 30 excluidas: `no_localizada` 21, `sin_acceso_abierto` 7 y `sin_doi` 2;
    - ninguna no comprobable.

    Las no localizadas son noticias, páginas web, libros y entradas sin título ni año, que ningún servicio registra. La excepción son dos DOI de DataCite (apartado 18.4).
  - **RN-19 en disco:** `importacion/` vacía, ningún archivo con la huella SHA-256 del artículo y ninguna caché de Docling para él. Hay un PDF en el almacén por cada documento.
  - **RN-19 en la base:** las 21 tablas se revisaron con cinco frases del cuerpo, la huella y el nombre del archivo. No hay texto del artículo ni su huella. Las únicas coincidencias están en 4 filas de `cache_metadatos`: son resultados de búsqueda de OpenAlex (para otras referencias) que traen entre sus candidatos el registro bibliográfico público del propio artículo (título y DOI). El comparador los descartó y ningún documento tiene ese DOI.
  - **RN-19 en el registro de la API:** ninguna de las frases.
  - **Subida desde pendientes con el canal real:** se subió un PDF ficticio de muestra (`pruebas/datos/pdf/articulo_es.pdf`; no otro artículo base, para no indexar artículos O1). La referencia quedó incluida en 23 s, con 9 fragmentos, y los pendientes bajaron de 9 a 8.
  - **DataCite, tras la corrección:** en un tema nuevo, `10.48550/arxiv.1612.08220` quedó incluido (acceso abierto `green`, descargado e indexado). `10.5281/zenodo.10360697` quedó pendiente de PDF con su página de acceso abierto; OpenAlex lo devuelve con el DOI del registro general (`10.5281/zenodo.10360696`).
  - **RN-19 después de estas pruebas:** se repitió con el mismo resultado; hay 15 PDF en el almacén para 15 documentos.

### 18.4. Problemas encontrados y soluciones

- **CP-21 contaba el artículo O1 ficticio:** la prueba del canal real ingiere toda la carpeta `pruebas/datos/pdf/`, y el O1 estaba ahí. El O1 pasó a `pruebas/datos/o1/`, aparte del corpus, que es donde corresponde, porque nunca debe ingerirse.
- **Los DOI de DataCite quedaban "no localizados":** Crossref no conoce los DOI de arXiv ni de Zenodo, y Unpaywall tampoco. Ahora se consultan en OpenAlex por DOI y se usa su acceso abierto (apartado 18.3).
- **La lista de DOI repetía exclusiones:** al reimportar, una línea sin forma de DOI volvía a registrarse en `exclusion_corpus`, y esas líneas no sumaban al avance. Corregido y probado.
- **La descarga usaba `.stream(`,** que la regla de arquitectura toma por una consulta a la base fuera de `repositorios/`. Ahora usa `send(..., stream=True)`.
- **En jsdom, `fetch` no acepta un `File` dentro de un `FormData`:** en la prueba de la subida se sustituye el envío y se comprueba el formulario.
- **La cookie de sesión es `Secure`:** el guion de la prueba real, que llamaba a la API por `http://127.0.0.1`, la envía en la cabecera. La aplicación no cambió.
- **Un `Error` simple no muestra su texto en `AvisoError`** (solo los `ErrorApi`). La pantalla nueva usa `ErrorApi` para sus validaciones. Las de T11 y T13 tienen el mismo defecto (apartado 18.5).
- **Antes de la migración 0011:**
  - una importación cortada se marca `interrumpida` en la siguiente consulta, no al arrancar, porque al arrancar la base puede no estar disponible;
  - se agregó el motivo `doi_invalido`;
  - se descartó la variante `-Completo` de `scripts/e2e.ps1` (decisión, apartado 9).

### 18.5. Pendientes y riesgos

- **Mensajes de validación de T11 y T13:** `PanelCaso.tsx` e `Investigador.tsx` crean `new Error(...)` y la pantalla muestra "Ocurrió un error inesperado." en lugar del texto. **Corregido al inicio de T17** (apartado 19).
- **Descargas fallidas en la prueba real (7 de 23 abiertas):** muchos sitios rechazan las descargas automáticas. El investigador las sube a mano desde la pantalla de pendientes, como prevé la Fase 1 (n.° 14).
- **Tiempo:** cada PDF descargado pasa por Docling (unos 30 a 60 s en CPU). Un artículo con 50 referencias tarda unos 18 minutos. La cola persistente es de T28.

### 18.6. Archivos

- **Creados:**
  - `backend/app/importacion/` (`extraccion.py`, `resolucion.py`, `descarga.py`, `servicio.py` y `fabrica.py`), `backend/app/repositorios/importacion.py`, `backend/app/api/importacion.py`, `backend/app/bd/modelos/importacion.py` y `backend/migraciones/versiones/0011_importacion_de_referencias.py`;
  - `backend/pruebas/datos/articulo_o1.py` y `pruebas/datos/o1/` (PDF y .docx ficticios), `pruebas/contrato/grabar_grobid_referencias.py` y `pruebas/contrato/grobid/` (2 respuestas reales), `pruebas/dobles_importacion.py` e `integracion/test_importacion.py`;
  - `frontend/src/paginas/Importacion.tsx` y `frontend/src/pruebas/importacion.test.tsx`;
  - `docs/decisiones/T15-importador-referencias.md`.
- **Modificados:**
  - `backend/app/bd/enumeraciones.py`, `bd/modelos/__init__.py`, `corpus/grobid.py` (referencias con GROBID), `corpus/indexacion.py` (mensajes de los motivos nuevos), `repositorios/corpus.py` (`n_pendientes`) y `unidad.py`, y `main.py` (rutas y limpieza al arrancar; también se corrigieron sus tildes mal codificadas);
  - `backend/pruebas/datos/generar_pdf_muestra.py` y `generar_docx_muestra.py`, `pruebas/dobles_corpus.py` (marca `VARIANTE=`) y `pruebas/matriz_autorizacion.py` (5 rutas);
  - `frontend/src/App.tsx`, `componentes/controles.tsx` (`CampoTextoLargo`), `estilos.css`, `paginas/Investigador.tsx` (enlace), `api/esquema.d.ts` y `e2e/flujo.spec.ts`;
  - `docs/api/openapi.json`, `docs/diccionario-de-datos.md`, `README.md`, `CLAUDE.md` y este archivo.

### 18.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t15-importador-referencias`: `d103b25` (`T15: agregar el importador de referencias del artículo O1`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#11 |
| CI de la solicitud | **Verde**, ejecución 44992224855 (la de `d103b25`), 9 de 9 trabajos |
| Integración en `main` | Commit de integración `56d1229` |
| CI de `main` tras integrar | Ejecución 44994653518: **verde** |

---

## 19. Fase 3 (F3): T17. Adaptador de modelos de lenguaje e instrucciones versionadas

Rama `t17-adaptador-modelos`, desde `main` con T15 (`56d1229`). Decisión: `docs/decisiones/T17-adaptador-modelos.md` (T17-01). Según el orden de ejecución de la hoja de ruta, T17 va antes que T16.

Decisiones del equipo del 22 de noviembre de 2026:
- **DeepSeek:** solo ofrece alias, así que se admite solo en desarrollo, registrando la versión que informa.
- **Gemini:** `gemini-3.8-flash`, su modelo estable.
- **Llamadas:** con `httpx` directo, sin SDK.

**Corrección previa (pendiente de T11 y T13, apartado 18.5):** las validaciones propias de la interfaz ahora muestran su mensaje tal cual (por ejemplo, "Elija el hito y el archivo .docx de su borrador.") y no "Ocurrió un error inesperado.".
- `errorDeValidacion` en `frontend/src/api/cliente.ts`, usado en `PanelCaso.tsx`, `Investigador.tsx` e `Importacion.tsx`.
- Pruebas en `frontend/src/pruebas/validacion.test.tsx`: el panel del caso muestra el mensaje y no llama a la API, y un error imprevisto sigue sin mostrar su texto técnico.

### 19.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Interfaz `ModeloLenguaje.generar(instruccion, entrada, esquema)` | Hecha | `app/llm/interfaces.py` y `modelos.py`. `EntradaModelo` solo admite texto en modo estricto (tarea y bloques etiquetados, con tamaño máximo). `ResultadoEstructurado[T]` devuelve los datos validados, proveedor, modelo, versión informada, instrucción y huella, tokens, duración, costo, intentos y si hubo respaldo |
| 2. Proveedor GroqCloud con esquema JSON estricto | Hecha | `proveedores.py` (`ProveedorCompatibleOpenAI`): `openai/gpt-oss-120b` con `response_format: json_schema` y `strict: true`. `esquema.py` arma el esquema estricto: todo requerido, `additionalProperties: false` y opcionales como unión con `null` |
| 3. Proveedores de respaldo DeepSeek y Gemini | Hecha | DeepSeek (`deepseek-flash`): modo JSON con el esquema escrito en la instrucción; un contenido en blanco se trata como falla transitoria. Gemini (`gemini-3.8-flash`): API de interacciones con `response_format` |
| 4. Cadena de respaldo solo para errores de disponibilidad | Hecha | `cadena.py`. Red, tiempo agotado, 429, 402, 5xx y límite diario pasan al siguiente proveedor tras 2 reintentos con espera exponencial (o `retry-after`). Una solicitud rechazada (400, 401…) o una salida inválida se reportan sin respaldo. Cada intento registra el proveedor usado |
| 5. Proveedor simulado determinista | Hecha | `ProveedorSimulado`: valores válidos para cualquier esquema, o respuestas fijas por esquema, y una falla simulada a pedido. Es el proveedor por defecto en `ENTORNO=pruebas` |
| 6. Limitador del lado del cliente | Hecha | `limitador.py`: solicitudes y tokens por minuto y por día, con reserva estimada y ajuste con el uso real. Groq: 30 solicitudes y 8 000 tokens por minuto; 1 000 solicitudes y 200 000 tokens por día (R-01). Si la espera supera `ESPERA_MAXIMA_LIMITADOR_S`, pasa al respaldo |
| 7. Validación local con Pydantic de toda salida | Hecha | `esquema.validar`: siempre, también con esquema estricto. El error lleva la ubicación y el tipo de cada falla, nunca los valores |
| 8. Tokens, duración y costo en `evento_tecnico` | Hecha | `fabrica.registrador_en_base` y `RepositorioEventosTecnicos`. El costo se estima con los precios de lista de la configuración; si la base falla, la llamada sigue |
| 9. Cargador de instrucciones con identificador y huella | Hecha | `app/instrucciones/cargador.py`: archivos `backend/instrucciones/<agente>/<version>.md` con cabecera, huella SHA-256 y `registro.json`, que impide editar una versión publicada. `python -m app.instrucciones listar\|registrar`. La configuración elige la versión (`versiones_instrucciones`) y cada solicitud guarda su `configuracion_id` (RNF-21). Plantilla en `backend/instrucciones/plantilla.md` |
| 10. Regla de entorno de producción | Hecha | `PROVEEDORES_MODELO`, validada al arrancar: en `produccion` solo se admiten los proveedores de la lista de producción, vacía hasta T25 (D-10), así que no hay respaldo gratuito. La fábrica vuelve a comprobarlo y rechaza un alias fuera de desarrollo (RN-24) |
| Tarea: contenido delimitado como datos (RN-23) | Hecha | `mensajes.py`: regla fija en el mensaje de sistema y bloques `<datos etiqueta="…">`, con los cierres de etiqueta neutralizados |
| Tarea: reintento técnico hasta 2 veces (4.4) | Hecha | Esperas de 1 s y 2 s, o el `retry-after` del proveedor (hasta 20 s) |
| Tarea: identificadores fijos (RN-24) | Hecha | Configuración (migración de datos 0012): `openai/gpt-oss-120b` y `gemini-3.8-flash` fijos; `deepseek-flash` marcado como alias |
| Tarea: claves solo de la configuración (RNF-16) | Hecha | `CLAVE_GROQ`, `CLAVE_DEEPSEEK` y `CLAVE_GEMINI` de los ajustes. Un proveedor sin clave se omite y queda registrado |

### 19.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Una salida que no cumple el esquema se rechaza localmente y se reporta | **Cumplido** | `test_una_salida_fuera_del_esquema_...` y `test_una_salida_invalida_se_reporta_sin_pasar_al_respaldo`: da `SalidaInvalida` con cada campo y tipo de error, sin los valores; el respaldo no se llama y el evento queda con `SalidaInvalida:salida_invalida` |
| Con Groq simulado no disponible, la llamada pasa a DeepSeek y queda registrado el proveedor usado | **Cumplido** | `test_con_groq_caido_pasa_a_deepseek_...`: Groq responde 503, se reintenta 2 veces (esperas de 1 s y 2 s) y responde DeepSeek. El resultado dice `deepseek`, `deepseek-flash` y `respaldo = True`; hay 4 eventos (3 de Groq con su error y 1 de DeepSeek). Con la base real, `integracion/test_llm_registro.py` |
| En `produccion`, intentar usar un proveedor gratuito falla al arrancar | **Cumplido** | `test_en_produccion_un_proveedor_gratuito_falla_al_arrancar`: con `groq`, `deepseek`, `gemini` o `groq,gemini`, `cargar_ajustes` lanza `ErrorConfiguracion`. Sin proveedores, arranca sin respaldo |
| Cada llamada registra tokens y duración | **Cumplido** | `test_cada_llamada_registra_tokens_duracion_y_costo` (210 y 30 tokens, costo 0,000050 USD con precios de Groq) y, con la base real, `evento_tecnico` con etapa, proveedor, modelo, tokens, duración y error, sin la tarea, los datos ni la salida |

### 19.3. Pruebas

- **Backend en contenedor (Python 3.12):** 625 pruebas superadas, cobertura del 92,70 %. Ruff y mypy sin observaciones.
  - Esa corrida omitió además las 9 del canal real, porque el volumen de recursos del proyecto aislado se había borrado al cerrar T15. Con los recursos copiados de nuevo pasan las 9, CP-21 incluida.
  - Las 8 omitidas restantes necesitan GROBID o el servicio de modelos, o son las 3 de contrato que esperan las grabaciones.
- **Unitarias (`unitarias/test_llm.py`, 36):**
  - esquema estricto y validación;
  - RN-23: bloques delimitados y cierres neutralizados;
  - RNF-10: con un .docx de muestra, la carga enviada lleva solo la sección del alcance, como texto, ni la firma del .docx ni los párrafos de fuera del alcance, y solo los campos esperados;
  - cuerpo y respuesta de Groq, DeepSeek y Gemini;
  - clasificación de 10 fallas;
  - cadena de respaldo;
  - limitador con reloj simulado;
  - regla de entorno y alias;
  - fábrica;
  - cargador e inmutabilidad de las instrucciones.
- **Contrato (`unitarias/test_llm_contrato.py`):** reproduce la respuesta real grabada de cada proveedor y valida su esquema; comprueba que ninguna grabación lleve claves. **Pendiente de las claves** (apartado 19.5): sin grabación, las 3 pruebas se omiten y lo dicen.
- **Integración:** `test_llm_registro.py` (2), con la base real, y la migración 0012 en `test_migraciones.py` (subida, bajada y versión 1 congelada). La semilla sigue coincidiendo con `parametros_iniciales()`.
- **Interfaz:** 16 pruebas unitarias, con las 3 nuevas de validación.

### 19.4. Problemas encontrados y soluciones

- **Un `bytes` se aceptaba como texto:** Pydantic convierte `bytes` en `str` por defecto, así que un .docx podía entrar en un bloque de datos. `EntradaModelo` y `BloqueDatos` validan ahora en modo estricto (RNF-10).
- **El esquema estricto perdía propiedades llamadas `title`:** al quitar la palabra clave `title`, también se borraba una propiedad con ese nombre. Ahora los nombres dentro de `properties` y `$defs` se conservan.
- **La documentación de los proveedores cambió:**
  - DeepSeek ya no publica `deepseek-chat`; ofrece `deepseek-flash` y `deepseek-v4-pro`, ambos alias.
  - Gemini 2.5 está obsoleto y su API recomendada es la de interacciones.
  - Groq no deja claro si los 8 000 tokens por minuto son los del plan gratuito.

  Se consultaron el 22 de noviembre de 2026 y se decidió con el equipo (apartado 19, encabezado).

### 19.5. Pendientes y riesgos

- **Grabaciones de contrato:** la de Groq se grabó el 23 de noviembre de 2026, al cargarse `CLAVE_GROQ` (apartado 21). `CLAVE_DEEPSEEK` y `CLAVE_GEMINI` siguen vacías. Con cada clave cargada: `python -m pruebas.contrato.grabar_modelos`, una llamada por proveedor con la tarea ficticia `contrato/v1`.
- **Límites gratuitos de Gemini:** no están publicados; la configuración usa 5 solicitudes por minuto y 100 por día hasta conocerlos.
- **Limitador por proceso:** T28 decide si la API y el trabajador necesitan uno compartido.
- **Reordenador (T08, 18,6 s):** afecta la latencia de T16, no a este adaptador. Se trata en T16.

### 19.6. Archivos

- **Creados:**
  - `backend/app/llm/` (`modelos.py`, `interfaces.py`, `esquema.py`, `mensajes.py`, `limitador.py`, `proveedores.py`, `cadena.py` y `fabrica.py`) y `backend/app/instrucciones/` (`cargador.py` y `__main__.py`);
  - `backend/instrucciones/` (`plantilla.md`, `contrato/v1.md` y `registro.json`) y `backend/migraciones/versiones/0012_modelos_de_lenguaje.py`;
  - `backend/pruebas/contrato/grabar_modelos.py`, `unitarias/test_llm.py`, `unitarias/test_llm_contrato.py` e `integracion/test_llm_registro.py`;
  - `frontend/src/pruebas/validacion.test.tsx`;
  - `docs/decisiones/T17-adaptador-modelos.md`.
- **Modificados:**
  - `backend/app/configuracion/ajustes.py` (`PROVEEDORES_MODELO`, tiempos y regla de entorno), `administracion/parametros.py` (`modelos` y `versiones_instrucciones`) y `repositorios/sistema.py` y `unidad.py` (`RepositorioEventosTecnicos`);
  - `backend/Dockerfile` (copia `instrucciones/`), `pruebas/integracion/test_migraciones.py` y `.env.example`;
  - `frontend/src/api/cliente.ts`, `paginas/PanelCaso.tsx`, `Investigador.tsx` e `Importacion.tsx`;
  - `docs/decisiones/T15-importador-referencias.md` (registro público del artículo en la caché, aceptado por el equipo), `README.md`, `CLAUDE.md` y este archivo.

### 19.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t17-adaptador-modelos`: `a0aee34` (`T17: agregar el adaptador de modelos y las instrucciones versionadas`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#12 |
| CI de la solicitud | **Verde**, ejecución 44998881166 (la de `a0aee34`), 9 de 9 trabajos |
| Integración en `main` | Commit de integración `2eeb26f` |
| CI de `main` tras integrar | Ejecución 45000391996: **verde** |

---

## 20. Fase 3 (F3): T16. Recuperación híbrida y suficiencia

Rama `t16-recuperacion-suficiencia`, desde `main` con T17 (`2eeb26f`). Decisión: `docs/decisiones/T16-recuperacion-suficiencia.md` (T16-01).

Decisiones del equipo del 22 de noviembre de 2026:
- **Candidatos del reordenador:** 20 (18.6 dice 30), por latencia, a calibrar en T34.
- **Presupuesto de contexto:** 2 400 tokens (R-01).
- **Conjunto de consultas:** redactado por el asistente como lo escribiría un estudiante, con el documento de origen marcado. El equipo lo revisará antes de T34 y T38.

### 20.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Búsqueda densa (k = 30) sobre las colecciones permitidas | Hecha | `app/repositorios/recuperacion.py` (`RepositorioRecuperacion.buscar_denso`): coseno con el índice HNSW, solo fragmentos con vector de documentos recuperables. Las colecciones salen siempre de `colecciones_permitidas(tipo, contexto)` |
| 2. Búsqueda léxica (k = 30) con `tsvector` | Hecha | `buscar_lexico`: `websearch_to_tsquery` simple con OR entre los términos de la consulta, sin palabras vacías |
| 3. Fusión por rangos recíprocos | Hecha | `app/rag/fusion.py` (`fusionar`): suma de 1 / (60 + posición), determinista ante empates |
| 4. Reranking y los mejores 8 | Hecha | `app/rag/recuperacion.py`: los primeros 20 de la fusión (`candidatos_reranking`) pasan por el reordenador. Se toman hasta 8 (`n_reranking`) sin superar 2 400 tokens (`presupuesto_tokens_contexto`) y sin cortar ninguno |
| 5. Suficiencia, paso 1 | Hecha | `app/rag/suficiencia.py`: al menos N = 2 fragmentos con puntaje de 0,5 o más; si no, abstención sin llamar al modelo |
| 6. Suficiencia, paso 2 | Hecha | El adaptador de T17 con `instrucciones/suficiencia/v1.md` (versión fijada en la configuración) responde `{suficiente, motivo}`, con los fragmentos como datos. Con el modelo caído, la falla es técnica, no una abstención |
| 7. Identificadores `F1` a `Fn` y `fragmento_recuperado` | Hecha | `app/rag/servicio.py` (`ServicioEvidencia.preparar`): una fila por fragmento numerado, con los puntajes denso, léxico, de la fusión y del reranking, y su posición, también cuando hay abstención. Deja además eventos técnicos de `recuperacion` y `reranking` |
| 8. Conjunto de consultas de prueba | Hecha, en borrador | `evaluacion/conjuntos/recuperacion-t16.json`: 20 consultas, 10 por tema, con su origen. Línea base con `python -m app.rag.evaluar` (apartado 20.3) |
| Tarea: recibe `ContextoAcceso` y tipo, no colección | Hecha | Ni `Recuperador.recuperar` ni el repositorio aceptan una colección |
| Tarea: parámetros de la configuración versionada | Hecha | k, constante, candidatos, número final, presupuesto, N y tau se leen de la configuración vigente. Migración de datos 0013 |
| Tarea: presupuesto de contexto (R-01) | Hecha | 2 400 tokens. En la línea base, de 5 a 7 fragmentos por consulta |

### 20.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| CP-05 superado: con evidencia insuficiente no se genera nada | **Cumplido** | `test_cp05_sin_evidencia_no_se_genera_y_la_abstencion_queda_registrada`: una consulta de otro asunto no llama a la generación ni al modelo de suficiencia (paso 1). Queda un `resultado` con `abstencion = true`, etiqueta `sin_evidencia_suficiente`, el aviso "Sin evidencia suficiente" y el paso que decidió. También el paso 2 (`test_el_juicio_del_modelo_puede_decidir_abstencion`) |
| Una consulta del caso A nunca devuelve fragmentos de la colección personal del caso B ni de otro tema | **Cumplido** | `test_el_caso_a_solo_recupera_de_su_tema_y_su_coleccion_personal`. Con fragmentos del mismo asunto en la colección personal de B (mismo tema), en TEMA-B, en las guías y en un documento retirado, A solo recibe de su científica y de su personal. Por tipo, `revision_estructura` solo recibe guías y `verificacion_referencias`, nada. Un documento incompleto sin confirmar no entra, y B no puede preparar evidencia para una solicitud de A |
| Precisión contextual y exhaustividad calculadas sobre el conjunto de prueba y registradas como línea base | **Cumplido** | Apartado 20.3 |

### 20.3. Pruebas y línea base

- **Backend en contenedor (Python 3.12):** 659 pruebas superadas y 8 omitidas, cobertura del 92,82 %. Ruff y mypy sin observaciones.
  - Las omitidas necesitan GROBID o el servicio de modelos, o son las 3 de contrato de T17.
  - La regla de arquitectura detectó consultas directas en el evaluador; pasaron a `RepositorioEvaluacion`.
- **Unitarias (`unitarias/test_rag.py`, 16):**
  - fusión y determinismo;
  - presupuesto de contexto;
  - parámetros y validación;
  - paso 1 sin llamar al modelo;
  - paso 2 en ambos desenlaces;
  - fragmentos como datos etiquetados;
  - modelo caído;
  - esquema del juicio;
  - métricas y conjunto: el conjunto se lee con su esquema, está en borrador y ninguna consulta copia cuatro palabras seguidas del título.
- **Integración (`integracion/test_rag.py`, 8):**
  - aislamiento;
  - colecciones por tipo;
  - candidatos y presupuesto;
  - registro de fragmentos y eventos;
  - CP-05;
  - generación solo con evidencia;
  - abstención por juicio del modelo;
  - documento incompleto.

  Además, la migración 0013 en `test_migraciones.py`.
- **Línea base** (`evaluacion/resultados/linea-base-t16.json`): conjunto `borrador-1`, corpus provisional y servicio de modelos reales (bge-m3 y bge-reranker-v2-m3), con los parámetros iniciales. Cada tema se evaluó en una transacción revertida; se comprobó después que la base de desarrollo no cambió (102 documentos, 2 785 fragmentos y ningún caso de evaluación).

  | Medida | Global | Tema 1 (IA en educación) | Tema 2 (MYPES) |
  | --- | --- | --- | --- |
  | Precisión contextual | 0,68 | 0,52 | 0,84 |
  | Exhaustividad | 0,80 | 0,70 | 0,90 |
  | Consultas con el documento de origen en el contexto | 16 de 20 | 7 de 10 | 9 de 10 |
  | Tiempo medio por consulta | 24,9 s | | |

  - **Sin umbral todavía:** el de la tesis (precisión de 0,80) se exige en T38.
  - **Interpretación:** solo el documento de origen cuenta como esperado, así que la medida es conservadora. En el tema 1 hay muchos artículos sobre ChatGPT en educación, y otros fragmentos pertinentes cuentan como fallos. La revisión del conjunto por el equipo puede agregar documentos esperados.
  - **Tiempo:** casi todo es el reordenador con 20 candidatos.

### 20.4. Problemas encontrados y soluciones

- **Búsqueda léxica con todos los términos:** la consulta de prueba de T10 (`plainto_tsquery`) exige todos los términos, y una consulta escrita como oración rara vez coincidiría. Por diseño, la recuperación usa OR entre los términos, sin palabras vacías.
- **El registro de instrucciones se escribía con finales de línea de Windows:** `python -m app.instrucciones registrar` escribe ahora siempre con LF.
- **psycopg asíncrono no funciona con el bucle Proactor de Windows:** el evaluador usa el bucle Selector en Windows.
- **El contenedor de pruebas no veía `evaluacion/`:** se monta en solo lectura, igual que `docs/`.
- **La CI de la solicitud falló en `ruff format --check`:** la migración 0013 no estaba formateada, porque en local solo se había pasado Ruff por `app` y `pruebas`. Se formateó (el SQL no cambia, solo las comillas de Python) y ahora se revisa todo `backend/` antes de subir.
- **El reordenador fue más lento que en T08:** 28,2 s con 30 candidatos, frente a 18,6 s. De ahí la decisión de usar 20 (T16-01, apartado 3).

### 20.5. Pendientes y riesgos

- **Revisión del conjunto por el equipo** antes de las métricas finales de T34 y T38: reescribir o agregar consultas y documentos esperados.
- **Latencia:** unos 25 s por recuperación en la computadora de desarrollo, casi todo del reordenador. En ARM será mayor. Opciones para T34, sin adelantarlas: menos candidatos, menos tokens por par o cuantización.
- **Paso 2 con un modelo real:** espera `CLAVE_GROQ` (apartado 19.5). En CI y en las pruebas se usa el proveedor simulado.

### 20.6. Archivos

- **Creados:**
  - `backend/app/rag/` (`modelos.py`, `fusion.py`, `recuperacion.py`, `suficiencia.py`, `servicio.py` y `evaluar.py`) y `backend/app/repositorios/recuperacion.py` y `evaluacion.py` (el evaluador consulta por repositorio, como exige la regla de arquitectura);
  - `backend/instrucciones/suficiencia/v1.md` y `backend/migraciones/versiones/0013_recuperacion_y_suficiencia.py`;
  - `backend/pruebas/dobles_rag.py`, `unitarias/test_rag.py` e `integracion/test_rag.py`;
  - `evaluacion/conjuntos/recuperacion-t16.json` y `evaluacion/resultados/linea-base-t16.json`;
  - `docs/decisiones/T16-recuperacion-suficiencia.md`.
- **Modificados:**
  - `backend/app/administracion/parametros.py` (`candidatos_reranking`, `presupuesto_tokens_contexto` y versión de `suficiencia`) y `repositorios/unidad.py`;
  - `backend/app/instrucciones/__main__.py` (LF) e `instrucciones/registro.json`;
  - `backend/pruebas/integracion/test_migraciones.py` y `docker-compose.yml` (monta `evaluacion/` en el contenedor de pruebas);
  - `README.md`, `CLAUDE.md` y este archivo.

### 20.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t16-recuperacion-suficiencia`: `9413668` (`T16: agregar la recuperación híbrida y la suficiencia en dos pasos`) y `2847cc8` (formato de la migración 0013), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#13 |
| CI de la solicitud | La primera ejecución falló en `ruff format --check` (apartado 20.4). **Verde** tras la corrección: ejecución 45185586537 (la de `2847cc8`), 9 de 9 trabajos |
| Integración en `main` | Commit de integración `73b506d` |
| CI de `main` tras integrar | Ejecución 45187955058: **verde** |

---

## 21. Fase 3 (F3): T18. Contrato común de agentes y comprobaciones deterministas

Rama `t18-contrato-agentes`, desde `main` con T16 (`73b506d`). Decisión: `docs/decisiones/T18-contrato-agentes.md` (T18-01). Decisión del equipo del 23 de noviembre de 2026:
- `citeproc-py` 0.12.3 con los estilos oficiales de `citeproc-py-styles` 0.2.0, en versiones fijas;
- con DOI, la cita de doi.org; si no hay DOI o doi.org no responde, el formateador local;
- las tres normas de D-12;
- migrar la base de desarrollo con respaldo.

**Antes de empezar:**
- **Base de desarrollo:** estaba en la migración 0010. T18 no necesita migrarla porque no cambia el esquema. A pedido del equipo se migró a 0013 tras un respaldo completo (`datos/respaldos/antes-de-0013-2026-11-23.*`). Se conserva todo: 102 documentos, 2 785 fragmentos (2 759 con vector), 4 exclusiones, 13 cuentas y 7 casos. La configuración v1 ganó los modelos de T17 y los parámetros de T16.
- **Groq:** con `CLAVE_GROQ` cargada se grabó la respuesta real de contrato (`pruebas/contrato/modelos/groq.json`, una llamada con la tarea ficticia `contrato/v1`: 478 tokens de entrada y 144 de salida). La prueba de contrato de Groq ya no se omite y pasa. La grabadora reconstruía la respuesta con `content-encoding` y httpx intentaba descomprimirla otra vez; se corrigió.

### 21.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Estado de entrada | Hecha | `app/agentes/contrato.py` (`EstadoAgente`): `solicitud_id`, `caso_id`, `tipo`, `alcance`, `hito`, `tema_id`, `version_id`, `intento` y `motivos_falla`. Inmutable y sin campos extra: no admite historial. Los motivos solo llegan en el intento 2 |
| 2. Esquemas de salida de los seis tipos | Hecha | `app/agentes/esquemas.py` (tablas 12 a 15): estrictos, con longitudes máximas y citas `F<n>` (al menos una por afirmación, hallazgo, tarea o cambio). `VerificacionReferencias` es la salida determinista de T20 |
| 3. Clase base de agente | Hecha | `Agente.atender`: recupera y decide la suficiencia (T16). Con abstención no llama al modelo. Si no, genera (T17) con la instrucción vigente, el alcance y `F1` a `Fn` como datos, y el esquema del tipo. En el intento 2 agrega los motivos de la falla |
| 4. Comprobaciones 1 y 3 | Hecha | `app/verificacion/comprobaciones.py`: `comprobar_esquema` (esquema del tipo) y `comprobar_citas`, que reúne los `F<n>` de los campos `citas` y de cualquier texto y exige que estén entre los de `fragmento_recuperado`. Los motivos nombran campos e identificadores, nunca contenido |
| 5. Constructor de referencias | Hecha | `app/bibliografia/referencias.py` (`ConstructorReferencias`): de los identificadores citados obtiene los documentos de la solicitud, siempre con el caso, y arma una referencia por documento en la norma. Con DOI usa doi.org; si no, CSL local. Indica el método |
| 6. Formateador CSL (IEEE y APA 7) | Hecha, también Vancouver | `app/bibliografia/csl.py` con `citeproc-py` 0.12.3 y `es-ES`. Usa `apa.csl`, `ieee.csl` y `nlm-citation-sequence.csl` oficiales, copiados en `app/bibliografia/estilos/` con su huella y su licencia (CC BY-SA 3.0). Quita el número de lista de IEEE y Vancouver |
| Tarea: ningún agente consulta el historial | Hecha | El agente solo recibe `EstadoAgente` y usa la evidencia de su solicitud. Una prueba compara lo enviado al modelo con y sin una solicitud previa del caso |
| Tarea: sin campos de texto libre para referencias | Hecha | Ningún esquema que produce el modelo tiene campos de referencia, fuente, documento, DOI, URL ni autor (prueba sobre los esquemas). Las fuentes las calcula el sistema |
| Tarea: las comprobaciones viven en `verificacion/` | Hecha | Reutilizables por T30 sobre la salida guardada |

### 21.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| Una salida simulada que cita `F9` cuando solo hay `F1` a `F8` es rechazada | **Cumplido** | `test_una_salida_que_cita_f9_se_rechaza`, con la base real: el agente de prueba genera una salida que cita `F1` y `F9`; la solicitud tiene `F1` a `F8` en `fragmento_recuperado`. La comprobación 3 da "cita a un fragmento no recuperado: F9". También en las pruebas unitarias, con citas en campos y dentro del texto |
| Toda referencia mostrada proviene de metadatos almacenados | **Cumplido** | `test_las_referencias_salen_de_los_metadatos_guardados` en las tres normas: el documento con DOI toma la cita de doi.org en el estilo de la norma, sin el número de lista. El que no tiene DOI se arma en local con su título, autores y año guardados. Un `F99` no arma nada y otro caso no obtiene ninguna referencia. Con doi.org caído, todo se arma en local con los metadatos guardados, incluido el DOI |

### 21.3. Pruebas

- **Backend en contenedor (Python 3.12, con `citeproc-py` en la imagen):** 703 pruebas superadas y 7 omitidas, cobertura del 93,12 %. Las omitidas necesitan GROBID o el servicio de modelos, o son las de contrato de DeepSeek y Gemini. Ruff (todo `backend/`) y mypy sin observaciones.
- **Unitarias (`unitarias/test_agentes.py`, 32):**
  - un ejemplo válido por tipo;
  - 9 salidas defectuosas fabricadas: citas vacías o mal formadas, `F0`, enumeraciones inválidas, campos que faltan y campos extra como `referencias` o `fuentes`;
  - esquemas sin campos de referencias y compatibles con el modo estricto;
  - comprobación 3 en campos y en texto;
  - estado del agente;
  - formateador CSL en las tres normas, con artículo y con libro y con el texto exacto esperado;
  - DOI y URL;
  - huella de los estilos;
  - número de lista.
- **Integración (`integracion/test_agentes.py`, 11):**
  - agente de prueba con el modelo simulado: generación con las comprobaciones, `F9` rechazado, abstención sin llamar al modelo, intento 2, sin memoria y tipos o casos ajenos;
  - constructor de referencias en las tres normas, con doi.org simulado que responde y que no responde, y aislamiento por caso.
- **Escenario compartido:** el de T16 pasó a `integracion/escenario_rag.py`, registrado en `conftest.py`, para que lo usen T16 y T18.
- **Contrato de Groq:** `unitarias/test_llm_contrato.py` pasa con la respuesta real grabada.

### 21.4. Problemas encontrados y soluciones

- **APA aplicaba capitalización de títulos en inglés a una revista en español** («De Pedagogía»): se pasa al motor el idioma guardado del documento, y CSL solo aplica esa regla a títulos en inglés.
- **IEEE y Vancouver numeran la lista:** una referencia suelta no lleva número. Se quita «[n]» o «n.», también en la cita de doi.org.
- **No hay un estilo llamado `vancouver.csl`:** se usa `nlm-citation-sequence.csl` (*Citing Medicine*, 2.ª edición), el estilo de referencia de Vancouver.
- **El paquete de estilos pesa 60 MB (10 867 estilos):** se copian solo los tres que se usan, con su huella, y la dependencia es solo `citeproc-py`.
- **El simulado no armaba citas válidas:** sus valores neutros no respetaban el patrón `F<n>`. Ahora genera `F1` para ese patrón.
- **Importar el fixture del escenario en otro módulo lo redefinía (Ruff F811):** se movió a un módulo compartido que registra `conftest.py`.

### 21.5. Pendientes y riesgos

- **Grabaciones de DeepSeek y Gemini:** esperan sus claves (apartado 19.5).
- **Formato de las referencias:** salen en texto plano, sin cursivas (doi.org también entrega texto plano). La presentación en la interfaz es de T19.
- **Agentes concretos (D1 a D4):** desde T19, cada uno con su instrucción, consulta y presentación del alcance.

### 21.6. Archivos

- **Creados:**
  - `backend/app/agentes/` (`contrato.py` y `esquemas.py`) y `backend/app/verificacion/comprobaciones.py`;
  - `backend/app/bibliografia/csl.py`, `referencias.py` y `estilos/` (tres estilos CSL y `LEEME.md`);
  - `backend/pruebas/unitarias/test_agentes.py`, `integracion/test_agentes.py`, `integracion/escenario_rag.py` y `pruebas/contrato/modelos/groq.json`;
  - `docs/decisiones/T18-contrato-agentes.md`.
- **Modificados:**
  - `backend/app/repositorios/caso.py` (`identificadores` y `documentos_citados`, con el caso) y `app/llm/proveedores.py` (citas del simulado);
  - `backend/pyproject.toml` y `restricciones-corpus.txt` (`citeproc-py==0.12.3`);
  - `backend/pruebas/contrato/grabar_modelos.py` (cabeceras de la grabadora), `integracion/conftest.py` y `test_rag.py`;
  - `README.md`, `CLAUDE.md` y este archivo.

### 21.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t18-contrato-agentes`: `8f62988` (`T18: agregar el contrato común de agentes, las comprobaciones 1 y 3 y el constructor de referencias`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#14 |
| CI de la solicitud | **Verde**, ejecución 45200473182 (la de `8f62988`), 9 de 9 trabajos |
| Integración en `main` | Commit de integración `07c7215` |
| CI de `main` tras integrar | Ejecución 45212472022: **verde** |

## 22. Fase 3 (F3): T19. Agente D4: búsqueda de evidencia

Rama `t19-agente-evidencia`, desde `main` con T18 (`07c7215`). Decisión: `docs/decisiones/T19-agente-evidencia.md` (T19-01). Decisión del equipo del 24 de noviembre de 2026 ("paquete recomendado"):
- pertinencia con reglas y similitud de bge-m3 local, sin modelo de lenguaje;
- trabajo en segundo plano con consulta del avance;
- sin reintento hasta T30: una comprobación fallida se entrega "Con advertencias";
- un comando que completa solo los metadatos de acceso abierto desde Unpaywall, tras un respaldo.

**Insumos del equipo:** T19 no necesita borradores con errores ni la hoja de errores, que son de T20, T23, T24, T26 y T27. Necesita la revisión de `evaluacion/conjuntos/recuperacion-t16.json` y el conjunto `evaluacion/conjuntos/validacion-consultas-t19.json`. Ese conjunto lleva unas 15 consultas aceptadas y 15 rechazadas, redactadas por el equipo, con los campos `id`, `consulta`, `esperado`, `motivo` y `nota` (T19-01, apartado 9). Mientras llegan, se trabajó con un borrador de 16 consultas y con datos simulados.

### 22.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Instrucciones de D4 (versión 1) | Hecha | `backend/instrucciones/evidencia/v1.md`, registrada con su huella. Esquema de la tabla 15, sin campos de referencias (RN-17) |
| 2. Validación previa de la consulta | Hecha | `app/agentes/validacion_consulta.py`: las reglas dan `muy_corta`, `muy_larga`, `fuera_de_alcance` o `ambigua`. Después, la similitud con bge-m3 contra las fuentes del caso, con umbral 0,55. Una consulta rechazada queda como solicitud `rechazada` con su `motivo` y no se encola. El mensaje explica qué se puede pedir. Los parámetros están en la configuración (migración 0014) |
| 3. Agente sobre el contrato común | Hecha | `app/agentes/evidencia.py` (`AgenteEvidencia`), con las comprobaciones 1, 3 y 5 y el resultado guardado con sus advertencias |
| 4. Regla de acceso abierto | Hecha | Solo se recomiendan los documentos citados con estado OA comprobado (`gold`, `green`, `hybrid` o `bronze`). La comprobación 5 falla si se cita uno sin comprobar. `python -m app.corpus.acceso_abierto` completa el estado desde Unpaywall |
| 5. Ruta directa | Hecha | `POST /caso/evidencias` (202) y `GET /caso/evidencias/{id}` en `app/api/evidencia.py`, en segundo plano (`AtencionEvidencia`). Una solicitud cortada por un reinicio queda `no_atendida` con el motivo `interrumpida` |
| 6. Pantalla de evidencia | Hecha | `frontend/src/paginas/Evidencia.tsx` en `/panel/evidencia`. Cada cita se despliega con el fragmento, el documento, la sección, las páginas y el enlace OA |
| Tarea: abstención registrada y mostrada | Hecha | "Sin evidencia suficiente", con la invitación a aportar una fuente (el aporte llega en T32) |
| Tarea: evidencia divergente sin elegir | Hecha | Las posturas se presentan tal como aparecen; la instrucción prohíbe elegir |

### 22.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| CP-05 superado | **Cumplido** | `test_cp05_sin_evidencia_se_abstiene_e_invita_a_aportar`: una consulta sin fragmentos pertinentes no genera contenido. Entrega "Sin evidencia suficiente" con la invitación, sin llamar al modelo, y la abstención queda registrada en `resultado` con el caso de la solicitud |
| CP-11 superado | **Cumplido** | `test_cp11_una_fuente_cerrada_no_se_recomienda_y_la_verificacion_falla`: con un documento `closed` entre lo recuperado y citado, no aparece en las fuentes recomendadas. La comprobación 5 no se supera y la respuesta va "Con advertencias" con el motivo |
| Ninguna salida del conjunto de prueba cita algo fuera de lo recuperado | **Cumplido con modelo simulado; con modelo real, ver 22.3** | Con el modelo simulado lo garantiza la comprobación 3: una cita inventada se marca "Con advertencias" (`test_una_cita_inventada_se_marca_con_advertencias`). Con Groq, 0 citas fuera de lo recuperado en las 4 respuestas generadas |
| Una fuente cerrada nunca aparece como recomendada | **Cumplido** | Por construcción: las fuentes recomendadas se filtran por estado OA comprobado (CP-11 y la prueba con la base real). En la ejecución con Groq, 0 fuentes cerradas recomendadas |

### 22.3. Pruebas

- **Backend en contenedor (Python 3.12):** 734 pruebas superadas y 7 omitidas, cobertura del 91,64 %. Las omitidas necesitan GROBID o el servicio de modelos, o son las de contrato de DeepSeek y Gemini. Ruff (formato y estilo sobre todo `backend/`) y mypy (estricto sobre `app/`, como la CI) sin observaciones.
- **Unitarias (`unitarias/test_evidencia.py`, 19):**
  - las reglas rechazan con su motivo y aceptan consultas bien formuladas;
  - ninguna consulta del conjunto de T16 se rechaza por reglas;
  - el borrador del conjunto de validación se cumple;
  - los parámetros están en la configuración;
  - la comprobación 5.
- **Integración (`integracion/test_evidencia.py`, 11, con la base real y el modelo simulado):**
  - una consulta fuera de alcance no se encola;
  - el clasificador rechaza una consulta ajena al tema;
  - la entrega con citas desplegables y fuentes abiertas;
  - CP-11, una cita inventada y CP-05;
  - modelo caído (CP-07) y solicitud cortada por un reinicio;
  - aislamiento: otro caso no ve la solicitud y sin versión no se pide;
  - el registro no lleva la consulta ni la salida;
  - el comando de acceso abierto cambia solo esos metadatos.
- **Migraciones:** 0014 sube y baja, y respeta una versión 1 congelada.
- **Matriz de autorización:** las dos rutas nuevas, con `admite_propio` para 503 y 404 del propio caso.
- **Interfaz:** 4 pruebas nuevas en `src/pruebas/evidencia.test.tsx` (rechazo, entrega con citas, abstención y no atendida), 20 en total. Extremo a extremo con Playwright: 6 de 6, con la pantalla nueva sin errores graves de accesibilidad.
- **Validación con bge-m3 real** (corpus provisional): las consultas del tema dan 0,61 a 0,74, las ajenas 0,36 a 0,49 y las del otro tema 0,41 a 0,63. De ahí el umbral 0,55 (T19-01, apartado 2).
- **Comportamiento con Groq** (`python -m app.agentes.evaluar_evidencia`, 3 consultas por tema del conjunto de T16, transacción revertida): 4 respuestas generadas y 2 abstenciones del juicio del modelo, sin errores del proveedor; 0 citas fuera de lo recuperado y 0 fuentes cerradas recomendadas. Una respuesta (T2-03) cita 4 fragmentos de documentos sin OA comprobado: en el flujo real iría "Con advertencias". Cada respuesta tardó entre 88 y 122 s por la espera del límite por minuto (T19-01, apartado 7). Informe en `evaluacion/resultados/comportamiento-d4-t19.json`.
- **Acceso abierto del corpus de desarrollo**, tras el respaldo `datos/respaldos/antes-de-acceso-abierto-2026-11-24.*`:
  - 86 documentos con DOI consultados en Unpaywall;
  - 83 quedan con acceso abierto comprobado (72 `gold`, 6 `hybrid`, 3 `green`, 2 `bronze`);
  - 3 no tienen registro y los 16 sin DOI siguen sin comprobar;
  - los 2.785 fragmentos no cambiaron.

### 22.4. Problemas encontrados y soluciones

- **Límite por minuto de Groq:** cada consulta hace dos llamadas (suficiencia y generación) y el limitador, con la espera máxima de 30 s, hacía fallar la segunda. Como D4 trabaja en segundo plano, con solo Groq se usa `ESPERA_MAXIMA_LIMITADOR_S=65` (`.env.example` y T19-01, apartado 7). No cambia el valor por defecto de T17.
- **La limpieza entre pruebas no restauraba los parámetros de la configuración:** una prueba que bajaba el umbral de pertinencia hacía fallar la de la semilla según el orden. `bd_limpia` ahora restaura los parámetros tal como los deja la migración.
- **La matriz exigía 403 o 401 para todo:** las rutas de evidencia dan 503 sin servicio de modelos y 404 para una solicitud ajena. Se agregó `admite_propio` por entrada.
- **Un archivo JSON guardado por PowerShell llevaba BOM:** los evaluadores leen con `utf-8-sig`.

### 22.5. Pendientes y riesgos

- **Conjuntos del equipo:** la revisión del conjunto de T16 y el conjunto de validación de consultas (T19-01, apartado 9). Sin ellos no hay tasas de la validación previa con datos reales.
- **Reintento con los motivos de la falla:** llega en T30 con el verificador.
- **Grabaciones de DeepSeek y Gemini:** esperan sus claves (apartado 19.5).
- **Base de desarrollo:** sigue en la migración 0013. El agente funciona con los valores por defecto de los parámetros nuevos. La 0014 se aplica cuando el equipo lo indique.

### 22.6. Archivos

- **Creados:**
  - `backend/app/agentes/evidencia.py`, `validacion_consulta.py` y `evaluar_evidencia.py`;
  - `backend/app/api/evidencia.py` y `backend/app/corpus/acceso_abierto.py`;
  - `backend/instrucciones/evidencia/v1.md` y `backend/migraciones/versiones/0014_agente_de_evidencia.py`;
  - `backend/pruebas/unitarias/test_evidencia.py` e `integracion/test_evidencia.py`;
  - `frontend/src/paginas/Evidencia.tsx` y `src/pruebas/evidencia.test.tsx`;
  - `evaluacion/conjuntos/validacion-consultas-t19.json` (borrador) y `evaluacion/resultados/comportamiento-d4-t19.json`;
  - `docs/decisiones/T19-agente-evidencia.md`.
- **Modificados:**
  - `backend/app/administracion/parametros.py`, `app/main.py` y `app/verificacion/comprobaciones.py` (comprobación 5);
  - `backend/app/repositorios/caso.py`, `corpus.py` y `evaluacion.py`;
  - `backend/instrucciones/registro.json`;
  - `backend/pruebas/integracion/conftest.py`, `escenario_rag.py`, `test_matriz_autorizacion.py` y `test_migraciones.py`, y `pruebas/matriz_autorizacion.py` y `unitarias/test_rag.py`;
  - `docs/api/openapi.json` y `frontend/src/api/esquema.d.ts` (regenerados);
  - `frontend/src/App.tsx`, `paginas/PanelCaso.tsx`, `estilos.css` y `e2e/flujo.spec.ts`;
  - `.env.example`, `README.md`, `CLAUDE.md` y este archivo.

### 22.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t19-agente-evidencia`: `4282cad` (`T19: agregar el agente D4 de búsqueda de evidencia, la validación previa de consultas y la regla de acceso abierto`), sin línea de coautoría |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#15 |
| CI de la solicitud | **Verde**, ejecución 45342885551 (la de `4282cad`), 9 de 9 trabajos |
| Integración en `main` | Commit de integración `76fd745` |
| CI de `main` tras integrar | Ejecución 45343961414: **verde** |

### 22.8. Revisión de los conjuntos por el equipo (25 de noviembre de 2026)

El equipo llenó la hoja `evaluacion/revision/revision-conjuntos-t16-t19.xlsx` y se convirtió a JSON (las versiones anteriores son el borrador del asistente).

**Validación de consultas de T19** (`evaluacion/conjuntos/validacion-consultas-t19.json`, versión `revision-1`):
- 30 consultas, 15 aceptadas y 15 rechazadas. Se conservaron 14 del borrador, se descartaron A-01 y A-05 (no son de ninguno de los dos temas) y se agregaron 16.
- Cada consulta lleva ahora `tema`, el del caso contra el que se prueba.
- **Con datos reales:** reglas más pertinencia con bge-m3 sobre el corpus de desarrollo, en solo lectura. **30 de 30 aciertos**, con el motivo esperado en las 15 rechazadas.
  - La aceptada con menor similitud llega a 0,634.
  - Las 3 ajenas al proyecto quedan entre 0,390 y 0,459.
  - El umbral 0,55 tiene margen a ambos lados.
  - Informe en `evaluacion/resultados/validacion-consultas-t19.json`.

**Recuperación de T16, primera ronda** (`evaluacion/conjuntos/recuperacion-t16.json`, versión `revision-1`):
- **13 consultas se mantienen** y forman el conjunto revisado:
  - `documentos_esperados` son los documentos con algún fragmento marcado como que responde, más los que el equipo anotó como faltantes;
  - en T1-01 ningún fragmento responde y queda el documento de origen;
  - `juicios` guarda la marca de cada uno de los 8 fragmentos.
- **7 reescritas y 10 nuevas** quedan en `pendientes_de_revision`, que el evaluador no lee.
- **Segunda ronda:** se recuperaron sus 8 fragmentos con el texto nuevo, en `evaluacion/revision/revision-t16-segunda-ronda.xlsx`. Con el texto reescrito, el documento de origen de T2-03 sale primero, el de T1-02 sigue sin aparecer y el de T2-08 dejó de aparecer.
- **Precisión contextual en las 13 revisadas:** 0,665 con las marcas del equipo por fragmento, frente a 0,786 a nivel de documento (la medida de la línea base de T16). La diferencia viene de fragmentos del documento correcto que no responden. Qué medida se reporta se decide en T34 con el conjunto completo.
- **Pruebas:** `test_rag.py` y `test_evidencia.py` leen los conjuntos revisados (estado `revisado`, 13 y 30 consultas) y pasan.

**Propuesta del equipo para T34:** reportar como medida principal la precisión contextual estricta, con marcas por fragmento, y dejar la de documentos esperados como referencia. Está anotada en la decisión T16-01, apartado 7.

**Pendiente:** la segunda ronda de T16 (17 consultas).

**Confirmación:** el equipo aceptó la conversión el 25 de noviembre de 2026. Estos cambios, junto con el registro de la integración de T19 (22.7), entran en el primer commit de T20.

## 23. Fase 3 (F3): T20. Agente D4: verificación de referencias

Rama `t20-verificacion-referencias`, desde `main` con T19 (`76fd745`). Decisión: `docs/decisiones/T20-verificacion-referencias.md` (T20-01). Decisión del equipo del 25 de noviembre de 2026 ("paquete recomendado"):
- un DOI que lleva a otra obra da "con discrepancias", nunca "verificada";
- un año que difiere, aunque sea en uno, es discrepancia;
- en Vancouver, citas entre corchetes o paréntesis, sin superíndices y con aviso;
- explicación de las discrepancias con el modelo, apagada por defecto;
- trabajo en segundo plano con avance;
- libros por metadatos, sin ISBN;
- el asistente arma el borrador del conjunto de prueba y el equipo lo revisa con una hoja de Excel.

**Insumos del equipo:** la revisión del conjunto de referencias de prueba con `evaluacion/revision/revision-referencias-t20.xlsx`. Es una fila por referencia (tipo, estado esperado, campos con error) y otra por cita de los dos borradores. Mientras llega, se trabajó con datos ficticios en la CI y con el borrador del asistente sobre obras reales.

**Incluye también:** el registro de la integración de T19 (22.7), la revisión de los conjuntos de T16 y T19 (22.8) y la propuesta del equipo de medida para T34, que quedaron sin confirmar en `main`.

### 23.1. Actividades

| Actividad | Estado | Evidencia |
| --- | --- | --- |
| 1. Estructurar la lista con GROBID | Hecha | `AtencionReferencias` envía a `processCitationList` las entradas que detectó T12. Si GROBID no trae el DOI o el año y la entrada los tiene, se toman del texto (el año, sin mirar el DOI) |
| 2. Extractores de citas por norma | Hecha | `app/agentes/citas.py`. IEEE: `[1]`, `[1], [3]`, `[1]-[3]` y `[2-4]`. Vancouver: además `(1)`, `(2,3)` y `(1-3)`. APA 7: entre paréntesis (`&`, `y`, `et al.`, varias obras, varios años, letras, página y `s. f.`) y narrativas |
| 3. DOI en Crossref; sin DOI, metadatos en Crossref y OpenAlex | Hecha | `Verificador`, con los clientes de T14. Compara título, autores (también el primero) y año |
| 4. Estados | Hecha | `verificada`, `con_discrepancias`, `no_localizada` y `no_comprobable` (RN-18). El modelo no interviene |
| 5. Cruce de citas y lista | Hecha | Por número o por primer apellido y año, con citas sin entrada y entradas no citadas |
| 6. Explicación con el modelo, si se configura | Hecha | `explicar_discrepancias` (migración de datos 0015, apagado por defecto) e instrucción `referencias/v1`. Al modelo solo van las discrepancias |
| 7. Informe en la interfaz y en el registro | Hecha | `frontend/src/paginas/Referencias.tsx` en `/panel/referencias`. El informe se guarda como `resultado` con la comprobación 1 |
| 8. Conjunto de prueba de referencias | Hecha, en borrador | `evaluacion/conjuntos/referencias-t20.json` y dos borradores .docx: 8 reales, 6 con errores y 6 fabricadas, en IEEE y APA 7. A revisar por el equipo |
| Tarea: el modelo no decide estados | Hecha | El estado sale del `Verificador`. Una prueba comprueba que, con explicaciones, los estados no cambian |
| Tarea: límite de búsqueda de Crossref | Hecha | Los clientes de T14 respetan su cubeta. El objetivo de 120 s para 40 referencias se mide en T30 |
| Tarea: libros con ISBN por metadatos | Hecha | Búsqueda por título, autor y año. Escenario `libro` en las pruebas |

### 23.2. Criterios de aceptación

| Criterio | Estado | Cómo se comprobó |
| --- | --- | --- |
| CP-12 superado | **Cumplido** | `test_cp12_informe_completo_en_ieee` y `..._en_apa7`, con la base real y servicios simulados. Cada entrada se marca verificada, con discrepancias o no localizada según su escenario, con los campos esperados, y se señalan la cita sin entrada y la entrada no citada. Con servicios reales, sobre el conjunto de obras reales, los 40 estados coinciden con la clave (23.3) |
| CP-13 superado | **Cumplido** | `test_cp13_con_los_servicios_caidos_nada_queda_inexistente`: con Crossref y OpenAlex sin responder, las 11 quedan `no_comprobable`, el informe avisa que la verificación no pudo completarse y ninguna queda `no_localizada`. En las pruebas unitarias, también cuando cae un solo servicio |
| Ninguna referencia fabricada del conjunto queda como verificada | **Cumplido** | Sin red: las tres fabricadas de los borradores de prueba, en ambas normas. Con servicios reales: 0 de 12 (6 por norma) en el conjunto de obras reales |
| Las citas se extraen correctamente en ambas normas sobre los borradores de prueba | **Cumplido** | 48 pruebas unitarias de extractores. En los borradores ficticios y en los de obras reales, todas las citas, la cita sin entrada y la entrada no citada coinciden con la clave en IEEE y en APA 7 |

### 23.3. Pruebas

- **Backend en contenedor (Python 3.12):** 816 pruebas superadas y 7 omitidas, cobertura del 91,18 %. Las omitidas necesitan GROBID o el servicio de modelos, o son los contratos de DeepSeek y Gemini. Ruff (formato y estilo sobre todo `backend/`) y mypy (estricto sobre `app/`) sin observaciones.
- **Unitarias:** `test_citas.py` (48: extractores por norma, entradas, cruce y año desde el texto) y `test_verificacion_referencias.py` (21: estados, discrepancias, DOI ajeno, DOI mal escrito, libro, servicios caídos y salvaguardas de GROBID).
- **Integración (`test_referencias.py`, 12):**
  - CP-12 en IEEE y APA 7, y CP-13;
  - el resultado registrado en la base;
  - sin versión (409), lista no detectada (422) y GROBID caído (`no_atendida`);
  - aislamiento entre casos;
  - el registro no lleva el texto de las referencias;
  - las explicaciones: apagadas por defecto, encendidas con el modelo simulado y con el modelo caído.
- **Migraciones:** 0015 sube y baja, y respeta una versión 1 congelada. **Matriz de autorización:** las dos rutas nuevas.
- **Interfaz:** 3 pruebas nuevas (lista no detectada, avance e informe completo, no atendida), 23 en total. Extremo a extremo con Playwright: 7 de 7, con la pantalla nueva sin errores graves de accesibilidad.
- **Con servicios reales** (`python -m app.agentes.evaluar_referencias`, GROBID, Crossref y OpenAlex, sin base ni modelo; informe en `evaluacion/resultados/verificacion-referencias-t20.json`):
  - 20 de 20 estados iguales a la clave en IEEE y 20 de 20 en APA 7;
  - 0 fabricadas verificadas;
  - en ambas normas se detectan la cita sin entrada y la entrada no citada, y se extraen 20 de 20 citas.

### 23.4. Problemas encontrados y soluciones

- **GROBID no devolvía el año** de tres entradas IEEE reales con páginas largas (`pp. 101805`). Ahora el año se toma del texto de la entrada, sin mirar el DOI.
- **GROBID tomó la revista como título** en una obra cuyo título termina en "año 2023". Si el título de la fuente está tal cual en la entrada, no se marca discrepancia de título. Un título cambiado o un DOI ajeno siguen detectándose: no contienen el título real.
- **GROBID parte los apellidos compuestos** ("Alarcón Llontop" quedaba como "Llontop") y daba citas APA sin entrada falsas. En APA el apellido sale del texto de la entrada (`Apellido, I.`).
- **Un primer autor cambiado con coautores reales pasaba como verificada.** Ahora también se exige que coincida el primer autor.
- **Choque de nombres en el contrato:** `ReferenciaVista` ya existía en T15, y el contrato renombraba ambos modelos. El nuevo se llama `ReferenciaVerificadaVista`.
- **Lista no detectada:** el mensaje remitía a una pantalla de marcado que todavía no existe (la ruta es de T12). Ahora pide poner a la lista un título con estilo y volver a cargar la versión.

### 23.5. Pendientes y riesgos

- **Revisión del conjunto por el equipo** (`revision-referencias-t20.xlsx`). El resultado con servicios reales es sobre el borrador del asistente.
- **Pantalla para marcar a mano** la lista de referencias o las secciones: la ruta existe desde T12; su pantalla no es de esta fase.
- **Vancouver con servicios reales** y un borrador completo, y la **explicación con un modelo real** (apagada por defecto).
- **Rendimiento** de 40 referencias en 120 s (RNF-12): se mide en T30.
- **Segunda ronda de T16** (22.8).

### 23.6. Archivos

- **Creados:**
  - `backend/app/agentes/citas.py`, `verificacion_referencias.py`, `referencias.py` y `evaluar_referencias.py`;
  - `backend/app/api/referencias.py`;
  - `backend/instrucciones/referencias/v1.md` y `backend/migraciones/versiones/0015_verificacion_de_referencias.py`;
  - `backend/pruebas/unitarias/test_citas.py`, `test_verificacion_referencias.py` e `integracion/test_referencias.py`;
  - `backend/pruebas/datos/referencias_t20.py` y `pruebas/dobles_referencias.py`;
  - `backend/pruebas/contrato/grobid/referencias_t20_ieee.tei.xml` y `referencias_t20_apa7.tei.xml`, y `pruebas/datos/docx/referencias_ieee.docx` y `referencias_apa7.docx`;
  - `frontend/src/paginas/Referencias.tsx` y `src/pruebas/referencias.test.tsx`;
  - `evaluacion/conjuntos/referencias-t20.json` y `referencias-t20/` (dos borradores), y `evaluacion/resultados/verificacion-referencias-t20.json`;
  - `evaluacion/revision/` (hojas de revisión de T16, T19 y T20);
  - `docs/decisiones/T20-verificacion-referencias.md`.
- **Modificados:**
  - `backend/app/administracion/parametros.py` y `app/main.py`;
  - `backend/instrucciones/registro.json`;
  - `backend/pruebas/datos/generar_docx_muestra.py`, `pruebas/contrato/grabar_grobid_referencias.py` (graba también las listas de T20), `pruebas/matriz_autorizacion.py` e `integracion/test_migraciones.py`;
  - `docs/api/openapi.json` y `frontend/src/api/esquema.d.ts` (regenerados);
  - `frontend/src/App.tsx`, `paginas/PanelCaso.tsx`, `estilos.css` y `e2e/flujo.spec.ts`;
  - `README.md`, `CLAUDE.md` y este archivo;
  - de la revisión de T16 y T19 (22.8): los dos conjuntos, `test_rag.py`, `test_evidencia.py` y las decisiones T16-01 y T19-01.

### 23.7. Integración

| Paso | Resultado |
| --- | --- |
| Rama y confirmaciones | `t20-verificacion-referencias`: `e9e17dd` (`T20: agregar la verificación de referencias del agente D4, los extractores de citas por norma y el conjunto de prueba`), sin línea de coautoría. Incluye el registro de la integración de T19 (22.7) y la revisión de los conjuntos (22.8) |
| Solicitud de cambio | DavidAndreRoca/SistemaMultiagenteRag#16 |
| CI de la solicitud | **Verde**, ejecución 45551444643 (la de `e9e17dd`), 9 de 9 trabajos |
| Integración en `main` | Commit de integración `0d3870c` |
| CI de `main` tras integrar | Ejecución 45556140317: **verde** |

## 24. Prototipo navegable (cambio de plan del 26 de noviembre de 2026)

El equipo pidió priorizar un prototipo demostrable de punta a punta para el docente: el estudiante entra, carga su borrador, consulta evidencia y verifica sus referencias. Se cierra en forma ligera: solicitud de cambio, CI e integración.

**Fases para el recorrido:**
- **Imprescindibles, ya hechas:** T03 a T20 (autenticación, casos, borradores y secciones, corpus, recuperación, modelos, agente D4 de evidencia y de referencias, interfaz).
- **Corrección del equipo (26 de noviembre de 2026):** el cambio de plan omite las revisiones humanas, no recorta el sistema.
  - **Reactivadas:** T22 a T33, en el orden de la hoja de ruta, empezando por lo de más valor visible en la demostración.
  - **Siguen pospuestas:** T21 (ensayo en Oracle; la demostración es local), T34 y T38 (mediciones finales, al final y con revisión del equipo) y T35 a T37 y T39 a T44.
  - **Pantalla:** mientras un agente no esté completo, el panel lo muestra como "Pendiente", sin enlace.

**Prototipo** (`scripts/prototipo.ps1`, `docker-compose.demo.yml`, guion en `docs/demo/guion-prototipo.md`):
- Usa la base de desarrollo con el corpus provisional (`sma_rag`), los servicios compartidos y la interfaz en http://127.0.0.1:5173.
- `python -m app.bd.demo` crea el investigador `INV-DEMO` y el caso `DEMO-01` (TEMA-1-IA-EDUCACION, IEEE). Las contraseñas van solo a `datos/demo/credenciales.txt`, fuera de Git. La demostración anterior (`scripts/demo.ps1`, base vacía, para el asesor) no cambia.
- **Base de desarrollo:** migrada de 0013 a 0015 (solo configuración) tras el respaldo `datos/respaldos/antes-de-0015-2026-11-26.*`.
- **Títulos del corpus:** 9 títulos vacíos, cortos o en mayúsculas se tomaron de Crossref (`python -m app.corpus.titulos`). Solo cambia el título; los 2.785 fragmentos siguen iguales.
- **Corrección:** las referencias de doi.org ya no muestran entidades HTML ("&amp;").
- **Recorrido comprobado en el navegador** el 26 de noviembre de 2026:
  - entrada con `DEMO-01-1`;
  - carga del borrador de demostración;
  - evidencia en 92 s, con 5 afirmaciones citadas y 3 fuentes de acceso abierto recomendadas;
  - verificación de referencias en unos 7 s, con 4 verificadas, 2 con discrepancias, 1 no localizada, la cita [8] sin entrada y la entrada [7] no citada, como se preparó.
- **Lista de solicitudes en el panel** (pedida por el equipo el 26 de noviembre de 2026; versión reducida del historial de T33):
  - `GET /caso/solicitudes` lista las búsquedas de evidencia y las verificaciones del caso, sin las rechazadas;
  - el panel muestra la tabla "Sus búsquedas y verificaciones" con "Ver resultado";
  - las pantallas guardan la solicitud en la dirección (`?solicitud=...`), así un resultado sobrevive a una recarga y se abre desde la lista;
  - una prueba de integración comprueba que otro caso no ve la lista (aislamiento), y la matriz incluye la ruta;
  - comprobado en el navegador.

**Conjuntos revisados por el equipo** (hojas entregadas el 26 de noviembre de 2026):
- **T16:** 30 consultas (13 de la primera ronda y 17 de la segunda). Precisión contextual estricta, con las marcas del equipo por fragmento: 0,647; en 6 consultas ningún fragmento del contexto responde.
- **T20:** 32 referencias (20 del asistente, con dos correcciones, y 12 del equipo), con la lista APA en orden alfabético sin acentos. Con GROBID, Crossref y OpenAlex reales: 64 de 64 estados iguales a la clave, 0 fabricadas verificadas, y la cita sin entrada y la entrada no citada detectadas en IEEE y APA 7.

**Provisional, sin revisión humana** (decidido por el asistente, según las reglas del equipo del 26 de noviembre de 2026):
- el borrador de demostración (`docs/demo/borrador-demostracion.docx`): texto ficticio y elección de sus 7 referencias y errores;
- la consulta del guion y los textos del guion;
- la aplicación de los comentarios de las hojas: R-04 queda verificada pese al año ambiguo; en T16, las consultas nuevas sin documento de origen toman como origen su primer documento esperado;
- la corrección de títulos del corpus desde Crossref.

**Integración:** solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#17, CI verde (ejecución 45870830391, 9 de 9 trabajos), integrada en `main`.

**Lugar de la presentación (equipo, 26 de noviembre de 2026):** por ahora desde la computadora local con `scripts/prototipo.ps1`; el servidor (T21) sigue pospuesto.

**Integración de la lista de solicitudes:** solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#18, CI verde (ejecución 45873636447, 9 de 9 trabajos), integrada en `main`.

### 24.1. Diseño visual del prototipo (cambio visual sin impacto funcional)

Ninguna fase de la hoja de ruta cubre el diseño visual: T13 dejó la interfaz base, T33 completa el contenido del panel y T41 endurece la accesibilidad. A pedido del equipo, se hizo como mejora acotada.

- **Qué cambia:**
  - **Hoja de estilos:** paleta con variables (azul marino principal, verde azulado de acento, fondo gris claro, estados con texto sobre fondo claro), tipografía del sistema con jerarquía de títulos y espaciado uniforme.
  - **Componentes:** tarjetas para las secciones e insignias de estado con palabra, no solo color.
  - **Encabezado:** oscuro, con un ícono simple (`Logo.tsx`, decorativo) y el nombre del sistema, que no cambia.
  - **Inicio de sesión:** centrado, con el ícono, el nombre y una descripción breve.
  - **Panel:** "Qué puede pedir" con tarjetas. Evidencia y referencias están activas; estructura, metodología y redacción figuran como "Pendiente".
- **Qué no cambia:** la lógica, las rutas, los datos y los textos que usan las pruebas.
- **Accesibilidad:** contraste AA en todos los textos, foco visible (amarillo sobre el encabezado oscuro) y el mismo orden de tabulación.
- **Pruebas:** extremo a extremo con Playwright y revisión automática de accesibilidad, 7 de 7; 24 pruebas de la interfaz, lint, tipos y compilación.
- **Capturas:** antes y después en `docs/demo/capturas/` (`frontend/capturas/`, que no forma parte de las pruebas).
- **Provisional, sin revisión humana:** la descripción del sistema en el inicio de sesión y los textos de las tarjetas de acciones.

**Integración del diseño visual:** solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#19, CI verde (ejecución 45876704509, 9 de 9 trabajos), integrada en `main`.

## 25. Bloque 2: T22 (corpus de guías) y T23 (agente de estructura y coherencia)

Rama `t22-t23-guias-y-estructura`. Decisión: `docs/decisiones/T22-T23-guias-y-estructura.md`. Cierre ligero, según las reglas del equipo del 26 de noviembre de 2026.

- **T22:**
  - comando `python -m app.corpus.guias`, con segmentación por apartado y la sección registrada;
  - la rúbrica se rechaza por nombre y por huella;
  - en la base de desarrollo quedan indexadas 4 guías provisionales, con 28 fragmentos;
  - las 4 consultas de prueba, una por tipo de guía, traen primero el apartado esperado;
  - pruebas: 6 unitarias y 2 de integración (indexación sin duplicar, recuperación solo para D1 a D3 y rechazo de la rúbrica).
- **T23:**
  - el agente `AgenteEstructura`, con la instrucción `estructura/v1`;
  - la comprobación 2 de no reescritura (CP-08), con 4 pruebas unitarias;
  - la atención por sección, las rutas `/caso/estructura` y la pantalla `/panel/estructura`; la tarjeta del panel ya está activa;
  - la migración 0016, que en la base de desarrollo creó la versión 2 de la configuración porque la 1 ya la usaban solicitudes (RNF-21).
  - **Pruebas:**
    - 5 de integración: secciones revisables, CP-08 con orden por severidad y criterios, reescritura "Con advertencias", abstención sin guías y aislamiento;
    - 2 de la migración y 1 de la interfaz;
    - extremo a extremo 8 de 8, con accesibilidad.
  - **Modelo real:** con la introducción del borrador de demostración, 3 hallazgos con citas a las guías y comprobaciones superadas, en 20 s.
- **Provisional, sin revisión humana:**
  - las 4 guías de `backend/guias/provisionales/`;
  - la instrucción `estructura/v1`;
  - los textos de la pantalla;
  - la única prueba con el modelo real, sobre el borrador de demostración.
- **Pendiente:** el conjunto de borradores con errores estructurales y su clave, que arma el asistente antes de T34, y el reintento, en T30.

**Integración de T22 y T23:** solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#20, CI verde (ejecución 45880622403, 9 de 9 trabajos), integrada en `main`.

## 26. Bloque 2: T27 (agente estilístico, propuesta de redacción)

Rama `t27-agente-redaccion`. Decisión: `docs/decisiones/T27-agente-de-redaccion.md`. Cierre ligero, según las reglas del equipo del 26 de noviembre de 2026.

- **Agente D3:**
  - `AgenteRedaccion` y `AtencionRedaccion`, con la instrucción `redaccion/v1`;
  - la atención común `AtencionPorAlcance`, que reutilizan D1 y D3 (y D2 en T26);
  - las rutas `/caso/redaccion` y la pantalla `/panel/redaccion`, con original y propuesta lado a lado, cambios resaltados y la pauta de cada cambio; la tarjeta del panel ya está activa.
- **Límites:**
  - CP-09 antes de crear la solicitud: más de un párrafo o más de 250 palabras se rechaza; títulos y lista de referencias no se admiten (RN-17);
  - CP-10 con la comprobación 2 `limites_propuesta`: hasta 1.2 veces, un párrafo, sin números ni citas nuevas y cambios presentes en el texto.
- **Migraciones:**
  - 0017, instrucción `redaccion/v1`: en la base de desarrollo creó la versión 3 de la configuración;
  - 0018, tope de salida de Groq de 4096 tokens: creó la versión 4.
- **Proveedor:** el 400 `json_validate_failed` de Groq (salida cortada o que no cumple el esquema) ahora se reintenta, y el registro guarda el código del proveedor, sin contenido.
- **Pruebas:**
  - 11 unitarias de `limites_propuesta` y `contar_palabras`;
  - 6 de integración: párrafos sin títulos ni referencias, CP-10 superado y excedido, cita nueva, CP-09 sin crear solicitud y aislamiento;
  - 3 de migraciones;
  - 2 del proveedor;
  - 4 de la interfaz, con el comparador;
  - 1 extremo a extremo con accesibilidad.
- **Modelo real:** 2 párrafos del borrador de demostración, con las comprobaciones superadas; entre 30 y 140 s por el límite de tokens por minuto de Groq.
- **Provisional, sin revisión humana:**
  - la guía `lista-comprobacion-redaccion.md`;
  - la instrucción `redaccion/v1`;
  - el párrafo coloquial agregado al borrador de demostración;
  - los textos de la pantalla;
  - las dos pruebas reales.
- **Pendiente:** el conjunto de párrafos con errores de redacción y su clave, que arma el asistente antes de T34; el reintento y el evaluador de conservación del contenido, en T30.

**Integración de T27:** solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#21, CI verde (ejecución 45932874643, 9 de 9 trabajos), integrada en `main`.

## 27. Bloque 2: T26 (agente metodológico)

Rama `t26-agente-metodologia`. Decisión: `docs/decisiones/T26-agente-metodologico.md`. Cierre ligero, según las reglas del equipo del 26 de noviembre de 2026.

- **Agente D2:**
  - `AgenteMetodologia` y `AtencionMetodologia`, con la instrucción `metodologia/v1`;
  - `identificar_diseno` reconoce el diseño declarado; si no se nombra, el agente lo pregunta;
  - la herramienta `lista_de_comprobacion(diseno)` lee del corpus de guías los criterios del diseño y los comunes, y sus criterios abreviados son la consulta de recuperación;
  - el contrato de agentes suma `consulta_con_herramientas`;
  - las rutas `/caso/metodologia` y la pantalla `/panel/metodologia`; la tarjeta del panel ya está activa, y "Plan de tarea" (T24) figura como pendiente.
- **Comprobación 2 para D2:** no reescritura (CP-08), que ahora también revisa las preguntas, y `sin_datos_inventados`: ningún número que no esté en la sección del estudiante o en un fragmento citado.
- **Migración 0019:** instrucción `metodologia/v1`. En la base de desarrollo creó la versión 5 de la configuración.
- **Pruebas:**
  - 13 unitarias: diseño declarado, números y consulta;
  - 5 de integración: secciones con su diseño, diseño no identificable con pregunta, lista del diseño cuasiexperimental, valor inventado "Con advertencias" y aislamiento;
  - 1 de migraciones y 1 de la interfaz;
  - 1 extremo a extremo con accesibilidad.
  - Se corrigió la prueba de la semilla de configuración, que dependía del orden: ahora restaura la semilla con `bd_limpia`.
- **Modelo real:** el Método del borrador de demostración, con un párrafo nuevo con errores a propósito, en 85 s.
  - **Hallazgos:** 3, de severidad alta: la afirmación causal en un diseño correlacional, la muestra y el instrumento sin justificar y el análisis sin prueba.
  - **Preguntas:** 7, sobre lo que falta.
  - **Comprobaciones:** las 4 superadas.
- **Provisional, sin revisión humana:**
  - la instrucción `metodologia/v1`;
  - el párrafo con errores metodológicos del borrador de demostración;
  - los textos de la pantalla;
  - la prueba real.
- **Pendiente:** la hoja de errores metodológicos con su clave, que arma el asistente antes de T34; el reintento, en T30.

**Integración de T26:** solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#22, CI verde (ejecución 45936782234, 9 de 9 trabajos), integrada en `main`.

## 28. Bloque 2: T24 (plan de tarea del hito)

Rama `t24-plan-de-tarea`. Decisión: `docs/decisiones/T24-plan-de-tarea.md`. Cierre ligero, según las reglas del equipo del 26 de noviembre de 2026. Con T24, los cinco tipos de solicitud con agente de lenguaje tienen pantalla, y el panel ya no muestra agentes pendientes.

- **Plan de tarea:**
  - `AgentePlan` y `AtencionPlan`, con la instrucción `plan/v1`;
  - el alcance es de hito; al modelo va el estado del borrador (títulos, palabras y elementos detectados), no su texto;
  - la herramienta `instrucciones_del_hito` lee el apartado del hito en las guías;
  - las rutas `/caso/plan` y la pantalla `/panel/plan`, con el plan copiable y descargable en texto.
- **Abstención sin instrucciones del hito:** el contrato suma `falta_insumo` y `ServicioEvidencia.abstener` (paso `herramienta`); se abstiene sin recuperar ni llamar al modelo.
- **Guía provisional nueva:** `guia-estado-del-arte-y-plan.md`, para que el avance 2 y la entrega del plan tengan pautas. Con la consulta final, los 8 hitos traen su instrucción y una pauta pertinente sobre el umbral.
- **Migración 0020:** instrucción `plan/v1`. En la base de desarrollo creó la versión 6 de la configuración.
- **Pruebas:**
  - 2 unitarias;
  - 5 de integración: hitos con versión, plan con el estado del borrador, abstención sin instrucciones sin recuperar ni generar, hito sin versión o inexistente y aislamiento;
  - 1 de migraciones y 3 de la interfaz, incluido el texto descargable;
  - 1 extremo a extremo con accesibilidad.
- **Modelo real:** el avance 1 del borrador de demostración dio 9 tareas en orden con su criterio y sus citas, en 21 s y con las comprobaciones superadas.
- **Provisional, sin revisión humana:**
  - la instrucción `plan/v1`;
  - la guía `guia-estado-del-arte-y-plan.md`;
  - los textos de la pantalla;
  - la prueba real.
- **Pendiente:** el reintento, en T30.

**Integración de T24:** solicitud de cambio DavidAndreRoca/SistemaMultiagenteRag#23, CI verde (ejecución 45941793107, 9 de 9 trabajos), integrada en `main`.

## 29. Bloque 3: T28 (orquestación, cola y trabajador)

Rama `t28-orquestacion-cola`. Decisión: `docs/decisiones/T28-orquestacion-cola-trabajador.md`. Cierre ligero, según las reglas del equipo del 26 de noviembre de 2026.

- **Un solo camino:** grafo de LangGraph 1.2 (validar, enrutar, ejecutar, verificar, etiquetar, registrar y entregar, o no atendida), con enrutamiento por tabla fija tipo a agente, sin modelo. Las seis atenciones son ahora ejecutores con tres pasos, y una fábrica por proceso comparte la cadena de modelos.
- **Checkpointer en PostgreSQL:** sus tablas las crea la migración 0021. El estado guardado no lleva texto del borrador ni de la salida.
- **Cola y trabajador:**
  - la cola usa `FOR UPDATE SKIP LOCKED`; el trabajador es un proceso aparte (`app.orquestacion.trabajador`, servicio `trabajador`) con concurrencia configurable;
  - recupera las solicitudes huérfanas;
  - una caída del proveedor devuelve la solicitud a la cola, con espera, hasta 3 intentos técnicos.
- **API:** las rutas solo crean la solicitud. La ejecución en el proceso de la API (`EJECUCION_EN_PROCESO`) queda para pruebas. Las pantallas siguen también los estados "verificando" y "reintentando".
- **Trazas en la nube:** pospuestas por decisión del equipo; la configuración no arranca si se encienden.
- **Pruebas:**
  - 9 de integración del orquestador (CP-03, CP-04, CP-07, huérfanas, espera tras la caída, checkpointer real sin texto y API en cola) y 4 unitarias de enrutamiento;
  - las pruebas de todas las pantallas pasan ahora por el grafo;
  - backend 900 y frontend 33;
  - extremo a extremo: se corrigió una carrera en la prueba de redacción, que abría la lista antes de que llegaran los párrafos.
- **Modelo real, con el trabajador en el prototipo:** el plan de tarea en 37 s y la revisión de estructura pedida desde el navegador en 43 s.
- **Pendiente:**
  - el avance "n de m referencias" solo se ve con la ejecución en proceso, y vuelve con los eventos de T29;
  - formulario, eventos y reenvío (T29);
  - reintento y evaluador (T30).
