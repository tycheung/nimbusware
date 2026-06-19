#!/usr/bin/env python3
"""First-publish gates: build bootstrap wheel + VSIX without uploading (operator preflight)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _run(label: str, cmd: list[str]) -> bool:
    print(f"\n==> {label}", flush=True)
    proc = subprocess.run(cmd, cwd=_ROOT, check=False)
    if proc.returncode != 0:
        print(f"FAILED: {label} (exit {proc.returncode})", flush=True)
    return proc.returncode == 0


def main() -> int:
    py = sys.executable
    steps = [
        ("Bootstrap CI gate", [py, "scripts/ci/run_publish_bootstrap_ci_gate.py"]),
        ("VS Code extension CI gate", [py, "scripts/ci/run_publish_vscode_ci_gate.py"]),
        ("Bootstrap wheel build (twine check)", [py, "scripts/publish/publish_bootstrap_release.py"]),
        ("VS Code .vsix package", [py, "scripts/publish/publish_vscode_extension.py"]),
    ]
    failed = 0
    for label, cmd in steps:
        if not _run(label, cmd):
            failed += 1
    if failed:
        print(f"\n{failed} gate(s) failed — fix before PyPI/VSCE publish.", flush=True)
        return 1
    print(
        "\nBuild-only gates passed. To publish:\n"
        "  PyPI:  poetry run python scripts/publish/publish_bootstrap_release.py --pypi\n"
        "  VSCE: poetry run python scripts/publish/publish_vscode_extension.py --publish\n"
        "  Or:   poetry run python scripts/publish/run_v11_ship_gates.py "
        "--publish-pypi --publish-vscode\n"
        "Secrets: PYPI_API_TOKEN, VSCE_PAT (optional TESTPYPI_API_TOKEN).\n"
        "Docs: docs/deploy/pypi-publish.md, docs/deploy/vscode-marketplace.md",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
