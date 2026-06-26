#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "packages" / "nimbusware_orchestrator" / "llm" / "common.py"


def main() -> int:
    text = COMMON.read_text(encoding="utf-8")
    required = (
        "mesh_participant_overrides",
        "mesh_actor_user_id",
        "ModelBindingResolver",
        "participant_overrides=mesh_participant_overrides()",
    )
    missing = [token for token in required if token not in text]
    if missing:
        sys.stderr.write("collab LLM audit: llm/common.py missing mesh wiring:\n")
        for item in missing:
            sys.stderr.write(f"  - {item}\n")
        return 1
    print("collab LLM audit gate OK (fo2013)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
