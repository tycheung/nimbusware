from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    RunEscalatedEvent,
    RunEscalatedPayload,
    StageFailedEvent,
    StageFailedPayload,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from nimbusware_store.memory import InMemoryEventStore


_RUN_ESCALATED = "run.escalated"
_VERIFIER_CHECKPOINT = "verifier_failure_checkpoint"
_ANTI_DEADLOCK = "anti_deadlock_insufficient_progress"
_VERIFIER_NOTES_LITERAL = "escalate_on_first_verifier_failure policy"


def _escalation_rows(mem: InMemoryEventStore, rid: UUID) -> list[dict[str, Any]]:
    """Return ``run.escalated`` rows for the run, in store order."""
    return [r for r in mem.list_run_events(str(rid)) if r.get("event_type") == _RUN_ESCALATED]


def _append_escalation(mem: InMemoryEventStore, rid: UUID, reason: str) -> None:
    """Append one synthetic ``RUN_ESCALATED`` row with the given reason_code."""
    mem.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="system:fo106_seed",
                reason_code=reason,
                notes="fo106 seed",
            ),
        ),
    )


def _append_stage_failed(mem: InMemoryEventStore, rid: UUID, name: str) -> None:
    """Append one synthetic ``STAGE_FAILED`` row (event_type filter foil)."""
    mem.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=StageFailedPayload(
                stage_name=name,
                reason_code="fo106_unrelated",
                message="fo106 unrelated stage failure",
            ),
        ),
    )


def test_verifier_failure_checkpoint_suppress_and_loader_5_axis() -> None:
    orch_a1, mem_a1 = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("escalation_suppress_on")
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ) as loader_spy_a1:
        orch_a1._maybe_escalate_verifier_failure_checkpoint(rid_a1)  # noqa: SLF001
    assert loader_spy_a1.call_count == 0, (
        "A1: suppress fork short-circuits BEFORE load_escalate_on_first_verifier_failure; "
        "fo88 B5 only proves no emit, this pins the loader-NOT-called ordering "
        "invariant (loader sits AFTER the suppress check at pipeline.py:1406-1408)"
    )
    assert _escalation_rows(mem_a1, rid_a1) == [], (
        "A1: suppress fork emits no RUN_ESCALATED (control reaffirms fo88 B5)"
    )

    orch_a2, _ = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=False,
    ) as loader_spy_a2:
        orch_a2._maybe_escalate_verifier_failure_checkpoint(rid_a2)  # noqa: SLF001
    assert loader_spy_a2.call_args is not None, "A2: loader was called"
    assert loader_spy_a2.call_args.args == (orch_a2._repo_root,), (  # noqa: SLF001
        f"A2: loader receives `self._repo_root` POSITIONALLY; got args="
        f"{loader_spy_a2.call_args.args!r}, expected ({orch_a2._repo_root!r},). "  # noqa: SLF001
        "Pins repo_root routing (would break if refactored to kwarg or to "
        "load_escalate_on_first_verifier_failure() with no arg)"
    )

    orch_a3, _ = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ) as loader_spy_a3:
        orch_a3._maybe_escalate_verifier_failure_checkpoint(rid_a3)  # noqa: SLF001
    assert loader_spy_a3.call_count == 1, (
        f"A3: loader called EXACTLY ONCE per emit invocation; got "
        f"{loader_spy_a3.call_count}. Pins loader is NOT re-invoked across "
        "downstream branches (rows scan / dedup / emit)"
    )

    orch_a4, mem_a4 = make_dev_orchestrator()
    rid_a4 = orch_a4.create_run("default")
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=False,
    ):
        orch_a4._maybe_escalate_verifier_failure_checkpoint(rid_a4)  # noqa: SLF001
    assert _escalation_rows(mem_a4, rid_a4) == [], (
        "A4: loader returns False -> no emit. Pins the `if not load_...: return` "
        "early-return arm at pipeline.py:1408-1409"
    )

    orch_a5, _ = make_dev_orchestrator()
    rid_a5 = orch_a5.create_run("default")
    with (
        patch.object(
            orch_a5,
            "_workflow_suppresses_automatic_escalation",
            wraps=orch_a5._workflow_suppresses_automatic_escalation,  # noqa: SLF001
        ) as guard_spy_a5,
        patch(
            "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
            return_value=False,
        ),
    ):
        orch_a5._maybe_escalate_verifier_failure_checkpoint(rid_a5)  # noqa: SLF001
    assert guard_spy_a5.call_count == 1, (
        f"A5: _workflow_suppresses_automatic_escalation called EXACTLY ONCE; "
        f"got {guard_spy_a5.call_count}"
    )
    assert guard_spy_a5.call_args.args == (rid_a5,), (
        f"A5: shared suppress guard receives `run_id` positionally; got "
        f"args={guard_spy_a5.call_args.args!r}. Pins delegation to the shared "
        "guard used by fo88 / fo102 / fo104 / fo106"
    )


