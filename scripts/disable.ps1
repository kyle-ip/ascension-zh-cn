﻿﻿﻿﻿﻿#Requires -Version 5.1
<#
.SYNOPSIS
  Disable the Chinese patch and restore the game to pre-patch state (idempotent).
  Backups (state/backups/) are KEPT so the patch can be re-enabled later simply
  by running enable.ps1.

.DESCRIPTION
  Idempotent: running twice in a row is a no-op.
    - If the patch is already disabled (no BepInEx / no plugin / no overlay),
      AscensionZhCn-Setup.exe restore still exits non-zero because there was
      nothing to restore; this script catches that and validates the *result*
      (files removed) instead of relying purely on exit codes.
    - If BepInEx.Uninstall refuses to delete a single in-use DLL, we fall back
      to a direct file-system clean-up and retry the marker files + folders.
    - After everything, we run 'status' and return 0 if BepInEx/core, plugin DLL
      and zh-cn overlay.tsv are all gone; otherwise non-zero.
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot "patch.json"))) {
    throw "Run inside the ascension-zh-cn repo (patch.json not found at: $RepoRoot)"
}
$Dist = Join-Path $RepoRoot "dist"
$Installer = Join-Path $Dist "AscensionZhCn-Setup.exe"
$GameDir = Split-Path -Parent $RepoRoot
$BackupDir = Join-Path $RepoRoot "state\backups"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK  : $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "    SKIP: $msg" -ForegroundColor DarkGray }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

# --- 1. Installer availability -----------------------------------------------
if (-not (Test-Path $Installer)) {
    Write-Warn "Installer missing; running install.ps1 to produce it..."
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "install.ps1")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Installer)) {
        throw "Could not produce installer: $Installer"
    }
}
Write-Ok "installer: $Installer"

# --- 2. Game process check ---------------------------------------------------
$game = Get-Process -Name AscensionGame -ErrorAction SilentlyContinue
if ($game) {
    throw "AscensionGame.exe is running (PID $($game.Id)). Close the game completely then re-run disable.ps1."
}

# --- 3. Informational: do we even have backups? -----------------------------
if (-not (Test-Path (Join-Path $BackupDir "Lua"))) {
    Write-Skip "No backup (state/backups/Lua) present. Expected if patch was never installed."
}

# --- 4. Call installer restore ----------------------------------------------
Write-Step "AscensionZhCn-Setup.exe restore"
& $Installer restore
$installExit = $LASTEXITCODE
if ($installExit -ne 0) {
    Write-Warn ("AscensionZhCn-Setup.exe restore exited with non-zero ($installExit). " +
        "This is normal when patch was never installed; cleaning up any residual files directly...")
}

# --- 5. Direct fallback cleanup (removes any leftover markers / folders even ---
#    when installer short-circuits on an already-clean install, or BepInEx's
#    Uninstall bails because of a transient file lock).
foreach ($name in @("winhttp.dll", "doorstop_config.ini", ".doorstop_version")) {
    $path = Join-Path $GameDir $name
    if (Test-Path $path) { try { Remove-Item $path -Force; Write-Ok "removed leftover: $name" } catch { Write-Warn "could not remove $name`: $($_.Exception.Message)" } }
}
foreach ($fld in @("BepInEx", "dotnet")) {
    $path = Join-Path $GameDir $fld
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $path) { Write-Warn "could not remove folder $path (likely file locks); retry after reboot" }
        else { Write-Ok "removed leftover folder: $fld" }
    }
}
$zhDest = Join-Path $GameDir "AscensionGame_Data\StreamingAssets\zh-cn"
if (Test-Path $zhDest) {
    Remove-Item $zhDest -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $zhDest) { Write-Warn "could not remove $zhDest" } else { Write-Ok "removed leftover: zh-cn" }
}
$changelog = Join-Path $GameDir "changelog.txt"
if (Test-Path $changelog) {
    $head = [System.IO.File]::ReadAllText($changelog)
    if ($head -match "BepInEx") { Remove-Item $changelog; Write-Ok "removed leftover: changelog.txt" }
}

# --- 6. Verify patch IS disabled ---------------------------------------------
Write-Step "post-restore verification"
$checks = @(
    @{ Name = "BepInEx/core DLL"; Path = Join-Path $GameDir "BepInEx\core\BepInEx.Unity.IL2CPP.dll" },
    @{ Name = "plugin DLL";       Path = Join-Path $GameDir "BepInEx\plugins\AscensionZhCn.dll" },
    @{ Name = "zh-cn overlay";    Path = Join-Path $GameDir "AscensionGame_Data\StreamingAssets\zh-cn\overlay.tsv" },
    @{ Name = "winhttp marker";   Path = Join-Path $GameDir "winhttp.dll" }
)
$allGood = $true
foreach ($c in $checks) {
    if (Test-Path $c.Path) { Write-Warn "$($c.Name) STILL EXISTS: $($c.Path)"; $allGood = $false }
    else { Write-Ok "$($c.Name) removed" }
}
# Backups MUST be kept (re-enable needs them)
if (Test-Path (Join-Path $BackupDir "Lua")) {
    Write-Ok "backups preserved (re-enable safe): $BackupDir"
} else {
    Write-Skip "no backups (expected if patch was never installed)"
}

# --- 7. Final status (run installer status, non-zero tolerated if check above OK)
Write-Step "AscensionZhCn-Setup.exe status"
& $Installer status
Write-Host ""

if ($allGood) {
    Write-Host "Chinese patch DISABLED. Backups preserved; re-enable anytime with .\scripts\enable.ps1." -ForegroundColor Green
    exit 0
} else {
    Write-Warn "Some patch artifacts remain (usually transient file locks). Re-run disable.ps1 once after a reboot, or run as Administrator."
    exit 1
}
