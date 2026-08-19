# Install developer dependencies for a clean machine.
# Does NOT modify the Ascension game install — use .\enable.ps1 for that.
#
# Game folder: set config.json "gameRoot", or leave empty to be asked once.
#
# What this does:
#   - Checks Python 3
#   - Downloads BepInEx IL2CPP pack zip into state/ (used later by enable)
#   - Downloads/extracts a portable .NET 8 SDK into state/dotnet-sdk/
#   - Resolves the Ascension game folder (config.json or interactive)
#   - Checks for a CJK system font (Microsoft YaHei / SimHei)
#
# Usage (from repo root):
#   .\install.ps1

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Set-Location -LiteralPath $PSScriptRoot
$Root = $PSScriptRoot
$State = Join-Path $Root "state"
New-Item -ItemType Directory -Force -Path $State | Out-Null

Write-Host "==> Ascension Chinese: INSTALL (deps only, game untouched)"
Write-Host ""

function Get-File([string]$Url, [string]$Dest, [int]$MinBytes) {
    if ((Test-Path -LiteralPath $Dest) -and ((Get-Item -LiteralPath $Dest).Length -gt $MinBytes)) {
        Write-Host "    already have $(Split-Path -Leaf $Dest) ($((Get-Item -LiteralPath $Dest).Length) bytes)"
        return
    }
    Write-Host "    downloading $Url"
    $tmp = "$Dest.partial"
    Invoke-WebRequest -Uri $Url -OutFile $tmp -UseBasicParsing -UserAgent "ascension-zh-cn-install"
    Move-Item -Force $tmp $Dest
    Write-Host "    wrote $(Split-Path -Leaf $Dest) ($((Get-Item -LiteralPath $Dest).Length) bytes)"
}

# --- Python -----------------------------------------------------------------
Write-Host "[1/5] Python"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    throw @"
Python 3 was not found on PATH.
Install from https://www.python.org/downloads/ and tick 'Add python.exe to PATH',
then re-run .\install.ps1
"@
}
$verOut = & python -c "import sys; print('%d.%d'%sys.version_info[:2])"
if ($LASTEXITCODE -ne 0) { throw "python failed to report version" }
Write-Host "    python: $($py.Source) ($verOut)"
$major, $minor = $verOut.Split(".") | ForEach-Object { [int]$_ }
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    throw "Need Python 3.10+. Found $verOut"
}
Write-Host "    OK (stdlib only; no pip packages required)"

# --- BepInEx pack (cached zip; extracted into the game by enable) ------------
Write-Host "[2/5] BepInEx IL2CPP pack (cached under state\)"
$BepInExZip = Join-Path $State "BepInExPack_IL2CPP-6.0.755.zip"
Get-File `
    "https://gcdn.thunderstore.io/live/repository/packages/BepInEx-BepInExPack_IL2CPP-6.0.755.zip" `
    $BepInExZip `
    1000000

# --- Portable .NET 8 SDK ----------------------------------------------------
Write-Host "[3/5] .NET 8 SDK"
$SdkZip = Join-Path $State "dotnet-sdk-8.0.424-win-x64.zip"
$SdkDir = Join-Path $State "dotnet-sdk"
$Dotnet = Join-Path $SdkDir "dotnet.exe"

$sysDotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if ($sysDotnet) {
    Write-Host "    system dotnet on PATH: yes"
}

Get-File `
    "https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.424/dotnet-sdk-8.0.424-win-x64.zip" `
    $SdkZip `
    1000000

if (-not (Test-Path -LiteralPath $Dotnet)) {
    Write-Host "    extracting portable SDK -> state\dotnet-sdk\"
    New-Item -ItemType Directory -Force -Path $SdkDir | Out-Null
    Expand-Archive -Path $SdkZip -DestinationPath $SdkDir -Force
}
if (-not (Test-Path -LiteralPath $Dotnet)) {
    throw "dotnet.exe missing after extracting SDK zip"
}
Write-Host "    portable SDK ready under state\dotnet-sdk\"
& $Dotnet --list-sdks | Select-Object -First 5 | ForEach-Object { Write-Host "      $_" }

# --- Game root: config.json, or interactive ask -----------------------------
Write-Host "[4/5] Ascension game folder"
Write-Host "    (reads config.json; asks if gameRoot is empty)"
$game = & python -c @"
import sys
sys.path.insert(0, 'tools')
from common import detect_game_root
print(detect_game_root(prompt=True))
"@
if ($LASTEXITCODE -ne 0 -or -not $game) {
    throw "Could not resolve Ascension game folder. Set gameRoot in config.json or answer the prompt."
}
Write-Host "    using: $game"

# --- CJK font ---------------------------------------------------------------
Write-Host "[5/5] CJK system font"
$fonts = Join-Path $env:WINDIR "Fonts"
$cjkNames = @("msyh.ttc", "msyh.ttf", "msyhbd.ttc", "simhei.ttf")
$cjkHit = $null
foreach ($name in $cjkNames) {
    $p = Join-Path $fonts $name
    if (Test-Path -LiteralPath $p) { $cjkHit = $name; break }
}
if ($cjkHit) {
    Write-Host "    OK: $cjkHit"
} else {
    Write-Host "    WARNING: Microsoft YaHei / SimHei not found under %WINDIR%\Fonts."
    Write-Host "    Install a Chinese language pack, or drop an OFL TTF into fonts\"
}

# Marker so enable.ps1 can detect a completed install
$marker = Join-Path $State "install.ok"
@(
    "ok=1"
    "utc=$((Get-Date).ToUniversalTime().ToString('o'))"
    "python=$verOut"
) | Set-Content -LiteralPath $marker -Encoding UTF8

Write-Host ""
Write-Host "Install complete. Game files were NOT changed."
Write-Host "Next:"
Write-Host "  .\enable.ps1     # apply Chinese overlay to the game"
Write-Host "  .\disable.ps1    # restore vanilla English"
