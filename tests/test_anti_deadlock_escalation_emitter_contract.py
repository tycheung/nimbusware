"""``_maybe_emit_anti_deadlock_escalation`` direct contract (fo104).

The anti-deadlock escalation emitter at [pipeline.py:1250-1281] is the only
mainline orchestrator-level `_maybe_emit_*` escalation path with no direct
happy-path or per-branch contract test today. Existing coverage:

* [tests/test_anti_deadlock.py] -- pure `should_emit_anti_deadlock_escalation`
  helper only (3 axes, no orchestrator method).
* [tests/test_deadlock_minutes_env.py] -- pure `load_anti_deadlock_settings`
  loader only (env + YAML cascade + RAISE arms).
* [tests/test_workflow_suppress_automatic_escalation_matrix.py] B1 (fo88) --
  only the **suppress arm**, single axis, no control side, no ordering pin.

fo104 closes the gap via 4 parts spanning 20 axes (~29 assertions, source
unchanged):

* **Part A** -- settings loader delegation + suppress fork control (5 axes --
  suppress short-circuits BEFORE loader / loader receives `self._repo_root` /
  loader called exactly once / `enabled=False` propagates / `stall_minutes=0`
  propagates).
* **Part B** -- `should_emit_anti_deadlock_escalation` delegation (5 axes --
  rows kwarg threading / kwargs from loader / return False -> no emit /
  return True -> exactly one emit / `now` is tz-aware UTC).
* **Part C** -- dedup-by-reason-code + dedup-before-should_emit ordering
  (5 axes -- prior matching blocks / prior different reason_code does NOT
  block / prior STAGE_FAILED does NOT block / two prior matching still
  block / dedup fires BEFORE should_emit).
* **Part D** -- happy-path emit shape + literal notes format (5 axes --
  exactly 1 RUN_ESCALATED / payload literals / notes literal format /
  notes reflects loader values / no extraneous fields).

Key contract divergences pinned by fo104:

* **Per-reason-code dedup** -- distinct from fo102 C's ANY-RUN_ESCALATED
  asymmetric dedup for `_maybe_auto_escalate`. A future "unify all
  escalation dedup" refactor would silently flip this.
* **Notes literal** `f"stall_minutes={S} min_progress_events={M}"` --
  distinct from fo102's `f"threshold=N cumulative_*=n"` shape.
* **Suppress arm sits at TOP of function** -- loader is NOT called when
  suppress fires (fo88 only proves no emit).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    RunEscalatedEvent,
    RunEscalatedPayload,
    StageFailedEvent,
    StageFailedPayload,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore


_RUN_ESCALATED = "run.escalated"
_STAGE_FAILED = "stage.failed"
_ANTI_DEADLOCK = "anti_deadlock_insufficient_progress"


def _escalation_rows(mem: InMemoryEventStore, rid: UUID) -> list[dict[str, Any]]:
    """Return ``run.escalated`` rows for the run, in store order."""
    return [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == _RUN_ESCALATED
    ]


def _append_escalation(mem: InMemoryEventStore, rid: UUID, reason: str) -> None:
    """Append one synthetic ``RUN_ESCALATED`` row with the given reason_code."""
    mem.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="system:fo104_seed",
                reason_code=reason,
                notes="fo104 seed",
            ),
        ),
    )


def _append_stage_failed(mem: InMemoryEventStore, rid: UUID, name: str) -> None:
    """Append one synthetic ``STAGE_FAILED`` row (different event_type -- dedup foil)."""
    mem.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=StageFailedPayload(
                stage_name=name,
                reason_code="fo104_unrelated",
                message="fo104 unrelated stage failure",
            ),
        ),
    )


def test_anti_deadlock_escalation_settings_and_suppress_5_axis() -> None:
    """Pin `load_anti_deadlock_settings(self._repo_root)` delegation + suppress-before-loader.

    Coverage delta vs fo88 B1: fo88 proves "no emit when suppress" but does NOT
    prove (a) the loader is short-circuited BEFORE call, (b) the loader receives
    `self._repo_root` positionally, (c) the loader is called exactly once per
    emit invocation, (d) `enabled=False` / `stall_minutes=0` from the loader
    flow through `should_emit` to no-emit.
    """
    orch_a1, _ = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("escalation_suppress_on")
    with patch(
        "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
        return_value=(True, 15, 3),
    ) as loader_spy_a1:
        orch_a1._maybe_emit_anti_deadlock_escalation(rid_a1)  # noqa: SLF001
    assert loader_spy_a1.call_count == 0, (
        "A1: suppress fork short-circuits BEFORE load_anti_deadlock_settings; "
        "fo88 B1 only proves no emit, this pins ordering (loader sits AFTER "
        "the suppress check at pipeline.py:1251-1253)"
    )
    assert _escalation_rows(orch_a1._store, rid_a1) == [], (  # noqa: SLF001
        "A1: suppress fork emits no RUN_ESCALATED (control reaffirms fo88 B1)"
    )

    orch_a2, _ = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    with patch(
        "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
        return_value=(True, 15, 3),
    ) as loader_spy_a2:
        orch_a2._maybe_emit_anti_deadlock_escalation(rid_a2)  # noqa: SLF001
    assert loader_spy_a2.call_args is not None, "A2: loader was called"
    assert loader_spy_a2.call_args.args == (orch_a2._repo_root,), (  # noqa: SLF001
        f"A2: loader receives `self._repo_root` POSITIONALLY; got args="
        f"{loader_spy_a2.call_args.args!r}, expected ({orch_a2._repo_root!r},). "  # noqa: SLF001
        "Pins the repo_root routing (would break if refactored to kwarg or to "
        "load_anti_deadlock_settings() with no arg)"
    )

    orch_a3, _ = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    with patch(
        "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
        return_value=(True, 15, 3),
    ) as loader_spy_a3:
        orch_a3._maybe_emit_anti_deadlock_escalation(rid_a3)  # noqa: SLF001
    assert loader_spy_a3.call_count == 1, (
        f"A3: loader called EXACTLY ONCE per emit invocation; got "
        f"{loader_spy_a3.call_count}. Pins loader is NOT re-invoked across "
        "downstream branches (dedup / should_emit / emit)"
    )

    orch_a4, _ = make_dev_orchestrator()
    rid_a4 = orch_a4.create_run("default")
    with patch(
        "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
        return_value=(False, 15, 3),
    ):
        orch_a4._maybe_emit_anti_deadlock_escalation(rid_a4)  # noqa: SLF001
    assert _escalation_rows(orch_a4._store, rid_a4) == [], (  # noqa: SLF001
        "A4: enabled=False from loader flows through should_emit "
        "(short-circuits on `not enabled` at anti_deadlock.py:68) -> no emit"
    )

    orch_a5, _ = make_dev_orchestrator()
    rid_a5 = orch_a5.create_run("default")
    with patch(
        "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
        return_value=(True, 0, 3),
    ):
        orch_a5._maybe_emit_anti_deadlock_escalation(rid_a5)  # noqa: SLF001
    assert _escalation_rows(orch_a5._store, rid_a5) == [], (  # noqa: SLF001
        "A5: stall_minutes=0 from loader flows through should_emit "
        "(short-circuits on `stall_minutes <= 0` at anti_deadlock.py:68) -> no emit"
    )


def test_anti_deadlock_escalation_should_emit_delegation_5_axis() -> None:
    """Pin `should_emit_anti_deadlock_escalation` call shape at pipeline.py:1261-1267.

    Coverage delta vs existing tests: no test today verifies the orchestrator
    threads (rows, now=, enabled=, stall_minutes=, min_progress_events=) into
    the pure helper. A refactor swapping kwarg names / positions / drop the
    tz-aware `now` would silently break observable behavior under
    [tests/test_anti_deadlock.py] (which constructs its own kwargs).
    """
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    _append_stage_failed(mem_b1, rid_b1, "fo104_b1_stage")
    expected_rows = orch_b1._store.list_run_events(str(rid_b1))  # noqa: SLF001
    should_emit_spy_b1 = MagicMock(return_value=False)
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            should_emit_spy_b1,
        ),
    ):
        orch_b1._maybe_emit_anti_deadlock_escalation(rid_b1)  # noqa: SLF001
    assert should_emit_spy_b1.call_count == 1, "B1 setup: should_emit invoked once"
    positional = should_emit_spy_b1.call_args.args
    assert len(positional) == 1, (
        f"B1: should_emit receives exactly ONE positional arg (rows); got "
        f"{len(positional)} positional args"
    )
    assert positional[0] == expected_rows, (
        "B1: positional `rows` arg equals `list_run_events(str(run_id))` "
        "verbatim (full list, no filtering, includes the synthetic STAGE_FAILED "
        "row)"
    )

    orch_b2, _ = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("default")
    should_emit_spy_b2 = MagicMock(return_value=False)
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 17, 5),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            should_emit_spy_b2,
        ),
    ):
        orch_b2._maybe_emit_anti_deadlock_escalation(rid_b2)  # noqa: SLF001
    kwargs_b2 = dict(should_emit_spy_b2.call_args.kwargs)
    kwargs_b2.pop("now", None)
    assert kwargs_b2 == {
        "enabled": True,
        "stall_minutes": 17,
        "min_progress_events": 5,
    }, (
        f"B2: should_emit kwargs propagate VERBATIM from loader tuple "
        f"`(True, 17, 5)` -> `enabled=True, stall_minutes=17, "
        f"min_progress_events=5`; got {kwargs_b2!r}. Pins tuple-unpack "
        "ordering at pipeline.py:1253 (would silently swap if positions "
        "reversed)"
    )

    orch_b3, _ = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run("default")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=False,
        ),
    ):
        orch_b3._maybe_emit_anti_deadlock_escalation(rid_b3)  # noqa: SLF001
    assert _escalation_rows(orch_b3._store, rid_b3) == [], (  # noqa: SLF001
        "B3: should_emit returning False yields no RUN_ESCALATED row"
    )

    orch_b4, _ = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("default")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_b4._maybe_emit_anti_deadlock_escalation(rid_b4)  # noqa: SLF001
    assert len(_escalation_rows(orch_b4._store, rid_b4)) == 1, (  # noqa: SLF001
        "B4: should_emit returning True emits EXACTLY ONE RUN_ESCALATED row"
    )

    orch_b5, _ = make_dev_orchestrator()
    rid_b5 = orch_b5.create_run("default")
    should_emit_spy_b5 = MagicMock(return_value=False)
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            should_emit_spy_b5,
        ),
    ):
        orch_b5._maybe_emit_anti_deadlock_escalation(rid_b5)  # noqa: SLF001
    now_val = should_emit_spy_b5.call_args.kwargs.get("now")
    assert isinstance(now_val, datetime), (
        f"B5: `now` kwarg is a datetime instance; got {type(now_val).__name__}"
    )
    assert now_val.tzinfo is not None, (
        "B5: `now` kwarg is tz-AWARE (not naive). Pins `datetime.now(timezone.utc)`"
    )
    assert now_val.utcoffset() == timedelta(0), (
        f"B5: `now` kwarg is in UTC (utcoffset == 0); got "
        f"{now_val.utcoffset()!r}. Would silently break if refactored to "
        "naive `datetime.now()` or a non-UTC tz"
    )


def test_anti_deadlock_escalation_dedup_by_reason_code_5_axis() -> None:
    """Pin per-reason-code dedup at pipeline.py:1255-1260 + dedup-before-should_emit.

    Coverage delta vs fo102 C (`_maybe_auto_escalate`): fo102 C pins ANY-
    RUN_ESCALATED dedup (asymmetric -- any prior reason_code short-circuits).
    fo104 C pins PER-reason-code dedup (orthogonal -- only matching reason_code
    short-circuits). A "unify all escalation dedup" refactor would flip these
    two contracts; fo102 + fo104 together prevent silent unification.
    """
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("default")
    _append_escalation(mem_c1, rid_c1, _ANTI_DEADLOCK)
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_c1._maybe_emit_anti_deadlock_escalation(rid_c1)  # noqa: SLF001
    rows_c1 = _escalation_rows(mem_c1, rid_c1)
    assert len(rows_c1) == 1, (
        f"C1: prior RUN_ESCALATED with matching reason `{_ANTI_DEADLOCK}` "
        f"blocks new emit (only the seeded row remains); got {len(rows_c1)} rows"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    _append_escalation(mem_c2, rid_c2, "cumulative_stage_failures")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_c2._maybe_emit_anti_deadlock_escalation(rid_c2)  # noqa: SLF001
    rows_c2 = _escalation_rows(mem_c2, rid_c2)
    assert len(rows_c2) == 2, (
        f"C2: prior RUN_ESCALATED with a DIFFERENT reason_code "
        f"(`cumulative_stage_failures`) does NOT block emit; got "
        f"{len(rows_c2)} rows (expected seeded + new = 2). Pins **per-reason-"
        "code** semantics (asymmetric vs fo102 C's ANY-RUN_ESCALATED dedup "
        "for `_maybe_auto_escalate`)"
    )
    reasons_c2 = [(r.get("payload") or {}).get("reason_code") for r in rows_c2]
    assert _ANTI_DEADLOCK in reasons_c2, (
        f"C2: the newly emitted row carries reason_code `{_ANTI_DEADLOCK}`; "
        f"got reasons={reasons_c2!r}"
    )

    orch_c3, mem_c3 = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("default")
    _append_stage_failed(mem_c3, rid_c3, "fo104_c3_stage")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_c3._maybe_emit_anti_deadlock_escalation(rid_c3)  # noqa: SLF001
    rows_c3 = _escalation_rows(mem_c3, rid_c3)
    assert len(rows_c3) == 1, (
        f"C3: prior STAGE_FAILED row does NOT block emit; got "
        f"{len(rows_c3)} RUN_ESCALATED rows (expected 1). Pins the "
        "`event_type == RUN_ESCALATED.value` filter inside the dedup scan "
        "(would silently break if filter widened to all event_types with "
        "reason_code)"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    _append_escalation(mem_c4, rid_c4, _ANTI_DEADLOCK)
    _append_escalation(mem_c4, rid_c4, _ANTI_DEADLOCK)
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_c4._maybe_emit_anti_deadlock_escalation(rid_c4)  # noqa: SLF001
    assert len(_escalation_rows(mem_c4, rid_c4)) == 2, (
        "C4: TWO prior matching RUN_ESCALATED rows still block (any-of "
        "semantics; `any()` short-circuits on first match -- second seed "
        "is irrelevant but still proves no extra emission slips through)"
    )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = orch_c5.create_run("default")
    _append_escalation(mem_c5, rid_c5, _ANTI_DEADLOCK)
    should_emit_spy_c5 = MagicMock(return_value=True)
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            should_emit_spy_c5,
        ),
    ):
        orch_c5._maybe_emit_anti_deadlock_escalation(rid_c5)  # noqa: SLF001
    assert should_emit_spy_c5.call_count == 0, (
        f"C5: dedup fires BEFORE should_emit; spy `call_count == 0` when a "
        f"prior matching RUN_ESCALATED exists. Got "
        f"{should_emit_spy_c5.call_count}. Pins early-return order at "
        "pipeline.py:1255-1267 (would silently break if refactored to "
        "compute should_emit first)"
    )


def test_anti_deadlock_escalation_emit_shape_and_notes_5_axis() -> None:
    """Pin happy-path emit shape + literal notes format at pipeline.py:1269-1281.

    Coverage delta vs existing tests: no test today verifies (a) the exact
    f-string notes format, (b) `actor_id="system:orchestrator"` literal,
    (c) `reason_code="anti_deadlock_insufficient_progress"` literal, (d) loader
    tuple positions flow into the notes string in the correct order, (e) the
    payload has no extraneous fields (no `policy_snapshot_id` leak).
    """
    orch_d1, mem_d1 = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_d1._maybe_emit_anti_deadlock_escalation(rid_d1)  # noqa: SLF001
    rows_d1 = _escalation_rows(mem_d1, rid_d1)
    assert len(rows_d1) == 1, (
        f"D1: happy path emits EXACTLY ONE RUN_ESCALATED row; got {len(rows_d1)}"
    )

    payload_d2 = rows_d1[0].get("payload") or {}
    assert payload_d2.get("reason_code") == _ANTI_DEADLOCK, (
        f"D2: payload.reason_code literal == `{_ANTI_DEADLOCK}`; got "
        f"{payload_d2.get('reason_code')!r}"
    )
    assert payload_d2.get("actor_id") == "system:orchestrator", (
        f"D2: payload.actor_id literal == `system:orchestrator`; got "
        f"{payload_d2.get('actor_id')!r}"
    )

    assert payload_d2.get("notes") == "stall_minutes=15 min_progress_events=3", (
        f"D3: notes literal format == `stall_minutes=15 min_progress_events=3` "
        f"(exact f-string match); got {payload_d2.get('notes')!r}. Distinct "
        "from fo102's `threshold=N cumulative_*=n` format -- a refactor "
        "harmonizing all escalation `notes` strings would break this"
    )

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("default")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 99, 0),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_d4._maybe_emit_anti_deadlock_escalation(rid_d4)  # noqa: SLF001
    rows_d4 = _escalation_rows(mem_d4, rid_d4)
    assert len(rows_d4) == 1, "D4 setup: exactly one emit"
    notes_d4 = (rows_d4[0].get("payload") or {}).get("notes")
    assert notes_d4 == "stall_minutes=99 min_progress_events=0", (
        f"D4: with loader returning `(True, 99, 0)`, notes == "
        f"`stall_minutes=99 min_progress_events=0`; got {notes_d4!r}. Pins "
        "both loader-tuple positions (stall_minutes, min_progress_events) "
        "flow into the f-string in the correct order (would silently swap "
        "if positions reversed)"
    )

    payload_d5 = rows_d1[0].get("payload") or {}
    assert payload_d5.get("policy_snapshot_id") is None, (
        f"D5: payload.policy_snapshot_id stays None (no leak from "
        "orchestrator state into the escalation payload); got "
        f"{payload_d5.get('policy_snapshot_id')!r}"
    )
    populated_keys = {
        k for k, v in payload_d5.items() if v is not None and v != []
    }
    assert populated_keys == {"actor_id", "reason_code", "notes"}, (
        f"D5: only `actor_id`, `reason_code`, `notes` are populated on the "
        f"emitted RunEscalatedPayload; got populated_keys={populated_keys!r}. "
        "Pins no unintended payload attribute spill (would catch a future "
        "refactor that started passing `policy_snapshot_id` or any other "
        "field through the emitter)"
    )
