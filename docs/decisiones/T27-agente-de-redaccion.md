# T27-01. Agente estilístico (D3): propuesta de redacción de un párrafo

**Fase:** T27 (Bloque 2). **Fecha:** 26 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional, sin revisión humana. El cierre es ligero.

## Entrada (CP-09, RN-07)

- **Alcance:** un solo párrafo del cuerpo de la versión vigente, de hasta `limite_palabras_d3` (250) palabras, medidas con `contar_palabras` (separación por espacios), la misma medida para el original y la propuesta.
- **Validación antes de crear la solicitud:** `validar_alcance` (T12) rechaza más de un párrafo o un párrafo más largo con el mensaje "Seleccione un fragmento más corto"; no se crea la solicitud ni se llama al modelo.
- **Títulos y lista de referencias:** no se admiten. Una propuesta sobre una entrada de la lista sería una referencia escrita por el modelo (RN-17).
- **Lista de párrafos:** `GET /caso/redaccion/parrafos` muestra también los que exceden el límite, marcados, para que la pantalla explique por qué no se procesan.

## Recuperación y generación

- **Consulta:** nombra los tres indicadores, sin el texto del estudiante (lección de T23-01) y sin "artículo científico empírico". Con esas palabras, el reordenador traía apartados de estructura por delante de las pautas de redacción y el juez de suficiencia se abstenía.
- **Guía provisional nueva:** `lista-comprobacion-redaccion.md`, con criterios RED-1 a RED-13 por indicador. Con la guía de redacción anterior, los apartados de fluidez y gramática quedaban bajo el umbral. Con la consulta final, los cinco primeros fragmentos son de redacción y tres superan 0,5.
- **Instrucción `redaccion/v1`:** mismo contenido, citas y números del original sin cambios, un solo párrafo, hasta 1.2 veces, cambios con `antes` y `despues` literales y la pauta citada. Lo de otra dimensión va en una nota.
- **Original:** el sistema reemplaza `original` de la salida por el párrafo guardado, para que las comprobaciones y la vista partan del texto real.

## Comprobaciones

- 1 (esquema) y 3 (citas a fragmentos recuperados), como en D1.
- **2 para D3, `limites_propuesta` (CP-10):**
  - la propuesta tiene hasta `int(palabras del original × 1.2)` palabras;
  - es un solo párrafo;
  - no agrega números ni citas entre corchetes o paréntesis que el original no tenga;
  - cada cambio está en el original (`antes`) y en la propuesta (`despues`), comparando palabras sin puntuación ni mayúsculas.
- Si alguna falla, "Con advertencias"; el reintento es de T30. La conservación del resto del contenido la juzga el evaluador de T30 sobre la salida guardada.

## Atención común

`AtencionPorAlcance` (en `app/agentes/seccion.py`) es el camino común de D1, D2 y D3: valida el alcance antes de crear la solicitud, atiende en segundo plano y aplica las comprobaciones del tipo. `AtencionSeccion` (D1 y D2) y `AtencionRedaccion` (D3) solo definen cómo resolver el alcance, el ajuste de la salida y sus comprobaciones.

## Proveedor de modelo

- **Tope de salida de Groq de 2048 a 4096** (migración 0018). gpt-oss-120b razona antes de responder y esos tokens cuentan como salida: en el párrafo coloquial usó hasta 3196. Con 2048 la salida se cortaba y Groq respondía 400 `json_validate_failed`.
- **`json_validate_failed` se reintenta.** Se clasifica como respuesta ilegible (error de disponibilidad), porque es una generación fallida ocasional, no una solicitud mal formada. El registro guarda el código del proveedor (`http_400:json_validate_failed`), nunca el mensaje ni la generación fallida.
- **Latencia:** el limitador reserva la entrada más el tope y el plan gratuito de Groq admite 8000 tokens por minuto. Por eso la propuesta puede esperar hasta un minuto la ventana del limitador: tardó entre 30 y 140 s.

## Pantalla `/panel/redaccion`

- Selector de párrafo con su sección, inicio y palabras, y el párrafo elegido completo.
- Original y propuesta lado a lado. La comparación es palabra por palabra (subsecuencia común más larga, `frontend/src/diferencias.ts`): en el original se tacha lo que cambia (`del`) y en la propuesta se subraya lo nuevo (`ins`), sin depender solo del color.
- Cada cambio con su tipo, antes y después, su razón y la pauta desplegable (guía y apartado). Aviso de que el borrador no se modifica.

## Prueba con el modelo real

Groq, 26 de noviembre de 2026, provisional:
- **Párrafo de la introducción, con citas [3] y [4]:** 3 cambios, citas conservadas y comprobaciones superadas.
- **Párrafo coloquial agregado al borrador de demostración:** 6 a 7 cambios. Corrige "como todos saben", "un montón" y "nosotros pensamos" y desarrolla la sigla IA. Comprobaciones superadas, de 62 a 56 palabras.

## Provisional, sin revisión humana

- La guía `lista-comprobacion-redaccion.md`.
- La instrucción `redaccion/v1`.
- El párrafo coloquial del borrador de demostración.
- Los textos de la pantalla.
- Las dos pruebas reales.

**Pendiente:**
- un conjunto de párrafos con errores de redacción y su clave, que arma el asistente antes de T34;
- el reintento con los motivos de falla y el evaluador de conservación del contenido, en T30.
