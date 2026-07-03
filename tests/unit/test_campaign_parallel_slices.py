from __future__ import annotations

from uuid import uuid4

from agent_core.models.backlog import SliceStatus
from orchestrator.campaign.driver_execute import (
    _parallel_slice_count_for_run,
    _select_slices_for_tick,
)


def test_parallel_slice_count_default_is_one() -> None:
    assert _parallel_slice_count_for_run(uuid4()) >= 1


def test_select_slices_for_tick_returns_list() -> None:
    class _Slice:
        slice_id = "s1"
        rationale = "r"
        target_paths: list[str] = []
        status = SliceStatus.PENDING
        depends_on: tuple[str, ...] = ()

    class _Feature:
        feature_id = "f1"
        slices = [_Slice()]

    class _Epic:
        epic_id = "e1"
        features = [_Feature()]

    class _Meta:
        slices_completed = 0

    class _Backlog:
        epics = [_Epic()]
        metadata = _Meta()

    out = _select_slices_for_tick(uuid4(), _Backlog())
    assert isinstance(out, list)
