from __future__ import annotations

import json

from nimbusware_console.universal_critique_timeline_display import (
    universal_critique_fail_stage_rows_csv,
    universal_critique_from_timeline,
    universal_critique_snapshot_from_compare_paste,
    universal_critique_timeline_default_on_caption,
    universal_critique_timeline_export_filename_slug,
    universal_critique_timeline_export_json,
    universal_critique_timeline_fail_count_caption,
    universal_critique_timeline_fail_rate_caption,
    universal_critique_timeline_fail_stage_caption,
    universal_critique_timeline_fail_stage_rows,
    universal_critique_timeline_operator_metrics,
    universal_critique_timeline_operator_metrics_caption,
    universal_critique_timeline_operator_metrics_export_filename_slug,
    universal_critique_timeline_operator_metrics_export_json,
    universal_critique_timeline_operator_metrics_table_rows,
    universal_critique_timeline_operator_metrics_table_rows_csv,
    universal_critique_timeline_stage_rows,
    universal_critique_timeline_stage_rows_csv,
    universal_critique_unanimous_gate_caption,
)


def test_universal_critique_from_timeline() -> None:
    body = {
        "universal_critique": {
            "stage_count": 2,
            "fail_count": 1,
            "stages": [
                {"stage_name": "planner.critique", "verdict": "PASS"},
                {"stage_name": "implementation.critique", "verdict": "FAIL"},
            ],
        },
    }
    uc = universal_critique_from_timeline(body)
    assert uc is not None
    assert uc["fail_count"] == 1
    assert universal_critique_from_timeline(None) is None


def test_universal_critique_timeline_stage_rows() -> None:
    summary = {
        "stages": [
            {
                "stage_name": "test_writer.critique",
                "verdict": "PASS",
                "failure_reason_code": None,
            },
        ],
    }
    rows = universal_critique_timeline_stage_rows(summary)
    assert len(rows) == 1
    assert rows[0]["Stage"] == "test_writer.critique"
    assert rows[0]["Verdict"] == "PASS"
    assert rows[0]["Failure reason"] == "—"
    assert universal_critique_timeline_stage_rows(None) == []


def test_universal_critique_timeline_stage_rows_csv() -> None:
    summary = {
        "stages": [
            {"stage_name": "planner.critique", "verdict": "PASS"},
            {
                "stage_name": "implementation.critique",
                "verdict": "FAIL",
                "failure_reason_code": "weak",
            },
        ],
    }
    rows = universal_critique_timeline_stage_rows(summary)
    csv_text = universal_critique_timeline_stage_rows_csv(rows)
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("Stage,")
    assert len(lines) == 3
    assert "planner.critique" in csv_text
    assert "implementation.critique" in csv_text
    assert universal_critique_timeline_stage_rows_csv([]) == ""


def test_universal_critique_timeline_stage_rows_supports_new_runtime_stages() -> None:
    summary = {
        "stages": [
            {"stage_name": "frontend_writer.critique", "verdict": "PASS"},
            {"stage_name": "module_integrator.critique", "verdict": "FAIL"},
        ],
    }
    rows = universal_critique_timeline_stage_rows(summary)
    assert len(rows) == 2
    assert rows[0]["Stage"] == "frontend_writer.critique"
    assert rows[1]["Stage"] == "module_integrator.critique"
    fail_rows = universal_critique_timeline_fail_stage_rows(summary)
    assert len(fail_rows) == 1
    assert fail_rows[0]["Stage"] == "module_integrator.critique"


def test_universal_critique_timeline_default_on_caption() -> None:
    cap = universal_critique_timeline_default_on_caption(
        {"default_enabled_effective": True},
    )
    assert cap is not None
    assert "default-on" in cap.lower()
    assert "enabled" in cap.lower()
    off = universal_critique_timeline_default_on_caption(
        {"default_enabled_effective": False},
    )
    assert off is not None
    assert "off" in off.lower()
    assert universal_critique_timeline_default_on_caption(None) is None


def test_universal_critique_timeline_fail_count_caption() -> None:
    cap = universal_critique_timeline_fail_count_caption(
        {"stage_count": 3, "fail_count": 1},
    )
    assert cap is not None
    assert "**1**" in cap
    assert "**3**" in cap
    assert universal_critique_timeline_fail_count_caption(None) is None
    assert universal_critique_timeline_fail_count_caption({"stage_count": 0}) is None


def test_universal_critique_timeline_summary_fail_rate_field() -> None:
    from agent_core.models import EventType
    from nimbusware_api.routes.runs import universal_critique_timeline_summary

    events = [
        {
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {"stage_name": "planner.critique", "verdict": "PASS"},
        },
        {
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {
                "stage_name": "implementation.critique",
                "verdict": "FAIL",
                "failure_reason_code": "x",
            },
        },
    ]
    summary = universal_critique_timeline_summary(events)
    assert summary is not None
    assert summary.get("fail_rate") == 0.5


def test_universal_critique_timeline_fail_rate_caption() -> None:
    cap = universal_critique_timeline_fail_rate_caption(
        {"stage_count": 5, "fail_count": 2},
    )
    assert cap is not None
    assert "**40.0%**" in cap
    assert "(2/5)" in cap
    assert universal_critique_timeline_fail_rate_caption(None) is None


