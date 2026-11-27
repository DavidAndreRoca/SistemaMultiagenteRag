# T31-01. Decisiones sobre los resultados y contadores de uso

**Fase:** T31. **Fecha:** 27 de noviembre de 2026. **Estado:** vigente.

Con las reglas del equipo del 26 de noviembre de 2026, el asistente decide lo no técnico y lo anota como provisional. El cierre es ligero.

## Decisiones (RF-12, CU-11, HU-10, RN-08)

- **Sobre qué se decide:** el resultado final de una solicitud entregada del propio caso. Si hubo reintento, el del último intento.
  - Otra solicitud responde 404, igual que una inexistente (4.4).
  - Una solicitud todavía en curso o no atendida responde 409 `sin_resultado`.
- **Opciones:**
  - sobre una propuesta, aceptar, modificar o rechazar;
  - tras una abstención ("Sin evidencia suficiente"), continuar o aportar;
  - otra opción responde 422 `opcion_no_admitida`, con las admitidas en el detalle.
- **Cambio de decisión:**
  - una decisión nunca se edita: cambiarla registra otra con `decision_reemplazada_id` apuntando a la anterior, y las dos se conservan;
  - repetir la vigente responde 409 `decision_repetida`;
  - la solicitud se bloquea (`FOR UPDATE`) mientras se decide, y el índice único sobre el reemplazo cubre dos decisiones simultáneas: la segunda responde 409.
- **Orden del historial:** sigue la cadena de reemplazos, no la hora, porque dos decisiones pueden registrarse en el mismo instante.
- **Registro:** un evento `decision` con el tipo, la opción y si reemplaza a otra, sin texto del resultado (4.6).
- **Rutas:** `GET` y `POST /caso/solicitudes/{id}/decision` en `app/api/decisiones.py`, sobre `RepositorioDecisiones` (`app/repositorios/caso.py`).

## Contadores (RN-08)

`GET /caso/contadores` devuelve:

- decisiones vigentes por tipo de solicitud y opción: una decisión reemplazada ya no cuenta;
- solicitudes entregadas por hito frente al uso mínimo orientativo de la configuración (`uso_minimo_por_hito`). Se informa, no bloquea ninguna entrega.

Se calculan al consultar, sin tablas de contadores aparte: no hay datos que puedan desfasarse.

## Interfaz

- **Componente `DecisionSobreResultado`** (`frontend/src/componentes/Decision.tsx`):
  - aparece bajo el resultado entregado en las seis pantallas;
  - muestra la decisión vigente con su fecha, los botones de las otras opciones y las decisiones anteriores en un desplegable;
  - si no carga, el resultado se sigue viendo.
- **Sección "Su uso del sistema"** en el panel del caso: la tabla por hito con "Alcanzado" o "Faltan n", y la de decisiones por tipo. Si no carga, el resto del panel sigue disponible.
- **Aportar una fuente:** se muestra deshabilitado con la insignia "Pendiente" hasta T32, que lo implementa.

## Provisional, sin revisión humana

- Los textos de los botones: "La acepto", "La usaré con cambios", "No la usaré" y "Continuar sin aportar una fuente".
- Contar solo las decisiones vigentes.
- Medir el uso mínimo con las solicitudes entregadas de cada hito, de cualquier tipo.
- Los contadores por tipo agrupan todos los hitos; el desglose por hito y tipo queda para el informe del docente si se pide.
