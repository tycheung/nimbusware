# Mirror the default CI unit job locally (see .github/workflows/ci.yml).
# Optional: -WithIntegration (Postgres integration pytest), -WithE2e (pytest tests/e2e -m e2e).
param(
    [switch]$WithIntegration,
    [switch]$WithE2e
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $env:NIMBUSWARE_SKIP_PREFLIGHT) { $env:NIMBUSWARE_SKIP_PREFLIGHT = "1" }

$CovJson = Join-Path $Root ".ci_coverage.json"

poetry run python scripts/rebuild_bundle_faiss_if_stale.py --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run ruff check packages tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run python scripts/audit_operator_env.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run ruff format --check packages tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$mypyTargets = (poetry run python scripts/mypy_ci_targets.py).Split(" ")
poetry run mypy @mypyTargets
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run bandit -c pyproject.toml -r packages -lll -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$ErrorActionPreference = "Continue"
poetry run pip-audit 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run pytest tests -q -m "not integration and not slow and not benchmark" `
  --cov=packages `
  --cov-report=term-missing:skip-covered `
  --cov-report=json:$CovJson `
  --cov-fail-under=75
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run python scripts/coverage_package_floors.py --report $CovJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Remove-Item -Force $CovJson -ErrorAction SilentlyContinue

if (-not $env:NIMBUSWARE_SLICE_E2E_COMMAND) {
    $env:NIMBUSWARE_SLICE_E2E_COMMAND = 'python -c "print(''ok'')"'
}
poetry run pytest tests/e2e/journeys/test_slice_e2e_workflow.py::test_micro_slice_web_apply_emits_slice_e2e_stage -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    Push-Location (Join-Path $Root "packages\nimbusware_maker_web")
    if (Test-Path package.json) {
        npm ci --silent 2>$null
        if ($LASTEXITCODE -eq 0) {
            npm test --silent
            if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
        }
    }
    Pop-Location
    $adminUi = Join-Path $Root "packages\nimbusware_admin_ui"
    if ((Test-Path (Join-Path $adminUi "package.json")) -and (Test-Path (Join-Path $adminUi "dist\index.html"))) {
        Push-Location $adminUi
        npm ci --silent 2>$null
        if ($LASTEXITCODE -eq 0) {
            npm test --silent
            if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
        }
        Pop-Location
    }
    $pwDir = Join-Path $Root "tests\e2e\web"
    if ((Test-Path (Join-Path $pwDir "package.json")) -and (Get-Command npx -ErrorAction SilentlyContinue)) {
        Push-Location $pwDir
        npm ci --silent 2>$null
        if ($LASTEXITCODE -eq 0) {
            npx playwright install chromium 2>$null
            if ($LASTEXITCODE -eq 0) {
                npm test --silent
                if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
            }
        }
        Pop-Location
    }
}

if ($WithIntegration -or $WithE2e) {
    if (-not $env:NIMBUSWARE_DATABASE_URL) {
        Write-Error "NIMBUSWARE_DATABASE_URL is required when using -WithIntegration or -WithE2e"
        exit 1
    }
    if (-not $env:NIMBUSWARE_REPO_ROOT) { $env:NIMBUSWARE_REPO_ROOT = $Root }
}

if ($WithIntegration) {
    & "$PSScriptRoot\run_integration_like_ci.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($WithE2e) {
    $env:NIMBUSWARE_E2E_FLAKE_RETRIES = "1"
    poetry run pytest tests/e2e -q -m e2e --reruns 1 --reruns-delay 2
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

exit 0
