from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.campaign import (
    campaign_effective_from_rows,
    campaign_enabled_for_run,
    campaign_policy_from_workflow,
    emit_campaign_created,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_campaign import (
    parse_backlog_workflow_block,
    parse_campaign_workflow_block,
)


def test_campaign_micro_slice_workflow_parses() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_campaign_workflow_block(repo, "campaign_micro_slice")
    assert block.enabled is True
    backlog = parse_backlog_workflow_block(repo, "campaign_micro_slice")
    assert backlog.generator == "heuristic"


def test_create_run_sets_campaign_effective_metadata() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    rows = store.list_run_events(str(run_id))
    assert campaign_enabled_for_run(rows) is True
    ce = campaign_effective_from_rows(rows)
    assert ce is not None
    assert ce.get("autonomous") is True
    assert ce.get("policy", {}).get("backlog_generator") == "heuristic"


def test_autonomous_campaign_skips_maker_approval() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run(
        "campaign_micro_slice",
        requirements={"business_prompt": "Build a thing"},
        autonomous=True,
    )
    rows = store.list_run_events(str(run_id))
    meta = rows[0].get("metadata") or {}
    assert meta.get("maker_approval") is None
    assert meta.get("campaign_effective", {}).get("autonomous") is True


def test_emit_campaign_created_event() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    policy = campaign_policy_from_workflow(repo, "campaign_micro_slice")
    emit_campaign_created(
        store,
        run_id,
        workflow_profile="campaign_micro_slice",
        policy=policy,
    )
    rows = store.list_run_events(str(run_id))
    types = [r.get("event_type") for r in rows]
    assert "campaign.created" in types
