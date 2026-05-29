"""Console run escalated display helper (follow-on 39 §14 #19)."""

from __future__ import annotations

import json
from pathlib import Path

from nimbusware_console.run_escalated_display import (
    run_escalated_actor_without_notes_caption,
    run_escalated_delta_export_filename_slug,
    run_escalated_delta_export_json,
    run_escalated_delta_from_timeline,
    run_escalated_delta_operator_metrics,
    run_escalated_delta_operator_metrics_caption,
    run_escalated_delta_operator_metrics_export_filename_slug,
    run_escalated_delta_operator_metrics_export_json,
    run_escalated_delta_operator_metrics_table_rows,
    run_escalated_delta_operator_metrics_table_rows_csv,
    run_escalated_delta_summary_rows,
    run_escalated_delta_table_rows_csv,
    run_escalated_delta_transition_caption,
    run_escalated_event_id_caption,
    run_escalated_export_filename_slug,
    run_escalated_export_json,
    run_escalated_from_timeline,
    run_escalated_history_distinct_actors_caption,
    run_escalated_history_entry_count_caption,
    run_escalated_history_export_filename_slug,
    run_escalated_history_export_json,
    run_escalated_history_from_timeline,
    run_escalated_history_operator_metrics,
    run_escalated_history_operator_metrics_caption,
    run_escalated_history_operator_metrics_export_filename_slug,
    run_escalated_history_operator_metrics_export_json,
    run_escalated_history_operator_metrics_table_rows,
    run_escalated_history_operator_metrics_table_rows_csv,
    run_escalated_history_table_rows,
    run_escalated_history_table_rows_csv,
    run_escalated_notes_preview_caption,
    run_escalated_occurred_at_caption,
    run_escalated_operator_metrics,
    run_escalated_operator_metrics_caption,
    run_escalated_operator_metrics_export_json,
    run_escalated_operator_metrics_table_rows,
    run_escalated_operator_metrics_table_rows_csv,
    run_escalated_policy_cross_ref_caption,
    run_escalated_reason_summary_caption,
    run_escalated_summary_rows,
    run_escalated_summary_rows_csv,
)


def test_run_escalated_from_timeline_none_when_missing() -> None:
    assert run_escalated_from_timeline(None) is None
    assert run_escalated_from_timeline({}) is None
    assert run_escalated_from_timeline({"run_escalated": None}) is None
    assert run_escalated_from_timeline({"run_escalated": "x"}) is None


def test_run_escalated_from_timeline_returns_dict() -> None:
    body = {
        "events": [],
        "run_escalated": {
            "actor_id": "human",
            "reason_code": "THRESHOLD",
            "policy_snapshot_id": "snap-1",
            "notes": "note",
        },
    }
    esc = run_escalated_from_timeline(body)
    assert esc == {
        "actor_id": "human",
        "reason_code": "THRESHOLD",
        "policy_snapshot_id": "snap-1",
        "notes": "note",
    }


def test_run_escalated_notes_preview_caption() -> None:
    cap = run_escalated_notes_preview_caption({"notes": "  operator context  "})
    assert cap is not None
    assert "operator context" in cap
    long_note = "x" * 150
    cap_long = run_escalated_notes_preview_caption({"notes": long_note})
    assert cap_long is not None
    assert "…" in cap_long
    assert run_escalated_notes_preview_caption(None) is None
    assert run_escalated_notes_preview_caption({}) is None
    assert run_escalated_notes_preview_caption({"notes": ""}) is None


def test_run_escalated_event_id_caption() -> None:
    cap = run_escalated_event_id_caption(
        {"event_id": "ev-abc-123"},
    )
    assert cap is not None
    assert "ev-abc-123" in cap
    assert run_escalated_event_id_caption(None) is None
    assert run_escalated_event_id_caption({}) is None
    assert run_escalated_event_id_caption({"event_id": ""}) is None
    assert run_escalated_event_id_caption({"event_id": "   "}) is None


