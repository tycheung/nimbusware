# Soak / dual-run day helper (gate may be SUSPENDED — sak417 / sak421)
# Runs checklist + live ping + require-live smoke.
# Does NOT edit the calendar — print results for the operator to record.
# Usage (from Nimbusware/ or any cwd):
#   .\scripts\peel_soak_restored_day.ps1
# Optional: -HttpUrl http://127.0.0.1:8787
# Optional: -DualRunOnly  → force =1 for all domains (parity drill)
param(
    [string]$HttpUrl = "http://127.0.0.1:8787",
    [switch]$DualRunOnly
)

$ErrorActionPreference = "Stop"
$Nimbus = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Nimbus "scripts\peel_checklist.py"))) {
    $Nimbus = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Nimbusware"
}

Push-Location $Nimbus
try {
    $env:PYTHONPATH = "packages;tests"
    $env:NIMBUSWARE_BROKER_HTTP = $HttpUrl.TrimEnd("/")

    # Under suspension: prefer broker-only (=2) for all peeled capability domains
    # including COMPUTE + CAPACITY (`sak421-a`). -DualRunOnly forces =1 for parity drills.
    $cap = if ($DualRunOnly) { "1" } else { "2" }
    $env:NIMBUSWARE_BROKER_LLM = $cap
    $env:NIMBUSWARE_BROKER_SANDBOX = $cap
    $env:NIMBUSWARE_BROKER_TOOLS = $cap
    $env:NIMBUSWARE_BROKER_MEMORY = $cap
    $env:NIMBUSWARE_BROKER_RESEARCH = $cap
    $env:NIMBUSWARE_BROKER_EGRESS = $cap
    $env:NIMBUSWARE_BROKER_COMPUTE = $cap
    $env:NIMBUSWARE_BROKER_CAPACITY = $cap

    Write-Host "== peel soak day $(Get-Date -Format yyyy-MM-dd) =="
    Write-Host "HTTP=$($env:NIMBUSWARE_BROKER_HTTP) flags=$cap (LLM/SANDBOX/TOOLS/MEMORY/RESEARCH/EGRESS/COMPUTE/CAPACITY)"
    Write-Host "(under suspension: =2 broker-only default; -DualRunOnly for =1)"
    Write-Host ""

    python scripts/peel_checklist.py --strict
    if ($LASTEXITCODE -ne 0) { throw "peel_checklist failed: $LASTEXITCODE" }

    python scripts/peel_live_ping.py
    if ($LASTEXITCODE -ne 0) { throw "peel_live_ping failed: $LASTEXITCODE" }

    # Default smoke uses flags=1 in-process; pass --broker-only when operator wants =2 asserts.
    if ($DualRunOnly) {
        python scripts/peel_soak_smoke.py --require-live
    } else {
        python scripts/peel_soak_smoke.py --require-live --broker-only
    }
    if ($LASTEXITCODE -ne 0) { throw "peel_soak_smoke --require-live failed: $LASTEXITCODE" }

    Write-Host ""
    Write-Host "PASS — capability peel in progress (gate suspended; do not fake calendar soak days)."
}
finally {
    Pop-Location
}
