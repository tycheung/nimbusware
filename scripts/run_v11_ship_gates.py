#!/usr/bin/env python3
"""Run v1.1 finish-line gates locally (distribution build-only + benchmarks + soak)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, cmd: list[str], *, optional: bool = False) -> bool:
    print(f"\n==> {label}", flush=True)
    proc = subprocess.run(cmd, cwd=_ROOT, check=False)
    ok = proc.returncode == 0
    if not ok and not optional:
        print(f"FAILED: {label} (exit {proc.returncode})", flush=True)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="v1.1 ship gates (local, build-only distribution)")
    parser.add_argument(
        "--skip-benchmarks",
        action="store_true",
        help="Skip intent_to_patch and live-writers soak (faster)",
    )
    parser.add_argument(
        "--publish-testpypi",
        action="store_true",
        help="Upload bootstrap to TestPyPI (requires TESTPYPI_API_TOKEN)",
    )
    parser.add_argument(
        "--publish-pypi",
        action="store_true",
        help="Upload bootstrap to PyPI (requires PYPI_API_TOKEN)",
    )
    parser.add_argument(
        "--publish-vscode",
        action="store_true",
        help="Publish VS Code extension (requires VSCE_PAT)",
    )
    args = parser.parse_args()
    py = sys.executable
    failed = 0

    steps: list[tuple[str, list[str], bool]] = [
        ("Bootstrap workflow contract", [py, "scripts/run_publish_bootstrap_ci_gate.py"], False),
        ("VS Code extension workflow contract", [py, "scripts/run_publish_vscode_ci_gate.py"], False),
        (
            "Bootstrap wheel build (twine check)",
            [py, "scripts/publish_bootstrap_release.py"],
            False,
        ),
        (
            "VS Code extension package (.vsix)",
            [py, "scripts/publish_vscode_extension.py"],
            False,
        ),
    ]
    if not args.skip_benchmarks:
        steps.extend(
            [
                (
                    "Intent-to-patch via Chat benchmark",
                    [
                        py,
                        "scripts/measure_intent_to_patch.py",
                        "--via-chat",
                        "--json",
                        str(_ROOT / "benchmarks" / "latest_intent_to_patch.json"),
                    ],
                    False,
                ),
                ("Live writers production profile soak", [py, "scripts/run_live_writers_soak.py"], False),
            ],
        )

    for label, cmd, optional in steps:
        if not _run(label, cmd, optional=optional):
            failed += 1

    if args.publish_testpypi:
        if not _run(
            "Publish bootstrap to TestPyPI",
            [py, "scripts/publish_bootstrap_release.py", "--testpypi", "--skip-gate"],
            optional=False,
        ):
            failed += 1

    if args.publish_pypi:
        if not _run(
            "Publish bootstrap to PyPI",
            [py, "scripts/publish_bootstrap_release.py", "--pypi", "--skip-gate"],
            optional=False,
        ):
            failed += 1

    if args.publish_vscode:
        if not _run(
            "Publish VS Code extension to Marketplace",
            [py, "scripts/publish_vscode_extension.py", "--publish"],
            optional=False,
        ):
            failed += 1

    if failed:
        print(f"\nv1.1 ship gates: {failed} step(s) failed", flush=True)
        return 1
    print("\nv1.1 ship gates: all steps passed", flush=True)
    if not (args.publish_pypi or args.publish_testpypi or args.publish_vscode):
        print(
            "Distribution: build-only OK. Re-run with --publish-pypi / --publish-testpypi / "
            "--publish-vscode when tokens are configured (see docs/deploy/v1.1-ship-checklist.md).",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
