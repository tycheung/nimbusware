"""Fail when key packages fall below documented coverage floors."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_FLOORS: dict[str, float] = {
    "agent_core": 85.0,
    "nimbusware_store": 85.0,
    "nimbusware_executor": 85.0,
    "nimbusware_config": 85.0,
    "nimbusware_projections": 85.0,
}


def _package_coverage_pct(report: dict, pkg: str) -> float | None:
    files = report.get("files") or {}
    covered = 0
    total = 0
    prefix = f"packages/{pkg}/"
    for path, entry in files.items():
        norm = path.replace("\\", "/")
        if not norm.startswith(prefix):
            continue
        summary = entry.get("summary") or {}
        covered += int(summary.get("covered_lines") or 0)
        total += int(summary.get("num_statements") or 0)
    if total == 0:
        return None
    return 100.0 * covered / total


def _check_report(report: dict) -> int:
    failures: list[str] = []
    for pkg, floor in _FLOORS.items():
        pct = _package_coverage_pct(report, pkg)
        if pct is None:
            failures.append(f"no coverage data for {pkg}")
        elif pct < floor:
            failures.append(f"{pkg}: {pct:.1f}% < floor {floor:.1f}%")
    if failures:
        print("Package coverage floors not met:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Package coverage floors OK:", ", ".join(f"{k}>={v}%" for k, v in _FLOORS.items()))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        help="coverage.py JSON report from pytest --cov-report=json:PATH (avoids re-running tests)",
    )
    args = parser.parse_args()
    if args.report is not None:
        if not args.report.is_file():
            print(f"coverage report not found: {args.report}", file=sys.stderr)
            return 1
        report = json.loads(args.report.read_text(encoding="utf-8"))
        return _check_report(report)

    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "coverage.json"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "-m",
                "not integration and not slow and not benchmark",
                "--cov=packages",
                f"--cov-report=json:{json_path}",
                "-q",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "NIMBUSWARE_SKIP_PREFLIGHT": "1"},
        )
        if proc.returncode not in (0, 1):
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            return proc.returncode or 1
        if not json_path.is_file():
            print("coverage JSON report missing", file=sys.stderr)
            return 1
        report = json.loads(json_path.read_text(encoding="utf-8"))
    return _check_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
