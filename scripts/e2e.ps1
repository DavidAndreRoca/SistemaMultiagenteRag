<#
.SYNOPSIS
Pruebas de extremo a extremo de la interfaz (T13) en un proyecto de Compose aislado.

.DESCRIPTION
1. Levanta la base y la API en el proyecto "sma_e2e" (puertos 8030 y 5437), con la base vacía.
2. Crea una cuenta de investigador de prueba. Su contraseña inicial no se imprime: pasa a
   Playwright en un archivo temporal que se borra al terminar.
3. Ejecuta Playwright (imagen oficial, misma versión que package.json) contra la interfaz
   compilada, que reenvía /api a la API.
4. Detiene el proyecto y borra su base.

Requiere las dependencias del frontend instaladas (ver README, "Interfaz").
#>
$ErrorActionPreference = "Continue"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz
$env:PUERTO_API = "8030"
$env:PUERTO_BD = "5437"
$Compose = @("-p", "sma_e2e", "-f", "docker-compose.yml")
$Imagen = "mcr.microsoft.com/playwright:v1.65.0-noble"

docker compose @Compose down -v --remove-orphans 2>&1 | Out-Null
docker compose @Compose up -d --wait --build bd api 2>&1 | Select-Object -Last 2
if ($LASTEXITCODE -ne 0) { throw "No se pudo levantar la API de pruebas." }

$codigo = "INV-E2E-" + [guid]::NewGuid().ToString("N").Substring(0, 6).ToUpper()
$salida = docker compose @Compose run --rm --no-deps api python -m app.seguridad.crear_investigador $codigo 2>$null | Out-String
# Sin la "ñ" de "Contraseña": PowerShell 5.1 puede decodificar mal la salida de Docker.
if ($salida -notmatch "inicial \(se muestra una sola vez\): (\S+)") {
    docker compose @Compose down -v 2>&1 | Out-Null
    throw "No se pudo crear la cuenta de investigador de prueba."
}
$temporal = New-TemporaryFile
try {
    "E2E_INVESTIGADOR=$codigo", "E2E_CONTRASENA_INVESTIGADOR=$($Matches[1])", "URL_API=http://api:8000" |
        Set-Content -Encoding ascii $temporal
    $Matches = $null
    docker run --rm --network sma_e2e_default --env-file $temporal -v "${Raiz}:/repo" -w /repo/frontend $Imagen npx playwright test
    $resultado = $LASTEXITCODE
}
finally {
    Remove-Item $temporal -ErrorAction SilentlyContinue
    docker compose @Compose down -v --remove-orphans 2>&1 | Out-Null
}
"Pruebas de extremo a extremo: " + ($(if ($resultado -eq 0) { "superadas" } else { "con fallos (ver frontend/playwright-report)" }))
exit $resultado
