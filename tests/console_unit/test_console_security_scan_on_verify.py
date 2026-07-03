from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


import json
from datetime import datetime, timezone

from console.security_scan_on_verify import (
    security_scan_category_severity_caption,
    security_scan_finding_event_ids_caption,
    security_scan_history_entry_count_caption,
    security_scan_history_export_filename_slug,
    security_scan_history_export_json,
    security_scan_history_from_timeline,
    security_scan_history_operator_metrics,
    security_scan_history_operator_metrics_caption,
    security_scan_history_operator_metrics_export_filename_slug,
    security_scan_history_operator_metrics_export_json,
    security_scan_history_operator_metrics_table_rows,
    security_scan_history_operator_metrics_table_rows_csv,
    security_scan_history_severity_sample_caption,
    security_scan_history_table_rows,
    security_scan_history_table_rows_csv,
    security_scan_linter_exit_codes_caption,
    security_scan_linter_failed_linters_caption,
    security_scan_linter_missing_linters_caption,
    security_scan_linter_nonzero_caption,
    security_scan_linter_ok_linters_caption,
    security_scan_linter_operator_metrics,
    security_scan_linter_operator_metrics_caption,
    security_scan_linter_operator_metrics_export_filename_slug,
    security_scan_linter_operator_metrics_export_json,
    security_scan_linter_operator_metrics_table_rows,
    security_scan_linter_operator_metrics_table_rows_csv,
    security_scan_linter_operator_rollup_caption,
    security_scan_linter_status_rows,
    security_scan_linter_status_summary_caption,
    security_scan_linter_worst_status_caption,
    security_scan_metadata_timeline_workflow_alignment_caption,
    security_scan_occurred_at_age_caption,
    security_scan_on_verify_from_timeline,
    security_scan_on_verify_latest_export_filename_slug,
    security_scan_on_verify_latest_export_json,
    security_scan_on_verify_latest_operator_metrics,
    security_scan_on_verify_latest_operator_metrics_caption,
    security_scan_on_verify_latest_operator_metrics_export_json,
    security_scan_on_verify_latest_operator_metrics_table_rows,
    security_scan_on_verify_latest_operator_metrics_table_rows_csv,
    security_scan_on_verify_latest_summary_rows_csv,
    security_scan_on_verify_summary_rows,
    security_scan_snippet_length_caption,
    security_scan_snippet_line_count_caption,
)


def test_security_scan_on_verify_from_timeline_none_when_missing() -> None:
    assert security_scan_on_verify_from_timeline(None) is None
    assert security_scan_on_verify_from_timeline({}) is None
    assert security_scan_on_verify_from_timeline({"security_scan_on_verify": None}) is None
    assert security_scan_on_verify_from_timeline({"security_scan_on_verify": "x"}) is None


def test_security_scan_snippet_length_caption_counts_non_whitespace() -> None:
    cap = security_scan_snippet_length_caption(
        {"security_scan_snippet": "  abc  "},
    )
    assert cap is not None
    assert "3" in cap


def test_security_scan_snippet_length_caption_none_when_empty_or_whitespace() -> None:
    assert security_scan_snippet_length_caption({}) is None
    assert security_scan_snippet_length_caption({"security_scan_snippet": ""}) is None
    assert security_scan_snippet_length_caption({"security_scan_snippet": "   \n"}) is None


def test_security_scan_snippet_length_caption_none_for_non_string() -> None:
    assert security_scan_snippet_length_caption({"security_scan_snippet": 42}) is None
    assert security_scan_snippet_length_caption(None) is None


def test_security_scan_snippet_line_count_caption() -> None:
    cap = security_scan_snippet_line_count_caption(
        {"security_scan_snippet": "a\nb\nc"},
    )
    assert cap is not None
    assert "3" in cap
    assert security_scan_snippet_line_count_caption({"security_scan_snippet": "x"}) is not None
    one = security_scan_snippet_line_count_caption({"security_scan_snippet": "only"})
    assert one is not None and "1" in one


def test_security_scan_snippet_line_count_caption_none() -> None:
    assert security_scan_snippet_line_count_caption({}) is None
    assert security_scan_snippet_line_count_caption(None) is None


def test_security_scan_finding_event_ids_caption() -> None:
    cap = security_scan_finding_event_ids_caption(
        {"finding_id": " f1 ", "event_id": "e1"},
    )
    assert cap is not None
    assert "finding_id" in cap
    assert "event_id" in cap


def test_security_scan_finding_event_ids_caption_partial() -> None:
    only_f = security_scan_finding_event_ids_caption({"finding_id": "x"})
    assert only_f == "Security scan summary: finding_id present."
    only_e = security_scan_finding_event_ids_caption({"event_id": "y"})
    assert only_e == "Security scan summary: event_id present."
    assert security_scan_finding_event_ids_caption({"finding_id": ""}) is None
    assert security_scan_finding_event_ids_caption({}) is None


