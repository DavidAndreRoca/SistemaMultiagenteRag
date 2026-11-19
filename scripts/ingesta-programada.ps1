<#
.SYNOPSIS
Ingesta del corpus provisional completo y respaldo, para una ejecución programada (T10).

.DESCRIPTION
El corpus completo (unas 2 500 páginas) tarda horas en un portátil: no se usa en el día a
día. Este guion lo ingiere de punta a punta, sin intervención, y deja un respaldo que
luego se restaura en minutos con scripts/respaldo_corpus.py.

* Reanudable: si se interrumpe (apagado, Ctrl+C), la próxima ejecución continúa donde
  quedó; lo ya ingerido no se repite.
* Requiere los servicios compartidos (GROBID y modelos) y la API unida a ellos:
    docker compose -f compartido/docker-compose.yml up -d --wait
    docker compose -f docker-compose.yml -f docker-compose.corpus.yml up -d --wait bd api
* Deja el registro en datos/corpus-provisional/ingesta-AAAAMMDD-HHMM.log.

Programarlo (no lo hace este guion): en Windows, el Programador de tareas con la acción
  powershell.exe -NoProfile -File "<repositorio>\scripts\ingesta-programada.ps1"
por ejemplo de noche; en el servidor Linux, una entrada de cron con el equivalente en
docker compose.

.PARAMETER Investigador
Cuenta A2 que figura como autora de la ingesta.
#>
param([string]$Investigador = "INV-DEV")

# "Continue": en PowerShell 5.1, con "Stop" la primera línea de stderr de Docker (2>&1)
# detendría el guion aunque el comando termine bien. El resultado se juzga por $LASTEXITCODE.
$ErrorActionPreference = "Continue"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz
$Compose = @("-f", "docker-compose.yml", "-f", "docker-compose.corpus.yml")
$Temas = [ordered]@{
    "tema-1-ia-educacion"                 = "TEMA-1-IA-EDUCACION"
    "tema-2-transformacion-digital-mypes" = "TEMA-2-TRANSFORMACION-DIGITAL-MYPES"
}
$Registro = Join-Path $Raiz ("datos\corpus-provisional\ingesta-{0:yyyyMMdd-HHmm}.log" -f (Get-Date))

function Escribir([string]$Texto) {
    $Texto | Tee-Object -FilePath $Registro -Append
}

Escribir "Ingesta programada del corpus provisional: $(Get-Date -Format s)"
$fallos = 0
foreach ($carpeta in $Temas.Keys) {
    $origen = Join-Path $Raiz "datos\corpus-provisional\$carpeta"
    Escribir "== $($Temas[$carpeta])"
    docker compose @Compose run --rm --no-deps -v "${origen}:/entrada:ro" api `
        python -m app.corpus.ingesta /entrada --tema $Temas[$carpeta] --investigador $Investigador 2>&1 |
        Where-Object { $_ -notmatch '"nivel"|Loading weights|it/s\]|^\s*$' } |
        ForEach-Object { Escribir "$_" }
    if ($LASTEXITCODE -ne 0) { $fallos++ }
}
if ($fallos -eq 0) {
    Escribir "== Respaldo"
    $Python = Join-Path $Raiz "backend\.venv\Scripts\python.exe"
    if (-not (Test-Path $Python)) { $Python = "python" }
    & $Python scripts/respaldo_corpus.py respaldar --nombre ("corpus-provisional-{0:yyyyMMdd}" -f (Get-Date)) 2>&1 |
        ForEach-Object { Escribir "$_" }
    if ($LASTEXITCODE -ne 0) { Escribir "El respaldo falló." }
} else {
    Escribir "Hubo $fallos temas con errores: no se respalda. Vuelva a ejecutar para reintentar."
}
Escribir "Fin: $(Get-Date -Format s)"
