from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    FindingFixStrictnessSettings,
    NetworkEgressPolicySnapshot,
    PolicySnapshotV1,
    RunCreatedEvent,
    RunCreatedPayload,
    RunStartedEvent,
    RunStartedPayload,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from nimbusware_store.memory import InMemoryEventStore

_RUN_CREATED = "run.created"


def _stored_policy_snapshot_dict(mem: InMemoryEventStore, run_id: UUID) -> Any:
    for r in mem._rows:  # noqa: SLF001
        if r["event_type"] == _RUN_CREATED and r["run_id"] == run_id:
            return r["payload"]["policy_snapshot"]
    raise AssertionError(f"no RUN_CREATED row for {run_id}")


def _make_synthetic_run_created(
    run_id: UUID,
    *,
    domain_allowlist: list[str] | None = None,
    policy_snapshot_none: bool = False,
) -> RunCreatedEvent:
    """Hand-craft a RUN_CREATED event for degenerate-edge axes (bypasses ``create_run``)."""
    if policy_snapshot_none:
        ps: PolicySnapshotV1 | None = None
    else:
        ps = PolicySnapshotV1(
            finding_fix_strictness=FindingFixStrictnessSettings(),
            network_egress=NetworkEgressPolicySnapshot(
                scraper_role_allowlist=[],
                domain_allowlist=list(domain_allowlist or []),
                budget_bytes_per_run=None,
            ),
        )
    return RunCreatedEvent(
        event_type=EventType.RUN_CREATED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        payload=RunCreatedPayload(
            workflow_profile="default",
            policy_version="1",
            config_snapshot_id=str(uuid4()),
            policy_snapshot=ps,
        ),
    )


def test_policy_snapshot_for_run_empty_and_no_match_3_axis_contract() -> None:
    orch_a1, _ = make_dev_orchestrator()
    assert orch_a1.policy_snapshot_for_run(uuid4()) == {}

    orch_a2, _ = make_dev_orchestrator()
    real_rid = orch_a2.create_run("default")
    other_rid = uuid4()
    assert orch_a2.policy_snapshot_for_run(other_rid) == {}, (
        "different run_id should miss (per-run lookup, not global state)"
    )
    assert orch_a2.policy_snapshot_for_run(real_rid) != {}, (
        "sanity: real run_id should still return non-empty snapshot"
    )

    orch_a3, mem_a3 = make_dev_orchestrator()
    rid_a3 = uuid4()
    mem_a3.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=rid_a3,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="fo87-test"),
        ),
    )
    assert orch_a3.policy_snapshot_for_run(rid_a3) == {}, (
        "same run_id but no RUN_CREATED row should still yield {} (event_type filter at line 543)"
    )


def test_policy_snapshot_for_run_happy_path_and_roundtrip_4_axis_contract() -> None:
    orch_b1, _ = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    snap_b1 = orch_b1.policy_snapshot_for_run(rid_b1)
    assert isinstance(snap_b1, dict)
    assert "finding_fix_strictness" in snap_b1
    assert "network_egress" in snap_b1
    assert isinstance(snap_b1["finding_fix_strictness"], dict)
    assert isinstance(snap_b1["network_egress"], dict)
    assert snap_b1["network_egress"]["domain_allowlist"] == []
    assert snap_b1["network_egress"]["scraper_role_allowlist"] == []
    assert snap_b1["network_egress"]["budget_bytes_per_run"] is None

    orch_b2, _ = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run(
        "default",
        run_policy_overrides={
            "network_egress": {"domain_allowlist": [".example.test", ".pypi.org"]},
        },
    )
    snap_b2 = orch_b2.policy_snapshot_for_run(rid_b2)
    assert snap_b2["network_egress"]["domain_allowlist"] == [".example.test", ".pypi.org"]

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run(
        "default",
        run_policy_overrides={
            "network_egress": {"domain_allowlist": [".alpha.test"]},
        },
    )
    stored = _stored_policy_snapshot_dict(mem_b3, rid_b3)
    read_back = orch_b3.policy_snapshot_for_run(rid_b3)
    assert stored == read_back, (
        f"WRITE/READ round-trip broken: stored policy_snapshot dict must equal "
        f"policy_snapshot_for_run return value (fo86 cross-link); "
        f"stored={stored!r} read_back={read_back!r}"
    )

    orch_b4, _ = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("agent_evaluator_on")
    snap_b4 = orch_b4.policy_snapshot_for_run(rid_b4)
    assert "finding_fix_strictness" in snap_b4 and "network_egress" in snap_b4, (
        "read is workflow-agnostic; agent_evaluator_on should yield expected shape"
    )


def test_policy_snapshot_for_run_degenerate_edges_and_downstream_4_axis_contract() -> None:
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = uuid4()
    mem_c1.append(_make_synthetic_run_created(rid_c1, policy_snapshot_none=True))
    assert orch_c1.policy_snapshot_for_run(rid_c1) == {}, (
        "stored policy_snapshot=None should yield {} (line 549-550 None-branch)"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = uuid4()
    mem_c2.append(_make_synthetic_run_created(rid_c2, domain_allowlist=[".alpha.test"]))
    mem_c2.append(_make_synthetic_run_created(rid_c2, domain_allowlist=[".beta.test"]))
    snap_c2 = orch_c2.policy_snapshot_for_run(rid_c2)
    got_c2 = snap_c2["network_egress"]["domain_allowlist"]
    assert got_c2 == [".alpha.test"], (
        f"two RUN_CREATED rows for same run_id: FIRST in append order must win "
        f"(list_run_events sorted by store_seq); got {got_c2!r}"
    )

    orch_c3, _ = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run(
        "default",
        run_policy_overrides={
            "network_egress": {"domain_allowlist": [".original.test"]},
        },
    )
    snap_first = orch_c3.policy_snapshot_for_run(rid_c3)
    snap_first["network_egress"]["domain_allowlist"].append(".injected.test")
    snap_first["network_egress"]["budget_bytes_per_run"] = 999999
    snap_second = orch_c3.policy_snapshot_for_run(rid_c3)
    assert snap_second["network_egress"]["domain_allowlist"] == [".original.test"], (
        f"mutation safety broken: caller mutation of first-call dict leaked into "
        f"store; second call returned {snap_second['network_egress']['domain_allowlist']!r}"
    )
    assert snap_second["network_egress"]["budget_bytes_per_run"] is None, (
        "mutation of budget_bytes_per_run leaked back into store on subsequent reads"
    )

    orch_c4, _ = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    ctx = orch_c4._strictness_context(rid_c4)  # noqa: SLF001
    assert "finding_fix_strictness" in ctx, (
        "_strictness_context must surface finding_fix_strictness when "
        "policy_snapshot_for_run returns a populated dict"
    )
    assert isinstance(ctx["finding_fix_strictness"], FindingFixStrictnessSettings), (
        f"_strictness_context must wrap the dict as FindingFixStrictnessSettings; "
        f"got {type(ctx['finding_fix_strictness']).__name__}"
    )
