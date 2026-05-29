# Build HermesLauncher.exe (Windows GUI entry point).
# Cross-platform: use scripts/build_launcher.sh on macOS / Linux.
# Requires: poetry install (pywebview), and PyInstaller on PATH or via pip.
# PyInstaller may not support the newest Python yet — use 3.10–3.12 if build fails.
#
# Output: dist/HermesLauncher.exe
# Place the exe in the Hermes repo root (next to pyproject.toml) or any parent/child
# directory that contains the checkout.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Installing Python dependencies..."
poetry install

Write-Host "Ensuring PyInstaller is available..."
poetry run python -m pip install --upgrade "pyinstaller>=6"

Write-Host "Building HermesLauncher.exe..."
poetry run pyinstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name HermesLauncher `
  --paths packages `
  launcher.py

Write-Host ""
Write-Host "Built: dist/HermesLauncher.exe"
Write-Host "Copy dist/HermesLauncher.exe into your Hermes repo root for Install / Update / Run."
