from __future__ import annotations

import json

from nimbusware_console.findings_display import (
    findings_empty_caption,
    findings_export_filename_slug,
    findings_export_json,
    findings_list_from_response,
    findings_operator_metrics,
    findings_operator_metrics_caption,
    findings_operator_metrics_export_filename_slug,
    findings_operator_metrics_export_json,
    findings_operator_metrics_table_rows,
    findings_operator_metrics_table_rows_csv,
    findings_table_rows,
    findings_table_rows_csv,
)


def _finding(
    *,
    severity: str = "HIGH",
    category: str = "security",
    finding_id: str = "f1",
    event_id: str = "e1",
    occurred_at: str = "2026-01-01T00:00:00Z",
) -> dict:
    return {
        "event_type": "finding.created",
        "event_id": event_id,
        "occurred_at": occurred_at,
        "payload": {
            "finding_id": finding_id,
            "category": category,
            "owner_role": "critic:security",
            "severity": severity,
            "source_artifact": "scan.log",
        },
    }


def test_findings_list_from_response_empty() -> None:
    assert findings_list_from_response(None) == []
    assert findings_list_from_response({}) == []
    assert findings_list_from_response({"findings": "x"}) == []
    assert findings_list_from_response({"findings": [1, {}]}) == [{}]


def test_findings_operator_metrics_empty() -> None:
    m = findings_operator_metrics([])
    assert m["finding_count"] == 0
    assert m["distinct_categories"] == 0
    assert findings_operator_metrics_caption(m) is None


def test_findings_operator_metrics_mixed_severities() -> None:
    findings = [
        _finding(severity="BLOCKER", category="a", finding_id="f1", event_id="e1"),
        _finding(severity="HIGH", category="b", finding_id="f2", event_id="e2"),
        _finding(severity="LOW", category="a", finding_id="f3", event_id="e3"),
        _finding(severity="WEIRD", category="c", finding_id="f4", event_id="e4"),
    ]
    m = findings_operator_metrics(findings)
    assert m["finding_count"] == 4
    assert m["severity_blocker"] == 1
    assert m["severity_high"] == 1
    assert m["severity_low"] == 1
    assert m["severity_other"] == 1
    assert m["distinct_categories"] == 3
    cap = findings_operator_metrics_caption(m)
    assert cap is not None
    assert "4" in cap
    assert "BLOCKER" in cap


def test_findings_table_rows_and_csv() -> None:
    findings = [_finding()]
    rows = findings_table_rows(findings)
    assert len(rows) == 1
    assert rows[0]["severity"] == "HIGH"
    assert rows[0]["finding_id"] == "f1"
    assert rows[0]["occurred_at"] == "2026-01-01T00:00:00Z"
    csv_text = findings_table_rows_csv(rows)
    assert "severity,category" in csv_text or "#,severity" in csv_text
    assert "HIGH" in csv_text
    assert findings_table_rows_csv([]) == ""


def test_findings_export_json_and_slug() -> None:
    body = {"run_id": "r1", "findings": [_finding()]}
    parsed = json.loads(findings_export_json(body))
    assert parsed["run_id"] == "r1"
    assert json.loads(findings_export_json(None)) == {}
    rid = "00000000-0000-4000-8000-000000000001"
    assert findings_export_filename_slug(rid) == rid
    assert findings_export_filename_slug("R@un!") == "r_un"


def test_findings_operator_metrics_table_rows() -> None:
    m = findings_operator_metrics([_finding(severity="HIGH")])
    rows = findings_operator_metrics_table_rows(m)
    assert any(r["field"] == "Finding count" for r in rows)
    assert any(r["field"] == "HIGH" for r in rows)


def test_findings_empty_caption() -> None:
    assert "finding.created" in findings_empty_caption()


def test_findings_operator_metrics_export_json() -> None:
    assert json.loads(findings_operator_metrics_export_json(None)) == {}
    m = findings_operator_metrics([_finding(severity="HIGH")])
    parsed = json.loads(findings_operator_metrics_export_json(m))
    assert parsed["finding_count"] == 1
    assert parsed["severity_high"] == 1


def test_findings_operator_metrics_table_rows_csv() -> None:
    m = findings_operator_metrics([_finding(severity="HIGH")])
    rows = findings_operator_metrics_table_rows(m)
    csv_text = findings_operator_metrics_table_rows_csv(rows)
    assert csv_text.startswith("field,value")
    assert "Finding count" in csv_text
    assert findings_operator_metrics_table_rows_csv([]) == ""


def test_findings_operator_metrics_export_filename_slug() -> None:
    rid = "00000000-0000-4000-8000-000000000001"
    assert findings_operator_metrics_export_filename_slug(rid) == rid
    assert findings_operator_metrics_export_filename_slug("R@un!") == "r_un"
