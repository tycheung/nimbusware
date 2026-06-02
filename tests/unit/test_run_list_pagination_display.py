from __future__ import annotations

import json

from nimbusware_console.run_list_pagination_display import (
    run_detail_summary_export_filename_slug,
    run_detail_summary_export_json,
    run_detail_summary_operator_metrics,
    run_detail_summary_operator_metrics_caption,
    run_detail_summary_operator_metrics_export_filename_slug,
    run_detail_summary_operator_metrics_export_json,
    run_detail_summary_operator_metrics_table_rows,
    run_list_active_query_params_caption,
    run_list_created_range_caption,
    run_list_has_escalation_filter_caption,
    run_list_has_more_true_caption,
    run_list_include_summary_filter_caption,
    run_list_keyset_next_page_caption,
    run_list_next_cursor_length_caption,
    run_list_order_desc_caption,
    run_list_page_vs_total_caption,
    run_list_pagination_link_caption,
    run_list_response_pagination_caption,
    run_list_status_filter_caption,
    run_list_summaries_sparse_caption,
    run_list_workflow_profile_filter_caption,
    timeline_events_export_filename_slug,
    timeline_events_export_json,
    timeline_events_from_body,
    timeline_events_operator_metrics,
    timeline_events_operator_metrics_caption,
    timeline_events_operator_metrics_export_json,
    timeline_events_operator_metrics_table_rows,
    timeline_events_operator_metrics_table_rows_csv,
    timeline_events_table_rows,
    timeline_events_table_rows_csv,
)


def test_run_list_pagination_link_caption() -> None:
    cap = run_list_pagination_link_caption(link_header_present=True)
    assert cap is not None
    assert "Link header" in cap
    assert run_list_pagination_link_caption(link_header_present=False) is None


def test_run_list_response_pagination_caption_none_without_run_ids() -> None:
    assert run_list_response_pagination_caption(None, link_header_present=False) is None
    assert run_list_response_pagination_caption({}, link_header_present=False) is None
    assert (
        run_list_response_pagination_caption({"total": 3}, link_header_present=False)
        is None
    )


def test_run_list_response_pagination_caption_full() -> None:
    data = {
        "run_ids": ["a", "b"],
        "total": 99,
        "has_more": True,
        "next_cursor": "opaque-token",
    }
    cap = run_list_response_pagination_caption(data, link_header_present=True)
    assert cap is not None
    assert "2 run_id" in cap
    assert "total=99" in cap
    assert "has_more=yes" in cap
    assert "next_cursor=present" in cap
    assert "Link header=present" in cap


def test_run_list_response_pagination_caption_no_link_no_cursor() -> None:
    data = {"run_ids": ["x"], "total": 1, "has_more": False, "next_cursor": None}
    cap = run_list_response_pagination_caption(data, link_header_present=False)
    assert cap is not None
    assert "has_more=no" in cap
    assert "next_cursor=absent" in cap
    assert "Link header=absent" in cap


def test_run_list_response_pagination_caption_includes_offset_limit() -> None:
    data = {
        "run_ids": ["a"],
        "total": 10,
        "has_more": True,
        "next_cursor": "c",
        "offset": 20,
        "limit": 50,
    }
    cap = run_list_response_pagination_caption(data, link_header_present=False)
    assert cap is not None
    assert "offset=20" in cap
    assert "limit=50" in cap


def test_run_list_summaries_sparse_caption_when_partial() -> None:
    cap = run_list_summaries_sparse_caption(
        {
            "run_ids": ["a", "b"],
            "summaries": {"a": {"status": "running"}},
        },
    )
    assert cap is not None
    assert "Sparse" in cap
    assert "1" in cap and "2" in cap


def test_run_list_summaries_sparse_caption_none_when_full_coverage() -> None:
    assert (
        run_list_summaries_sparse_caption(
            {
                "run_ids": ["a", "b"],
                "summaries": {"a": {}, "b": {}},
            },
        )
        is None
    )


