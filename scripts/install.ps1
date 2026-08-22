﻿﻿﻿﻿﻿#Requires -Version 5.1
<#
.SYNOPSIS
  One-time developer bootstrap (idempotent): install / download all build-time
  dependencies (.NET SDK 8 portable, BepInEx IL2CPP zip) and build the installer.

.DESCRIPTION
  Idempotent:
  - Downloaded files are reused when they exceed a minimum size (no re-download).
  - Portable SDK is extracted once; if dotnet.exe already exists we skip extraction.
  - Installer build only happens when the .exe is missing.
  - Python is checked (for overlay generation) but not auto-installed. A warning
    is issued if missing; enable.ps1 can still work with a pre-existing overlay.

  Run this script once after a fresh `git clone` on a clean machine. After that
  use enable.ps1 and disable.ps1 for day-to-day development.
#>

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot "patch.json"))) {
    throw "Run inside the ascension-zh-cn repo (patch.json not found at: $RepoRoot)"
}
$StateDir = Join-Path $RepoRoot "state"
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK  : $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "    SKIP: $msg" -ForegroundColor DarkGray }

# --- Download helper ----------------------------------------------------------
function Get-File([string]$Url, [string]$Dest, [int]$MinBytes) {
    if ((Test-Path $Dest) -and ((Get-Item $Dest).Length -gt $MinBytes)) {
        Write-Skip "cached $Dest ($((Get-Item $Dest).Length) bytes)"
        return $true
    }
    Write-Step "downloading $Url"
    $tmp = "$Dest.partial"
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -Uri $Url -OutFile $tmp -UseBasicParsing -UserAgent "ascension-zh-cn-install-ps1"
    if ((Get-Item $tmp).Length -le $MinBytes) {
        Remove-Item $tmp -ErrorAction SilentlyContinue
        throw "downloaded file too small (or failed): $Url"
    }
    Move-Item -Force $tmp $Dest
    Write-Ok "saved $Dest ($((Get-Item $Dest).Length) bytes)"
    return $false
}

# --- dotnet ------------------------------------------------------------------
$DotnetOnPath = Get-Command dotnet -ErrorAction SilentlyContinue
if ($DotnetOnPath) {
    $ver = & $DotnetOnPath.Source --version 2>$null
    Write-Ok "dotnet on PATH: $($DotnetOnPath.Source) (version $ver)"
    $Dotnet = $DotnetOnPath.Source
} else {
    $SdkZip = Join-Path $StateDir "dotnet-sdk-8.0.424-win-x64.zip"
    Get-File `
        "https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.424/dotnet-sdk-8.0.424-win-x64.zip" `
        $SdkZip 1000000 | Out-Null
    $SdkDir = Join-Path $StateDir "dotnet-sdk"
    $Dotnet = Join-Path $SdkDir "dotnet.exe"
    if (-not (Test-Path $Dotnet)) {
        Write-Step "extracting portable .NET SDK -> $SdkDir"
        New-Item -ItemType Directory -Force -Path $SdkDir | Out-Null
        Expand-Archive -Path $SdkZip -DestinationPath $SdkDir -Force
    }
    if (-not (Test-Path $Dotnet)) {
        throw "dotnet.exe missing after extract: $Dotnet"
    }
    $ver = & $Dotnet --version 2>$null
    Write-Ok "portable dotnet: $Dotnet (version $ver)"
}

# --- BepInEx pack ------------------------------------------------------------
$BepInExZip = Join-Path $StateDir "BepInExPack_IL2CPP-6.0.755.zip"
Get-File `
    "https://gcdn.thunderstore.io/live/repository/packages/BepInEx-BepInExPack_IL2CPP-6.0.755.zip" `
    $BepInExZip 1000000 | Out-Null

# --- Python (informational) --------------------------------------------------
$Py = Get-Command python -ErrorAction SilentlyContinue
if ($Py) {
    $v = & $Py.Source --version 2>&1
    Write-Ok "python on PATH: $($Py.Source) ($v)"
} else {
    Write-Warning ("Python 3.9+ is recommended for rebuilding translation tables " +
        "(build_zh.py / overlay.py). If missing, enable.ps1 will reuse any " +
        "pre-existing overlay.tsv; please install Python with 'Add to PATH' " +
        "if you want to regenerate the translation tables from source.")
}

# --- Build installer if missing ----------------------------------------------
$Installer = Join-Path $RepoRoot "dist\AscensionZhCn-Setup.exe"
$Overlay = Join-Path $RepoRoot "loc\zh-Hans\overlay.tsv"
if (-not (Test-Path $Installer)) {
    Write-Step "building installer -> $Installer"
    if (-not (Test-Path $Overlay) -and $Py) {
        Write-Step "overlay.tsv missing; regenerating via python tools/overlay.py"
        Push-Location $RepoRoot
        try { & $Py.Source tools\overlay.py } finally { Pop-Location }
    }
    $publish = Join-Path $PSScriptRoot "publish-installer.ps1"
    & powershell -ExecutionPolicy Bypass -File $publish
    if ($LASTEXITCODE -ne 0) { throw "publish-installer.ps1 failed (exit $LASTEXITCODE)" }
} else {
    Write-Skip "installer already exists: $Installer"
}
if (-not (Test-Path $Installer)) { throw "installer was not produced: $Installer" }

# --- Final status ------------------------------------------------------------
Write-Host ""
Write-Host "=================== DEV ENVIRONMENT READY ===================" -ForegroundColor Green
Write-Host ("  dotnet   : " + $Dotnet)
Write-Host ("  python   : " + $(if ($Py) { $Py.Source } else { "<missing (optional if overlay.tsv exists)>" }))
Write-Host ("  BepInEx  : " + $BepInExZip)
Write-Host ("  installer: " + $Installer)
Write-Host "  next steps:"
Write-Host "     .\scripts\enable.ps1    install Chinese patch into the game"
Write-Host "     .\scripts\disable.ps1   restore English"
Write-Host "============================================================" -ForegroundColor Green
exit 0
