"""Unit tests for critic matrix display helpers (§14 #11)."""

from __future__ import annotations

import json

from nimbusware_console.critic_matrix_display import (
    critic_matrix_export_filename_slug,
    critic_matrix_export_json,
    critic_matrix_live_display_caption,
    critic_matrix_live_summary_caption,
    critic_matrix_live_table_rows,
    critic_matrix_operator_metrics,
    critic_matrix_operator_metrics_caption,
    critic_matrix_operator_metrics_export_filename_slug,
    critic_matrix_operator_metrics_export_json,
    critic_matrix_operator_metrics_table_rows,
    critic_matrix_operator_metrics_table_rows_csv,
    critic_matrix_rows_from_events,
    critic_matrix_table_rows_csv,
)


def _critic_event(
    *,
    critic_role: str = "security_critic",
    verdict: str = "PASS",
    severity: str = "LOW",
    owner_role: str = "critic:security",
    event_id: str = "e1",
    occurred_at: str = "2026-01-01T00:00:00Z",
) -> dict:
    return {
        "event_type": "critic.verdict.emitted",
        "event_id": event_id,
        "occurred_at": occurred_at,
        "payload": {
            "critic_role": critic_role,
            "verdict": verdict,
            "severity": severity,
            "owner_role": owner_role,
        },
    }


def test_critic_matrix_rows_from_events_empty() -> None:
    assert critic_matrix_rows_from_events([]) == []
    assert critic_matrix_rows_from_events(None) == []  # type: ignore[arg-type]
    assert critic_matrix_rows_from_events([1, {"event_type": "run.started"}]) == []


def test_critic_matrix_rows_from_events_extracts() -> None:
    events = [
        _critic_event(verdict="PASS", event_id="e1"),
        _critic_event(verdict="FAIL", event_id="e2", critic_role="domain_critic"),
        "skip",
    ]
    rows = critic_matrix_rows_from_events(events)
    assert len(rows) == 2
    assert rows[0]["verdict"] == "PASS"
    assert rows[1]["critic_role"] == "domain_critic"
    assert rows[1]["event_id"] == "e2"


def test_critic_matrix_operator_metrics_and_caption() -> None:
    rows = critic_matrix_rows_from_events(
        [
            _critic_event(verdict="PASS"),
            _critic_event(verdict="FAIL"),
            _critic_event(verdict="ADVISORY"),
        ],
    )
    m = critic_matrix_operator_metrics(rows)
    assert m["verdict_count"] == 3
    assert m["fail_count"] == 1
    assert m["pass_count"] == 1
    assert m["other_verdict_count"] == 1
    cap = critic_matrix_operator_metrics_caption(m)
    assert cap is not None
    assert "FAIL" in cap
    assert critic_matrix_operator_metrics_caption({"verdict_count": 0}) is None


def test_critic_matrix_export_json_and_csv() -> None:
    rows = critic_matrix_rows_from_events([_critic_event()])
    parsed = json.loads(critic_matrix_export_json(rows))
    assert len(parsed) == 1
    assert parsed[0]["verdict"] == "PASS"
    csv_text = critic_matrix_table_rows_csv(rows)
    assert "critic_role,verdict" in csv_text
    assert "PASS" in csv_text
    assert critic_matrix_table_rows_csv([]) == ""


def test_critic_matrix_export_filename_slug() -> None:
    rid = "00000000-0000-4000-8000-000000000001"
    assert critic_matrix_export_filename_slug(rid) == rid
    assert critic_matrix_export_filename_slug("R@un!") == "r_un"


def test_critic_matrix_operator_metrics_table_rows() -> None:
    m = critic_matrix_operator_metrics(
        critic_matrix_rows_from_events([_critic_event(verdict="FAIL")]),
    )
    rows = critic_matrix_operator_metrics_table_rows(m)
    assert any(r["field"] == "FAIL" for r in rows)


def test_critic_matrix_operator_metrics_export_json() -> None:
    assert json.loads(critic_matrix_operator_metrics_export_json(None)) == {}
    rows = critic_matrix_rows_from_events([_critic_event(verdict="FAIL")])
    m = critic_matrix_operator_metrics(rows)
    parsed = json.loads(critic_matrix_operator_metrics_export_json(m))
    assert parsed["fail_count"] == 1


def test_critic_matrix_operator_metrics_table_rows_csv() -> None:
    rows = critic_matrix_rows_from_events([_critic_event(verdict="FAIL")])
    m = critic_matrix_operator_metrics(rows)
    metric_rows = critic_matrix_operator_metrics_table_rows(m)
    csv_text = critic_matrix_operator_metrics_table_rows_csv(metric_rows)
    assert csv_text.startswith("field,value")
    assert "FAIL" in csv_text
    assert critic_matrix_operator_metrics_table_rows_csv([]) == ""


def test_critic_matrix_operator_metrics_export_filename_slug() -> None:
    rid = "00000000-0000-4000-8000-000000000001"
    assert critic_matrix_operator_metrics_export_filename_slug(rid) == rid
    assert critic_matrix_operator_metrics_export_filename_slug("R@un!") == "r_un"


def test_critic_matrix_live_helpers_distinct_from_extracted() -> None:
    cap = critic_matrix_live_display_caption()
    assert "Live (orchestration)" in cap
    assert "Extracted" in cap
    rows = [
        {
            "stage_name": "implementation.critique",
            "verdict": "PASS",
            "status": "decided",
            "parallel_group": "writers",
            "stage_graph_order_index": 3,
        },
    ]
    table = critic_matrix_live_table_rows(rows)
    assert table[0]["stage_name"] == "implementation.critique"
    summary_cap = critic_matrix_live_summary_caption(
        {"row_count": 1, "pass_count": 1, "fail_count": 0, "pending_count": 0},
    )
    assert summary_cap is not None
    assert "pending" in summary_cap.lower()
    extracted = critic_matrix_rows_from_events([])
    assert extracted == []
