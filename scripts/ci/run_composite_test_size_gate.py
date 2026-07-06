from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS_UNIT = ROOT / "tests" / "unit"
MAX_LINES = 200
ALLOWLIST = frozenset()


def main() -> int:
    offenders: list[str] = []
    for path in sorted(TESTS_UNIT.glob("test_*composite_contract*.py")):
        if path.name in ALLOWLIST:
            continue
        line_count = sum(1 for _ in path.open(encoding="utf-8"))
        if line_count > MAX_LINES:
            offenders.append(f"{path.name}: {line_count} lines (max {MAX_LINES})")
    if offenders:
        print("composite test size gate failed:", file=sys.stderr)
        for item in offenders:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"composite test size gate: ok (allowlist {len(ALLOWLIST)} pending migrations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
