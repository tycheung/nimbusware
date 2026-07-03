from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


import json

import pytest

from console.self_refinement import (
    self_refinement_auto_promote_caption,
    self_refinement_description_length_caption,
    self_refinement_evaluation_caption,
    self_refinement_from_timeline,
    self_refinement_iteration_caption,
    self_refinement_latest_export_filename_slug,
    self_refinement_latest_export_json,
    self_refinement_latest_summary_rows_csv,
    self_refinement_llm_critique_stage_caption,
    self_refinement_marker_avg_interval_caption,
    self_refinement_marker_avg_interval_seconds,
    self_refinement_marker_first_last_caption,
    self_refinement_marker_history_entry_count_caption,
    self_refinement_marker_history_export_filename_slug,
    self_refinement_marker_history_export_json,
    self_refinement_marker_history_from_timeline,
    self_refinement_marker_history_operator_metrics,
    self_refinement_marker_history_operator_metrics_caption,
    self_refinement_marker_history_operator_metrics_export_json,
    self_refinement_marker_history_operator_metrics_table_rows,
    self_refinement_marker_history_operator_metrics_table_rows_csv,
    self_refinement_marker_history_table_rows,
    self_refinement_marker_history_table_rows_csv,
    self_refinement_marker_window_caption,
    self_refinement_marker_window_seconds,
    self_refinement_markers_per_minute,
    self_refinement_markers_per_minute_caption,
    self_refinement_phase_d_signal_caption,
    self_refinement_policy_attempt_caption,
    self_refinement_prior_gate_verdict_caption,
    self_refinement_session_caption,
    self_refinement_snapshot_from_compare_paste,
    self_refinement_stage_name_caption,
    self_refinement_summary_rows,
    self_refinement_timeline_metrics_table_rows,
    self_refinement_timeline_operator_metrics,
    self_refinement_timeline_operator_metrics_export_filename_slug,
    self_refinement_timeline_operator_metrics_export_json,
    self_refinement_timeline_operator_metrics_table_rows_csv,
    self_refinement_timeline_policy_version_caption,
    self_refinement_ungated_loop_caption,
    self_refinement_version_attempt_caption,
)


def test_self_refinement_policy_attempt_caption() -> None:
    cap_match = self_refinement_policy_attempt_caption(
        {"attempt": 1},
        {"marker_merge": {"would_emit_marker_after_env": True}},
    )
    assert cap_match is not None
    assert "match" in cap_match
    cap_mismatch = self_refinement_policy_attempt_caption(
        {"attempt": 2},
        {"marker_merge": {"would_emit_marker_after_env": True}},
    )
    assert cap_mismatch is not None
    assert "mismatch" in cap_mismatch
    cap_tl_only = self_refinement_policy_attempt_caption(
        {"attempt": 3},
        {"marker_merge": {"would_emit_marker_after_env": False}},
    )
    assert cap_tl_only is not None
    assert "timeline=3" in cap_tl_only
    assert self_refinement_policy_attempt_caption(None, None) is None
    assert self_refinement_policy_attempt_caption({}, None) is None
    assert self_refinement_policy_attempt_caption({"attempt": "1"}, None) is None


def test_self_refinement_version_attempt_caption() -> None:
    cap = self_refinement_version_attempt_caption(
        {"version": 2, "attempt": 1},
    )
    assert cap is not None
    assert "version=2" in cap
    assert "attempt=1" in cap
    assert self_refinement_version_attempt_caption({"version": 1}) is not None
    assert self_refinement_version_attempt_caption(None) is None
    assert self_refinement_version_attempt_caption({}) is None


def test_self_refinement_from_timeline_none_when_missing() -> None:
    assert self_refinement_from_timeline(None) is None
    assert self_refinement_from_timeline({}) is None
    assert self_refinement_from_timeline({"self_refinement": None}) is None
    assert self_refinement_from_timeline({"self_refinement": "x"}) is None


def test_self_refinement_from_timeline_returns_dict() -> None:
    body = {
        "events": [],
        "self_refinement": {
            "version": "v1",
            "description": "policy note",
            "stage_name": "self_refinement:policy",
            "attempt": 1,
        },
    }
    sr = self_refinement_from_timeline(body)
    assert sr == {
        "version": "v1",
        "description": "policy note",
        "stage_name": "self_refinement:policy",
        "attempt": 1,
    }


def test_snapshot_from_compare_paste_bare_self_refinement() -> None:
    bare = {"version": 3, "description": "only inner"}
    assert self_refinement_snapshot_from_compare_paste(bare) == bare


def test_snapshot_from_compare_paste_full_timeline() -> None:
    body = {
        "run_id": "00000000-0000-4000-8000-000000000001",
        "events": [],
        "self_refinement": {"version": 9, "description": "from timeline"},
    }
    assert self_refinement_snapshot_from_compare_paste(body) == {
        "version": 9,
        "description": "from timeline",
    }


