"""Maker git commit read model from run events."""

from __future__ import annotations

from agent_core.models import EventType
from nimbusware_maker.approval import STAGE_SLICE_APPLIED, last_git_commit_from_rows


def _stage_passed(stage_name: str, metadata: dict, store_seq: int) -> dict:
    return {
        "event_type": EventType.STAGE_PASSED.value,
        "store_seq": store_seq,
        "metadata": metadata,
        "payload": {"stage_name": stage_name},
    }


def test_last_git_commit_from_rows() -> None:
    rows = [
        _stage_passed(
            STAGE_SLICE_APPLIED,
            {
                "slice_id": "s1",
                "git_commit": {"status": "committed", "branch": "nimbusware/run-1", "sha": "abc123"},
            },
            10,
        ),
    ]
    out = last_git_commit_from_rows(rows)
    assert out is not None
    assert out["status"] == "committed"
    assert out["branch"] == "nimbusware/run-1"
    assert out["slice_id"] == "s1"
