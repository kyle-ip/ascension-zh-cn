﻿﻿﻿#Requires -Version 5.1
<#
.SYNOPSIS
  Enable / update the Chinese patch (idempotent). Re-run after any code or
  translation change:
    1. Rebuild the overlay translation table (if Python is available).
    2. Rebuild the plugin DLL from source (once BepInEx interop exists).
    3. Copy the latest plugin DLL into the installer payload.
    4. Call AscensionZhCn-Setup.exe install (idempotent) which:
         - backs up (if not already backed up) original Lua / resources / scenes
         - patches Lua / assets / scenes with Chinese content
         - installs / refreshes BepInEx + plugin + overlay
         - sets patch.json enabled = true
    5. Double-verify with AscensionZhCn-Setup.exe status, and force-sync the
       overlay.tsv / DLL to the game to make sure the latest source is deployed.

.DESCRIPTION
  Idempotent: running twice in a row is safe.
  - Rebuilding translation / DLL when inputs are unchanged is a no-op or an
    overwrite of the same content (modulo build timestamp / module version id).
  - The installer's own install path is already idempotent (BackupIfNeeded,
    skips BepInEx install if detected).
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot "patch.json"))) {
    throw "Run inside the ascension-zh-cn repo (patch.json not found at: $RepoRoot)"
}
$ScriptsDir = $PSScriptRoot
$Dist = Join-Path $RepoRoot "dist"
$Installer = Join-Path $Dist "AscensionZhCn-Setup.exe"
$GameDir = Split-Path -Parent $RepoRoot

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK  : $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "    SKIP: $msg" -ForegroundColor DarkGray }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

# --- 1. Installer availability -----------------------------------------------
if (-not (Test-Path $Installer)) {
    Write-Warn "Installer not found. Running scripts\install.ps1 to bootstrap..."
    & powershell -ExecutionPolicy Bypass -File (Join-Path $ScriptsDir "install.ps1")
    if ($LASTEXITCODE -ne 0) { throw "install.ps1 failed" }
    if (-not (Test-Path $Installer)) { throw "install.ps1 succeeded but $Installer is still missing" }
}
Write-Ok "installer: $Installer"

# --- 2. Abort if the game is running (installer will bail) -------------------
$game = Get-Process -Name AscensionGame -ErrorAction SilentlyContinue
if ($game) {
    throw "AscensionGame.exe is running (PID $($game.Id)). Close the game completely then re-run enable.ps1."
}

# --- 3. Rebuild overlay translation table ------------------------------------
$Overlay = Join-Path $RepoRoot "loc\zh-Hans\overlay.tsv"
$Py = Get-Command python -ErrorAction SilentlyContinue
if ($Py) {
    Write-Step "rebuild overlay.tsv (python tools/overlay.py)"
    Push-Location $RepoRoot
    try {
        & $Py.Source tools\overlay.py
        if ($LASTEXITCODE -ne 0) { throw "overlay.py failed (exit=$LASTEXITCODE)" }
    } finally { Pop-Location }
    if (-not (Test-Path $Overlay)) { throw "overlay.py succeeded but $Overlay is missing" }
    Write-Ok ("overlay.tsv: " + (Get-Item $Overlay).Length + " bytes")
} else {
    if (Test-Path $Overlay) { Write-Skip "Python not found; preserving existing overlay.tsv ($((Get-Item $Overlay).Length) bytes)" }
    else { Write-Warn "overlay.tsv missing AND Python not installed; the patch will install but may have incomplete translations. Install Python 3.9+ on PATH then re-run enable.ps1." }
}

