"""Fail when key packages fall below documented coverage floors (fo537)."""

from __future__ import annotations

import subprocess
import sys

_FLOORS: dict[str, float] = {
    "hermes_store": 85.0,
    "nimbusware_config": 85.0,
    "nimbusware_projections": 85.0,
}


def main() -> int:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "-m",
            "not integration and not slow and not benchmark",
            "--cov=packages",
            "--cov-report=term",
            "-q",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode or 1
    lines = proc.stdout.splitlines()
    failures: list[str] = []
    for pkg, floor in _FLOORS.items():
        prefix = f"packages\\{pkg}"
        alt = f"packages/{pkg}"
        pct: float | None = None
        for line in lines:
            if prefix in line or alt in line:
                parts = line.split()
                if parts and parts[-1].endswith("%"):
                    try:
                        pct = float(parts[-1].rstrip("%"))
                    except ValueError:
                        continue
        if pct is None:
            failures.append(f"no coverage row found for {pkg}")
        elif pct < floor:
            failures.append(f"{pkg}: {pct:.1f}% < floor {floor:.1f}%")
    if failures:
        print("Package coverage floors not met:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Package coverage floors OK:", ", ".join(f"{k}>={v}%" for k, v in _FLOORS.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
