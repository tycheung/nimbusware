"""Select the next pending backlog slice for campaign execution."""

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


def select_next_slice(backlog: DeliveryBacklog) -> SelectedSlice | None:
    graph = backlog_dependency_graph(backlog)
    passed = _passed_ids(backlog)
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
                    return SelectedSlice(
                        slice=sl, epic_id=epic.epic_id, feature_id=feature.feature_id
                    )
    return None


def all_slices_terminal(backlog: DeliveryBacklog) -> bool:
    if not backlog_slice_ids(backlog):
        return True
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.status in (SliceStatus.PENDING, SliceStatus.IN_FLIGHT):
                    return False
    return True