def test_run_escalated_occurred_at_caption() -> None:
    cap = run_escalated_occurred_at_caption(
        {"occurred_at": "2026-05-15T12:00:00Z"},
    )
    assert cap is not None
    assert "2026-05-15T12:00:00Z" in cap
    assert run_escalated_occurred_at_caption(None) is None
    assert run_escalated_occurred_at_caption({}) is None
    assert run_escalated_occurred_at_caption({"occurred_at": ""}) is None
    assert run_escalated_occurred_at_caption({"occurred_at": "   "}) is None


def test_run_escalated_reason_summary_caption() -> None:
    cap = run_escalated_reason_summary_caption(
        {
            "reason_code": "CUMULATIVE_FINDINGS",
            "actor_id": "system",
            "policy_snapshot_id": "snap-1",
        },
    )
    assert cap is not None
    assert "CUMULATIVE_FINDINGS" in cap
    assert "system" in cap
    assert "snap-1" in cap
    assert run_escalated_reason_summary_caption(None) is None
    assert run_escalated_reason_summary_caption({}) is None


def test_run_escalated_summary_rows_empty_for_none() -> None:
    assert run_escalated_summary_rows(None) == []


def test_run_escalated_summary_rows_ordered_fields() -> None:
    summary = {
        "actor_id": "system",
        "reason_code": "CUMULATIVE_FINDINGS",
        "policy_snapshot_id": None,
        "notes": "many findings",
        "event_id": "e1",
        "occurred_at": "2026-01-01T00:00:00Z",
    }
    rows = run_escalated_summary_rows(summary)
    labels = [r["field"] for r in rows]
    assert labels[0] == "Actor id"
    assert labels.index("Reason code") < labels.index("Event id")
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Actor id"] == "system"
    assert by_field["Reason code"] == "CUMULATIVE_FINDINGS"
    assert by_field["Policy snapshot id"] == "—"
    assert by_field["Notes"] == "many findings"
    assert by_field["Event id"] == "e1"
    assert by_field["Occurred at"] == "2026-01-01T00:00:00Z"


def test_run_escalated_policy_cross_ref_caption_none_without_snapshot() -> None:
    assert run_escalated_policy_cross_ref_caption(Path("."), None) is None
    assert run_escalated_policy_cross_ref_caption(Path("."), {}) is None
    assert (
        run_escalated_policy_cross_ref_caption(
            Path("."),
            {"reason_code": "x"},
        )
        is None
    )


def test_run_escalated_policy_cross_ref_caption_with_snapshot_no_repo(tmp_path: Path) -> None:
    cap = run_escalated_policy_cross_ref_caption(
        None,
        {"policy_snapshot_id": "snap-a"},
    )
    assert cap is not None
    assert "snap-a" in cap
    assert "configs/escalation/policy.yaml" in cap


def test_run_escalated_policy_cross_ref_caption_detects_policy_file(tmp_path: Path) -> None:
    pol = tmp_path / "configs" / "escalation"
    pol.mkdir(parents=True)
    (pol / "policy.yaml").write_text("{}", encoding="utf-8")
    cap = run_escalated_policy_cross_ref_caption(
        tmp_path,
        {"policy_snapshot_id": "snap-b"},
    )
    assert cap is not None and "present" in cap.lower() and "snap-b" in cap


def test_run_escalated_policy_cross_ref_caption_missing_policy_file(tmp_path: Path) -> None:
    cap = run_escalated_policy_cross_ref_caption(
        tmp_path,
        {"policy_snapshot_id": "snap-c"},
    )
    assert cap is not None and "missing" in cap.lower()


def test_run_escalated_actor_without_notes_caption_when_actor_and_empty_notes() -> None:
    cap = run_escalated_actor_without_notes_caption(
        {"actor_id": "system", "notes": ""},
    )
    assert cap is not None and "notes** are empty" in cap


def test_run_escalated_actor_without_notes_caption_when_notes_missing() -> None:
    cap = run_escalated_actor_without_notes_caption({"actor_id": "human"})
    assert cap is not None


def test_run_escalated_actor_without_notes_caption_none_when_notes_populated() -> None:
    assert (
        run_escalated_actor_without_notes_caption(
            {"actor_id": "system", "notes": "ok"},
        )
        is None
    )


