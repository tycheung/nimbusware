# Entry point wrapper — implementation in scripts/install/install-nimbusware.ps1
$ErrorActionPreference = "Continue"
& (Join-Path $PSScriptRoot "install\install-nimbusware.ps1") @args
exit $LASTEXITCODE
