from __future__ import annotations

import json

from console.scraper_fetch_display import (
    scraper_fetch_artifacts_caption,
    scraper_fetch_failure_reason_caption,
    scraper_fetch_fetches_export_filename_slug,
    scraper_fetch_fetches_export_json,
    scraper_fetch_fetches_table_rows,
    scraper_fetch_fetches_table_rows_csv,
    scraper_fetch_from_timeline,
    scraper_fetch_operator_metrics,
    scraper_fetch_operator_metrics_caption,
    scraper_fetch_operator_metrics_export_filename_slug,
    scraper_fetch_operator_metrics_export_json,
    scraper_fetch_operator_metrics_table_rows,
    scraper_fetch_operator_metrics_table_rows_csv,
    scraper_fetch_outcome_caption,
    scraper_fetch_summary_export_filename_slug,
    scraper_fetch_summary_export_json,
    scraper_fetch_summary_rows,
    scraper_fetch_summary_rows_csv,
)


def test_scraper_fetch_from_timeline_extracts_dict() -> None:
    body = {"scraper_fetch": {"outcome": "passed", "fetch_count": 2}}
    assert scraper_fetch_from_timeline(body) == {"outcome": "passed", "fetch_count": 2}


def test_scraper_fetch_from_timeline_non_mapping() -> None:
    assert scraper_fetch_from_timeline(None) is None
    assert scraper_fetch_from_timeline([]) is None


def test_scraper_fetch_summary_rows_empty() -> None:
    assert scraper_fetch_summary_rows(None) == []
    assert scraper_fetch_summary_rows({}) == []


def test_scraper_fetch_summary_rows_passed_fixture() -> None:
    rows = scraper_fetch_summary_rows(
        {
            "outcome": "passed",
            "fetch_count": 2,
            "total_bytes": 150,
            "stage_name": "scraper:fetch",
        },
    )
    fields = {r["field"] for r in rows}
    assert "Outcome" in fields
    assert "Fetch count" in fields
    assert "Total bytes" in fields


def test_scraper_fetch_summary_export_helpers() -> None:
    summary = {
        "outcome": "passed",
        "fetch_count": 2,
        "total_bytes": 150,
        "stage_name": "scraper:fetch",
    }
    rows = scraper_fetch_summary_rows(summary)
    csv_text = scraper_fetch_summary_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert "passed" in csv_text
    assert json.loads(scraper_fetch_summary_export_json(summary))["fetch_count"] == 2
    assert scraper_fetch_summary_rows_csv([]) == ""
    assert json.loads(scraper_fetch_summary_export_json(None)) == {}
    assert json.loads(scraper_fetch_summary_export_json([])) == {}
    assert scraper_fetch_summary_export_filename_slug("Sf@x") == "sf_x"


def test_scraper_fetch_outcome_caption_passed_multi_url() -> None:
    cap = scraper_fetch_outcome_caption(
        {"outcome": "passed", "fetch_count": 2, "total_bytes": 150},
    )
    assert cap == "Scraper fetch: passed. 2 URL(s), 150 bytes total."


def test_scraper_fetch_outcome_caption_none_when_missing_outcome() -> None:
    assert scraper_fetch_outcome_caption(None) is None
    assert scraper_fetch_outcome_caption({"fetch_count": 1}) is None


def test_scraper_fetch_failure_reason_caption_budget_exceeded() -> None:
    cap = scraper_fetch_failure_reason_caption(
        {
            "outcome": "failed",
            "reason_code": "scraper_budget_exceeded",
            "failed_url_host": "b.com",
        },
    )
    assert cap == "Failure reason: scraper_budget_exceeded (host b.com)."


def test_scraper_fetch_failure_reason_caption_outbound_disabled() -> None:
    cap = scraper_fetch_failure_reason_caption(
        {"outcome": "failed", "reason_code": "outbound_fetch_disabled"},
    )
    assert cap == "Failure reason: outbound_fetch_disabled."


def test_scraper_fetch_failure_reason_caption_none_when_passed() -> None:
    assert scraper_fetch_failure_reason_caption({"outcome": "passed"}) is None


def test_scraper_fetch_fetches_table_rows_csv_empty() -> None:
    assert scraper_fetch_fetches_table_rows_csv([]) == ""


