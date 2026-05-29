"""Console integrator gate display helper (follow-on 31 §14 #13)."""

from __future__ import annotations

import json

import pytest

from hermes_console.integrator_gate_display import (
    integrator_gate_compatibility_ranking_caption,
    integrator_gate_compatibility_ranking_table_rows,
    integrator_gate_delta_bundle_changed_caption,
    integrator_gate_delta_export_filename_slug,
    integrator_gate_delta_export_json,
    integrator_gate_delta_from_timeline,
    integrator_gate_delta_operator_metrics,
    integrator_gate_delta_operator_metrics_caption,
    integrator_gate_delta_operator_metrics_export_filename_slug,
    integrator_gate_delta_operator_metrics_export_json,
    integrator_gate_delta_operator_metrics_table_rows_csv,
    integrator_gate_delta_operator_table_rows,
    integrator_gate_delta_summary_rows,
    integrator_gate_delta_summary_rows_csv,
    integrator_gate_delta_transition_caption,
    integrator_gate_delta_verdict_changed_caption,
    integrator_gate_from_timeline,
    integrator_gate_history_distinct_bundles_caption,
    integrator_gate_history_entry_count_caption,
    integrator_gate_history_export_filename_slug,
    integrator_gate_history_export_json,
    integrator_gate_history_failure_reason_caption,
    integrator_gate_history_from_timeline,
    integrator_gate_history_latest_margin_caption,
    integrator_gate_history_metrics_table_rows,
    integrator_gate_history_operator_metrics,
    integrator_gate_history_operator_metrics_caption,
    integrator_gate_history_operator_metrics_export_filename_slug,
    integrator_gate_history_operator_metrics_export_json,
    integrator_gate_history_operator_metrics_table_rows_csv,
    integrator_gate_history_score_range_caption,
    integrator_gate_history_table_rows,
    integrator_gate_history_table_rows_csv,
    integrator_gate_history_verdict_tally_caption,
    integrator_gate_latest_bundle_id_caption,
    integrator_gate_latest_export_filename_slug,
    integrator_gate_latest_export_json,
    integrator_gate_latest_metrics_table_rows,
    integrator_gate_latest_operator_metrics,
    integrator_gate_latest_operator_metrics_caption,
    integrator_gate_latest_operator_metrics_export_filename_slug,
    integrator_gate_latest_operator_metrics_export_json,
    integrator_gate_latest_operator_metrics_table_rows_csv,
    integrator_gate_latest_score_margin_caption,
    integrator_gate_latest_summary_rows_csv,
    integrator_gate_latest_tag_overlap_caption,
    integrator_gate_summary_rows,
)


def test_integrator_gate_from_timeline_none_when_missing() -> None:
    assert integrator_gate_from_timeline(None) is None
    assert integrator_gate_from_timeline({}) is None
    assert integrator_gate_from_timeline({"integrator_gate": None}) is None
    assert integrator_gate_from_timeline({"integrator_gate": "x"}) is None


def test_integrator_gate_from_timeline_returns_dict() -> None:
    body = {"events": [], "integrator_gate": {"verdict": "PASS", "bundle_id": "b1"}}
    ig = integrator_gate_from_timeline(body)
    assert ig == {"verdict": "PASS", "bundle_id": "b1"}


def test_integrator_gate_compatibility_ranking_caption_and_rows() -> None:
    ig = {
        "bundle_id": "auth-rbac-starter",
        "selected_bundle_rank": 1,
        "bundle_compatibility_ranking_count": 2,
        "bundle_compatibility_ranking": [
            {"bundle_id": "top", "score": 1.0, "passes_gate": True, "title": "Top"},
            {"bundle_id": "auth-rbac-starter", "score": 0.9, "passes_gate": True},
        ],
    }
    cap = integrator_gate_compatibility_ranking_caption(ig)
    assert cap is not None
    assert "rank **1**" in cap
    assert "auth-rbac-starter" in cap
    rows = integrator_gate_compatibility_ranking_table_rows(ig)
    assert len(rows) == 2
    assert rows[0]["bundle_id"] == "top"
    assert integrator_gate_compatibility_ranking_caption(None) is None
    assert integrator_gate_compatibility_ranking_table_rows(None) == []


