from __future__ import annotations

from nimbusware_maker.archetype_workflow import (
    campaign_profile_for_archetype,
    resolve_start_workflow_profile,
)


def test_safe_coding_archetype_uses_merged_campaign_profile() -> None:
    assert (
        campaign_profile_for_archetype(archetype="safe_coding") == "safe_coding_campaign_fullstack"
    )


def test_resolve_start_remaps_safe_coding_for_campaign() -> None:
    assert (
        resolve_start_workflow_profile("safe_coding", work_type="campaign")
        == "safe_coding_campaign_fullstack"
    )


def test_resolve_start_clears_micro_slice_for_campaign() -> None:
    assert resolve_start_workflow_profile("micro_slice", work_type="campaign") == ""


def test_resolve_start_keeps_micro_slice_for_slice() -> None:
    assert resolve_start_workflow_profile("micro_slice", work_type="slice") == "micro_slice"