def test_scraper_fetch_fetches_export_json_and_csv() -> None:
    summary = {
        "fetches": [
            {"url_host": "a.com", "http_status": 200, "bytes": 100},
            {"url_host": "b.com", "http_status": 404},
        ],
    }
    rows = scraper_fetch_fetches_table_rows(summary)
    csv_body = scraper_fetch_fetches_table_rows_csv(rows)
    assert csv_body.startswith("#,URL host,HTTP status,")
    assert csv_body.count("\n") == 3
    parsed = json.loads(scraper_fetch_fetches_export_json(summary))
    assert len(parsed) == 2
    assert parsed[0]["url_host"] == "a.com"


def test_scraper_fetch_fetches_export_json_empty() -> None:
    assert scraper_fetch_fetches_export_json(None) == "[]"
    assert scraper_fetch_fetches_export_json({}) == "[]"
    assert scraper_fetch_fetches_export_json({"fetches": None}) == "[]"


def test_scraper_fetch_fetches_export_filename_slug() -> None:
    assert scraper_fetch_fetches_export_filename_slug("run/x!") == "run_x"
    assert scraper_fetch_fetches_export_filename_slug("   ") == "run"


def test_scraper_fetch_fetches_table_rows_multi_url() -> None:
    rows = scraper_fetch_fetches_table_rows(
        {
            "fetches": [
                {"url_host": "a.com", "http_status": 200, "bytes": 100},
                {"url_host": "b.com", "http_status": 404, "bytes": 0},
            ],
        },
    )
    assert len(rows) == 2
    assert rows[0]["URL host"] == "a.com"
    assert rows[1]["HTTP status"] == "404"


def test_scraper_fetch_artifacts_caption_counts_relpath_rows() -> None:
    cap = scraper_fetch_artifacts_caption(
        {
            "fetches": [
                {"url_host": "a.com", "artifact_relpath": "artifacts/a.html"},
                {"url_host": "b.com"},
            ],
        },
    )
    assert cap is not None
    assert "1" in cap
    assert scraper_fetch_artifacts_caption({"fetches": [{"url_host": "x.com"}]}) is None


def test_scraper_fetch_operator_metrics_empty() -> None:
    m = scraper_fetch_operator_metrics(None)
    assert m["fetch_count"] == 0
    assert m["outcome"] is None
    assert scraper_fetch_operator_metrics_caption(m) is None
    rows = scraper_fetch_operator_metrics_table_rows(m)
    assert len(rows) == 2
    assert rows[0]["field"] == "Fetch count"


def test_scraper_fetch_operator_metrics_passed_multi_fetch() -> None:
    summary = {
        "outcome": "passed",
        "fetch_count": 2,
        "total_bytes": 250,
        "fetches": [
            {"url_host": "a.com", "bytes": 100, "artifact_relpath": "a.html"},
            {"url_host": "b.com", "bytes": 150},
        ],
    }
    m = scraper_fetch_operator_metrics(summary)
    assert m["outcome"] == "passed"
    assert m["fetch_count"] == 2
    assert m["total_bytes"] == 250
    assert m["artifact_relpath_count"] == 1
    assert m["failed_url_present"] is False
    cap = scraper_fetch_operator_metrics_caption(m)
    assert cap is not None
    assert "passed" in cap
    rows = scraper_fetch_operator_metrics_table_rows(m)
    assert any(r["field"] == "Artifact relpath rows" for r in rows)


def test_scraper_fetch_operator_metrics_failed_outcome() -> None:
    summary = {
        "outcome": "failed",
        "fetch_count": 1,
        "failed_url_host": "bad.example",
    }
    m = scraper_fetch_operator_metrics(summary)
    assert m["outcome"] == "failed"
    assert m["failed_url_present"] is True
    rows = scraper_fetch_operator_metrics_table_rows(m)
    assert any(r["field"] == "Failed URL host present" for r in rows)


def test_scraper_fetch_operator_metrics_export() -> None:
    summary = {"outcome": "passed", "fetch_count": 1, "total_bytes": 50}
    m = scraper_fetch_operator_metrics(summary)
    parsed = json.loads(scraper_fetch_operator_metrics_export_json(m))
    assert parsed["fetch_count"] == 1
    assert json.loads(scraper_fetch_operator_metrics_export_json(None)) == {}
    rows = scraper_fetch_operator_metrics_table_rows(m)
    csv_text = scraper_fetch_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert scraper_fetch_operator_metrics_table_rows_csv([]) == ""
    assert scraper_fetch_operator_metrics_export_filename_slug("Ab c!") == "ab_c"