def test_integrator_gate_summary_rows_empty_for_none() -> None:
    assert integrator_gate_summary_rows(None) == []


def test_integrator_gate_summary_rows_ordered_fields() -> None:
    ig = {
        "verdict": "FAIL",
        "bundle_id": "auth-rbac-starter",
        "integrator_score": 0.42,
        "integrator_project_tags": ["a", "b"],
        "event_id": "e1",
    }
    rows = integrator_gate_summary_rows(ig)
    labels = [r["field"] for r in rows]
    assert labels[0] == "Verdict"
    assert labels.index("Bundle id") < labels.index("Event id")
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Verdict"] == "FAIL"
    assert by_field["Bundle id"] == "auth-rbac-starter"
    assert by_field["Integrator score"] == "0.42"
    assert '"a"' in by_field["Project tags"]


def test_integrator_gate_latest_export_helpers() -> None:
    ig = {
        "verdict": "PASS",
        "bundle_id": "b99",
        "integrator_score": 0.9,
    }
    rows = integrator_gate_summary_rows(ig)
    csv_text = integrator_gate_latest_summary_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert "PASS" in csv_text
    assert json.loads(integrator_gate_latest_export_json(ig))["bundle_id"] == "b99"
    assert integrator_gate_latest_summary_rows_csv([]) == ""
    assert json.loads(integrator_gate_latest_export_json(None)) == {}
    assert integrator_gate_latest_export_filename_slug("Ig@1") == "ig_1"


def test_integrator_gate_history_from_timeline_empty() -> None:
    assert integrator_gate_history_from_timeline(None) == []
    assert integrator_gate_history_from_timeline({}) == []
    assert integrator_gate_history_from_timeline({"integrator_gate_history": None}) == []


def test_integrator_gate_history_table_rows() -> None:
    hist = [
        {
            "occurred_at": "t1",
            "verdict": "PASS",
            "integrator_score": 0.8,
            "min_score_to_pass": 0.5,
            "bundle_id": "b1",
            "stage_name": "s1",
            "event_id": "e1",
        },
    ]
    rows = integrator_gate_history_table_rows(hist)
    assert len(rows) == 1
    assert rows[0]["#"] == "1"
    assert rows[0]["Verdict"] == "PASS"
    assert rows[0]["Bundle"] == "b1"
    assert rows[0]["Failure reason"] == "—"
    assert rows[0]["Bundle title"] == "—"
    assert rows[0]["Matched tags"] == "—"


def test_integrator_gate_history_table_rows_csv_empty() -> None:
    assert integrator_gate_history_table_rows_csv([]) == ""


def test_integrator_gate_history_table_rows_csv_matches_display_rows() -> None:
    hist = [
        {
            "occurred_at": "t1",
            "verdict": "PASS",
            "integrator_score": 0.8,
            "bundle_id": "b1",
        },
        {
            "occurred_at": "t2",
            "verdict": "FAIL",
            "failure_reason_code": "low_score",
            "bundle_id": "b2",
        },
    ]
    rows = integrator_gate_history_table_rows(hist)
    csv_body = integrator_gate_history_table_rows_csv(rows)
    assert csv_body.startswith("#,Occurred at,Verdict,")
    assert csv_body.count("\n") == 3  # header + 2 rows
    assert "PASS" in csv_body
    assert "FAIL" in csv_body


def test_integrator_gate_history_export_json_empty() -> None:
    assert integrator_gate_history_export_json([]) == "[]"


def test_integrator_gate_history_export_json_round_trip() -> None:
    hist = [{"verdict": "PASS", "bundle_id": "b1"}]
    parsed = json.loads(integrator_gate_history_export_json(hist))
    assert len(parsed) == 1
    assert parsed[0]["bundle_id"] == "b1"


def test_integrator_gate_history_export_filename_slug() -> None:
    assert integrator_gate_history_export_filename_slug(
        "00000000-0000-4000-8000-000000000001",
    ) == "00000000-0000-4000-8000-000000000001"
    assert integrator_gate_history_export_filename_slug("bad/id!") == "bad_id"
    assert integrator_gate_history_export_filename_slug("   ") == "run"


