from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from console.prune_status_display import (
    SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH,
    load_prune_status,
    prune_scraper_artifact_prune_workflow_caption,
    prune_status_age_since_wrote_at_caption,
    prune_status_base_dir_caption,
    prune_status_dry_run_caption,
    prune_status_export_json,
    prune_status_freshness_caption,
    prune_status_max_age_days_caption,
    prune_status_object_store_prune_caption,
    prune_status_operator_metrics,
    prune_status_operator_metrics_caption,
    prune_status_operator_metrics_export_filename_slug,
    prune_status_operator_metrics_export_json,
    prune_status_operator_metrics_table_rows,
    prune_status_operator_metrics_table_rows_csv,
    prune_status_pattern_filter_caption,
    prune_status_pruned_outcome_caption,
    prune_status_retention_alert_caption,
    prune_status_retention_execution_caption,
    prune_status_retention_policy_caption,
    prune_status_schema_version_caption,
    prune_status_summary_rows,
    prune_status_summary_rows_csv,
    prune_status_wrote_at_caption,
    scraper_artifact_inventory_retention_alert_caption,
    scraper_artifact_inventory_retention_execution_caption,
    scraper_artifact_inventory_storage_caption,
)

_FULL_STATUS: dict[str, object] = {
    "schema_version": 1,
    "pruned": 3,
    "base": "/tmp/nimbusware_scraper",
    "dry_run": True,
    "max_age_days": 14,
    "include_patterns": ["*.bin"],
    "exclude_patterns": ["*.keep"],
    "include_pattern_count": 1,
    "exclude_pattern_count": 1,
    "wrote_at": "2026-05-12T18:00:00+00:00",
}


# load_prune_status


def test_load_prune_status_returns_none_when_path_is_none() -> None:
    assert load_prune_status(None) is None


def test_load_prune_status_returns_none_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "no_such_file.json"
    assert not missing.exists()
    assert load_prune_status(missing) is None