def test_run_escalated_actor_without_notes_caption_none_without_actor() -> None:
    assert run_escalated_actor_without_notes_caption({"notes": ""}) is None
    assert run_escalated_actor_without_notes_caption({"actor_id": ""}) is None
    assert run_escalated_actor_without_notes_caption(None) is None


def test_run_escalated_actor_without_notes_caption_none_when_notes_non_string() -> None:
    assert (
        run_escalated_actor_without_notes_caption({"actor_id": "x", "notes": 1}) is None
    )


def test_run_escalated_history_from_timeline() -> None:
    body = {
        "run_escalated_history": [
            {"reason_code": "A", "actor_id": "human"},
            {"reason_code": "B", "actor_id": "system"},
        ],
    }
    hist = run_escalated_history_from_timeline(body)
    assert len(hist) == 2
    assert run_escalated_history_from_timeline(None) == []


def test_run_escalated_history_table_rows() -> None:
    hist = [
        {
            "occurred_at": "t1",
            "actor_id": "human",
            "reason_code": "THRESHOLD",
            "policy_snapshot_id": "snap-1",
            "notes": "n1",
            "event_id": "e1",
        },
    ]
    rows = run_escalated_history_table_rows(hist)
    assert rows[0]["#"] == "1"
    assert rows[0]["Reason"] == "THRESHOLD"
    assert rows[0]["Actor"] == "human"


def test_run_escalated_history_table_rows_csv_empty() -> None:
    assert run_escalated_history_table_rows_csv([]) == ""


def test_run_escalated_history_export_roundtrip() -> None:
    hist = [
        {
            "occurred_at": "t1",
            "actor_id": "human",
            "reason_code": "THRESHOLD",
            "policy_snapshot_id": "snap-1",
            "notes": "n1",
            "event_id": "e1",
        },
        {
            "occurred_at": "t2",
            "actor_id": "system",
            "reason_code": "X",
            "event_id": "e2",
        },
    ]
    rows = run_escalated_history_table_rows(hist)
    csv_text = run_escalated_history_table_rows_csv(rows)
    header = csv_text.splitlines()[0]
    assert header.split(",")[0] == "#"
    assert "Occurred at" in header
    assert "THRESHOLD" in csv_text
    parsed = json.loads(run_escalated_history_export_json(hist))
    assert len(parsed) == 2
    assert parsed[0]["reason_code"] == "THRESHOLD"
    assert parsed[1]["actor_id"] == "system"


def test_run_escalated_history_export_json_empty_list() -> None:
    assert json.loads(run_escalated_history_export_json([])) == []


def test_run_escalated_history_export_filename_slug() -> None:
    assert run_escalated_history_export_filename_slug("Ab c!12") == "ab_c_12"
    assert run_escalated_history_export_filename_slug("   ") == "run"


def test_run_escalated_history_entry_count_caption() -> None:
    assert run_escalated_history_entry_count_caption([{}, {}]) is not None
    assert run_escalated_history_entry_count_caption([]) is None


def test_run_escalated_history_distinct_actors_caption() -> None:
    hist = [
        {"actor_id": "alice"},
        {"actor_id": "bob"},
        {"actor_id": "alice"},
        {"actor_id": ""},
    ]
    m = run_escalated_history_operator_metrics(hist)
    cap = run_escalated_history_distinct_actors_caption(m)
    assert cap is not None
    assert "**2** distinct actors" in cap
    assert "**4** escalation" in cap
    empty_m = run_escalated_history_operator_metrics(
        [{"reason_code": "X"}, {"reason_code": "Y"}],
    )
    cap_zero = run_escalated_history_distinct_actors_caption(empty_m)
    assert cap_zero is not None
    assert "no distinct actor" in cap_zero
    assert run_escalated_history_distinct_actors_caption(None) is None
    assert run_escalated_history_distinct_actors_caption({"entry_count": 0}) is None


def test_run_escalated_delta_transition_caption() -> None:
    delta = {
        "reason_code_changed": True,
        "previous_reason_code": "THRESHOLD",
        "current_reason_code": "ANTI_DEADLOCK",
        "actor_id_changed": True,
        "previous_actor_id": "human",
        "current_actor_id": "system",
    }
    cap = run_escalated_delta_transition_caption(delta)
    assert cap is not None
    assert "THRESHOLD" in cap
    assert "ANTI_DEADLOCK" in cap
    assert run_escalated_delta_transition_caption(None) is None
    assert run_escalated_delta_transition_caption({}) is None


