# T12-01. Secciones del borrador, lista de referencias y alcance

**Fase:** T12 (Fase 3). **Fecha:** 19 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T12. Especificación de la Fase 1: RF-02 (F-05 y F-06), base de RF-09, herramientas de D1 y D2 (`estructura_borrador()`) e insumos de T04 (tabla 3, tipos y alcances). CP-09, según la tesis (`docs/especificacion-fase1/casos-de-prueba-tesis.md`): un fragmento de más de un párrafo o de más de unas 250 palabras hace que el sistema pida seleccionar un fragmento más corto y no procese la solicitud. La primera versión de esta fase solo validaba el límite de palabras; el rechazo de las selecciones de varios párrafos se agregó al contrastarla (apartado 6).

## 1. Alcance

T12 detecta las secciones de cada versión, separa su lista de referencias y valida el alcance de una futura solicitud. No crea solicitudes ni las encola (T28 y T29), ni tiene pantalla (T13). Lo que sí agrega son tres rutas del caso, para ver las secciones de su versión y marcarlas a mano.

## 2. Correcciones a la extracción de T11

Las dos vienen de la tarea técnica "tolerancia a campos de gestores bibliográficos":
- **Controles de contenido de bloque (`w:sdt`):** python-docx solo recorre los `w:p` y `w:tbl` que cuelgan del cuerpo. La bibliografía de Mendeley y la de Word vienen dentro de un `w:sdt` de bloque, así que se perdían enteras. Ahora la extracción recorre también el contenido de los `w:sdt` y `w:customXml`, en el cuerpo y en las celdas.
- **Saltos de línea:** se conservan como `\n` dentro del texto del párrafo. Así se separan las entradas cuando la lista de referencias va en un solo párrafo con saltos de línea. Los demás espacios se siguen normalizando.
- **Nivel de título:** cada párrafo guarda `nivel`:
  - `0` para el título del documento;
  - `1` a `9` para un título;
  - nulo para el texto.

Las versiones de T11 no guardaban el nivel. Solo existen en las pruebas, así que no hace falta migrar datos: el esquema de la tabla no cambia y el nivel ausente se lee como nulo.

## 3. Detección por estilos (`app/borradores/secciones.py`)

El nivel de un párrafo del cuerpo se decide, en este orden:
1. El nivel de esquema del propio párrafo (`w:outlineLvl`). El valor 9 significa texto.
2. El nombre del estilo, siguiendo la cadena de estilos base:
   - "Heading N", "Título N" o "Encabezado N" dan el nivel N;
   - "Title" o "Título" dan el título del documento.

   Word guarda en inglés los nombres de sus estilos integrados aunque esté en español; los estilos propios suelen llamarse "Título 1".
3. El nivel de esquema definido en el estilo o en sus estilos base.

Los párrafos de las tablas nunca son títulos.

**Árbol:**
- Cada título abre una sección `s1`, `s2`… (estable dentro de la versión), con su nivel, su padre y los párrafos que siguen hasta el próximo título.
- Lo anterior al primer título son los preliminares (título, autores, resumen sin título). Quedan fuera de las secciones.
- **Clase de cada sección:** se reutiliza el clasificador de títulos del corpus (T09-01, apartado 4.2), así que "2. Método", "Methods" y "Metodología" son `metodos`. Una subsección sin clase hereda la de su padre.
- **"Con estilos"** significa que hay al menos un título de nivel 1 a 9. Un documento que solo tiene "Título" no tiene secciones.

**Sin estilos:** la versión se crea igual (RF-01). La respuesta de la carga pide marcar las secciones, y `PUT /caso/versiones/{id}/secciones` recibe los párrafos que son títulos y su nivel. Las guarda con el método `manual` y vuelve a detectar las referencias.

## 4. Lista de referencias

- **Automática:** la primera sección cuyo título clasifica como referencias ("Referencias", "Bibliografía", "References", "Lista de referencias"…), con sus subsecciones.
- **Manual:** `PUT /caso/versiones/{id}/referencias` con el primer y, si se quiere, el último párrafo de la lista. Sirve cuando la lista no tiene un título con estilo.
- **Entradas:** una por línea no vacía de esos párrafos. Las entradas son texto: T15 y T20 las analizan y verifican. Aquí no se interpreta nada ni interviene un modelo de lenguaje (RN-17).