def test_snapshot_from_compare_paste_timeline_events_only() -> None:
    """``events`` list implies a timeline body even without ``self_refinement`` key."""
    assert self_refinement_snapshot_from_compare_paste({"events": []}) is None


def test_snapshot_from_compare_paste_timeline_null_block() -> None:
    assert (
        self_refinement_snapshot_from_compare_paste({"events": [], "self_refinement": None}) is None
    )


def test_self_refinement_timeline_operator_metrics_ungated_fields() -> None:
    sr = {
        "version": 1,
        "ungated_loop": True,
        "ungated_iteration_count": 2,
    }
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["ungated_loop"] is True
    assert m["ungated_iteration_count"] == 2
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Ungated loop"] == "True"
    assert by["Ungated iteration count"] == "2"


def test_self_refinement_timeline_operator_metrics_loop_signal_count() -> None:
    sr = {"version": 1, "loop_signal_count": 3, "ungated_loop": True}
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["loop_signal_count"] == 3
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Loop signal count"] == "3"


def test_self_refinement_timeline_operator_metrics_prior_gate_and_llm_summary() -> None:
    sr = {
        "version": 1,
        "prior_gate_verdict": "hold",
        "llm_critique_summary": "policy suggests follow-up",
    }
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["prior_gate_verdict"] == "hold"
    assert m["llm_critique_summary_preview"] == "policy suggests follow-up"
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Prior gate verdict"] == "hold"
    assert "follow-up" in by["LLM critique summary (preview)"]


def test_self_refinement_timeline_operator_metrics_gate_and_progress() -> None:
    sr = {
        "version": 1,
        "gate_decision": "continue",
        "iteration_progress_ratio": 0.5,
        "should_continue": True,
    }
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["gate_decision"] == "continue"
    assert m["iteration_progress_ratio"] == 0.5
    assert m["should_continue"] is True
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Gate decision"] == "continue"
    assert by["Iteration progress ratio"] == "0.500"


def test_self_refinement_timeline_operator_metrics_max_iterations() -> None:
    sr = {
        "version": 1,
        "max_iterations": 3,
        "max_iterations_exceeded": False,
    }
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["max_iterations"] == 3
    assert m["max_iterations_exceeded"] is False
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Max iterations"] == "3"
    assert by["Max iterations exceeded"] == "False"


def test_self_refinement_timeline_operator_metrics_marker_count() -> None:
    sr = {"version": 1, "marker_count": 3, "stage_name": "self_refinement:policy"}
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["marker_count"] == 3
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Self-refinement markers (session)"] == "3"


def test_self_refinement_timeline_policy_version_caption_match() -> None:
    cap = self_refinement_timeline_policy_version_caption(
        {"version": 1},
        {
            "policy_yaml": {"policy_yaml_top_level_version_int": 1, "version": 1},
            "marker_merge": {"merged_version": 1},
        },
    )
    assert cap is not None
    assert "timeline=1" in cap
    assert "match" in cap


def test_self_refinement_timeline_policy_version_caption_mismatch() -> None:
    cap = self_refinement_timeline_policy_version_caption(
        {"version": 2},
        {"policy_yaml": {"version": 1}, "marker_merge": {"merged_version": 1}},
    )
    assert cap is not None
    assert "mismatch" in cap


def test_self_refinement_timeline_policy_version_caption_none_without_timeline_version() -> None:
    assert self_refinement_timeline_policy_version_caption(None, {}) is None
    assert self_refinement_timeline_policy_version_caption({}, {}) is None


def test_self_refinement_summary_rows_empty_for_none() -> None:
    assert self_refinement_summary_rows(None) == []


def test_self_refinement_summary_rows_ordered_fields() -> None:
    sr = {
        "version": "v2",
        "description": "second",
        "stage_name": "self_refinement:policy",
        "attempt": 1,
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:01Z",
        "last_marker_occurred_at": "2026-01-01T00:00:02Z",
        "event_id": "e1",
        "occurred_at": "2026-01-01T00:00:00Z",
    }
    rows = self_refinement_summary_rows(sr)
    labels = [r["field"] for r in rows]
    assert labels[0] == "Version"
    assert labels.index("Description") < labels.index("Marker count (session)")
    assert labels.index("Marker count (session)") < labels.index("First marker occurred at")
    assert labels.index("First marker occurred at") < labels.index("Last marker occurred at")
    assert labels.index("Last marker occurred at") < labels.index("Event id")
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Version"] == "v2"
    assert by_field["Description"] == "second"
    assert by_field["Stage name"] == "self_refinement:policy"
    assert by_field["Attempt"] == "1"
    assert by_field["Marker count (session)"] == "2"
    assert by_field["First marker occurred at"] == "2026-01-01T00:00:01Z"
    assert by_field["Last marker occurred at"] == "2026-01-01T00:00:02Z"
    assert by_field["Event id"] == "e1"
    assert by_field["Occurred at"] == "2026-01-01T00:00:00Z"


