# Apaga la demostración: la base y la API de "sma_demo" y los servicios compartidos.
#
#   powershell -ExecutionPolicy Bypass -File .\scripts\demo-detener.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\demo-detener.ps1 -BorrarBase
#
# No borra el volumen de modelos (sma_modelos, unos 4,6 GB): la próxima demostración no
# vuelve a descargarlos. Con -BorrarBase borra también la base de la demostración
# (demo.ps1 la recrea vacía de todos modos). Su proyecto de desarrollo no se toca.

param([switch] $BorrarBase)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$env:COMPOSE_PROJECT_NAME = 'sma_demo'  # nunca el proyecto de desarrollo del .env

function Invoke-DockerSilencioso {
    # Función simple con $args: en una función avanzada PowerShell se quedaría con
    # "-p" y "-v" (-PipelineVariable y -Verbose) y no llegarían a docker.
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $salida = & docker @args 2>&1 | ForEach-Object { "$_" }
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = $anterior
    if ($codigo -ne 0) { $salida | Select-Object -Last 10 | ForEach-Object { Write-Host $_ }; throw "Falló: docker $($args -join ' ')" }
}

if ($BorrarBase) {
    Invoke-DockerSilencioso compose -p sma_demo down -v --remove-orphans
    Write-Host 'Base y API de la demostración detenidas; base borrada.'
}
else {
    Invoke-DockerSilencioso compose -p sma_demo down --remove-orphans
    Write-Host 'Base y API de la demostración detenidas (la base se conserva).'
}
# Sin -v: el volumen sma_modelos se conserva.
Invoke-DockerSilencioso compose -p sma_compartido -f compartido/docker-compose.yml down
Write-Host 'GROBID y servicio de modelos detenidos. El volumen de modelos sma_modelos se conserva.'
