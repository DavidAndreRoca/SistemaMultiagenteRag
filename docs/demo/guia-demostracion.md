# Guía de la demostración del avance

Para mostrar al asesor lo construido hasta T08:
- La API con sesiones y aislamiento por caso.
- El modelo de datos y las normas de citación.
- GROBID y el servicio de modelos de embeddings.

Todos los datos son ficticios.

Cada paso indica qué hacer, qué se debe ver y **qué se obtuvo** en el ensayo completo del 6 de noviembre de 2026. El ensayo partió de un estado limpio: sin base de la demostración, sin servicios compartidos y sin pesos de modelos descargados. Se hizo en Windows 11 con Docker Desktop (amd64, 8 GB para Docker) y Windows PowerShell 5.1.

## 0. Preparación (unos 5 minutos la primera vez y poco más de 1 minuto las siguientes)

**Requisitos:**
- Docker Desktop en marcha.
- El archivo `.env` en la raíz del repositorio (copia de `.env.example` con `SECRETO_SESION` y `CORREO_POLITE`).
- Los puertos 8000, 8001, 8070 y 5434 libres.
- Unos 7 GB de memoria disponibles para Docker.

Si tiene levantado su proyecto de desarrollo, detenga su API, que también usa el puerto 8000:

```powershell
docker compose stop api
```

Desde la raíz del repositorio, en PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
```

El script, sin mostrar ninguna contraseña:
1. Levanta GROBID y el servicio de modelos. Descarga y verifica los pesos (4,6 GB) solo si faltan.
2. Crea la base y la API de la demostración en el proyecto `sma_demo`. Su base de desarrollo no se toca.
3. Aplica las migraciones y carga las semillas.
4. Deja lista la cuenta `INV-DEMO` y los casos `DEMO-A` y `DEMO-B`, con las cuentas `DEMO-A-1` y `DEMO-B-1`, todas con la contraseña inicial ya cambiada.
5. Guarda las contraseñas en `%USERPROFILE%\sma-demo\credenciales.json`, fuera del repositorio, y deja un PDF ficticio en la misma carpeta.
6. Comprueba la API, GROBID y el servicio de modelos.

**Resultado obtenido:**
- Desde el estado limpio, con su base de desarrollo en marcha en el puerto 5432, terminó en 266 s, descarga incluida, con código de salida 0.
- La base de desarrollo no cambió: tenía 12 cuentas antes y 12 después.
- Una segunda ejecución seguida tardó 74 s.

Las últimas líneas fueron:

```text
== Cuentas de la demostración
   INV-DEMO lista (contraseña inicial cambiada)
   DEMO-A-1 lista (contraseña inicial cambiada)
   DEMO-B-1 lista (contraseña inicial cambiada)
== Credenciales y PDF ficticio
   Credenciales: C:\Users\USUARIO\sma-demo\credenciales.json
   PDF ficticio: C:\Users\USUARIO\sma-demo\articulo-ficticio.pdf
== Comprobaciones
   API /salud: ok (base de datos True, pgvector 0.8.7)
   GROBID: sano
   Servicio de modelos: sano (BAAI/bge-m3 y BAAI/bge-reranker-v2-m3)
```

Si se vuelve a ejecutar, la base de la demostración se recrea vacía y las contraseñas cambian.

### Terminal para los pasos con PowerShell

Abra una ventana de PowerShell en la raíz del repositorio y cargue las funciones de apoyo una sola vez:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

```powershell
. .\scripts\demo-funciones.ps1
```

| Función | Qué hace |
| --- | --- |
| `Enter-DemoSesion CUENTA` | Inicia sesión con la contraseña del archivo de credenciales |
| `Invoke-DemoApi METODO RUTA CUERPO -Como CUENTA` | Envía la cookie y la cabecera `X-CSRF-Token` de esa cuenta |
| `Show-DemoRespuesta` | Muestra el código HTTP y el cuerpo, con las contraseñas y el valor CSRF ocultos |

### Cómo iniciar sesión en `/docs` y enviar la cabecera CSRF

Use Chrome o Edge en `http://localhost:8000/docs`. Las cookies de sesión llevan el atributo `Secure`, y estos navegadores las aceptan en `localhost`.

1. Copie la contraseña al portapapeles sin mostrarla en pantalla:

   ```powershell
   (Get-Content $HOME\sma-demo\credenciales.json | ConvertFrom-Json).cuentas.'INV-DEMO' | Set-Clipboard
   ```