def test_security_scan_occurred_at_age_caption_parses_z_suffix() -> None:
    cap = security_scan_occurred_at_age_caption(
        {"occurred_at": "2020-01-01T00:00:00Z"},
    )
    assert cap is not None
    assert "occurred_at" in cap.lower()
    assert " s " in cap


def test_security_scan_occurred_at_age_caption_none_unparseable() -> None:
    assert security_scan_occurred_at_age_caption({"occurred_at": "not-a-date"}) is None


def test_security_scan_occurred_at_age_caption_none_missing() -> None:
    assert security_scan_occurred_at_age_caption({}) is None
    assert security_scan_occurred_at_age_caption(None) is None


def test_security_scan_occurred_at_age_caption_none_future_skew() -> None:
    future = datetime.now(timezone.utc).replace(year=2099)
    cap = security_scan_occurred_at_age_caption(
        {"occurred_at": future.strftime("%Y-%m-%dT%H:%M:%SZ")},
    )
    assert cap is None


def test_security_scan_on_verify_from_timeline_returns_dict() -> None:
    body = {
        "events": [],
        "security_scan_on_verify": {
            "security_scan_exit": 0,
            "security_scan_snippet": "ok",
            "finding_id": "f1",
        },
    }
    ss = security_scan_on_verify_from_timeline(body)
    assert ss == {
        "security_scan_exit": 0,
        "security_scan_snippet": "ok",
        "finding_id": "f1",
    }


def test_security_scan_on_verify_summary_rows_empty_for_none() -> None:
    assert security_scan_on_verify_summary_rows(None) == []


def test_security_scan_on_verify_summary_rows_ordered_fields() -> None:
    summary = {
        "security_scan_exit": 2,
        "security_scan_snippet": "trace",
        "category": "verify",
        "severity": "LOW",
        "source_artifact": "writer_verifier_bundle",
        "finding_id": "fid",
        "event_id": "e1",
        "occurred_at": "2026-01-01T00:00:00Z",
    }
    rows = security_scan_on_verify_summary_rows(summary)
    labels = [r["field"] for r in rows]
    assert labels[0] == "Security scan exit"
    assert labels.index("Category") < labels.index("Event id")
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Security scan exit"] == "2"
    assert by_field["Security scan snippet"] == "trace"
    assert by_field["Category"] == "verify"
    assert by_field["Severity"] == "LOW"
    assert by_field["Source artifact"] == "writer_verifier_bundle"
    assert by_field["Finding id"] == "fid"
    assert by_field["Event id"] == "e1"
    assert by_field["Occurred at"] == "2026-01-01T00:00:00Z"


def test_security_scan_on_verify_summary_rows_includes_per_tool_exits() -> None:
    summary = {
        "security_scan_exit": 2,
        "security_scan_ruff_exit": 1,
        "security_scan_bandit_exit": 2,
        "security_scan_snippet": "tail",
    }
    rows = security_scan_on_verify_summary_rows(summary)
    labels = [r["field"] for r in rows]
    assert labels[:4] == [
        "Security scan exit",
        "Ruff exit",
        "Bandit exit",
        "Security scan snippet",
    ]


def test_security_scan_on_verify_latest_export_helpers() -> None:
    summary = {
        "security_scan_exit": 0,
        "security_scan_snippet": "ok",
        "finding_id": "f1",
    }
    rows = security_scan_on_verify_summary_rows(summary)
    csv_text = security_scan_on_verify_latest_summary_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert "ok" in csv_text
    assert json.loads(security_scan_on_verify_latest_export_json(summary))["finding_id"] == "f1"
    assert security_scan_on_verify_latest_summary_rows_csv([]) == ""
    assert json.loads(security_scan_on_verify_latest_export_json(None)) == {}
    assert json.loads(security_scan_on_verify_latest_export_json([])) == {}
    assert security_scan_on_verify_latest_export_filename_slug("Ss@x") == "ss_x"


def test_security_scan_linter_nonzero_caption_none_when_clean() -> None:
    assert security_scan_linter_nonzero_caption(None) is None
    assert security_scan_linter_nonzero_caption({}) is None
    assert (
        security_scan_linter_nonzero_caption(
            {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
        )
        is None
    )


def test_security_scan_linter_nonzero_caption_flags_ruff_and_bandit() -> None:
    cap = security_scan_linter_nonzero_caption(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 2},
    )
    assert cap is not None
    assert "Ruff" in cap and "`1`" in cap
    assert "Bandit" in cap and "`2`" in cap
    assert "Security scan metadata" in cap


def test_security_scan_linter_nonzero_caption_ignores_non_int_exits() -> None:
    assert (
        security_scan_linter_nonzero_caption(
            {"security_scan_ruff_exit": "1", "security_scan_bandit_exit": None},
        )
        is None
    )


