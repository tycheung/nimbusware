#!/usr/bin/env bash
# Build NimbuswareLauncher binary (macOS / Linux GUI entry point).
# Requires: poetry install, PyInstaller via pip.
#
# Output: dist/NimbuswareLauncher (or dist/NimbuswareLauncher.exe on Windows if run there)
# Place the binary in the Nimbusware repo root (next to pyproject.toml).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Installing Python dependencies..."
poetry install

echo "Ensuring PyInstaller is available..."
poetry run python -m pip install --upgrade "pyinstaller>=6"

echo "Building NimbuswareLauncher..."
poetry run pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name NimbuswareLauncher \
  --paths packages \
  launcher.py

echo ""
echo "Built: dist/NimbuswareLauncher"
echo "Copy dist/NimbuswareLauncher into your Nimbusware repo root for Install / Update / Run."
