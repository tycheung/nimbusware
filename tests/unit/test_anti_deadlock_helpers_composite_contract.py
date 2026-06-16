from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from nimbusware_orchestrator.anti_deadlock import (
    _PROGRESS_IGNORE,
    _first_run_created_at,
    count_progress_events,
)

_FIVE_HOURS = timezone(timedelta(hours=5))


def _make_row(
    *,
    store_seq: int | str,
    event_type: str,
    occurred_at: Any = ...,
) -> dict[str, Any]:
    """Build a single row dict matching the ``list_run_events`` shape.

    ``occurred_at = ...`` (Ellipsis sentinel) omits the key entirely so
    Part A's "missing key" sub-axis exercises the ``r.get(...)``
    ``None`` default. Any other value (including ``None``) is set
    verbatim.

    ``store_seq`` accepts ``int`` or ``str`` so Part B B5 can sweep
    the ``int(x["store_seq"])`` sort-key coercion.
    """
    row: dict[str, Any] = {"store_seq": store_seq, "event_type": event_type}
    if occurred_at is not ...:
        row["occurred_at"] = occurred_at
    return row


def test_first_run_created_at_empty_and_no_match_and_isinstance_guard_contract() -> None:
    assert _first_run_created_at([]) is None, (
        "A1: empty rows -> the for-loop body never executes -> falls "
        "through to the final `return None` (line 33). A refactor "
        "adding a default datetime sentinel would FLIP this axis"
    )

    a2_rows: list[dict[str, Any]] = [
        _make_row(
            store_seq=1,
            event_type="stage.started",
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        ),
        _make_row(
            store_seq=2,
            event_type="model.preflight.passed",
            occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        ),
        _make_row(
            store_seq=3,
            event_type="finding.created",
            occurred_at=datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc),
        ),
    ]
    assert _first_run_created_at(a2_rows) is None, (
        "A2: rows with NO `event_type == 'run.created'` (all 3 other "
        "types here) -> every iteration hits the `continue` at line "
        "26-27 -> falls through to `return None`. Pins that the "
        "event-type filter is EXACT-match, not substring/prefix"
    )

    non_datetime_cases: list[tuple[str, Any]] = [
        ("str_iso", "2026-01-01T12:00:00+00:00"),
        ("int_epoch", 1735732800),
        ("explicit_none", None),
    ]
    for label, bad_value in non_datetime_cases:
        rows = [_make_row(store_seq=1, event_type="run.created", occurred_at=bad_value)]
        assert _first_run_created_at(rows) is None, (
            f"A3 ({label}): single run.created row with occurred_at="
            f"{bad_value!r} (type {type(bad_value).__name__}) -> "
            "`isinstance(at, datetime)` is False -> skipped via the "
            "guard at line 29 -> falls through to `return None`. KEY "
            "DIVERGENCE pin: a refactor swapping the isinstance guard "
            "for `if at is None: continue` would raise TypeError on "
            "the str_iso / int_epoch cases when `.tzinfo` is accessed"
        )

    a3_missing_row = _make_row(store_seq=1, event_type="run.created")
    assert "occurred_at" not in a3_missing_row, (
        "A3 setup: the missing-key variant must literally omit the "
        f"occurred_at key. Got keys: {sorted(a3_missing_row.keys())!r}"
    )
    assert _first_run_created_at([a3_missing_row]) is None, (
        "A3 (missing_key): row WITHOUT the occurred_at key entirely "
        "-> `r.get('occurred_at')` returns None -> isinstance guard "
        "skips -> `return None`. Distinct path from the explicit-None "
        "case but same end-state (both reach the guard, both fail it)"
    )

    a4_dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    a4_rows = [_make_row(store_seq=1, event_type="run.created", occurred_at=a4_dt)]
    a4_result = _first_run_created_at(a4_rows)
    assert a4_result == a4_dt, (
        f"A4: single valid run.created row with tz-aware UTC datetime "
        f"-> returns it verbatim. Got {a4_result!r}, expected "
        f"{a4_dt!r}. Pins the happy path (input is already UTC, "
        "`astimezone(UTC)` is an identity transform)"
    )
    assert a4_result is not None and a4_result.tzinfo is timezone.utc, (
        f"A4(tz): return value MUST be UTC-aware. Got tzinfo={a4_result.tzinfo!r}"
    )

    a5_invalid_dt = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)
    a5_valid_dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    a5_rows = [
        _make_row(store_seq=1, event_type="run.created", occurred_at="not-a-datetime"),
        _make_row(store_seq=2, event_type="run.created", occurred_at=a5_valid_dt),
    ]
    a5_result = _first_run_created_at(a5_rows)
    assert a5_result == a5_valid_dt, (
        f"A5: two run.created rows; the FIRST (by sort) has a non-"
        f"datetime occurred_at and is skipped via the isinstance "
        f"guard, the SECOND has a valid datetime and is returned. "
        f"Got {a5_result!r}, expected {a5_valid_dt!r} (NOT "
        f"{a5_invalid_dt!r}, which would only match if the loop had "
        "exited early on the first run.created). Pins that the loop "
        "CONTINUES past invalid run.created rows rather than "
        "short-circuiting"
    )