def test_integrator_gate_history_table_rows_failure_and_tags() -> None:
    hist = [
        {
            "verdict": "FAIL",
            "failure_reason_code": "score_below_min",
            "bundle_title": "Auth starter",
            "integrator_matched_tags": ["zeta", "alpha", "beta", "gamma"],
        },
    ]
    rows = integrator_gate_history_table_rows(hist)
    assert rows[0]["Failure reason"] == "score_below_min"
    assert rows[0]["Bundle title"] == "Auth starter"
    assert rows[0]["Matched tags"] == "alpha, beta, gamma, +1 more"


def test_integrator_gate_history_failure_reason_caption() -> None:
    assert integrator_gate_history_failure_reason_caption([]) is None
    assert integrator_gate_history_failure_reason_caption(None) is None
    all_pass = [{"verdict": "PASS"}, {"verdict": "PASS"}]
    assert integrator_gate_history_failure_reason_caption(all_pass) is None
    hist = [
        {"verdict": "PASS", "failure_reason_code": ""},
        {"verdict": "FAIL", "failure_reason_code": "tag_mismatch"},
    ]
    cap = integrator_gate_history_failure_reason_caption(hist)
    assert cap == "Latest gate failure reason: tag_mismatch (verdict FAIL)."


def test_integrator_gate_history_distinct_bundles_caption() -> None:
    hist = [
        {"verdict": "PASS", "bundle_id": "a"},
        {"verdict": "FAIL", "bundle_id": "b"},
        {"verdict": "PASS", "bundle_id": "a"},
    ]
    metrics = integrator_gate_history_operator_metrics(hist)
    cap = integrator_gate_history_distinct_bundles_caption(metrics)
    assert cap is not None
    assert "**2**" in cap
    assert integrator_gate_history_distinct_bundles_caption(None) is None
    assert integrator_gate_history_distinct_bundles_caption({}) is None
    assert integrator_gate_history_distinct_bundles_caption(
        {"gate_event_count": 0},
    ) is None


def test_integrator_gate_history_score_range_caption() -> None:
    hist = [
        {"verdict": "PASS", "integrator_score": 0.42},
        {"verdict": "FAIL", "integrator_score": 0.91},
    ]
    metrics = integrator_gate_history_operator_metrics(hist)
    cap = integrator_gate_history_score_range_caption(metrics)
    assert cap is not None
    assert "**0.42**" in cap
    assert "**0.91**" in cap
    assert "numeric rows only" in cap
    assert integrator_gate_history_score_range_caption(None) is None
    assert integrator_gate_history_score_range_caption({}) is None
    assert integrator_gate_history_score_range_caption(
        {"gate_event_count": 0},
    ) is None
    assert integrator_gate_history_score_range_caption(
        {"gate_event_count": 1},
    ) is None


def test_integrator_gate_history_latest_margin_caption() -> None:
    hist = [
        {"verdict": "PASS", "integrator_score": 0.9, "min_score_to_pass": 0.5},
        {"verdict": "FAIL", "integrator_score": 0.3, "min_score_to_pass": 0.5},
    ]
    metrics = integrator_gate_history_operator_metrics(hist)
    cap = integrator_gate_history_latest_margin_caption(metrics)
    assert cap is not None
    assert "**-0.2**" in cap
    assert "latest row" in cap
    assert integrator_gate_history_latest_margin_caption(None) is None
    assert integrator_gate_history_latest_margin_caption(
        {"gate_event_count": 0},
    ) is None
    assert integrator_gate_history_latest_margin_caption(
        {"gate_event_count": 1},
    ) is None


def test_integrator_gate_history_operator_metrics_caption() -> None:
    m = integrator_gate_history_operator_metrics(
        [
            {
                "verdict": "FAIL",
                "integrator_score": 0.4,
                "min_score_to_pass": 0.5,
                "bundle_id": "b-a",
            },
            {
                "verdict": "pass",
                "integrator_score": 0.9,
                "min_score_to_pass": 0.5,
                "bundle_id": "b-b",
            },
        ],
    )
    cap = integrator_gate_history_operator_metrics_caption(m)
    assert cap is not None
    assert "**2**" in cap
    assert "FAIL=1" in cap
    assert "bundle" in cap.lower()
    assert integrator_gate_history_operator_metrics_caption(
        {"gate_event_count": 0},
    ) is None
    assert integrator_gate_history_operator_metrics_caption(None) is None


