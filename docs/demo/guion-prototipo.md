# Guion del prototipo (5 minutos)

Recorrido de punta a punta del estudiante: entra, carga su borrador, pide evidencia y verifica sus referencias. Los datos de demostración son ficticios y provisionales, sin revisión humana (ESTADO, apartado 24).

## Antes de la presentación (unos 10 minutos)

1. Con Docker Desktop abierto, en PowerShell, desde la raíz del repositorio:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\prototipo.ps1
   ```

   Al final dice "Listo. Abra http://127.0.0.1:5173". Cada ejecución cambia las contraseñas de las cuentas de demostración.
2. Abra `datos\demo\credenciales.txt` y tenga a mano la contraseña de `DEMO-01-1`. El archivo está fuera de Git: no lo comparta ni lo proyecte.
3. En el navegador, abra http://127.0.0.1:5173.
4. Prueba en seco: entre como `DEMO-01-1` y haga una búsqueda de evidencia. Así la primera respuesta en vivo no paga el arranque en frío del servicio de modelos.

Si algo falla: `docker compose logs api --tail 50`.

## En vivo

| Minuto | Qué hacer | Qué decir |
|---|---|---|
| 0:00 | Pestaña 1: **Iniciar sesión** con `DEMO-01-1` | Cada estudiante (caso) tiene su cuenta y solo ve lo suyo. No se usan datos personales: el código es ficticio. |
| 0:30 | En el **Panel del caso**, en "Cargar una versión", elija el hito **Avance 1**, el archivo `docs\demo\borrador-demostracion.docx` y **Cargar la versión** | El sistema valida el .docx (tamaño, macros, formato) y detecta sus secciones y la lista de referencias. La versión queda registrada y es la vigente del hito. |
| 1:00 | Clic en **Buscar evidencia en las fuentes de su tema**. Escriba: *¿Los estudiantes universitarios usan ChatGPT para mejorar su escritura académica?* y **Buscar evidencia** | Primero se valida la consulta (no se aceptan pedidos de "redacta mi introducción" ni consultas ajenas al tema). Después se busca solo en el corpus del tema, que son las referencias de acceso abierto del artículo O1. Tarda uno o dos minutos. |
| 1:30 | Mientras busca, **Volver al panel del caso** (la búsqueda sigue en el servidor), **Verificar las referencias de su borrador** y luego **Verificar las referencias** | Cada referencia se comprueba en Crossref y OpenAlex, sin modelo de lenguaje. El estado lo decide el sistema, no la IA. |
| 2:00 | Recorra el informe | [1] a [3] están **verificadas**. [4] tiene el **año** equivocado. [5] **no se localiza**: está inventada. [6] usa el **DOI de otra obra**. [7] está en la lista, pero no se cita. El texto cita **[8]**, que no está en la lista. Si un servicio no responde, la referencia queda "no comprobable", nunca "inexistente". |
| 3:00 | **Volver al panel del caso**: en **Sus solicitudes**, la búsqueda de evidencia ya figura como Entregada. Clic en **Ver resultado** | El panel guarda cada búsqueda y verificación para volver a abrirla. Cada afirmación cita fragmentos (F1, F2...). Al desplegar una cita se ve el texto exacto, el documento, la sección, las páginas y el enlace de acceso abierto. Las **fuentes recomendadas** son solo de acceso abierto comprobado, y la referencia la arma el sistema, no el modelo. |
| 3:30 | **Volver al panel del caso** → **Revisar la estructura de una sección**, elija **1. Introducción** y **Revisar la sección** (unos 20 s) | El agente de estructura diagnostica con las guías del programa: hallazgos por severidad, con ubicación, qué revisar y el criterio de la guía desplegable. No reescribe: si una recomendación se alarga, la verificación la marca. |
| 4:00 | Pregunta de cierre: *Redacta la introducción completa de mi artículo* | Se rechaza con el motivo y un ejemplo de lo que sí se puede pedir. El asistente no escribe por el estudiante. |
| 4:30 | (Opcional) Una consulta sin evidencia en el corpus | Si la evidencia no alcanza, el sistema se abstiene ("Sin evidencia suficiente") en lugar de inventar. |

## Qué decir si preguntan

- **¿De dónde sale la evidencia?** De 69 artículos de acceso abierto del tema, segmentados e indexados con búsqueda híbrida (vectorial y léxica) y reordenados.
- **¿Puede inventar referencias?** No. El modelo solo cita identificadores de fragmentos recuperados, y las referencias se arman con los metadatos guardados. Si cita algo fuera de lo recuperado, la respuesta va "Con advertencias".
- **¿Qué falta?** Los agentes de estructura, metodología y redacción (D1 a D3), el orquestador, el historial de solicitudes y las mediciones finales. Ver ESTADO, apartado 24.