def test_self_refinement_latest_export_helpers() -> None:
    sr = {
        "version": "v2",
        "description": "policy note",
        "stage_name": "self_refinement:policy",
        "attempt": 1,
    }
    rows = self_refinement_summary_rows(sr)
    csv_text = self_refinement_latest_summary_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert "policy note" in csv_text
    assert json.loads(self_refinement_latest_export_json(sr))["attempt"] == 1
    assert self_refinement_latest_summary_rows_csv([]) == ""
    assert json.loads(self_refinement_latest_export_json(None)) == {}
    assert json.loads(self_refinement_latest_export_json([])) == {}
    assert self_refinement_latest_export_filename_slug("Sr@x") == "sr_x"


def test_self_refinement_timeline_operator_metrics_absent() -> None:
    m = self_refinement_timeline_operator_metrics(None)
    assert m == {"present": False}
    assert self_refinement_timeline_metrics_table_rows(m) == []


def test_self_refinement_timeline_operator_metrics_preview_and_version() -> None:
    long_desc = "x" * 300
    sr = {
        "version": "2",
        "description": long_desc,
        "attempt": 3,
        "stage_name": "self_refinement:policy",
    }
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["present"] is True
    assert m["description_char_len"] == 300
    assert m["description_preview"].endswith("...")
    assert len(m["description_preview"]) == 240 + 3
    assert m["version_as_int"] == 2
    assert m["attempt_raw"] == 3
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Description length (chars)"] == "300"
    assert by["Version (integer parse when digits-only)"] == "2"


def test_self_refinement_timeline_operator_metrics_export_json_and_csv() -> None:
    sr = {
        "version": "2",
        "description": "hello",
        "attempt": 3,
        "stage_name": "self_refinement:policy",
    }
    metrics = self_refinement_timeline_operator_metrics(sr)
    rows = self_refinement_timeline_metrics_table_rows(metrics)
    parsed = json.loads(self_refinement_timeline_operator_metrics_export_json(metrics))
    assert parsed["present"] is True
    assert parsed["description_char_len"] == 5
    csv_text = self_refinement_timeline_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert self_refinement_timeline_operator_metrics_export_filename_slug(
        "run-abc"
    ) == self_refinement_latest_export_filename_slug("run-abc")


def test_self_refinement_timeline_operator_metrics_export_absent() -> None:
    metrics = self_refinement_timeline_operator_metrics(None)
    rows = self_refinement_timeline_metrics_table_rows(metrics)
    assert json.loads(self_refinement_timeline_operator_metrics_export_json(metrics)) == {}
    assert self_refinement_timeline_operator_metrics_export_json(None) == "{}"
    assert self_refinement_timeline_operator_metrics_table_rows_csv(rows) == ""
    assert self_refinement_timeline_operator_metrics_table_rows_csv([]) == ""


def test_self_refinement_marker_window_seconds_none_for_missing_summary() -> None:
    assert self_refinement_marker_window_seconds(None) is None
    assert self_refinement_marker_window_seconds({}) is None


def test_self_refinement_marker_window_seconds_zero_for_single_marker() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:05Z",
        "last_marker_occurred_at": "2026-01-01T00:00:05Z",
    }
    assert self_refinement_marker_window_seconds(sr) == 0


def test_self_refinement_marker_window_seconds_delta_between_two_markers() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:42Z",
    }
    assert self_refinement_marker_window_seconds(sr) == 42


def test_self_refinement_marker_window_seconds_none_when_first_missing() -> None:
    sr = {"last_marker_occurred_at": "2026-01-01T00:00:42Z"}
    assert self_refinement_marker_window_seconds(sr) is None


def test_self_refinement_marker_window_seconds_none_when_iso_malformed() -> None:
    sr = {
        "first_marker_occurred_at": "not-a-date",
        "last_marker_occurred_at": "2026-01-01T00:00:42Z",
    }
    assert self_refinement_marker_window_seconds(sr) is None


def test_self_refinement_marker_window_seconds_collapses_negative_delta() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:42Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    assert self_refinement_marker_window_seconds(sr) is None


