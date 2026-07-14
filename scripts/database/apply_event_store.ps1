# Drop public schema and apply Nimbusware PostgreSQL bootstrap (greenfield).
# Usage: set NIMBUSWARE_DATABASE_URL=postgresql://user:pass@host:5432/dbname then:
#   .\scripts\database\apply_event_store.ps1

$ErrorActionPreference = "Stop"
$url = $env:NIMBUSWARE_DATABASE_URL
if (-not $url) {
    Write-Error "NIMBUSWARE_DATABASE_URL is not set."
}
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$reset = Join-Path $root "packages\store\schema\reset_public.sql"
$sql = Join-Path $root "packages\store\schema\postgres.sql"
if (-not (Test-Path $reset)) {
    Write-Error "Reset script not found: $reset"
}
if (-not (Test-Path $sql)) {
    Write-Error "Schema not found: $sql"
}
& psql $url -v ON_ERROR_STOP=1 -f $reset
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to reset public schema"
}
& psql $url -v ON_ERROR_STOP=1 -f $sql
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to apply schema"
}
Write-Host "Reset and applied: $sql"
