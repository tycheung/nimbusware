#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_EXT = _ROOT / "extensions" / "nimbusware-status"


def _npm() -> str:
    for name in ("npm.cmd", "npm"):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("npm is required to package the VS Code extension")


def _run(cmd: list[str], *, cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _package() -> Path:
    npm = _npm()
    install_cmd = [npm, "ci"] if (_EXT / "package-lock.json").is_file() else [npm, "install"]
    _run(install_cmd, cwd=_EXT)
    _run([npm, "run", "compile"], cwd=_EXT)
    for old in _EXT.glob("*.vsix"):
        old.unlink()
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise SystemExit("npx is required to package the VS Code extension")
    _run([npx, "vsce", "package", "--no-dependencies"], cwd=_EXT)
    vsix = sorted(_EXT.glob("*.vsix"))
    if not vsix:
        raise SystemExit("vsce package produced no .vsix")
    return vsix[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Package and optionally publish nimbusware-status")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish to Visual Studio Marketplace (requires VSCE_PAT)",
    )
    parser.add_argument(
        "--skip-gate",
        action="store_true",
        help="Skip publish workflow contract gate",
    )
    args = parser.parse_args()

    if not args.skip_gate:
        _run(
            [sys.executable, str(_ROOT / "scripts" / "ci" / "run_publish_vscode_ci_gate.py")],
            cwd=_ROOT,
        )

    vsix = _package()
    print(f"VSIX packaged: {vsix.name}", flush=True)

    if not args.publish:
        print("Package-only mode. Re-run with --publish to upload to the marketplace.", flush=True)
        return 0

    token = os.environ.get("VSCE_PAT", "").strip()
    if not token:
        raise SystemExit(
            "VSCE_PAT is required for --publish (see docs/deploy/vscode-marketplace.md)"
        )

    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise SystemExit("npx is required to publish the VS Code extension")
    _run([npx, "vsce", "publish", "--no-dependencies", "-p", token], cwd=_EXT)
    print("Published nimbusware-status to Visual Studio Marketplace", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
