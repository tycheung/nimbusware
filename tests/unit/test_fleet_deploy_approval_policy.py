from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent
from agent_core.models.events_payloads import RunCreatedPayload
from nimbusware_maker.deploy_approval_enforcement import (
    deploy_dual_control_satisfied,
    user_may_record_deploy_approval,
)
from nimbusware_maker.deploy_pipeline_events import deploy_apply_ready, emit_deploy_approved
from nimbusware_orchestrator.fleet_policies import (
    FleetDeployApprovalPolicy,
    load_fleet_deploy_approval_policies,
    save_fleet_deploy_approval_policies,
)
from nimbusware_store.memory import InMemoryEventStore


def test_fleet_deploy_approval_policies_round_trip(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_deploy_approval_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  default:\n    deploy_approval_chain: maker_only\n",
        encoding="utf-8",
    )
    policies = load_fleet_deploy_approval_policies(tmp_path)
    policies["regulated"] = FleetDeployApprovalPolicy(
        tenant_slug="regulated",
        deploy_approval_chain="dual_control",
    )
    save_fleet_deploy_approval_policies(policies, repo_root=tmp_path)
    reloaded = load_fleet_deploy_approval_policies(tmp_path)
    assert reloaded["regulated"].deploy_approval_chain == "dual_control"


def test_dual_control_requires_maker_then_fleet_admin() -> None:
    rows: list[dict] = []
    ok, _, kind = user_may_record_deploy_approval(
        user_id="maker-1",
        is_fleet_admin=False,
        session_role="session_write",
        chain="dual_control",
        rows=rows,
    )
    assert ok and kind == "maker"
    rows.append(
        {
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {"stage_name": "deploy.approved"},
            "metadata": {"approver_user_id": "maker-1", "approval_kind": "maker"},
        },
    )
    ok_admin, _, kind_admin = user_may_record_deploy_approval(
        user_id="admin-1",
        is_fleet_admin=True,
        session_role=None,
        chain="dual_control",
        rows=rows,
    )
    assert ok_admin and kind_admin == "fleet_admin"
    assert not deploy_dual_control_satisfied(rows)
    rows.append(
        {
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {"stage_name": "deploy.approved"},
            "metadata": {"approver_user_id": "admin-1", "approval_kind": "fleet_admin"},
        },
    )
    assert deploy_dual_control_satisfied(rows)
    assert deploy_apply_ready(rows, deploy_approval_chain="dual_control")


def test_session_admin_chain_blocks_writer() -> None:
    ok, detail, _ = user_may_record_deploy_approval(
        user_id="u1",
        is_fleet_admin=False,
        session_role="session_write",
        chain="session_admin",
        rows=[],
    )
    assert not ok
    assert detail


def test_emit_deploy_approved_records_actor() -> None:
    store = InMemoryEventStore()
    rid = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="campaign_fullstack",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    emit_deploy_approved(store, rid, approver_user_id="user-a", approval_kind="maker")
    meta = store.list_run_events(str(rid))[-1].get("metadata") or {}
    assert meta.get("approver_user_id") == "user-a"
    assert meta.get("approval_kind") == "maker"
