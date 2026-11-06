# Estado del desarrollo

Registro del avance **verificado** frente a `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`. Solo se marca como cumplido lo que se comprobó con una prueba o un comando cuyo resultado se anota aquí.

**Última actualización:** 6 de noviembre de 2026 (Fase 2: T04 a T07, y contraste de T04 con la especificación de la Fase 1, apartado 10.9).

## Resumen

| Fase | Nombre | Estado |
| --- | --- | --- |
| T00 (F0) | Cuentas, accesos y secretos | Fuera de esta sesión: lo realizan los integrantes. Sin verificar |
| **T01 (F1)** | Servidor de desarrollo en Oracle | **Parcial**: documentación y verificación de imágenes ARM hechas; la instancia no existe aún |
| **T02 (F1)** | Repositorio, calidad de código e integración continua | **Implementada**; el repositorio ya está en GitHub (`DavidAndreRoca/SistemaMultiagenteRag`, confirmación `84f444c`). No se pudo consultar el resultado de la CI desde esta sesión (credenciales de `gh` inválidas) |
| **T03 (F1)** | Infraestructura base de la aplicación (H0) | **Completa y verificada** (criterios de aceptación cumplidos) |
| **T04 (F2)** | Modelo de datos, diccionario y migraciones | **Completa y verificada**. Contrastada con la especificación de la Fase 1 y la ficha de métricas (migraciones 0005 y 0006, apartado 10.9). Queda provisional tau = 0.5 hasta T34 |
| **T05 (F2)** | Repositorios con aislamiento por caso | **Completa y verificada** |
| **T06 (F2)** | Autenticación, roles y sesiones | **Completa y verificada** |
| **T07 (F2)** | Casos, temas, colecciones y cuentas | **Completa y verificada** (CP-22 superado) |
| T08 en adelante | | No iniciadas |

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
| 1. Crear la instancia ARM | **Pendiente** (requiere la cuenta de Oracle de David) | |
| 2. Endurecer SSH (solo llave) | **Pendiente**; procedimiento documentado | `docs/operacion/servidor-desarrollo.md`, apartado 2 |
| 3. Usuarios Linux por integrante | **Pendiente**; procedimiento documentado | idem, apartado 3 |
| 4. Instalar Docker, Compose, Git, Python 3.12, Node LTS, Claude Code | **Pendiente**; script de verificación listo | `scripts/verificar-herramientas.sh` |
| 5. Documentar conexión e inactividad | **Hecha** | `docs/operacion/servidor-desarrollo.md` |
| Tarea: verificar imágenes ARM | **Hecha** | `scripts/verificar-imagenes-arm.sh` |
| Tarea: Compose `compartido` y bases por integrante | Documentado; el `docker-compose.yml` admite nombre de proyecto y puertos por integrante | `.env.example` (`COMPOSE_PROJECT_NAME`, `PUERTO_BD`, `PUERTO_API`) |

### Hallazgo: GROBID sin arm64 en la serie 0.8.x (riesgo R-03)

La consulta de manifiestos mostró que `grobid/grobid:0.8.x` (todas sus variantes), `0.9.0` y `0.9.1-full` son **solo amd64**. Solo `grobid/grobid:0.9.0-crf` y `0.9.1-crf` publican arm64. Como pide T01, quedó registrado en `docs/decisiones/T01-grobid-arm64.md` con una **propuesta** (usar `0.9.1-crf` y medir su calidad en T09) que **deben confirmar los integrantes** antes de T08.

### Criterios de aceptación

| Criterio | Estado |
| --- | --- |
| Ambos integrantes entran por SSH con su usuario | Pendiente |
| `docker run` de PostgreSQL con pgvector en ARM | Pendiente en ARM. La imagen publica arm64 (verificado) y funciona en amd64 local |
| Claude Code se inicia en la carpeta de cada usuario | Pendiente |

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
| La integración continua termina en verde con el repositorio vacío | **Verificado en local (equivalente); pendiente en GitHub** | Los mismos comandos de cada trabajo pasan con Python 3.12 en contenedor; `actionlint` 1.7.7 valida el flujo sin errores |

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

Trabajo hecho sobre `main` local, **sin confirmar** (los integrantes confirman y publican). Verificación en un contenedor con Python 3.12.16 y PostgreSQL 16 con pgvector 0.8.7.

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
4. **Normas `ieee` y `apa7`**: propuesta de D-12, a confirmar antes de T20. Desde 0006 los códigos van en minúsculas.
5. **CI en GitHub**: los cambios de la Fase 2 no están confirmados ni publicados. Tampoco se pudo ver desde esta sesión el resultado de la CI de la Fase 1.

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

Detalle de cada diferencia y su justificación en `docs/decisiones/T04-contraste-especificacion-fase1.md`. Trabajo sin confirmar en `main` local. Las migraciones 0001 a 0004 no se tocaron.

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
- La lista de normas queda pendiente de confirmación antes de T20 (D-12).
- Las instrucciones oficiales de cada hito llegan en T22.
- La deduplicación por DOI y la confirmación de documentos incompletos se dejan para T09, T10 y T15, sin adelantarlas.
