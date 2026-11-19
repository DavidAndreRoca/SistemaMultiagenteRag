# T11-01. Carga, validación y versiones del borrador

**Fase:** T11 (Fase 3). **Fecha:** 19 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T11. Especificación de la Fase 1: RF-01, F-04, RN-09, RN-16, RNF-01 y RNF-10; apartado 6 (validación de archivos). CP-01 y CP-02, según la tesis (Tabla 20, en `docs/especificacion-fase1/casos-de-prueba-tesis.md`):
- **CP-01:** un .docx de un caso registrado registra una versión nueva con fecha y hora, y las versiones anteriores se conservan.
- **CP-02:** un archivo de formato distinto de .docx o dañado se rechaza, se informa el motivo y no se registra ninguna versión.

Las macros, el cifrado y el contenido anómalo no son parte de CP-02: los rechaza RN-16, con las mismas garantías.

## 1. Alcance

T11 recibe el .docx, lo valida, lo guarda, extrae sus párrafos y registra la versión. No detecta secciones ni la lista de referencias: eso es T12, que trabaja sobre los párrafos guardados aquí. Tampoco hay pantalla de carga: la interfaz es de T13.

## 2. Validación (`app/borradores/validacion.py`)

Se valida sin abrir el documento con Word ni ejecutar nada de él. El orden va de lo más barato a lo más caro y se detiene en el primer problema:

| Paso | Comprobación | Motivo del rechazo |
| --- | --- | --- |
| 1 | Tamaño: 15 MB (`tamano_max_docx_mb`), mientras se recibe el archivo | `archivo_demasiado_grande` (413) |
| 2 | Extensión: `.docm` es macro; toda otra que no sea `.docx` no se admite | `docx_con_macros` o `formato_no_admitido` |
| 3 | Tipo MIME declarado por el navegador: el de .docx, `application/octet-stream` o vacío (los navegadores no son uniformes); otro, no | `formato_no_admitido` |
| 4 | Firma del contenedor: ZIP (`PK\x03\x04`). Un contenedor OLE (`D0 CF 11 E0`) con el flujo `EncryptionInfo` es un .docx cifrado (Word siempre cifra así); sin él, es un .doc antiguo | `docx_cifrado` o `formato_no_admitido` |
| 5 | Tamaño descomprimido declarado, antes de descomprimir: total hasta 150 MB (10 veces el límite), una parte de más de 1 MB no puede comprimirse más de 100 a 1, y hasta 2 000 partes | `contenido_anomalo` |
| 6 | Tipo MIME real: la parte principal en `[Content_Types].xml` debe ser la de un documento de Word; la de macros (`macroEnabled`) se rechaza | `formato_no_admitido` o `docx_con_macros` |
| 7 | Contenido ejecutable: `vbaProject.bin` o controles ActiveX | `docx_con_macros` |
| 8 | Integridad: el CRC de cada parte y la apertura con python-docx | `docx_danado` |
| 9 | Sin DTD (`<!DOCTYPE`) en las partes XML: Word nunca los escribe y son la vía de las bombas XML | `contenido_anomalo` |

**Por qué basta con los tamaños declarados (paso 5):** `zipfile` no descomprime más bytes de los que declara cada parte; si el contenido real difiere, falla el CRC (paso 8). Además, python-docx analiza el XML sin expandir entidades (`resolve_entities=False`).

**Límites de seguridad, no parámetros funcionales:** los del paso 5 son constantes del código. El de 15 MB sí está en la configuración versionada, porque lo fija RN-16.

**Contraseña de edición:** un .docx protegido solo contra la edición (`w:documentProtection`) no está cifrado: se abre y se admite.

**Evento de validación:** cada rechazo se registra en el registro JSON (`tipo_evento: "validacion_borrador"`) con el motivo, el caso y el tamaño. No se registran el nombre ni el texto del archivo (4.6).

Todos los rechazos responden con el formato único de error (4.4) y no crean versión ni guardan el archivo. Los rechazos del contenido responden 422 y el de tamaño, 413.

## 3. Almacenamiento