def test_security_scan_linter_status_rows_empty_for_non_mapping() -> None:
    assert security_scan_linter_status_rows(None) == []
    assert security_scan_linter_status_rows("x") == []


def test_security_scan_linter_status_rows_both_ok_when_zero() -> None:
    rows = security_scan_linter_status_rows(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    assert [r["linter"] for r in rows] == ["Ruff", "Bandit"]
    assert all(r["status"] == "ok" for r in rows)
    assert all(r["exit"] == "0" for r in rows)


def test_security_scan_linter_status_rows_marks_failed_when_nonzero() -> None:
    rows = security_scan_linter_status_rows(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 0},
    )
    by_linter = {r["linter"]: r for r in rows}
    assert by_linter["Ruff"]["status"] == "failed"
    assert by_linter["Ruff"]["exit"] == "1"
    assert by_linter["Bandit"]["status"] == "ok"


def test_security_scan_linter_status_rows_marks_missing_when_absent() -> None:
    rows = security_scan_linter_status_rows({"security_scan_ruff_exit": 0})
    by_linter = {r["linter"]: r for r in rows}
    assert by_linter["Bandit"]["status"] == "missing"
    assert by_linter["Bandit"]["exit"] == "—"
    assert by_linter["Ruff"]["status"] == "ok"


def test_security_scan_linter_status_rows_marks_missing_for_non_int() -> None:
    rows = security_scan_linter_status_rows(
        {"security_scan_ruff_exit": "1", "security_scan_bandit_exit": True},
    )
    assert all(r["status"] == "missing" for r in rows)
    assert all(r["exit"] == "—" for r in rows)


def test_security_scan_linter_status_summary_caption_none_for_non_mapping() -> None:
    assert security_scan_linter_status_summary_caption(None) is None
    assert security_scan_linter_status_summary_caption("x") is None


def test_security_scan_linter_status_summary_caption_none_when_all_missing() -> None:
    assert security_scan_linter_status_summary_caption({}) is None
    assert (
        security_scan_linter_status_summary_caption(
            {"security_scan_ruff_exit": "1", "security_scan_bandit_exit": None},
        )
        is None
    )


def test_security_scan_linter_status_summary_caption_both_ok() -> None:
    cap = security_scan_linter_status_summary_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    assert cap == "Linter summary: 2 ok, 0 failed, 0 missing."


def test_security_scan_linter_status_summary_caption_mixed_ok_and_failed() -> None:
    cap = security_scan_linter_status_summary_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 2},
    )
    assert cap == "Linter summary: 1 ok, 1 failed, 0 missing."


def test_security_scan_linter_status_summary_caption_one_missing_one_failed() -> None:
    cap = security_scan_linter_status_summary_caption(
        {"security_scan_ruff_exit": 1},
    )
    assert cap == "Linter summary: 0 ok, 1 failed, 1 missing."


def test_security_scan_linter_worst_status_caption_none_for_non_mapping() -> None:
    assert security_scan_linter_worst_status_caption(None) is None
    assert security_scan_linter_worst_status_caption("x") is None


def test_security_scan_linter_worst_status_caption_none_when_all_missing() -> None:
    assert security_scan_linter_worst_status_caption({}) is None
    assert (
        security_scan_linter_worst_status_caption(
            {"security_scan_ruff_exit": "1", "security_scan_bandit_exit": None},
        )
        is None
    )


def test_security_scan_linter_worst_status_caption_both_ok() -> None:
    cap = security_scan_linter_worst_status_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    assert cap == "All linters passed (Ruff exit 0, Bandit exit 0)."


def test_security_scan_linter_worst_status_caption_single_failed_names_linter() -> None:
    cap = security_scan_linter_worst_status_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 2},
    )
    assert cap == "Worst linter: **Bandit** (exit `2`)."


def test_security_scan_linter_worst_status_caption_both_failed_picks_first_row() -> None:
    cap = security_scan_linter_worst_status_caption(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 2},
    )
    assert cap == "Worst linter: **Ruff** (exit `1`)."


def test_security_scan_linter_worst_status_caption_one_ok_one_missing_still_ok() -> None:
    cap = security_scan_linter_worst_status_caption(
        {"security_scan_ruff_exit": 0},
    )
    assert cap == "All linters passed (Ruff exit 0)."


def test_security_scan_linter_operator_metrics_zeros_for_non_mapping() -> None:
    metrics = security_scan_linter_operator_metrics(None)
    assert metrics == {
        "observable_count": 0,
        "ok_count": 0,
        "failed_count": 0,
        "missing_count": 0,
        "worst_status": None,
        "worst_linter": None,
        "worst_exit": None,
    }
    assert security_scan_linter_operator_metrics("x") == metrics


def test_security_scan_linter_operator_metrics_both_ok() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    assert metrics["observable_count"] == 2
    assert metrics["ok_count"] == 2
    assert metrics["failed_count"] == 0
    assert metrics["missing_count"] == 0
    assert metrics["worst_status"] == "ok"
    assert metrics["worst_linter"] is None
    assert metrics["worst_exit"] is None


