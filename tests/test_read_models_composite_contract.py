"""``read_models.py`` composite direct contracts.

Three public surfaces in [read_models.py:16-85](packages/hermes_orchestrator/read_models.py)
form the data layer for ``GET /v1/runs/{run_id}`` and ``GET /v1/runs``:

* ``build_run_summary(rows)`` (lines 19-74) -- 8-field dict derived
 from ``list_run_events`` rows. Multiple defensive arms: empty-row
 short-circuit, 4-state status ladder (terminal > started > created
 > running-default), workflow_profile extraction (LAST-wins via
 no-break), terminal extraction (LAST-wins via no-break),
 run_created_metadata extraction (FIRST-wins via break),
 findings_count sum, has_escalation any-flag, event_count, and
 latest_event_type.
* ``run_has_started(rows)`` (lines 77-85) -- RUN_STARTED scan with
 ``isinstance(ev, RunStartedEvent)`` guard. ZERO direct unit tests
 AND ZERO callers in the codebase as of fo115 -- pure unpinned
 public surface.
* ``RUN_LIST_FILTER_STATUSES`` (line 16) --
 ``frozenset({"created", "running", "terminal"})``; ``"unknown"``
 intentionally absent (empty-run sentinel).

Existing coverage is sampled only:

* [tests/test_read_models.py](tests/test_read_models.py) --
 ``test_build_run_summary_created`` samples 3 of 8 fields on a
 single RUN_CREATED row; ``test_build_run_summary_empty`` samples 1
 of 8 default fields.
* ``run_has_started`` has NO direct test.
* ``RUN_LIST_FILTER_STATUSES`` has NO direct test.

fo115 closes these in 4 parts / 20 axes (source unchanged).

Five KEY DIVERGENCES are pinned across the matrix:

* **FIRST-wins vs LAST-wins inside the same function** --
 ``workflow_profile`` overwrites on every RUN_CREATED (no break);
 ``run_created_metadata`` returns the FIRST RUN_CREATED's metadata
 (break statement). Part C C4/C5 share the SAME 2-RUN_CREATED row
 sequence but disagree on which RUN_CREATED is authoritative,
 proving the asymmetry IS the contract.
* **Status ladder priority is terminal > started > created** -- a
 sequence containing RUN_STARTED AND RUN_FAILED returns
 ``"terminal"``, not ``"running"``. Part B B4 pins it.
* **Default ``"running"`` arm** -- non-empty rows with NO terminal,
 NO RUN_STARTED, latest NOT RUN_CREATED -> ``status="running"``
 (the line-47 default). Distinct from the line-50 started-branch
 ``"running"``. Part B B2 pins it via a RUN_CREATED + STAGE_STARTED
 sequence (NO RUN_STARTED, latest is STAGE_STARTED).
* **``"unknown"`` is NOT in ``RUN_LIST_FILTER_STATUSES``** --
 empty-runs intentionally fall outside the API filter set; this is
 the contract for ``GET /v1/runs?status=``. Part A A2 pins it.
* **``run_has_started`` does NOT catch ``ValidationError``** -- a
 refactor wrapping the validate_event_dict call in try/except
 would silently swallow malformed RUN_STARTED rows and flip
 raise -> False. Part D D5 pins via ``pytest.raises``.

Four parts:

* **Part A** -- empty-rows baseline + ``RUN_LIST_FILTER_STATUSES``
 membership + ``run_has_started`` empty / non-started cases.
* **Part B** -- status ladder priority + terminal_event_type field
 (5 transitions through the 4-state ladder).
* **Part C** -- workflow_profile vs run_created_metadata FIRST-vs-LAST
 divergence (same row sequence, two assertions).
* **Part D** -- counters / flags / event_count + latest_event_type
 sweep + ``run_has_started`` happy / position-independent / raise
 on malformed RUN_STARTED.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    RunCompletedEvent,
    RunCompletedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    RunFailedEvent,
    RunFailedPayload,
    RunStartedEvent,
    RunStartedPayload,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
)
from hermes_orchestrator.read_models import (
    RUN_LIST_FILTER_STATUSES,
    build_run_summary,
    run_has_started,
)
from hermes_store.memory import InMemoryEventStore

_BACKEND_WRITER = UUID("44444444-4444-4444-8444-444444444404")


def _make_store_and_run() -> tuple[InMemoryEventStore, UUID]:
    """Fresh ``InMemoryEventStore`` + a new run UUID for one axis."""
    return InMemoryEventStore(), uuid4()


def _append_run_created(
    store: InMemoryEventStore,
    run_id: UUID,
    *,
    workflow_profile: str = "default",
    metadata: dict[str, Any] | None = None,
) -> None:
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile=workflow_profile,
                policy_version="1",
                config_snapshot_id="snap",
            ),
            metadata=metadata or {},
        ),
    )


def _append_run_started(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="fo115_actor"),
        ),
    )


def _append_run_failed(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunFailedEvent(
            event_type=EventType.RUN_FAILED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunFailedPayload(
                reason_code="fo115_reason",
                message="fo115 terminal failure",
            ),
        ),
    )


def _append_run_completed(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunCompletedEvent(
            event_type=EventType.RUN_COMPLETED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCompletedPayload(summary="fo115 happy completion"),
        ),
    )


def _append_run_escalated(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="fo115_human",
                reason_code="fo115_escalation",
            ),
        ),
    )


def _append_stage_started(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="fo115_stage", attempt=1),
        ),
    )


def _append_finding_created(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=FindingCreatedPayload(
                finding_id=uuid4(),
                category="fo115_category",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="fo115",
                repro_steps=[],
                required_fixes=[],
            ),
        ),
    )


def test_read_models_empty_rows_and_filter_set_and_run_has_started_baseline(
    tmp_path: Any,  # noqa: ARG001  (unused; pytest-supplied fixture for parity)
) -> None:
    """Pin empty-rows defaults + RUN_LIST_FILTER_STATUSES + run_has_started baseline (5 axes).

    A1: empty rows -> exact 8-field default dict.
    A2: ``"unknown"`` NOT in ``RUN_LIST_FILTER_STATUSES``; the 3
        non-empty statuses ARE.
    A3: ``RUN_LIST_FILTER_STATUSES`` IS a ``frozenset`` and equals
        ``frozenset({"created", "running", "terminal"})``.
    A4: ``run_has_started([])`` -> False.
    A5: ``run_has_started([RUN_FAILED row])`` -> False (no RUN_STARTED
        present; pins the function is RUN_STARTED-specific, not a
        generic "is run active?" probe).
    """
    expected_empty = {
        "status": "unknown",
        "workflow_profile": None,
        "event_count": 0,
        "latest_event_type": "unknown",
        "terminal_event_type": None,
        "findings_count": 0,
        "has_escalation": False,
        "run_created_metadata": {},
        "persona_assignment": None,
    }
    actual_empty = build_run_summary([])
    assert actual_empty == expected_empty, (
        f"A1: build_run_summary([]) must return exactly the 9-field "
        f"default dict {expected_empty!r}, got {actual_empty!r}. "
        "A refactor flipping ANY single default value surfaces as a "
        "single mismatched key in this equality check"
    )

    assert "unknown" not in RUN_LIST_FILTER_STATUSES, (
        "A2: `\"unknown\"` MUST be excluded from RUN_LIST_FILTER_STATUSES "
        "-- empty runs are intentionally outside the GET /v1/runs?status= "
        "filter set. A refactor adding 'unknown' would let API clients "
        "filter for runs that have NO events (data anomaly), which is "
        "the explicit anti-contract"
    )
    for status in ("created", "running", "terminal"):
        assert status in RUN_LIST_FILTER_STATUSES, (
            f"A2: `\"{status}\"` MUST be present in RUN_LIST_FILTER_STATUSES "
            "-- it is the GET /v1/runs?status= filter set"
        )

    assert isinstance(RUN_LIST_FILTER_STATUSES, frozenset), (
        f"A3: RUN_LIST_FILTER_STATUSES must be a frozenset for "
        "immutability guarantees on the module-level constant; got "
        f"{type(RUN_LIST_FILTER_STATUSES).__name__!r}. A refactor "
        "swapping to a regular set or list would permit accidental "
        "in-place mutation by importers"
    )
    assert RUN_LIST_FILTER_STATUSES == frozenset({"created", "running", "terminal"}), (
        f"A3: exact 3-element membership pinned. Got "
        f"{RUN_LIST_FILTER_STATUSES!r}. A refactor adding/removing a "
        "status value would surface as an inequality here"
    )

    assert run_has_started([]) is False, (
        "A4: run_has_started([]) must return False. Empty rows -> the "
        "for-loop body never executes -> returns the final False "
        "literal. A refactor adding a default-True or raising on "
        "empty would FLIP this axis"
    )

    a5_store, a5_rid = _make_store_and_run()
    _append_run_failed(a5_store, a5_rid)
    a5_rows = a5_store.list_run_events(str(a5_rid))
    assert run_has_started(a5_rows) is False, (
        "A5: run_has_started on rows containing ONLY a RUN_FAILED row "
        "must return False. Proves the function is RUN_STARTED-specific "
        "(not a generic active-run probe) -- a refactor checking for "
        "any 'lifecycle' event would FLIP this"
    )


def test_build_run_summary_status_ladder_priority_and_terminal_event_type_contract() -> None:
    """Pin 4-state status ladder + terminal_event_type field (5 axes).

    The ladder at lines 47-53 has three explicit transitions stacked
    against a default ``"running"`` initializer:

    1. Default: ``status = "running"`` (line 47).
    2. ``if terminal:`` -> ``"terminal"`` (lines 48-49).
    3. ``elif any(... RUN_STARTED ...):`` -> ``"running"`` (lines 50-51).
    4. ``elif latest_et == RUN_CREATED:`` -> ``"created"`` (lines 52-53).

    The 5 axes pin EACH transition:

    * B1: RUN_CREATED only -> ``"created"`` (branch 4).
    * B2: RUN_CREATED + STAGE_STARTED -> ``"running"`` via DEFAULT
      (branch 1, falls through because no terminal / no started / not
      latest=RUN_CREATED).
    * B3: RUN_CREATED + RUN_STARTED -> ``"running"`` via STARTED
      (branch 3).
    * B4: RUN_CREATED + RUN_STARTED + RUN_FAILED -> ``"terminal"``
      (branch 2 BEATS branch 3 -- the priority is terminal > started).
    * B5: RUN_CREATED + RUN_COMPLETED -> ``"terminal"`` AND
      terminal_event_type == ``"run.completed"`` (pins both RUN_COMPLETED
      as a terminal trigger AND the terminal_event_type field tracks
      the exact event_type, not just the boolean state).
    """
    b1_store, b1_rid = _make_store_and_run()
    _append_run_created(b1_store, b1_rid, workflow_profile="b1_profile")
    b1_summary = build_run_summary(b1_store.list_run_events(str(b1_rid)))
    assert b1_summary["status"] == "created", (
        f"B1: RUN_CREATED only -> status='created' (latest is RUN_CREATED, "
        f"no started, no terminal). Got {b1_summary['status']!r}"
    )
    assert b1_summary["latest_event_type"] == "run.created", (
        f"B1(latest): latest_event_type tracks rows[-1]['event_type']. "
        f"Got {b1_summary['latest_event_type']!r}"
    )
    assert b1_summary["terminal_event_type"] is None, (
        f"B1(terminal): no RUN_FAILED/RUN_COMPLETED -> terminal_event_type "
        f"stays None. Got {b1_summary['terminal_event_type']!r}"
    )

    b2_store, b2_rid = _make_store_and_run()
    _append_run_created(b2_store, b2_rid)
    _append_stage_started(b2_store, b2_rid)
    b2_summary = build_run_summary(b2_store.list_run_events(str(b2_rid)))
    assert b2_summary["status"] == "running", (
        f"B2: RUN_CREATED + STAGE_STARTED (NO RUN_STARTED) -> status='running' "
        "via the DEFAULT branch (line 47). The latest_event_type is NOT "
        "RUN_CREATED (it's STAGE_STARTED) so the created-branch is also "
        f"skipped. Got {b2_summary['status']!r}. KEY DIVERGENCE pin: a "
        "refactor swapping the default 'running' for 'unknown' or 'created' "
        "would FLIP this from 'running' to that value"
    )
    assert b2_summary["latest_event_type"] == "stage.started", (
        f"B2(latest): latest is STAGE_STARTED. Got "
        f"{b2_summary['latest_event_type']!r}"
    )

    b3_store, b3_rid = _make_store_and_run()
    _append_run_created(b3_store, b3_rid)
    _append_run_started(b3_store, b3_rid)
    b3_summary = build_run_summary(b3_store.list_run_events(str(b3_rid)))
    assert b3_summary["status"] == "running", (
        f"B3: RUN_CREATED + RUN_STARTED -> status='running' via the STARTED "
        "branch (line 50). Same return value as B2 but DIFFERENT code path. "
        f"Got {b3_summary['status']!r}"
    )
    assert b3_summary["latest_event_type"] == "run.started", (
        f"B3(latest): latest is RUN_STARTED. Got "
        f"{b3_summary['latest_event_type']!r}"
    )

    b4_store, b4_rid = _make_store_and_run()
    _append_run_created(b4_store, b4_rid)
    _append_run_started(b4_store, b4_rid)
    _append_run_failed(b4_store, b4_rid)
    b4_summary = build_run_summary(b4_store.list_run_events(str(b4_rid)))
    assert b4_summary["status"] == "terminal", (
        f"B4: RUN_CREATED + RUN_STARTED + RUN_FAILED -> status='terminal' "
        "(terminal beats started -- pins the ladder priority). A refactor "
        "reordering the elif chain to check started BEFORE terminal would "
        f"flip this to 'running'. Got {b4_summary['status']!r}"
    )
    assert b4_summary["terminal_event_type"] == "run.failed", (
        f"B4(terminal_event_type): terminal_event_type tracks the EXACT "
        "event_type that triggered the terminal status, not just the "
        f"boolean state. Got {b4_summary['terminal_event_type']!r}"
    )

    b5_store, b5_rid = _make_store_and_run()
    _append_run_created(b5_store, b5_rid)
    _append_run_completed(b5_store, b5_rid)
    b5_summary = build_run_summary(b5_store.list_run_events(str(b5_rid)))
    assert b5_summary["status"] == "terminal", (
        f"B5: RUN_CREATED + RUN_COMPLETED (NO RUN_STARTED) -> status='terminal'. "
        "Pins RUN_COMPLETED as a terminal trigger AND that no RUN_STARTED "
        f"is required to reach terminal. Got {b5_summary['status']!r}"
    )
    assert b5_summary["terminal_event_type"] == "run.completed", (
        f"B5(terminal_event_type): RUN_COMPLETED's event_type is "
        f"'run.completed', distinct from 'run.failed'. Got "
        f"{b5_summary['terminal_event_type']!r}. A refactor consolidating "
        "the two terminal types into a single 'terminal' string in "
        "terminal_event_type would FLIP this axis"
    )


def test_build_run_summary_first_vs_last_run_created_extraction_divergence_contract() -> None:
    """Pin workflow_profile (LAST-wins) vs run_created_metadata (FIRST-wins) (5 axes).

    The implementation has TWO loops over the same rows that both
    look for RUN_CREATED events but extract DIFFERENT fields with
    DIFFERENT termination semantics:

    Loop 1 (lines 32-40): workflow_profile -- NO break, so the LAST
    RUN_CREATED wins.

    Loop 2 (lines 56-64): run_created_metadata -- HAS break, so the
    FIRST RUN_CREATED wins.

    A "harmonize the two loops" refactor would have to pick ONE
    behavior and break the other field's contract. The 5 axes pin
    both behaviors with co-located evidence:

    * C1: single RUN_CREATED with workflow_profile -> happy path.
    * C2: single RUN_CREATED with non-empty metadata -> happy +
      ``dict()`` copy semantics.
    * C3: NO RUN_CREATED in rows -> both fields stay at initial
      defaults.
    * C4: TWO RUN_CREATED events with different workflow_profile ->
      LAST wins for workflow_profile.
    * C5: SAME 2-RUN_CREATED rows as C4 (in this same test) but with
      different metadata -> FIRST wins for run_created_metadata.
      KEY DIVERGENCE pin: same rows, opposite resolution.
    """
    c1_store, c1_rid = _make_store_and_run()
    _append_run_created(c1_store, c1_rid, workflow_profile="alpha")
    c1_summary = build_run_summary(c1_store.list_run_events(str(c1_rid)))
    assert c1_summary["workflow_profile"] == "alpha", (
        f"C1: single RUN_CREATED with workflow_profile='alpha' -> "
        f"summary['workflow_profile']='alpha'. Got "
        f"{c1_summary['workflow_profile']!r}"
    )

    c2_store, c2_rid = _make_store_and_run()
    c2_metadata = {"actor": "fo115_test", "trace_id": "xyz"}
    _append_run_created(c2_store, c2_rid, metadata=c2_metadata)
    c2_summary = build_run_summary(c2_store.list_run_events(str(c2_rid)))
    assert c2_summary["run_created_metadata"] == c2_metadata, (
        f"C2(value): single RUN_CREATED with metadata={c2_metadata!r} -> "
        f"run_created_metadata equals it. Got "
        f"{c2_summary['run_created_metadata']!r}"
    )
    assert c2_summary["run_created_metadata"] is not c2_metadata, (
        "C2(copy): the implementation does `dict(ev.metadata)` (line 63), "
        "producing a NEW dict rather than aliasing. A refactor swapping "
        "`dict(ev.metadata)` for `ev.metadata` would let the caller "
        "mutate the event's frozen metadata. Pin via `is not` identity"
    )

    c3_store, c3_rid = _make_store_and_run()
    _append_stage_started(c3_store, c3_rid)
    _append_finding_created(c3_store, c3_rid)
    c3_summary = build_run_summary(c3_store.list_run_events(str(c3_rid)))
    assert c3_summary["workflow_profile"] is None, (
        f"C3(workflow): rows with NO RUN_CREATED -> workflow_profile "
        f"stays at initial None (line 32 default). Got "
        f"{c3_summary['workflow_profile']!r}"
    )
    assert c3_summary["run_created_metadata"] == {}, (
        f"C3(metadata): rows with NO RUN_CREATED -> run_created_metadata "
        f"stays at initial {{}} (line 56 default). Got "
        f"{c3_summary['run_created_metadata']!r}"
    )

    c45_store, c45_rid = _make_store_and_run()
    _append_run_created(
        c45_store,
        c45_rid,
        workflow_profile="alpha",
        metadata={"order": "first"},
    )
    _append_run_created(
        c45_store,
        c45_rid,
        workflow_profile="beta",
        metadata={"order": "second"},
    )
    c45_rows = c45_store.list_run_events(str(c45_rid))
    c45_summary = build_run_summary(c45_rows)
    assert c45_summary["workflow_profile"] == "beta", (
        "C4: TWO RUN_CREATED events with workflow_profile alpha (first) "
        "and beta (second) -> workflow_profile='beta' (LAST-wins via "
        f"line-34 no-break loop). Got {c45_summary['workflow_profile']!r}. "
        "KEY DIVERGENCE pin: a refactor adding a `break` to the line-34 "
        "loop would FLIP this from 'beta' to 'alpha'"
    )
    assert c45_summary["run_created_metadata"] == {"order": "first"}, (
        "C5: SAME 2-RUN_CREATED row sequence as C4 -> run_created_metadata "
        "= {'order': 'first'} (FIRST-wins via line-64 break statement). "
        f"Got {c45_summary['run_created_metadata']!r}. KEY DIVERGENCE pin: "
        "a refactor REMOVING the line-64 `break` would FLIP this from "
        "first to second. C4 and C5 together prove the two loops have "
        "INTENTIONALLY ASYMMETRIC termination semantics"
    )


def test_read_models_counters_flags_event_count_and_run_has_started_defensive_contract() -> None:
    """Pin counters / flags / event_count / latest_event_type + run_has_started arms (5 axes).

    The 5 axes cover the remaining build_run_summary fields and the
    final two arms of run_has_started:

    * D1: ``findings_count`` is a SUM-counter (not boolean) across 0
      / 1 / 3 FINDING_CREATED events.
    * D2: ``has_escalation`` is an ANY-flag (not count) across 0 / 1
      / 2 RUN_ESCALATED events.
    * D3: ``event_count == len(rows)`` AND ``latest_event_type ==
      rows[-1]["event_type"]`` across 3 distinct row-tail shapes.
    * D4: ``run_has_started`` returns True regardless of RUN_STARTED
      position (proves the function visits ALL rows looking for a
      match, not just rows[0] or rows[-1]).
    * D5: ``run_has_started`` does NOT catch ``ValidationError`` on a
      malformed RUN_STARTED row -- the validate_event_dict call is
      bare (no try/except). KEY DIVERGENCE pin via pytest.raises.
      Also pins the early-continue guard on event_type via a malformed
      non-RUN_STARTED row that would crash if validation came first.
    """
    d1_counts: list[tuple[int, int]] = [(0, 0), (1, 1), (3, 3)]
    for n_findings, expected in d1_counts:
        d1_store, d1_rid = _make_store_and_run()
        _append_run_created(d1_store, d1_rid)
        for _ in range(n_findings):
            _append_finding_created(d1_store, d1_rid)
        d1_summary = build_run_summary(d1_store.list_run_events(str(d1_rid)))
        assert d1_summary["findings_count"] == expected, (
            f"D1 n={n_findings}: findings_count expected {expected}, got "
            f"{d1_summary['findings_count']!r}. Pins sum-semantics (not "
            "any/boolean). A refactor swapping `sum(...)` for "
            "`any(...)` would flip the n=3 case from 3 to True (1) and "
            "lose the count granularity that the API summary returns"
        )

    d2_cases: list[tuple[int, bool]] = [(0, False), (1, True), (2, True)]
    for n_escalations, expected_flag in d2_cases:
        d2_store, d2_rid = _make_store_and_run()
        _append_run_created(d2_store, d2_rid)
        for _ in range(n_escalations):
            _append_run_escalated(d2_store, d2_rid)
        d2_summary = build_run_summary(d2_store.list_run_events(str(d2_rid)))
        assert d2_summary["has_escalation"] is expected_flag, (
            f"D2 n={n_escalations}: has_escalation expected "
            f"{expected_flag!r}, got {d2_summary['has_escalation']!r}. "
            "Pins any-semantics (not count). A refactor returning the "
            "RAW count (e.g. via sum(...)) would flip n=2 from True to 2 "
            "and break the boolean contract on the API field"
        )

    d3_tails: list[tuple[str, list[str]]] = [
        ("run.created", ["run.created"]),
        ("stage.started", ["run.created", "stage.started"]),
        ("finding.created", ["run.created", "stage.started", "finding.created"]),
    ]
    for expected_latest, sequence in d3_tails:
        d3_store, d3_rid = _make_store_and_run()
        for et in sequence:
            if et == "run.created":
                _append_run_created(d3_store, d3_rid)
            elif et == "stage.started":
                _append_stage_started(d3_store, d3_rid)
            elif et == "finding.created":
                _append_finding_created(d3_store, d3_rid)
        d3_rows = d3_store.list_run_events(str(d3_rid))
        d3_summary = build_run_summary(d3_rows)
        assert d3_summary["event_count"] == len(sequence), (
            f"D3({expected_latest}) event_count: expected "
            f"{len(sequence)}, got {d3_summary['event_count']!r}. "
            "Pins event_count == len(rows)"
        )
        assert d3_summary["latest_event_type"] == expected_latest, (
            f"D3({expected_latest}) latest_event_type: expected "
            f"{expected_latest!r}, got {d3_summary['latest_event_type']!r}. "
            "Pins latest_event_type == rows[-1]['event_type'] regardless "
            "of which event type the tail is"
        )

    d4_store_simple, d4_rid_simple = _make_store_and_run()
    _append_run_created(d4_store_simple, d4_rid_simple)
    _append_run_started(d4_store_simple, d4_rid_simple)
    assert run_has_started(d4_store_simple.list_run_events(str(d4_rid_simple))) is True, (
        "D4(happy): RUN_CREATED + RUN_STARTED -> True"
    )

    d4_store_middle, d4_rid_middle = _make_store_and_run()
    _append_run_created(d4_store_middle, d4_rid_middle)
    _append_run_started(d4_store_middle, d4_rid_middle)
    _append_stage_started(d4_store_middle, d4_rid_middle)
    _append_finding_created(d4_store_middle, d4_rid_middle)
    d4_middle_rows = d4_store_middle.list_run_events(str(d4_rid_middle))
    assert run_has_started(d4_middle_rows) is True, (
        f"D4(middle): RUN_STARTED in the MIDDLE of the row sequence "
        f"(positions 1 of 4) -> True. Pins position-independence -- a "
        f"refactor checking only rows[0] or rows[-1] would FLIP this. "
        f"Row event_types: {[r['event_type'] for r in d4_middle_rows]!r}"
    )

    malformed_started_row: dict[str, Any] = {
        "store_seq": 1,
        "event_id": uuid4(),
        "run_id": uuid4(),
        "stage_id": None,
        "task_id": None,
        "event_type": EventType.RUN_STARTED.value,
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc),
        "actor_role": None,
        "model_id": None,
        "correlation_id": None,
        "causation_id": None,
        "payload": {},  # missing required `started_by` -> validation fails
        "metadata": {},
    }
    with pytest.raises(ValidationError) as exc_info:
        run_has_started([malformed_started_row])
    assert "started_by" in str(exc_info.value) or "RunStartedPayload" in str(exc_info.value), (
        f"D5(raise): run_has_started on a malformed RUN_STARTED row "
        "(payload missing `started_by`) must propagate the underlying "
        f"ValidationError. Got message: {str(exc_info.value)!r}. KEY "
        "DIVERGENCE pin: a 'defensive' refactor wrapping the "
        "validate_event_dict call in try/except and returning False "
        "would silently swallow malformed RUN_STARTED rows and flip "
        "raise -> False"
    )

    malformed_failed_then_valid_started_rows: list[dict[str, Any]] = [
        {
            "store_seq": 1,
            "event_id": uuid4(),
            "run_id": uuid4(),
            "stage_id": None,
            "task_id": None,
            "event_type": EventType.RUN_FAILED.value,
            "event_version": 1,
            "occurred_at": datetime.now(timezone.utc),
            "actor_role": None,
            "model_id": None,
            "correlation_id": None,
            "causation_id": None,
            "payload": {},
            "metadata": {},
        },
    ]
    d5b_store, d5b_rid = _make_store_and_run()
    _append_run_started(d5b_store, d5b_rid)
    malformed_failed_then_valid_started_rows.extend(
        d5b_store.list_run_events(str(d5b_rid)),
    )
    assert run_has_started(malformed_failed_then_valid_started_rows) is True, (
        "D5(early-continue): a malformed RUN_FAILED row (payload missing "
        "required fields) BEFORE a valid RUN_STARTED row -> True. Proves "
        "the `if r['event_type'] != RUN_STARTED.value: continue` guard "
        "fires BEFORE validate_event_dict, so non-RUN_STARTED rows "
        "cannot poison the scan with their own validation failures. A "
        "refactor that validated ALL rows up-front (e.g. via replay_validate) "
        "would crash here on the malformed RUN_FAILED row instead of "
        "returning True"
    )
