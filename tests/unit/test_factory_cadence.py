from __future__ import annotations

from pathlib import Path

from orchestrator.factory_cadence import (
    FACTORY_CADENCE_STAGE,
    FACTORY_COMPLETE_STAGE,
    FACTORY_GATE_STAGE,
    factory_blocks_campaign_pass,
    factory_complete_emitted,
    factory_completion_policy_from_rows,
    maybe_run_factory_cadence_pass,
    should_run_factory_cadence,
)
from orchestrator.factory_completion import factory_ui_flow_required
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.workflow_campaign import parse_completion_workflow_block

REPO = Path(__file__).resolve().parents[2]


def test_parse_factory_zero_touch_completion_block() -> None:
    block = parse_completion_workflow_block(REPO, "campaign_factory_zero_touch")
    assert block.factory_tier == "T2"
    assert block.e2e_on_every_n_slices == 3
    assert block.auto_launch_eval is True


def test_should_run_factory_cadence_on_slice_multiple() -> None:
    assert should_run_factory_cadence(3, 3, tier="T2") is True
    assert should_run_factory_cadence(4, 3, tier="T2") is False
    assert should_run_factory_cadence(3, 3, tier="T0") is False


def test_factory_ui_flow_required_for_t2b_and_t3() -> None:
    assert factory_ui_flow_required(metadata_tier="T2b") is True
    assert factory_ui_flow_required(metadata_tier="T3") is True
    assert factory_ui_flow_required(metadata_tier="T2") is False


def test_factory_completion_policy_t2b_sets_ui_flow_required() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "campaign_effective": {
                    "enabled": True,
                    "completion": {"factory_tier": "T2b"},
                },
            },
        },
    ]
    policy = factory_completion_policy_from_rows(rows)
    assert policy is not None
    assert policy.factory_tier == "T2"
    assert policy.raw_factory_tier == "T2b"
    assert policy.ui_flow_required is True


def test_factory_completion_policy_from_campaign_metadata() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "campaign_effective": {
                    "enabled": True,
                    "completion": {
                        "factory_tier": "T2",
                        "e2e_on_every_n_slices": 5,
                        "auto_launch_eval": True,
                    },
                },
            },
        },
    ]
    policy = factory_completion_policy_from_rows(rows)
    assert policy is not None
    assert policy.factory_tier == "T2"


def test_factory_blocks_campaign_pass_requires_launch_and_complete() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "campaign_effective": {
                    "enabled": True,
                    "completion": {"factory_tier": "T2"},
                },
            },
        },
    ]
    assert factory_blocks_campaign_pass(rows) == (
        "launch_eval_not_completed",
        "factory_complete_pending",
    )


def test_maybe_run_factory_cadence_emits_stages_on_tiny_api() -> None:
    orch, mem = make_dev_orchestrator(REPO)
    ws = REPO / "tests" / "fixtures" / "repos" / "tiny_api_app"
    run_id = orch.create_run(
        "campaign_factory_zero_touch",
        project_workspace_path=str(ws),
        requirements={"business_prompt": "Build a contacts REST API with health check"},
    )
    rows = mem.list_run_events(str(run_id))
    result = maybe_run_factory_cadence_pass(
        mem,
        run_id,
        rows,
        workspace=ws,
        slices_completed=3,
        repo_root=REPO,
        force=True,
    )
    assert result is not None
    updated = mem.list_run_events(str(run_id))
    stage_names = [
        row.get("payload", {}).get("stage_name")
        for row in updated
        if isinstance(row.get("payload"), dict)
    ]
    assert FACTORY_CADENCE_STAGE in stage_names
    assert FACTORY_GATE_STAGE in stage_names
    if result.factory_complete:
        assert factory_complete_emitted(updated)
        assert FACTORY_COMPLETE_STAGE in stage_names
