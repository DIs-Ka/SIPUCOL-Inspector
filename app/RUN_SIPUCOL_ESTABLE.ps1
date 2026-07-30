$ErrorActionPreference = "Stop"

$Project = "C:\Users\Admin\OneDrive\Documentos\Zenith\2. Proyectos\2. SIPUCOL Autom\sipucol-inspector"
Set-Location $Project

Write-Host ""
Write-Host "=== SIPUCOL INSPECTOR V1 TRACKER ===" -ForegroundColor Cyan
Write-Host "Proyecto: $Project" -ForegroundColor DarkGray
Write-Host ""

if (!(Test-Path ".\package.json")) {
    Write-Host "ERROR: Falta package.json. Carpeta incorrecta." -ForegroundColor Red
    exit 1
}

if (!(Test-Path ".\backend\server.py")) {
    Write-Host "ERROR: Falta backend\server.py" -ForegroundColor Red
    exit 1
}

Write-Host "Probando backend + tracker..." -ForegroundColor Yellow
py -c "import backend.server as s; t=s.generar_template_tracker(); print('OK backend.server'); print('Hojas trackeadas:', t['total_sheets']); print('Filas trackeadas:', t['total_rows'])"

Write-Host ""
Write-Host "Iniciando app..." -ForegroundColor Cyan
Write-Host "Abre: http://127.0.0.1:5173/" -ForegroundColor Cyan
Write-Host ""

npm run dev:full