def test_security_scan_linter_operator_metrics_export_json_and_csv() -> None:
    summary = {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0}
    metrics = security_scan_linter_operator_metrics(summary)
    rows = security_scan_linter_operator_metrics_table_rows(metrics)
    parsed = json.loads(security_scan_linter_operator_metrics_export_json(metrics))
    assert parsed["worst_status"] == "ok"
    assert parsed["ok_count"] == 2
    csv_text = security_scan_linter_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert security_scan_linter_operator_metrics_export_filename_slug(
        "run-abc"
    ) == security_scan_on_verify_latest_export_filename_slug("run-abc")


def test_security_scan_linter_operator_metrics_export_non_mapping() -> None:
    metrics = security_scan_linter_operator_metrics(None)
    rows = security_scan_linter_operator_metrics_table_rows(metrics)
    assert json.loads(security_scan_linter_operator_metrics_export_json(metrics)) == metrics
    assert security_scan_linter_operator_metrics_export_json(None) == "{}"
    csv_text = security_scan_linter_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert "Observable linters,0" in csv_text
    assert security_scan_linter_operator_metrics_table_rows_csv([]) == ""


def test_security_scan_linter_operator_metrics_single_failed_names_worst() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 2},
    )
    assert metrics["observable_count"] == 2
    assert metrics["ok_count"] == 1
    assert metrics["failed_count"] == 1
    assert metrics["missing_count"] == 0
    assert metrics["worst_status"] == "failed"
    assert metrics["worst_linter"] == "Bandit"
    assert metrics["worst_exit"] == 2


def test_security_scan_linter_operator_metrics_caption() -> None:
    m = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 1},
    )
    cap = security_scan_linter_operator_metrics_caption(m)
    assert cap is not None
    assert "observable=2" in cap
    assert "worst=Bandit exit 1" in cap
    assert (
        security_scan_linter_operator_metrics_caption(
            {"observable_count": 0},
        )
        is None
    )
    assert security_scan_linter_operator_metrics_caption(None) is None


def test_security_scan_linter_operator_rollup_caption() -> None:
    cap = security_scan_linter_operator_rollup_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 1},
    )
    assert cap is not None
    assert "observable=2" in cap
    assert "worst=Bandit exit 1" in cap
    assert security_scan_linter_operator_rollup_caption({}) is None


def test_security_scan_linter_operator_metrics_both_failed_prefers_ruff() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 3},
    )
    assert metrics["failed_count"] == 2
    assert metrics["ok_count"] == 0
    assert metrics["worst_status"] == "failed"
    assert metrics["worst_linter"] == "Ruff"
    assert metrics["worst_exit"] == 1


def test_security_scan_linter_operator_metrics_one_ok_one_missing() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 0},
    )
    assert metrics["observable_count"] == 1
    assert metrics["ok_count"] == 1
    assert metrics["failed_count"] == 0
    assert metrics["missing_count"] == 1
    assert metrics["worst_status"] == "ok"
    assert metrics["worst_linter"] is None
    assert metrics["worst_exit"] is None


def test_security_scan_linter_operator_metrics_all_missing_worst_none() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": "1", "security_scan_bandit_exit": True},
    )
    assert metrics["observable_count"] == 0
    assert metrics["ok_count"] == 0
    assert metrics["failed_count"] == 0
    assert metrics["missing_count"] == 2
    assert metrics["worst_status"] is None
    assert metrics["worst_linter"] is None
    assert metrics["worst_exit"] is None


def test_security_scan_linter_operator_metrics_table_rows_empty_for_non_mapping() -> None:
    assert security_scan_linter_operator_metrics_table_rows(None) == []
    assert security_scan_linter_operator_metrics_table_rows("x") == []
    assert security_scan_linter_operator_metrics_table_rows({}) == []


def test_security_scan_linter_operator_metrics_table_rows_both_ok_no_worst_rows() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    rows = security_scan_linter_operator_metrics_table_rows(metrics)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field == {
        "Observable linters": "2",
        "Ok": "2",
        "Failed": "0",
        "Missing": "0",
        "Worst status": "ok",
    }
    assert "Worst linter" not in by_field
    assert "Worst exit" not in by_field


def test_security_scan_linter_operator_metrics_table_rows_single_failed_includes_worst_rows() -> (
    None
):
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 2},
    )
    rows = security_scan_linter_operator_metrics_table_rows(metrics)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Observable linters"] == "2"
    assert by_field["Ok"] == "1"
    assert by_field["Failed"] == "1"
    assert by_field["Missing"] == "0"
    assert by_field["Worst status"] == "failed"
    assert by_field["Worst linter"] == "Bandit"
    assert by_field["Worst exit"] == "2"


