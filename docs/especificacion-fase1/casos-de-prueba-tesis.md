# Casos de prueba de la tesis (Tabla 20)

**Fuente:** tesis, apartado 6.2.7.1, Tabla 20. Es el texto oficial que se usa para contrastar las pruebas de cada fase. La hoja de ruta (apartado 0) remite aquí: cada caso aparece en el criterio de aceptación de al menos una fase.

**Estado de esta copia:** **incompleta**. Contiene solo los casos que el equipo entregó el 19 de noviembre de 2026 (CP-01 y CP-02). Faltan CP-03 a CP-23 y PI-01 a PI-09, que se agregarán cuando el equipo entregue la tabla completa. Hasta entonces, una fase que dependa de un caso que falta lo toma de la especificación de la Fase 1 y lo deja registrado como pendiente de contrastar.

| Caso | Caso de uso | Descripción | Entrada | Resultado esperado | Fase | Pruebas |
| --- | --- | --- | --- | --- | --- | --- |
| CP-01 | CU-01 | Carga válida del borrador | Archivo .docx de un caso registrado | Se registra una nueva versión con fecha y hora; las versiones anteriores se conservan | T11 | `pruebas/integracion/test_borradores.py::test_cp01_carga_valida_registra_la_version_y_conserva_las_anteriores` |
| CP-02 | CU-01, E1 | Archivo con formato no admitido | Archivo en un formato distinto de .docx o dañado | La carga se rechaza, se informa el motivo y no se registra ninguna versión | T11 | `pruebas/integracion/test_borradores.py::test_cp02_formato_distinto_o_danado_se_rechaza_sin_registrar_version` |
