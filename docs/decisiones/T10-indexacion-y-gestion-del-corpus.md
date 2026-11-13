# T10-01. Indexación y gestión del corpus científico

**Fase:** T10 (Fase 3). **Fecha:** 12 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T10. Especificación de la Fase 1: RF-15, CU-14, CP-21, RN-11, RN-14, RN-19, apartados 18.2 a 18.10 y n.° 13. Decisiones del equipo del 12 de noviembre de 2026 (apartados 1 y 3).

## 1. Alcance y lo que queda pendiente

T10 lleva el `DocumentoProcesado` de T09 a la base, con vectores y texto léxico, y da al investigador las herramientas para administrar el corpus:
- rutas para subir, listar, confirmar y retirar documentos;
- un comando de ingesta en lote;
- un comando de reindexación.

**Actividad 7 (ingerir el corpus provisional):** queda pendiente. El corpus provisional no existe todavía en el carril de insumos (hoja de ruta, apartado 1, y riesgo R-08). El equipo decidió el 12 de noviembre de 2026 que lo entregará después. Todo T10 se implementa y prueba con los PDF ficticios de muestra. Cuando llegue el corpus, se ingiere con el comando del apartado 7.

## 2. Solo colecciones científicas

Las rutas y el comando indexan únicamente en la colección científica de un tema:
- **Guías:** se segmentan por apartado y no por IMRaD (T22). Con el canal de T09 todas quedarían "incompletas".
- **Colecciones personales:** reciben los aportes de cada caso (T32).

En consecuencia, en T10 ninguna vía indexa en el corpus de guías y la rúbrica no puede entrar en él (RN-11). La regla se vuelve a revisar en T22.

## 3. Modelo de datos (migración 0009)

- **Índices de `fragmento`** (18.2):
  - HNSW con `vector_cosine_ops` sobre `embedding`;
  - GIN sobre `texto_lexico`;
  - compuesto `(coleccion_id, documento_id)` para el filtro obligatorio por colección.
- **Tabla nueva `exclusion_corpus`:** registra con su motivo cada archivo o referencia que no entró al corpus (RF-15, CP-21, 18.3 y 18.9). El equipo eligió una tabla de detalle y no solo los contadores de `coleccion`.
  - Guarda la colección, el objeto (archivo o referencia), el identificador (nombre del archivo, DOI o referencia), la huella del archivo, el motivo, el documento del que es duplicado, quién la registró y cuándo.
  - Un mismo archivo se registra una sola vez por colección (índice único parcial).
  - T15 la reutiliza para las referencias sin acceso abierto (motivo `sin_acceso_abierto`, ya previsto).
- **Columnas nuevas de `documento`:**
  - `huella_archivo`, para la idempotencia;
  - `archivo_original`, el nombre con que se subió, para el investigador;
  - `indexado_por_id`, porque la Fase 1 (19.1) pide registrar quién y cuándo indexó;
  - `confirmado_en` y `confirmado_por_id`, para los incompletos (18.3);
  - `modelo_embeddings` y `revision_embeddings` (18.5, RNF-21).

## 4. Estados y recuperabilidad

| Estado | Vectores | ¿Se recupera? | Cuenta en `n_incluidas` |
| --- | --- | --- | --- |
| `activo` | Sí | Sí | Sí |
| `incompleto` sin confirmar | No | No | No |
| `incompleto` confirmado | Sí | Sí, con su marca visible (18.3) | Sí |
| `retirado` | Se conservan | No | No |

- **Confirmar un incompleto** embebe sus fragmentos y registra quién lo confirmó y cuándo. El estado sigue siendo `incompleto` y el motivo se conserva, para que la interfaz pueda mostrar el aviso al estudiante.
- **Retirar un documento** conserva sus fragmentos para la trazabilidad de solicitudes pasadas (18.9).
- **Contadores de `coleccion`:** se recalculan desde las tablas en cada cambio. `n_incluidas` cuenta los documentos recuperables y `n_excluidas` las exclusiones.
- **Pendientes de PDF:** `n_pendientes` es de T15.

## 5. Idempotencia y duplicados

