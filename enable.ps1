# Enable Chinese overlay: reload translations, rebuild overlay, build/deploy plugin.
# Close Ascension before running.
# Prerequisites: run .\install.ps1 once on a clean machine.
# Usage:  .\enable.ps1

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$State = Join-Path $PSScriptRoot "state"
$PortableDotnet = Join-Path $State "dotnet-sdk\dotnet.exe"

function Require-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python not on PATH. Run .\install.ps1 first."
    }
}

function Resolve-Dotnet {
    if (Test-Path -LiteralPath $PortableDotnet) { return $PortableDotnet }
    $cmd = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "No .NET SDK. Run .\install.ps1 first."
}

Require-Python
$dotnet = Resolve-Dotnet
$env:DOTNET_ROOT = Split-Path -Parent $dotnet
$env:PATH = "$(Split-Path -Parent $dotnet);$env:PATH"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"

if (-not (Test-Path -LiteralPath (Join-Path $State "install.ok"))) {
    Write-Host "NOTE: state\install.ok missing — run .\install.ps1 if this is a new machine."
    Write-Host ""
}

Write-Host "==> Ascension Chinese: ENABLE"
Write-Host "    Close the game first if it is running."
Write-Host ""

# 1) Load workbench CSVs into loc/zh-Hans (if present)
if (Test-Path -LiteralPath "loc\workbench") {
    Write-Host "[1/4] Loading workbench translations..."
    python tools\workbench_load.py
    if ($LASTEXITCODE -ne 0) { throw "workbench_load.py failed ($LASTEXITCODE)" }
} else {
    Write-Host "[1/4] No loc\workbench — skipping workbench load"
}

# 2) Refresh achievements Exact map into loc/zh-Hans
Write-Host "[2/4] Building achievements table..."
if (Test-Path -LiteralPath "tools\build_achievements.py") {
    python tools\build_achievements.py
    if ($LASTEXITCODE -ne 0) { throw "build_achievements.py failed ($LASTEXITCODE)" }
    if (Test-Path -LiteralPath "loc\workbench\achievements.csv") {
        New-Item -ItemType Directory -Force -Path "loc\zh-Hans" | Out-Null
        Copy-Item -Force "loc\workbench\achievements.csv" "loc\zh-Hans\achievements.csv"
    }
}

# 3) Full enable: Lua/assets/scene + overlay + BepInEx plugin build/deploy
Write-Host "[3/4] Enabling patch + rebuilding plugin..."
python tools\patch.py enable --locale zh-Hans
if ($LASTEXITCODE -ne 0) { throw "patch.py enable failed ($LASTEXITCODE)" }

# 4) Keep debug dump off (Shop can freeze if left on)
Write-Host "[4/4] Ensuring DumpUntranslated is off..."
$gameRoot = & python -c @"
import sys
sys.path.insert(0, 'tools')
from common import detect_game_root
print(detect_game_root(prompt=True))
"@
if ($LASTEXITCODE -ne 0 -or -not $gameRoot) {
    throw "Could not resolve Ascension game folder."
}
$cfg = Join-Path $gameRoot "BepInEx\config\ascension.zh.cn.cfg"
if (Test-Path -LiteralPath $cfg) {
    $text = Get-Content -LiteralPath $cfg -Raw
    $new = $text -replace "DumpUntranslated\s*=\s*true", "DumpUntranslated = false"
    if ($new -ne $text) {
        Set-Content -LiteralPath $cfg -Value $new -NoNewline
        Write-Host "    Updated DumpUntranslated = false"
    } else {
        Write-Host "    OK: DumpUntranslated already false"
    }
} else {
    Write-Host "    (config not created yet — first launch will use plugin default false)"
}

Write-Host ""
Write-Host "Done. Restart Ascension to use the Chinese overlay."
Write-Host "Edit translations under loc\workbench\, then run .\enable.ps1 again."
