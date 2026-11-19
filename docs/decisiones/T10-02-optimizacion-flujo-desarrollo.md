# T10-02. Optimización del flujo de desarrollo del corpus

**Fase:** T10 (Fase 3), antes de cerrar la actividad 7. **Fecha:** 19 de noviembre de 2026. **Estado:** vigente.

**Origen:** pedido del equipo del 19 de noviembre de 2026. La ingesta del corpus provisional tardó más de 2 horas en el portátil de desarrollo (Ryzen 7, 16 GB compartidos con otras tareas; la máquina virtual de Docker tiene 6 procesadores y 7,76 GB) y se detuvo a mano. Restricción: **los modelos no cambian** (bge-m3 y bge-reranker-v2-m3, revisiones de `servicio_modelos/servicio/catalogo.py`), ni el modelo de diseño de página de Docling.

## 1. Medición

**Método:**
- 3 PDF reales del corpus provisional (89 páginas, 192 fragmentos), en `datos/medicion/tema-medicion/`.
- Proyecto de Compose aislado (`sma_medicion`), base vacía en cada corrida.
- Tiempo por etapa con `app/corpus/medicion.py`. Pico de memoria del proceso por etapa (VmHWM, que se reinicia al empezar cada etapa).
- Memoria de cada contenedor con `docker stats` cada medio segundo.

**Antes:**

| Etapa | Tiempo | Proporción |
| --- | ---: | ---: |
| Embeddings (servicio de modelos, 3 hilos) | 385 s | 65 % |
| Extracción con Docling | 143 s | 24 % |
| Validación (pypdf) | 21 s | 4 % |
| Cabecera (GROBID) | 19 s | 3 % |
| Segmentación | 2 s | 0 % |
| Escritura en la base | 1 s | 0 % |
| **Total de la ingesta** (incluye la carga de Docling) | **589 s** | |

Picos de memoria por contenedor: GROBID 3,48 GB, servicio de modelos 1,99 GB y proceso de ingesta 3,37 GB. La suma (8,8 GB) supera los 7,76 GB de la máquina virtual: el sistema anfitrión pagina, y eso explica buena parte de las más de 2 horas.

**Después:** apartado 9.

## 2. Docling en modo liviano

Ya estaba sin OCR, sin estructura de tablas y sin enriquecimientos (decisión T09-01, apartado 2): el corpus científico solo admite PDF con capa de texto, y un escaneado se excluye. Lo que quedaba por ajustar era el lector del PDF y el tamaño de las colas. Se compararon variantes con los mismos 3 PDF, comparando el texto de cada fragmento con el de la configuración vigente:

| Variante | Tiempo | Pico | Resultado frente a la vigente |
| --- | ---: | ---: | --- |
| Vigente (lote 4, cola 100) | 138,5 s | 3,58 GB | referencia |
| Lote 2, cola 8 | 128,6 s | 2,91 GB | idéntico |
| **Lote 1, cola 4 (elegida)** | **131,7 s** | **2,64 GB** | **idéntico** |
| 2 hilos | 155,3 s | | idéntico, más lento |
| Lector pypdfium2 | 130,9 s | 2,16 GB | 40 % de fragmentos idénticos y 16,8 % más palabras |

**Decisión:** lote de 1 página y cola de 4 páginas (`OpcionesDocling` en `extractor_docling.py`), con el lector `docling_parse`. Ahorra 0,9 GB de pico sin cambiar una sola palabra extraída.

**pypdfium2 se descarta:** era el más liviano, pero duplicaba texto. En un PDF dio 14 298 palabras cuando pypdf cuenta 9 712. Con eso se pierde calidad, que es la condición del pedido.

Los hilos de Docling se fijan con `HILOS_DOCLING` (por defecto 4).

## 3. Caché de la extracción

`app/corpus/cache_extraccion.py` guarda el `DocumentoExtraido` de Docling comprimido, con una clave de dos partes:
- la huella SHA-256 del PDF;
- la firma del extractor: versión de Docling, revisión del modelo de diseño de página y lector del PDF. Si cambia alguna, la entrada anterior no se usa.

