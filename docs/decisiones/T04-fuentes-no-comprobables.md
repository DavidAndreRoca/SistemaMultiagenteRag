# T04-04. Conteo de fuentes no comprobables en la verificación

**Estado:** Aceptada por los autores el 6 de noviembre de 2026. Migración 0005.

## Contexto

La salida del módulo de verificación (Fase 1, 6.7) registra en la comprobación 4 dos conteos: `n_fuentes_citadas` y `n_fuentes_confirmadas`. La métrica M6 (tasa de referencias no verificables) cuenta las referencias que no se localizaron por DOI ni por metadatos.

RN-18 y la tabla 42 distinguen dos casos:
- **No localizada:** los servicios respondieron y no hubo coincidencia.
- **No comprobable:** el servicio no respondió. Una fuente así nunca se declara inexistente.

## Decisión

`verificacion` tiene una tercera columna, `n_fuentes_no_comprobables` (entero, 0 por defecto). La base impone `n_fuentes_confirmadas + n_fuentes_no_comprobables <= n_fuentes_citadas`.

## Motivo

Con solo dos conteos, la diferencia entre citadas y confirmadas mezcla las no localizadas con las no comprobables. M6 contaría entonces como no verificable una fuente que solo quedó sin comprobar por una caída del servicio, lo que contradice RN-18.

## Consecuencias

- M6 usa `n_fuentes_citadas - n_fuentes_confirmadas - n_fuentes_no_comprobables` como no localizadas; las no comprobables se informan aparte.
- `superada` sigue exigiendo que todas las fuentes citadas estén confirmadas: una fuente no comprobable no supera la verificación, pero tampoco cuenta como fabricada.
