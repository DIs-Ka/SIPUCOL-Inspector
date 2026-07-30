$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$AppRoot = Join-Path $ProjectRoot "app"

if (-not (Test-Path $AppRoot)) {
    Write-Host "ERROR: no existe la carpeta app." -ForegroundColor Red
    exit 1
}

Set-Location $AppRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "INSPECTOR SIPUCOL" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

powershell `
    -ExecutionPolicy Bypass `
    -File ".\RUN_SIPUCOL_ESTABLE.ps1"
