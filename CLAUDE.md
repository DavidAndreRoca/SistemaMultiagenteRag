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

Canal de PDF (T09): `app/corpus/` (`procesar_pdf` en `extraccion.py`, sin acceso a la base). Docling y el tokenizador van en el extra `corpus`, con el árbol fijado en `backend/restricciones-corpus.txt` (PyTorch en CPU). Sus recursos (modelo de diseño de página y tokenizador de bge-m3) tienen revisión y huella en `app/corpus/recursos.py`. Los PDF de muestra son ficticios y se regeneran con `python -m pruebas.datos.generar_pdf_muestra`.

```bash
docker compose --profile pruebas run --rm --no-deps pruebas python -m app.corpus.recursos /recursos  # una vez, 190 MB
```

Indexación (T10): `app/corpus/indexacion.py` (`Indexador`: ingerir, indexar, confirmar, retirar, reindexar), `app/repositorios/corpus.py` (A2, incluye las consultas de prueba densa y léxica), rutas en `app/api/corpus.py`, comandos `python -m app.corpus.ingesta` y `python -m app.corpus.reindexar`. Solo colecciones científicas (guías en T22, aportes en T32). La API llega a GROBID y al servicio de modelos con `-f docker-compose.yml -f docker-compose.corpus.yml`. En pruebas, `pruebas/dobles_corpus.py` sustituye el canal y los embeddings.

```bash
docker compose -f compartido/docker-compose.yml --profile descarga run --rm --build descargar_modelos  # una vez, 4,6 GB
docker compose -f compartido/docker-compose.yml up -d --wait   # modelos en :8001, GROBID en :8070
docker compose -f compartido/docker-compose.yml --profile pruebas run --rm --build pruebas_modelos  # pesos reales
```

Flujo de desarrollo del corpus (T10-02): la ingesta es reanudable (Ctrl+C y repetir el comando); la extracción de Docling queda en caché en `/archivos/extraccion/` (`app/corpus/cache_extraccion.py`) y `python -m app.corpus.resegmentar --tema T --investigador I [--aplicar]` vuelve a segmentar sin releer los PDF. Para el día a día, el subconjunto de `scripts/crear_subconjunto_desarrollo.py`; el corpus completo, con `scripts/ingesta-programada.ps1`. Respaldo: `python scripts/respaldo_corpus.py respaldar|restaurar`. Presupuesto de memoria de 8 GB en `docs/decisiones/T10-02-optimizacion-flujo-desarrollo.md`.

Borradores (T11): `app/borradores/` (`validacion.py` sin acceso a la base, `extraccion.py` con python-docx, `servicio.py`), rutas en `app/api/borradores.py`, versiones en `app/repositorios/caso.py` (`RepositorioVersiones`). Los .docx de muestra (válidos e inválidos, ficticios) se regeneran con `python -m pruebas.datos.generar_docx_muestra`. El nombre original del archivo no se guarda ni se registra.

Secciones y alcance (T12): `app/borradores/secciones.py` (detección por estilos, marcado manual, referencias, `estructura_borrador`) y `app/borradores/alcance.py` (`validar_alcance`, CP-09), sobre los párrafos guardados, sin volver a leer el .docx. Casos de prueba oficiales de la tesis en `docs/especificacion-fase1/casos-de-prueba-tesis.md`.

Interfaz (T13): `frontend/` (React 19, TypeScript estricto, Vite, React Aria Components, React Router). Herramientas en el contenedor `node:24.22.2-bookworm-slim` (Node del equipo demasiado antiguo); `node_modules` queda instalado para Linux. El cliente se genera del contrato: `python -m app.contrato` y luego `npm run generar:api`; una prueba del backend y la CI fallan si quedan desfasados. La interfaz llama a `/api/...` y Vite lo reenvía a la API (mismo origen). Extremo a extremo: `scripts/e2e.ps1` (proyecto `sma_e2e` aislado). En desarrollo: `docker compose --profile interfaz up -d interfaz`.

Servicios bibliográficos (T14): `app/bibliografia/` (Crossref, doi.org, Unpaywall y OpenAlex detrás de `interfaces.py`, con limitador, reintentos, caché en `cache_metadatos` y comparador). Toda falla da `no_comprobable`, nunca `no_encontrado` (RN-18). Las pruebas usan respuestas grabadas en `pruebas/contrato/respuestas/` (`python -m pruebas.contrato.grabar`, con `CORREO_POLITE` y `CLAVE_OPENALEX`), nunca la red.

Importador O1 (T15): `app/importacion/` (`extraccion.py` sin acceso a la base; `resolucion.py` con `Localizador`; `descarga.py`; `servicio.py` con `Importador` en segundo plano, que borra el artículo de `/archivos/importacion/<id>/` al extraer, RN-19), repositorio `app/repositorios/importacion.py`, rutas en `app/api/importacion.py`, pantalla `frontend/src/paginas/Importacion.tsx`. En pruebas, `pruebas/dobles_importacion.py` simula GROBID (TEI grabados en `pruebas/contrato/grobid/`), los servicios y las descargas a partir de `pruebas/datos/articulo_o1.py`.

Modelos de lenguaje (T17): `app/llm/` (`ModeloLenguaje` en `interfaces.py`, proveedores Groq, DeepSeek, Gemini y simulado en `proveedores.py`, `CadenaModelos` con reintentos, respaldo y registro en `cadena.py`, `limitador.py`, `fabrica.crear_cadena`). Orden en `PROVEEDORES_MODELO` (validado al arrancar; en pruebas, `simulado`); modelos, límites y precios en la configuración (migración 0012). Instrucciones en `backend/instrucciones/<agente>/<version>.md`, cargadas con `app/instrucciones/cargador.py`; una versión publicada no se edita (`registro.json`, `python -m app.instrucciones registrar`). Ninguna prueba automática llama a un proveedor real: el contrato usa `pruebas/contrato/modelos/` (`python -m pruebas.contrato.grabar_modelos`).

Recuperación (T16): `app/rag/` (`fusion.py` con RRF y presupuesto de contexto, `recuperacion.Recuperador`, `suficiencia.decidir` en dos pasos, `servicio.ServicioEvidencia` con `preparar` y `atender`, que solo genera con evidencia suficiente y registra `fragmento_recuperado`, eventos y la abstención). Consultas por tipo y contexto en `app/repositorios/recuperacion.py`, nunca por colección. Instrucción `instrucciones/suficiencia/v1.md`. Línea base con `python -m app.rag.evaluar` sobre `evaluacion/conjuntos/` (transacción revertida, no escribe en la base). En pruebas, `pruebas/dobles_rag.py` (reordenador por coincidencia de palabras).

Contrato de agentes (T18): `app/agentes/contrato.py` (`EstadoAgente` sin historial; `Agente.atender` recupera, decide suficiencia y genera con el esquema del tipo de `app/agentes/esquemas.py`, que no tiene campos de referencias). Comprobaciones 1 (esquema) y 3 (citas a `fragmento_recuperado`) en `app/verificacion/comprobaciones.py`. Referencias en `app/bibliografia/referencias.py` (doi.org con DOI; si no, `csl.py` con `citeproc-py` y los estilos de `app/bibliografia/estilos/`, con huella fijada). En pruebas, el escenario compartido de T16 y T18 está en `pruebas/integracion/escenario_rag.py`.

## Estructura

Ver `docs/HOJA-DE-RUTA-TECNICA-DESARROLLO.md`, apartado 4.1. Las carpetas se crean en la fase que las usa.