def test_run_list_summaries_sparse_caption_none_for_bad_payload() -> None:
    assert run_list_summaries_sparse_caption(None) is None
    assert run_list_summaries_sparse_caption({"run_ids": []}) is None
    assert run_list_summaries_sparse_caption({"run_ids": ["a"]}) is None


def test_run_list_next_cursor_length_caption_when_present() -> None:
    cap = run_list_next_cursor_length_caption(
        {"run_ids": ["a"], "next_cursor": "  abc  "},
    )
    assert cap is not None
    assert "3" in cap
    assert "next_cursor" in cap


def test_run_list_created_range_caption() -> None:
    cap_both = run_list_created_range_caption(
        {"created_after": "2026-01-01T00:00:00Z", "created_before": "2026-12-31T23:59:59Z"},
    )
    assert cap_both is not None
    assert "created_after=set" in cap_both
    assert "created_before=set" in cap_both
    cap_after = run_list_created_range_caption({"created_after": "2026-01-01"})
    assert cap_after is not None
    assert "created_after=set" in cap_after
    assert run_list_created_range_caption(None) is None
    assert run_list_created_range_caption({}) is None
    assert run_list_created_range_caption({"created_after": "   "}) is None


def test_run_list_status_filter_caption() -> None:
    cap = run_list_status_filter_caption({"status": "running"})
    assert cap is not None
    assert "**running**" in cap
    cap_term = run_list_status_filter_caption({"status": "  terminal  "})
    assert cap_term is not None
    assert "**terminal**" in cap_term
    assert run_list_status_filter_caption(None) is None
    assert run_list_status_filter_caption({}) is None
    assert run_list_status_filter_caption({"status": "   "}) is None
    assert run_list_status_filter_caption({"status": 1}) is None


def test_run_list_workflow_profile_filter_caption() -> None:
    cap_wf = run_list_workflow_profile_filter_caption(
        {"workflow_profile": "  my-profile  "},
    )
    assert cap_wf is not None
    assert "my-profile" in cap_wf
    cap_pfx = run_list_workflow_profile_filter_caption(
        {"workflow_profile_prefix": "dev-"},
    )
    assert cap_pfx is not None
    assert "dev-" in cap_pfx
    assert run_list_workflow_profile_filter_caption(
        {"workflow_profile": "x", "workflow_profile_prefix": "y"},
    ) is not None
    assert "x" in (
        run_list_workflow_profile_filter_caption(
            {"workflow_profile": "x", "workflow_profile_prefix": "y"},
        )
        or ""
    )
    assert run_list_workflow_profile_filter_caption(None) is None
    assert run_list_workflow_profile_filter_caption({}) is None
    assert run_list_workflow_profile_filter_caption({"workflow_profile": "  "}) is None


def test_run_list_has_escalation_filter_caption() -> None:
    cap0 = run_list_has_escalation_filter_caption({"has_escalation": 0})
    assert cap0 is not None
    assert "**0**" in cap0
    assert "no escalation" in cap0
    cap1 = run_list_has_escalation_filter_caption({"has_escalation": 1})
    assert cap1 is not None
    assert "**1**" in cap1
    assert "escalation only" in cap1
    assert run_list_has_escalation_filter_caption(None) is None
    assert run_list_has_escalation_filter_caption({}) is None
    assert run_list_has_escalation_filter_caption({"has_escalation": 2}) is None
    assert run_list_has_escalation_filter_caption({"has_escalation": True}) is None


def test_run_list_active_query_params_caption_defaults_when_empty() -> None:
    cap = run_list_active_query_params_caption(None)
    assert cap is not None
    assert "defaults only" in cap
    cap2 = run_list_active_query_params_caption({})
    assert cap2 is not None
    assert "defaults only" in cap2


def test_run_list_active_query_params_caption_lists_filters() -> None:
    cap = run_list_active_query_params_caption(
        {
            "order": "newest_first",
            "limit": 20,
            "status": "running",
            "has_escalation": 1,
            "include_summary": 1,
            "cursor": "tok",
        },
    )
    assert cap is not None
    assert "order=newest_first" in cap
    assert "limit=20" in cap
    assert "status=running" in cap
    assert "has_escalation=1" in cap
    assert "include_summary=yes" in cap
    assert "cursor=keyset" in cap


