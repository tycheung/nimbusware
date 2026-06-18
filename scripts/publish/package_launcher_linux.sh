#!/usr/bin/env bash
# Package launcher as .tar.gz with install helper (Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
poetry run python scripts/publish/rename_launcher_artifact.py >/dev/null
BIN="$(poetry run python scripts/publish/launcher_artifact_name.py)"
STAGING="build/launcher-linux"
OUT_DIR="dist/release"
rm -rf "$STAGING"
mkdir -p "$STAGING" "$OUT_DIR"
cp "dist/$BIN" "$STAGING/"
chmod +x "$STAGING/$BIN"
cp scripts/publish/INSTALL.txt "$STAGING/"
ARCHIVE="$OUT_DIR/${BIN}.tar.gz"
rm -f "$ARCHIVE"
tar -czf "$ARCHIVE" -C "$STAGING" .
echo "$ARCHIVE"