def test_run_escalated_delta_from_timeline() -> None:
    body = {"run_escalated_delta": {"reason_code_changed": True}}
    assert run_escalated_delta_from_timeline(body) == {"reason_code_changed": True}
    assert run_escalated_delta_from_timeline({}) is None


def test_run_escalated_delta_summary_rows_and_export() -> None:
    delta = {
        "previous_event_id": "p1",
        "current_event_id": "c1",
        "reason_code_changed": True,
        "actor_id_changed": True,
        "policy_snapshot_id_changed": False,
        "previous_reason_code": "THRESHOLD",
        "current_reason_code": "ANTI_DEADLOCK",
        "previous_actor_id": "human",
        "current_actor_id": "system",
    }
    rows = run_escalated_delta_summary_rows(delta)
    assert any(r["field"] == "Previous reason code" for r in rows)
    csv_text = run_escalated_delta_table_rows_csv(rows)
    assert "field,value" in csv_text.replace(" ", "") or "field" in csv_text.splitlines()[0]
    assert "THRESHOLD" in csv_text
    body = json.loads(run_escalated_delta_export_json(delta))
    assert body["current_reason_code"] == "ANTI_DEADLOCK"
    assert run_escalated_delta_summary_rows(None) == []
    assert run_escalated_delta_table_rows_csv([]) == ""
    assert json.loads(run_escalated_delta_export_json(None)) == {}
    assert json.loads(run_escalated_delta_export_json("x")) == {}
    assert run_escalated_delta_export_filename_slug("X@y") == "x_y"


def test_run_escalated_delta_operator_metrics_absent() -> None:
    m = run_escalated_delta_operator_metrics(None)
    assert m["present"] is False
    assert run_escalated_delta_operator_metrics_caption(m) is None
    assert run_escalated_delta_operator_metrics_table_rows(m) == []


def test_run_escalated_delta_operator_metrics_stable_caption() -> None:
    delta = {
        "previous_event_id": "ev-1",
        "current_event_id": "ev-2",
        "reason_code_changed": False,
        "actor_id_changed": False,
        "policy_snapshot_id_changed": False,
    }
    m = run_escalated_delta_operator_metrics(delta)
    cap = run_escalated_delta_operator_metrics_caption(m)
    assert cap is not None
    assert "no field changes" in cap
    assert "previous and current" in cap


def test_run_escalated_delta_operator_metrics_change_flags() -> None:
    delta = {
        "previous_event_id": "ev-1",
        "current_event_id": "ev-2",
        "reason_code_changed": True,
        "actor_id_changed": False,
        "policy_snapshot_id_changed": True,
    }
    m = run_escalated_delta_operator_metrics(delta)
    assert m["present"] is True
    assert m["has_previous"] is True
    assert m["has_current"] is True
    assert m["reason_code_changed"] is True
    assert m["actor_id_changed"] is False
    assert m["policy_snapshot_id_changed"] is True
    cap = run_escalated_delta_operator_metrics_caption(m)
    assert cap is not None
    assert "reason code" in cap
    assert "policy snapshot id" in cap
    rows = run_escalated_delta_operator_metrics_table_rows(m)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Reason code changed"] == "true"
    assert by_field["Actor id changed"] == "false"


def test_run_escalated_operator_metrics_empty() -> None:
    m = run_escalated_operator_metrics(None)
    assert m["notes_present"] is False
    assert run_escalated_operator_metrics_caption(m) is None
    assert run_escalated_operator_metrics_table_rows(m) == []


def test_run_escalated_operator_metrics_presence_flags() -> None:
    summary = {
        "actor_id": "human",
        "reason_code": "THRESHOLD",
        "policy_snapshot_id": "snap-1",
        "event_id": "ev-1",
        "notes": "operator note",
    }
    m = run_escalated_operator_metrics(summary)
    assert m["notes_present"] is True
    assert m["actor_id_present"] is True
    assert m["reason_code_present"] is True
    assert m["policy_snapshot_id_present"] is True
    assert m["event_id_present"] is True
    cap = run_escalated_operator_metrics_caption(m)
    assert cap is not None
    assert "reason code" in cap


