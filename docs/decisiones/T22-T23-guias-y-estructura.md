# T22-01 y T23-01. Corpus de guías y agente de estructura y coherencia (D1)

**Fases:** T22 y T23 (Bloque 2). **Fecha:** 26 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional, sin revisión humana. El cierre es ligero.

## T22. Corpus de guías

- **Formato:** Markdown con cabecera (título, tipo, procedencia y licencia) y apartados `##`, o .docx con títulos con estilo. Comando: `python -m app.corpus.guias --investigador I --carpeta DIR [--aplicar]`.
- **Segmentación por apartado,** no por IMRaD: cada fragmento registra su apartado en `seccion_original`, y un apartado largo se divide por párrafos (hasta unos 450 tokens). Una guía con el mismo texto no se duplica.
- **Colección `guias`:** una sola, compartida, que solo recuperan D1, D2 y D3 (la búsqueda de evidencia no la ve).
- **Rúbrica:** nunca se indexa (RN-11). Se rechaza por nombre ("rúbrica" en el archivo o el título) y por huella SHA-256 registrada en `backend/guias/rubricas-bloqueadas.txt`.
- **Guías provisionales** (`backend/guias/provisionales/`), redactadas por el asistente y **provisionales, sin revisión humana**:
  - estructura y coherencia del artículo IMRaD;
  - listas de comprobación por diseño (experimental, cuasiexperimental, correlacional y descriptivo, con criterios identificables);
  - instrucciones del programa por hito, a partir del catálogo de hitos de la configuración;
  - redacción académica.

  Si el equipo entrega las instrucciones oficiales del programa, el sílabo o la guía de la universidad, se indexan con el mismo comando, sin cambiar código.
- **Consultas de prueba** con el reordenador real: las cuatro, una por tipo de guía, traen primero el apartado esperado.

## T23. Agente de estructura y coherencia (D1)

- **Alcance:** una sección de la versión vigente, con sus subsecciones y cada párrafo identificado (`[p12]`). La lista de referencias no se revisa.
- **Consulta de recuperación:** los criterios y el título de la sección, sin el texto del estudiante. En la primera prueba real, con el texto mezclado, el reordenador no encontraba las guías y el sistema se abstenía. El texto del estudiante igual llega al modelo en el alcance.
- **Instrucción `estructura/v1`:**
  - tres indicadores (alineación entre problema, objetivos e hipótesis; secuencia lógica; cohesión);
  - hallazgos con ubicación, severidad, recomendación y citas a las guías, de 40 palabras como máximo;
  - sin puntajes y sin reescribir;
  - una nota que redirige si el problema es de otra dimensión.
- **Comprobaciones:** 1 (esquema), 3 (citas a fragmentos recuperados) y 2 nueva, de no reescritura. La 2 rechaza cualquier texto de la salida con más de `limite_reescritura_palabras` (40) palabras propias, sin contar lo que cita entre comillas del propio estudiante (CP-08). Si alguna falla, el resultado va "Con advertencias"; el reintento es de T30.
- **Atención genérica por sección** (`app/agentes/seccion.py`), que reutilizará D2 (T26). Los hallazgos se guardan de mayor a menor severidad.
- **Migración 0016:** fija `versiones_instrucciones.estructura`. Si la versión 1 de la configuración ya la usan solicitudes, como en la base de desarrollo, crea una versión nueva y vigente en lugar de modificarla (RNF-21).
- **Pantalla `/panel/estructura`:**
  - elección de la sección, avance y diagnóstico;
  - hallazgos con insignia de severidad y criterios desplegables (guía y apartado);
  - fortalezas y notas.
  - El panel activa la tarjeta y la lista de solicitudes incluye este tipo.

**Prueba con el modelo real** (Groq, 26 de noviembre de 2026), sobre la introducción del borrador de demostración. Fue un solo caso, provisional:
- respondió en 20 s, con las tres comprobaciones superadas;
- un hallazgo de severidad alta: no presenta problema, objetivos ni hipótesis, que es lo que le falta a ese borrador;
- uno medio de transición y uno bajo de cohesión, cada uno con su apartado de guía;
- tres fortalezas.

**Pendiente:**
- un conjunto de borradores con errores estructurales y su clave, para medir que detecta los errores y no comenta otras dimensiones (criterio de T23). Lo arma el asistente, provisional, antes de T34;
- el reintento con los motivos de falla, en T30.
