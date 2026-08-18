# Download vendor tools that must stay off GitHub.
# Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts/download-tools.ps1

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path -Parent $PSScriptRoot
$State = Join-Path $Root "state"
New-Item -ItemType Directory -Force -Path $State | Out-Null

function Get-File([string]$Url, [string]$Dest, [int]$MinBytes) {
    if ((Test-Path $Dest) -and ((Get-Item $Dest).Length -gt $MinBytes)) {
        Write-Host "already have $Dest ($((Get-Item $Dest).Length) bytes)"
        return
    }
    Write-Host "downloading $Url"
    $tmp = "$Dest.partial"
    Invoke-WebRequest -Uri $Url -OutFile $tmp -UseBasicParsing -UserAgent "ascension-zh-cn-download-tools"
    Move-Item -Force $tmp $Dest
    Write-Host "wrote $Dest ($((Get-Item $Dest).Length) bytes)"
}

$BepInExZip = Join-Path $State "BepInExPack_IL2CPP-6.0.755.zip"
Get-File `
    "https://gcdn.thunderstore.io/live/repository/packages/BepInEx-BepInExPack_IL2CPP-6.0.755.zip" `
    $BepInExZip `
    1000000

$SdkZip = Join-Path $State "dotnet-sdk-8.0.424-win-x64.zip"
Get-File `
    "https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.424/dotnet-sdk-8.0.424-win-x64.zip" `
    $SdkZip `
    1000000

$SdkDir = Join-Path $State "dotnet-sdk"
$Dotnet = Join-Path $SdkDir "dotnet.exe"
if (-not (Test-Path $Dotnet)) {
    Write-Host "extracting portable .NET SDK -> $SdkDir"
    New-Item -ItemType Directory -Force -Path $SdkDir | Out-Null
    Expand-Archive -Path $SdkZip -DestinationPath $SdkDir -Force
}
if (-not (Test-Path $Dotnet)) {
    throw "dotnet.exe missing after extracting $SdkZip"
}

Write-Host ""
Write-Host "OK. Portable SDK: $Dotnet"
Write-Host "BepInEx pack: $BepInExZip"
Write-Host "These paths are gitignored. Next: scripts/publish-installer.ps1"
Write-Host "Optional CJK font: drop an OFL TTF into fonts/ (also gitignored)."
