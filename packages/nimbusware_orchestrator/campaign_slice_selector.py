from __future__ import annotations

from dataclasses import dataclass

from agent_core.models.backlog import (
    BacklogSlice,
    DeliveryBacklog,
    SliceStatus,
    backlog_dependency_graph,
    backlog_slice_ids,
)


@dataclass(frozen=True)
class SelectedSlice:
    slice: BacklogSlice
    epic_id: str
    feature_id: str


def _passed_ids(backlog: DeliveryBacklog) -> set[str]:
    passed: set[str] = set()
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status == SliceStatus.PASSED:
                    passed.add(sl.slice_id)
    return passed


def _surface_pass_counts(backlog: DeliveryBacklog) -> dict[str, int]:
    counts: dict[str, int] = {}
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                sid = str(sl.surface_id or "").strip()
                if not sid:
                    continue
                if sl.status == SliceStatus.PASSED:
                    counts[sid] = counts.get(sid, 0) + 1
    return counts


def _pick_round_robin(ready: list[SelectedSlice], backlog: DeliveryBacklog) -> SelectedSlice | None:
    if not ready:
        return None
    if len(ready) == 1:
        return ready[0]
    counts = _surface_pass_counts(backlog)
    surfaces = {str(s.slice.surface_id or "") for s in ready if s.slice.surface_id}
    if len(surfaces) <= 1:
        return ready[0]
    return min(
        ready,
        key=lambda sel: (
            counts.get(str(sel.slice.surface_id or ""), 0),
            sel.slice.slice_id,
        ),
    )


def _select_with_extra_passed(
    backlog: DeliveryBacklog,
    extra_passed: set[str],
) -> SelectedSlice | None:
    graph = backlog_dependency_graph(backlog)
    passed = _passed_ids(backlog) | extra_passed
    ready: list[SelectedSlice] = []
    blocked: set[str] = set()
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status in (SliceStatus.FAILED, SliceStatus.DEFERRED, SliceStatus.IN_FLIGHT):
                    blocked.add(sl.slice_id)

    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status != SliceStatus.PENDING:
                    continue
                if sl.slice_id in blocked:
                    continue
                deps = graph.get(sl.slice_id, ())
                if all(dep in passed for dep in deps):
                    ready.append(
                        SelectedSlice(
                            slice=sl, epic_id=epic.epic_id, feature_id=feature.feature_id
                        ),
                    )
    return _pick_round_robin(ready, backlog)


def select_next_slice(backlog: DeliveryBacklog) -> SelectedSlice | None:
    return _select_with_extra_passed(backlog, set())


def select_next_slices(backlog: DeliveryBacklog, max_n: int) -> list[SelectedSlice]:
    if max_n <= 1:
        one = select_next_slice(backlog)
        return [one] if one is not None else []
    graph = backlog_dependency_graph(backlog)
    passed = _passed_ids(backlog)
    blocked: set[str] = set()
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status in (SliceStatus.FAILED, SliceStatus.DEFERRED, SliceStatus.IN_FLIGHT):
                    blocked.add(sl.slice_id)

    out: list[SelectedSlice] = []
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status != SliceStatus.PENDING:
                    continue
                if sl.slice_id in blocked:
                    continue
                deps = graph.get(sl.slice_id, ())
                if all(dep in passed for dep in deps):
                    out.append(
                        SelectedSlice(
                            slice=sl, epic_id=epic.epic_id, feature_id=feature.feature_id
                        ),
                    )
                    if len(out) >= max_n:
                        return out
    return out


def all_slices_terminal(backlog: DeliveryBacklog) -> bool:
    if not backlog_slice_ids(backlog):
        return True
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status in (SliceStatus.PENDING, SliceStatus.IN_FLIGHT):
                    return False
    return True