def test_security_scan_linter_operator_metrics_table_rows_both_failed_prefers_ruff() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 3},
    )
    rows = security_scan_linter_operator_metrics_table_rows(metrics)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Failed"] == "2"
    assert by_field["Ok"] == "0"
    assert by_field["Worst status"] == "failed"
    assert by_field["Worst linter"] == "Ruff"
    assert by_field["Worst exit"] == "1"


def test_security_scan_linter_operator_metrics_table_rows_all_missing_omits_worst_rows() -> None:
    metrics = security_scan_linter_operator_metrics(
        {"security_scan_ruff_exit": "1", "security_scan_bandit_exit": True},
    )
    rows = security_scan_linter_operator_metrics_table_rows(metrics)
    fields = [r["field"] for r in rows]
    assert fields == ["Observable linters", "Ok", "Failed", "Missing"]
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Observable linters"] == "0"
    assert by_field["Missing"] == "2"


def test_security_scan_linter_exit_codes_caption_none_for_non_mapping() -> None:
    assert security_scan_linter_exit_codes_caption(None) is None
    assert security_scan_linter_exit_codes_caption("x") is None
    assert security_scan_linter_exit_codes_caption([1, 2]) is None


def test_security_scan_linter_exit_codes_caption_none_when_neither_observable() -> None:
    assert security_scan_linter_exit_codes_caption({}) is None
    assert (
        security_scan_linter_exit_codes_caption(
            {"security_scan_ruff_exit": True, "security_scan_bandit_exit": False},
        )
        is None
    )
    assert (
        security_scan_linter_exit_codes_caption(
            {"security_scan_ruff_exit": "0", "security_scan_bandit_exit": None},
        )
        is None
    )


def test_security_scan_linter_exit_codes_caption_ruff_only() -> None:
    cap = security_scan_linter_exit_codes_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": "x"},
    )
    assert cap == "Linter exit codes: Ruff=0."


def test_security_scan_linter_exit_codes_caption_bandit_only() -> None:
    cap = security_scan_linter_exit_codes_caption(
        {"security_scan_ruff_exit": True, "security_scan_bandit_exit": 3},
    )
    assert cap == "Linter exit codes: Bandit=3."


def test_security_scan_linter_exit_codes_caption_both_ok() -> None:
    cap = security_scan_linter_exit_codes_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    assert cap == "Linter exit codes: Ruff=0, Bandit=0."


def test_security_scan_linter_exit_codes_caption_both_failed_distinct_exits() -> None:
    cap = security_scan_linter_exit_codes_caption(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 2},
    )
    assert cap == "Linter exit codes: Ruff=1, Bandit=2."


def test_security_scan_linter_exit_codes_caption_bool_ruff_treated_as_missing() -> None:
    cap = security_scan_linter_exit_codes_caption(
        {"security_scan_ruff_exit": False, "security_scan_bandit_exit": 2},
    )
    assert cap == "Linter exit codes: Bandit=2."


def test_security_scan_linter_failed_linters_caption_none_for_non_mapping() -> None:
    assert security_scan_linter_failed_linters_caption(None) is None
    assert security_scan_linter_failed_linters_caption("x") is None
    assert security_scan_linter_failed_linters_caption([1, 2]) is None


def test_security_scan_linter_failed_linters_caption_none_when_neither_observable() -> None:
    assert security_scan_linter_failed_linters_caption({}) is None
    assert (
        security_scan_linter_failed_linters_caption(
            {"security_scan_ruff_exit": True, "security_scan_bandit_exit": "x"},
        )
        is None
    )


def test_security_scan_linter_failed_linters_caption_none_when_all_observable_ok() -> None:
    cap = security_scan_linter_failed_linters_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    assert cap is None


def test_security_scan_linter_failed_linters_caption_ruff_only_failed_singular() -> None:
    cap = security_scan_linter_failed_linters_caption(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 0},
    )
    assert cap == "Failed linter: Ruff."


def test_security_scan_linter_failed_linters_caption_bandit_only_failed_singular() -> None:
    cap = security_scan_linter_failed_linters_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 3},
    )
    assert cap == "Failed linter: Bandit."


def test_security_scan_linter_failed_linters_caption_both_failed_plural() -> None:
    cap = security_scan_linter_failed_linters_caption(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 2},
    )
    assert cap == "Failed linters: Ruff, Bandit."


def test_security_scan_linter_failed_linters_caption_one_ok_one_failed_names_only_failed() -> None:
    cap = security_scan_linter_failed_linters_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 5},
    )
    assert cap == "Failed linter: Bandit."


def test_security_scan_linter_failed_linters_caption_bool_failed_exit_treated_as_missing() -> None:
    cap = security_scan_linter_failed_linters_caption(
        {"security_scan_ruff_exit": True, "security_scan_bandit_exit": 2},
    )
    assert cap == "Failed linter: Bandit."


