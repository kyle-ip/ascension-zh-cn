# Disable Chinese overlay and restore the vanilla English install.
# Close Ascension before running.
# Usage:  .\disable.ps1

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Missing required command: python. Run .\install.ps1 first."
}

Write-Host "==> Ascension Chinese: DISABLE"
Write-Host "    Close the game first if it is running."
Write-Host ""

python tools\patch.py disable
if ($LASTEXITCODE -ne 0) { throw "patch.py disable failed ($LASTEXITCODE)" }

Write-Host ""
Write-Host "Done. Restart Ascension for the original English version."
Write-Host "To turn Chinese back on later:  .\enable.ps1"
