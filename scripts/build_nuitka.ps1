#Requires -Version 5.1
<#
.SYNOPSIS
  Build SMOXI Service with Nuitka (Windows onedir).
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "==> Installing Nuitka (if needed)..."
& $Python -m pip install -q "nuitka>=2.4" ordered-set zstandard

$OutDir = Join-Path $Root "dist\smoxi-service"
if (Test-Path $OutDir) {
    Remove-Item -Recurse -Force $OutDir
}

Write-Host "==> Compiling with Nuitka..."
& $Python -m nuitka `
    --standalone `
    --assume-yes-for-downloads `
    --enable-plugin=pyside6 `
    --include-data-dir=assets=assets `
    --include-package-data=app `
    --include-data-dir=app/telegram/miniapp/static=app/telegram/miniapp/static `
    --include-data-dir=app/telegram/customer_miniapp/static=app/telegram/customer_miniapp/static `
    --output-dir=dist `
    --output-filename=smoxi-service.exe `
    --company-name=SMOXI `
    --product-name="SMOXI Service" `
    --file-version=1.5.0.0 `
    --product-version=1.5.0.0 `
    run.py

# Nuitka names folder after script by default (run.dist) — normalize
$Built = Join-Path $Root "dist\run.dist"
if (Test-Path $Built) {
    if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
    Rename-Item $Built "smoxi-service"
}

Write-Host "==> Done. Output: $OutDir"
