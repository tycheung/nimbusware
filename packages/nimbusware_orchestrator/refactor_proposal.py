from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_refactor import RefactorWorkflowBlock


def build_refactor_proposal(
    repo_root: Path,
    workspace: Path,
    block: RefactorWorkflowBlock,
) -> dict[str, Any]:
    from nimbusware_orchestrator.code_intel_store import load_or_build_code_intel

    bundle = load_or_build_code_intel(repo_root, workspace)
    orphans_raw = bundle.get("orphans")
    orphans: list[str] = []
    if isinstance(orphans_raw, dict):
        raw_list = orphans_raw.get("orphans")
        if isinstance(raw_list, list):
            orphans = [str(x) for x in raw_list if isinstance(x, str) and x.strip()]
    reach = bundle.get("route_reachability")
    unreachable_count = 0
    if isinstance(reach, dict):
        raw_n = reach.get("unreachable_count")
        if isinstance(raw_n, int) and not isinstance(raw_n, bool):
            unreachable_count = raw_n

    if orphans:
        target = orphans[0]
        summary = f"Remove or wire orphan module `{target}`."
        kind = "orphan_fixup"
    elif unreachable_count > 0:
        target = "packages/"
        summary = f"Wire {unreachable_count} unreachable module(s) from entry routes."
        kind = "route_reachability"
    else:
        target = "packages/"
        summary = "No orphan or unreachable modules; hygiene pass only."
        kind = "noop"

    return {
        "proposal_kind": kind,
        "target_paths": [target],
        "summary": summary,
        "patch_artifact": "[]",
        "orphan_count": len(orphans),
        "unreachable_module_count": unreachable_count,
        "stub_only": block.stub_only,
    }


def orphan_gate_exceeded(
    proposal: dict[str, Any],
    *,
    orphan_gate_max: int | None,
) -> bool:
    if orphan_gate_max is None or orphan_gate_max < 0:
        return False
    raw = proposal.get("orphan_count")
    if not isinstance(raw, int) or isinstance(raw, bool):
        return False
    return raw > orphan_gate_max
