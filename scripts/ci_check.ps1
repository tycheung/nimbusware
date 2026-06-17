# Entry point wrapper — implementation in scripts/ci/ci_check.ps1
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "ci\ci_check.ps1") @args
exit $LASTEXITCODE
