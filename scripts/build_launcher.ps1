# Build NimbuswareLauncher.exe (Windows GUI entry point).
# Cross-platform: use scripts/build_launcher.sh on macOS / Linux.
#
# Output: dist/NimbuswareLauncher.exe
# Work files: build/pyinstaller/ (gitignored via build/)
# Spec: scripts/NimbuswareLauncher.spec
#
# Place the exe in the Nimbusware repo root (next to pyproject.toml).

# Native tools (poetry, PyInstaller) write diagnostics to stderr; do not treat that as failure.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Remove-StrayRootBuildJunk {
    foreach ($name in @("NimbuswareLauncher.spec")) {
        if (Test-Path $name) {
            Remove-Item -Force $name
            Write-Host "Removed stray $name from repo root."
        }
    }
    Get-ChildItem -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d$' } | ForEach-Object {
        Write-Host "Removed stray root file: $($_.Name)"
        Remove-Item -Force $_.FullName
    }
}

Write-Host "Installing Python dependencies..."
poetry install
if ($LASTEXITCODE -ne 0) {
    Write-Error "poetry install failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Host "Ensuring PyInstaller is available..."
poetry run python -m pip install --upgrade "pyinstaller>=6"
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install pyinstaller failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

New-Item -ItemType Directory -Force -Path dist, build/pyinstaller | Out-Null

Write-Host "Building NimbuswareLauncher.exe..."
poetry run python -m PyInstaller `
  --noconfirm `
  --clean `
  --distpath dist `
  --workpath build/pyinstaller `
  scripts/NimbuswareLauncher.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Remove-StrayRootBuildJunk

$exe = Join-Path (Get-Location) "dist\NimbuswareLauncher.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Build finished but output is missing: $exe"
    exit 1
}

Write-Host ""
Write-Host "Built: $exe"
Write-Host "Copy dist/NimbuswareLauncher.exe into your Nimbusware repo root for Install / Update / Run."
