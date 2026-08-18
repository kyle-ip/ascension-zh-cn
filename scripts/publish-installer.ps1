# Build plugin (if interop exists) and publish a single-file Windows installer to dist/.
# Run from the repo root after scripts/download-tools.ps1:
#   powershell -ExecutionPolicy Bypass -File scripts/publish-installer.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$State = Join-Path $Root "state"

function Resolve-Dotnet {
    $cmd = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $portable = Join-Path $State "dotnet-sdk\dotnet.exe"
    if (Test-Path $portable) { return $portable }
    $sys = Join-Path ${env:ProgramFiles} "dotnet\dotnet.exe"
    if (Test-Path $sys) { return $sys }
    throw "No .NET SDK. Run scripts/download-tools.ps1, or install .NET 8."
}

$Dotnet = Resolve-Dotnet
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
Write-Host "dotnet: $Dotnet"

$PluginProj = Join-Path $Root "plugin\AscensionZhCn\AscensionZhCn.csproj"
$GameDir = Split-Path $Root
$InteropTmp = Join-Path $GameDir "BepInEx\interop\UnityEngine.CoreModule.dll"
if (Test-Path $PluginProj) {
    if (Test-Path $InteropTmp) {
        Write-Host "building overlay plugin"
        & $Dotnet restore $PluginProj --verbosity quiet
        & $Dotnet build $PluginProj -c Release --verbosity minimal
        if ($LASTEXITCODE -ne 0) { throw "plugin build failed" }
    }
    else {
        Write-Host "skip plugin compile (BepInEx interop not generated yet)"
    }
}

$BuiltDll = Join-Path $Root "plugin\AscensionZhCn\bin\Release\AscensionZhCn.dll"
$PayloadDir = Join-Path $Root "installer\AscensionZhCn.Installer\payload"
New-Item -ItemType Directory -Force -Path $PayloadDir | Out-Null
if (Test-Path $BuiltDll) {
    Copy-Item -Force $BuiltDll (Join-Path $PayloadDir "AscensionZhCn.dll")
    Write-Host "payload plugin -> $PayloadDir\AscensionZhCn.dll"
}
elseif (-not (Test-Path (Join-Path $PayloadDir "AscensionZhCn.dll"))) {
    Write-Host "WARNING: no AscensionZhCn.dll. Installer will patch files but in-game loc overlay needs the plugin."
}

$Overlay = Join-Path $Root "loc\zh-Hans\overlay.tsv"
if (-not (Test-Path $Overlay)) {
    throw "missing $Overlay — run python tools/build_zh.py first"
}

$InstallerProj = Join-Path $Root "installer\AscensionZhCn.Installer\AscensionZhCn.Installer.csproj"
$Dist = Join-Path $Root "dist"
Write-Host "publishing installer -> $Dist"
& $Dotnet publish $InstallerProj -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true `
    -p:IncludeNativeLibrariesForSelfExtract=true `
    -p:DebugType=None `
    -p:DebugSymbols=false `
    -o $Dist
if ($LASTEXITCODE -ne 0) { throw "installer publish failed" }

$PayloadOut = Join-Path $Dist "payload"
New-Item -ItemType Directory -Force -Path $PayloadOut | Out-Null
if (Test-Path (Join-Path $PayloadDir "AscensionZhCn.dll")) {
    Copy-Item -Force (Join-Path $PayloadDir "AscensionZhCn.dll") (Join-Path $PayloadOut "AscensionZhCn.dll")
}

$Exe = Join-Path $Dist "AscensionZhCn-Setup.exe"
if (-not (Test-Path $Exe)) { throw "publish did not produce AscensionZhCn-Setup.exe" }
Write-Host "OK: $Exe"
Write-Host "dist/ is gitignored. Attach this exe to a GitHub Release if you want players to download it."
