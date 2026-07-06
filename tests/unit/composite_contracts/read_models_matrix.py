from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from agent_core.models import EventType
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

EMPTY_RUN_SUMMARY: dict[str, Any] = {
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

_FILTER_MEMBERS = frozenset({"created", "running", "terminal"})


def append_event_sequence(
    sequence: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    store, run_id = make_store_and_run()
    for spec in sequence:
        kind = spec["kind"]
        if kind == "run.created":
            append_run_created(
                store,
                run_id,
                workflow_profile=spec.get("workflow_profile", "default"),
                metadata=spec.get("metadata"),
            )
        elif kind == "run.started":
            append_run_started(store, run_id)
        elif kind == "run.failed":
            append_run_failed(store, run_id)
        elif kind == "run.completed":
            append_run_completed(store, run_id)
        elif kind == "run.escalated":
            append_run_escalated(store, run_id)
        elif kind == "stage.started":
            append_stage_started(store, run_id)
        elif kind == "finding.created":
            append_finding_created(store, run_id)
        else:
            raise ValueError(f"unknown event kind: {kind!r}")
    return store.list_run_events(str(run_id))


def append_event_sequence_with_repeat(
    base_sequence: tuple[dict[str, Any], ...],
    *,
    repeat_kind: str,
    repeat_count: int,
) -> list[dict[str, Any]]:
    store, run_id = make_store_and_run()
    for spec in base_sequence:
        kind = spec["kind"]
        if kind == "run.created":
            append_run_created(store, run_id)
        elif kind == "run.escalated":
            append_run_escalated(store, run_id)
        elif kind == "finding.created":
            append_finding_created(store, run_id)
        else:
            raise ValueError(f"unsupported base kind in repeat helper: {kind!r}")
    for _ in range(repeat_count):
        if repeat_kind == "finding.created":
            append_finding_created(store, run_id)
        elif repeat_kind == "run.escalated":
            append_run_escalated(store, run_id)
        else:
            raise ValueError(f"unsupported repeat kind: {repeat_kind!r}")
    return store.list_run_events(str(run_id))


_C2_METADATA: dict[str, str] = {"actor": "fo115_test", "trace_id": "xyz"}


def _validate_c2_metadata_copy(case: dict[str, Any], summary: dict[str, Any]) -> None:
    source = case["source_metadata"]
    assert summary["run_created_metadata"] is not source, (
        "C2(copy): the implementation does `dict(ev.metadata)` (line 63), "
        "producing a NEW dict rather than aliasing. A refactor swapping "
        "`dict(ev.metadata)` for `ev.metadata` would let the caller "
        "mutate the event's frozen metadata. Pin via `is not` identity"
    )


def _validate_c45_divergence(case: dict[str, Any], summary: dict[str, Any]) -> None:
    assert summary["workflow_profile"] == "beta", (
        "C4: TWO RUN_CREATED events with workflow_profile alpha (first) "
        "and beta (second) -> workflow_profile='beta' (LAST-wins via "
        f"line-34 no-break loop). Got {summary['workflow_profile']!r}. "
        "KEY DIVERGENCE pin: a refactor adding a `break` to the line-34 "
        "loop would FLIP this from 'beta' to 'alpha'"
    )
    assert summary["run_created_metadata"] == {"order": "first"}, (
        "C5: SAME 2-RUN_CREATED row sequence as C4 -> run_created_metadata "
        "= {'order': 'first'} (FIRST-wins via line-64 break statement). "
        f"Got {summary['run_created_metadata']!r}. KEY DIVERGENCE pin: "
        "a refactor REMOVING the line-64 `break` would FLIP this from "
        "first to second. C4 and C5 together prove the two loops have "
        "INTENTIONALLY ASYMMETRIC termination semantics"
    )


def _validate_d5_raise(case: dict[str, Any], exc: BaseException) -> None:
    assert "started_by" in str(exc) or "RunStartedPayload" in str(exc), (
        f"D5(raise): run_has_started on a malformed RUN_STARTED row "
        "(payload missing `started_by`) must propagate the underlying "
        f"ValidationError. Got message: {str(exc)!r}. KEY "
        "DIVERGENCE pin: a 'defensive' refactor wrapping the "
        "validate_event_dict call in try/except and returning False "
        "would silently swallow malformed RUN_STARTED rows and flip "
        "raise -> False"
    )


def malformed_started_row() -> dict[str, Any]:
    return {
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
        "payload": {},
        "metadata": {},
    }


def malformed_failed_then_valid_started_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
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
    store, run_id = make_store_and_run()
    append_run_started(store, run_id)
    rows.extend(store.list_run_events(str(run_id)))
    return rows


EMPTY_SUMMARY_CASE: dict[str, Any] = {
    "case_id": "a1_empty_rows",
    "rows": [],
    "expected": EMPTY_RUN_SUMMARY,
}

FILTER_STATUS_MEMBERSHIP_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a2_unknown_excluded",
        "status": "unknown",
        "expect_member": False,
        "msg": (
            'A2: `"unknown"` MUST be excluded from RUN_LIST_FILTER_STATUSES '
            "-- empty runs are intentionally outside the GET /v1/runs?status= "
            "filter set"
        ),
    },
    {
        "case_id": "a2_created_present",
        "status": "created",
        "expect_member": True,
        "msg": 'A2: `"created"` MUST be present in RUN_LIST_FILTER_STATUSES',
    },
    {
        "case_id": "a2_running_present",
        "status": "running",
        "expect_member": True,
        "msg": 'A2: `"running"` MUST be present in RUN_LIST_FILTER_STATUSES',
    },
    {
        "case_id": "a2_terminal_present",
        "status": "terminal",
        "expect_member": True,
        "msg": 'A2: `"terminal"` MUST be present in RUN_LIST_FILTER_STATUSES',
    },
)