def test_integrator_gate_history_verdict_tally_caption() -> None:
    hist = [
        {"verdict": "PASS", "integrator_score": 0.9},
        {"verdict": "FAIL", "integrator_score": 0.3},
        {"verdict": "PASS", "integrator_score": 0.8},
    ]
    metrics = integrator_gate_history_operator_metrics(hist)
    cap = integrator_gate_history_verdict_tally_caption(metrics)
    assert cap is not None
    assert "FAIL=1" in cap
    assert "PASS=2" in cap
    assert integrator_gate_history_verdict_tally_caption(None) is None
    assert integrator_gate_history_verdict_tally_caption({}) is None
    assert integrator_gate_history_verdict_tally_caption({"gate_event_count": 0}) is None


def test_integrator_gate_history_entry_count_caption() -> None:
    cap = integrator_gate_history_entry_count_caption([{}, {}])
    assert cap is not None
    assert "**2**" in cap
    assert "decisions" in cap
    cap1 = integrator_gate_history_entry_count_caption([{}])
    assert cap1 is not None
    assert "decision" in cap1
    assert integrator_gate_history_entry_count_caption([]) is None
    assert integrator_gate_history_entry_count_caption(None) is None


def test_integrator_gate_delta_transition_caption() -> None:
    cap = integrator_gate_delta_transition_caption(
        {
            "integrator_score_delta": 0.1,
            "previous_verdict": "FAIL",
            "current_verdict": "PASS",
            "bundle_id_changed": True,
        },
    )
    assert cap is not None
    assert "verdict" in cap
    assert "score up" in cap
    assert "bundle id changed" in cap
    assert integrator_gate_delta_transition_caption(None) is None
    assert integrator_gate_delta_transition_caption({}) is None


def test_integrator_gate_delta_verdict_changed_caption() -> None:
    cap_t = integrator_gate_delta_verdict_changed_caption({"verdict_changed": True})
    assert cap_t is not None
    assert "**true**" in cap_t
    cap_f = integrator_gate_delta_verdict_changed_caption({"verdict_changed": False})
    assert cap_f is not None
    assert "**false**" in cap_f
    assert integrator_gate_delta_verdict_changed_caption(None) is None
    assert integrator_gate_delta_verdict_changed_caption({}) is None
    assert integrator_gate_delta_verdict_changed_caption(
        {"verdict_changed": 1},
    ) is None


def test_integrator_gate_delta_bundle_changed_caption() -> None:
    cap_t = integrator_gate_delta_bundle_changed_caption({"bundle_id_changed": True})
    assert cap_t is not None
    assert "**true**" in cap_t
    cap_f = integrator_gate_delta_bundle_changed_caption({"bundle_id_changed": False})
    assert cap_f is not None
    assert "**false**" in cap_f
    assert integrator_gate_delta_bundle_changed_caption(None) is None
    assert integrator_gate_delta_bundle_changed_caption(
        {"bundle_id_changed": 1},
    ) is None


def test_integrator_gate_latest_bundle_id_caption() -> None:
    cap = integrator_gate_latest_bundle_id_caption({"bundle_id": "auth-rbac"})
    assert cap is not None
    assert "auth-rbac" in cap
    assert integrator_gate_latest_bundle_id_caption(None) is None
    assert integrator_gate_latest_bundle_id_caption({"bundle_id": ""}) is None
    assert integrator_gate_latest_bundle_id_caption({"bundle_id": "   "}) is None


def test_integrator_gate_history_operator_metrics_empty() -> None:
    m = integrator_gate_history_operator_metrics([])
    assert m == {"gate_event_count": 0}
    assert integrator_gate_history_metrics_table_rows(m) == [
        {"field": "Gate events in view", "value": "0"},
    ]


