# T09-01. Canal de extracción y segmentación de PDF

**Fase:** T09 (Fase 3). **Fecha:** 8 de noviembre de 2026. **Estado:** vigente, salvo el apartado 3.2, que queda propuesto hasta que el equipo lo confirme.

**Origen:** hoja de ruta, T09; especificación de la Fase 1, 18.2 a 18.4; RN-16 y RN-23; línea base D-01 (Docling y GROBID).

## 1. Contexto

T09 convierte un PDF de artículo en fragmentos IMRaD limpios con metadatos, sin indexar. El canal es `procesar_pdf(ruta) -> DocumentoProcesado` (`app/corpus/extraccion.py`), sin acceso a la base. Una prueba de arquitectura lo comprueba.

Pasos del canal:

1. Validación del archivo.
2. Docling.
3. Limpieza.
4. Secciones.
5. Segmentación.
6. GROBID.
7. Regla de incompleto.

Las decisiones se tomaron después de procesar con Docling y GROBID reales los PDF ficticios de muestra (`backend/pruebas/datos/pdf/`). Cada regla de limpieza responde a algo que se observó en esa salida.

## 2. Docling

| Aspecto | Decisión |
| --- | --- |
| Paquete | `docling-slim[format-pdf,models-local,convert-core]==2.149.0`, no `docling`. El paquete completo trae OCR (RapidOCR, OpenCV) y formatos de oficina que el canal no usa |
| Modelo | `docling-project/docling-layout-heron`, revisión `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`, Apache 2.0, 172 MB. Detecta títulos, párrafos, encabezados y pies de página y el orden de lectura |
| Lo que no se usa | OCR, estructura de tablas y enriquecimientos (imágenes, fórmulas, código, gráficos). Un PDF escaneado se excluye del corpus científico (18.3); el OCR de guías escaneadas, si hiciera falta, corresponde a T22 |
| Sin red | `artifacts_path` apunta a la carpeta de recursos y la imagen fija `HF_HUB_OFFLINE=1` y `DOCLING_SECURITY_REFUSE_UNPINNED_REMOTE_CODE=1` |
| Dependencia | Extra opcional `corpus` de `backend/pyproject.toml`. El árbol completo (API más extra) se fija en `backend/restricciones-corpus.txt`, con PyTorch 2.14.1 para CPU desde el índice de PyTorch. Ocupa 1,6 GB instalado. La imagen de la API y la de pruebas lo instalan; los trabajos de análisis, tipado y pruebas de la CI no, y un trabajo nuevo, `corpus`, prueba el canal con Docling real |
| Importación | Docling y `tokenizers` se importan al crear el extractor o el contador. mypy los ignora porque el trabajo de tipado no los instala |

**Recursos fijados** (`app/corpus/recursos.py`): el modelo de diseño de página y el `tokenizer.json` de bge-m3, este último con la misma revisión y huella que el servicio de modelos (T08).

`python -m app.corpus.recursos <carpeta>` hace lo siguiente:
- Los descarga de `huggingface.co/<repo>/resolve/<revisión>/`.
- Verifica el tamaño y el SHA-256.
- No repite lo que ya está bien.

El canal se niega a arrancar si falta algo o una huella no coincide.

**Medición** (amd64, 4 hilos, PDF de muestra):

| Medida | Valor |
| --- | --- |
| Primera conversión, con carga del modelo | 7,6 s |
| Artículo de 2 páginas | 2,1 s |
| Pico de memoria del proceso | 1,1 GB |

La ingesta es fuera de línea (18.5), pero la memoria se suma a la de los servicios compartidos de T08 cuando corre en la instancia. Ver el apartado 9.

## 3. Validación del archivo (RN-16)

### 3.1. Orden de las comprobaciones

`app/corpus/validacion.py`, con pypdf 7 (BSD, ya elegido como respaldo en la especificación), sin ejecutar nada del documento (RN-23):

1. Tamaño (25 MB), antes de leer el archivo.
2. Tipo real: la firma `%PDF-` en el primer kilobyte, no la extensión.
3. Que se pueda abrir; si no, `pdf_ilegible`.
4. Cifrado (apartado 3.2).
5. Páginas (60).
6. Capa de texto: si menos de la mitad de las páginas tiene al menos 40 caracteres extraíbles, el PDF se considera escaneado y se excluye con `sin_capa_de_texto` (actividad 8).

Los límites salen de la configuración versionada (`tamano_max_pdf_mb`, `paginas_max_pdf`).

### 3.2. PDF cifrados (propuesta para confirmar)

RN-16 dice que se rechazan los archivos cifrados. Muchos PDF de editoriales están "cifrados" solo para restringir permisos (imprimir, copiar) y se abren sin contraseña.