def test_run_list_page_vs_total_caption_none_when_page_covers_total() -> None:
    assert run_list_page_vs_total_caption(None) is None
    assert run_list_page_vs_total_caption({}) is None
    assert run_list_page_vs_total_caption({"run_ids": [], "total": 10}) is None
    assert run_list_page_vs_total_caption({"run_ids": ["a", "b"], "total": 2}) is None
    assert run_list_page_vs_total_caption({"run_ids": ["a"], "total": 1}) is None


def test_run_list_page_vs_total_caption_when_total_exceeds_page() -> None:
    cap = run_list_page_vs_total_caption({"run_ids": ["a", "b"], "total": 99})
    assert cap is not None
    assert "**2** run_ids" in cap
    assert "**99** total" in cap
    cap_one = run_list_page_vs_total_caption({"run_ids": ["x"], "total": 5})
    assert cap_one is not None
    assert "**1** run_id" in cap_one


def test_run_list_keyset_next_page_caption() -> None:
    cap = run_list_keyset_next_page_caption(
        {"has_more": True, "next_cursor": "opaque-token"},
    )
    assert cap is not None
    assert "keyset" in cap.lower()
    assert run_list_keyset_next_page_caption(None) is None
    assert run_list_keyset_next_page_caption({}) is None
    assert run_list_keyset_next_page_caption({"has_more": False, "next_cursor": "x"}) is None
    assert run_list_keyset_next_page_caption({"has_more": True}) is None
    assert run_list_keyset_next_page_caption({"has_more": True, "next_cursor": ""}) is None


def test_run_list_next_cursor_length_caption_none_when_absent_or_blank() -> None:
    assert run_list_next_cursor_length_caption(None) is None
    assert run_list_next_cursor_length_caption({}) is None
    assert run_list_next_cursor_length_caption({"next_cursor": ""}) is None
    assert run_list_next_cursor_length_caption({"next_cursor": "   "}) is None
    assert run_list_next_cursor_length_caption({"next_cursor": None}) is None


def test_run_list_include_summary_filter_caption() -> None:
    cap = run_list_include_summary_filter_caption({"include_summary": 1})
    assert cap is not None
    assert "include_summary=yes" in cap
    assert run_list_include_summary_filter_caption({"include_summary": 0}) is None
    assert run_list_include_summary_filter_caption(None) is None
    assert run_list_include_summary_filter_caption({}) is None


def test_run_list_order_desc_caption() -> None:
    cap = run_list_order_desc_caption({"order": "desc"})
    assert cap is not None
    assert "**desc**" in cap
    assert run_list_order_desc_caption({"order": "asc"}) is None
    assert run_list_order_desc_caption(None) is None


def test_run_list_has_more_true_caption() -> None:
    cap = run_list_has_more_true_caption({"has_more": True})
    assert cap is not None
    assert "has_more=yes" in cap
    assert run_list_has_more_true_caption({"has_more": False}) is None
    assert run_list_has_more_true_caption(None) is None


def test_run_detail_summary_export_json_and_slug() -> None:
    body = {"event_count": 1, "findings_count": 0, "has_escalation": False}
    parsed = json.loads(run_detail_summary_export_json(body))
    assert parsed == body
    assert json.loads(run_detail_summary_export_json(None)) == {}
    assert run_detail_summary_export_json("x") == "{}"
    rid = "00000000-0000-4000-8000-000000000001"
    assert run_detail_summary_export_filename_slug(rid) == rid
    assert run_detail_summary_export_filename_slug("R@un!") == "r_un"


def test_run_detail_summary_operator_metrics() -> None:
    body = {
        "run_id": "00000000-0000-4000-8000-000000000001",
        "event_count": 12,
        "findings_count": 3,
        "has_escalation": True,
        "status": "completed",
        "workflow_profile": "demo",
    }
    m = run_detail_summary_operator_metrics(body)
    assert m["event_count"] == 12
    assert m["findings_count"] == 3
    assert m["has_escalation"] is True
    assert m["run_id_present"] is True
    cap = run_detail_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "12" in cap