FILTER_STATUS_TYPE_CASE: dict[str, Any] = {
    "case_id": "a3_frozenset_immutable",
    "expected_type": frozenset,
    "expected_value": _FILTER_MEMBERS,
}

RUN_HAS_STARTED_BASELINE_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a4_empty_rows",
        "rows": [],
        "expected": False,
        "msg": (
            "A4: run_has_started([]) must return False. Empty rows -> the "
            "for-loop body never executes -> returns the final False literal"
        ),
    },
    {
        "case_id": "a5_only_run_failed",
        "rows_builder": lambda: append_event_sequence(({"kind": "run.failed"},)),
        "expected": False,
        "msg": (
            "A5: run_has_started on rows containing ONLY a RUN_FAILED row "
            "must return False. Proves the function is RUN_STARTED-specific"
        ),
    },
)

STATUS_LADDER_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "b1_run_created_only",
        "sequence": ({"kind": "run.created", "workflow_profile": "b1_profile"},),
        "expected": {
            "status": "created",
            "latest_event_type": "run.created",
            "terminal_event_type": None,
        },
    },
    {
        "case_id": "b2_stage_started_no_run_started",
        "sequence": ({"kind": "run.created"}, {"kind": "stage.started"}),
        "expected": {
            "status": "running",
            "latest_event_type": "stage.started",
        },
    },
    {
        "case_id": "b3_run_started",
        "sequence": ({"kind": "run.created"}, {"kind": "run.started"}),
        "expected": {
            "status": "running",
            "latest_event_type": "run.started",
        },
    },
    {
        "case_id": "b4_terminal_failed",
        "sequence": (
            {"kind": "run.created"},
            {"kind": "run.started"},
            {"kind": "run.failed"},
        ),
        "expected": {
            "status": "terminal",
            "terminal_event_type": "run.failed",
        },
    },
    {
        "case_id": "b5_terminal_completed",
        "sequence": ({"kind": "run.created"}, {"kind": "run.completed"}),
        "expected": {
            "status": "terminal",
            "terminal_event_type": "run.completed",
        },
    },
)