def test_universal_critique_timeline_fail_stage_rows_mixed() -> None:
    summary = {
        "stages": [
            {"stage_name": "planner.critique", "verdict": "PASS"},
            {"stage_name": "implementation.critique", "verdict": "FAIL"},
            {"stage_name": "test_writer.critique", "verdict": "fail"},
        ],
    }
    rows = universal_critique_timeline_fail_stage_rows(summary)
    assert len(rows) == 2
    stages = {r["Stage"] for r in rows}
    assert stages == {"implementation.critique", "test_writer.critique"}


def test_universal_critique_timeline_fail_stage_rows_all_pass() -> None:
    summary = {
        "stages": [{"stage_name": "a.critique", "verdict": "PASS"}],
    }
    assert universal_critique_timeline_fail_stage_rows(summary) == []
    assert universal_critique_timeline_fail_stage_caption(summary) is None


def test_universal_critique_timeline_fail_stage_caption() -> None:
    summary = {
        "stages": [
            {"stage_name": "z.critique", "verdict": "FAIL"},
            {"stage_name": "a.critique", "verdict": "FAIL"},
        ],
    }
    cap = universal_critique_timeline_fail_stage_caption(summary)
    assert cap is not None
    assert cap == "FAIL critique stages: a.critique, z.critique."


def test_universal_critique_timeline_fail_stage_rows_skips_bad_verdict() -> None:
    summary = {
        "stages": [
            {"stage_name": "x.critique", "verdict": None},
            {"stage_name": "y.critique", "verdict": 1},
        ],
    }
    assert universal_critique_timeline_fail_stage_rows(summary) == []


def test_snapshot_from_compare_paste_bare_universal_critique() -> None:
    bare = {"stage_count": 2, "fail_count": 0, "stages": []}
    assert universal_critique_snapshot_from_compare_paste(bare) == bare


def test_snapshot_from_compare_paste_full_timeline() -> None:
    body = {
        "run_id": "00000000-0000-4000-8000-000000000001",
        "events": [],
        "universal_critique": {
            "stage_count": 1,
            "fail_count": 1,
            "stages": [{"stage_name": "x.critique", "verdict": "FAIL"}],
        },
    }
    assert universal_critique_snapshot_from_compare_paste(body) == body["universal_critique"]


def test_snapshot_from_compare_paste_timeline_events_only() -> None:
    assert universal_critique_snapshot_from_compare_paste({"events": []}) is None


def test_snapshot_from_compare_paste_timeline_null_block() -> None:
    assert (
        universal_critique_snapshot_from_compare_paste(
            {"events": [], "universal_critique": None},
        )
        is None
    )


def test_universal_critique_fail_stage_rows_csv_and_timeline_json() -> None:
    summary = {
        "stage_count": 2,
        "fail_count": 1,
        "stages": [
            {"stage_name": "planner.critique", "verdict": "PASS"},
            {
                "stage_name": "implementation.critique",
                "verdict": "FAIL",
                "failure_reason_code": "weak",
            },
        ],
    }
    fail_rows = universal_critique_timeline_fail_stage_rows(summary)
    csv_text = universal_critique_fail_stage_rows_csv(fail_rows)
    assert "implementation.critique" in csv_text
    assert csv_text.count("\n") >= 2  # header + one FAIL row
    assert "planner.critique" not in csv_text
    assert universal_critique_fail_stage_rows_csv([]) == ""
    all_pass = {"stages": [{"stage_name": "a.critique", "verdict": "PASS"}]}
    assert universal_critique_fail_stage_rows_csv(
        universal_critique_timeline_fail_stage_rows(all_pass),
    ) == ""
    body = json.loads(universal_critique_timeline_export_json(summary))
    assert body["fail_count"] == 1
    assert json.loads(universal_critique_timeline_export_json(None)) == {}
    assert universal_critique_timeline_export_filename_slug("R@un") == "r_un"


def test_universal_critique_timeline_operator_metrics_empty() -> None:
    m = universal_critique_timeline_operator_metrics(None)
    assert m["stage_count"] == 0
    assert m["fail_count"] == 0
    assert m["distinct_fail_stages"] == []
    assert universal_critique_timeline_operator_metrics_caption(m) is None


def test_universal_critique_timeline_operator_metrics_mixed_stages() -> None:
    summary = {
        "stage_count": 3,
        "fail_count": 2,
        "stages": [
            {"stage_name": "planner.critique", "verdict": "PASS"},
            {"stage_name": "implementation.critique", "verdict": "FAIL"},
            {"stage_name": "test_writer.critique", "verdict": "fail"},
        ],
    }
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["stage_count"] == 3
    assert m["fail_count"] == 2
    assert m["pass_count"] == 1
    assert m["other_verdict_count"] == 0
    assert m["distinct_fail_stages"] == [
        "implementation.critique",
        "test_writer.critique",
    ]
    rate_cap = universal_critique_timeline_fail_rate_caption(
        {"stage_count": 3, "fail_count": 2},
    )
    assert rate_cap is not None
    assert "66.7%" in rate_cap
    cap = universal_critique_timeline_operator_metrics_caption(m)
    assert cap is not None
    assert "**2**" in cap
    assert "**1** PASS" in cap
    rows = universal_critique_timeline_operator_metrics_table_rows(m)
    assert any(r["field"] == "Distinct FAIL stages" for r in rows)


