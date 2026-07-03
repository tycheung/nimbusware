from __future__ import annotations

from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogSlice,
    DeliveryBacklog,
    sync_backlog_metadata,
)
from orchestrator.campaign.generator import validate_backlog, validate_backlog_limits


def test_validate_backlog_limits() -> None:
    backlog = sync_backlog_metadata(
        DeliveryBacklog(
            campaign_id="c1",
            epics=(
                BacklogEpic(
                    epic_id="e1",
                    title="E",
                    features=(
                        BacklogFeature(
                            feature_id="f1",
                            title="F",
                            slices=tuple(BacklogSlice(slice_id=f"s{i}") for i in range(3)),
                        ),
                    ),
                ),
            ),
        )
    )
    assert validate_backlog_limits(backlog, max_slices=2)
    assert not validate_backlog(backlog, max_slices=5)
