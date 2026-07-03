# Match CI integration job: apply packages/store/schema/postgres.sql then pytest -m integration.
# Prerequisites: PostgreSQL reachable, psql on PATH, Poetry env installed.
# Usage:
#   $env:NIMBUSWARE_DATABASE_URL = "postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware"
#   $env:NIMBUSWARE_REPO_ROOT = (Resolve-Path .).Path   # optional; defaults to repo root
#   .\scripts\run_integration_like_ci.ps1

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $env:NIMBUSWARE_REPO_ROOT) {
    $env:NIMBUSWARE_REPO_ROOT = $root
}
if (-not $env:NIMBUSWARE_SKIP_PREFLIGHT) {
    $env:NIMBUSWARE_SKIP_PREFLIGHT = "1"
}
& (Join-Path (Split-Path $PSScriptRoot -Parent) "database\apply_event_store.ps1")
Set-Location $root
poetry run pytest tests -q -m integration