def test_integrator_gate_history_operator_metrics_and_table_rows() -> None:
    hist = [
        {
            "occurred_at": "t1",
            "verdict": "FAIL",
            "integrator_score": 0.4,
            "min_score_to_pass": 0.5,
            "bundle_id": "b-a",
            "stage_name": "s1",
            "event_id": "e1",
        },
        {
            "occurred_at": "t2",
            "verdict": "pass",
            "integrator_score": 0.9,
            "min_score_to_pass": 0.5,
            "bundle_id": "b-b",
            "stage_name": "s2",
            "event_id": "e2",
        },
    ]
    m = integrator_gate_history_operator_metrics(hist)
    assert m["gate_event_count"] == 2
    assert m["verdict_counts"] == {"FAIL": 1, "PASS": 1}
    assert m["distinct_bundle_id_count"] == 2
    assert m["integrator_score_min"] == 0.4
    assert m["integrator_score_max"] == 0.9
    assert m["latest_score_minus_min_pass"] == pytest.approx(0.4)
    rows = integrator_gate_history_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Gate events in view"] == "2"
    assert "FAIL: 1" in by["Verdict tally"]
    assert "PASS: 1" in by["Verdict tally"]
    assert "b-a, b-b" in by["Bundle id list"]


def test_integrator_gate_history_operator_metrics_export_json_and_csv() -> None:
    hist = [
        {
            "occurred_at": "t1",
            "verdict": "FAIL",
            "integrator_score": 0.4,
            "min_score_to_pass": 0.5,
            "bundle_id": "b-a",
            "stage_name": "s1",
            "event_id": "e1",
        },
        {
            "occurred_at": "t2",
            "verdict": "pass",
            "integrator_score": 0.9,
            "min_score_to_pass": 0.5,
            "bundle_id": "b-b",
            "stage_name": "s2",
            "event_id": "e2",
        },
    ]
    metrics = integrator_gate_history_operator_metrics(hist)
    rows = integrator_gate_history_metrics_table_rows(metrics)
    parsed = json.loads(integrator_gate_history_operator_metrics_export_json(metrics))
    assert parsed["gate_event_count"] == 2
    assert parsed["verdict_counts"] == {"FAIL": 1, "PASS": 1}
    csv_text = integrator_gate_history_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert (
        integrator_gate_history_operator_metrics_export_filename_slug("run-abc")
        == integrator_gate_history_export_filename_slug("run-abc")
    )


def test_integrator_gate_history_operator_metrics_export_empty() -> None:
    metrics = integrator_gate_history_operator_metrics([])
    rows = integrator_gate_history_metrics_table_rows(metrics)
    parsed = json.loads(integrator_gate_history_operator_metrics_export_json(metrics))
    assert parsed == {"gate_event_count": 0}
    csv_text = integrator_gate_history_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert integrator_gate_history_operator_metrics_export_json(None) == "{}"
    assert integrator_gate_history_operator_metrics_table_rows_csv([]) == ""


def test_integrator_gate_latest_operator_metrics_compatibility_ranking() -> None:
    ig = {
        "integrator_score": 0.9,
        "min_score_to_pass": 0.5,
        "bundle_compatibility_ranking": [{"bundle_id": "a", "score": 0.9}],
        "bundle_compatibility_ranking_count": 3,
        "selected_bundle_rank": 1,
    }
    m = integrator_gate_latest_operator_metrics(ig)
    assert m["bundle_compatibility_ranking_count"] == 3
    assert m["selected_bundle_rank"] == 1
    cap = integrator_gate_latest_operator_metrics_caption(m)
    assert cap is not None
    assert "ranked candidate" in cap
    assert "selected rank **1**" in cap
    rows = integrator_gate_latest_metrics_table_rows(m)
    assert any(r["field"] == "Selected bundle rank" for r in rows)


def test_integrator_gate_latest_operator_metrics_caption() -> None:
    m = integrator_gate_latest_operator_metrics(
        {
            "integrator_score": 0.8,
            "min_score_to_pass": 0.5,
            "integrator_project_tags": ["a", "b"],
            "integrator_matched_tags": ["a"],
            "integrator_bundle_tags": ["a"],
        },
    )
    cap = integrator_gate_latest_operator_metrics_caption(m)
    assert cap is not None
    assert "tag overlap" in cap.lower()
    assert "meets bar" in cap
    assert integrator_gate_latest_operator_metrics_caption({"present": False}) is None
    assert integrator_gate_latest_operator_metrics_caption(None) is None


def test_integrator_gate_latest_score_margin_caption_meets_bar() -> None:
    cap = integrator_gate_latest_score_margin_caption(
        {
            "integrator_score": 0.8,
            "min_score_to_pass": 0.5,
            "failure_reason_code": "TAG_MISMATCH",
        },
    )
    assert cap is not None
    assert "meets numeric bar" in cap
    assert "TAG_MISMATCH" in cap


