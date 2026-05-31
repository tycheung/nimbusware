# Mirror the default CI unit job locally (see .github/workflows/ci.yml).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $env:HERMES_SKIP_PREFLIGHT) { $env:HERMES_SKIP_PREFLIGHT = "1" }

poetry run python scripts/rebuild_bundle_faiss_if_stale.py --dry-run
poetry run ruff check packages tests
poetry run mypy packages
poetry run bandit -r packages -lll -q
poetry run pytest tests -q -m "not integration and not slow and not benchmark" `
  --cov=packages `
  --cov-report=term-missing:skip-covered `
  --cov-fail-under=60
