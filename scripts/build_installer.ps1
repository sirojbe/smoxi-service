#Requires -Version 5.1
<#
.SYNOPSIS
  Compile Inno Setup installer from Nuitka output.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Iss = Join-Path $Root "installer\smoxi.iss"
$Dist = Join-Path $Root "dist\smoxi-service"

if (-not (Test-Path $Dist)) {
    Write-Error "Missing $Dist — run scripts/build_nuitka.ps1 first."
}

$Iscc = $env:ISCC_PATH
if (-not $Iscc) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $Iscc = $c; break }
    }
}
if (-not $Iscc -or -not (Test-Path $Iscc)) {
    Write-Error "ISCC.exe not found. Install Inno Setup 6 or set ISCC_PATH."
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root "installer\output") | Out-Null
Write-Host "==> Compiling installer..."
& $Iscc $Iss
Write-Host "==> Installer written to installer/output/"
