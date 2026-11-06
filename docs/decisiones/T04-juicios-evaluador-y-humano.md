# T04-03. Dos columnas por juicio de evaluación (evaluador y humano)

**Estado:** Aceptada por los autores el 6 de noviembre de 2026. Migración 0005.

## Contexto

Las métricas M2 (precisión contextual), M3 (completitud) y M5 (relevancia) se calculan con el juicio de un modelo evaluador sobre todas las solicitudes, más una muestra humana del 20 al 30 % (tesis 6.2.7.2). RF-25 pide además calcular la concordancia entre ambos.

Los insumos de T04 proponían una sola columna por juicio con su origen (por ejemplo, `pertinente` con `pertinencia_fuente` = `evaluador` o `humano`), o una tabla de evaluación aparte.

## Decisión

Cada juicio tiene dos columnas, una del modelo evaluador y otra de la revisión humana:

| Tabla | Columnas | Tipo | Métrica |
| --- | --- | --- | --- |
| `fragmento_recuperado` | `pertinencia_evaluador`, `pertinencia_humana` | booleano | M2 |
| `solicitud` | `completitud_evaluador`, `completitud_humana` | decimal de 0 a 1 (CHECK) | M3 |
| `resultado` | `relevancia_evaluador`, `relevancia_humana` | decimal de 0 a 1 (CHECK) | M5 |

Todas son nulas hasta que se evalúen. Se llenan en T38 (arnés) y en el cálculo de O2, nunca durante la solicitud.

## Motivo

- Para calcular la concordancia hacen falta los dos juicios del mismo elemento. Con una sola columna y su origen, el juicio humano reemplazaría al del evaluador y la concordancia no podría calcularse.
- Las columnas viven en la tabla del elemento juzgado. Así conservan su clave foránea y su `caso_id`, y el aislamiento por caso no cambia.
- Una tabla de evaluación aparte necesitaría una referencia polimórfica (fragmento, solicitud o resultado) sin integridad referencial.

## Consecuencias

- La muestra humana se identifica por las filas con la columna humana no nula.
- Si más adelante hace falta registrar quién evaluó o con qué modelo, se agrega con una migración (el modelo del arnés queda en la configuración versionada, RF-25).
