#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "packages" / "nimbusware_orchestrator" / "llm" / "common.py"
HYDRATE = ROOT / "packages" / "nimbusware_orchestrator" / "host_collab_mesh_hydrate.py"


def main() -> int:
    common = COMMON.read_text(encoding="utf-8")
    hydrate = HYDRATE.read_text(encoding="utf-8")
    required_common = (
        "mesh_participant_overrides",
        "mesh_actor_user_id",
        "ModelBindingResolver",
        "participant_overrides=mesh_participant_overrides()",
        "ensure_mesh_binding_for_llm",
    )
    missing = [token for token in required_common if token not in common]
    if "ensure_mesh_binding_for_llm" not in hydrate:
        missing.append("host_collab_mesh_hydrate.ensure_mesh_binding_for_llm")
    if missing:
        sys.stderr.write("collab LLM audit: missing mesh wiring:\n")
        for item in missing:
            sys.stderr.write(f"  - {item}\n")
        return 1
    print("collab LLM audit gate OK (fo2013)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
