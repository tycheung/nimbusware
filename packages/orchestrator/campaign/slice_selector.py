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


def _ready_slices(
    backlog: DeliveryBacklog,
    extra_passed: set[str] | None = None,
) -> list[SelectedSlice]:
    graph = backlog_dependency_graph(backlog)
    passed = _passed_ids(backlog) | (extra_passed or set())
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
    return ready


def _pick_round_robin_batch(
    ready: list[SelectedSlice],
    backlog: DeliveryBacklog,
    max_n: int,
) -> list[SelectedSlice]:
    if max_n <= 0 or not ready:
        return []
    if len(ready) <= max_n:
        return list(ready)
    counts = dict(_surface_pass_counts(backlog))
    by_surface: dict[str, list[SelectedSlice]] = {}
    for sel in ready:
        surf = str(sel.slice.surface_id or "").strip() or "_none"
        by_surface.setdefault(surf, []).append(sel)
    for items in by_surface.values():
        items.sort(key=lambda sel: sel.slice.slice_id)
    out: list[SelectedSlice] = []
    while len(out) < max_n:
        candidates: list[tuple[int, str]] = []
        for surf, items in by_surface.items():
            if items:
                key = surf if surf != "_none" else ""
                candidates.append((counts.get(key, 0), surf))
        if not candidates:
            break
        _, pick_surf = min(candidates, key=lambda x: (x[0], x[1]))
        sel = by_surface[pick_surf].pop(0)
        out.append(sel)
        sid = str(sel.slice.surface_id or "").strip()
        if sid:
            counts[sid] = counts.get(sid, 0) + 1
    return out


def _select_with_extra_passed(
    backlog: DeliveryBacklog,
    extra_passed: set[str],
) -> SelectedSlice | None:
    ready = _ready_slices(backlog, extra_passed)
    return _pick_round_robin(ready, backlog)


def select_next_slice(backlog: DeliveryBacklog) -> SelectedSlice | None:
    return _select_with_extra_passed(backlog, set())


def select_next_slices(backlog: DeliveryBacklog, max_n: int) -> list[SelectedSlice]:
    if max_n <= 1:
        one = select_next_slice(backlog)
        return [one] if one is not None else []
    ready = _ready_slices(backlog)
    return _pick_round_robin_batch(ready, backlog, max_n)


def all_slices_terminal(backlog: DeliveryBacklog) -> bool:
    if not backlog_slice_ids(backlog):
        return True
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status in (SliceStatus.PENDING, SliceStatus.IN_FLIGHT):
                    return False
    return True