2. En `/docs`, abra **sesion > POST /sesion**, pulse **Try it out** y escriba el cuerpo. Pegue la contraseña donde dice `pegue-aquí`:

   ```json
   {"codigo": "INV-DEMO", "contrasena": "pegue-aquí"}
   ```

   Pulse **Execute**. Debe ver **200** con `"debe_cambiar_contrasena": false` y un valor `csrf`. El navegador guarda las cookies `sma_sesion` y `sma_csrf`.
3. Las rutas **GET** (por ejemplo, `GET /investigador/casos`) ya funcionan con **Try it out**.
4. Las rutas que **modifican datos** (POST, PUT, DELETE) exigen la cabecera `X-CSRF-Token`. La pantalla de `/docs` no tiene un campo para ella, porque la API no la declara en su contrato. Para que `/docs` la envíe sola, pulse **F12**, vaya a la pestaña **Consola**, pegue esto y pulse Enter:

   ```javascript
   const fetchOriginal = window.fetch;
   window.fetch = (url, opciones = {}) => {
     const valor = (document.cookie.match(/(?:^|; )sma_csrf=([^;]*)/) || [])[1];
     if (valor) {
       opciones.headers = new Headers(opciones.headers || {});
       opciones.headers.set('X-CSRF-Token', decodeURIComponent(valor));
     }
     return fetchOriginal(url, opciones);
   };
   ```

   Desde ese momento, cada **Execute** de `/docs` lleva la cabecera con el valor de la cookie `sma_csrf`. Si recarga la página, debe pegarlo de nuevo. Si en la consola aparece un aviso de seguridad sobre pegar código, escriba lo que pida (en Chrome, `allow pasting`).

   **Ensayo:** se comprobó en el navegador integrado de desarrollo (Chromium) que, con este fragmento, **Execute** envía `X-CSRF-Token` con el valor de la cookie `sma_csrf`. La prueba usó un valor ficticio y una petición sin sesión, que respondió `sesion_invalida`, como corresponde. El inicio de sesión real desde `/docs` no se ensayó: el asistente no escribe contraseñas en el navegador. Todos los resultados de los pasos 3 y 4 se obtuvieron con los comandos de PowerShell. Pruebe el inicio de sesión en `/docs` antes de la reunión; si algo no responde como se describe, use PowerShell.
5. Para cambiar de cuenta, inicie sesión otra vez en **POST /sesion**: las cookies nuevas reemplazan a las anteriores. Para salir, use **DELETE /sesion**.

Si algo de `/docs` se complica durante la demostración, use el comando de PowerShell de cada paso: hace lo mismo y en el ensayo dio los resultados que se anotan.

## 1. Suite de pruebas: total superado y cobertura

En la terminal, la suite de la API, con PostgreSQL real (unos 60 s):

```powershell
docker compose -p sma_demo run --rm --no-deps --build pruebas
```

Se debe ver al final el resumen de cobertura y el total de pruebas.

**Resultado obtenido:**

```text
TOTAL                                  1943     41    246     20    97%
Required test coverage of 70.0% reached. Total coverage: 97.12%
======================= 195 passed, 3 skipped in 57.59s ========================
```

Las 3 pruebas omitidas necesitan variables que apunten a GROBID y al servicio de modelos en marcha. Se ejecutan aparte (ver el paso 6, opcional).

La suite del servicio de modelos, sin los pesos (unos 10 s):

```powershell
docker compose -p sma_compartido -f compartido/docker-compose.yml --profile pruebas run --rm -e COVERAGE_FILE=/tmp/.coverage pruebas_modelos pytest -m "not modelos_locales" --cov -p no:cacheprovider
```

**Resultado obtenido:**

```text
TOTAL                      296      4     34      4    98%
Required test coverage of 70.0% reached. Total coverage: 97.58%
======================= 26 passed, 4 deselected in 1.05s =======================
```

En total: **221 pruebas superadas**, con cobertura del 97,12 % (API) y del 97,58 % (servicio de modelos); el mínimo exigido es 70 %.

## 2. Estado de la API: `/salud`

En el navegador, abra `http://localhost:8000/salud`.

**Se debe ver y se obtuvo:**

```json
{"estado":"ok","version":"0.1.0","base_de_datos":true,"extension_vector":"0.8.7"}
```

