"""Unit tests for cross-run preflight trend helpers (fo130 / §14 #1)."""

from __future__ import annotations

import json

import httpx

from nimbusware_console.preflight_cross_run_display import (
    fetch_preflight_history,
    preflight_cross_run_checks_passed_coverage_caption,
    preflight_cross_run_latency_sample_count_coverage_caption,
    preflight_cross_run_multisample_caption,
    preflight_cross_run_operator_depth_caption,
    preflight_cross_run_operator_metrics,
    preflight_cross_run_operator_metrics_caption,
    preflight_cross_run_operator_metrics_export_filename_slug,
    preflight_cross_run_operator_metrics_export_json,
    preflight_cross_run_operator_metrics_table_rows,
    preflight_cross_run_operator_metrics_table_rows_csv,
    preflight_cross_run_p95_spread_caption,
    preflight_cross_run_p95_spread_ms,
    preflight_cross_run_projection_without_p95_count,
    preflight_cross_run_trend_export_filename_slug,
    preflight_cross_run_trend_export_json,
    preflight_cross_run_trend_rows,
    preflight_cross_run_trend_rows_csv,
    preflight_cross_run_trend_summary,
    preflight_cross_run_validated_model_id_coverage_caption,
    preflight_history_metrics_export_download_filename_slug,
    preflight_history_metrics_export_download_json,
    preflight_history_response_avg_p95_latency_ms,
    preflight_history_response_coverage_ratio,
    preflight_history_response_distinct_validated_model_id_count,
    preflight_history_response_limit,
    preflight_history_response_max_p95_latency_ms,
    preflight_history_response_metrics_export,
    preflight_history_response_metrics_export_caption,
    preflight_history_response_p95_latency_coverage_ratio,
    preflight_history_response_runs_with_checks_passed,
    preflight_history_response_runs_with_multisample_preflight,
    preflight_history_response_runs_with_preflight,
    preflight_history_response_runs_without_preflight,
    preflight_history_response_sli_caption,
    preflight_pairs_from_history_response,
    short_run_id_label,
)


