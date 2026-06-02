# Mirror the default CI unit job locally (see .github/workflows/ci.yml).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $env:HERMES_SKIP_PREFLIGHT) { $env:HERMES_SKIP_PREFLIGHT = "1" }

$CovJson = Join-Path $Root ".ci_coverage.json"

poetry run python scripts/rebuild_bundle_faiss_if_stale.py --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run ruff check packages tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run ruff format --check packages tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run mypy packages/nimbusware_console/services packages/nimbusware_maker/services packages/nimbusware_projections packages/nimbusware_client packages/hermes_agent_tools packages/nimbusware_api/routes/ollama.py packages/nimbusware_api/schemas/ollama.py packages/nimbusware_api/errors.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run bandit -r packages -lll -q
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