`extension_vector` es la versión de pgvector en la base.

## 3. Como investigador: tema, caso, código repetido (CP-22) y norma de citación

Inicie sesión como `INV-DEMO` en `/docs` y pegue el fragmento de la consola del apartado 0. Luego:

| # | En `/docs` | Cuerpo | Se debe ver |
| --- | --- | --- | --- |
| 3.1 | **POST /investigador/colecciones/cientificas** | `{"tema": "TEMA-ASESOR"}` | **201**: colección científica del tema |
| 3.2 | **POST /investigador/casos** | `{"codigo": "CASO-ASESOR-01", "tipo_autoria": "pareja", "tema": "TEMA-ASESOR"}` | **201**: el caso con dos cuentas y sus contraseñas iniciales, que se muestran una sola vez |
| 3.3 | **POST /investigador/casos** con el mismo código | `{"codigo": "CASO-ASESOR-01", "tipo_autoria": "individual", "tema": "TEMA-ASESOR"}` | **409** `codigo_repetido` (CP-22) |
| 3.4 | **PUT /investigador/casos/{codigo}/norma**, `codigo` = `CASO-ASESOR-01` | `{"norma": "APA7"}` | **200** con `"norma_citacion": "apa7"` |
| 3.5 | La misma ruta | `{"norma": "MLA"}` | **422** `norma_no_permitida` con la lista permitida |
| 3.6 | **GET /investigador/casos/{codigo}**, `codigo` = `CASO-ASESOR-01` | | **200** con el registro del cambio de norma |

La misma secuencia en PowerShell:

```powershell
Enter-DemoSesion INV-DEMO | Show-DemoRespuesta
Invoke-DemoApi POST /investigador/colecciones/cientificas @{ tema = 'TEMA-ASESOR' } -Como INV-DEMO | Show-DemoRespuesta
Invoke-DemoApi POST /investigador/casos @{ codigo = 'CASO-ASESOR-01'; tipo_autoria = 'pareja'; tema = 'TEMA-ASESOR' } -Como INV-DEMO | Show-DemoRespuesta
Invoke-DemoApi POST /investigador/casos @{ codigo = 'CASO-ASESOR-01'; tipo_autoria = 'individual'; tema = 'TEMA-ASESOR' } -Como INV-DEMO | Show-DemoRespuesta
Invoke-DemoApi PUT /investigador/casos/CASO-ASESOR-01/norma @{ norma = 'APA7' } -Como INV-DEMO | Show-DemoRespuesta
Invoke-DemoApi PUT /investigador/casos/CASO-ASESOR-01/norma @{ norma = 'MLA' } -Como INV-DEMO | Show-DemoRespuesta
Invoke-DemoApi GET /investigador/casos/CASO-ASESOR-01 -Como INV-DEMO | Show-DemoRespuesta
```

**Resultado obtenido** (PowerShell; contraseñas y CSRF ocultos):

| # | Respuesta |
| --- | --- |
| Sesión | `HTTP 200`, `"rol": "A2"`, `"debe_cambiar_contrasena": false` |
| 3.1 | `HTTP 201`, `{"tipo": "cientifica", "tema": "TEMA-ASESOR", "n_incluidas": 0, ...}` |
| 3.2 | `HTTP 201`, `"codigo": "CASO-ASESOR-01"`, `"tipo_autoria": "pareja"`, `"norma_citacion": "ieee"`, cuentas `CASO-ASESOR-01-1` y `CASO-ASESOR-01-2` |
| 3.3 | `HTTP 409`, `"codigo": "codigo_repetido"`, `"mensaje": "Ya existe un caso con el código CASO-ASESOR-01. Use otro código."` |
| 3.4 | `HTTP 200`, `"norma_citacion": "apa7"` (se escribió `APA7` y se guarda en minúsculas) |
| 3.5 | `HTTP 422`, `"codigo": "norma_no_permitida"`, `"mensaje": "La norma mla no está en la lista configurada."`, `"normas_permitidas": ["ieee", "apa7", "vancouver"]` |
| 3.6 | `HTTP 200`, `"cambios_norma": [{"norma_anterior": "ieee", "norma_nueva": "apa7", ...}]` |

Para repetir el paso 3 sin recrear todo, use otro tema y otro código, por ejemplo `TEMA-ASESOR-2` y `CASO-ASESOR-02`.

