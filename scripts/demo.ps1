# Prepara la demostración del avance (Windows con Docker Desktop, amd64).
#
#   powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
#
# Qué hace, desde la raíz del repositorio:
#   1. Levanta los servicios compartidos (GROBID y servicio de modelos); descarga y
#      verifica los pesos si faltan.
#   2. Levanta una base y una API propias de la demostración (proyecto de Compose
#      "sma_demo", API en http://localhost:8000). La base de la demostración se
#      recrea vacía en cada ejecución; su proyecto de desarrollo no se toca.
#   3. Aplica las migraciones (servicio "migrar") y carga las semillas ficticias.
#   4. Crea la cuenta de investigador INV-DEMO y los casos ficticios DEMO-A y DEMO-B,
#      y cambia sus contraseñas iniciales.
#   5. Guarda las credenciales en %USERPROFILE%\sma-demo\credenciales.json (fuera del
#      repositorio) junto con un PDF ficticio para GROBID.
#   6. Comprueba que la API, GROBID y el servicio de modelos están sanos.
#
# No imprime contraseñas. Requiere el archivo .env de la raíz (copia de .env.example).

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
. (Join-Path $PSScriptRoot 'demo-funciones.ps1')

$Proyecto = 'sma_demo'
$Compartido = 'compartido/docker-compose.yml'
# Además de -p en cada comando: nunca se usa el proyecto de desarrollo del .env.
$env:COMPOSE_PROJECT_NAME = $Proyecto

function Write-Paso([string] $texto) { Write-Host "`n== $texto" -ForegroundColor Yellow }

function Invoke-Docker {
    # Ejecuta docker y falla si el comando falla. Devuelve la salida (no la imprime).
    # Función simple a propósito, con $args y sin [Parameter]: en una función avanzada
    # PowerShell tomaría "-p", "-d" y "-v" como sus parámetros comunes (-PipelineVariable,
    # -Debug, -Verbose) y no llegarían a docker.
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'  # docker escribe avances en stderr
    $salida = & docker @args 2>&1 | ForEach-Object { "$_" }
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = $anterior
    if ($codigo -ne 0) {
        $salida | Select-Object -Last 15 | ForEach-Object { Write-Host $_ }
        throw "Falló: docker $($args -join ' ')"
    }
    $salida
}

function Test-PuertoLibre([int] $puerto) {
    $uso = Invoke-Docker ps --filter "publish=$puerto" --format '{{.Names}}'
    $ajenos = @($uso | Where-Object { $_ -and $_ -notlike "$Proyecto-*" -and $_ -notlike 'sma_compartido-*' })
    if ($ajenos.Count -gt 0) {
        throw "El puerto $puerto lo usa el contenedor $($ajenos -join ', '). Deténgalo (por ejemplo, 'docker compose down' en su proyecto de desarrollo) y vuelva a ejecutar."
    }
}

# --- 0. Requisitos ---
Write-Paso 'Comprobando requisitos'
Invoke-Docker info --format '{{.ServerVersion}}' | Out-Null
if (-not (Test-Path '.env')) { throw 'Falta .env en la raíz: copie .env.example a .env y complete SECRETO_SESION y CORREO_POLITE.' }
if (-not (Test-Path 'compartido/.env')) { Copy-Item 'compartido/.env.example' 'compartido/.env' }
Test-PuertoLibre 8000
New-Item -ItemType Directory -Force $script:DemoCarpeta | Out-Null

# --- 1. Servicios compartidos ---
Write-Paso 'Servicios compartidos: pesos de los modelos (se descargan solo si faltan, unos 4,6 GB)'
Invoke-Docker compose -p sma_compartido -f $Compartido --profile descarga run --rm --build descargar_modelos |
    Where-Object { $_ -like 'Verificado*' -or $_ -like 'Descargando*' } | ForEach-Object { Write-Host "   $_" }
Write-Paso 'Servicios compartidos: GROBID y servicio de modelos'
Invoke-Docker compose -p sma_compartido -f $Compartido up -d --wait --build | Out-Null
Write-Host '   GROBID en :8070 y servicio de modelos en :8001 en marcha'

# --- 2 y 3. Base, migraciones, API y semillas de la demostración ---
Write-Paso "Base y API de la demostración (proyecto $Proyecto, base nueva)"
$env:PUERTO_API = '8000'
$env:PUERTO_BD = '5434'
Invoke-Docker compose -p $Proyecto down -v --remove-orphans | Out-Null
Invoke-Docker compose -p $Proyecto up -d --wait --build bd api | Out-Null
$propios = Invoke-Docker ps --filter "label=com.docker.compose.project=$Proyecto" --filter 'publish=8000' --format '{{.Names}}'
if (-not $propios) { throw "La API de :8000 no pertenece al proyecto $Proyecto; se detiene para no tocar otro proyecto." }
$version = Invoke-Docker compose -p $Proyecto run --rm --no-deps migrar alembic current
$cabeza = ($version | Where-Object { $_ -match '^\d{4} \(head\)' }) -join ''
if (-not $cabeza) { throw "Las migraciones no quedaron en la cabeza: $($version -join ' ')" }
Write-Host "   Migraciones aplicadas: $cabeza"
# Las semillas imprimen contraseñas iniciales de cuentas de desarrollo: se descartan.
Invoke-Docker compose -p $Proyecto run --rm --no-deps api python -m app.bd.semillas | Out-Null
Write-Host '   Semillas ficticias cargadas (INV-DEV, TEMA-DEV-01, CASO-DEV-01, CASO-DEV-02)'