def test_run_escalated_operator_metrics_severity_scalar() -> None:
    summary = {"severity": "critical", "reason_code": "THRESHOLD"}
    m = run_escalated_operator_metrics(summary)
    assert m["severity"] == "critical"
    cap = run_escalated_operator_metrics_caption(m)
    assert cap is not None
    assert "critical" in cap
    rows = run_escalated_operator_metrics_table_rows(m)
    assert any(r["field"] == "Severity" and r["value"] == "critical" for r in rows)


def test_run_escalated_operator_metrics_and_summary_export() -> None:
    summary = {"reason_code": "THRESHOLD", "actor_id": "human"}
    m = run_escalated_operator_metrics(summary)
    parsed = json.loads(run_escalated_operator_metrics_export_json(m))
    assert parsed["reason_code_present"] is True
    assert json.loads(run_escalated_operator_metrics_export_json(None)) == {}
    rows = run_escalated_operator_metrics_table_rows(m)
    csv_text = run_escalated_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    sum_rows = run_escalated_summary_rows(summary)
    sum_csv = run_escalated_summary_rows_csv(sum_rows)
    assert "THRESHOLD" in sum_csv
    assert json.loads(run_escalated_export_json(summary))["actor_id"] == "human"
    assert run_escalated_export_filename_slug("X@y") == "x_y"


def test_run_escalated_delta_operator_metrics_export() -> None:
    delta = {"reason_code_changed": True, "current_event_id": "ev-2"}
    m = run_escalated_delta_operator_metrics(delta)
    parsed = json.loads(run_escalated_delta_operator_metrics_export_json(m))
    assert parsed["present"] is True
    assert json.loads(run_escalated_delta_operator_metrics_export_json(None)) == {}
    rows = run_escalated_delta_operator_metrics_table_rows(m)
    csv_text = run_escalated_delta_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert run_escalated_delta_operator_metrics_table_rows_csv([]) == ""
    assert run_escalated_delta_operator_metrics_export_filename_slug("X@y") == "x_y"


def test_run_escalated_history_operator_metrics_empty() -> None:
    m = run_escalated_history_operator_metrics([])
    assert m["entry_count"] == 0
    assert run_escalated_history_operator_metrics_caption(m) is None
    assert run_escalated_history_operator_metrics_table_rows(m)


def test_run_escalated_history_operator_metrics_multi_entry() -> None:
    hist = [
        {
            "reason_code": "THRESHOLD",
            "actor_id": "human",
            "notes": "first",
        },
        {
            "reason_code": "ANTI_DEADLOCK",
            "actor_id": "system",
        },
        {
            "reason_code": "THRESHOLD",
            "actor_id": "human",
            "notes": "",
        },
    ]
    m = run_escalated_history_operator_metrics(hist)
    assert m["entry_count"] == 3
    assert m["distinct_reason_codes"] == 2
    assert m["distinct_actor_ids"] == 2
    assert m["notes_present_count"] == 1
    cap = run_escalated_history_operator_metrics_caption(m)
    assert cap is not None
    assert "**3**" in cap
    assert "distinct actor" in cap


def test_run_escalated_history_operator_metrics_export() -> None:
    hist = [{"reason_code": "A", "actor_id": "human", "notes": "n"}]
    m = run_escalated_history_operator_metrics(hist)
    parsed = json.loads(run_escalated_history_operator_metrics_export_json(m))
    assert parsed["entry_count"] == 1
    assert json.loads(run_escalated_history_operator_metrics_export_json(None)) == {}
    rows = run_escalated_history_operator_metrics_table_rows(m)
    csv_text = run_escalated_history_operator_metrics_table_rows_csv(rows)
    assert csv_text.startswith("field,value")
    assert run_escalated_history_operator_metrics_table_rows_csv([]) == ""
    assert run_escalated_history_operator_metrics_export_filename_slug("Ab c!") == "ab_c"