def test_universal_critique_timeline_operator_metrics_fail_rate_from_summary() -> None:
    summary = {"stage_count": 4, "fail_count": 1, "fail_rate": 0.25, "stages": []}
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["fail_rate"] == 0.25
    rows = universal_critique_timeline_operator_metrics_table_rows(m)
    assert any(r["field"] == "FAIL rate" and "25.0%" in r["value"] for r in rows)


def test_universal_critique_timeline_operator_metrics_caption_other_verdict() -> None:
    summary = {
        "stages": [
            {"stage_name": "a.critique", "verdict": "FAIL"},
            {"stage_name": "b.critique", "verdict": "SKIP"},
        ],
    }
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["other_verdict_count"] == 1
    cap = universal_critique_timeline_operator_metrics_caption(m)
    assert cap is not None
    assert "other verdict" in cap


def test_universal_critique_timeline_operator_metrics_pass_count_from_summary() -> None:
    summary = {"stage_count": 4, "fail_count": 1, "pass_count": 3, "stages": []}
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["pass_count"] == 3
    rows = universal_critique_timeline_operator_metrics_table_rows(m)
    assert any(r["field"] == "PASS" and r["value"] == "3" for r in rows)


def test_universal_critique_timeline_operator_metrics_uses_distinct_fail_stages_fallback() -> None:
    summary = {"stage_count": 2, "fail_count": 1, "distinct_fail_stages": ["planner.critique"]}
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["distinct_fail_stages"] == ["planner.critique"]


def test_universal_critique_timeline_operator_metrics_export() -> None:
    summary = {
        "stages": [{"stage_name": "a.critique", "verdict": "FAIL"}],
    }
    m = universal_critique_timeline_operator_metrics(summary)
    parsed = json.loads(universal_critique_timeline_operator_metrics_export_json(m))
    assert parsed["fail_count"] == 1
    assert json.loads(universal_critique_timeline_operator_metrics_export_json(None)) == {}
    rows = universal_critique_timeline_operator_metrics_table_rows(m)
    csv_text = universal_critique_timeline_operator_metrics_table_rows_csv(rows)
    assert csv_text.startswith("field,value")
    assert universal_critique_timeline_operator_metrics_table_rows_csv([]) == ""
    assert (
        universal_critique_timeline_operator_metrics_export_filename_slug("R@un")
        == "r_un"
    )


def test_universal_critique_unanimous_gate_caption() -> None:
    assert (
        universal_critique_unanimous_gate_caption({"unanimous_gate_effective": True})
        is not None
    )
    assert (
        universal_critique_unanimous_gate_caption({"unanimous_gate_effective": False})
        is not None
    )


def test_universal_critique_timeline_operator_metrics_frozen_flags() -> None:
    summary = {
        "stage_count": 2,
        "fail_count": 0,
        "pass_count": 2,
        "default_enabled_effective": True,
        "unanimous_gate_effective": False,
        "stages": [],
    }
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["default_enabled_effective"] is True
    assert m["unanimous_gate_effective"] is False
    cap = universal_critique_timeline_operator_metrics_caption(m)
    assert cap is not None
    assert "default-on **enabled**" in cap
    assert "unanimous gate legacy" in cap
    rows = universal_critique_timeline_operator_metrics_table_rows(m)
    by = {r["field"]: r["value"] for r in rows}
    assert by["Default-on effective"] == "True"


def test_universal_critique_timeline_operator_metrics_critique_coverage_counts() -> None:
    summary = {
        "stage_count": 1,
        "fail_count": 0,
        "pass_count": 1,
        "critique_coverage": {
            "registry_producers": ["a", "b", "c"],
            "paired_producers": ["a", "b"],
            "unpaired_producers": ["c"],
        },
        "stages": [],
    }
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["registry_producer_count"] == 3
    assert m["paired_producer_count"] == 2
    assert m["unpaired_producer_count"] == 1
    cap = universal_critique_timeline_operator_metrics_caption(m)
    assert cap is not None
    assert "**3** registry producer" in cap


def test_universal_critique_timeline_operator_metrics_failing_critics_total() -> None:
    summary = {
        "stages": [
            {
                "stage_name": "implementation.critique",
                "verdict": "FAIL",
                "failing_critics": ["11111111-1111-4111-8111-111111111101"],
            },
            {
                "stage_name": "test_writer.critique",
                "verdict": "FAIL",
                "failing_critics": ["22222222-2222-4222-8222-222222222202", "333"],
            },
        ],
    }
    m = universal_critique_timeline_operator_metrics(summary)
    assert m["failing_critics_total_count"] == 3
    cap = universal_critique_timeline_operator_metrics_caption(m)
    assert cap is not None
    assert "**3** failing critic" in cap