Vive en `DIRECTORIO_ARCHIVOS/extraccion/`, junto a los PDF, porque contiene su texto; nunca se sirve. Una entrada dañada se ignora y se vuelve a extraer.

**Re-segmentar sin releer los PDF:** `python -m app.corpus.resegmentar --tema T --investigador I [--aplicar]`.
- Toma los bloques de la caché (o extrae una vez y los guarda) y aplica la limpieza, las secciones y la segmentación vigentes.
- Sin `--aplicar` solo informa qué cambiaría.
- Con `--aplicar` reemplaza los fragmentos que cambian, conserva el vector de los que mantienen su texto y embebe solo los nuevos. Si el modelo de embeddings cambió de revisión, embebe todo (no se mezclan vectores).
- No toca documentos retirados ni los que ya alimentaron solicitudes (sus fragmentos son trazas, 18.9), y no deja dos documentos con el mismo texto en una colección.
- Sirve para la corrección de referencias de la decisión T09-01, apartado 10, y para la calibración de la ventana (T34).

## 4. Validación por muestra de páginas

La comprobación de capa de texto leía todas las páginas con pypdf: 19 s en un PDF de 52 páginas. Ahora lee todas si son 12 o menos y, si son más, 12 repartidas de forma uniforme (`paginas_de_muestra` en `validacion.py`). Un PDF escaneado no tiene texto en ninguna página, así que la muestra lo detecta igual. Un PDF con algunas páginas escaneadas tampoco se excluía antes, porque el criterio es el promedio.

## 5. Ingesta reanudable con avance

- Cada documento se confirma por separado, y un archivo ya indexado o ya excluido no se procesa otra vez (ya era así en T10). Ctrl+C revierte el documento en curso, informa cuántos quedaron y se continúa con el mismo comando.
- Cada línea muestra la posición, el porcentaje, el tiempo transcurrido, la estimación del restante y el tiempo de cada etapa. Al final, el tiempo y el pico de memoria por etapa. Nunca se imprime texto de los documentos.

## 6. Memoria dentro de 8 GB

| Componente | Cambio | Efecto medido |
| --- | --- | --- |
| Servicio de modelos | El reordenador se carga al primer `/reordenar` (`REORDENADOR_PEREZOSO=true`). La ingesta solo embebe. | 0,66 GB en reposo y pico de 1,52 GB al embeber, en lugar de 1,99 GB |
| Servicio de modelos | PyTorch usa todos los procesadores del contenedor (`HILOS_INFERENCIA=0`); por su cuenta tomaba solo los núcleos físicos (3 de 6). | Embeddings de 0,50 a 0,60 fragmentos por segundo en la ingesta (0,51 a 0,67 medido aparte), con vectores idénticos bit a bit |
| Servicio de modelos | Sin cambio: lote de 16 textos y 1 inferencia a la vez. | |
| GROBID | `modelPreload: false` y `concurrency: 2` (`compartido/grobid/grobid.yaml`). | 0,32 GB en reposo en lugar de 3,1 GB. Al usar la cabecera sube a unos 3,4 GB: sus modelos son nativos y `-Xmx` no los acota. |
| Docling | Lote 1 y cola 4 (apartado 2). Un PDF a la vez por proceso (ya era así). | Proceso de ingesta con pico de 2,29 GB en lugar de 3,37 GB |

**Presupuesto durante la ingesta (picos medidos, apartado 9):** GROBID 3,42 + modelos 1,52 + ingesta 2,29 + bases y API 0,2, unos 7,4 GB. Es la suma de los picos, que no coinciden en el tiempo: Docling, GROBID y los embeddings se ejecutan uno tras otro. Queda bajo 8 GB, con poco margen:
- no se ingiere en dos procesos a la vez, ni se sube un PDF por la API mientras corre una ingesta;
- tamaños de lote y concurrencia: 1 PDF a la vez, 16 textos por pasada de embeddings, 1 inferencia simultánea y 2 solicitudes simultáneas en GROBID;
- si hiciera falta más margen, se reinicia GROBID después de la ingesta (vuelve a 0,32 GB).

