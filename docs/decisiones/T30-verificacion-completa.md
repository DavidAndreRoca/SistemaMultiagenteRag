# T30-01. Módulo de integración y verificación completo

**Fase:** T30 (H4). **Fecha:** 27 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional. El cierre es ligero.

## Las seis comprobaciones, por tipo

| Comprobación | Evidencia | Estructura y metodología | Redacción | Plan | Referencias |
|---|---|---|---|---|---|
| 1. Esquema | sí | sí | sí | sí | sí |
| 2. Límites | no aplica | no reescritura; metodología, también números | 1.2 veces, un párrafo, sin datos ni citas nuevas | no reescritura | no aplica |
| 3. Citas a fragmentos recuperados | sí | sí | sí | sí | no aplica |
| 4. Existencia de fuentes | fuentes recomendadas | no aplica (guías del programa) | no aplica | no aplica | no aplica (es el propio informe) |
| 5. Acceso abierto | fuentes recomendadas | no aplica | no aplica | no aplica | no aplica |
| 6. Fidelidad (evaluador) | afirmaciones | criterio del hallazgo | conservación del contenido | tareas | no aplica (sin modelo) |

- **Comprobación 4** (`app/verificacion/fuentes.py`):
  - con DOI, se busca en Crossref (servicios de T14, con caché); si no lo encuentra, o si no hay DOI, se confirma por metadatos (título, al menos un autor y año);
  - un Crossref caído da "no comprobable" (RN-18): no se supera, pero no es inexistencia;
  - método `doi`, `metadatos` o `mixto`.
- **Comprobación 6** (`app/verificacion/evaluador.py`, instrucción propia `evaluador/v1`, migración 0022):
  - el evaluador divide la salida en afirmaciones y clasifica cada una como respaldada, no respaldada o contradicha, solo por los fragmentos que la salida cita;
  - fidelidad = respaldadas / total; umbral `umbral_fidelidad` (0.90) de la configuración;
  - sin afirmaciones (por ejemplo, ningún hallazgo), no aplica;
  - en redacción mide la conservación del contenido: cada afirmación de la propuesta debe estar en el original;
  - al evaluador van la salida y los fragmentos citados, o el original y la propuesta (RNF-10).
- **Independencia:** el evaluador no comparte instrucciones con los agentes. Hoy usa la misma cadena de modelos (Groq); la Fase 1 admite otro modelo, y su elección queda para T25.

## Reintento y etiquetas (RN-05, RN-06, CP-06)

- **Nodo `reintentar` del grafo:** si el intento 1 tiene alguna falla que el agente puede corregir, registra ese intento, con etiqueta "Con advertencias" y su verificación, y pide un único reintento:
  - con los motivos (a lo sumo diez), los mismos fragmentos y sin repetir la recuperación ni la suficiencia (`Agente.reintentar`);
  - el intento 2 se verifica igual.
- **Fallas que no se reintentan** (`Comprobacion.reintentable = False`): un servicio bibliográfico o el evaluador caídos, y el informe determinista de referencias. Regenerar no las arregla, así que el resultado sale "Con advertencias" sin un segundo intento.
- **Etiquetas:** "Verificada" si se superan todas las comprobaciones (antes era un nulo); "Con advertencias" con la lista de fallas; "Sin evidencia suficiente" en la abstención (T16).
- **Registro (PI-04, RNF-05):** cada intento tiene su resultado y su fila en `verificacion`, con cada comprobación en su columna (`app/verificacion/registro.py`). Las abstenciones no tienen verificación.

## Latencias (actividad 9; RNF-12; Fase 1, n.° 11)

- **Eventos técnicos por etapa:** `ejecucion`, `verificacion`, `reintento` y `orquestacion`, además de `recuperacion` y `reranking` de T16.
- **Informe:** `python -m app.orquestacion.latencias --investigador I` da la mediana y el percentil 95 por tipo y por etapa, frente a los objetivos (60 s; 120 s para referencias).
- **Primera medición, en el prototipo, con solo Groq (8000 tokens por minuto):**
  - el plan de tarea con reintento tardó 207 s: cuatro llamadas al modelo, más la espera del limitador;
  - la verificación sola puede llevar 2 minutos;
  - con la verificación completa, D1 a D3 y evidencia superan el objetivo de 60 s del percentil 95.
  - La causa es el límite de tokens del plan gratuito, no el procesamiento. Elegir el proveedor de producción o un modelo aparte para el evaluador (T25) es lo que puede bajarlo, y tiene costos que decide el equipo.

## Interfaz

Los resultados verificados muestran la insignia "Verificada" con una explicación breve. "Con advertencias" sigue mostrando la lista de comprobaciones fallidas.

## Pruebas

- **Unitarias:** evaluador (respaldada, baja fidelidad con motivos, sin afirmaciones, servicio caído, conservación), existencia de fuentes (DOI, metadatos, mixto, sin metadatos, servicio caído), registro por columnas, motivos del reintento e informe de latencias.
- **Integración:**
  - CP-06: dos fallas dan "Con advertencias" con un solo reintento;
  - un reintento que se supera queda "Verificada";
  - una falla no corregible no pide reintento;
  - PI-04: todo resultado tiene etiqueta y su verificación;
  - con el agente real de estructura, el reintento usa los mismos fragmentos sin una segunda recuperación.
- **Modelo real:**
  - el evaluador rechazó una tarea del plan que exigía "al menos tres citas", un requisito ausente en las guías citadas;
  - la propuesta de redacción del párrafo coloquial salió "Verificada" en el primer intento, con la conservación del contenido en 7 de 7.

## Provisional, sin revisión humana

- La instrucción `evaluador/v1`.
- Usar la misma cadena para el evaluador.
- El texto de la insignia.

**Pendiente:** el modelo del evaluador y el proveedor de producción (T25), para cumplir RNF-12.