def test_self_refinement_metrics_table_rows_include_marker_window() -> None:
    sr = {
        "version": 1,
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["marker_window_seconds"] == 30
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Marker window (s)"] == "30"


def test_self_refinement_metrics_table_rows_omit_window_when_unavailable() -> None:
    m = self_refinement_timeline_operator_metrics({"version": 1, "marker_count": 1})
    assert "marker_window_seconds" not in m
    rows = self_refinement_timeline_metrics_table_rows(m)
    assert all(r["field"] != "Marker window (s)" for r in rows)


def test_self_refinement_marker_avg_interval_seconds_none_for_non_mapping() -> None:
    assert self_refinement_marker_avg_interval_seconds(None) is None
    assert self_refinement_marker_avg_interval_seconds("x") is None


def test_self_refinement_marker_avg_interval_seconds_none_for_single_marker() -> None:
    sr = {
        "marker_count": 1,
        "first_marker_occurred_at": "2026-01-01T00:00:05Z",
        "last_marker_occurred_at": "2026-01-01T00:00:05Z",
    }
    assert self_refinement_marker_avg_interval_seconds(sr) is None


def test_self_refinement_marker_avg_interval_seconds_two_markers_equals_window() -> None:
    sr = {
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_avg_interval_seconds(sr) == 30


def test_self_refinement_marker_avg_interval_seconds_four_markers_rounds_window_div_three() -> None:
    sr = {
        "marker_count": 4,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:10Z",
    }
    assert self_refinement_marker_avg_interval_seconds(sr) == 3


def test_self_refinement_marker_avg_interval_seconds_none_when_window_missing() -> None:
    sr = {"marker_count": 4, "first_marker_occurred_at": "not-a-date"}
    assert self_refinement_marker_avg_interval_seconds(sr) is None


def test_self_refinement_marker_avg_interval_seconds_none_when_marker_count_missing() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_avg_interval_seconds(sr) is None


def test_self_refinement_marker_avg_interval_seconds_none_when_marker_count_bool() -> None:
    sr = {
        "marker_count": True,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_avg_interval_seconds(sr) is None


def test_self_refinement_metrics_table_rows_include_marker_avg_interval() -> None:
    sr = {
        "version": 1,
        "marker_count": 4,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    m = self_refinement_timeline_operator_metrics(sr)
    assert m["marker_avg_interval_seconds"] == 10
    rows = self_refinement_timeline_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Marker average interval (s)"] == "10"


def test_self_refinement_metrics_table_rows_omit_avg_when_unavailable() -> None:
    m = self_refinement_timeline_operator_metrics({"version": 1, "marker_count": 1})
    assert "marker_avg_interval_seconds" not in m
    rows = self_refinement_timeline_metrics_table_rows(m)
    assert all(r["field"] != "Marker average interval (s)" for r in rows)


def test_self_refinement_session_caption_none_for_non_mapping() -> None:
    assert self_refinement_session_caption(None) is None
    assert self_refinement_session_caption("x") is None


def test_self_refinement_session_caption_none_when_marker_count_missing() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_session_caption(sr) is None


def test_self_refinement_session_caption_none_when_marker_count_bool() -> None:
    assert self_refinement_session_caption({"marker_count": True}) is None


def test_self_refinement_session_caption_none_when_marker_count_zero() -> None:
    assert self_refinement_session_caption({"marker_count": 0}) is None


def test_self_refinement_session_caption_single_marker() -> None:
    sr = {
        "marker_count": 1,
        "first_marker_occurred_at": "2026-01-01T00:00:05Z",
        "last_marker_occurred_at": "2026-01-01T00:00:05Z",
    }
    assert self_refinement_session_caption(sr) == "Self-refinement: single marker."


def test_self_refinement_session_caption_two_markers() -> None:
    sr = {
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_session_caption(sr) == "Self-refinement: 2 markers across 30s (avg 30s)."


def test_self_refinement_session_caption_four_markers_uses_window_div_three() -> None:
    sr = {
        "marker_count": 4,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_session_caption(sr) == "Self-refinement: 4 markers across 30s (avg 10s)."


def test_self_refinement_session_caption_none_when_window_unavailable_for_multi() -> None:
    sr = {
        "marker_count": 3,
        "first_marker_occurred_at": "not-a-date",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_session_caption(sr) is None


def test_self_refinement_markers_per_minute_none_for_non_mapping() -> None:
    assert self_refinement_markers_per_minute(None) is None
    assert self_refinement_markers_per_minute("x") is None


def test_self_refinement_markers_per_minute_none_for_single_marker() -> None:
    sr = {
        "marker_count": 1,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    assert self_refinement_markers_per_minute(sr) is None


def test_self_refinement_markers_per_minute_two_markers_thirty_seconds_yields_four() -> None:
    sr = {
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute(sr) == 4


def test_self_refinement_markers_per_minute_four_markers_thirty_seconds_yields_eight() -> None:
    sr = {
        "marker_count": 4,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute(sr) == 8


def test_self_refinement_markers_per_minute_none_when_window_missing() -> None:
    sr = {"marker_count": 3}
    assert self_refinement_markers_per_minute(sr) is None


def test_self_refinement_markers_per_minute_none_when_marker_count_missing() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute(sr) is None


def test_self_refinement_markers_per_minute_none_when_marker_count_bool() -> None:
    sr = {
        "marker_count": True,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute(sr) is None


def test_self_refinement_markers_per_minute_none_when_window_zero() -> None:
    sr = {
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    assert self_refinement_markers_per_minute(sr) is None


def test_self_refinement_metrics_table_rows_include_markers_per_minute() -> None:
    sr = {
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    metrics = self_refinement_timeline_operator_metrics(sr)
    assert metrics.get("markers_per_minute") == 4
    rows = self_refinement_timeline_metrics_table_rows(metrics)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field.get("Markers per minute") == "4"


def test_self_refinement_metrics_table_rows_omit_markers_per_minute_when_unavailable() -> None:
    sr = {"marker_count": 1, "first_marker_occurred_at": "2026-01-01T00:00:00Z"}
    metrics = self_refinement_timeline_operator_metrics(sr)
    assert "markers_per_minute" not in metrics
    rows = self_refinement_timeline_metrics_table_rows(metrics)
    fields = {r["field"] for r in rows}
    assert "Markers per minute" not in fields


def test_self_refinement_marker_first_last_caption_none_for_non_mapping() -> None:
    assert self_refinement_marker_first_last_caption(None) is None
    assert self_refinement_marker_first_last_caption("x") is None


def test_self_refinement_marker_first_last_caption_none_when_both_missing() -> None:
    assert self_refinement_marker_first_last_caption({}) is None


def test_self_refinement_marker_first_last_caption_none_when_first_missing() -> None:
    sr = {"last_marker_occurred_at": "2026-01-01T00:00:30Z"}
    assert self_refinement_marker_first_last_caption(sr) is None


def test_self_refinement_marker_first_last_caption_none_when_last_missing() -> None:
    sr = {"first_marker_occurred_at": "2026-01-01T00:00:00Z"}
    assert self_refinement_marker_first_last_caption(sr) is None


def test_self_refinement_marker_first_last_caption_none_when_iso_unparseable() -> None:
    sr = {
        "first_marker_occurred_at": "not-a-date",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_first_last_caption(sr) is None
    sr2 = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "also-bad",
    }
    assert self_refinement_marker_first_last_caption(sr2) is None


def test_self_refinement_marker_first_last_caption_single_when_equal() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    cap = self_refinement_marker_first_last_caption(sr)
    assert cap == "Markers: single at 2026-01-01T00:00:00Z."


def test_self_refinement_marker_first_last_caption_first_last_when_differ() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    cap = self_refinement_marker_first_last_caption(sr)
    assert cap == ("Markers: first 2026-01-01T00:00:00Z, last 2026-01-01T00:00:30Z.")


def test_self_refinement_marker_first_last_caption_strips_whitespace_in_raw_iso() -> None:
    sr = {
        "first_marker_occurred_at": " 2026-01-01T00:00:00Z ",
        "last_marker_occurred_at": " 2026-01-01T00:00:30Z ",
    }
    cap = self_refinement_marker_first_last_caption(sr)
    assert cap == ("Markers: first 2026-01-01T00:00:00Z, last 2026-01-01T00:00:30Z.")


def test_self_refinement_marker_avg_interval_caption_none_for_non_mapping() -> None:
    assert self_refinement_marker_avg_interval_caption(None) is None
    assert self_refinement_marker_avg_interval_caption("x") is None


def test_self_refinement_marker_avg_interval_caption_none_for_single_marker() -> None:
    sr = {
        "marker_count": 1,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    assert self_refinement_marker_avg_interval_caption(sr) is None


def test_self_refinement_marker_avg_interval_caption_two_markers_thirty_seconds() -> None:
    sr = {
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_avg_interval_caption(sr) == "Markers: avg interval ~30s."


def test_self_refinement_marker_avg_interval_caption_four_markers_thirty_seconds() -> None:
    sr = {
        "marker_count": 4,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_avg_interval_caption(sr) == "Markers: avg interval ~10s."


def test_self_refinement_marker_avg_interval_caption_none_when_window_missing() -> None:
    sr = {"marker_count": 4, "first_marker_occurred_at": "2026-01-01T00:00:00Z"}
    assert self_refinement_marker_avg_interval_caption(sr) is None


def test_self_refinement_marker_avg_interval_caption_none_when_marker_count_missing() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_avg_interval_caption(sr) is None


def test_self_refinement_marker_avg_interval_caption_none_when_marker_count_bool() -> None:
    sr = {
        "marker_count": True,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_avg_interval_caption(sr) is None


def test_self_refinement_markers_per_minute_caption_none_for_non_mapping() -> None:
    assert self_refinement_markers_per_minute_caption(None) is None
    assert self_refinement_markers_per_minute_caption("x") is None


def test_self_refinement_markers_per_minute_caption_none_for_single_marker() -> None:
    sr = {
        "marker_count": 1,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    assert self_refinement_markers_per_minute_caption(sr) is None


def test_self_refinement_markers_per_minute_caption_two_markers_thirty_seconds() -> None:
    sr = {
        "marker_count": 2,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute_caption(sr) == "Markers: 4/min."


def test_self_refinement_markers_per_minute_caption_four_markers_thirty_seconds() -> None:
    sr = {
        "marker_count": 4,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute_caption(sr) == "Markers: 8/min."


def test_self_refinement_markers_per_minute_caption_none_when_window_missing() -> None:
    sr = {"marker_count": 4, "first_marker_occurred_at": "2026-01-01T00:00:00Z"}
    assert self_refinement_markers_per_minute_caption(sr) is None


def test_self_refinement_markers_per_minute_caption_none_when_marker_count_missing() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute_caption(sr) is None


def test_self_refinement_markers_per_minute_caption_none_when_marker_count_bool() -> None:
    sr = {
        "marker_count": True,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_markers_per_minute_caption(sr) is None


def test_self_refinement_markers_per_minute_caption_none_when_window_zero() -> None:
    sr = {
        "marker_count": 3,
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    assert self_refinement_markers_per_minute_caption(sr) is None


def test_self_refinement_marker_window_caption_none_for_non_mapping() -> None:
    assert self_refinement_marker_window_caption(None) is None
    assert self_refinement_marker_window_caption("x") is None
    assert self_refinement_marker_window_caption([1, 2]) is None


def test_self_refinement_marker_window_caption_none_when_both_missing() -> None:
    assert self_refinement_marker_window_caption({}) is None


def test_self_refinement_marker_window_caption_none_when_only_first() -> None:
    sr = {"first_marker_occurred_at": "2026-01-01T00:00:00Z"}
    assert self_refinement_marker_window_caption(sr) is None


def test_self_refinement_marker_window_caption_none_when_only_last() -> None:
    sr = {"last_marker_occurred_at": "2026-01-01T00:00:30Z"}
    assert self_refinement_marker_window_caption(sr) is None


def test_self_refinement_marker_window_caption_zero_when_first_equals_last() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:00Z",
    }
    assert self_refinement_marker_window_caption(sr) == "Marker window: 0s."


def test_self_refinement_marker_window_caption_thirty_second_span() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:00:30Z",
    }
    assert self_refinement_marker_window_caption(sr) == "Marker window: 30s."


def test_self_refinement_marker_window_caption_multi_minute_span() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "2026-01-01T00:02:15Z",
    }
    assert self_refinement_marker_window_caption(sr) == "Marker window: 135s."


def test_self_refinement_marker_window_caption_none_when_malformed_iso() -> None:
    sr = {
        "first_marker_occurred_at": "2026-01-01T00:00:00Z",
        "last_marker_occurred_at": "not-a-timestamp",
    }
    assert self_refinement_marker_window_caption(sr) is None


def test_self_refinement_description_length_caption_none_for_non_mapping() -> None:
    assert self_refinement_description_length_caption(None) is None
    assert self_refinement_description_length_caption("x") is None
    assert self_refinement_description_length_caption([1, 2]) is None


def test_self_refinement_description_length_caption_none_when_description_missing() -> None:
    sr = {"version": 1, "marker_count": 2}
    assert self_refinement_description_length_caption(sr) is None


def test_self_refinement_description_length_caption_none_when_description_empty() -> None:
    sr = {"description": ""}
    assert self_refinement_description_length_caption(sr) is None


def test_self_refinement_description_length_caption_one_char() -> None:
    sr = {"description": "x"}
    assert self_refinement_description_length_caption(sr) == "Description length: 1 chars."


def test_self_refinement_description_length_caption_long_description() -> None:
    text = "a" * 42
    sr = {"description": text}
    assert self_refinement_description_length_caption(sr) == "Description length: 42 chars."


def test_self_refinement_description_length_caption_bool_char_len_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "console.self_refinement.timeline_metrics.self_refinement_timeline_operator_metrics",
        lambda _sr: {"present": True, "description_char_len": True},
    )
    assert self_refinement_description_length_caption({"description": "x"}) is None


def test_self_refinement_description_length_caption_negative_char_len_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "console.self_refinement.timeline_metrics.self_refinement_timeline_operator_metrics",
        lambda _sr: {"present": True, "description_char_len": -1},
    )
    assert self_refinement_description_length_caption({"description": "x"}) is None


def test_self_refinement_description_length_caption_non_int_char_len_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "console.self_refinement.timeline_metrics.self_refinement_timeline_operator_metrics",
        lambda _sr: {"present": True, "description_char_len": "12"},
    )
    assert self_refinement_description_length_caption({"description": "x"}) is None


def test_self_refinement_stage_name_caption_none_for_non_mapping() -> None:
    assert self_refinement_stage_name_caption(None) is None
    assert self_refinement_stage_name_caption("x") is None


def test_self_refinement_stage_name_caption_none_when_missing_or_blank() -> None:
    assert self_refinement_stage_name_caption({}) is None
    assert self_refinement_stage_name_caption({"stage_name": ""}) is None
    assert self_refinement_stage_name_caption({"stage_name": "   "}) is None
    assert self_refinement_stage_name_caption({"stage_name": 42}) is None


def test_self_refinement_stage_name_caption_emits() -> None:
    cap = self_refinement_stage_name_caption({"stage_name": "  self_refinement:policy  "})
    assert cap == "Self-refinement stage: self_refinement:policy."


def test_self_refinement_evaluation_caption() -> None:
    cap = self_refinement_evaluation_caption(
        {
            "evaluation_status": "ok",
            "promotion_ready": True,
            "evaluation_gaps": [],
        },
    )
    assert cap is not None
    assert "status='ok'" in cap
    assert "promotion_ready=True" in cap
    assert "gap_count=0" in cap
    assert self_refinement_evaluation_caption({"evaluation_status": ""}) is None


def test_self_refinement_iteration_caption() -> None:
    cap = self_refinement_iteration_caption(
        {"attempt": 2, "max_iterations": 3, "max_iterations_exceeded": False},
    )
    assert cap == "Self-refinement iteration: attempt 2 of 3."
    exceeded = self_refinement_iteration_caption(
        {"attempt": 4, "max_iterations": 3, "max_iterations_exceeded": True},
    )
    assert exceeded == "Self-refinement iteration: attempt 4 exceeded max 3."
    assert self_refinement_iteration_caption(None) is None


def test_self_refinement_auto_promote_caption() -> None:
    applied = self_refinement_auto_promote_caption({"auto_promote_applied": True})
    assert applied == "Self-refinement auto-promote: applied."
    skipped = self_refinement_auto_promote_caption(
        {"auto_promote_applied": False, "auto_promote_reason": "env_kill_switch"},
    )
    assert skipped == "Self-refinement auto-promote: not applied (env_kill_switch)."
    assert self_refinement_auto_promote_caption({}) is None


def test_self_refinement_summary_rows_include_v2_fields() -> None:
    sr = {
        "attempt": 2,
        "max_iterations": 3,
        "max_iterations_exceeded": False,
        "iteration_progress_ratio": 0.667,
        "should_continue": True,
        "auto_promote_applied": True,
    }
    labels = {r["field"] for r in self_refinement_summary_rows(sr)}
    assert "Max iterations" in labels
    assert "Iteration progress ratio" in labels
    assert "Should continue" in labels
    assert "Auto-promote applied" in labels


def test_self_refinement_prior_gate_verdict_caption() -> None:
    cap = self_refinement_prior_gate_verdict_caption({"prior_gate_verdict": "hold"})
    assert cap is not None
    assert "**HOLD**" in cap
    assert self_refinement_prior_gate_verdict_caption(None) is None
    labels = {r["field"] for r in self_refinement_summary_rows({"prior_gate_verdict": "pass"})}
    assert "Prior gate verdict" in labels


def test_self_refinement_phase_d_signal_caption_and_row() -> None:
    sr = {
        "phase_d_signal": {
            "signal": "phase_d_kickoff",
            "attempt": 2,
            "max_iterations": 3,
            "gate_decision": "hold",
        },
    }
    cap = self_refinement_phase_d_signal_caption(sr)
    assert cap == "Self-refinement Phase D (rules gate): phase_d_kickoff (attempt 2/3, gate=hold)."


def test_self_refinement_llm_critique_stage_caption() -> None:
    sr = {
        "llm_critique_stage": {
            "stage_name": "self_refinement.critique",
            "verdict": "PASS",
        },
    }
    cap = self_refinement_llm_critique_stage_caption(sr)
    assert cap is not None
    assert "verdict=PASS" in cap
    assert "self_refinement.critique" in cap


def test_self_refinement_phase_d_signal_caption_llm_branch() -> None:
    sr = {
        "phase_d_signal": {
            "signal": "phase_d_iteration",
            "attempt": 2,
            "max_iterations": 3,
            "gate_decision": "hold",
            "orchestration_branch": "rules_with_llm_critique",
            "llm_gate_decision": "proceed",
            "llm_critique_enabled": True,
            "llm_critique_attempted": True,
            "llm_critique_verdict": "PASS",
        },
    }
    cap = self_refinement_phase_d_signal_caption(sr)
    assert cap is not None
    assert "branch=rules_with_llm_critique" in cap
    assert "llm_gate=proceed" in cap
    assert "llm_critique_enabled=True" in cap
    assert "llm_critique_attempted=True" in cap
    assert "llm_critique_verdict=PASS" in cap
    labels = {r["field"] for r in self_refinement_summary_rows(sr)}
    assert "Phase D loop signal" in labels


def test_self_refinement_summary_rows_include_llm_critique_summary() -> None:
    sr = {"llm_critique_summary": "policy suggests follow-up"}
    labels = {r["field"] for r in self_refinement_summary_rows(sr)}
    assert "LLM critique summary" in labels


def test_self_refinement_summary_rows_include_ungated_depth_fields() -> None:
    sr = {"ungated_loop": True, "ungated_iteration_count": 2}
    labels = {r["field"] for r in self_refinement_summary_rows(sr)}
    assert "Ungated loop" in labels
    assert "Ungated iteration count" in labels


def test_self_refinement_ungated_loop_caption() -> None:
    cap = self_refinement_ungated_loop_caption(
        {
            "ungated_loop": True,
            "loop_signal_count": 2,
            "ungated_iteration_count": 1,
            "gate_decision": "proceed",
            "loops_remaining": 1,
            "iteration_progress_ratio": 0.333,
            "should_continue": True,
        },
    )
    assert cap is not None
    assert "ungated_loop=True" in cap
    assert "loop_signal_count=2" in cap
    assert "ungated_iteration_count=1" in cap
    assert "gate=proceed" in cap
    assert "loops_remaining=1" in cap
    assert "progress_ratio=0.333" in cap
    assert "should_continue=True" in cap
    assert self_refinement_ungated_loop_caption({"ungated_loop": "yes"}) is None


def test_self_refinement_marker_history_from_timeline_three_markers() -> None:
    hist = [
        {"event_id": "e1", "occurred_at": "t1", "version": "v1"},
        {"event_id": "e2", "occurred_at": "t2", "version": "v2"},
        {"event_id": "e3", "occurred_at": "t3", "version": "v3"},
    ]
    body = {"self_refinement_marker_history": hist}
    assert self_refinement_marker_history_from_timeline(body) == hist
    assert self_refinement_marker_history_from_timeline(None) == []


def test_self_refinement_marker_history_table_rows() -> None:
    rows = self_refinement_marker_history_table_rows(
        [{"occurred_at": "t1", "version": "v1", "event_id": "e1"}],
    )
    assert len(rows) == 1
    assert rows[0]["Version"] == "v1"
    assert rows[0]["Event id"] == "e1"


def test_self_refinement_marker_history_entry_count_caption() -> None:
    cap = self_refinement_marker_history_entry_count_caption([{}, {}, {}])
    assert cap is not None
    assert "3" in cap
    assert self_refinement_marker_history_entry_count_caption([]) is None


def test_self_refinement_marker_history_table_rows_csv_empty() -> None:
    assert self_refinement_marker_history_table_rows_csv([]) == ""


def test_self_refinement_marker_history_export_json_and_csv() -> None:
    hist = [{"occurred_at": "t1", "version": 2, "event_id": "e1"}]
    rows = self_refinement_marker_history_table_rows(hist)
    csv_body = self_refinement_marker_history_table_rows_csv(rows)
    assert csv_body.startswith("#,Occurred at,Version,")
    parsed = json.loads(self_refinement_marker_history_export_json(hist))
    assert len(parsed) == 1
    assert parsed[0]["event_id"] == "e1"


def test_self_refinement_marker_history_export_filename_slug() -> None:
    assert self_refinement_marker_history_export_filename_slug("x/y") == "x_y"


def test_self_refinement_marker_history_operator_metrics_empty() -> None:
    m = self_refinement_marker_history_operator_metrics([])
    assert m["entry_count"] == 0
    assert self_refinement_marker_history_operator_metrics_caption(m) is None
    assert self_refinement_marker_history_operator_metrics_table_rows(m)


def test_self_refinement_marker_history_operator_metrics_multi() -> None:
    hist = [
        {"occurred_at": "2026-05-12T18:00:00+00:00", "version": 1},
        {"occurred_at": "2026-05-12T18:00:30+00:00", "version": 2},
        {"occurred_at": "2026-05-12T18:00:30+00:00", "version": 2},
    ]
    m = self_refinement_marker_history_operator_metrics(hist)
    assert m["entry_count"] == 3
    assert m["distinct_version_count"] == 2
    assert m["marker_window_seconds"] == 30
    cap = self_refinement_marker_history_operator_metrics_caption(m)
    assert cap is not None
    assert "3" in cap


def test_self_refinement_marker_history_operator_metrics_export() -> None:
    hist = [{"occurred_at": "2026-05-12T18:00:00+00:00", "version": 1}]
    m = self_refinement_marker_history_operator_metrics(hist)
    parsed = json.loads(self_refinement_marker_history_operator_metrics_export_json(m))
    assert parsed["entry_count"] == 1
    assert json.loads(self_refinement_marker_history_operator_metrics_export_json(None)) == {}
    rows = self_refinement_marker_history_operator_metrics_table_rows(m)
    csv_text = self_refinement_marker_history_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert self_refinement_marker_history_operator_metrics_table_rows_csv([]) == ""
