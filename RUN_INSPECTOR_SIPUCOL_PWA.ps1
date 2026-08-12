$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$App = Join-Path $Root "app"
$Url = "http://127.0.0.1:4173/"

function Test-LocalPort {
    param(
        [Parameter(Mandatory)]
        [int]$Port
    )

    $Connection = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue

    return [bool]$Connection
}

if (-not (Test-Path -LiteralPath $App)) {
    throw "No existe la carpeta app del proyecto."
}

if (-not (Test-LocalPort -Port 8000)) {
    Write-Host "Iniciando backend..." -ForegroundColor Cyan

    Start-Process `
        -FilePath "py.exe" `
        -WorkingDirectory $App `
        -ArgumentList @(
            "-m",
            "uvicorn",
            "backend.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--no-access-log"
        )

    Start-Sleep -Seconds 3
}
else {
    Write-Host "BACKEND_ACTIVO=OK" -ForegroundColor Green
}

if (-not (Test-LocalPort -Port 4173)) {
    Write-Host "Iniciando PWA..." -ForegroundColor Cyan

    Start-Process `
        -FilePath "cmd.exe" `
        -WorkingDirectory $App `
        -ArgumentList @(
            "/k",
            "npm.cmd run preview -- --host 127.0.0.1 --port 4173 --strictPort"
        )
}
else {
    Write-Host "PWA_ACTIVA=OK" -ForegroundColor Green
}

$PwaReady = $false

for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
    if (Test-LocalPort -Port 4173) {
        $PwaReady = $true
        break
    }

    Start-Sleep -Milliseconds 500
}

if (-not $PwaReady) {
    throw "La PWA no inició en el puerto 4173."
}

Start-Process $Url

Write-Host ""
Write-Host "PWA_ABIERTA=OK" -ForegroundColor Green
Write-Host "DIRECCION=$Url" -ForegroundColor Green