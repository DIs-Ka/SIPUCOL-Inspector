param(
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

# La ruta se obtiene desde este mismo archivo.
# No existe ninguna ruta fija hacia SIPUCOL 100 MILLONES.
$ProjectRoot = $PSScriptRoot

Set-Location -LiteralPath $ProjectRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "INSPECTOR SIPUCOL" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proyecto: $ProjectRoot"
Write-Host ""

if (-not (Test-Path ".\package.json")) {
    Write-Host "ERROR: no se encontró package.json." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".\backend\server.py")) {
    Write-Host "ERROR: no se encontró backend\server.py." -ForegroundColor Red
    exit 1
}

Write-Host "Probando backend de Inspector Sipucol..."

py -c "from backend import server; print('OK backend.server'); print('MOTOR_PDF=' + server.convertir_excel_seleccionado_job.__module__)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: el backend de Inspector Sipucol no cargó." -ForegroundColor Red
    exit $LASTEXITCODE
}

$TrackerPath = Join-Path $ProjectRoot "backend\template_tracker.json"

if (Test-Path $TrackerPath) {
    py -c "import json, pathlib; p=pathlib.Path(r'$TrackerPath'); d=json.loads(p.read_text(encoding='utf-8')); hojas=d.get('sheets') or d.get('hojas') or []; filas=d.get('rows') or d.get('filas') or []; print('Tracker disponible: OK'); print('Hojas trackeadas:', len(hojas) if isinstance(hojas, list) else len(hojas.keys()) if isinstance(hojas, dict) else 'disponible'); print('Filas trackeadas:', len(filas) if isinstance(filas, list) else len(filas.keys()) if isinstance(filas, dict) else 'disponible')"
}

$ProductRoot = Split-Path -Parent $ProjectRoot
$RuntimeFile = Join-Path $ProductRoot "docs\RUNTIME_ACTIVO.txt"

@"
INSPECTOR SIPUCOL - RUNTIME ACTIVO
Fecha: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Proyecto: $ProjectRoot
Motor esperado: backend.pdf_clean_final_override
"@ | Set-Content -LiteralPath $RuntimeFile -Encoding UTF8

Write-Host ""
Write-Host "RUNTIME_PATH=$ProjectRoot" -ForegroundColor Green
Write-Host "RUNTIME_MARKER=$RuntimeFile" -ForegroundColor Green

if ($VerifyOnly) {
    Write-Host "RUNTIME_INSPECTOR_SIPUCOL=OK" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Iniciando Inspector Sipucol..."
Write-Host "Abre: http://127.0.0.1:5173/"
Write-Host ""

npm run dev:full
