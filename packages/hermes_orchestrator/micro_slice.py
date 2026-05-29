"""Micro-slice planning, diff budgets, and timeline helpers (fo152)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_orchestrator.workflow_micro_slice import MicroSliceWorkflowBlock


@dataclass(frozen=True)
class SlicePlan:
    slice_id: str
    rationale: str
    target_paths: tuple[str, ...]
    acceptance_criteria: str = ""


@dataclass(frozen=True)
class DiffBudgetResult:
    ok: bool
    file_count: int
    loc_count: int
    message: str = ""


def parse_slice_plan(raw: dict[str, Any]) -> SlicePlan:
    paths_raw = raw.get("target_paths") or raw.get("paths") or []
    if isinstance(paths_raw, str):
        paths = (paths_raw.strip(),) if paths_raw.strip() else ()
    elif isinstance(paths_raw, list):
        paths = tuple(str(p).strip() for p in paths_raw if str(p).strip())
    else:
        paths = ()
    return SlicePlan(
        slice_id=str(raw.get("slice_id", "slice-1")).strip() or "slice-1",
        rationale=str(raw.get("rationale", "")).strip(),
        target_paths=paths,
        acceptance_criteria=str(raw.get("acceptance_criteria", "")).strip(),
    )


def validate_diff_budget(
    *,
    changed_files: list[str],
    loc_added: int,
    loc_removed: int,
    config: MicroSliceWorkflowBlock,
) -> DiffBudgetResult:
    file_count = len(changed_files)
    loc_count = loc_added + loc_removed
    if file_count > config.max_files:
        return DiffBudgetResult(
            ok=False,
            file_count=file_count,
            loc_count=loc_count,
            message=f"slice exceeds max_files ({config.max_files}): {file_count} files",
        )
    if loc_count > config.max_loc:
        return DiffBudgetResult(
            ok=False,
            file_count=file_count,
            loc_count=loc_count,
            message=f"slice exceeds max_loc ({config.max_loc}): {loc_count} lines",
        )
    return DiffBudgetResult(
        ok=True,
        file_count=file_count,
        loc_count=loc_count,
        message="within budget",
    )


def micro_slice_stage_graph_nodes() -> tuple[dict[str, Any], ...]:
    """Optional stage_graph extension when ``slice.enabled`` is true."""
    return (
        {"stage_name": "slice.plan", "depends_on": ("plan",)},
        {"stage_name": "slice.implement", "depends_on": ("slice.plan",)},
        {"stage_name": "slice.verify", "depends_on": ("slice.implement",)},
        {"stage_name": "slice.critique", "depends_on": ("slice.verify",)},
        {"stage_name": "slice.test", "depends_on": ("slice.critique",)},
        {"stage_name": "slice.gate", "depends_on": ("slice.test",)},
    )


def micro_slice_timeline_summary(
  events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize slice plans and gate outcomes from run events (read-model helper)."""
    plans: list[str] = []
    blocked: list[str] = []
    completed: list[str] = []
    for row in events:
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        if meta.get("slice_plan"):
            sid = str(meta.get("slice_id", ""))
            if sid:
                plans.append(sid)
        if meta.get("slice_gate_verdict") == "FAIL":
            sid = str(meta.get("slice_id", ""))
            if sid:
                blocked.append(sid)
        if meta.get("slice_gate_verdict") == "PASS":
            sid = str(meta.get("slice_id", ""))
            if sid:
                completed.append(sid)
    current = plans[-1] if plans and len(completed) < len(plans) else ""
    return {
        "slice_count_planned": len(plans),
        "slices_completed": len(completed),
        "slices_blocked": len(blocked),
        "current_slice_id": current or None,
    }
