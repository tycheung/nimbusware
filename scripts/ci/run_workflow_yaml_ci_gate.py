#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / "configs" / "workflows"
ALLOWLIST_PATH = ROOT / "scripts" / "ci" / "workflow_yaml_allowlist.txt"
MAX_LINES = 120


def _load_allowlist() -> frozenset[str]:
    if not ALLOWLIST_PATH.is_file():
        return frozenset()
    names: set[str] = set()
    for raw in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        names.add(line)
    return frozenset(names)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    allowlist = _load_allowlist()
    if not WORKFLOWS_DIR.is_dir():
        print(f"workflow yaml gate: missing directory {WORKFLOWS_DIR}", file=sys.stderr)
        return 1

    violations: list[str] = []
    for path in sorted(WORKFLOWS_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        count = _line_count(path)
        if count <= MAX_LINES:
            continue
        if path.name in allowlist:
            continue
        violations.append(f"{path.name}: {count} lines (max {MAX_LINES})")

    if violations:
        print(
            "Workflow YAML line budget exceeded — use `extends: default` or add to "
            f"{ALLOWLIST_PATH.relative_to(ROOT)} only when a full profile is intentional:",
            file=sys.stderr,
        )
        for item in violations:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"workflow yaml gate: ok (<= {MAX_LINES} lines or allowlisted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
