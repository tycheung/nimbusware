# Bootstrap Nimbusware: Poetry deps, Docker Postgres, schema apply.
# Usage (from repo root):
#   .\scripts\install-nimbusware.ps1
# Options are forwarded to scripts/install_nimbusware.py — run:
#   python scripts/install_nimbusware.py --help

# Native tools (psql, poetry) write diagnostics to stderr; do not treat that as failure.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$installScript = Join-Path $PSScriptRoot "install_nimbusware.py"

if (Get-Command poetry -ErrorAction SilentlyContinue) {
    & poetry run python $installScript @args
    exit $LASTEXITCODE
}

$py = $null
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $py = $venvPy
} else {
    foreach ($candidate in @("py", "python", "python3")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            $py = $candidate
            break
        }
    }
}
if (-not $py) {
    Write-Error "Python not found. Install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
}

& $py $installScript @args
exit $LASTEXITCODE