def test_preflight_pairs_from_history_response_maps_entries() -> None:
    body = {
        "entries": [
            {"run_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "preflight": {"p95_latency_ms": 10}},
            {"run_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "preflight": None},
        ],
        "limit": 2,
    }
    pairs = preflight_pairs_from_history_response(body)
    assert len(pairs) == 2
    rows = preflight_cross_run_trend_rows(pairs)
    assert rows[0]["p95_latency_ms"] == 10
    assert rows[1]["has_preflight"] is False
    assert preflight_history_response_limit(body) == 2


def test_preflight_history_response_sli_extractors() -> None:
    body = {
        "entries": [],
        "runs_with_preflight": 7,
        "runs_without_preflight": 3,
        "avg_p95_latency_ms": 123.5,
        "max_p95_latency_ms": 222,
        "preflight_coverage_ratio": 0.7,
        "runs_with_checks_passed": 6,
        "distinct_validated_model_id_count": 2,
    }
    assert preflight_history_response_runs_with_preflight(body) == 7
    assert preflight_history_response_runs_without_preflight(body) == 3
    assert preflight_history_response_avg_p95_latency_ms(body) == 123.5
    assert preflight_history_response_max_p95_latency_ms(body) == 222
    assert preflight_history_response_coverage_ratio(body) == 0.7
    assert preflight_history_response_runs_with_checks_passed(body) == 6
    assert preflight_history_response_distinct_validated_model_id_count(body) == 2


def test_fetch_preflight_history_include_metrics_export_param(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"entries": []}

    def _fake_get(
        url: str,
        *,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", _fake_get)
    body = fetch_preflight_history(
        "http://127.0.0.1/v1",
        limit=10,
        include_metrics_export=True,
    )
    assert body == {"entries": []}
    assert captured["params"] == {
        "limit": 10,
        "order": "newest_first",
        "include_metrics_export": 1,
    }


def test_preflight_history_metrics_export_download_json() -> None:
    body = {
        "metrics_export": {
            "export_schema_version": 1,
            "runs_scanned": 3,
            "window_total_matching_runs": 5,
        }
    }
    parsed = json.loads(preflight_history_metrics_export_download_json(body))
    assert parsed["runs_scanned"] == 3
    assert preflight_history_metrics_export_download_json(None) == "{}"
    assert (
        preflight_history_metrics_export_download_filename_slug()
        == "preflight_history_metrics_export"
    )


def test_preflight_history_response_metrics_export_extractors() -> None:
    body = {
        "metrics_export": {
            "export_schema_version": 1,
            "runs_scanned": 5,
            "window_limit": 10,
            "window_total_matching_runs": 12,
            "has_more": True,
            "export_window_consistent": True,
            "filters": {"status": "created"},
        }
    }
    export = preflight_history_response_metrics_export(body)
    assert export is not None
    assert export["runs_scanned"] == 5
    cap = preflight_history_response_metrics_export_caption(body)
    assert cap is not None
    assert "runs_scanned=5" in cap
    assert "window_total=12" in cap
    assert "has_more=yes" in cap
    assert "status=created" in cap
    assert "schema=v1" in cap
    assert "window_consistent=yes" in cap


def test_preflight_history_response_sli_caption() -> None:
    cap = preflight_history_response_sli_caption(
        {
            "runs_with_preflight": 7,
            "runs_without_preflight": 3,
            "preflight_coverage_ratio": 0.7,
            "avg_p95_latency_ms": 123.5,
            "max_p95_latency_ms": 222,
            "runs_with_checks_passed": 6,
            "distinct_validated_model_id_count": 2,
        },
    )
    assert cap is not None
    assert "with_preflight=7" in cap
    assert "without_preflight=3" in cap
    assert "coverage=0.700" in cap
    assert "avg_p95_ms=123.5" in cap
    assert "max_p95_ms=222" in cap
    assert "checks_passed_runs=6" in cap
    assert "distinct_validated_model_ids=2" in cap


def test_preflight_history_response_multisample_extractor_and_caption() -> None:
    body = {
        "runs_with_preflight": 5,
        "runs_with_multisample_preflight": 3,
    }
    assert preflight_history_response_runs_with_multisample_preflight(body) == 3
    cap = preflight_history_response_sli_caption(body)
    assert cap is not None
    assert "multisample=3" in cap


def test_preflight_history_response_p95_coverage_extractor_and_caption() -> None:
    body = {
        "runs_with_preflight": 10,
        "runs_without_preflight": 0,
        "preflight_coverage_ratio": 1.0,
        "p95_latency_coverage_ratio": 0.8,
    }
    assert preflight_history_response_p95_latency_coverage_ratio(body) == 0.8
    cap = preflight_history_response_sli_caption(body)
    assert cap is not None
    assert "p95_coverage=0.800" in cap


def test_preflight_pairs_from_history_matches_timeline_shape() -> None:
    """Equivalent preflight dict produces the same trend rows as timeline extraction."""
    from nimbusware_console.preflight_history_display import preflight_history_from_timeline

    pf = {
        "p95_latency_ms": 120,
        "preflight_latency_sample_count": 3,
        "validated_model_id": "m1",
    }
    timeline_body = {"preflight": pf}
    pairs_api = preflight_pairs_from_history_response(
        {"entries": [{"run_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "preflight": pf}]},
    )
    pairs_tl = [
        (
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            preflight_history_from_timeline(timeline_body),
        ),
    ]
    assert preflight_cross_run_trend_rows(pairs_api) == preflight_cross_run_trend_rows(pairs_tl)


def test_short_run_id_label_truncates() -> None:
    long = "11111111-2222-4333-8444-555555555555"
    assert short_run_id_label(long, head=8) == "11111111…"
    assert short_run_id_label("short") == "short"


def test_preflight_cross_run_trend_rows_none_preflight() -> None:
    rows = preflight_cross_run_trend_rows(
        [("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", None)],
    )
    assert len(rows) == 1
    assert rows[0]["run_index"] == 1
    assert rows[0]["has_preflight"] is False
    assert rows[0]["p95_latency_ms"] is None


def test_preflight_cross_run_trend_rows_p95_and_samples() -> None:
    pf = {
        "p95_latency_ms": 120,
        "preflight_latency_sample_count": 3,
        "validated_model_id": "m1",
    }
    rows = preflight_cross_run_trend_rows(
        [
            ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", pf),
            ("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", None),
        ],
    )
    assert rows[0]["p95_latency_ms"] == 120
    assert rows[0]["sample_count"] == 3
    assert rows[0]["validated_model_id"] == "m1"
    assert rows[0]["has_preflight"] is True
    assert rows[1]["run_index"] == 2
    assert rows[1]["has_preflight"] is False


def test_preflight_cross_run_trend_rows_rejects_bad_p95() -> None:
    rows = preflight_cross_run_trend_rows(
        [("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", {"p95_latency_ms": -1})],
    )
    assert rows[0]["has_preflight"] is True
    assert rows[0]["p95_latency_ms"] is None


def test_preflight_cross_run_trend_summary() -> None:
    rows = [
        {
            "has_preflight": True,
            "p95_latency_ms": 1,
            "validated_model_id": "m-a",
            "sample_count": 1,
        },
        {
            "has_preflight": True,
            "p95_latency_ms": None,
            "validated_model_id": "m-a",
            "sample_count": 3,
        },
        {"has_preflight": False, "p95_latency_ms": None},
    ]
    s = preflight_cross_run_trend_summary(rows)
    assert s["runs"] == 3
    assert s["with_preflight_projection"] == 2
    assert s["with_p95_latency"] == 1
    assert s["with_validated_model_id"] == 2
    assert s["distinct_validated_model_id_count"] == 1
    assert s["with_integer_sample_count"] == 2
    assert s["with_sample_count_gt_one"] == 1


def test_preflight_cross_run_trend_summary_multisample_counts() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 1, "preflight_latency_sample_count": 1}),
            ("b", {"p95_latency_ms": 2, "preflight_latency_sample_count": 5}),
        ],
    )
    s = preflight_cross_run_trend_summary(rows)
    assert s["with_preflight_projection"] == 2
    assert s["with_integer_sample_count"] == 2
    assert s["with_sample_count_gt_one"] == 1


def test_preflight_cross_run_multisample_caption() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 1, "preflight_latency_sample_count": 4}),
            ("b", {"p95_latency_ms": 2, "preflight_latency_sample_count": 2}),
        ],
    )
    cap = preflight_cross_run_multisample_caption(rows)
    assert cap is not None
    assert "Multisample preflight" in cap
    assert "preflight_latency_sample_count" in cap