def test_security_scan_linter_ok_linters_caption_none_for_non_mapping() -> None:
    assert security_scan_linter_ok_linters_caption(None) is None
    assert security_scan_linter_ok_linters_caption("x") is None
    assert security_scan_linter_ok_linters_caption([1, 2]) is None


def test_security_scan_linter_ok_linters_caption_none_when_neither_observable() -> None:
    assert security_scan_linter_ok_linters_caption({}) is None
    assert (
        security_scan_linter_ok_linters_caption(
            {"security_scan_ruff_exit": True, "security_scan_bandit_exit": "x"},
        )
        is None
    )


def test_security_scan_linter_ok_linters_caption_none_when_all_failed() -> None:
    cap = security_scan_linter_ok_linters_caption(
        {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 2},
    )
    assert cap is None


def test_security_scan_linter_ok_linters_caption_ruff_only_ok_singular() -> None:
    cap = security_scan_linter_ok_linters_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 3},
    )
    assert cap == "Passing linter: Ruff."


def test_security_scan_linter_ok_linters_caption_bandit_only_ok_singular() -> None:
    cap = security_scan_linter_ok_linters_caption(
        {"security_scan_ruff_exit": 5, "security_scan_bandit_exit": 0},
    )
    assert cap == "Passing linter: Bandit."


def test_security_scan_linter_ok_linters_caption_both_ok_plural() -> None:
    cap = security_scan_linter_ok_linters_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
    )
    assert cap == "Passing linters: Ruff, Bandit."


def test_security_scan_linter_ok_linters_caption_one_ok_one_failed_names_only_passing() -> None:
    cap = security_scan_linter_ok_linters_caption(
        {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 5},
    )
    assert cap == "Passing linter: Ruff."


def test_security_scan_linter_ok_linters_caption_bool_ok_exit_treated_as_missing() -> None:
    cap = security_scan_linter_ok_linters_caption(
        {"security_scan_ruff_exit": False, "security_scan_bandit_exit": 0},
    )
    assert cap == "Passing linter: Bandit."


def test_security_scan_linter_missing_linters_caption_none_for_non_mapping() -> None:
    assert security_scan_linter_missing_linters_caption(None) is None
    assert security_scan_linter_missing_linters_caption("x") is None
    assert security_scan_linter_missing_linters_caption([1, 2]) is None


def test_security_scan_linter_missing_linters_caption_none_when_both_observable() -> None:
    assert (
        security_scan_linter_missing_linters_caption(
            {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 0},
        )
        is None
    )
    assert (
        security_scan_linter_missing_linters_caption(
            {"security_scan_ruff_exit": 1, "security_scan_bandit_exit": 2},
        )
        is None
    )
    assert (
        security_scan_linter_missing_linters_caption(
            {"security_scan_ruff_exit": 0, "security_scan_bandit_exit": 3},
        )
        is None
    )


def test_security_scan_linter_missing_linters_caption_ruff_only_missing() -> None:
    cap = security_scan_linter_missing_linters_caption(
        {"security_scan_bandit_exit": 0},
    )
    assert cap == "Missing linter: Ruff."


def test_security_scan_linter_missing_linters_caption_bandit_only_missing() -> None:
    cap = security_scan_linter_missing_linters_caption(
        {"security_scan_ruff_exit": 0},
    )
    assert cap == "Missing linter: Bandit."


def test_security_scan_linter_missing_linters_caption_both_missing() -> None:
    cap = security_scan_linter_missing_linters_caption({})
    assert cap == "Missing linters: Ruff, Bandit."


def test_security_scan_linter_missing_linters_caption_bool_treated_as_missing() -> None:
    cap = security_scan_linter_missing_linters_caption(
        {"security_scan_ruff_exit": True, "security_scan_bandit_exit": 0},
    )
    assert cap == "Missing linter: Ruff."


def test_security_scan_linter_missing_linters_caption_missing_key_observable_other() -> None:
    cap = security_scan_linter_missing_linters_caption(
        {"security_scan_bandit_exit": 1},
    )
    assert cap == "Missing linter: Ruff."


def test_security_scan_category_severity_caption_none_for_non_mapping() -> None:
    assert security_scan_category_severity_caption(None) is None
    assert security_scan_category_severity_caption("x") is None


def test_security_scan_category_severity_caption_none_when_both_missing() -> None:
    assert security_scan_category_severity_caption({}) is None
    assert security_scan_category_severity_caption({"category": "", "severity": "  "}) is None
    assert security_scan_category_severity_caption({"category": 1, "severity": None}) is None


def test_security_scan_category_severity_caption_category_only() -> None:
    cap = security_scan_category_severity_caption({"category": "  verify  "})
    assert cap == "Security scan finding: category verify."


def test_security_scan_category_severity_caption_both_legs() -> None:
    cap = security_scan_category_severity_caption(
        {"category": "gate", "severity": "HIGH"},
    )
    assert cap == "Security scan finding: category gate, severity HIGH."