def test_verifier_failure_checkpoint_happy_path_and_literal_notes_5_axis() -> None:
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_b1._maybe_escalate_verifier_failure_checkpoint(rid_b1)  # noqa: SLF001
    rows_b1 = _escalation_rows(mem_b1, rid_b1)
    assert len(rows_b1) == 1, (
        f"B1: happy path emits EXACTLY ONE RUN_ESCALATED row; got {len(rows_b1)}"
    )

    payload_b = rows_b1[0].get("payload") or {}
    assert payload_b.get("reason_code") == _VERIFIER_CHECKPOINT, (
        f"B2: payload.reason_code literal == `{_VERIFIER_CHECKPOINT}`; got "
        f"{payload_b.get('reason_code')!r}"
    )
    assert payload_b.get("actor_id") == "system:orchestrator", (
        f"B3: payload.actor_id literal == `system:orchestrator`; got "
        f"{payload_b.get('actor_id')!r}. Pins cross-emitter actor consistency "
        "(same literal as fo104 D2)"
    )

    assert payload_b.get("notes") == _VERIFIER_NOTES_LITERAL, (
        f"B4: payload.notes == LITERAL `{_VERIFIER_NOTES_LITERAL}` (exact "
        f"string match, NOT parameterized); got {payload_b.get('notes')!r}. "
        "KEY DIVERGENCE from fo104 D3 (f-string `stall_minutes={S} "
        "min_progress_events={M}`) and fo102's `threshold=N cumulative_*=n`. "
        "A `harmonize all escalation notes` refactor would silently break this"
    )
    orch_b4_repeat, mem_b4_repeat = make_dev_orchestrator()
    rid_b4_repeat = orch_b4_repeat.create_run("default")
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_b4_repeat._maybe_escalate_verifier_failure_checkpoint(rid_b4_repeat)  # noqa: SLF001
    repeat_notes = (_escalation_rows(mem_b4_repeat, rid_b4_repeat)[0].get("payload") or {}).get(
        "notes"
    )
    assert repeat_notes == _VERIFIER_NOTES_LITERAL, (
        f"B4 invariance: a second fresh-orchestrator invocation yields the "
        f"IDENTICAL notes string `{_VERIFIER_NOTES_LITERAL}`; got "
        f"{repeat_notes!r}. Pins notes is NOT parameterized on call / run state"
    )

    assert payload_b.get("policy_snapshot_id") is None, (
        f"B5: payload.policy_snapshot_id stays None (no leak from "
        f"orchestrator state); got {payload_b.get('policy_snapshot_id')!r}"
    )
    populated_keys = {k for k, v in payload_b.items() if v is not None and v != []}
    assert populated_keys == {"actor_id", "reason_code", "notes"}, (
        f"B5: only `actor_id`, `reason_code`, `notes` are populated; got "
        f"populated_keys={populated_keys!r}. Pins no unintended payload "
        "attribute spill (same shape contract as fo104 D5)"
    )


