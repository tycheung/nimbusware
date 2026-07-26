from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogSlice,
    DeliveryBacklog,
    SliceStatus,
    backlog_dependency_graph,
    sync_backlog_metadata,
)

# After this many gate fails on the same slice, step one dependency further back.
FAILS_PER_LEVEL = 2


@dataclass(frozen=True)
class EscalateDecision:
    slice_id: str
    epic_id: str
    feature_id: str
    depth: int
    fail_streak: int
    needs_replan: bool
    failed_slice_id: str


def slice_gate_fail_streak(rows: list[dict[str, Any]], slice_id: str) -> int:
    """Count trailing slice.gate FAILs for ``slice_id`` (broken by a PASS)."""
    streak = 0
    for row in reversed(rows):
        payload = row.get("payload")
        if not isinstance(payload, dict) or payload.get("stage_name") != "slice.gate":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        sid = meta.get("backlog_slice_id") or meta.get("slice_id")
        if not isinstance(sid, str) or sid.strip() != slice_id:
            continue
        if meta.get("slice_gate_verdict") == "PASS":
            break
        streak += 1
    return streak


def escalation_depth(fail_streak: int, *, fails_per_level: int = FAILS_PER_LEVEL) -> int:
    if fail_streak <= 0 or fails_per_level <= 0:
        return 0
    return fail_streak // fails_per_level


def dependency_chain_depth(graph: dict[str, tuple[str, ...]], slice_id: str) -> int:
    depth = 0
    current = slice_id
    seen: set[str] = set()
    while True:
        deps = graph.get(current, ())
        if not deps:
            return depth
        nxt = deps[0]
        if nxt in seen:
            return depth
        seen.add(nxt)
        current = nxt
        depth += 1


def walk_dependency_back(
    graph: dict[str, tuple[str, ...]],
    slice_id: str,
    depth: int,
) -> str:
    current = slice_id
    for _ in range(max(0, depth)):
        deps = graph.get(current, ())
        if not deps:
            return current
        current = deps[0]
    return current


def _index_slices(
    backlog: DeliveryBacklog,
) -> dict[str, tuple[BacklogSlice, str, str]]:
    out: dict[str, tuple[BacklogSlice, str, str]] = {}
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                out[sl.slice_id] = (sl, epic.epic_id, feature.feature_id)
    return out


def open_replan_slice_id(backlog: DeliveryBacklog, failed_slice_id: str) -> str | None:
    prefix = f"replan-{failed_slice_id}-"
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if not sl.slice_id.startswith(prefix):
                    continue
                if sl.status in (SliceStatus.PENDING, SliceStatus.IN_FLIGHT):
                    return sl.slice_id
    return None


def decide_escalation(
    backlog: DeliveryBacklog,
    rows: list[dict[str, Any]],
    *,
    fails_per_level: int = FAILS_PER_LEVEL,
) -> EscalateDecision | None:
    """Pick retry target for a failed head slice, escalating ancestors as fails pile up."""
    graph = backlog_dependency_graph(backlog)
    index = _index_slices(backlog)
    candidates: list[tuple[int, str]] = []
    for sid, (sl, _epic, _feat) in index.items():
        if sl.status != SliceStatus.FAILED:
            continue
        deps = graph.get(sid, ())
        passed = {s for s, (row, _, _) in index.items() if row.status == SliceStatus.PASSED}
        # Allow escalate even when deps are failed/passed — walk uses graph only.
        # Prefer heads whose deps are all passed (or none).
        if all(d in passed for d in deps):
            candidates.append((slice_gate_fail_streak(rows, sid), sid))
    if not candidates:
        # Still escalate any FAILED slice with a fail streak.
        for sid, (sl, _, _) in index.items():
            if sl.status == SliceStatus.FAILED:
                candidates.append((slice_gate_fail_streak(rows, sid), sid))
    if not candidates:
        return None
    fail_streak, failed_id = max(candidates, key=lambda x: (x[0], x[1]))
    if fail_streak <= 0:
        fail_streak = 1
    depth = escalation_depth(fail_streak, fails_per_level=fails_per_level)
    chain = dependency_chain_depth(graph, failed_id)
    needs_replan = depth > chain
    target = walk_dependency_back(graph, failed_id, min(depth, chain))
    if needs_replan:
        open_id = open_replan_slice_id(backlog, failed_id)
        if open_id and open_id in index:
            target = open_id
    sl, epic_id, feature_id = index[target]
    return EscalateDecision(
        slice_id=target,
        epic_id=epic_id,
        feature_id=feature_id,
        depth=depth,
        fail_streak=fail_streak,
        needs_replan=needs_replan and open_replan_slice_id(backlog, failed_id) is None,
        failed_slice_id=failed_id,
    )


def revise_backlog_with_replan(
    backlog: DeliveryBacklog,
    *,
    failed_slice_id: str,
    fail_streak: int,
) -> DeliveryBacklog:
    """Prepend a pending replan slice and make the failed slice depend on it."""
    replan_id = f"replan-{failed_slice_id}-{fail_streak}"
    if open_replan_slice_id(backlog, failed_slice_id):
        return backlog
    epics: list[BacklogEpic] = []
    for epic in backlog.epics:
        features: list[BacklogFeature] = []
        for feature in epic.features:
            slices = list(feature.slices)
            if not any(s.slice_id == failed_slice_id for s in slices):
                features.append(feature)
                continue
            replan = BacklogSlice(
                slice_id=replan_id,
                status=SliceStatus.PENDING,
                rationale=(f"Escalate replan after {fail_streak} failures on {failed_slice_id}"),
                target_paths=("README.md", "docs/"),
                estimated_loc=40,
            )
            updated: list[BacklogSlice] = [replan]
            for sl in slices:
                if sl.slice_id == failed_slice_id:
                    deps = tuple(
                        dict.fromkeys((replan_id, *sl.depends_on)),
                    )
                    updated.append(
                        sl.model_copy(
                            update={
                                "depends_on": deps,
                                "status": SliceStatus.PENDING,
                            },
                        ),
                    )
                else:
                    updated.append(sl)
            features.append(feature.model_copy(update={"slices": tuple(updated)}))
        epics.append(epic.model_copy(update={"features": tuple(features)}))
    return sync_backlog_metadata(backlog.model_copy(update={"epics": tuple(epics)}))
