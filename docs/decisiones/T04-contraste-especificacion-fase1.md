# T04-02. Contraste del modelo de datos con la especificación de la Fase 1

**Estado:** Vigente (6 de noviembre de 2026). Cierra los puntos provisionales de `T04-modelo-de-datos.md`.

**Fuentes:**
- `docs/especificacion-fase1/02_funcionalidades.md`, apartado 6.7 (salida de la verificación).
- `docs/especificacion-fase1/06_rag_seguridad.md`, apartados 18.2, 18.4, 18.6 y 18.9.
- `docs/especificacion-fase1/03_requisitos.md`, RF-02, RF-13, RF-25 y RN-18.
- `docs/insumos/insumos-modelo-de-datos-y-configuracion.md`: ficha de métricas, hitos, tabla de tipos y alcances, y valores iniciales.

**Migraciones:**
- `0005_contraste_especificacion_fase1`: esquema.
- `0006_configuracion_v1_y_hitos`: configuración versión 1 y normas en minúsculas.

Las migraciones 0001 a 0004 no se tocaron.

## 1. Diferencias encontradas y corrección

### 1.1. `verificacion` (6.7, campo "Salida")

La especificación pide, por intento, `formato_ok`, `limites_ok`, `citas_ok`, `n_fuentes_citadas`, `n_fuentes_confirmadas`, `metodo`, `acceso_abierto_ok`, `fidelidad` y `superada`.

| Tabla provisional de T04 | Especificación | Corrección |
| --- | --- | --- |
| `c1_esquema` (estado de 4 valores) | `formato_ok` | Booleano no nulo |
| `c2_limites` | `limites_ok` | Booleano; nulo si no aplica al tipo |
| `c3_citas` | `citas_ok` | Booleano; nulo si no aplica |
| `c4_existencia` (un solo estado) | `n_fuentes_citadas`, `n_fuentes_confirmadas`, `metodo` | Dos conteos y `metodo` (`doi`, `metadatos` o `mixto`) |
| `c5_acceso_abierto` | `acceso_abierto_ok` | Booleano; nulo si no aplica |
| `c6_fidelidad` (estado) | `fidelidad` (valor) | Se elimina el estado: la fidelidad ya se guardaba como valor y se compara con `umbral_fidelidad` |
| `aprobada` | `superada` | Se renombra |
| (no existía) | `advertencias` (salida del módulo, no por intento) | `resultado.advertencias` (JSONB) |

Se conservan, porque la especificación las necesita aunque no las nombre en la salida:
- `umbral_fidelidad`: el umbral se calibra y hay que saber cuál se aplicó.
- Los conteos de afirmaciones: 6.7 define fidelidad = respaldadas / total.
- `motivos_falla`: 6.1 los pasa al reintento.
- `modelo_evaluador`: RN-24.

Añadidos, con justificación (los dos primeros los aceptaron los autores el 6 de noviembre de 2026; ver `T04-fuentes-no-comprobables.md` y `T04-metodo-mixto.md`):
- **`n_fuentes_no_comprobables`.** RN-18 y la tabla 42 distinguen "no localizada" de "no comprobable" (servicio caído). Con solo dos conteos, una fuente no comprobable contaría para M6 como no verificable, y RN-18 lo prohíbe. La columna permite informarlas aparte.
- **Valor `mixto` en `metodo`.** Una verificación puede tener fuentes confirmadas por DOI y otras por metadatos. La especificación da un solo `metodo` por verificación, y `mixto` es la única forma de no perder la información.
- **Restricciones de coherencia** (segunda barrera, como en T04-01):
  - `superada` exige que ninguna comprobación aplicable haya fallado, que todas las fuentes estén confirmadas y que la fidelidad alcance el umbral.
  - Conteos no negativos, con confirmadas más no comprobables menor o igual que citadas.
  - `metodo` nulo si y solo si no hay confirmadas.
  - Intento 1 o 2.

### 1.2. `documento` (18.2)