def test_first_run_created_at_utc_normalization_and_sort_order_contract() -> None:
    aware_plus5 = datetime(2026, 1, 1, 12, 0, tzinfo=_FIVE_HOURS)
    expected_b1 = datetime(2026, 1, 1, 7, 0, tzinfo=timezone.utc)
    b1_rows = [_make_row(store_seq=1, event_type="run.created", occurred_at=aware_plus5)]
    b1_result = _first_run_created_at(b1_rows)
    assert b1_result == expected_b1, (
        f"B1: tz-aware datetime in +05:00 zone (12:00:00+05:00) -> "
        f"astimezone(UTC) shifts to 07:00:00 UTC. Got {b1_result!r}, "
        f"expected {expected_b1!r}. Pins that the aware branch uses "
        "`astimezone` (wall-clock-SHIFTING) not `replace` "
        "(wall-clock-PRESERVING)"
    )
    assert b1_result is not None and b1_result.tzinfo == timezone.utc, (
        f"B1(tz): aware branch must return UTC tzinfo. Got {b1_result.tzinfo!r}"
    )

    naive_dt = datetime(2026, 1, 1, 12, 0)
    expected_b2 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    b2_rows = [_make_row(store_seq=1, event_type="run.created", occurred_at=naive_dt)]
    b2_result = _first_run_created_at(b2_rows)
    assert b2_result == expected_b2, (
        f"B2: tz-naive datetime (12:00:00, no tzinfo) -> "
        f"replace(tzinfo=UTC) attaches UTC without shifting wall-clock "
        f"-> 12:00:00 UTC. Got {b2_result!r}, expected {expected_b2!r}. "
        "Pins that the naive branch ASSUMES UTC rather than rejecting "
        "or converting from local time"
    )
    assert b2_result is not None and b2_result.tzinfo == timezone.utc, (
        f"B2(tz): naive branch must attach UTC tzinfo. Got {b2_result.tzinfo!r}"
    )

    b3_aware_dt = datetime(2026, 1, 1, 12, 0, tzinfo=_FIVE_HOURS)
    b3_naive_dt = datetime(2026, 1, 1, 12, 0)
    b3_aware_rows = [
        _make_row(store_seq=1, event_type="run.created", occurred_at=b3_aware_dt),
    ]
    b3_naive_rows = [
        _make_row(store_seq=1, event_type="run.created", occurred_at=b3_naive_dt),
    ]
    b3_aware_result = _first_run_created_at(b3_aware_rows)
    b3_naive_result = _first_run_created_at(b3_naive_rows)
    assert b3_aware_result == datetime(2026, 1, 1, 7, 0, tzinfo=timezone.utc), (
        f"B3 KEY DIVERGENCE(aware): same wall-clock 12:00:00 in +05:00 "
        f"-> shifted to 07:00:00 UTC. Got {b3_aware_result!r}"
    )
    assert b3_naive_result == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc), (
        f"B3 KEY DIVERGENCE(naive): SAME wall-clock 12:00:00 (naive) "
        f"-> assumed UTC, returned 12:00:00 UTC. Got {b3_naive_result!r}"
    )
    assert b3_aware_result != b3_naive_result, (
        f"B3 KEY DIVERGENCE: same wall-clock numbers, different code "
        f"paths, DIFFERENT UTC results. aware={b3_aware_result!r}, "
        f"naive={b3_naive_result!r}. A refactor unifying to "
        "`astimezone(UTC)` would crash on the naive case (ValueError "
        "from astimezone on naive datetime in some Python versions, "
        "or wall-clock shift relative to system local). A refactor "
        "unifying to `replace(tzinfo=UTC)` would silently mis-shift "
        "the aware case from 07:00 to 12:00"
    )

    b4_dt_5 = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
    b4_dt_1 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    b4_dt_3 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    b4_rows = [
        _make_row(store_seq=5, event_type="run.created", occurred_at=b4_dt_5),
        _make_row(store_seq=1, event_type="run.created", occurred_at=b4_dt_1),
        _make_row(store_seq=3, event_type="run.created", occurred_at=b4_dt_3),
    ]
    b4_result = _first_run_created_at(b4_rows)
    assert b4_result == b4_dt_1, (
        f"B4: input rows in unsorted order [seq=5, seq=1, seq=3] -> "
        f"sort key int(store_seq) orders as [1, 3, 5] -> returns "
        f"seq=1's datetime ({b4_dt_1!r}). Got {b4_result!r}. KEY "
        "DIVERGENCE pin: a refactor dropping the `sorted(rows, ...)` "
        "wrapper would return seq=5's datetime (input-order FIRST) "
        f"which is {b4_dt_5!r}, NOT seq=1's"
    )

    b5_dt_10 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    b5_dt_2 = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)
    b5_rows = [
        _make_row(store_seq="10", event_type="run.created", occurred_at=b5_dt_10),
        _make_row(store_seq="2", event_type="run.created", occurred_at=b5_dt_2),
    ]
    b5_result = _first_run_created_at(b5_rows)
    assert b5_result == b5_dt_2, (
        f"B5 KEY DIVERGENCE: store_seq as str -- numeric sort orders "
        f"int('2')=2 BEFORE int('10')=10 -> returns seq='2's datetime "
        f"({b5_dt_2!r}). Got {b5_result!r}. A refactor dropping the "
        "`int(...)` cast would use Python's default string comparison "
        f"on `str(store_seq)`, where '10' < '2' lexicographically, "
        f"flipping the result to {b5_dt_10!r}. The string '10' starts "
        "with character '1' which has lower ASCII than '2', so lex "
        "sort picks '10' first -- distinct from numeric sort"
    )


