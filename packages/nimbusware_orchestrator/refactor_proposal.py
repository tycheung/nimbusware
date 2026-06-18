from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_refactor import RefactorWorkflowBlock


def estimate_loc_delta_from_patch(patch_artifact: str) -> int | None:
    try:
        ops = json.loads(patch_artifact)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(ops, list):
        return None
    total = 0
    for op in ops:
        if not isinstance(op, dict):
            continue
        val = op.get("value")
        if isinstance(val, str):
            total += max(1, val.count("\n") + 1)
        else:
            total += 1
    return total


def build_refactor_patch_artifact(
    proposal: dict[str, Any],
    workspace: Path,
) -> str:
    kind = proposal.get("proposal_kind")
    targets = proposal.get("target_paths")
    target_list = targets if isinstance(targets, list) else []
    patches: list[dict[str, str]] = []

    if kind == "orphan_fixup" and target_list:
        target = str(target_list[0]).strip()
        mod_stem = Path(target).stem
        parent = str(Path(target).parent).replace("\\", "/")
        init_rel = f"{parent}/__init__.py" if parent not in ("", ".") else "__init__.py"
        wire_line = f"from .{mod_stem} import *  # refactor: wire orphan `{target}`"
        patches.append(
            {
                "op": "add",
                "path": init_rel,
                "value": wire_line,
            },
        )
    elif kind == "route_reachability":
        unreachable = proposal.get("unreachable_module_count", 0)
        patches.append(
            {
                "op": "add",
                "path": "packages/__init__.py",
                "value": (
                    f"# refactor: wire {unreachable} unreachable module(s) "
                    "from entry routes or package __init__ re-exports"
                ),
            },
        )

    return json.dumps(patches)


def build_refactor_proposal(
    repo_root: Path,
    workspace: Path,
    block: RefactorWorkflowBlock,
) -> dict[str, Any]:
    from nimbusware_orchestrator.code_intel_store import load_or_build_code_intel

    bundle = load_or_build_code_intel(repo_root, workspace)
    orphans_raw = bundle.get("orphans")
    orphans: list[str] = []
    orphan_metadata: dict[str, str] = {}
    if isinstance(orphans_raw, dict):
        raw_list = orphans_raw.get("orphans")
        if isinstance(raw_list, list):
            orphans = [str(x) for x in raw_list if isinstance(x, str) and x.strip()]
        meta_raw = orphans_raw.get("orphan_metadata")
        if isinstance(meta_raw, dict):
            orphan_metadata = {str(k): str(v) for k, v in meta_raw.items()}

    reach = bundle.get("route_reachability")
    unreachable_count = 0
    unreachable_modules: list[str] = []
    if isinstance(reach, dict):
        raw_n = reach.get("unreachable_count")
        if isinstance(raw_n, int) and not isinstance(raw_n, bool):
            unreachable_count = raw_n
        raw_list = reach.get("unreachable_modules")
        if isinstance(raw_list, list):
            unreachable_modules = [str(x) for x in raw_list if isinstance(x, str) and x.strip()]

    if orphans:
        target = orphans[0]
        reason = orphan_metadata.get(target, "orphan")
        summary = f"Remove or wire orphan module `{target}` ({reason})."
        kind = "orphan_fixup"
    elif unreachable_count > 0:
        target = unreachable_modules[0] if unreachable_modules else "packages/"
        summary = f"Wire {unreachable_count} unreachable module(s) from entry routes."
        kind = "route_reachability"
    else:
        target = "packages/"
        summary = "No orphan or unreachable modules; hygiene pass only."
        kind = "noop"

    proposal: dict[str, Any] = {
        "proposal_kind": kind,
        "target_paths": [target],
        "summary": summary,
        "orphan_count": len(orphans),
        "unreachable_module_count": unreachable_count,
        "stub_only": block.stub_only,
    }
    proposal["patch_artifact"] = build_refactor_patch_artifact(proposal, workspace)
    return proposal


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
