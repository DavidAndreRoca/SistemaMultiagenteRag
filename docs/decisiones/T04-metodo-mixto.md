# T04-05. Valor `mixto` en el método de comprobación de fuentes

**Estado:** Aceptada por los autores el 6 de noviembre de 2026. Migración 0005.

## Contexto

La salida de la verificación (Fase 1, 6.7) tiene un solo campo `metodo` por intento, con los valores `doi` o `metadatos`. Una misma propuesta puede citar varias fuentes, y es posible confirmar unas por DOI y otras por metadatos (título, al menos un autor y año).

## Decisión

`verificacion.metodo` admite tres valores: `doi`, `metadatos` y `mixto`. Es nulo si y solo si no se confirmó ninguna fuente (CHECK `metodo_si_hay_confirmadas`).

La enumeración es `MetodoComprobacionFuentes`, distinta de `MetodoExistencia` (solo `doi` o `metadatos`), que sigue usándose en `fuente_aportada` porque allí cada fila es una sola fuente.

## Motivo

Con un solo campo y dos valores, una verificación con fuentes confirmadas por ambos métodos tendría que perder información. `mixto` es la única forma de no perderla sin cambiar la forma de la salida de 6.7.

## Consecuencias

M6 puede desglosarse por método, y las verificaciones `mixto` se informan como tales. Si más adelante hace falta el método de cada fuente por separado, se agrega con una migración.
