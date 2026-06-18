#!/usr/bin/env bash
# Wrap launcher binary in a macOS .dmg (run on macOS only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
poetry run python scripts/publish/rename_launcher_artifact.py >/dev/null
BIN="$(poetry run python scripts/publish/launcher_artifact_name.py)"
STAGING="build/launcher-dmg"
DMG_DIR="dist/release"
rm -rf "$STAGING"
mkdir -p "$STAGING" "$DMG_DIR"
cp "dist/$BIN" "$STAGING/"
cp scripts/publish/INSTALL.txt "$STAGING/"
DMG="$DMG_DIR/${BIN%.exe}.dmg"
rm -f "$DMG"
hdiutil create -volname "Nimbusware Launcher" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
echo "$DMG"
