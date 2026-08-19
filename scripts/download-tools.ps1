# Deprecated wrapper — use repo-root .\install.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "scripts\download-tools.ps1 is deprecated; forwarding to .\install.ps1"
& (Join-Path $Root "install.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
