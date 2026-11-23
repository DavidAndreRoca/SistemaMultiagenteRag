# T16-01. Recuperación híbrida y suficiencia en dos pasos

**Fase:** T16 (Fase 3; va después de T17 según el orden de ejecución). **Fecha:** 22 de noviembre de 2026. **Estado:** vigente.

**Origen:** hoja de ruta, T16 y riesgo R-01. Especificación de la Fase 1:
- RF-10, CU-09 y CP-05;
- RN-03: cada tipo consulta solo su colección;
- RN-04: sin evidencia suficiente no se genera contenido;
- RNF-04: abstención;
- 18.6: recuperación, reranking y suficiencia.

Decisiones del equipo del 22 de noviembre de 2026: apartados 3, 4 y 7.

## 1. Alcance

`app/rag/` recupera, para una solicitud de un caso, los fragmentos más pertinentes de las colecciones permitidas y decide en dos pasos si alcanzan.
- **Si alcanzan:** entrega un contexto cerrado, con fragmentos numerados `F1` a `Fn`.
- **Si no:** registra la abstención.

Los agentes (T18 en adelante) y el grafo (T28) lo usan; en T16 no se genera nada.

## 2. Flujo (18.6)

1. **Colecciones:** `colecciones_permitidas(tipo, contexto)`.
   - La función pública recibe el `ContextoAcceso` del caso, el tipo de solicitud y la consulta. No acepta una colección.
   - El repositorio de recuperación vuelve a calcular las colecciones a partir del tipo y del contexto (RN-03, RNF-03).
   - Solo cuentan los documentos recuperables (activos, o incompletos confirmados).
2. **Búsqueda densa** (k = 30, coseno con bge-m3) y **léxica** (k = 30, `tsvector` simple).
3. **Fusión por rangos recíprocos:** puntaje = suma de 1 / (60 + posición), con `rrf_constante`.
4. **Reranking:** los primeros `candidatos_reranking` de la fusión pasan por bge-reranker-v2-m3 y se ordenan por su puntaje (sigmoide, de 0 a 1).
5. **Presupuesto de contexto:** se toman los mejores en orden, hasta `n_reranking` (8) y sin superar `presupuesto_tokens_contexto`, sin cortar ningún fragmento. Se numeran `F1` a `Fn`.
6. **Suficiencia, paso 1:** al menos `suficiencia_n` (2) fragmentos con puntaje igual o mayor que `suficiencia_tau` (0,5, provisional). Si no se cumple, hay abstención sin llamar al modelo.
7. **Suficiencia, paso 2:** el modelo, mediante el adaptador de T17 con la instrucción `suficiencia/v1`, responde `{suficiente, motivo}` sobre la solicitud y los fragmentos. Los fragmentos van delimitados como datos (RN-23).
   - Si el modelo no está disponible, el resultado es un error técnico: la solicitud quedará "no atendida" en T28 (4.4).
   - No es una abstención, porque nadie juzgó la evidencia.

## 3. Candidatos del reordenador (decisión del equipo)

- **Medición:** con fragmentos reales del corpus provisional, en la computadora de desarrollo, el reordenador tardó:

  | Candidatos | Tiempo |
  | --- | --- |
  | 30 | 28,2 s |
  | 20 | 17,4 s |
  | 15 | 14,2 s |
  | 10 | 8,9 s |

  En el servidor ARM será más lento.
- **Decisión:** la configuración inicial reordena **20** candidatos (`candidatos_reranking`), en lugar de los 30 de la especificación (18.6). Es un valor provisional que T34 calibra con el conjunto de prueba.

## 4. Presupuesto de contexto (decisión del equipo, R-01)

- **Motivo:** los fragmentos del corpus provisional tienen 365 tokens en promedio. Con 8 en el contexto, el juicio de suficiencia más la generación se acercan a los 8 000 tokens por minuto de Groq.
- **Decisión:** `presupuesto_tokens_contexto = 2400` toma los mejores fragmentos en orden hasta ese tope (unos 6) y nunca corta uno. Siempre entra al menos el primero, aunque lo supere.
- **Recalibración:** T34 y T38 lo recalibran con el modelo de producción.

## 5. Registro

- **`fragmento_recuperado`:** una fila por fragmento numerado, con:
  - identificador visible y posición;
  - similitud coseno y puntaje léxico, si la búsqueda lo encontró;
  - puntaje de la fusión y del reranking.

  Se guarda también cuando hay abstención (alimenta M2 y M3).
- **Abstención:** un `resultado` con `abstencion = true`, etiqueta `sin_evidencia_suficiente`, el paso que decidió y su motivo, y el aviso "Sin evidencia suficiente" (CP-05).
- **Eventos técnicos:** la recuperación deja eventos técnicos (`recuperacion`, `reranking`) con su duración. El juicio del modelo deja los del adaptador.
- **Sin contenido:** el registro JSON no lleva la consulta ni los fragmentos (4.6).

## 6. Configuración (migración de datos 0013)

| Parámetro | Valor | Origen |
| --- | --- | --- |
| `candidatos_reranking` | 20 | Apartado 3 |
| `presupuesto_tokens_contexto` | 2 400 | Apartado 4 |
| `versiones_instrucciones.suficiencia` | `v1` | Instrucción nueva, registrada con su huella |

Siguen sin cambios `k_denso` (30), `k_lexico` (30), `rrf_constante` (60), `n_reranking` (8), `suficiencia_n` (2) y `suficiencia_tau` (0,5).

## 7. Conjunto de consultas de prueba (decisión del equipo)

- **Ubicación:** `evaluacion/conjuntos/recuperacion-t16.json`. Tiene unas 20 consultas, 10 por tema del corpus provisional.
- **Redacción:** cada consulta está escrita como la formularía un estudiante en su borrador (una afirmación que quiere sustentar o una duda), sin copiar frases de los títulos ni de los resúmenes.
- **Datos de cada consulta:**
  - el tema;
  - el tipo de solicitud (`busqueda_evidencia`);
  - el documento del que salió (por DOI y título);
  - los documentos esperados.
- **Estado:** queda como **borrador** hasta que el equipo lo revise, reescriba o amplíe, antes de usarlo en las métricas finales de T34 y T38.
- **Métricas de la línea base**, sin modelo de lenguaje y con los documentos esperados como referencia. Un fragmento es pertinente si pertenece a un documento esperado.
  - **Precisión contextual:** precisión promedio ponderada por posición sobre los `F1` a `Fn`, como la de Ragas pero con esa referencia.
  - **Exhaustividad:** fracción de documentos esperados presentes en el contexto.

  Ragas con modelo evaluador es del arnés de T38.
- **Registro:** la línea base se anota en ESTADO sin umbral. El umbral de la tesis es de 0,80 para la precisión contextual y se exige en T38.

## 8. Pruebas

- **Unitarias:**
  - fusión por rangos recíprocos;
  - presupuesto de contexto;
  - paso 1 de la suficiencia;
  - numeración;
  - paso 2 con el modelo simulado, en ambos desenlaces y con el modelo caído.
- **Integración con la base real:**
  - aislamiento: el caso A nunca recibe fragmentos de la colección personal del caso B, de otro tema, de las guías ni de documentos retirados;
  - filtros por tipo;
  - registro de `fragmento_recuperado` y de la abstención;
  - CP-05: con un tema sin documentos pertinentes no se llama a la generación y la abstención queda registrada.
- **Línea base:** `python -m app.rag.evaluar` con el corpus provisional y el servicio de modelos reales, en solo lectura.