# --- 4. Rebuild plugin DLL (interop must exist) -----------------------------
$Dotnet = $null
$dn = Get-Command dotnet -ErrorAction SilentlyContinue
if ($dn) { $Dotnet = $dn.Source } else {
    $portable = Join-Path $RepoRoot "state\dotnet-sdk\dotnet.exe"
    if (Test-Path $portable) { $Dotnet = $portable }
}
$PluginProj = Join-Path $RepoRoot "plugin\AscensionZhCn\AscensionZhCn.csproj"
$InteropMarker = Join-Path $GameDir "BepInEx\interop\UnityEngine.CoreModule.dll"
$BuiltDll = Join-Path $RepoRoot "plugin\AscensionZhCn\bin\Release\AscensionZhCn.dll"
$PayloadDir = Join-Path $RepoRoot "installer\AscensionZhCn.Installer\payload"
$PayloadDll = Join-Path $PayloadDir "AscensionZhCn.dll"

if ((Test-Path $InteropMarker) -and (Test-Path $PluginProj) -and $Dotnet) {
    Write-Step "BepInEx interop exists; compiling plugin from source"
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
    Push-Location (Split-Path -Parent $PluginProj)
    try {
        & $Dotnet restore AscensionZhCn.csproj --verbosity quiet
        & $Dotnet build AscensionZhCn.csproj -c Release --verbosity minimal
        if ($LASTEXITCODE -ne 0) { throw "plugin build failed" }
    } finally { Pop-Location }
    if (-not (Test-Path $BuiltDll)) { throw "plugin build succeeded but no DLL: $BuiltDll" }
    New-Item -ItemType Directory -Force -Path $PayloadDir | Out-Null
    Copy-Item -Force $BuiltDll $PayloadDll
    Write-Ok ("plugin DLL -> payload ($((Get-Item $PayloadDll).Length) bytes)")
} elseif (-not (Test-Path $InteropMarker)) {
    if (Test-Path $PayloadDll) {
        Write-Skip ("BepInEx interop not generated yet (run the game once after enabling). " +
            "Using payload DLL ($((Get-Item $PayloadDll).Length) bytes).")
    } else {
        Write-Warn ("Neither interop nor payload DLL present. Enable will continue, " +
            "but after the first run you MUST fully exit then re-run enable.ps1 " +
            "so the latest source DLL can be compiled and deployed.")
    }
} else {
    Write-Skip "dotnet not available / plugin project missing; not recompiling plugin DLL"
}

# --- 5. Run installer install (idempotent) ----------------------------------
Write-Step "AscensionZhCn-Setup.exe install"
& $Installer install
$installExit = $LASTEXITCODE
if ($installExit -ne 0) {
    throw "AscensionZhCn-Setup.exe install failed (exit=$installExit). Try running with Administrator privileges, and make sure the game is fully closed."
}

# --- 6. Force-sync latest overlay / DLL (in case installer path used stale) --
$ZhcnDest = Join-Path $GameDir "AscensionGame_Data\StreamingAssets\zh-cn"
if (Test-Path $Overlay) {
    New-Item -ItemType Directory -Force -Path $ZhcnDest | Out-Null
    Copy-Item -Force $Overlay (Join-Path $ZhcnDest "overlay.tsv")
    $BepPlugins = Join-Path $GameDir "BepInEx\plugins"
    if (Test-Path $BepPlugins) {
        Copy-Item -Force $Overlay (Join-Path $BepPlugins "overlay.tsv")
        if (Test-Path $BuiltDll) {
            try { Copy-Item -Force $BuiltDll (Join-Path $BepPlugins "AscensionZhCn.dll") -ErrorAction Stop }
            catch { Write-Warn "could not overwrite plugin DLL (file lock?): $($_.Exception.Message)" }
        }
    }
}

# --- 7. Verify via installer status ------------------------------------------
Write-Step "AscensionZhCn-Setup.exe status"
& $Installer status
Write-Host ""
Write-Host "Chinese patch ENABLED / UPDATED." -ForegroundColor Green
Write-Host "If the game still appears in English after first enable:" -ForegroundColor Yellow
Write-Host "  1. Launch the game once (BepInEx generates interop assemblies; may take 1-2 minutes)."
Write-Host "  2. Fully exit the game, then run .\scripts\enable.ps1 one more time so the latest"
Write-Host "     source DLL gets compiled against the newly-generated interop and deployed."
exit 0