**Propuesta:** se rechaza (`pdf_cifrado`) el PDF que exige contraseña de apertura y se admite el que solo restringe permisos, que pypdf abre con contraseña vacía. Rechazar también estos excluiría artículos de acceso abierto legítimos. Los dos casos tienen un PDF de muestra (`cifrado.pdf` y `solo_permisos.pdf`). Si el equipo prefiere la lectura estricta, el cambio es una línea en `validacion.py` y su prueba.

## 4. Limpieza y secciones

### 4.1. Limpieza (`limpieza.py`)

- **Normalización Unicode:** NFC; ligaduras tipográficas a letras; guiones Unicode a `-`; espacios especiales a espacio; se quitan los caracteres invisibles y de control. Se eligió NFC y no NFKC para no convertir `m²` en `m2`.
- **Mobiliario de página:** se quitan los bloques que Docling marca como encabezado o pie y también todo texto igual (con los números reemplazados) a uno de ellos o repetido en al menos la mitad de las páginas (mínimo 3). Docling marcó el encabezado de la revista como mobiliario en las páginas 1 y 3, y como título de sección en la 2.
- **Mobiliario dentro de un párrafo:** ese mismo texto, con cualquier número de página, se quita también de dentro de los párrafos. Al unir un párrafo que continúa en la página siguiente, Docling le pegó al final el encabezado de esa página ("…ansiedad inicial Revista Ficticia…, 4(2), 2026…").
- **Títulos dentro de un párrafo:** se separan como título cuando cumplen todas estas condiciones:
  - van al comienzo del bloque o después de un fin de oración, con numeración opcional;
  - son un título completo reconocido (por ejemplo, "Análisis de datos" o "Resultados y discusión");
  - tienen hasta 4 palabras, la primera con mayúscula y las demás en minúscula;
  - no terminan en una palabra funcional;
  - les sigue una mayúscula o el final del bloque.

  Caso real: al alargar el artículo de muestra, el modelo de diseño de página tomó casi dos páginas enteras como un solo párrafo, con "2.2. Instrumentos", "3. Resultados", "Agradecimientos" y "Referencias" dentro. Sin esta regla, las referencias habrían llegado a los fragmentos. También cubre el "Resumen" que Docling une a su párrafo. Las pruebas cubren los casos que no deben separarse: "Resultados de la Encuesta…", "Results showed…", "Palabras clave: …".
- **Números de página sueltos y bloques sin letras:** se quitan. Docling entregó como párrafos las celdas numéricas de una tabla que no reconoció.
- **Párrafos partidos:** un bloque que no termina en puntuación y otro del mismo tipo que empieza en minúscula se unen; si el primero termina en guion, sin espacio. Docling partió un párrafo en una pieza por línea al pie de la página 1 ("…de la interv-" / "ención. …").
- **Título en minúscula:** un "título" que empieza en minúscula es la cola de un párrafo y vuelve a ser texto. Docling tomó por título la última línea de un párrafo que pasaba a la otra columna.
- **Guion de corte con espacio** ("investi- gación"): se une si la segunda parte empieza en minúscula y no es una conjunción ("pre- y postest" queda igual). Docling ya une casi todos los cortes; esto cubre los que deja.
- **Tablas, fórmulas y entradas de bibliografía:** se descartan. Las de bibliografía son las que Docling etiqueta `reference`, aunque falte el título "Referencias".

### 4.2. Secciones (`secciones.py`)

- **Títulos reconocidos:** un título reconocido abre su sección. Se reconoce en español y en inglés por su comienzo, sin numeración, tildes ni mayúsculas, con un sufijo corto ("Métodos", "Conclusions", "Acknowledgements"). Un título de más de 12 palabras no se reconoce. La lista está en el código y tiene una prueba por caso.
- **Equivalencias:** marco teórico, antecedentes y revisión de literatura cuentan como introducción. Participantes, instrumentos, procedimiento y análisis de datos cuentan como métodos. Limitaciones e implicaciones cuentan como discusión. Anexos, financiamiento, conflicto de intereses, contribuciones y disponibilidad de datos son "otra".
- **Títulos combinados:** cuenta la primera sección nombrada. "Resultados y discusión" es resultados; "Discusión y conclusiones" es discusión.
- **Títulos no reconocidos:** dentro del cuerpo (introducción a conclusiones) son subsecciones y heredan la sección. Fuera del cuerpo abren "otra". Un "Summary" dentro del cuerpo no es el resumen.
- **Preliminares:** lo anterior a la primera sección reconocida no se segmenta: título, autores, afiliaciones y la portada que añaden algunos repositorios. Son metadatos y los da GROBID. Si el documento no tiene ninguna sección reconocida, todo su texto es "otra".
- **Exclusiones:** las referencias y los agradecimientos se excluyen (18.3).
- **`seccion_original`:** guarda el título más cercano (por ejemplo, "2.1. Diseño y participantes"), que es lo que el estudiante busca en el PDF.

## 5. Segmentación (`segmentacion.py`)

