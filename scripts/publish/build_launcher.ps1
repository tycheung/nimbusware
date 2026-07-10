# Build NimbuswareLauncher.exe (Windows GUI entry point).
# Native tools (poetry, PyInstaller) write diagnostics to stderr; do not treat that as failure.
$ErrorActionPreference = "Continue"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path

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

Write-Host "Rendering launcher logo assets..."
poetry run python scripts/publish/render_launcher_logo.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "render_launcher_logo failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Host "Building NimbuswareLauncher.exe..."
poetry run python -m PyInstaller `
  --noconfirm `
  --clean `
  --distpath dist `
  --workpath build/pyinstaller `
  scripts/publish/NimbuswareLauncher.spec
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
$renamed = poetry run python scripts/publish/rename_launcher_artifact.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "rename_launcher_artifact failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}
Write-Host "Release artifact: $renamed"
Write-Host "Copy the release artifact into your Nimbusware repo root for Quick / Full setup."
