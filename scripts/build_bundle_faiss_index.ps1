<#
.SYNOPSIS
  Local one-shot build for the optional bundle FAISS index (PLAN_GAP §14 #12).

.DESCRIPTION
  Runs ``poetry install --with faiss`` then ``scripts/build_bundle_faiss_index.py`` with
  the same defaults as ``.github/workflows/bundle_faiss_index.yml``.

.PARAMETER RepoRoot
  Repository root. Defaults to the parent of this script's directory.

.EXAMPLE
  .\scripts\build_bundle_faiss_index.ps1
  .\scripts\build_bundle_faiss_index.ps1 -RepoRoot "D:\Nimbusware"
#>
param(
    [string]$RepoRoot = ""
)
$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$root = (Resolve-Path -LiteralPath $RepoRoot).Path
Set-Location -LiteralPath $root
poetry install --with faiss
poetry run python scripts/build_bundle_faiss_index.py --repo-root "$root"
