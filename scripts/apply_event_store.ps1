# Apply Nimbusware PostgreSQL bootstrap schema (single file, greenfield).
# Usage: set NIMBUSWARE_DATABASE_URL=postgresql://user:pass@host:5432/dbname then:
#   .\scripts\apply_event_store.ps1

$ErrorActionPreference = "Stop"
$url = $env:NIMBUSWARE_DATABASE_URL
if (-not $url) {
    Write-Error "NIMBUSWARE_DATABASE_URL is not set."
}
$root = Split-Path -Parent $PSScriptRoot
$sql = Join-Path $root "packages\nimbusware_store\schema\postgres.sql"
if (-not (Test-Path $sql)) {
    Write-Error "Schema not found: $sql"
}
& psql $url -v ON_ERROR_STOP=1 -f $sql
Write-Host "Applied: $sql"