def test_preflight_cross_run_multisample_caption_none_when_all_single_sample() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 1, "preflight_latency_sample_count": 1}),
        ],
    )
    assert preflight_cross_run_multisample_caption(rows) is None


def test_preflight_cross_run_projection_without_p95_count() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 10}),
            ("b", {"p95_latency_ms": -1}),
            ("c", None),
        ],
    )
    assert preflight_cross_run_projection_without_p95_count(rows) == 1
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 100}),
            ("b", {"p95_latency_ms": 40}),
        ],
    )
    sp = preflight_cross_run_p95_spread_ms(rows)
    assert sp == {"min_p95_ms": 40, "max_p95_ms": 100, "span_ms": 60, "n": 2}
    single = preflight_cross_run_trend_rows([("a", {"p95_latency_ms": 1})])
    assert preflight_cross_run_p95_spread_ms(single) is None


def test_preflight_cross_run_p95_spread_caption() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 100}),
            ("b", {"p95_latency_ms": 40}),
        ],
    )
    cap = preflight_cross_run_p95_spread_caption(rows)
    assert cap is not None
    assert "**40**" in cap
    assert "**100**" in cap
    assert "**60**" in cap
    assert preflight_cross_run_p95_spread_caption([]) is None
    single = preflight_cross_run_trend_rows([("a", {"p95_latency_ms": 1})])
    assert preflight_cross_run_p95_spread_caption(single) is None


def test_preflight_cross_run_operator_depth_caption() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 200}),
            ("b", {"p95_latency_ms": 50}),
            ("c", {"p95_latency_ms": -5}),
        ],
    )
    cap = preflight_cross_run_operator_depth_caption(rows)
    assert cap is not None
    assert "without a usable p95" in cap
    assert "50 / 200 ms" in cap


def test_preflight_cross_run_latency_sample_count_coverage_caption() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 1, "preflight_latency_sample_count": 3}),
            ("b", {"p95_latency_ms": 2}),
        ],
    )
    cap = preflight_cross_run_latency_sample_count_coverage_caption(rows)
    assert cap is not None
    assert "1" in cap and "2" in cap


def test_preflight_cross_run_latency_sample_count_coverage_caption_none_without_preflight() -> None:
    rows = preflight_cross_run_trend_rows([("a", None)])
    assert preflight_cross_run_latency_sample_count_coverage_caption(rows) is None


def test_preflight_cross_run_trend_summary_no_validated_model_ids() -> None:
    rows = [
        {"has_preflight": True, "p95_latency_ms": 1},
        {"has_preflight": True, "p95_latency_ms": 2, "validated_model_id": None},
    ]
    s = preflight_cross_run_trend_summary(rows)
    assert s["with_validated_model_id"] == 0
    assert s["distinct_validated_model_id_count"] == 0
    assert s["with_integer_sample_count"] == 0
    assert s["with_sample_count_gt_one"] == 0


def test_preflight_cross_run_validated_model_id_coverage_caption() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 1, "validated_model_id": "x"}),
            ("b", {"p95_latency_ms": 2, "validated_model_id": "y"}),
            ("c", {"p95_latency_ms": 3, "validated_model_id": "x"}),
        ],
    )
    cap = preflight_cross_run_validated_model_id_coverage_caption(rows)
    assert cap is not None
    assert "3" in cap and "2" in cap


