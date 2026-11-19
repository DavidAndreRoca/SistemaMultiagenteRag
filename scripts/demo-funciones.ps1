# Funciones de apoyo para la demostración (Windows PowerShell 5.1 y PowerShell 7).
# Se cargan con:  . .\scripts\demo-funciones.ps1
#
# Usan System.Net.Http directamente porque:
#  * las cookies de sesión llevan el atributo Secure y PowerShell no las reenvía por
#    http://localhost; aquí se envían a mano en la cabecera Cookie;
#  * así se leen igual las respuestas de error (401, 403, 409, 422) y el texto en UTF-8.
# Nunca imprimen contraseñas ni tokens.

Add-Type -AssemblyName System.Net.Http

$script:DemoApi = 'http://localhost:8000'
$script:DemoModelos = 'http://localhost:8001'
$script:DemoGrobid = 'http://localhost:8070'
$script:DemoCarpeta = Join-Path $HOME 'sma-demo'
$script:DemoCredenciales = Join-Path $script:DemoCarpeta 'credenciales.json'
$script:DemoSesiones = @{}

$manejador = New-Object System.Net.Http.HttpClientHandler
$manejador.UseCookies = $false
$script:DemoHttp = New-Object System.Net.Http.HttpClient($manejador)
$script:DemoHttp.Timeout = [TimeSpan]::FromMinutes(10)

function Invoke-DemoHttp {
    param(
        [Parameter(Mandatory)] [string] $Metodo,
        [Parameter(Mandatory)] [string] $Url,
        $Cuerpo = $null,
        [hashtable] $Cabeceras = @{},
        [string] $ArchivoPdf = ''
    )
    $peticion = New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::new($Metodo), $Url)
    foreach ($nombre in $Cabeceras.Keys) {
        [void] $peticion.Headers.TryAddWithoutValidation($nombre, [string] $Cabeceras[$nombre])
    }
    if ($ArchivoPdf) {
        $formulario = New-Object System.Net.Http.MultipartFormDataContent
        $bytes = [System.IO.File]::ReadAllBytes($ArchivoPdf)
        $archivo = New-Object System.Net.Http.ByteArrayContent(, $bytes)
        $archivo.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/pdf')
        $formulario.Add($archivo, 'input', [System.IO.Path]::GetFileName($ArchivoPdf))
        $peticion.Content = $formulario
    }
    elseif ($null -ne $Cuerpo) {
        $json = $Cuerpo | ConvertTo-Json -Depth 10 -Compress
        $peticion.Content = New-Object System.Net.Http.StringContent($json, [System.Text.Encoding]::UTF8, 'application/json')
    }
    $respuesta = $script:DemoHttp.SendAsync($peticion).GetAwaiter().GetResult()
    $bytes = $respuesta.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
    $texto = [System.Text.Encoding]::UTF8.GetString($bytes)
    $datos = $texto
    if ($respuesta.Content.Headers.ContentType -and $respuesta.Content.Headers.ContentType.MediaType -eq 'application/json') {
        $datos = $texto | ConvertFrom-Json
    }
    $cookies = @()
    $valores = $null
    if ($respuesta.Headers.TryGetValues('Set-Cookie', [ref] $valores)) { $cookies = @($valores) }
    [pscustomobject] @{ Estado = [int] $respuesta.StatusCode; Datos = $datos; Texto = $texto; Cookies = $cookies }
}

function Get-DemoCredenciales {
    if (-not (Test-Path $script:DemoCredenciales)) {
        throw "No existe $($script:DemoCredenciales). Ejecute antes .\scripts\demo.ps1"
    }
    Get-Content -Raw -Encoding UTF8 $script:DemoCredenciales | ConvertFrom-Json
}

function Enter-DemoSesion {
    <# Inicia sesión y guarda la cookie y el valor CSRF de esa cuenta. #>
    param(
        [Parameter(Mandatory)] [string] $Cuenta,
        [string] $Contrasena = ''
    )
    if (-not $Contrasena) { $Contrasena = (Get-DemoCredenciales).cuentas.$Cuenta }
    $r = Invoke-DemoHttp POST "$($script:DemoApi)/sesion" @{ codigo = $Cuenta; contrasena = $Contrasena }
    if ($r.Estado -ne 200) { return $r }
    $partes = foreach ($c in $r.Cookies) { ($c -split ';')[0] }
    $script:DemoSesiones[$Cuenta] = @{ Cookie = ($partes -join '; '); Csrf = $r.Datos.csrf }
    $r
}