## 4. Como `DEMO-A`: intentar ver datos de `DEMO-B`

Inicie sesión como `DEMO-A-1` en `/docs`. Copie antes su contraseña con la línea del apartado 0, cambiando `'INV-DEMO'` por `'DEMO-A-1'`. Luego:

| # | En `/docs` | Se debe ver |
| --- | --- | --- |
| 4.1 | **GET /caso** | **200** con los datos de `DEMO-A` y nada más: un caso solo ve su propio caso |
| 4.2 | **GET /investigador/casos/{codigo}** con `DEMO-B` | **403** `sin_permiso` |
| 4.3 | **GET /investigador/casos** | **403** `sin_permiso` |

Además, en PowerShell, una modificación sin la cabecera CSRF se rechaza aunque la cookie sea válida.

```powershell
Enter-DemoSesion DEMO-A-1 | Show-DemoRespuesta
Invoke-DemoApi GET /caso -Como DEMO-A-1 | Show-DemoRespuesta
Invoke-DemoApi GET /investigador/casos/DEMO-B -Como DEMO-A-1 | Show-DemoRespuesta
Invoke-DemoApi GET /investigador/casos -Como DEMO-A-1 | Show-DemoRespuesta
Invoke-DemoHttp PUT "$DemoApi/investigador/casos/DEMO-B/norma" @{ norma = 'ieee' } @{ Cookie = $DemoSesiones['DEMO-A-1'].Cookie } | Show-DemoRespuesta
```

**Resultado obtenido:**

| # | Respuesta |
| --- | --- |
| Sesión | `HTTP 200`, `"rol": "A1"` |
| 4.1 | `HTTP 200`, `{"codigo": "DEMO-A", "tipo_autoria": "individual", "tema": "TEMA-DEMO", "norma_citacion": "ieee"}` |
| 4.2 | `HTTP 403`, `"codigo": "sin_permiso"` |
| 4.3 | `HTTP 403`, `"codigo": "sin_permiso"` |
| Sin CSRF | `HTTP 403`, `"codigo": "csrf_invalido"` |

**Por qué 403 y no 404.** Según el apartado 4.4 de la hoja de ruta, 403 significa "rol insuficiente" y 404 significa "recurso de otro caso", sin revelar que existe.
- `/investigador/casos/DEMO-B` es una **ruta de investigador**: todo el enrutador `/investigador` exige el rol A2. Una cuenta de caso (A1) recibe 403 por su rol, antes de que se lea el código. La respuesta es idéntica exista o no `DEMO-B`, así que no revela nada.
- La única **ruta de caso** actual, `GET /caso`, no recibe ningún identificador: toma el caso de la sesión. Hoy un caso no tiene forma de pedir un recurso de otro caso.
- La regla del 404 se aplicará cuando existan rutas de caso con identificadores de recursos (versiones del borrador desde T11, solicitudes y resultados después).

El aislamiento de fondo, dentro de la base, se demuestra con sus pruebas:

```powershell
docker compose -p sma_demo run --rm --no-deps pruebas pytest pruebas/integracion/test_repositorios.py pruebas/integracion/test_matriz_autorizacion.py -v -p no:cacheprovider --no-cov
```

**Resultado obtenido:** `12 passed`. Entre ellas:
- `test_un_caso_no_lee_ni_lista_datos_de_otro`
- `test_registros_hijos_tambien_quedan_aislados`
- `test_contexto_de_investigador_no_sirve_para_datos_de_caso`
- `test_matriz_de_autorizacion`, que recorre todas las rutas con cada rol y con otro caso.

## 5. GROBID: título y autores de un PDF ficticio

El PDF está en `%USERPROFILE%\sma-demo\articulo-ficticio.pdf`. Lo crea `demo.ps1` y es ficticio.

**En el navegador:**
1. Abra la consola propia de GROBID en `http://localhost:8070`.
2. Vaya a la pestaña **Process** y deje **Service to call** en **Process Header Document**.
3. Pulse **Select file**, elija el PDF y envíelo.

Se debe ver el TEI con el título y los dos autores.

**En PowerShell** (muestra solo el título y los autores):

