#!/usr/bin/env bash
# Build NimbuswareLauncher binary (macOS / Linux GUI entry point).
#
# Output: dist/NimbuswareLauncher (or .exe on Windows)
# Work files: build/pyinstaller/
# Spec: scripts/publish/NimbuswareLauncher.spec

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

remove_stray_root_build_junk() {
  if [[ -f NimbuswareLauncher.spec ]]; then
    rm -f NimbuswareLauncher.spec
    echo "Removed stray NimbuswareLauncher.spec from repo root."
  fi
  for f in [0-9]; do
    if [[ -f "$f" ]]; then
      echo "Removed stray root file: $f"
      rm -f "$f"
    fi
  done
}

echo "Installing Python dependencies..."
poetry install

echo "Ensuring PyInstaller is available..."
poetry run python -m pip install --upgrade "pyinstaller>=6"

mkdir -p dist build/pyinstaller

echo "Building NimbuswareLauncher..."
poetry run python -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath dist \
  --workpath build/pyinstaller \
  scripts/publish/NimbuswareLauncher.spec

remove_stray_root_build_junk

if [[ -f dist/NimbuswareLauncher ]]; then
  OUT="dist/NimbuswareLauncher"
elif [[ -f dist/NimbuswareLauncher.exe ]]; then
  OUT="dist/NimbuswareLauncher.exe"
else
  echo "ERROR: PyInstaller finished but dist/NimbuswareLauncher* is missing" >&2
  exit 1
fi

echo ""
echo "Built: $OUT"
poetry run python scripts/publish/rename_launcher_artifact.py
echo "Release artifact in dist/ (platform-specific filename)."