| Provisional | 18.2 | Corrección |
| --- | --- | --- |
| `fuente` ("revista, libro o contenedor") | revista o editorial | Se renombra a `revista_editorial`. "Fuente" se confundía con `fuente_aportada` |
| (no existía) | ISBN | `isbn` sin guiones, con CHECK de ISBN-10 o ISBN-13. Se usa para libros (18.9) |
| (no existía) | ruta del archivo | `ruta_archivo`, nula si se indexó solo el resumen (RF-13 sin PDF) |
| Huella "del PDF" | huella SHA-256 del contenido; 18.9: "del texto normalizado" | Cambia la descripción: la huella es del texto normalizado, no del archivo |
| `creado_en` ("fecha de indexación") | fecha de indexación | Sin cambio |

Coinciden sin cambios: título, autores, año, DOI, idioma, licencia, estado OA y URL de acceso abierto, y estado (activo, retirado o incompleto).

Se conservan, porque las piden otros apartados:
- `motivo_estado`: 18.3, documento incompleto.
- `origen`: RF-13 y RF-20.
- `num_paginas`: RN-16.
- `retirado_en`: 18.9.

### 1.3. `fragmento` (18.2)

Las columnas coinciden: sección normalizada con los siete valores, título original, páginas, orden, texto, tokens y `vector(1024)`.

La diferencia está en el vector léxico. En T04 era una columna libre y nula, y nada garantizaba la configuración `simple`. Ahora es una **columna generada** `to_tsvector('simple', texto)`: siempre existe, no se puede escribir a mano y siempre usa `simple`. T10 ya no tiene que calcularla; solo crea el índice GIN.

### 1.4. `solicitud`: tipos y alcances (RF-02 y tabla 3 de los insumos)

| Provisional | Corrección |
| --- | --- |
| Tipos `estructura`, `plan_tarea`, `metodologico`, `redaccion`, `evidencia`, `referencias` | `revision_estructura`, `plan_tarea`, `revision_metodologica`, `propuesta_redaccion`, `busqueda_evidencia`, `verificacion_referencias` |
| Alcances `version`, `seccion`, `parrafo`, `consulta` | `seccion`, `hito`, `fragmento`, `consulta`, `version` (`parrafo` pasa a `fragmento`; se añade `hito`) |
| `alcance_contenido` (JSONB) | `alcance_ref` (texto): identificador de sección o párrafo, o texto de la consulta. Es nulo en `hito` y `version` |
| Sin relación entre tipo y alcance | CHECK `alcance_admitido_por_tipo` con la tabla 3 y CHECK `alcance_ref_segun_tipo` |

La tabla de alcances vive en `app/bd/enumeraciones.py` (`ALCANCES_ADMITIDOS`), y el CHECK del modelo se genera desde ella. La migración guarda una copia literal, y una prueba compara las restricciones de las migraciones con las que crean los modelos.

## 2. Juicios de evaluación (M2, M3 y M5)

Los insumos proponen una columna por juicio con su origen (`pertinente` y `pertinencia_fuente`, `relevancia` y `completitud`), o una tabla aparte. **Se eligió un par de columnas por juicio: una del evaluador y otra humana.** Los autores lo aceptaron el 6 de noviembre de 2026 (`T04-juicios-evaluador-y-humano.md`).

| Tabla | Columnas | Métrica |
| --- | --- | --- |
| `fragmento_recuperado` | `pertinencia_evaluador`, `pertinencia_humana` (booleanos) | M2 |
| `solicitud` | `completitud_evaluador`, `completitud_humana` (0 a 1) | M3 |
| `resultado` | `relevancia_evaluador`, `relevancia_humana` (0 a 1) | M5 |

Motivo: RF-25 pide "calcular concordancia" entre el modelo evaluador y la muestra humana del 20 al 30 %. Para eso se necesitan los dos juicios del mismo elemento, y una columna única con su origen perdería el del evaluador al cargar el humano. Con dos columnas se conservan ambos, se mantienen la clave foránea y el `caso_id` de cada tabla (aislamiento sin cambios) y no hace falta una tabla polimórfica.

Todas son nulas hasta que se evalúen. Se llenan en T38 y en el cálculo de O2, nunca durante la solicitud. Una CHECK limita los valores decimales a 0 a 1.

## 3. Columna "Alimenta" del diccionario