- **Tokens:** la ventana se cuenta con el tokenizador de bge-m3, sin los tokens especiales, porque los fragmentos se embeben con ese modelo.
- **Tramos:** las subsecciones consecutivas de una misma sección normalizada forman un tramo. Las secciones no se mezclan ni se solapan.
- **Empaquetado:**
  - Un párrafo entero entra si cabe.
  - Si no cabe y el fragmento ya alcanzó el mínimo (300), se cierra en el borde del párrafo.
  - Si no lo alcanzó, se completa oración por oración hasta el máximo (450).
  - Una oración más larga que el máximo se parte por palabras.
- **Solapamiento:** cada fragmento empieza con la última oración del anterior (`solapamiento_oraciones`), salvo que esa oración no deje espacio para contenido nuevo (más de máximo menos mínimo). Las páginas del fragmento incluyen las de esa oración.
- **Fragmento final corto:** el último fragmento de un tramo puede quedar por debajo del mínimo. No se une al anterior: si el anterior se cerró, es porque lo siguiente no cabía. El primer diseño lo unía, y la prueba mostró que ese código nunca se ejecutaba.
- **Oraciones:** se dividen con una expresión regular para español e inglés que no corta abreviaturas (et al., Fig., p., aprox.), iniciales ni decimales.

## 6. GROBID (`grobid.py`)

- Se usa `processHeaderDocument` con `consolidateHeader=0`: GROBID no consulta servicios externos. La comprobación con Crossref y OpenAlex es de T14 y T15.
- Se extraen título, autores (nombres y apellidos por separado, para las normas de citación de T20), año de publicación, DOI normalizado, revista e idioma.
- Una caída o respuesta inválida de GROBID es un error 503 (`grobid_no_disponible`), no un estado del documento: es transitoria y la ingesta de T10 la informa y reintenta.
- Lo observado en las cabeceras grabadas: GROBID partió mal un nombre con dos apellidos (Rafael | Quispe | Huamán), no tomó el DOI del encabezado del artículo en inglés y no halló el año en ninguno. Los metadatos de GROBID son un punto de partida, no la referencia final.

## 7. Documento incompleto

- **Umbral:** `palabras_minimas_articulo` = 1 500 (18.3). Es un parámetro funcional, así que va en la configuración versionada: la migración 0008 lo agrega a la versión 1 con la misma salvaguarda que 0006 y 0007.
- **Palabras:** se cuentan en el texto que se segmenta, sin preliminares, referencias ni agradecimientos.
- **"Sin secciones IMRaD":** significa que no se reconoció introducción, métodos, resultados, discusión ni conclusiones. Un documento con solo el resumen es incompleto.
- **Fragmentos:** un incompleto conserva sus fragmentos con el estado y los motivos explícitos. Se indexa solo si el investigador lo confirma (T10).
- **Exclusiones:** un PDF que no pasa la validación, que Docling no puede convertir o del que no sale ninguna palabra se excluye con su motivo y sin fragmentos.

## 8. Huellas

`DocumentoProcesado` lleva dos huellas:
- `huella_archivo`, el SHA-256 del archivo.
- `huella_texto`, el SHA-256 del texto que se segmenta, en minúsculas y con espacios simples.

La segunda es la de 18.9 para deduplicar en T10. Como no incluye preliminares, una portada añadida por un repositorio no la cambia.

## 9. Riesgos y límites conocidos

- **Fallos del modelo de diseño de página:** cuando Docling toma una o más páginas como un solo párrafo, los títulos se recuperan con la regla del apartado 4.1, pero las páginas de los fragmentos de ese tramo son las del bloque entero (por ejemplo, 2 a 4 en lugar de 3). Un título no reconocible dentro de ese bloque (un subtítulo propio del artículo) queda en el texto. No se usan los `charspan` de Docling para afinar las páginas, porque no son exactos tras su propia unión de guiones.
- **Nombres propios tras un fin de oración:** una oración que empieza con un título reconocido seguido de un nombre propio ("Método Delphi…") se separaría como título si está justo después de un punto. No se observó en las muestras.
- **Memoria:** Docling suma un pico de 1,1 GB. Con los servicios de T08 (3,7 GB y 2,5 GB) y dos bases, la estimación para la instancia de 12 GB pasa de 9,5 GB a unos 10,6 GB mientras se ingiere. Hay que medirlo en la instancia y, si hace falta, ingerir con el servicio de modelos detenido (la ingesta no lo necesita hasta embeber).
- **Guiones de compuestos:** un compuesto partido justo en su guion al final de línea ("well-known") queda unido ("wellknown") si Docling dejó un espacio después del guion.
- **Referencias sin marca:** una lista de referencias sin título reconocible ni etiqueta `reference` de Docling se segmentaría como parte de la sección anterior. En los PDF de muestra Docling reconoció ambos títulos.
- **Tablas:** las tablas no reconocidas aportan filas cortas como párrafos.
- **Calibración:** la ventana (300 a 450 tokens) y el umbral de 1 500 palabras son los iniciales; T34 calibra la ventana con el conjunto de prueba.
