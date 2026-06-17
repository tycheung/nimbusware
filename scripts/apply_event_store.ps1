# Entry point wrapper — implementation in scripts/database/apply_event_store.ps1
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "database\apply_event_store.ps1")
exit $LASTEXITCODE
