<#
.SYNOPSIS
Levanta el prototipo navegable con el corpus provisional y los datos de demostración.

.DESCRIPTION
A diferencia de scripts\demo.ps1 (API sobre una base vacía, para el asesor), este usa la
base de desarrollo con el corpus provisional, para que la búsqueda de evidencia funcione.

1. Levanta los servicios compartidos (GROBID y el servicio de modelos).
2. Levanta la base de desarrollo, la API unida a los servicios compartidos y la interfaz en
   http://127.0.0.1:5173. Al arrancar, la API aplica las migraciones pendientes.
3. Prepara las cuentas INV-DEMO y DEMO-01-1 (caso del tema TEMA-1-IA-EDUCACION) con
   contraseñas nuevas, que se guardan solo en datos\demo\credenciales.txt (fuera de Git).
   No se imprimen.
4. Genera docs\demo\borrador-demostracion.docx si no existe.

Requiere .env con CORREO_POLITE, CLAVE_OPENALEX y CLAVE_GROQ, el corpus provisional cargado
en la base de desarrollo y los pesos del servicio de modelos descargados (README).
Detener: docker compose -f docker-compose.yml -f docker-compose.corpus.yml -f docker-compose.demo.yml --profile interfaz down
#>
$ErrorActionPreference = "Continue"  # docker escribe sus avances en stderr
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz
$Compose = @("-f", "docker-compose.yml", "-f", "docker-compose.corpus.yml", "-f", "docker-compose.demo.yml", "--profile", "interfaz")

Write-Host "1/4 Servicios compartidos (GROBID y modelos)..."
docker compose -f compartido/docker-compose.yml up -d --wait 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "No se pudieron levantar los servicios compartidos." }

Write-Host "2/4 Base, API e interfaz (la primera vez tarda unos minutos)..."
docker compose @Compose up -d --wait --build bd api interfaz 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "No se pudo levantar el prototipo: revise 'docker compose logs api'." }

Write-Host "3/4 Cuentas de demostración..."
New-Item -ItemType Directory -Force "datos/demo" | Out-Null
docker compose @Compose run --rm --no-deps -v "${Raiz}/datos/demo:/demo" api python -m app.bd.demo --credenciales /demo/credenciales.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "No se pudieron preparar las cuentas de demostración." }

Write-Host "    Guías del programa (provisionales)..."
docker compose @Compose run --rm --no-deps api python -m app.corpus.guias --investigador INV-DEMO --carpeta guias/provisionales --aplicar 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "No se pudieron indexar las guías." }

Write-Host "4/4 Borrador de demostración..."
if (-not (Test-Path "docs/demo/borrador-demostracion.docx")) {
    & backend/.venv/Scripts/python.exe scripts/generar_borrador_demo.py
}

Write-Host ""
Write-Host "Listo. Abra http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Cuentas y contraseñas: datos\demo\credenciales.txt"
Write-Host "Borrador para cargar: docs\demo\borrador-demostracion.docx"
Write-Host "Guion de 5 minutos: docs\demo\guion-prototipo.md"