def test_security_scan_category_severity_caption_severity_only() -> None:
    cap = security_scan_category_severity_caption({"severity": "low"})
    assert cap == "Security scan finding: severity low."


def test_security_scan_metadata_timeline_workflow_alignment_scan_but_effective_false() -> None:
    cap = security_scan_metadata_timeline_workflow_alignment_caption(
        timeline_security_scan_on_verify={"security_scan_exit": 1},
        explainer_payload={"effective_enabled": False, "load_error": None},
    )
    assert cap is not None
    assert "effective false" in cap.lower()


def test_security_scan_metadata_timeline_workflow_alignment_effective_true_no_scan() -> None:
    cap = security_scan_metadata_timeline_workflow_alignment_caption(
        timeline_security_scan_on_verify=None,
        explainer_payload={"effective_enabled": True, "load_error": None},
    )
    assert cap is not None
    assert "no **security_scan_on_verify**" in cap


def test_security_scan_metadata_timeline_workflow_alignment_none_when_aligned() -> None:
    assert (
        security_scan_metadata_timeline_workflow_alignment_caption(
            timeline_security_scan_on_verify=None,
            explainer_payload={"effective_enabled": False, "load_error": None},
        )
        is None
    )
    assert (
        security_scan_metadata_timeline_workflow_alignment_caption(
            timeline_security_scan_on_verify={"security_scan_exit": 0},
            explainer_payload={"effective_enabled": True, "load_error": None},
        )
        is None
    )


def test_security_scan_metadata_timeline_workflow_alignment_none_on_load_error() -> None:
    assert (
        security_scan_metadata_timeline_workflow_alignment_caption(
            timeline_security_scan_on_verify={"security_scan_exit": 1},
            explainer_payload={"effective_enabled": False, "load_error": "boom"},
        )
        is None
    )


def test_security_scan_metadata_timeline_workflow_alignment_none_on_nonbool_effective() -> None:
    assert (
        security_scan_metadata_timeline_workflow_alignment_caption(
            timeline_security_scan_on_verify={"security_scan_exit": 1},
            explainer_payload={"effective_enabled": 1, "load_error": None},
        )
        is None
    )


def test_security_scan_history_from_timeline() -> None:
    hist = [
        {
            "event_id": "e1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "severity": "low",
            "security_scan_ruff_exit": 0,
            "security_scan_bandit_exit": 1,
            "security_scan_exit": 1,
            "finding_id": "f1",
        },
    ]
    body = {"security_scan_on_verify_history": hist}
    assert security_scan_history_from_timeline(body) == hist
    assert security_scan_history_from_timeline({}) == []
    assert security_scan_history_from_timeline(None) == []


def test_security_scan_history_table_rows_two_findings() -> None:
    rows = security_scan_history_table_rows(
        [
            {
                "occurred_at": "t1",
                "severity": "low",
                "security_scan_ruff_exit": 0,
                "security_scan_bandit_exit": 0,
                "security_scan_exit": 0,
                "finding_id": "f1",
                "event_id": "e1",
            },
            {
                "occurred_at": "t2",
                "severity": "medium",
                "security_scan_ruff_exit": 2,
                "security_scan_bandit_exit": 0,
                "security_scan_exit": 1,
                "finding_id": "f2",
                "event_id": "e2",
            },
        ],
    )
    assert len(rows) == 2
    assert rows[0]["#"] == "1"
    assert rows[1]["Ruff exit"] == "2"
    assert rows[1]["Finding id"] == "f2"


def test_security_scan_history_entry_count_caption() -> None:
    cap = security_scan_history_entry_count_caption([{}, {}])
    assert cap is not None
    assert "2" in cap
    assert security_scan_history_entry_count_caption([]) is None
    assert security_scan_history_entry_count_caption(None) is None


def test_security_scan_history_severity_sample_caption() -> None:
    hist = [
        {"severity": "high"},
        {"severity": " medium "},
        {"severity": "high"},
        {"severity": ""},
        {"severity": 1},
    ]
    cap = security_scan_history_severity_sample_caption(hist)
    assert cap == "Security scan history distinct severities: high, medium."
    assert security_scan_history_severity_sample_caption([]) is None
    assert security_scan_history_severity_sample_caption([{}]) is None
    keys = [f"s{i}" for i in range(8)]
    hist_many = [{"severity": k} for k in keys]
    cap_many = security_scan_history_severity_sample_caption(hist_many, max_n=6)
    assert cap_many is not None
    assert "(+2 more)" in cap_many


def test_security_scan_history_table_rows_csv_empty() -> None:
    assert security_scan_history_table_rows_csv([]) == ""


def test_security_scan_history_export_json_and_csv() -> None:
    hist = [{"severity": "low", "finding_id": "f1"}]
    rows = security_scan_history_table_rows(hist)
    csv_body = security_scan_history_table_rows_csv(rows)
    assert csv_body.startswith("#,Occurred at,Severity,")
    parsed = json.loads(security_scan_history_export_json(hist))
    assert len(parsed) == 1
    assert parsed[0]["finding_id"] == "f1"


