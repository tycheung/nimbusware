from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from unit.composite_contract_fixtures import store_event_row

_FIVE_HOURS = timezone(timedelta(hours=5))
_UTC = timezone.utc

_PROGRESS_IGNORE_MEMBERS: tuple[str, ...] = (
    "run.created",
    "model.preflight.started",
    "model.preflight.passed",
    "model.preflight.failed",
    "model.selected.primary",
    "model.selected.fallback",
)

_NON_IGNORE_SAMPLES: tuple[str, ...] = (
    "stage.started",
    "finding.created",
    "run.escalated",
    "gate.decision.emitted",
)

_NOVEL_EVENT_TYPES: tuple[str, ...] = (
    "fo116.synthetic",
    "",
    "unknown.event.type",
)

EXPECTED_PROGRESS_IGNORE = frozenset(_PROGRESS_IGNORE_MEMBERS)

_A4_DT = datetime(2026, 1, 1, 12, 0, tzinfo=_UTC)
_A5_VALID_DT = datetime(2026, 1, 1, 12, 0, tzinfo=_UTC)
_B4_DT_1 = datetime(2026, 1, 1, 10, 0, tzinfo=_UTC)
_B5_DT_2 = datetime(2026, 1, 1, 11, 0, tzinfo=_UTC)
_D3_DT = datetime(2026, 1, 1, 12, 0, tzinfo=_UTC)
_D5_BOOTSTRAP_DT = datetime(2026, 1, 1, 12, 0, tzinfo=_UTC)


def _validate_a3_missing_key(_case: dict[str, Any], _actual: Any) -> None:
    row = store_event_row(store_seq=1, event_type="run.created")
    assert "occurred_at" not in row


B3_AWARE_ROWS: list[dict[str, Any]] = [
    store_event_row(
        store_seq=1,
        event_type="run.created",
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=_FIVE_HOURS),
    ),
]

B3_NAIVE_ROWS: list[dict[str, Any]] = [
    store_event_row(
        store_seq=1,
        event_type="run.created",
        occurred_at=datetime(2026, 1, 1, 12, 0),
    ),
]

FIRST_RUN_CREATED_AT_GUARD_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "a1_empty", "rows": [], "expected": None},
    {
        "case_id": "a2_no_run_created",
        "rows": [
            store_event_row(store_seq=1, event_type="stage.started", occurred_at=_A4_DT),
            store_event_row(
                store_seq=2,
                event_type="model.preflight.passed",
                occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=_UTC),
            ),
            store_event_row(
                store_seq=3,
                event_type="finding.created",
                occurred_at=datetime(2026, 1, 1, 12, 2, tzinfo=_UTC),
            ),
        ],
        "expected": None,
    },
    {
        "case_id": "a3_str_iso",
        "rows": [
            store_event_row(
                store_seq=1,
                event_type="run.created",
                occurred_at="2026-01-01T12:00:00+00:00",
            ),
        ],
        "expected": None,
    },
    {
        "case_id": "a3_int_epoch",
        "rows": [store_event_row(store_seq=1, event_type="run.created", occurred_at=1735732800)],
        "expected": None,
    },
    {
        "case_id": "a3_explicit_none",
        "rows": [store_event_row(store_seq=1, event_type="run.created", occurred_at=None)],
        "expected": None,
    },
    {
        "case_id": "a3_missing_key",
        "rows": [store_event_row(store_seq=1, event_type="run.created")],
        "expected": None,
        "validate": _validate_a3_missing_key,
    },
    {
        "case_id": "a4_happy_path",
        "rows": [store_event_row(store_seq=1, event_type="run.created", occurred_at=_A4_DT)],
        "expected": _A4_DT,
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "a5_skip_invalid_first",
        "rows": [
            store_event_row(store_seq=1, event_type="run.created", occurred_at="not-a-datetime"),
            store_event_row(store_seq=2, event_type="run.created", occurred_at=_A5_VALID_DT),
        ],
        "expected": _A5_VALID_DT,
    },
)

