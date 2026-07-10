#!/usr/bin/env python3
"""Rasterize launcher SVG logo to PNG for Tkinter (dev/build helper)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "packages" / "env" / "assets"
SVG = ASSETS / "nimbusware_logo.svg"
PNG = ASSETS / "nimbusware_logo.png"


def _render_with_resvg() -> bool:
    npx = shutil.which("npx")
    if npx is None:
        return False
    proc = subprocess.run(
        [
            npx,
            "--yes",
            "@resvg/resvg-js-cli",
            str(SVG),
            str(PNG),
            "--fit-width",
            "200",
            "--background",
            "#00132d",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and PNG.is_file()


def main() -> int:
    if not SVG.is_file():
        print(f"Missing {SVG}", file=sys.stderr)
        return 1
    ASSETS.mkdir(parents=True, exist_ok=True)
    if _render_with_resvg():
        print(f"Wrote {PNG} ({PNG.stat().st_size} bytes)")
        return 0
    print(
        "Logo render failed. Install Node.js and run: "
        "npx @resvg/resvg-js-cli packages/env/assets/nimbusware_logo.svg "
        "packages/env/assets/nimbusware_logo.png --fit-width 200 --background '#00132d'",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
