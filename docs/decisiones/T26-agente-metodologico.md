# T26-01. Agente metodológico (D2): diagnóstico con la lista de comprobación del diseño

**Fase:** T26 (Bloque 2). **Fecha:** 26 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional, sin revisión humana. El cierre es ligero.

## Diseño declarado

`identificar_diseno` reconoce el diseño en el texto de la sección por su nombre, sin tildes y con límites de palabra:
- **Prioridad:** cuasiexperimental, experimental, correlacional y descriptivo. Si nombra varios, gana el más exigente; por ejemplo, "descriptivo correlacional" da correlacional.
- **"No experimental"** no cuenta como experimental.
- **Diseño no identificable:** la tarea pide preguntarlo en `preguntas_al_estudiante` y no suponerlo, y se revisa con los elementos comunes (CU-05, flujo alternativo).
- **Pantalla:** el diseño detectado se muestra en la lista de secciones y en el resultado.

## Herramienta `lista_de_comprobacion(diseno)`

- **Qué lee:** del corpus de guías (`RepositorioRecuperacion.por_apartado`, solo colecciones permitidas para el tipo), los criterios del apartado `Diseño <nombre>` y del apartado `Elementos comunes a todos los diseños`. Esos nombres son los de la guía provisional de listas de comprobación; una guía oficial debe usar los mismos títulos de apartado.
- **Cómo se usa:** los criterios, abreviados a sus 9 primeras palabras y sin código, forman la consulta de recuperación. Así la lista llega al modelo como fragmentos citables y pasa por la suficiencia como cualquier evidencia. El contrato de agentes suma el método `consulta_con_herramientas`, que por defecto devuelve `consulta`.
- **Pruebas con el reordenador real:**
  - una consulta abstracta ("lista de comprobación del diseño X") no traía la lista; puntajes por debajo de 0,3;
  - con el texto completo de los criterios, solo la lista del diseño superaba el umbral (0,64 contra 0,10) y el sistema se abstenía;
  - con los criterios abreviados, las dos listas quedan primeras en los cuatro diseños (de 0,78 a 0,98);
  - sin diseño, la consulta sobre "la sección de método, sea cual sea su diseño" trae los elementos comunes (0,99) y las instrucciones del avance de metodología (0,96).

## Comprobaciones

- 1 (esquema), 3 (citas) y 2 de no reescritura (CP-08); esta ahora también revisa `preguntas_al_estudiante`.
- **2 para D2, `sin_datos_inventados`:** cada número de los textos de la salida tiene que estar en la sección del estudiante o en un fragmento que la salida cita.
  - No cuentan los identificadores como `p12`, `H1` o `COR-6`.
  - La coma decimal se normaliza a punto.
  - Una salida con un valor estadístico inventado (por ejemplo, "r = 0,62 con p < 0,05") va "Con advertencias".
- Las comprobaciones reciben ahora el texto de cada fragmento recuperado (identificador a texto), no solo los identificadores.

## Pantalla `/panel/metodologia`

- Elige por defecto la sección de método.
- Muestra el diseño declarado o el aviso de que no se nombra.
- Presenta las preguntas sobre lo que falta y los hallazgos por severidad con el criterio de la guía desplegable.
- El panel activa la tarjeta y agrega "Plan de tarea" como pendiente (T24).

## Prueba con el modelo real

Groq, 26 de noviembre de 2026, provisional. El Método del borrador de demostración tiene un párrafo nuevo con errores a propósito: diseño correlacional con 30 estudiantes por conveniencia y "se demostrará que el uso de ChatGPT causa una mejora".
- **Tiempo:** 85 s; las 4 comprobaciones superadas.
- **Hallazgos, todos de severidad alta y con citas a la lista correlacional y a los elementos comunes:**
  - la afirmación causal en un diseño correlacional;
  - la muestra y el instrumento sin justificación ni confiabilidad;
  - el análisis sin prueba ni coeficiente.
- **7 preguntas sobre lo que falta:** variables, criterios de inclusión, tamaño de muestra, confiabilidad, programa, consentimiento y prueba.

## Provisional, sin revisión humana

- La instrucción `metodologia/v1`.
- El párrafo con errores metodológicos del borrador de demostración.
- Los textos de la pantalla.
- La prueba real.

**Pendiente:**
- una hoja de errores metodológicos (borradores con errores registrados y su clave), que arma el asistente antes de T34;
- el reintento con los motivos de falla, en T30.
