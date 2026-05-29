# Bootstrap Nimbusware: Poetry deps, Docker Postgres, schema apply.
# Usage (from repo root):
#   .\scripts\install-nimbusware.ps1
# Options are forwarded to scripts/install_nimbusware.py — run:
#   python scripts/install_nimbusware.py --help

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = $null
foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $py = $candidate
        break
    }
}
if (-not $py) {
    Write-Error "Python not found. Install Python 3.10+ from https://www.python.org/downloads/"
}

& $py (Join-Path $PSScriptRoot "install_nimbusware.py") @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
