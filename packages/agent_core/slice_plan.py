from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    paths: tuple[str, ...]
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
