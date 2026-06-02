"""RunOrchestrator.create_run`` post-gate idempotency contract."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from hermes_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore

_RUN_CREATED = "run.created"


def _count_run_created(mem: InMemoryEventStore) -> int:
    """Count RUN_CREATED rows in the in-memory event store."""
    return sum(1 for r in mem._rows if r["event_type"] == _RUN_CREATED)  # noqa: SLF001


def _correlation_ids_in_store(mem: InMemoryEventStore) -> list[UUID | None]:
    """Return ``correlation_id`` values (in append order) for all RUN_CREATED rows."""
    return [
        r.get("correlation_id")
        for r in mem._rows  # noqa: SLF001
        if r["event_type"] == _RUN_CREATED
    ]


def test_create_run_idempotency_fresh_run_and_precedence_4_axis_contract() -> None:
    """Pin 4 fresh-run paths through the idempotency block.

    Axis A1 -- both kwargs None: line 163 short-circuit. Each call
    creates a new run with ``event.correlation_id == None``.
    Axis A2 -- ``correlation_id`` only: line 162 read + line 180
    write. ``event.correlation_id == correlation_id``.
    Axis A3 -- ``idempotency_key`` only: the **implicit-promotion
    contract**. ``idempotency_key`` becomes ``event.correlation_id``
    via ``corr = correlation_id or idempotency_key``.
    Axis A4 -- both provided + different UUIDs: **precedence-winner**.
    ``correlation_id`` wins; ``idempotency_key`` value NOT stored.
    """
    orch, mem = make_dev_orchestrator()
    r1 = orch.create_run("default")
    r2 = orch.create_run("default")
    assert r1 != r2, f"both-None calls should produce distinct run_ids; got r1={r1} r2={r2}"
    assert _count_run_created(mem) == 2
    assert _correlation_ids_in_store(mem) == [None, None]

    orch, mem = make_dev_orchestrator()
    corr_a = uuid4()
    orch.create_run("default", correlation_id=corr_a)
    assert _correlation_ids_in_store(mem) == [corr_a]

    orch, mem = make_dev_orchestrator()
    idemp_k = uuid4()
    orch.create_run("default", idempotency_key=idemp_k)
    assert _correlation_ids_in_store(mem) == [idemp_k], (
        f"implicit-promotion broken: idempotency_key {idemp_k} should be "
        f"stored as event.correlation_id (line 180 write of corr)"
    )

    orch, mem = make_dev_orchestrator()
    corr_a = uuid4()
    idemp_b = uuid4()
    orch.create_run("default", correlation_id=corr_a, idempotency_key=idemp_b)
    assert _correlation_ids_in_store(mem) == [corr_a], (
        f"precedence broken: idempotency_key {idemp_b} should be IGNORED when "
        f"correlation_id {corr_a} is set (corr = correlation_id or idempotency_key)"
    )


def test_create_run_idempotency_return_roundtrip_4_axis_matrix() -> None:
    """Pin 4 idempotent-return roundtrips.

    Axis B1 -- same ``correlation_id`` repeated: same run_id, 1
    event after both calls.
    Axis B2 -- same ``idempotency_key`` repeated: same run_id,
    1 event.
    Axis B3 -- **cross-kwarg roundtrip** (consistency pin): call 1
    with ``idempotency_key=K``, call 2 with ``correlation_id=K``
    -> SAME run_id. Proves Axis A3's implicit-promotion contract
    is consistent with the lookup at line 164.
    Axis B4 -- same-corr + different ``workflow_profile``:
    idempotency does NOT re-validate the workflow on match.
    """
    orch, mem = make_dev_orchestrator()
    corr = uuid4()
    r1 = orch.create_run("default", correlation_id=corr)
    r2 = orch.create_run("default", correlation_id=corr)
    assert r1 == r2, f"same correlation_id should return same run_id; r1={r1} r2={r2}"
    assert _count_run_created(mem) == 1

    orch, mem = make_dev_orchestrator()
    idemp = uuid4()
    r1 = orch.create_run("default", idempotency_key=idemp)
    r2 = orch.create_run("default", idempotency_key=idemp)
    assert r1 == r2, f"same idempotency_key should return same run_id; r1={r1} r2={r2}"
    assert _count_run_created(mem) == 1

    orch, mem = make_dev_orchestrator()
    shared = uuid4()
    r1 = orch.create_run("default", idempotency_key=shared)
    r2 = orch.create_run("default", correlation_id=shared)
    assert r1 == r2, (
        f"cross-kwarg roundtrip broken: idempotency_key {shared} should promote "
        f"to event.correlation_id (line 180) and match in call 2's correlation_id "
        f"lookup at line 164; got r1={r1} r2={r2}"
    )
    assert _count_run_created(mem) == 1

    orch, mem = make_dev_orchestrator()
    corr = uuid4()
    r1 = orch.create_run("default", correlation_id=corr)
    r2 = orch.create_run("agent_evaluator_on", correlation_id=corr)
    assert r1 == r2, (
        f"idempotency must NOT re-validate workflow_profile on match; the stored "
        f"run_id should win regardless of workflow_profile arg; r1={r1} r2={r2}"
    )
    assert _count_run_created(mem) == 1


def test_create_run_idempotency_distinctness_and_precedence_lockout_3_axis_contract() -> None:
    """Pin 3 distinctness axes including the strong precedence-lockout pin.

    Axis C1 -- different ``correlation_id`` values: different
    run_ids, 2 events.
    Axis C2 -- mixed-None second call: ``correlation_id=A`` then
    no kwargs -> NEW run (the ``corr is not None`` guard at line
    163 strictly gates the lookup; no implicit re-match against
    most-recent).
    Axis C3 -- **precedence-lockout** (THE STRONG PIN): call 1
    with ``correlation_id=A, idempotency_key=B``, call 2 with
    ``idempotency_key=B`` alone -> call 2 creates a NEW run
    because B was IGNORED in call 1 (precedence) and never
    promoted to ``event.correlation_id``. A future refactor that
    "tries idempotency_key as fallback when correlation_id misses"
    would break this.
    """
    orch, mem = make_dev_orchestrator()
    r1 = orch.create_run("default", correlation_id=uuid4())
    r2 = orch.create_run("default", correlation_id=uuid4())
    assert r1 != r2, (
        f"different correlation_id values should produce distinct run_ids; r1={r1} r2={r2}"
    )
    assert _count_run_created(mem) == 2

    orch, mem = make_dev_orchestrator()
    corr_a = uuid4()
    r1 = orch.create_run("default", correlation_id=corr_a)
    r2 = orch.create_run("default")
    assert r1 != r2, (
        f"mixed-None second call should produce a NEW run_id (no implicit "
        f"re-match against most-recent); r1={r1} r2={r2}"
    )
    assert _count_run_created(mem) == 2

    orch, mem = make_dev_orchestrator()
    corr_a = uuid4()
    idemp_b = uuid4()
    r1 = orch.create_run("default", correlation_id=corr_a, idempotency_key=idemp_b)
    r2 = orch.create_run("default", idempotency_key=idemp_b)
    assert r1 != r2, (
        f"precedence-lockout broken: idempotency_key {idemp_b} was IGNORED in "
        f"call 1 (correlation_id {corr_a} took precedence); call 2 using "
        f"idempotency_key={idemp_b} alone should NOT match the existing run; "
        f"got r1={r1} r2={r2}"
    )
    assert _count_run_created(mem) == 2
    stored_corrs = _correlation_ids_in_store(mem)
    assert stored_corrs == [corr_a, idemp_b], (
        f"stored correlation_ids {stored_corrs} should be [call1_corr_a, "
        f"call2_idemp_b] -- proves idemp_b was NOT promoted in call 1 (precedence) "
        f"and IS promoted in call 2 (idempotency_key fallback path)"
    )