def test_count_progress_events_and_progress_ignore_membership_contract() -> None:
    assert count_progress_events([]) == 0, (
        "C1: empty rows -> sum over empty generator -> 0. Pins the "
        "natural sum-zero fallback (no special-case empty handling "
        "needed because sum() handles it)"
    )

    ignore_members = [
        "run.created",
        "model.preflight.started",
        "model.preflight.passed",
        "model.preflight.failed",
        "model.selected.primary",
        "model.selected.fallback",
    ]
    for et in ignore_members:
        single = [_make_row(store_seq=1, event_type=et)]
        actual = count_progress_events(single)
        assert actual == 0, (
            f"C2 ({et}): single row with event_type in _PROGRESS_IGNORE "
            f"-> 0. Got {actual!r}. Pins that EACH of the 6 ignore "
            "members is excluded from the progress count individually "
            "-- a refactor removing one member from the frozenset "
            "would surface as a single failing iteration here"
        )

    non_ignore_samples = [
        "stage.started",
        "finding.created",
        "run.escalated",
        "gate.decision.emitted",
    ]
    for et in non_ignore_samples:
        single = [_make_row(store_seq=1, event_type=et)]
        actual = count_progress_events(single)
        assert actual == 1, (
            f"C3 ({et}): single row with event_type NOT in "
            f"_PROGRESS_IGNORE -> 1. Got {actual!r}. Pins that "
            "NON-preflight events count toward progress -- the "
            "progress-detection signal anti-deadlock relies on"
        )

    c4_rows = [
        _make_row(store_seq=1, event_type="run.created"),
        _make_row(store_seq=2, event_type="model.preflight.passed"),
        _make_row(store_seq=3, event_type="model.selected.primary"),
        _make_row(store_seq=4, event_type="stage.started"),
        _make_row(store_seq=5, event_type="finding.created"),
        _make_row(store_seq=6, event_type="finding.created"),
        _make_row(store_seq=7, event_type="run.escalated"),
    ]
    actual_c4 = count_progress_events(c4_rows)
    assert actual_c4 == 4, (
        f"C4: 7-row mixed sequence (3 ignored + 4 progress) -> 4. Got "
        f"{actual_c4!r}. Pins sum-over-NOT-IGNORE on a realistic "
        "mixed-row input"
    )

    c5_rows = [
        _make_row(store_seq=1, event_type="fo116.synthetic"),
        _make_row(store_seq=2, event_type=""),
        _make_row(store_seq=3, event_type="unknown.event.type"),
    ]
    actual_c5 = count_progress_events(c5_rows)
    assert actual_c5 == 3, (
        f"C5 KEY DIVERGENCE fail-open: 3 rows with novel synthetic "
        f"event types ('fo116.synthetic', '', 'unknown.event.type') -> "
        f"3 (all counted as progress). Got {actual_c5!r}. The "
        "implementation uses `not in _PROGRESS_IGNORE` -- ANY type "
        "not explicitly listed in the 6-member ignore set counts. A "
        "refactor swapping to an allowlist `in _PROGRESS_ALLOW` "
        "(known-good progress types) would flip this from 3 to 0 and "
        "silently mask all unrecognized events"
    )