## 5. `estructura_borrador(version)`

Herramienta de D1 y D2 (T23, T24 y T26). Devuelve:
- el título del documento;
- el árbol de secciones (id, título, nivel, clase e hijos);
- el método de detección;
- la sección de referencias;
- las **ubicaciones** del problema, los objetivos y las hipótesis.

**Cómo se detectan las ubicaciones** (en español y en inglés, fuera de las referencias y de las tablas):
- **Por el título de una sección:** "Planteamiento del problema", "Objetivos", "Hipótesis"…
- **Por frases en el texto:** "el objetivo de este estudio", "se planteó como objetivo", "H1:", "la hipótesis", "pregunta de investigación", una pregunta entre "¿" y "?"…

Cada ubicación da la sección y el párrafo, y si se halló por el título o por el texto. Es una pista para el agente, no un juicio: el agente lee el texto.

## 6. Validación del alcance (`app/borradores/alcance.py`)

`validar_alcance(tipo, alcance_tipo, alcance_ref, version, parametros)` devuelve el texto del alcance o rechaza con un motivo (422):

| Regla | Motivo |
| --- | --- |
| El alcance debe ser uno de los admitidos por el tipo (insumos de T04, tabla 3; la base lo impone con un CHECK) | `alcance_no_admitido` |
| `seccion`: la versión tiene secciones y el id existe. El texto es la sección con sus subsecciones | `sin_secciones`, `seccion_inexistente` |
| `fragmento`: un solo párrafo (RF-02). Una selección de varios, como lista (`p3,p4`) o rango (`p3-p5`), se rechaza aunque sean cortos, y el mensaje dice cuántos abarca y pide uno más corto (CP-09). `p3-p3` es un solo párrafo | `fragmento_de_varios_parrafos` |
| `fragmento`: el id de párrafo existe | `parrafo_inexistente` |
| `fragmento` en `propuesta_redaccion` (D3): hasta `limite_palabras_d3` palabras (250, configuración versionada; CP-09). El mensaje dice cuántas tiene y pide seleccionar un fragmento más corto | `alcance_demasiado_largo` |
| `consulta`: texto no vacío, de hasta 2 000 caracteres | `consulta_vacia`, `consulta_demasiado_larga` |
| `hito` y `version`: sin referencia (toman la versión completa) | `alcance_ref_no_admitido` |

La pertinencia de la consulta (clasificador barato, RF-02) y la decisión de encolar son de las fases de orquestación.

## 7. Cambios manuales y trazabilidad

- Las secciones y las referencias de una versión se pueden marcar a mano mientras ninguna solicitud la use. Después, `PUT` responde 409 (`version_en_uso`): el alcance de una solicitud se refiere a sus ids y no debe cambiar debajo de ella (RNF-01).
- El texto de los párrafos nunca cambia: una versión es inmutable.

## 8. Rutas del caso

| Ruta | Qué hace |
| --- | --- |
| `GET /caso/versiones/{id}/secciones` | Método de detección, árbol de secciones, párrafos con su texto y sección, y referencias con sus entradas. El caso lee su propio borrador para elegir el alcance (F-05) |
| `PUT /caso/versiones/{id}/secciones` | Títulos marcados a mano: `{"titulos": [{"parrafo": "p2", "nivel": 1}]}` |
| `PUT /caso/versiones/{id}/referencias` | Lista de referencias marcada a mano: `{"desde": "p40", "hasta": "p60"}` |

Una versión de otro caso responde 404. La decisión T11-01 decía que ninguna ruta devolvía el texto. Esta fase la acota: el propio caso puede leer los párrafos de su versión, porque necesita verlos para elegir el alcance. El archivo sigue sin servirse.

## 9. Riesgos

- **Títulos mal marcados:** un párrafo largo con estilo de título se toma como título. El caso puede corregirlo marcando las secciones a mano.
- **Pistas de problema, objetivos e hipótesis:** son heurísticas, con falsos positivos y negativos. Por eso se presentan como ubicaciones, no como contenido detectado.
- **Notas al pie y cuadros de texto:** siguen sin extraerse (T11-01, apartado 7).
