$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$App = Join-Path $Root "app"

Set-Location -LiteralPath $App

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "INSPECTOR SIPUCOL — PWA LOCAL" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dirección: http://127.0.0.1:4173/"
Write-Host ""
Write-Host "Esta terminal mantiene activa la prueba PWA." -ForegroundColor Yellow
Write-Host "No la cierres mientras utilizas la aplicación." -ForegroundColor Yellow
Write-Host ""

npm.cmd run preview -- --host 127.0.0.1 --port 4173 --strictPort

Write-Host ""
Read-Host "Presiona Enter para cerrar"