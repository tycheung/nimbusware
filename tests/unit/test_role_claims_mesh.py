from uuid import uuid4

import pytest

from orchestrator.mesh_scheduler import MeshScheduler
from orchestrator.model_binding_audit import (
    RoleClaimConflictError,
    active_role_claims_from_events,
    assert_role_claim_available,
)
from orchestrator.role_claims_mesh import stage_role_claims


def test_mesh_scheduler_pins_claimed_stage_to_claimer_node() -> None:
    sched = MeshScheduler(mode="auto_share")
    sid = uuid4()
    n1, n2 = uuid4(), uuid4()
    user_a = "user-a"
    sched.register_session_nodes(sid, [n1, n2], node_users={n1: user_a, n2: "user-b"})
    out = sched.assign(
        parallel_group="writers",
        stage_names=["implementation", "test_writer"],
        session_id=sid,
        claims={"implementation": user_a},
    )
    assert out["implementation"] == n1
    assert out["test_writer"] in {n1, n2}


def test_stage_role_claims_maps_agent_role_to_stage() -> None:
    out = stage_role_claims({"backend_writer": "uid-1"})
    assert out["implementation"] == "uid-1"


def test_active_role_claims_from_events() -> None:
    run_id = uuid4()
    rows = [
        {
            "event_type": "workload.role_claimed",
            "event_id": str(uuid4()),
            "run_id": str(run_id),
            "occurred_at": "2026-01-01T00:00:00+00:00",
            "payload": {
                "agent_role": "planner",
                "claimer_user_id": "user-1",
                "provider_id": "ollama",
                "model_id": "llama",
            },
        },
        {
            "event_type": "workload.role_released",
            "event_id": str(uuid4()),
            "run_id": str(run_id),
            "occurred_at": "2026-01-02T00:00:00+00:00",
            "payload": {"agent_role": "planner", "claimer_user_id": "user-1"},
        },
    ]
    assert active_role_claims_from_events(rows) == {}


def test_assert_role_claim_available_blocks_second_claim() -> None:
    run_id = uuid4()
    rows = [
        {
            "event_type": "workload.role_claimed",
            "event_id": str(uuid4()),
            "run_id": str(run_id),
            "occurred_at": "2026-01-01T00:00:00+00:00",
            "payload": {
                "agent_role": "backend_writer",
                "claimer_user_id": "user-a",
                "provider_id": "ollama",
                "model_id": "llama",
            },
        },
    ]
    with pytest.raises(RoleClaimConflictError):
        assert_role_claim_available(
            rows,
            agent_role="backend_writer",
            claimer_user_id="user-b",
        )