def test_security_scan_history_export_filename_slug() -> None:
    assert security_scan_history_export_filename_slug("run/1!") == "run_1"


def test_security_scan_history_operator_metrics_empty() -> None:
    m = security_scan_history_operator_metrics([])
    assert m["entry_count"] == 0
    assert security_scan_history_operator_metrics_caption(m) is None
    assert security_scan_history_operator_metrics_table_rows(m)


def test_security_scan_history_operator_metrics_multi_entry() -> None:
    hist = [
        {
            "severity": "high",
            "security_scan_ruff_exit": 1,
            "security_scan_bandit_exit": 0,
            "security_scan_exit": 1,
        },
        {
            "severity": "medium",
            "security_scan_ruff_exit": 0,
            "security_scan_bandit_exit": 2,
        },
        {
            "severity": "high",
            "security_scan_ruff_exit": 0,
            "security_scan_bandit_exit": 0,
        },
    ]
    m = security_scan_history_operator_metrics(hist)
    assert m["entry_count"] == 3
    assert m["distinct_severity_count"] == 2
    assert m["severity_sample"] == ["high", "medium"]
    assert m["ruff_nonzero_exit_count"] == 1
    assert m["bandit_nonzero_exit_count"] == 1
    assert m["failed_scan_exit_count"] == 1
    cap = security_scan_history_operator_metrics_caption(m)
    assert cap is not None
    assert "3" in cap
    assert "Scan failed" in cap
    assert "severity sample" in cap
    assert "high" in cap
    rows = security_scan_history_operator_metrics_table_rows(m)
    fields = {r["field"] for r in rows}
    assert "Severity sample" in fields
    assert "Ruff non-zero exits" in fields
    assert "Bandit non-zero exits" in fields


def test_security_scan_history_operator_metrics_export() -> None:
    hist = [{"severity": "low", "security_scan_ruff_exit": 1}]
    m = security_scan_history_operator_metrics(hist)
    parsed = json.loads(security_scan_history_operator_metrics_export_json(m))
    assert parsed["entry_count"] == 1
    assert json.loads(security_scan_history_operator_metrics_export_json(None)) == {}
    rows = security_scan_history_operator_metrics_table_rows(m)
    csv_text = security_scan_history_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert security_scan_history_operator_metrics_table_rows_csv([]) == ""
    assert security_scan_history_operator_metrics_export_filename_slug("run/1!") == "run_1"


def test_security_scan_on_verify_latest_operator_metrics_empty() -> None:
    m = security_scan_on_verify_latest_operator_metrics(None)
    assert m["category_present"] is False
    assert security_scan_on_verify_latest_operator_metrics_caption(m) is None
    assert security_scan_on_verify_latest_operator_metrics_table_rows(m) == []


def test_security_scan_on_verify_latest_operator_metrics_finding() -> None:
    summary = {
        "category": "security",
        "severity": "high",
        "security_scan_snippet": "  line one\nline two  ",
        "finding_id": "f-1",
        "event_id": "ev-1",
    }
    m = security_scan_on_verify_latest_operator_metrics(summary)
    assert m["category_present"] is True
    assert m["severity_present"] is True
    assert m["snippet_char_len"] > 0
    assert m["finding_id_present"] is True
    assert m["event_id_present"] is True
    cap = security_scan_on_verify_latest_operator_metrics_caption(m)
    assert cap is not None
    assert "category" in cap
    rows = security_scan_on_verify_latest_operator_metrics_table_rows(m)
    fields = {r["field"] for r in rows}
    assert "Snippet length (chars)" in fields


def test_security_scan_on_verify_latest_operator_metrics_export() -> None:
    summary = {"category": "x", "severity": "low"}
    m = security_scan_on_verify_latest_operator_metrics(summary)
    parsed = json.loads(security_scan_on_verify_latest_operator_metrics_export_json(m))
    assert parsed["category_present"] is True
    assert json.loads(security_scan_on_verify_latest_operator_metrics_export_json(None)) == {}
    rows = security_scan_on_verify_latest_operator_metrics_table_rows(m)
    csv_text = security_scan_on_verify_latest_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert security_scan_on_verify_latest_operator_metrics_table_rows_csv([]) == ""


def test_security_scan_on_verify_latest_operator_metrics_linter_exits() -> None:
    summary = {
        "category": "security",
        "security_scan_ruff_exit": 0,
        "security_scan_bandit_exit": 1,
    }
    m = security_scan_on_verify_latest_operator_metrics(summary)
    assert m["security_scan_ruff_exit"] == 0
    assert m["security_scan_bandit_exit"] == 1
    cap = security_scan_on_verify_latest_operator_metrics_caption(m)
    assert cap is not None
    assert "ruff_exit=0" in cap
    assert "bandit_exit=1" in cap