function Invoke-DemoApi {
    <# Llama a la API como la cuenta indicada; añade la cookie y la cabecera X-CSRF-Token. #>
    param(
        [Parameter(Mandatory)] [string] $Metodo,
        [Parameter(Mandatory)] [string] $Ruta,
        $Cuerpo = $null,
        [string] $Como = ''
    )
    $cabeceras = @{}
    if ($Como) {
        $sesion = $script:DemoSesiones[$Como]
        if (-not $sesion) { throw "Primero: Enter-DemoSesion $Como" }
        $cabeceras['Cookie'] = $sesion.Cookie
        $cabeceras['X-CSRF-Token'] = $sesion.Csrf
    }
    Invoke-DemoHttp $Metodo "$($script:DemoApi)$Ruta" $Cuerpo $cabeceras
}

function Show-DemoRespuesta {
    <# Muestra el código HTTP y el cuerpo, ocultando contraseñas y valores CSRF. #>
    param([Parameter(Mandatory, ValueFromPipeline)] $Respuesta)
    process {
        Write-Host ("HTTP {0}" -f $Respuesta.Estado) -ForegroundColor Cyan
        $datos = $Respuesta.Datos
        if ($datos -is [string]) { Write-Host $datos; return }
        $copia = $datos | ConvertTo-Json -Depth 10 | ConvertFrom-Json
        if ($copia.PSObject.Properties.Name -contains 'csrf') { $copia.csrf = '(oculto)' }
        if ($copia.PSObject.Properties.Name -contains 'credenciales') {
            foreach ($c in $copia.credenciales) { $c.contrasena_inicial = '(oculta)' }
        }
        Write-Host ($copia | ConvertTo-Json -Depth 10)
    }
}

function New-DemoPdf {
    <# PDF ficticio de una página con texto (fuente Helvetica), sin herramientas externas. #>
    param([Parameter(Mandatory)] [string] $Ruta)
    $lineas = @(
        @(15, 'Ansiedad ante los examenes y rendimiento academico'),
        @(15, 'en estudiantes universitarios de Ica'),
        @(11, 'Maria Quispe Torres y Jose Ramos Huaman'),
        @(10, 'Universidad Ficticia del Sur, Ica, Peru'),
        @(11, 'Resumen'),
        @(10, 'Este articulo ficticio analiza la relacion entre la ansiedad y el rendimiento.'),
        @(11, '1. Introduccion'),
        @(10, 'La ansiedad ante los examenes es frecuente en la educacion superior.')
    )
    $y = 760
    $flujo = New-Object System.Text.StringBuilder
    [void] $flujo.Append("BT`n")
    foreach ($l in $lineas) {
        [void] $flujo.Append(("/F1 {0} Tf 1 0 0 1 60 {1} Tm ({2}) Tj`n" -f $l[0], $y, $l[1]))
        $y -= 26
    }
    [void] $flujo.Append('ET')
    $contenido = $flujo.ToString()
    $objetos = @(
        '<< /Type /Catalog /Pages 2 0 R >>',
        '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        ("<< /Length {0} >>`nstream`n{1}`nendstream" -f $contenido.Length, $contenido)
    )
    $salida = New-Object System.Text.StringBuilder
    [void] $salida.Append("%PDF-1.4`n")
    $posiciones = @()
    for ($i = 0; $i -lt $objetos.Count; $i++) {
        $posiciones += $salida.Length
        [void] $salida.Append(("{0} 0 obj`n{1}`nendobj`n" -f ($i + 1), $objetos[$i]))
    }
    $xref = $salida.Length
    [void] $salida.Append(("xref`n0 {0}`n0000000000 65535 f `n" -f ($objetos.Count + 1)))
    foreach ($p in $posiciones) { [void] $salida.Append(("{0:D10} 00000 n `n" -f $p)) }
    [void] $salida.Append(("trailer`n<< /Size {0} /Root 1 0 R >>`nstartxref`n{1}`n%%EOF`n" -f ($objetos.Count + 1), $xref))
    [System.IO.File]::WriteAllBytes($Ruta, [System.Text.Encoding]::ASCII.GetBytes($salida.ToString()))
}

function New-DemoContrasena {
    <# Contraseña aleatoria de 24 caracteres (criptográfica), solo letras y números. #>
    $alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    $bytes = New-Object byte[] 24
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    -join ($bytes | ForEach-Object { $alfabeto[$_ % $alfabeto.Length] })
}
