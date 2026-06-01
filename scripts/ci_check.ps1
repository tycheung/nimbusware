# Mirror the default CI unit job locally (see .github/workflows/ci.yml).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $env:HERMES_SKIP_PREFLIGHT) { $env:HERMES_SKIP_PREFLIGHT = "1" }

poetry run python scripts/rebuild_bundle_faiss_if_stale.py --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run ruff check packages tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run mypy packages/nimbusware_console/services packages/nimbusware_maker/services
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run bandit -r packages -lll -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run pytest tests -q -m "not integration and not slow and not benchmark" `
  --cov=packages `
  --cov-report=term-missing:skip-covered `
  --cov-fail-under=72