FIRST_RUN_CREATED_AT_NORMALIZATION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "b1_aware_plus5",
        "rows": [
            store_event_row(
                store_seq=1,
                event_type="run.created",
                occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=_FIVE_HOURS),
            ),
        ],
        "expected": datetime(2026, 1, 1, 7, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "b2_naive_assumes_utc",
        "rows": [
            store_event_row(
                store_seq=1,
                event_type="run.created",
                occurred_at=datetime(2026, 1, 1, 12, 0),
            ),
        ],
        "expected": datetime(2026, 1, 1, 12, 0, tzinfo=_UTC),
        "assert_tz_utc": True,
        "tzinfo": _UTC,
    },
    {
        "case_id": "b4_numeric_sort",
        "rows": [
            store_event_row(
                store_seq=5,
                event_type="run.created",
                occurred_at=datetime(2026, 1, 1, 14, 0, tzinfo=_UTC),
            ),
            store_event_row(store_seq=1, event_type="run.created", occurred_at=_B4_DT_1),
            store_event_row(
                store_seq=3,
                event_type="run.created",
                occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=_UTC),
            ),
        ],
        "expected": _B4_DT_1,
    },
    {
        "case_id": "b5_string_store_seq",
        "rows": [
            store_event_row(
                store_seq="10",
                event_type="run.created",
                occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=_UTC),
            ),
            store_event_row(store_seq="2", event_type="run.created", occurred_at=_B5_DT_2),
        ],
        "expected": _B5_DT_2,
    },
)

COUNT_PROGRESS_IGNORE_CASES: tuple[dict[str, Any], ...] = tuple(
    {
        "case_id": f"c2_{event_type.replace('.', '_')}",
        "rows": [store_event_row(store_seq=1, event_type=event_type)],
        "expected": 0,
    }
    for event_type in _PROGRESS_IGNORE_MEMBERS
)

COUNT_PROGRESS_NON_IGNORE_CASES: tuple[dict[str, Any], ...] = tuple(
    {
        "case_id": f"c3_{event_type.replace('.', '_')}",
        "rows": [store_event_row(store_seq=1, event_type=event_type)],
        "expected": 1,
    }
    for event_type in _NON_IGNORE_SAMPLES
)

COUNT_PROGRESS_MIXED_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "c1_empty", "rows": [], "expected": 0},
    {
        "case_id": "c4_mixed_sequence",
        "rows": [
            store_event_row(store_seq=1, event_type="run.created"),
            store_event_row(store_seq=2, event_type="model.preflight.passed"),
            store_event_row(store_seq=3, event_type="model.selected.primary"),
            store_event_row(store_seq=4, event_type="stage.started"),
            store_event_row(store_seq=5, event_type="finding.created"),
            store_event_row(store_seq=6, event_type="finding.created"),
            store_event_row(store_seq=7, event_type="run.escalated"),
        ],
        "expected": 4,
    },
    {
        "case_id": "c5_fail_open",
        "rows": [
            store_event_row(store_seq=1, event_type=_NOVEL_EVENT_TYPES[0]),
            store_event_row(store_seq=2, event_type=_NOVEL_EVENT_TYPES[1]),
            store_event_row(store_seq=3, event_type=_NOVEL_EVENT_TYPES[2]),
        ],
        "expected": 3,
    },
)

CROSS_HELPER_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d3_run_created_dual",
        "rows": [store_event_row(store_seq=1, event_type="run.created", occurred_at=_D3_DT)],
        "expected_timestamp": _D3_DT,
        "expected_progress": 0,
    },
    {
        "case_id": "d4_no_run_created",
        "rows": [
            store_event_row(
                store_seq=1,
                event_type="stage.started",
                occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=_UTC),
            ),
            store_event_row(
                store_seq=2,
                event_type="finding.created",
                occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=_UTC),
            ),
        ],
        "expected_timestamp": None,
        "expected_progress": 2,
    },
    {
        "case_id": "d5_bootstrap_silent",
        "rows": [
            store_event_row(store_seq=1, event_type="run.created", occurred_at=_D5_BOOTSTRAP_DT),
            store_event_row(
                store_seq=2,
                event_type="model.preflight.started",
                occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=_UTC),
            ),
            store_event_row(
                store_seq=3,
                event_type="model.preflight.passed",
                occurred_at=datetime(2026, 1, 1, 12, 2, tzinfo=_UTC),
            ),
            store_event_row(
                store_seq=4,
                event_type="model.selected.primary",
                occurred_at=datetime(2026, 1, 1, 12, 3, tzinfo=_UTC),
            ),
            store_event_row(
                store_seq=5,
                event_type="model.preflight.failed",
                occurred_at=datetime(2026, 1, 1, 12, 4, tzinfo=_UTC),
            ),
            store_event_row(
                store_seq=6,
                event_type="model.selected.fallback",
                occurred_at=datetime(2026, 1, 1, 12, 5, tzinfo=_UTC),
            ),
        ],
        "expected_timestamp": _D5_BOOTSTRAP_DT,
        "expected_progress": 0,
    },
)
