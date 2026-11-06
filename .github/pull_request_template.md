## Fase y resumen

Fase: T__ (rama `tNN-descripcion-corta`)

<!-- Qué cambia y por qué, en pocas líneas. -->

## Definición de terminado (hoja de ruta, 4.9)

- [ ] Los criterios de aceptación de la fase se cumplen.
- [ ] Sus pruebas y **todas las anteriores** pasan en la integración continua.
- [ ] La cobertura no baja del 70 % en servicios y agentes.
- [ ] El contrato OpenAPI y el diccionario de datos están actualizados si la fase los tocó.
- [ ] `docs/ESTADO_DESARROLLO.md` registra la fase con esta solicitud de cambio.
- [ ] Los casos de prueba de la tesis asignados a la fase quedan registrados como superados.

## Reglas que no se rompen (apartado 0)

- [ ] No hay funcionalidades de fases posteriores "por adelantado".
- [ ] El esquema de datos solo cambia mediante una migración de Alembic.
- [ ] Toda consulta a datos de caso pasa por `repositorios/` con `ContextoAcceso`.
- [ ] Al proveedor del modelo solo se envían solicitud, alcance y fragmentos (RNF-10).
- [ ] Ningún modelo de lenguaje escribe referencias bibliográficas (RN-17).
- [ ] Solo datos ficticios; sin secretos en el código; sin guiones largos en textos visibles.

## Revisión

Revisión cruzada del otro integrante: (nombre)
