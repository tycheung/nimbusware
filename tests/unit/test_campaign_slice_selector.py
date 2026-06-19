from __future__ import annotations

from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogMetadata,
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    SliceStatus,
)
from nimbusware_orchestrator.backlog_generator import generate_heuristic_backlog
from nimbusware_orchestrator.campaign_slice_selector import select_next_slice, select_next_slices


def _parallel_backlog(count: int = 3) -> DeliveryBacklog:
    slices = tuple(
        BacklogSlice(
            slice_id=f"slice-par-{i:03d}",
            status=SliceStatus.PENDING,
            target_paths=("packages/demo/a.py",),
            depends_on=(),
            estimated_loc=50,
            rationale=f"Parallel slice {i}",
        )
        for i in range(1, count + 1)
    )
    return DeliveryBacklog(
        campaign_id="run-parallel",
        epics=(
            BacklogEpic(
                epic_id="epic-par",
                title="Parallel epic",
                status=EpicStatus.IN_PROGRESS,
                features=(
                    BacklogFeature(
                        feature_id="feat-par",
                        title="Parallel feature",
                        acceptance_criteria=("Slices pass",),
                        slices=slices,
                    ),
                ),
            ),
        ),
        metadata=BacklogMetadata(generator_mode="stub", total_slices_planned=count),
    )


def test_select_next_slices_returns_independent_batch() -> None:
    backlog = _parallel_backlog(5)
    batch = select_next_slices(backlog, 3)
    assert len(batch) == 3
    ids = [sel.slice.slice_id for sel in batch]
    assert len(set(ids)) == 3


def test_select_next_slices_respects_single() -> None:
    backlog = generate_heuristic_backlog("run-one", max_slices=5)
    one = select_next_slices(backlog, 1)
    assert len(one) == 1
    assert one[0].slice.slice_id == select_next_slice(backlog).slice.slice_id  # type: ignore[union-attr]


def test_select_next_slices_respects_dependencies() -> None:
    backlog = generate_heuristic_backlog("run-deps", max_slices=5)
    batch = select_next_slices(backlog, 5)
    assert len(batch) == 1
    assert batch[0].slice.slice_id == "slice-001"