## 7. Subconjunto de desarrollo y ejecuciones programadas

- `scripts/crear_subconjunto_desarrollo.py` copia 3 PDF por tema a `datos/corpus-desarrollo/<tema>/`. Regla fija: PDF de 10 a 16 páginas que la ingesta completa indexó sin problemas, de menos a más páginas. Es el corpus de las pruebas diarias.
- El corpus completo se ingiere solo en ejecuciones programadas con `scripts/ingesta-programada.ps1`. Registra la ingesta en `datos/corpus-provisional/ingesta-AAAAMMDD-HHMM.log` y, si no hubo errores, respalda la base. La tarea programada no se registra sola: el guion explica cómo hacerlo y lo decide el equipo.

## 8. Respaldo y restauración

`scripts/respaldo_corpus.py` solo usa Docker:
- `respaldar [--nombre]`: `pg_dump` de la base, el volumen de archivos (PDF y caché de extracción) y un manifiesto con la revisión de Alembic, los documentos y fragmentos por colección y la huella de cada archivo, en `datos/respaldos/` (fuera de Git).
- `restaurar RUTA --confirmar`: comprueba las huellas, detiene la API, restaura la base y el volumen y vuelve a levantar la API.

## 9. Resultado

Misma medición del apartado 1, el 19 de noviembre de 2026, con los mismos 3 PDF y la base vacía:

| Etapa | Antes | Después | Cambio |
| --- | ---: | ---: | --- |
| Validación | 21 s | 7 s | muestra de 12 páginas |
| Extracción con Docling | 143 s | 137 s | mismo texto extraído |
| Segmentación | 2 s | 2 s | |
| Cabecera (GROBID) | 19 s | 42 s | carga del modelo al primer uso: 37 s en el primer PDF, luego 2 s |
| Embeddings | 385 s | 321 s | todos los procesadores |
| Escritura en la base | 1 s | 1 s | |
| **Total de la ingesta** | **589 s** | **524 s** | **11 % menos** |

| Pico de memoria | Antes | Después |
| --- | ---: | ---: |
| GROBID | 3,48 GB | 3,42 GB (0,32 GB en reposo, antes 3,1 GB) |
| Servicio de modelos | 1,99 GB | 1,52 GB |
| Proceso de ingesta | 3,37 GB | 2,29 GB |
| **Suma** | **8,9 GB** | **7,4 GB** |

**Re-segmentar los 3 PDF desde la caché:** 12 s en total, con 3 aciertos y ninguna extracción (antes, volver a procesar exigía repetir los 137 s de Docling).

**Respaldo y restauración**, probados en el proyecto aislado: tras borrar los 192 fragmentos y la caché, la restauración devolvió 3 documentos, 192 fragmentos con vector, los 3 PDF y las 3 entradas de caché. Después, la re-segmentación tuvo 3 aciertos.

**Lectura:**
- El tiempo de cómputo baja poco, un 11 %, porque lo dominan los embeddings y los modelos no cambian. La mejora principal es de memoria: la suma de picos baja de 8,9 GB, por encima de los 7,76 GB de la máquina virtual, a 7,4 GB. Con la suma por encima de la memoria disponible, el sistema paginaba, y eso explica la mayor parte de las más de 2 horas.
- En el día a día, lo que más ahorra no es cómputo, sino no repetirlo:
  - el subconjunto de 6 PDF se ingiere en minutos;
  - la caché evita Docling al volver a segmentar;
  - el respaldo evita volver a ingerir.
- **Proyección para el corpus completo** (107 PDF, unas 2 500 páginas y unos 2 850 fragmentos), con las velocidades medidas: Docling a 1,54 s por página (1,1 h) y embeddings a 0,60 fragmentos por segundo (1,3 h), más GROBID y la validación, unas 2,5 horas sin paginación. Es una estimación, no una medición. Por eso se deja para ejecuciones programadas.