```powershell
$t = Invoke-DemoHttp POST "$DemoGrobid/api/processHeaderDocument" -ArchivoPdf "$HOME\sma-demo\articulo-ficticio.pdf" -Cabeceras @{ Accept = 'application/xml' }
[xml] $tei = $t.Texto
$ns = New-Object System.Xml.XmlNamespaceManager($tei.NameTable); $ns.AddNamespace('t', 'http://www.tei-c.org/ns/1.0')
'Titulo: ' + $tei.SelectSingleNode('//t:titleStmt/t:title', $ns).InnerText
$tei.SelectNodes('//t:sourceDesc//t:author/t:persName', $ns) | ForEach-Object { 'Autor: ' + (($_.forename | ForEach-Object { $_.'#text' }) -join ' ') + ' ' + $_.surname }
```

**Resultado obtenido:**

```text
HTTP 200
Titulo: Ansiedad ante los examenes y rendimiento academico en estudiantes universitarios de Ica
Autor: Maria Quispe Torres
Autor: Jose Ramos Huaman
```

GROBID unió el título, que en el PDF ocupa dos líneas, y separó nombre y apellidos de cada autor. En T09 este servicio extraerá los metadatos de los artículos del corpus.

## 6. Servicio de modelos: el mismo texto da el mismo vector

**En el navegador:** el servicio tiene su propia página en `http://localhost:8001/docs`. En **POST /embeber**, pulse **Try it out** y envíe:

```json
{"textos": ["La prueba de Spearman se usa cuando los datos no siguen una distribución normal."]}
```

Se debe ver **200** con `"modelo": "BAAI/bge-m3"`, la revisión fija `5617a9f6...` y un vector de 1 024 números. Repita **Execute** y verá los mismos números. La comparación completa de los 1 024 valores es más clara en PowerShell.

**En PowerShell:**

```powershell
$texto = 'La prueba de Spearman se usa cuando los datos no siguen una distribución normal.'
$v1 = (Invoke-DemoHttp POST "$DemoModelos/embeber" @{ textos = @($texto) }).Datos
$v2 = (Invoke-DemoHttp POST "$DemoModelos/embeber" @{ textos = @($texto) }).Datos
$v3 = (Invoke-DemoHttp POST "$DemoModelos/embeber" @{ textos = @('Otro texto distinto y más largo, que acompaña en el mismo lote.', $texto) }).Datos
"Modelo: $($v1.modelo) @ $($v1.revision)"
"Dimension: $($v1.dimension)   Primeros valores: $(($v1.vectores[0][0..3] | ForEach-Object { '{0:N6}' -f $_ }) -join ', ')"
"Mismo vector en dos solicitudes: $(($v1.vectores[0] -join ',') -eq ($v2.vectores[0] -join ','))"
"Mismo vector dentro de un lote con otro texto: $(($v1.vectores[0] -join ',') -eq ($v3.vectores[1] -join ','))"
```

**Resultado obtenido:**

```text
Modelo: BAAI/bge-m3 @ 5617a9f61b028005a4858fdac845db406aefb181
Dimension: 1024   Primeros valores: -0.041431, 0.001230, -0.070823, 0.005095
Mismo vector en dos solicitudes: True
Mismo vector dentro de un lote con otro texto: True
```

La igualdad es exacta, bit a bit, incluso cuando el texto llega acompañado de otro. Es el criterio de T08, y se logra armando los lotes sin relleno (`docs/decisiones/T08-servicios-compartidos.md`).

**Opcional, si hay tiempo:** las pruebas de la API contra los servicios reales, que son las 3 omitidas en el paso 1. Desde `backend/`, con el entorno virtual de desarrollo:

```powershell
$env:URL_SERVICIO_MODELOS_PRUEBAS = 'http://127.0.0.1:8001'; $env:URL_GROBID_PRUEBAS = 'http://127.0.0.1:8070'; pytest -m servicios_compartidos -p no:cacheprovider
```

## 7. Al terminar

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\demo-detener.ps1
```

Apaga la base y la API de la demostración, GROBID y el servicio de modelos. **No borra el volumen de modelos** (`sma_modelos`), así que la próxima demostración no vuelve a descargar los 4,6 GB. Con `-BorrarBase` también borra la base de la demostración. Su proyecto de desarrollo no se toca; vuelva a levantar su API con `docker compose up -d api`.

`%USERPROFILE%\sma-demo\credenciales.json` contiene contraseñas de cuentas ficticias locales. No lo comparta ni lo suba al repositorio; bórrelo si ya no lo necesita.