def test_preflight_cross_run_validated_model_id_coverage_caption_none_without_ids() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 1}),
        ],
    )
    assert preflight_cross_run_validated_model_id_coverage_caption(rows) is None


def test_preflight_cross_run_trend_rows_checks_passed_count() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            (
                "a",
                {
                    "p95_latency_ms": 1,
                    "checks_passed": ["runtime_reachable", "model_available"],
                },
            ),
            ("b", {"p95_latency_ms": 2, "checks_passed": []}),
            ("c", {"p95_latency_ms": 3, "checks_passed": "not-a-list"}),
        ],
    )
    assert rows[0]["checks_passed_count"] == 2
    assert rows[1]["checks_passed_count"] is None
    assert rows[2]["checks_passed_count"] is None


def test_preflight_cross_run_checks_passed_coverage_caption() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"checks_passed": ["a_check"]}),
            ("b", {"checks_passed": ["b_check", "c_check"]}),
            ("c", {"p95_latency_ms": 1}),
        ],
    )
    cap = preflight_cross_run_checks_passed_coverage_caption(rows)
    assert cap is not None
    assert "**2**" in cap and "**3**" in cap


def test_preflight_cross_run_checks_passed_coverage_caption_none_all_missing() -> None:
    rows = preflight_cross_run_trend_rows(
        [
            ("a", {"p95_latency_ms": 1}),
            ("b", None),
        ],
    )
    assert preflight_cross_run_checks_passed_coverage_caption(rows) is None


def test_preflight_cross_run_checks_passed_coverage_caption_none_no_preflight() -> None:
    rows = preflight_cross_run_trend_rows([("a", None)])
    assert preflight_cross_run_checks_passed_coverage_caption(rows) is None


def test_preflight_cross_run_trend_rows_csv_empty() -> None:
    assert preflight_cross_run_trend_rows_csv([]) == ""


def test_preflight_cross_run_trend_export_json_empty() -> None:
    assert preflight_cross_run_trend_export_json([]) == "[]"


def test_preflight_cross_run_trend_export_json_and_csv() -> None:
    rid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    pf = {"p95_latency_ms": 120, "preflight_latency_sample_count": 3}
    rows = preflight_cross_run_trend_rows(
        [(rid, pf), ("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", None)],
    )
    csv_body = preflight_cross_run_trend_rows_csv(rows)
    assert csv_body.startswith("run_index,run_id,run_label,")
    assert rid in csv_body
    assert "True" in csv_body
    assert "False" in csv_body
    parsed = json.loads(preflight_cross_run_trend_export_json(rows))
    assert len(parsed) == 2
    assert parsed[0]["run_id"] == rid
    assert parsed[0]["p95_latency_ms"] == 120


def test_preflight_cross_run_trend_export_filename_slug() -> None:
    assert preflight_cross_run_trend_export_filename_slug() == "preflight_trends"


def test_preflight_cross_run_operator_metrics_empty() -> None:
    m = preflight_cross_run_operator_metrics(None)
    assert m == {}
    assert preflight_cross_run_operator_metrics_caption(m) is None
    assert preflight_cross_run_operator_metrics_table_rows(m) == []


def test_preflight_cross_run_operator_metrics_from_summary() -> None:
    rows = [
        {
            "has_preflight": True,
            "p95_latency_ms": 1,
            "validated_model_id": "m-a",
            "sample_count": 2,
        },
        {"has_preflight": False},
    ]
    summary = preflight_cross_run_trend_summary(rows)
    m = preflight_cross_run_operator_metrics(summary)
    assert m["runs"] == 2
    assert m["with_preflight_projection"] == 1
    assert m["with_p95_latency"] == 1
    cap = preflight_cross_run_operator_metrics_caption(m)
    assert cap is not None
    assert "2" in cap
    metric_rows = preflight_cross_run_operator_metrics_table_rows(m)
    assert any(r["field"] == "Runs scanned" for r in metric_rows)


def test_preflight_cross_run_operator_metrics_export() -> None:
    summary = preflight_cross_run_trend_summary(
        [{"has_preflight": True, "p95_latency_ms": 50, "sample_count": 1}],
    )
    m = preflight_cross_run_operator_metrics(summary)
    parsed = json.loads(preflight_cross_run_operator_metrics_export_json(m))
    assert parsed["runs"] == 1
    assert json.loads(preflight_cross_run_operator_metrics_export_json(None)) == {}
    rows = preflight_cross_run_operator_metrics_table_rows(m)
    csv_text = preflight_cross_run_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert preflight_cross_run_operator_metrics_table_rows_csv([]) == ""
    assert (
        preflight_cross_run_operator_metrics_export_filename_slug()
        == "preflight_trends_operator_metrics"
    )