Se reescribió con los códigos M1 a M6 de la ficha (`app/bd/metricas.py`):
- Si una métrica usa todas las columnas de una tabla (`fragmento_recuperado.*` en M2 y M3, `resultado.*` en M5), la tabla lo declara y el diccionario lo repite en cada columna.
- El diccionario termina con el índice inverso de métrica a columnas, generado automáticamente.
- Una prueba comprueba que cada columna de la tabla 1 de los insumos declara su métrica.

Se corrigieron indicaciones de T04 que no coincidían con la ficha:
- `documento.estado` decía "cobertura": M1 se calcula por solicitud, no por documento.
- `verificacion.c3_citas` y `c4_existencia` decían "tasa de referencias no verificables": M6 usa los conteos de fuentes.
- Los conteos de `coleccion` decían "cobertura": son el informe del corpus por tema (RF-15).

Otros datos exportados: los contadores de decisiones (`decision.opcion` por `solicitud.tipo` y `decision.caso_id`) y el uso mínimo por hito (`solicitud` unida a `version_borrador.hito`).

## 4. Configuración versión 1 y catálogo de hitos

La migración 0006 **reemplaza los parámetros de la versión 1**, en lugar de crear una versión 2, como piden los insumos ("versión 1, provisional"). Se detiene si la versión 1 está congelada o si alguna solicitud ya la usa, para que ningún registro quede asociado a parámetros que no tuvo. Hoy no hay solicitudes.

Diferencias con la semilla de 0002:
- **Nombres planos de la tabla 4 de los insumos** (`k_denso`, `rrf_constante`, `n_reranking`, `suficiencia_n`, `suficiencia_tau`, `limite_reescritura_palabras`, `tamano_max_docx_mb` y los demás), en lugar de grupos anidados.
- **Valores nuevos:**
  - `rrf_constante` 60.
  - `suficiencia_n` 2.
  - `suficiencia_tau` 0.5 (provisional, sobre el puntaje del reranker normalizado con sigmoide).
  - `ventana_tokens` con objetivo de 400.
  - `uso_minimo_por_hito` 1.
- **Los ocho hitos** de la tabla 2 (`avance_1` a `entrega_final`), con orden, nombre y contenido. El esquema exige códigos únicos y en minúsculas, y un orden de 1 a n sin saltos.
- **`solapamiento_oraciones: 1`** se conserva aunque no esté en la tabla 4: lo fija 18.4 ("una oración de solapamiento").
- No hay modelos ni precios: llegan en T17.

Una prueba comprueba que la versión 1 de la base, validada, es igual a `parametros_iniciales()` del código.

## 5. Normas de citación en minúsculas

Los insumos usan `ieee` y `apa7`. La migración 0006 los convierte en tres lugares: la configuración, `caso.norma_citacion` (incluido el valor por defecto) y `cambio_norma`. El descenso los devuelve a mayúsculas.

La ruta de cambio de norma acepta mayúsculas y las normaliza (`APA7` pasa a `apa7`). D-12 sigue igual: la lista está pendiente de confirmación antes de T20.

## 6. Precondiciones de la migración 0005

La migración 0005 exige `solicitud` y `verificacion` vacías: los datos viejos (`alcance_contenido` en JSONB, estados c1 a c6) no tienen traducción exacta. Si hay filas, se detiene sin cambiar nada; una prueba lo comprueba. Ninguna fase escribe esas tablas antes de T16 y T19.

## 7. Fuera de alcance (no se adelanta)

- Índices HNSW, GIN y compuesto por colección: T10, como dice el comentario del modelo.
- Deduplicación por DOI dentro de una colección (18.9): se evalúa en T10 junto con `indexar()`. Hoy solo es única la huella.
- Confirmación del investigador para indexar un documento incompleto (18.3): T09 y T15.
- Instrucciones oficiales de cada hito para el plan de tarea (RF-05): llegan con el corpus de guías (T22).

## 8. Pendiente de confirmación

- `suficiencia_tau` = 0.5 sigue provisional; T34 la fija con la curva de precisión.
- ~~La lista de normas sigue pendiente en D-12.~~ Cerrada el 6 de noviembre de 2026: `ieee` (por defecto), `apa7` y `vancouver` (migración 0007, D-12).