RUN_CREATED_EXTRACTION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "c1_single_workflow_profile",
        "sequence": ({"kind": "run.created", "workflow_profile": "alpha"},),
        "expected": {"workflow_profile": "alpha"},
    },
    {
        "case_id": "c2_metadata_copy",
        "sequence": ({"kind": "run.created", "metadata": _C2_METADATA},),
        "expected": {"run_created_metadata": dict(_C2_METADATA)},
        "source_metadata": _C2_METADATA,
        "validate": _validate_c2_metadata_copy,
    },
    {
        "case_id": "c3_no_run_created",
        "sequence": ({"kind": "stage.started"}, {"kind": "finding.created"}),
        "expected": {"workflow_profile": None, "run_created_metadata": {}},
    },
    {
        "case_id": "c45_first_vs_last_divergence",
        "sequence": (
            {
                "kind": "run.created",
                "workflow_profile": "alpha",
                "metadata": {"order": "first"},
            },
            {
                "kind": "run.created",
                "workflow_profile": "beta",
                "metadata": {"order": "second"},
            },
        ),
        "validate": _validate_c45_divergence,
    },
)

FINDINGS_COUNT_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d1_findings_0",
        "sequence": ({"kind": "run.created"},),
        "repeat": ("finding.created", 0),
        "expected_key": "findings_count",
        "expected": 0,
    },
    {
        "case_id": "d1_findings_1",
        "sequence": ({"kind": "run.created"},),
        "repeat": ("finding.created", 1),
        "expected_key": "findings_count",
        "expected": 1,
    },
    {
        "case_id": "d1_findings_3",
        "sequence": ({"kind": "run.created"},),
        "repeat": ("finding.created", 3),
        "expected_key": "findings_count",
        "expected": 3,
    },
)

ESCALATION_FLAG_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d2_escalations_0",
        "sequence": ({"kind": "run.created"},),
        "repeat": ("run.escalated", 0),
        "expected_key": "has_escalation",
        "expected": False,
    },
    {
        "case_id": "d2_escalations_1",
        "sequence": ({"kind": "run.created"},),
        "repeat": ("run.escalated", 1),
        "expected_key": "has_escalation",
        "expected": True,
    },
    {
        "case_id": "d2_escalations_2",
        "sequence": ({"kind": "run.created"},),
        "repeat": ("run.escalated", 2),
        "expected_key": "has_escalation",
        "expected": True,
    },
)

EVENT_COUNT_LATEST_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d3_run_created",
        "sequence": ({"kind": "run.created"},),
        "expected_latest": "run.created",
    },
    {
        "case_id": "d3_stage_started",
        "sequence": ({"kind": "run.created"}, {"kind": "stage.started"}),
        "expected_latest": "stage.started",
    },
    {
        "case_id": "d3_finding_created",
        "sequence": (
            {"kind": "run.created"},
            {"kind": "stage.started"},
            {"kind": "finding.created"},
        ),
        "expected_latest": "finding.created",
    },
)

RUN_HAS_STARTED_POSITION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d4_happy_simple",
        "sequence": ({"kind": "run.created"}, {"kind": "run.started"}),
        "expected": True,
    },
    {
        "case_id": "d4_middle_position",
        "sequence": (
            {"kind": "run.created"},
            {"kind": "run.started"},
            {"kind": "stage.started"},
            {"kind": "finding.created"},
        ),
        "expected": True,
    },
)

RUN_HAS_STARTED_MALFORMED_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d5_raise_on_malformed_started",
        "mode": "raise",
        "rows_builder": lambda: [malformed_started_row()],
        "exc_type": ValidationError,
        "validate": _validate_d5_raise,
    },
    {
        "case_id": "d5_early_continue_malformed_failed",
        "mode": "value",
        "rows_builder": malformed_failed_then_valid_started_rows,
        "expected": True,
    },
)
