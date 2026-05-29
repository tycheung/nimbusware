#!/usr/bin/env bash
# Build HermesLauncher binary (macOS / Linux GUI entry point).
# Requires: poetry install, PyInstaller via pip.
#
# Output: dist/HermesLauncher (or dist/HermesLauncher.exe on Windows if run there)
# Place the binary in the Hermes repo root (next to pyproject.toml).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Installing Python dependencies..."
poetry install

echo "Ensuring PyInstaller is available..."
poetry run python -m pip install --upgrade "pyinstaller>=6"

echo "Building HermesLauncher..."
poetry run pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name HermesLauncher \
  --paths packages \
  launcher.py

echo ""
echo "Built: dist/HermesLauncher"
echo "Copy dist/HermesLauncher into your Hermes repo root for Install / Update / Run."
