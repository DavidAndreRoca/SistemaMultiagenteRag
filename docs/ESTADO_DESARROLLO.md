# Estado del desarrollo

Registro del avance **verificado** frente a `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`. Solo se marca como cumplido lo que se comprobó con una prueba o un comando cuyo resultado se anota aquí.

**Última actualización:** 6 de noviembre de 2026.

## Resumen

| Fase | Nombre | Estado |
| --- | --- | --- |
| T00 (F0) | Cuentas, accesos y secretos | Fuera de esta sesión: lo realizan los integrantes. Sin verificar |
| **T01 (F1)** | Servidor de desarrollo en Oracle | **Parcial**: documentación y verificación de imágenes ARM hechas; la instancia no existe aún |
| **T02 (F1)** | Repositorio, calidad de código e integración continua | **Implementada localmente**; falta publicar en GitHub y comprobar los controles en solicitudes de cambio reales |
| **T03 (F1)** | Infraestructura base de la aplicación (H0) | **Completa y verificada** (criterios de aceptación cumplidos) |
| T04 en adelante | | No iniciadas |

**Interpretación de "Fase 1":** la hoja de ruta (apartado 5) hace corresponder la fase F1 de la planificación con T01 a T03. Esta es la fase ejecutada. T00 (F0) es administrativa y no la puede hacer el asistente.

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