def test_load_prune_status_returns_none_for_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{this is not json", encoding="utf-8")
    assert load_prune_status(bad) is None


def test_load_prune_status_returns_none_for_non_dict_top_level(tmp_path: Path) -> None:
    listy = tmp_path / "list.json"
    listy.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert load_prune_status(listy) is None


def test_load_prune_status_parses_valid_payload(tmp_path: Path) -> None:
    good = tmp_path / "status.json"
    good.write_text(json.dumps(_FULL_STATUS), encoding="utf-8")
    parsed = load_prune_status(good)
    assert parsed == _FULL_STATUS


# prune_status_summary_rows


def test_prune_status_summary_rows_returns_empty_for_none() -> None:
    assert prune_status_summary_rows(None) == []
    assert prune_status_summary_rows({}) == []


def test_prune_status_summary_rows_renders_full_status_in_stable_order() -> None:
    rows = prune_status_summary_rows(_FULL_STATUS)
    assert [r["field"] for r in rows] == [
        "Summary schema version",
        "Pruned",
        "Base dir",
        "Dry run",
        "Max age (days)",
        "Include patterns",
        "Exclude patterns",
        "Include pattern count",
        "Exclude pattern count",
        "Wrote at (UTC)",
    ]
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Summary schema version"] == "1"
    assert by_field["Pruned"] == "3"
    assert by_field["Base dir"] == "/tmp/nimbusware_scraper"
    assert by_field["Dry run"] == "True"
    assert by_field["Max age (days)"] == "14"
    # Lists are JSON-stringified by the helper
    assert by_field["Include patterns"] == '["*.bin"]'
    assert by_field["Exclude patterns"] == '["*.keep"]'
    assert by_field["Include pattern count"] == "1"
    assert by_field["Exclude pattern count"] == "1"
    assert by_field["Wrote at (UTC)"] == "2026-05-12T18:00:00+00:00"


def test_prune_status_summary_rows_renders_none_values_as_em_dash() -> None:
    """``None`` ⇒ em-dash; absent keys are skipped (matches preflight_history_display)."""
    status: dict[str, object | None] = {
        "pruned": 0,
        "base": "/tmp/nimbusware_scraper",
        "dry_run": False,
        "include_patterns": None,
        "exclude_patterns": None,
        "wrote_at": "2026-05-12T18:00:00+00:00",
    }
    rows = prune_status_summary_rows(status)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Include patterns"] == "—"
    assert by_field["Exclude patterns"] == "—"


def test_prune_status_summary_rows_skips_absent_keys() -> None:
    """Keys absent from ``status`` should NOT appear in the rendered rows."""
    rows = prune_status_summary_rows({"pruned": 1})
    assert [r["field"] for r in rows] == ["Pruned"]


def test_prune_status_export_json_and_summary_rows_csv() -> None:
    parsed = json.loads(prune_status_export_json(_FULL_STATUS))
    assert parsed == _FULL_STATUS
    assert json.loads(prune_status_export_json(None)) == {}
    assert prune_status_export_json("x") == "{}"
    rows = prune_status_summary_rows(_FULL_STATUS)
    csv_text = prune_status_summary_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert len(csv_text.splitlines()) >= 3
    assert prune_status_summary_rows_csv([]) == ""


# prune_status_age_since_wrote_at_caption


def test_age_since_wrote_at_caption_hours_and_minutes() -> None:
    wrote = datetime(2026, 5, 12, 18, 0, tzinfo=timezone.utc)
    cap = prune_status_age_since_wrote_at_caption(
        {"wrote_at": wrote.isoformat()},
        now=wrote + timedelta(hours=2, minutes=15),
    )
    assert cap is not None
    assert "2h 15m" in cap
    assert "8100s" in cap


def test_age_since_wrote_at_caption_minutes_only() -> None:
    wrote = datetime(2026, 5, 12, 18, 0, tzinfo=timezone.utc)
    cap = prune_status_age_since_wrote_at_caption(
        {"wrote_at": wrote.isoformat()},
        now=wrote + timedelta(minutes=7),
    )
    assert cap is not None
    assert "7m" in cap
    assert "420s" in cap


def test_age_since_wrote_at_caption_none_when_missing_status_or_wrote_at() -> None:
    assert prune_status_age_since_wrote_at_caption(None) is None
    assert prune_status_age_since_wrote_at_caption({"pruned": 1}) is None
    assert prune_status_age_since_wrote_at_caption({"wrote_at": "bad"}) is None


# prune_status_freshness_caption


_WROTE_AT = datetime(2026, 5, 12, 18, 0, tzinfo=timezone.utc)
_FRESH = {"wrote_at": _WROTE_AT.isoformat()}


def test_freshness_caption_no_status_points_at_summary_path() -> None:
    caption = prune_status_freshness_caption(None)
    assert "No prune status file yet" in caption
    assert "--summary-path" in caption
    assert "NIMBUSWARE_PRUNE_STATUS_PATH" in caption


def test_freshness_caption_missing_wrote_at() -> None:
    assert (
        prune_status_freshness_caption({"pruned": 1})
        == "Status file present but missing wrote_at timestamp."
    )


def test_freshness_caption_unparseable_wrote_at() -> None:
    assert (
        prune_status_freshness_caption({"wrote_at": "not-a-timestamp"})
        == "Status file present but missing wrote_at timestamp."
    )


def test_freshness_caption_seconds_minutes_hours() -> None:
    caption_seconds = prune_status_freshness_caption(
        _FRESH,
        now=_WROTE_AT + timedelta(seconds=12),
    )
    assert caption_seconds == "Last updated 12 seconds ago."

    caption_minute = prune_status_freshness_caption(
        _FRESH,
        now=_WROTE_AT + timedelta(seconds=61),
    )
    assert caption_minute == "Last updated 1 minute ago."

    caption_minutes = prune_status_freshness_caption(
        _FRESH,
        now=_WROTE_AT + timedelta(minutes=42),
    )
    assert caption_minutes == "Last updated 42 minutes ago."

    caption_hours = prune_status_freshness_caption(
        _FRESH,
        now=_WROTE_AT + timedelta(hours=3),
    )
    assert caption_hours == "Last updated 3 hours ago."


def test_freshness_caption_marks_stale_after_24h() -> None:
    fresh_24h = prune_status_freshness_caption(
        _FRESH,
        now=_WROTE_AT + timedelta(hours=23, minutes=59),
    )
    assert "Stale" not in fresh_24h

    stale = prune_status_freshness_caption(
        _FRESH,
        now=_WROTE_AT + timedelta(hours=25),
    )
    assert "Last updated 25 hours ago." in stale
    assert "Stale (>24h)." in stale


def test_prune_status_pruned_outcome_caption() -> None:
    cap = prune_status_pruned_outcome_caption(
        {"pruned": 3, "dry_run": True},
    )
    assert cap is not None
    assert "**3**" in cap
    assert "dry_run=**yes**" in cap
    cap_zero = prune_status_pruned_outcome_caption(
        {"pruned": 0, "dry_run": False},
    )
    assert cap_zero is not None
    assert "**0**" in cap_zero
    assert "dry_run=**no**" in cap_zero
    cap_one = prune_status_pruned_outcome_caption({"pruned": 1, "dry_run": False})
    assert cap_one is not None
    assert "path removed" in cap_one
    assert prune_status_pruned_outcome_caption(None) is None
    assert prune_status_pruned_outcome_caption({}) is None
    assert prune_status_pruned_outcome_caption({"dry_run": True}) is None
    assert prune_status_pruned_outcome_caption({"pruned": True, "dry_run": False}) is None


def test_prune_status_base_dir_caption() -> None:
    cap = prune_status_base_dir_caption({"base": "/tmp/nimbusware_scraper"})
    assert cap is not None
    assert "/tmp/nimbusware_scraper" in cap
    assert prune_status_base_dir_caption(None) is None
    assert prune_status_base_dir_caption({}) is None
    assert prune_status_base_dir_caption({"base": ""}) is None
    assert prune_status_base_dir_caption({"base": "   "}) is None
    assert prune_status_base_dir_caption({"base": 42}) is None


def test_prune_status_max_age_days_caption() -> None:
    cap = prune_status_max_age_days_caption({"max_age_days": 14})
    assert cap is not None
    assert "**14**" in cap
    assert "days" in cap
    cap_one = prune_status_max_age_days_caption({"max_age_days": 1})
    assert cap_one is not None
    assert "day" in cap_one
    assert prune_status_max_age_days_caption(None) is None
    assert prune_status_max_age_days_caption({}) is None
    assert prune_status_max_age_days_caption({"max_age_days": 0}) is None
    assert prune_status_max_age_days_caption({"max_age_days": True}) is None


def test_prune_status_retention_policy_caption() -> None:
    cap = prune_status_retention_policy_caption({"max_age_days": 14})
    assert cap == "Retention policy: remove artifacts older than **14** days."
    assert prune_status_retention_policy_caption({"max_age_days": 1}) == (
        "Retention policy: remove artifacts older than **1** day."
    )
    assert prune_status_retention_policy_caption(None) is None


def test_prune_status_pattern_filter_caption() -> None:
    cap = prune_status_pattern_filter_caption(_FULL_STATUS)
    assert cap is not None
    assert "1 include" in cap
    assert "1 exclude" in cap
    cap_lists = prune_status_pattern_filter_caption(
        {"include_patterns": ["a", "b"], "exclude_patterns": []},
    )
    assert cap_lists is not None
    assert "2 include" in cap_lists
    assert prune_status_pattern_filter_caption(None) is None
    assert prune_status_pattern_filter_caption({}) is None


def test_prune_scraper_artifact_prune_workflow_caption() -> None:
    cap = prune_scraper_artifact_prune_workflow_caption()
    assert SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH in cap
    assert "scraper_artifact_prune" in cap
    assert SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH == ".github/workflows/scraper_artifact_prune.yml"


def test_prune_status_dry_run_caption() -> None:
    cap_yes = prune_status_dry_run_caption({"dry_run": True})
    assert cap_yes is not None
    assert "**yes**" in cap_yes
    cap_no = prune_status_dry_run_caption({"dry_run": False})
    assert cap_no is not None
    assert "**no**" in cap_no
    assert prune_status_dry_run_caption(None) is None
    assert prune_status_dry_run_caption({}) is None
    assert prune_status_dry_run_caption({"dry_run": "yes"}) is None


def test_prune_status_wrote_at_caption() -> None:
    cap = prune_status_wrote_at_caption({"wrote_at": "2026-05-15T12:00:00Z"})
    assert cap is not None
    assert "2026-05-15T12:00:00Z" in cap
    assert prune_status_wrote_at_caption(None) is None
    assert prune_status_wrote_at_caption({}) is None
    assert prune_status_wrote_at_caption({"wrote_at": ""}) is None
    assert prune_status_wrote_at_caption({"wrote_at": "   "}) is None


def test_prune_status_schema_version_caption() -> None:
    cap = prune_status_schema_version_caption(_FULL_STATUS)
    assert cap is not None
    assert "**1**" in cap
    assert prune_status_schema_version_caption(None) is None
    assert prune_status_schema_version_caption({}) is None
    assert prune_status_schema_version_caption({"schema_version": 0}) is None
    assert prune_status_schema_version_caption({"schema_version": True}) is None


def test_freshness_caption_naive_wrote_at_treated_as_utc() -> None:
    """A naive ISO string should not raise and should be treated as UTC."""
    caption = prune_status_freshness_caption(
        {"wrote_at": "2026-05-12T18:00:00"},
        now=datetime(2026, 5, 12, 18, 30, tzinfo=timezone.utc),
    )
    assert caption == "Last updated 30 minutes ago."


def test_prune_status_operator_metrics_empty() -> None:
    m = prune_status_operator_metrics(None)
    assert m["pruned"] is None
    assert m["is_stale"] is False
    assert prune_status_operator_metrics_caption(m) is None
    assert prune_status_operator_metrics_table_rows(m) == []


def test_prune_status_operator_metrics_live_fixture() -> None:
    now = datetime(2026, 5, 12, 18, 0, tzinfo=timezone.utc)
    status = dict(_FULL_STATUS)
    m = prune_status_operator_metrics(status, now=now)
    assert m["pruned"] == 3
    assert m["dry_run"] is True
    assert m["max_age_days"] == 14
    assert m["include_pattern_count"] == 1
    assert m["exclude_pattern_count"] == 1
    assert m["schema_version"] == 1
    assert m["is_stale"] is False
    cap = prune_status_operator_metrics_caption(m)
    assert cap is not None
    assert "3" in cap
    rows = prune_status_operator_metrics_table_rows(m)
    assert any(r["field"] == "Dry run" for r in rows)


def test_prune_status_operator_metrics_stale() -> None:
    old = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
    now = datetime(2026, 5, 12, 18, 0, tzinfo=timezone.utc)
    m = prune_status_operator_metrics(
        {"pruned": 1, "wrote_at": old.isoformat()},
        now=now,
    )
    assert m["is_stale"] is True
    rows = prune_status_operator_metrics_table_rows(m)
    assert any(r["field"] == "Stale (>24h)" for r in rows)


def test_prune_status_retention_execution_and_object_store_captions() -> None:
    cap_mode = prune_status_retention_execution_caption(
        {"retention_execution_mode": "local_with_object_store_mirror"},
    )
    assert cap_mode is not None
    assert "local_with_object_store_mirror" in cap_mode
    cap_os = prune_status_object_store_prune_caption(
        {
            "object_store_attempted": 2,
            "object_store_removed": 1,
            "object_store_failed": 1,
            "object_store_last_error": "http_500",
        },
    )
    assert cap_os is not None
    assert "attempted=2" in cap_os
    assert "failed=1" in cap_os
    assert "last_error=http_500" in cap_os
    cap_os_lifecycle = prune_status_object_store_prune_caption(
        {
            "object_store_attempted": 2,
            "object_store_removed": 1,
            "object_store_failed": 1,
            "retention_lifecycle_state": "mirror_degraded",
        },
    )
    assert cap_os_lifecycle is not None
    assert "lifecycle_state=mirror_degraded" in cap_os_lifecycle


def test_prune_status_operator_metrics_retention_alert_fields() -> None:
    m = prune_status_operator_metrics(
        {
            "pruned": 2,
            "dry_run": False,
            "retention_alert_level": "stale_high",
            "retention_stale_file_count": 42,
            "retention_stale_bytes": 9000,
            "retention_lifecycle_state": "stale_pending",
        },
    )
    assert m["retention_alert_level"] == "stale_high"
    assert m["retention_stale_file_count"] == 42
    assert m["retention_stale_bytes"] == 9000
    assert m["retention_lifecycle_state"] == "stale_pending"
    cap = prune_status_operator_metrics_caption(m)
    assert cap is not None
    assert "retention_alert=stale_high" in cap
    assert "lifecycle=stale_pending" in cap
    rows = prune_status_operator_metrics_table_rows(m)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["Retention alert level"] == "stale_high"
    assert by_field["Retention stale files"] == "42"
    assert by_field["Retention lifecycle"] == "stale_pending"


def test_prune_status_retention_alert_caption() -> None:
    cap = prune_status_retention_alert_caption(
        {
            "retention_alert_level": "stale_high",
            "retention_stale_file_count": 150,
            "retention_stale_bytes": 1000,
        },
    )
    assert cap is not None
    assert "level=stale_high" in cap
    assert "stale_files=150" in cap
    cap_exec = prune_status_retention_alert_caption(
        {
            "retention_alert_level": "stale_present",
            "retention_execution_mode": "local_with_object_store_mirror",
            "retention_lifecycle_state": "stale_pending",
        },
    )
    assert cap_exec is not None
    assert "execution_mode=local_with_object_store_mirror" in cap_exec
    assert "lifecycle=stale_pending" in cap_exec
    assert prune_status_retention_alert_caption({"retention_alert_level": "none"}) is None


def test_scraper_artifact_inventory_retention_alert_caption() -> None:
    cap = scraper_artifact_inventory_retention_alert_caption(
        {
            "retention_alert_level": "stale_high",
            "retention_stale_file_count": 50,
            "retention_stale_bytes": 999,
        },
    )
    assert cap is not None
    assert "stale_high" in cap
    cap_exec = scraper_artifact_inventory_retention_alert_caption(
        {
            "retention_alert_level": "stale_present",
            "retention_execution_mode": "local_only",
            "retention_stale_file_count": 1,
        },
    )
    assert cap_exec is not None
    assert "execution_mode=local_only" in cap_exec


def test_scraper_artifact_inventory_retention_execution_caption() -> None:
    cap = scraper_artifact_inventory_retention_execution_caption(
        {"retention_execution_mode": "local_with_object_store_mirror"},
    )
    assert cap is not None
    assert "local_with_object_store_mirror" in cap
    assert scraper_artifact_inventory_retention_execution_caption(None) is None


def test_scraper_artifact_inventory_storage_caption() -> None:
    cap = scraper_artifact_inventory_storage_caption(
        {
            "storage_backend": "object_store_ready",
            "object_store_configured": True,
            "object_store_ready": True,
            "object_store_prune_requested": True,
            "object_store_prune_effective": True,
            "object_store_timeout_seconds": 15,
            "object_store_delete_max_attempts": 2,
        },
    )
    assert cap is not None
    assert "backend=object_store_ready" in cap
    assert "ready=True" in cap
    assert "prune_requested=True" in cap
    assert "prune_effective=True" in cap
    assert "timeout_s=15" in cap
    assert "delete_attempts=2" in cap


def test_prune_status_operator_metrics_export() -> None:
    m = prune_status_operator_metrics(_FULL_STATUS)
    parsed = json.loads(prune_status_operator_metrics_export_json(m))
    assert parsed["pruned"] == 3
    assert json.loads(prune_status_operator_metrics_export_json(None)) == {}
    rows = prune_status_operator_metrics_table_rows(m)
    csv_text = prune_status_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert prune_status_operator_metrics_table_rows_csv([]) == ""
    assert prune_status_operator_metrics_export_filename_slug() == "prune_status_operator_metrics"