# --- 4. Cuentas de la demostración ---
Write-Paso 'Cuentas de la demostración'
$credenciales = [ordered] @{}

function Set-ContrasenaDefinitiva([string] $cuenta, [string] $inicial) {
    $r = Enter-DemoSesion $cuenta $inicial
    if ($r.Estado -ne 200 -or -not $r.Datos.debe_cambiar_contrasena) { throw "No se pudo entrar como $cuenta (HTTP $($r.Estado))" }
    $nueva = New-DemoContrasena
    $c = Invoke-DemoApi POST '/sesion/contrasena' @{ contrasena_actual = $inicial; contrasena_nueva = $nueva } -Como $cuenta
    if ($c.Estado -ne 204) { throw "No se pudo cambiar la contraseña de $cuenta (HTTP $($c.Estado))" }
    $r = Enter-DemoSesion $cuenta $nueva
    if ($r.Estado -ne 200 -or $r.Datos.debe_cambiar_contrasena) { throw "La nueva contraseña de $cuenta no funcionó" }
    $credenciales[$cuenta] = $nueva
    Write-Host "   $cuenta lista (contraseña inicial cambiada)"
}

$salida = Invoke-Docker compose -p $Proyecto run --rm --no-deps api python -m app.seguridad.crear_investigador INV-DEMO
$linea = $salida | Where-Object { $_ -match 'inicial.*:\s*(\S+)\s*$' } | Select-Object -First 1
if (-not ($linea -match 'inicial.*:\s*(\S+)\s*$')) { throw 'No se obtuvo la contraseña inicial de INV-DEMO' }
Set-ContrasenaDefinitiva 'INV-DEMO' $Matches[1]

$r = Invoke-DemoApi POST '/investigador/colecciones/cientificas' @{ tema = 'TEMA-DEMO' } -Como 'INV-DEMO'
if ($r.Estado -ne 201) { throw "No se pudo crear TEMA-DEMO (HTTP $($r.Estado))" }
foreach ($codigo in 'DEMO-A', 'DEMO-B') {
    $r = Invoke-DemoApi POST '/investigador/casos' @{ codigo = $codigo; tipo_autoria = 'individual'; tema = 'TEMA-DEMO' } -Como 'INV-DEMO'
    if ($r.Estado -ne 201) { throw "No se pudo crear $codigo (HTTP $($r.Estado))" }
    $cuenta = $r.Datos.credenciales[0]
    Set-ContrasenaDefinitiva $cuenta.cuenta $cuenta.contrasena_inicial
}

# --- 5. Archivos fuera del repositorio ---
Write-Paso 'Credenciales y PDF ficticio'
$contenido = [ordered] @{
    nota = 'Credenciales ficticias de la demostración. No versionar. Se regeneran con scripts\demo.ps1.'
    api = $script:DemoApi
    cuentas = $credenciales
}
$json = $contenido | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($script:DemoCredenciales, $json, (New-Object System.Text.UTF8Encoding($false)))
New-DemoPdf (Join-Path $script:DemoCarpeta 'articulo-ficticio.pdf')
Write-Host "   Credenciales: $($script:DemoCredenciales)"
Write-Host "   PDF ficticio: $(Join-Path $script:DemoCarpeta 'articulo-ficticio.pdf')"

# --- 6. Comprobaciones finales ---
Write-Paso 'Comprobaciones'
$fallos = 0
$s = Invoke-DemoHttp GET "$($script:DemoApi)/salud"
if ($s.Estado -eq 200 -and $s.Datos.estado -eq 'ok') { Write-Host "   API /salud: ok (base de datos $($s.Datos.base_de_datos), pgvector $($s.Datos.extension_vector))" -ForegroundColor Green }
else { Write-Host "   API /salud: FALLA (HTTP $($s.Estado))" -ForegroundColor Red; $fallos++ }
$g = Invoke-DemoHttp GET "$($script:DemoGrobid)/api/isalive"
if ($g.Estado -eq 200 -and "$($g.Texto)".Trim() -eq 'true') { Write-Host '   GROBID: sano' -ForegroundColor Green }
else { Write-Host "   GROBID: FALLA (HTTP $($g.Estado))" -ForegroundColor Red; $fallos++ }
$m = Invoke-DemoHttp GET "$($script:DemoModelos)/salud"
if ($m.Estado -eq 200 -and $m.Datos.estado -eq 'ok') {
    $nombres = ($m.Datos.modelos | ForEach-Object { $_.modelo }) -join ' y '
    Write-Host "   Servicio de modelos: sano ($nombres)" -ForegroundColor Green
}
else { Write-Host "   Servicio de modelos: FALLA (HTTP $($m.Estado))" -ForegroundColor Red; $fallos++ }

if ($fallos -gt 0) { throw "$fallos comprobaciones fallaron" }
Write-Host "`nDemostración lista. Abra http://localhost:8000/docs y siga docs/demo/guia-demostracion.md." -ForegroundColor Green
Write-Host "Las contraseñas están en $($script:DemoCredenciales). Para apagar todo: .\scripts\demo-detener.ps1"