- **Mismo archivo:** la huella SHA-256 del archivo se calcula antes de procesar. Si el mismo archivo ya está en la colección, como documento (en cualquier estado, también retirado) o como exclusión, no se procesa ni se registra otra vez; el resultado es `ya_registrado`. Por eso el comando de ingesta puede repetirse sobre la misma carpeta.
- **Mismo texto o mismo DOI que un documento de la colección:** si el archivo es otro pero coincide el texto normalizado o el DOI, se registra una exclusión `duplicado` que apunta al original (18.9, CP-21).
- **Alcance de los duplicados:** se buscan dentro de la colección. El mismo artículo puede estar en dos temas.

## 6. Archivos

- El PDF se guarda en `DIRECTORIO_ARCHIVOS/corpus/` con un nombre aleatorio, fuera de toda carpeta pública. La base guarda solo la ruta relativa.
- Ninguna ruta de la API devuelve el PDF: el sistema no redistribuye los archivos (18.10, n.° 13).
- El PDF se conserva para volver a segmentar si T34 cambia la ventana, sin pedir otra vez los archivos.
- El cifrado en reposo y el respaldo del volumen son de T21 y T42.

## 7. Vías de ingesta

- **Ruta `POST /investigador/colecciones/{id}/documentos`** (multipart):
  - Procesa el PDF en la misma petición, en unos segundos.
  - Procesa un PDF a la vez por proceso, porque Docling ocupa más de 1 GB al convertir.
  - Lee el archivo en partes. Si supera `tamano_max_pdf_mb`, responde 413 sin procesarlo ni registrarlo.
  - Responde 201 si guardó el documento (indexado o incompleto) y 200 si lo excluyó, era duplicado o ya estaba registrado. El motivo va en la respuesta.
- **Comando `python -m app.corpus.ingesta CARPETA --tema T --investigador INV`:**
  - Procesa los `*.pdf` de la carpeta en orden alfabético.
  - Informa una línea por archivo, sin texto de los documentos, y un resumen.
  - Un error transitorio (GROBID o el servicio de modelos caídos) no deja nada a medias; el archivo se reintenta en la próxima pasada.
- **Parámetros:** los del canal (ventana, solapamiento, umbral y límites) se leen de la configuración vigente en cada ingesta. El canal se carga una sola vez y se le aplican esos parámetros (`CanalPdf.con_parametros`).
- **Indexador de la API:** se crea al primer uso. Si faltan `URL_GROBID`, `URL_SERVICIO_MODELOS`, `DIRECTORIO_RECURSOS_CORPUS` o `DIRECTORIO_ARCHIVOS`, la ingesta responde 503 `corpus_no_configurado` con los nombres; el resto de la API sigue funcionando.
- **Conexión con los servicios compartidos:** la API llega a la red `sma_compartido` con `docker-compose.corpus.yml`. Es un archivo aparte para que `docker compose up` no exija los servicios compartidos.

## 8. Consultas de prueba y reindexación

- **Consultas de prueba** (`RepositorioCorpus.buscar_denso` y `buscar_lexico`): sirven al criterio de T10.
  - Consultan una colección indicada por el investigador, solo documentos recuperables, con distancia coseno (HNSW) o `plainto_tsquery('simple', …)` (GIN).
  - No son la recuperación de T16, que recibirá el contexto del caso y el tipo de solicitud (RN-03).
- **Comando `python -m app.corpus.reindexar --investigador INV [--forzar]`:**
  - Vuelve a embeber los documentos recuperables cuyos vectores son de otro modelo o revisión.
  - Confirma documento por documento, así que puede reanudarse.

## 9. Contexto de los comandos de consola

Los comandos se ejecutan en el servidor, por quien lo administra, como `crear_investigador`. El contexto de acceso se construye desde una cuenta A2 existente (`app/seguridad/consola.py`), que queda registrada como autora; nunca desde datos de una petición web.

## 10. Riesgos

- **Memoria y duración:** al subir el primer PDF, la API carga Docling (pico de 1,1 GB) y cada subida tarda segundos. Si en la instancia la memoria no alcanza, la ingesta puede quedar solo en el comando, con el servicio de modelos levantado durante la carga.
- **Duplicados sin DOI:** dos versiones del mismo artículo con textos algo distintos (preimpresión y versión publicada) y sin DOI no se detectan como duplicados. El investigador puede retirar una.