def test_progress_ignore_frozenset_and_cross_helper_dual_purpose_contract() -> None:
    assert isinstance(_PROGRESS_IGNORE, frozenset), (
        f"D1: _PROGRESS_IGNORE must be a frozenset for module-level "
        f"immutability. Got type={type(_PROGRESS_IGNORE).__name__!r}. "
        "A refactor swapping to a regular `set` would silently allow "
        "`_PROGRESS_IGNORE.add('stage.started')` from any importer "
        "and corrupt the count contract globally"
    )

    expected_ignore = frozenset(
        {
            "run.created",
            "model.preflight.started",
            "model.preflight.passed",
            "model.preflight.failed",
            "model.selected.primary",
            "model.selected.fallback",
        },
    )
    assert _PROGRESS_IGNORE == expected_ignore, (
        f"D2: _PROGRESS_IGNORE must equal the exact 6-member frozenset. "
        f"Got {_PROGRESS_IGNORE!r}, expected {expected_ignore!r}. "
        "Equality covers BOTH presence (each of 6 members is in the "
        "set) AND absence (no extras like 'stage.started')"
    )
    assert len(_PROGRESS_IGNORE) == 6, (
        f"D2(len): exact 6-element cardinality. Got "
        f"len={len(_PROGRESS_IGNORE)!r}. A refactor adding a 7th "
        "preflight phase would surface here"
    )

    d3_dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    d3_rows = [_make_row(store_seq=1, event_type="run.created", occurred_at=d3_dt)]
    d3_timestamp = _first_run_created_at(d3_rows)
    d3_progress = count_progress_events(d3_rows)
    assert d3_timestamp == d3_dt, (
        f"D3 KEY DIVERGENCE(timestamp): single run.created row -> "
        f"_first_run_created_at returns the datetime ({d3_dt!r}). Got "
        f"{d3_timestamp!r}. Pins that 'run.created' is CONSUMED by "
        "the timestamp extractor"
    )
    assert d3_progress == 0, (
        f"D3 KEY DIVERGENCE(progress): SAME row -> count_progress_events "
        f"returns 0 (because 'run.created' is IN _PROGRESS_IGNORE). "
        f"Got {d3_progress!r}. Pins that 'run.created' is IGNORED by "
        "the progress counter. The two helpers use the SAME row for "
        "OPPOSITE purposes -- a refactor 'deduplicating' the helpers "
        "would have to pick one purpose and break the other"
    )

    d4_rows = [
        _make_row(
            store_seq=1,
            event_type="stage.started",
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        ),
        _make_row(
            store_seq=2,
            event_type="finding.created",
            occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        ),
    ]
    d4_timestamp = _first_run_created_at(d4_rows)
    d4_progress = count_progress_events(d4_rows)
    assert d4_timestamp is None, (
        f"D4(timestamp): no run.created row -> _first_run_created_at "
        f"returns None. Got {d4_timestamp!r}"
    )
    assert d4_progress == 2, (
        f"D4(progress): SAME rows -> both are non-ignore -> "
        f"count_progress_events returns 2. Got {d4_progress!r}. "
        "Pins the SYMMETRIC no-run.created axiom: no bootstrap "
        "timestamp AND full-progress count (every row counts toward "
        "progress when none are in the ignore set)"
    )

    d5_bootstrap_dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    d5_rows = [
        _make_row(store_seq=1, event_type="run.created", occurred_at=d5_bootstrap_dt),
        _make_row(
            store_seq=2,
            event_type="model.preflight.started",
            occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        ),
        _make_row(
            store_seq=3,
            event_type="model.preflight.passed",
            occurred_at=datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc),
        ),
        _make_row(
            store_seq=4,
            event_type="model.selected.primary",
            occurred_at=datetime(2026, 1, 1, 12, 3, tzinfo=timezone.utc),
        ),
        _make_row(
            store_seq=5,
            event_type="model.preflight.failed",
            occurred_at=datetime(2026, 1, 1, 12, 4, tzinfo=timezone.utc),
        ),
        _make_row(
            store_seq=6,
            event_type="model.selected.fallback",
            occurred_at=datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc),
        ),
    ]
    d5_timestamp = _first_run_created_at(d5_rows)
    d5_progress = count_progress_events(d5_rows)
    assert d5_timestamp == d5_bootstrap_dt, (
        f"D5(timestamp): all-bootstrap 6-row sequence -> "
        f"_first_run_created_at returns the run.created datetime "
        f"({d5_bootstrap_dt!r}). Got {d5_timestamp!r}"
    )
    assert d5_progress == 0, (
        f"D5(progress): SAME 6-row sequence -> ALL 6 events are in "
        f"_PROGRESS_IGNORE -> count_progress_events returns 0. Got "
        f"{d5_progress!r}. Pins the 'bootstrap silent' contract: a "
        "run that has executed the full preflight phase but no "
        "real progress events still has progress_count=0. This is "
        "the EXACT scenario should_emit_anti_deadlock_escalation "
        "fires on: timestamp present + 0 < min_progress_events"
    )