def test_verifier_failure_checkpoint_dedup_by_reason_code_5_axis() -> None:
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("default")
    _append_escalation(mem_c1, rid_c1, _VERIFIER_CHECKPOINT)
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_c1._maybe_escalate_verifier_failure_checkpoint(rid_c1)  # noqa: SLF001
    rows_c1 = _escalation_rows(mem_c1, rid_c1)
    assert len(rows_c1) == 1, (
        f"C1: prior RUN_ESCALATED with matching reason `{_VERIFIER_CHECKPOINT}` "
        f"blocks new emit (only the seeded row remains); got {len(rows_c1)}"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    _append_escalation(mem_c2, rid_c2, _ANTI_DEADLOCK)
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_c2._maybe_escalate_verifier_failure_checkpoint(rid_c2)  # noqa: SLF001
    rows_c2 = _escalation_rows(mem_c2, rid_c2)
    assert len(rows_c2) == 2, (
        f"C2: prior RUN_ESCALATED with DIFFERENT reason_code "
        f"(`{_ANTI_DEADLOCK}`) does NOT block emit; got {len(rows_c2)} rows "
        "(expected seeded + new = 2). Pins **per-reason-code** semantics "
        "(parallel to fo104 C2 with the reasons swapped; distinct from "
        "fo102 C's ANY-RUN_ESCALATED dedup on _maybe_auto_escalate)"
    )

    orch_c3, mem_c3 = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("default")
    _append_stage_failed(mem_c3, rid_c3, "fo106_c3_stage")
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_c3._maybe_escalate_verifier_failure_checkpoint(rid_c3)  # noqa: SLF001
    assert len(_escalation_rows(mem_c3, rid_c3)) == 1, (
        "C3: prior STAGE_FAILED row does NOT block emit (different event_type). "
        "Pins the `event_type == RUN_ESCALATED.value` filter inside the dedup scan"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    _append_escalation(mem_c4, rid_c4, _VERIFIER_CHECKPOINT)
    _append_escalation(mem_c4, rid_c4, _VERIFIER_CHECKPOINT)
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_c4._maybe_escalate_verifier_failure_checkpoint(rid_c4)  # noqa: SLF001
    assert len(_escalation_rows(mem_c4, rid_c4)) == 2, (
        "C4: TWO prior matching RUN_ESCALATED rows still block (any-of "
        "semantics; `any()` short-circuits on first match)"
    )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = orch_c5.create_run("default")
    _append_escalation(mem_c5, rid_c5, _VERIFIER_CHECKPOINT)
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
            return_value=True,
        ),
        patch.object(
            orch_c5._store,  # noqa: SLF001
            "append",
            wraps=orch_c5._store.append,  # noqa: SLF001
        ) as append_spy_c5,
    ):
        baseline_calls = append_spy_c5.call_count
        orch_c5._maybe_escalate_verifier_failure_checkpoint(rid_c5)  # noqa: SLF001
        post_calls = append_spy_c5.call_count
    assert post_calls == baseline_calls, (
        f"C5: dedup-blocked path means `store.append` is NOT called; "
        f"baseline={baseline_calls}, post={post_calls}. Pins early-return "
        "order: dedup triggers BEFORE the append at pipeline.py:1417 (would "
        "silently break if refactored to construct the event first)"
    )


