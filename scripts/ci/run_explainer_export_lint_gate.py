#!/usr/bin/env python3
"""CI gate: block new hand-written ``*_table_rows_csv`` exports outside explainer_core."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE_ROOT = ROOT / "packages" / "nimbusware_console"

# Migrated to explainer_core.table_rows_csv and functools.partial assignments (C46).
ALLOWLISTED_HAND_WRITTEN_TABLE_ROWS_CSV: frozenset[str] = frozenset()

_TABLE_ROWS_CSV_DEF = re.compile(r"^def \w+_table_rows_csv\b", re.MULTILINE)


def _rel_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def find_violations() -> list[str]:
    offenders: list[str] = []
    for path in sorted(CONSOLE_ROOT.rglob("*.py")):
        if "explainer_core" in path.parts:
            continue
        rel = _rel_posix(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not _TABLE_ROWS_CSV_DEF.search(text):
            continue
        if rel not in ALLOWLISTED_HAND_WRITTEN_TABLE_ROWS_CSV:
            offenders.append(rel)
    return offenders


def main() -> int:
    offenders = find_violations()
    if offenders:
        print(
            "New hand-written *_table_rows_csv exports outside explainer_core/ — "
            "use explainer_core.operator_metrics_exports instead:",
            file=sys.stderr,
        )
        for rel in offenders:
            print(f"  {rel}", file=sys.stderr)
        return 1
    print("explainer export lint gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