- El archivo se guarda en `DIRECTORIO_ARCHIVOS/borradores/` con un nombre aleatorio (UUID) y se registra su huella SHA-256. Ninguna ruta lo sirve, y nunca se envía al proveedor del modelo (RNF-10).
- **El nombre original no se guarda ni se registra:** suele llevar el nombre del estudiante, y el modelo de datos no admite datos personales.
- El almacén de archivos del corpus (T10) se generalizó a `app/comun/almacen.py`, con subcarpeta y extensión.

## 4. Versiones

- **Una versión por carga** (RN-09), aunque el archivo sea idéntico al anterior: lo que se registra es la carga.
- **Vigencia:** la nueva queda vigente en su hito, y la anterior vigente de ese hito deja de serlo sin borrarse. El índice único parcial de T04 garantiza una sola vigente por caso y hito.
- **Cargas simultáneas:** la fila del caso se bloquea (`SELECT ... FOR UPDATE`) mientras se registra la versión, así que dos cargas del mismo caso se ordenan en lugar de chocar.
- **Hito:** debe estar en el catálogo de la configuración vigente (`hito_desconocido`, 422 si no).
- **Primera versión de un hito:** la respuesta lo informa (`primera_del_hito` y un mensaje).

## 5. Extracción de párrafos (`app/borradores/extraccion.py`)

- **Recorrido:** el cuerpo en orden de lectura, con los párrafos y las celdas de las tablas (`origen`: `cuerpo` o `tabla`). Los párrafos vacíos se omiten.
- **Identificador:** `p1`, `p2`… dentro de la versión. Una versión no cambia, así que el identificador es estable. T12 los usa para secciones y alcances.
- **Estilo:** se guarda el nombre del estilo de cada párrafo, que T12 necesita para detectar títulos.
- **Texto:** todos los `w:t` del párrafo, incluidos los de hipervínculos, controles de contenido (`w:sdt`), inserciones con control de cambios y el resultado visible de los campos. Así quedan las citas de Zotero y Mendeley tal como se ven. No entran el texto eliminado con control de cambios (`w:delText`) ni el código de los campos (`w:instrText`).
- **Corregido en T12** (T12-01, apartado 2): la extracción recorre también los controles de contenido de bloque, donde Mendeley y Word ponen la bibliografía; conserva los saltos de línea y guarda el nivel de título de cada párrafo.
- **No se extraen:** encabezados y pies de página, notas al pie, comentarios ni cuadros de texto. No son parte del cuerpo del artículo. Las notas al pie se revisarán si T12 las necesita.
- **Almacenamiento:** en `version_borrador.parrafos` (JSONB, de carga diferida para que listar versiones no traiga el texto) y el total en `palabras` (migración 0010).

## 6. Rutas del caso (A1)

| Ruta | Qué hace |
| --- | --- |
| `POST /caso/versiones` | Formulario con `hito` y `archivo`. Responde 201 con la versión, `primera_del_hito` y mensajes |
| `GET /caso/versiones` | Versiones del propio caso, de la más reciente a la más antigua, con filtro opcional `?hito=`. Sin texto |
| `GET /caso/versiones/{id}` | Metadatos de una versión: hito, fecha y hora, tamaño, huella, vigencia, palabras y párrafos. Sin texto |

- **Aislamiento:** una versión de otro caso responde 404, igual que una inexistente. El repositorio filtra siempre por el caso de la sesión.
- **Sin descarga:** ninguna ruta devuelve el archivo ni el texto. *(Acotado por T12-01, apartado 8: el propio caso puede leer los párrafos de su versión para elegir el alcance.)* El texto se servirá como alcance de una solicitud (T12 y T13).

## 7. Riesgos y límites

- **python-docx no lee notas al pie** ni cuadros de texto: su texto no se extrae (apartado 5).
- **Un .doc antiguo** se rechaza como formato no admitido. El mensaje pide guardarlo como .docx.
- **Límites del paso 5:** se eligieron con margen para artículos con imágenes, que ya vienen comprimidas y no superan una proporción de 2 a 1. Si un borrador legítimo los supera, se ajustan aquí.