def test_integrator_gate_latest_score_margin_caption_none_without_numeric_fields() -> None:
    assert integrator_gate_latest_score_margin_caption(None) is None
    assert integrator_gate_latest_score_margin_caption({"verdict": "PASS"}) is None


def test_integrator_gate_latest_tag_overlap_caption() -> None:
    cap = integrator_gate_latest_tag_overlap_caption(
        {
            "integrator_project_tags": ["auth", "api"],
            "integrator_matched_tags": ["auth"],
        },
    )
    assert cap is not None
    assert "**1** matched" in cap
    assert "**2** project" in cap
    cap_zero = integrator_gate_latest_tag_overlap_caption(
        {
            "integrator_project_tags": ["a"],
            "integrator_matched_tags": [],
        },
    )
    assert cap_zero is not None
    assert "**0** matched" in cap_zero
    assert integrator_gate_latest_tag_overlap_caption(None) is None
    assert integrator_gate_latest_tag_overlap_caption({}) is None


def test_integrator_gate_latest_operator_metrics_absent() -> None:
    m = integrator_gate_latest_operator_metrics(None)
    assert m == {"present": False}
    assert integrator_gate_latest_metrics_table_rows(m) == []


def test_integrator_gate_latest_operator_metrics_tag_overlap_and_numeric() -> None:
    ig = {
        "verdict": "PASS",
        "integrator_project_tags": ["auth", "api"],
        "integrator_matched_tags": ["auth", "x"],
        "integrator_bundle_tags": ["b1"],
        "integrator_score": 0.7,
        "min_score_to_pass": 0.5,
        "failure_reason_code": "TAG_MISMATCH",
    }
    m = integrator_gate_latest_operator_metrics(ig)
    assert m["present"] is True
    assert m["tag_overlap_count"] == 1
    assert m["tag_overlap"] == ["auth"]
    assert m["latest_score_minus_min_pass"] == pytest.approx(0.2)
    assert m["score_meets_min_numeric"] is True
    assert m["failure_reason_code"] == "TAG_MISMATCH"
    assert m["integrator_score"] == pytest.approx(0.7)
    assert m["min_score_to_pass"] == pytest.approx(0.5)
    cap = integrator_gate_latest_operator_metrics_caption(m)
    assert cap is not None
    assert "integrator score" in cap
    assert "min pass" in cap
    rows = integrator_gate_latest_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Tag overlap (intersection)"] == "1"
    assert "auth" in by["Overlap tag list"]
    assert "Integrator score" in by


def test_integrator_gate_latest_operator_metrics_export_json_and_csv() -> None:
    ig = {
        "verdict": "PASS",
        "integrator_project_tags": ["auth", "api"],
        "integrator_matched_tags": ["auth", "x"],
        "integrator_bundle_tags": ["b1"],
        "integrator_score": 0.7,
        "min_score_to_pass": 0.5,
        "failure_reason_code": "TAG_MISMATCH",
    }
    metrics = integrator_gate_latest_operator_metrics(ig)
    rows = integrator_gate_latest_metrics_table_rows(metrics)
    parsed = json.loads(integrator_gate_latest_operator_metrics_export_json(metrics))
    assert parsed["present"] is True
    assert parsed["tag_overlap_count"] == 1
    assert parsed["latest_score_minus_min_pass"] == pytest.approx(0.2)
    csv_text = integrator_gate_latest_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert (
        integrator_gate_latest_operator_metrics_export_filename_slug("run-abc")
        == integrator_gate_latest_export_filename_slug("run-abc")
    )


def test_integrator_gate_latest_operator_metrics_export_absent() -> None:
    metrics = integrator_gate_latest_operator_metrics(None)
    rows = integrator_gate_latest_metrics_table_rows(metrics)
    assert json.loads(integrator_gate_latest_operator_metrics_export_json(metrics)) == {}
    assert integrator_gate_latest_operator_metrics_export_json(None) == "{}"
    assert integrator_gate_latest_operator_metrics_table_rows_csv(rows) == ""
    assert integrator_gate_latest_operator_metrics_table_rows_csv([]) == ""


