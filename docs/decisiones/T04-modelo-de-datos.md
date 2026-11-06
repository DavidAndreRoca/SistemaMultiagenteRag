# T04-01. Decisiones del modelo de datos

**Estado:** Vigente (decisión técnica nueva, fase T04). Los puntos que eran provisionales se contrastaron con la especificación de la Fase 1 y se corrigieron en `T04-contraste-especificacion-fase1.md` (migraciones 0005 y 0006).

## Decisiones

1. **Identificadores UUID** (`gen_random_uuid()`): evitan identificadores secuenciales adivinables entre casos.
2. **Enumeraciones como texto con CHECK** (no tipos `ENUM` de PostgreSQL): añadir un valor es una migración simple.
3. **`caso_id` en todas las tablas del registro metodológico**, incluidas las hijas (`fragmento_recuperado`, `resultado`, `verificacion`, `decision`, `fuente_aportada`), con **clave foránea compuesta** `(padre_id, caso_id)` hacia el padre. La base impide que un registro de un caso cuelgue de otro caso: es una segunda barrera, además del filtro de los repositorios (T05).
4. **Colección personal sin columna en `caso`**: se identifica por `coleccion.caso_id` con `tipo = 'personal'` (índice único parcial). Evita una clave circular `caso` y `coleccion` en ambos sentidos. `caso.coleccion_cientifica_id` sí existe.
5. **Una versión vigente por caso y hito** (índice único parcial), según la matriz 7.1 ("versión vigente por hito").
6. **`cambio_norma`** (migración 0004, T07) y **`sesion`** (migración 0003, T06) se añaden a las 15 tablas de T04, porque T06 pide sesiones en PostgreSQL y T07 pide registrar cada cambio de norma.
7. **Configuración semilla** (migración 0002): valores que fija la hoja de ruta (k = 30, número final 8, ventana 300 a 450 tokens, fidelidad 0.90, 40 palabras en D1, 1.2 veces en D3, 250 palabras en D3, límites de archivos, normas IEEE y APA7 con IEEE por defecto).

## Puntos provisionales (resueltos)

Se resolvieron el 6 de noviembre de 2026 al contrastar el modelo con la especificación de la Fase 1. El detalle está en `T04-contraste-especificacion-fase1.md`:
* Columnas de `verificacion`: campos de la salida de 6.7 en lugar de `c1_esquema` a `c6_fidelidad`.
* Metadatos de `documento`: se añaden ISBN y ruta del archivo; `fuente` pasa a `revista_editorial`.
* Tipos y alcances de `solicitud`: códigos de la tabla 3 de los insumos y CHECK de alcance por tipo.
* `tau` y `N` (0.5 y 2) y los ocho hitos cargados en la versión 1 (migración 0006).
* La columna "Alimenta" usa los códigos M1 a M6 de la ficha de métricas.