def test_verifier_failure_checkpoint_cross_emitter_independence_with_anti_deadlock_5_axis() -> None:
    orch_d1, mem_d1 = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
            return_value=True,
        ),
        patch(
            "nimbusware_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_d1._maybe_escalate_verifier_failure_checkpoint(rid_d1)  # noqa: SLF001
        orch_d1._maybe_emit_anti_deadlock_escalation(rid_d1)  # noqa: SLF001
    reasons_d1 = {
        (r.get("payload") or {}).get("reason_code") for r in _escalation_rows(mem_d1, rid_d1)
    }
    assert reasons_d1 == {_VERIFIER_CHECKPOINT, _ANTI_DEADLOCK}, (
        f"D1: verifier then anti-deadlock emit both succeed; got reasons="
        f"{reasons_d1!r}. Pins forward-direction cross-emitter independence "
        "(prior verifier RUN_ESCALATED does NOT block subsequent anti-deadlock)"
    )

    orch_d2, mem_d2 = make_dev_orchestrator()
    rid_d2 = orch_d2.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
            return_value=True,
        ),
        patch(
            "nimbusware_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_d2._maybe_emit_anti_deadlock_escalation(rid_d2)  # noqa: SLF001
        orch_d2._maybe_escalate_verifier_failure_checkpoint(rid_d2)  # noqa: SLF001
    reasons_d2 = {
        (r.get("payload") or {}).get("reason_code") for r in _escalation_rows(mem_d2, rid_d2)
    }
    assert reasons_d2 == {_VERIFIER_CHECKPOINT, _ANTI_DEADLOCK}, (
        f"D2: anti-deadlock then verifier emit both succeed; got reasons="
        f"{reasons_d2!r}. Pins reverse-direction cross-emitter independence "
        "(prior anti-deadlock RUN_ESCALATED does NOT block subsequent verifier)"
    )

    orch_d3, mem_d3 = make_dev_orchestrator()
    rid_d3 = orch_d3.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
            return_value=True,
        ),
        patch(
            "nimbusware_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_d3._maybe_escalate_verifier_failure_checkpoint(rid_d3)  # noqa: SLF001
        orch_d3._maybe_emit_anti_deadlock_escalation(rid_d3)  # noqa: SLF001
        orch_d3._maybe_escalate_verifier_failure_checkpoint(rid_d3)  # noqa: SLF001
        orch_d3._maybe_emit_anti_deadlock_escalation(rid_d3)  # noqa: SLF001
    assert len(_escalation_rows(mem_d3, rid_d3)) == 2, (
        f"D3: double-call both emitters yields EXACTLY 2 RUN_ESCALATED rows "
        f"total (each emitter's own dedup persists independently after the "
        f"first round); got {len(_escalation_rows(mem_d3, rid_d3))}. Pins that "
        "within-emitter dedup blocks self-repeat WITHOUT leaking into "
        "cross-emitter state"
    )

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("escalation_suppress_on")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
            return_value=True,
        ),
        patch(
            "nimbusware_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 15, 3),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_d4._maybe_escalate_verifier_failure_checkpoint(rid_d4)  # noqa: SLF001
        orch_d4._maybe_emit_anti_deadlock_escalation(rid_d4)  # noqa: SLF001
    assert _escalation_rows(mem_d4, rid_d4) == [], (
        "D4: shared suppress fork blocks BOTH emitters on "
        "`escalation_suppress_on` (zero RUN_ESCALATED rows from either). "
        "Pins the **shared guard invariant**: "
        "`_workflow_suppresses_automatic_escalation` is the single suppress "
        "mechanism. fo88 + fo104 A1 + fo106 A1 prove individual-emitter "
        "precedence; fo106 D4 proves cross-emitter consistency"
    )

    orch_d5, mem_d5 = make_dev_orchestrator()
    rid_d5 = orch_d5.create_run("default")
    _append_escalation(mem_d5, rid_d5, _ANTI_DEADLOCK)
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_d5._maybe_escalate_verifier_failure_checkpoint(rid_d5)  # noqa: SLF001
    rows_d5 = _escalation_rows(mem_d5, rid_d5)
    reasons_d5 = [(r.get("payload") or {}).get("reason_code") for r in rows_d5]
    assert len(rows_d5) == 2, (
        f"D5: pre-seed `{_ANTI_DEADLOCK}` RUN_ESCALATED + call verifier "
        f"emitter -> exactly 2 RUN_ESCALATED rows (seeded + new verifier); "
        f"got {len(rows_d5)}"
    )
    assert _VERIFIER_CHECKPOINT in reasons_d5 and _ANTI_DEADLOCK in reasons_d5, (
        f"D5: both reason_codes present after the cross-emitter pre-seed; "
        f"got reasons={reasons_d5!r}. Surgical proof of cross-reason "
        "independence (parallel to C2 but with the explicit cross-emitter framing)"
    )