def test_integrator_gate_delta_operator_metrics_direction() -> None:
    d = {
        "integrator_score_delta": 0.05,
        "verdict_changed": True,
        "bundle_id_changed": False,
        "previous_verdict": "FAIL",
        "current_verdict": "PASS",
    }
    m = integrator_gate_delta_operator_metrics(d)
    assert m["present"] is True
    assert m["score_delta_direction"] == "up"
    assert m["verdict_changed"] is True
    assert m["bundle_id_changed"] is False
    rows = integrator_gate_delta_operator_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Score delta direction"] == "up"
    assert "FAIL" in by["Verdict transition"]


def test_integrator_gate_delta_operator_metrics_export_json_and_csv() -> None:
    d = {
        "integrator_score_delta": 0.05,
        "verdict_changed": True,
        "bundle_id_changed": False,
        "previous_verdict": "FAIL",
        "current_verdict": "PASS",
    }
    metrics = integrator_gate_delta_operator_metrics(d)
    rows = integrator_gate_delta_operator_table_rows(metrics)
    parsed = json.loads(integrator_gate_delta_operator_metrics_export_json(metrics))
    assert parsed["present"] is True
    assert parsed["score_delta_direction"] == "up"
    assert "FAIL" in str(parsed["verdict_transition"])
    csv_text = integrator_gate_delta_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert (
        integrator_gate_delta_operator_metrics_export_filename_slug("run-abc")
        == integrator_gate_delta_export_filename_slug("run-abc")
    )


def test_integrator_gate_delta_operator_metrics_export_absent() -> None:
    metrics = integrator_gate_delta_operator_metrics(None)
    rows = integrator_gate_delta_operator_table_rows(metrics)
    assert json.loads(integrator_gate_delta_operator_metrics_export_json(metrics)) == {}
    assert integrator_gate_delta_operator_metrics_export_json(None) == "{}"
    assert integrator_gate_delta_operator_metrics_table_rows_csv(rows) == ""
    assert integrator_gate_delta_operator_metrics_table_rows_csv([]) == ""


def test_integrator_gate_delta_operator_metrics_flat_score() -> None:
    m = integrator_gate_delta_operator_metrics({"integrator_score_delta": 0.0})
    assert m["score_delta_direction"] == "flat"


def test_integrator_gate_delta_operator_metrics_caption() -> None:
    m = integrator_gate_delta_operator_metrics(
        {
            "integrator_score_delta": -0.05,
            "previous_verdict": "PASS",
            "current_verdict": "FAIL",
            "bundle_id_changed": False,
        },
    )
    cap = integrator_gate_delta_operator_metrics_caption(m)
    assert cap is not None
    assert "score down" in cap
    assert "verdict" in cap
    assert integrator_gate_delta_operator_metrics_caption({"present": False}) is None
    flat = integrator_gate_delta_operator_metrics({"integrator_score_delta": 0.0})
    flat_cap = integrator_gate_delta_operator_metrics_caption(flat)
    assert flat_cap is not None
    assert "score flat" in flat_cap


def test_integrator_gate_delta_from_timeline() -> None:
    body = {
        "integrator_gate_delta": {
            "integrator_score_delta": 0.1,
            "verdict_changed": False,
            "previous_event_id": "a",
            "current_event_id": "b",
        },
    }
    d = integrator_gate_delta_from_timeline(body)
    assert d is not None
    assert d["integrator_score_delta"] == 0.1


def test_integrator_gate_delta_summary_rows() -> None:
    rows = integrator_gate_delta_summary_rows(
        {"integrator_score_delta": 0.2, "verdict_changed": True},
    )
    by = {r["field"]: r["value"] for r in rows}
    assert by["Score delta (current − prior)"] == "0.2"
    assert by["Verdict changed"] == "True"


def test_integrator_gate_delta_export_helpers() -> None:
    delta = {"integrator_score_delta": -0.5, "verdict_changed": True}
    rows = integrator_gate_delta_summary_rows(delta)
    csv_text = integrator_gate_delta_summary_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert "-0.5" in csv_text
    assert json.loads(integrator_gate_delta_export_json(delta))["verdict_changed"] is True
    assert integrator_gate_delta_summary_rows_csv([]) == ""
    assert json.loads(integrator_gate_delta_export_json(None)) == {}
    assert integrator_gate_delta_export_filename_slug("A@b") == "a_b"
