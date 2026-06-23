from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent_core.models import EventType
from nimbusware_orchestrator.read_models import (
    RUN_LIST_FILTER_STATUSES,
    build_run_summary,
    run_has_started,
)
from unit.composite_store_fixtures import (
    append_finding_created,
    append_run_completed,
    append_run_created,
    append_run_escalated,
    append_run_failed,
    append_run_started,
    append_stage_started,
    make_store_and_run,
)


def test_read_models_empty_rows_and_filter_set_and_run_has_started_baseline(
    tmp_path: Any,  # noqa: ARG001  (unused; pytest-supplied fixture for parity)
) -> None:
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
        'A2: `"unknown"` MUST be excluded from RUN_LIST_FILTER_STATUSES '
        "-- empty runs are intentionally outside the GET /v1/runs?status= "
        "filter set. A refactor adding 'unknown' would let API clients "
        "filter for runs that have NO events (data anomaly), which is "
        "the explicit anti-contract"
    )
    for status in ("created", "running", "terminal"):
        assert status in RUN_LIST_FILTER_STATUSES, (
            f'A2: `"{status}"` MUST be present in RUN_LIST_FILTER_STATUSES '
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

    a5_store, a5_rid = make_store_and_run()
    append_run_failed(a5_store, a5_rid)
    a5_rows = a5_store.list_run_events(str(a5_rid))
    assert run_has_started(a5_rows) is False, (
        "A5: run_has_started on rows containing ONLY a RUN_FAILED row "
        "must return False. Proves the function is RUN_STARTED-specific "
        "(not a generic active-run probe) -- a refactor checking for "
        "any 'lifecycle' event would FLIP this"
    )


def test_build_run_summary_status_ladder_priority_and_terminal_event_type_contract() -> None:
    b1_store, b1_rid = make_store_and_run()
    append_run_created(b1_store, b1_rid, workflow_profile="b1_profile")
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

    b2_store, b2_rid = make_store_and_run()
    append_run_created(b2_store, b2_rid)
    append_stage_started(b2_store, b2_rid)
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
        f"B2(latest): latest is STAGE_STARTED. Got {b2_summary['latest_event_type']!r}"
    )

    b3_store, b3_rid = make_store_and_run()
    append_run_created(b3_store, b3_rid)
    append_run_started(b3_store, b3_rid)
    b3_summary = build_run_summary(b3_store.list_run_events(str(b3_rid)))
    assert b3_summary["status"] == "running", (
        f"B3: RUN_CREATED + RUN_STARTED -> status='running' via the STARTED "
        "branch (line 50). Same return value as B2 but DIFFERENT code path. "
        f"Got {b3_summary['status']!r}"
    )
    assert b3_summary["latest_event_type"] == "run.started", (
        f"B3(latest): latest is RUN_STARTED. Got {b3_summary['latest_event_type']!r}"
    )

    b4_store, b4_rid = make_store_and_run()
    append_run_created(b4_store, b4_rid)
    append_run_started(b4_store, b4_rid)
    append_run_failed(b4_store, b4_rid)
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

    b5_store, b5_rid = make_store_and_run()
    append_run_created(b5_store, b5_rid)
    append_run_completed(b5_store, b5_rid)
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
    c1_store, c1_rid = make_store_and_run()
    append_run_created(c1_store, c1_rid, workflow_profile="alpha")
    c1_summary = build_run_summary(c1_store.list_run_events(str(c1_rid)))
    assert c1_summary["workflow_profile"] == "alpha", (
        f"C1: single RUN_CREATED with workflow_profile='alpha' -> "
        f"summary['workflow_profile']='alpha'. Got "
        f"{c1_summary['workflow_profile']!r}"
    )

    c2_store, c2_rid = make_store_and_run()
    c2_metadata = {"actor": "fo115_test", "trace_id": "xyz"}
    append_run_created(c2_store, c2_rid, metadata=c2_metadata)
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

    c3_store, c3_rid = make_store_and_run()
    append_stage_started(c3_store, c3_rid)
    append_finding_created(c3_store, c3_rid)
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

    c45_store, c45_rid = make_store_and_run()
    append_run_created(
        c45_store,
        c45_rid,
        workflow_profile="alpha",
        metadata={"order": "first"},
    )
    append_run_created(
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
    d1_counts: list[tuple[int, int]] = [(0, 0), (1, 1), (3, 3)]
    for n_findings, expected in d1_counts:
        d1_store, d1_rid = make_store_and_run()
        append_run_created(d1_store, d1_rid)
        for _ in range(n_findings):
            append_finding_created(d1_store, d1_rid)
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
        d2_store, d2_rid = make_store_and_run()
        append_run_created(d2_store, d2_rid)
        for _ in range(n_escalations):
            append_run_escalated(d2_store, d2_rid)
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
        d3_store, d3_rid = make_store_and_run()
        for et in sequence:
            if et == "run.created":
                append_run_created(d3_store, d3_rid)
            elif et == "stage.started":
                append_stage_started(d3_store, d3_rid)
            elif et == "finding.created":
                append_finding_created(d3_store, d3_rid)
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

    d4_store_simple, d4_rid_simple = make_store_and_run()
    append_run_created(d4_store_simple, d4_rid_simple)
    append_run_started(d4_store_simple, d4_rid_simple)
    assert run_has_started(d4_store_simple.list_run_events(str(d4_rid_simple))) is True, (
        "D4(happy): RUN_CREATED + RUN_STARTED -> True"
    )

    d4_store_middle, d4_rid_middle = make_store_and_run()
    append_run_created(d4_store_middle, d4_rid_middle)
    append_run_started(d4_store_middle, d4_rid_middle)
    append_stage_started(d4_store_middle, d4_rid_middle)
    append_finding_created(d4_store_middle, d4_rid_middle)
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
    d5b_store, d5b_rid = make_store_and_run()
    append_run_started(d5b_store, d5b_rid)
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
