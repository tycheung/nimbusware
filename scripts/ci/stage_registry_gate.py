#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))


def main() -> int:
    from orchestrator._pipeline.stage_registry import PIPELINE_STAGES

    if not PIPELINE_STAGES:
        print("stage registry gate: no stages registered", file=sys.stderr)
        return 1
    missing: list[str] = []
    for entry in PIPELINE_STAGES:
        if entry.mixin is None:
            missing.append(entry.name)
    if missing:
        print(f"stage registry gate: missing mixin for {missing}", file=sys.stderr)
        return 1
    print(f"stage registry gate: ok ({len(PIPELINE_STAGES)} stages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
