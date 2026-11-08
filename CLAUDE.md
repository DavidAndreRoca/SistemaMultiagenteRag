# CLAUDE.md

Sistema multiagente con RAG para la asistencia en la producción de artículos científicos empíricos (UTP, Ica). Autores: David Roca Cáceres y Ángel Martín Peña García.

## Fuente de instrucciones

- Documento maestro: `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`. **No se modifica ni se elimina.** Cada fase (T00 a T44) se ejecuta sin reinterpretar el proyecto.
- Estado real del desarrollo: `docs/ESTADO_DESARROLLO.md`. Se actualiza al cerrar cada fase, solo con lo verificado.
- Decisiones técnicas: `docs/decisiones/` (un archivo por decisión).
- Si la especificación técnica de la Fase 1 y la hoja de ruta discrepan, manda la especificación (cópiela a `docs/especificacion-fase1/`).

## Reglas que no se rompen en ninguna fase (hoja de ruta, apartado 0)

- No implementar funcionalidades de fases posteriores "por adelantado".
- No modificar el esquema de datos fuera de una migración de Alembic.
- No escribir consultas a la base que omitan el filtro por caso (4.5). Ningún módulo fuera de `repositorios/` ejecuta consultas.
- No enviar al proveedor del modelo el .docx completo ni datos que no sean solicitud, alcance y fragmentos (RNF-10).
- No permitir que un modelo de lenguaje escriba referencias bibliográficas (RN-17).
- No usar datos reales de participantes en desarrollo; solo datos ficticios.
- No usar guiones largos en textos visibles para el usuario.

## Convenciones (hoja de ruta, apartado 4)

- **Python 3.12**, FastAPI, Pydantic 2, SQLAlchemy 2 (psycopg 3), Alembic. Tipado completo; Ruff; mypy estricto para `app/`.
- **Idioma:** código, tablas y rutas en español sin tildes; mensajes al usuario en español.
- **Esquemas:** todo dato que cruza una frontera (API, cola, agentes, servicios externos) tiene un modelo Pydantic.
- **Configuración:** solo variables de entorno validadas al arrancar (`app/configuracion/`). Los parámetros funcionales viven en la tabla `configuracion`, no en el entorno. Claves solo en `.env` (excluido de Git).
- **Errores:** formato único `{codigo, mensaje, detalle?, incidencia_id}` (4.4).
- **Registro:** JSON estructurado; nunca texto del borrador, de las propuestas ni contraseñas (4.6).
- **Pruebas primero** (4.7). CI con proveedor de modelo simulado; las pruebas con modelo real llevan `@pytest.mark.modelo_real` y solo se ejecutan bajo demanda. Cobertura mínima 70 %.
- **Git:** ramas cortas `tNN-descripcion-corta`; mensajes en español, imperativo, con el identificador de la fase (por ejemplo `T03: agregar ruta de salud`).
- **Definición de terminado:** apartado 4.9. Plantilla de solicitud de cambio en `.github/pull_request_template.md`.

## Comandos

Todo se ejecuta en contenedor con Python 3.12 (igual que la integración continua). Requiere `.env` (copiar de `.env.example`).

```bash
docker compose up -d --wait bd api      # base con pgvector y API en http://127.0.0.1:8000
docker compose run --rm --build pruebas # suite completa con base real y cobertura
docker compose down                     # detener (añadir -v para borrar el volumen)
docker compose run --rm --no-deps api python -m app.seguridad.crear_investigador INV-01
docker compose run --rm --no-deps api python -m app.bd.semillas   # datos ficticios de desarrollo
```

Esquema de datos: solo por migración de Alembic (`backend/migraciones/`). Tras cambiar un modelo, regenere `docs/diccionario-de-datos.md` con `python -m app.bd.diccionario`. Toda ruta nueva se añade a `backend/pruebas/matriz_autorizacion.py`; todo acceso a datos pasa por `app/repositorios/` con `ContextoAcceso` (`app/seguridad/dependencias.py` lo construye desde la sesión).

Desarrollo local sin contenedor para análisis rápido (desde `backend/`, con entorno virtual):

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
pytest                                  # las pruebas de integración se omiten sin URL_BD_PRUEBAS
python -m app.diagnostico               # prueba las claves de Groq y OpenAlex (necesita las variables cargadas)
```

Servicios compartidos (T08): GROBID y `servicio_modelos/` (bge-m3 y bge-reranker-v2-m3 en CPU) van en `compartido/docker-compose.yml`, proyecto `sma_compartido`, una sola vez por servidor. `servicio_modelos/` es un paquete aparte (`servicio/`), con su propio `pyproject.toml`, pruebas y trabajo de CI. Revisiones de los modelos fijadas en `servicio/catalogo.py`; versiones de inferencia en `restricciones.txt`. En `app/`, solo se usan las interfaces de `app/inferencia/interfaces.py`.

```bash
docker compose -f compartido/docker-compose.yml --profile descarga run --rm --build descargar_modelos  # una vez, 4,6 GB
docker compose -f compartido/docker-compose.yml up -d --wait   # modelos en :8001, GROBID en :8070
docker compose -f compartido/docker-compose.yml --profile pruebas run --rm --build pruebas_modelos  # pesos reales
```

## Estructura

Ver `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`, apartado 4.1. Las carpetas se crean en la fase que las usa.