def test_run_detail_summary_operator_metrics_export() -> None:
    m = run_detail_summary_operator_metrics(None)
    assert run_detail_summary_operator_metrics_caption(m) is None
    parsed = json.loads(run_detail_summary_operator_metrics_export_json(m))
    assert parsed["event_count"] == 0
    rows = run_detail_summary_operator_metrics_table_rows(m)
    assert rows[0]["field"] == "Event count"
    assert (
        run_detail_summary_operator_metrics_export_filename_slug()
        == "run_detail_summary_operator_metrics"
    )


def test_timeline_events_from_body_empty() -> None:
    assert timeline_events_from_body(None) == []
    assert timeline_events_from_body({}) == []
    assert timeline_events_from_body({"events": "x"}) == []


def test_timeline_events_export_json_roundtrip() -> None:
    evs = [
        {
            "event_type": "run.started",
            "occurred_at": "2026-01-01T00:00:00Z",
            "event_id": "e1",
        },
        {
            "event_type": "stage.started",
            "occurred_at": "2026-01-01T00:01:00Z",
            "event_id": "e2",
        },
    ]
    body = {"run_id": "r1", "events": evs, "integrator_gate": None}
    parsed = json.loads(timeline_events_export_json(body))
    assert parsed == evs
    assert json.loads(timeline_events_export_json(None)) == []


def test_timeline_events_table_rows_and_csv() -> None:
    evs = [
        {"event_type": "a", "occurred_at": "t1", "event_id": "id1"},
        "skip",
        {"event_type": "b", "occurred_at": "t2", "event_id": "id2"},
    ]
    rows = timeline_events_table_rows(evs)
    assert len(rows) == 2
    assert rows[0]["event_type"] == "a"
    csv_text = timeline_events_table_rows_csv(rows)
    assert "event_type,occurred_at,event_id" in csv_text
    assert csv_text.count("\n") == 3
    assert timeline_events_table_rows_csv([]) == ""


def test_timeline_events_export_filename_slug() -> None:
    rid = "00000000-0000-4000-8000-000000000001"
    assert timeline_events_export_filename_slug(rid) == rid
    assert timeline_events_export_filename_slug("R@un!") == "r_un"


def test_timeline_events_operator_metrics_empty() -> None:
    m = timeline_events_operator_metrics([])
    assert m["event_count"] == 0
    assert timeline_events_operator_metrics_caption(m) is None
    rows = timeline_events_operator_metrics_table_rows(m)
    assert len(rows) == 2
    assert rows[0]["field"] == "Event count"


def test_timeline_events_operator_metrics_mixed() -> None:
    events = [
        {"event_type": "run.started", "occurred_at": "t1", "event_id": "e1"},
        {"event_type": "stage.started", "occurred_at": "t2", "event_id": "e2"},
        {"event_type": "run.started", "occurred_at": "t3", "event_id": "e3"},
        "skip",
    ]
    m = timeline_events_operator_metrics(events)
    assert m["event_count"] == 3
    assert m["distinct_event_type_count"] == 2
    assert m["top_event_type"] == "run.started"
    assert m["top_event_type_count"] == 2
    cap = timeline_events_operator_metrics_caption(m)
    assert cap is not None
    assert "3" in cap
    rows = timeline_events_operator_metrics_table_rows(m)
    assert any("run.started" in r["value"] for r in rows)


def test_timeline_events_operator_metrics_export() -> None:
    events = [{"event_type": "a", "occurred_at": "t", "event_id": "e"}]
    m = timeline_events_operator_metrics(events)
    parsed = json.loads(timeline_events_operator_metrics_export_json(m))
    assert parsed["event_count"] == 1
    assert json.loads(timeline_events_operator_metrics_export_json(None)) == {}
    rows = timeline_events_operator_metrics_table_rows(m)
    csv_text = timeline_events_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert timeline_events_operator_metrics_table_rows_csv([]) == ""
