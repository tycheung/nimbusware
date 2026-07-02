from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from nimbusware_console.workflow_explainers.escalation_suppress import (
    escalation_policy_export_filename_slug,
    escalation_policy_yaml_age_caption,
    escalation_policy_yaml_file_bytes_caption,
    escalation_policy_yaml_keys_all_export_json,
    escalation_policy_yaml_keys_all_table_rows,
    escalation_policy_yaml_keys_all_table_rows_csv,
    escalation_policy_yaml_mtime_caption,
    escalation_policy_yaml_top_level_kinds_export_json,
    escalation_policy_yaml_top_level_kinds_table_rows,
    escalation_policy_yaml_top_level_kinds_table_rows_csv,
    escalation_suppress_workflow_explainer_payload,
)
from nimbusware_env import find_repo_root
from unit.composite_repo_fixtures import write_workflow_profile
from unit.workflow_explainer_case_runner import (
    assert_payload_expectations,
    load_explainer_cases_yaml,
    run_and_assert_caption_case,
    run_and_assert_operator_metrics_case,
    run_explainer_payload_case,
)
from unit.workflow_explainer_helpers import write_escalation_policy

pytestmark = pytest.mark.slow

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "explainers"
_CASES: dict[str, Any] = load_explainer_cases_yaml(_FIXTURES / "escalation_suppress_cases.yaml")
_SLUG = str(_CASES["slug"])

_PAYLOAD_CASES = _CASES.get("payload_cases") or []
_CAPTION_CASES = _CASES.get("caption_cases") or []
_CAPTION_REPO_CASES = _CASES.get("caption_repo_cases") or []
_OPERATOR_METRICS_CASES = _CASES.get("operator_metrics_cases") or []


@pytest.mark.parametrize("case", _PAYLOAD_CASES, ids=lambda c: c["id"])
def test_escalation_suppress_payload_case(case: dict[str, Any], tmp_path: Path) -> None:
    payload = run_explainer_payload_case(_SLUG, case, tmp_path)
    assert_payload_expectations(payload, case)


@pytest.mark.parametrize("case", _CAPTION_CASES, ids=lambda c: c["id"])
def test_escalation_suppress_caption_case(case: dict[str, Any]) -> None:
    run_and_assert_caption_case(_SLUG, case)


@pytest.mark.parametrize("case", _CAPTION_REPO_CASES, ids=lambda c: c["id"])
def test_escalation_suppress_caption_repo_case(case: dict[str, Any], tmp_path: Path) -> None:
    run_and_assert_caption_case(_SLUG, case, tmp_path)


@pytest.mark.parametrize("case", _OPERATOR_METRICS_CASES, ids=lambda c: c["id"])
def test_escalation_suppress_operator_metrics_case(case: dict[str, Any]) -> None:
    run_and_assert_operator_metrics_case(_SLUG, case)


def test_explainer_escalation_policy_yaml_peek_when_present(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / "policy.yaml").write_text("version: 1\nfoo: {a: 1}\nbar: 2\n", encoding="utf-8")
    pol_path = pol_dir / "policy.yaml"
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    assert pl["escalation_policy_yaml_path_exists"] is True
    assert pl["escalation_policy_yaml_relpath"] is not None
    assert "escalation" in pl["escalation_policy_yaml_relpath"].replace("\\", "/")
    assert pl["escalation_policy_yaml_file_bytes"] == pol_path.stat().st_size
    assert pl["escalation_policy_yaml_top_level_key_count"] == 3
    full_keys = pl["escalation_policy_yaml_top_level_keys"]
    assert full_keys == ["bar", "foo", "version"]
    sample = pl["escalation_policy_yaml_top_level_keys_sample"]
    assert isinstance(sample, list) and len(sample) <= 12
    assert set(sample) <= {"bar", "foo", "version"}
    assert sample == full_keys
    kinds = pl["escalation_policy_yaml_top_level_kinds"]
    assert kinds == {"mapping": 1, "scalar": 2, "list": 0, "other": 0}
    assert sum(kinds.values()) == pl["escalation_policy_yaml_top_level_key_count"]
    assert pl["escalation_policy_yaml_load_error"] is None
    assert pl["escalation_policy_yaml_has_verification_mapping"] is False
    assert pl["escalation_policy_yaml_has_anti_deadlock_mapping"] is False
    assert pl["escalation_policy_yaml_max_retries_per_stage"] is None
    assert pl["escalation_policy_yaml_deadlock_escalation_after_minutes"] is None
    assert pl["escalation_policy_yaml_version"] == 1
    assert pl["workflow_yaml_top_level_version_int"] == 1
    assert pl["escalation_policy_yaml_anti_deadlock_enabled"] is None
    assert pl.get("escalation_policy_yaml_anti_deadlock_min_progress_events") is None


def test_explainer_escalation_policy_yaml_mtime_iso_when_present(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    before = datetime.now(timezone.utc)
    (pol_dir / "policy.yaml").write_text("version: 1\n", encoding="utf-8")
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    iso = pl["escalation_policy_yaml_mtime_iso"]
    assert isinstance(iso, str) and iso.endswith("Z")
    parsed = datetime.fromisoformat(iso[:-1] + "+00:00")
    assert parsed.tzinfo is not None
    after = datetime.now(timezone.utc)
    assert (parsed - before).total_seconds() >= -1
    assert (after - parsed).total_seconds() <= 300


def test_escalation_policy_yaml_age_seconds_past_mtime_within_tolerance(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    pol_path = pol_dir / "policy.yaml"
    pol_path.write_text("version: 1\n", encoding="utf-8")
    now_ts = datetime.now(timezone.utc).timestamp()
    target_age = 3600
    past_ts = now_ts - target_age
    os.utime(pol_path, (past_ts, past_ts))
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    age = pl["escalation_policy_yaml_age_seconds"]
    assert isinstance(age, int)
    assert abs(age - target_age) <= 5


def test_escalation_policy_yaml_age_seconds_future_mtime_returns_none(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    pol_path = pol_dir / "policy.yaml"
    pol_path.write_text("version: 1\n", encoding="utf-8")
    now_ts = datetime.now(timezone.utc).timestamp()
    future_ts = now_ts + 3600
    os.utime(pol_path, (future_ts, future_ts))
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    assert pl["escalation_policy_yaml_age_seconds"] is None


def test_escalation_policy_yaml_file_bytes_caption(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    write_escalation_policy(tmp_path, "version: 1\n")
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    cap = escalation_policy_yaml_file_bytes_caption(pl)
    assert cap is not None
    raw = pl.get("escalation_policy_yaml_file_bytes")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert escalation_policy_yaml_file_bytes_caption(None) is None
    assert (
        escalation_policy_yaml_file_bytes_caption({"escalation_policy_yaml_load_error": "bad"})
        is None
    )
    assert (
        escalation_policy_yaml_file_bytes_caption({"escalation_policy_yaml_path_exists": False})
        is None
    )


def test_escalation_policy_yaml_age_caption(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    write_escalation_policy(tmp_path, "version: 1\n")
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    cap = escalation_policy_yaml_age_caption(pl)
    assert cap is not None
    raw = pl.get("escalation_policy_yaml_age_seconds")
    assert isinstance(raw, int)
    assert f"**{raw}**" in cap
    assert escalation_policy_yaml_age_caption(None) is None
    assert escalation_policy_yaml_age_caption({"escalation_policy_yaml_load_error": "bad"}) is None


def test_escalation_policy_yaml_mtime_caption_freshly_written_caption(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    write_escalation_policy(tmp_path, "version: 1\n")
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    iso = pl["escalation_policy_yaml_mtime_iso"]
    age = pl["escalation_policy_yaml_age_seconds"]
    assert isinstance(iso, str) and iso
    assert isinstance(age, int) and age >= 0
    cap = escalation_policy_yaml_mtime_caption(pl)
    assert cap == f"Policy YAML last modified: {iso} ({age} seconds ago)."


def test_escalation_policy_yaml_mtime_caption_past_mtime_within_tolerance(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    pol_path = pol_dir / "policy.yaml"
    pol_path.write_text("version: 1\n", encoding="utf-8")
    now_ts = datetime.now(timezone.utc).timestamp()
    target_age = 3600
    past_ts = now_ts - target_age
    os.utime(pol_path, (past_ts, past_ts))
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    cap = escalation_policy_yaml_mtime_caption(pl)
    assert isinstance(cap, str)
    assert cap.startswith("Policy YAML last modified: ")
    age = pl["escalation_policy_yaml_age_seconds"]
    assert isinstance(age, int)
    assert abs(age - target_age) <= 5
    assert cap.endswith(f"({age} seconds ago).")


def test_escalation_policy_yaml_keys_all_table_rows_thirteen_keys(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True)
    yaml_body = "".join(f"key_{i}: {i}\n" for i in range(13))
    (pol_dir / "policy.yaml").write_text(yaml_body, encoding="utf-8")
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    assert pl["escalation_policy_yaml_top_level_key_count"] == 13
    full = pl["escalation_policy_yaml_top_level_keys"]
    sample = pl["escalation_policy_yaml_top_level_keys_sample"]
    assert len(full) == 13
    assert len(sample) == 12
    all_rows = escalation_policy_yaml_keys_all_table_rows(pl)
    sample_rows = escalation_policy_yaml_keys_all_table_rows(
        {"escalation_policy_yaml_top_level_keys_sample": sample}
    )
    assert len(all_rows) == 13
    assert len(sample_rows) == 12
    assert {r["policy_key"] for r in all_rows} == set(full)
    parsed = json.loads(escalation_policy_yaml_keys_all_export_json(all_rows))
    assert len(parsed) == 13
    csv_text = escalation_policy_yaml_keys_all_table_rows_csv(all_rows)
    assert csv_text.splitlines()[0] == "policy_key"


def test_escalation_policy_yaml_keys_all_table_rows_at_most_twelve(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    write_escalation_policy(tmp_path, "version: 1\nfoo: {a: 1}\nbar: 2\n")
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    all_rows = escalation_policy_yaml_keys_all_table_rows(pl)
    sample_only = {
        "escalation_policy_yaml_top_level_keys_sample": pl[
            "escalation_policy_yaml_top_level_keys_sample"
        ]
    }
    sample_rows = escalation_policy_yaml_keys_all_table_rows(sample_only)
    assert all_rows == sample_rows


def test_escalation_policy_yaml_keys_all_table_rows_real_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    pl = escalation_suppress_workflow_explainer_payload(root, workflow_profile="default")
    if not pl.get("escalation_policy_yaml_path_exists"):
        return
    if pl.get("escalation_policy_yaml_load_error"):
        return
    all_rows = escalation_policy_yaml_keys_all_table_rows(pl)
    count = pl.get("escalation_policy_yaml_top_level_key_count")
    assert isinstance(count, int)
    if count > 0:
        assert len(all_rows) == count


def test_escalation_policy_yaml_top_level_kinds_table_rows_mixed_policy(tmp_path: Path) -> None:
    write_workflow_profile(tmp_path, "wf", "version: 1\n")
    write_escalation_policy(tmp_path, "version: 1\nfoo: {a: 1}\nbar: 2\n")
    pl = escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile="wf")
    rows = escalation_policy_yaml_top_level_kinds_table_rows(pl)
    assert len(rows) == 4
    assert sum(int(r["count"]) for r in rows) == pl["escalation_policy_yaml_top_level_key_count"]
    assert {r["kind"] for r in rows} == {"mapping", "scalar", "list", "other"}
    parsed = json.loads(escalation_policy_yaml_top_level_kinds_export_json(rows))
    assert len(parsed) == 4
    csv_text = escalation_policy_yaml_top_level_kinds_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "kind,count"


def test_escalation_policy_yaml_top_level_kinds_table_rows_empty_cases() -> None:
    assert escalation_policy_yaml_top_level_kinds_table_rows({}) == []
    assert escalation_policy_yaml_top_level_kinds_table_rows_csv([]) == ""
    assert (
        escalation_policy_yaml_top_level_kinds_table_rows(
            {"escalation_policy_yaml_path_exists": False}
        )
        == []
    )
    assert (
        escalation_policy_yaml_top_level_kinds_table_rows(
            {
                "escalation_policy_yaml_path_exists": True,
                "escalation_policy_yaml_load_error": "boom",
            }
        )
        == []
    )
    assert (
        escalation_policy_yaml_top_level_kinds_table_rows(
            {
                "escalation_policy_yaml_path_exists": True,
                "escalation_policy_yaml_top_level_kinds": {
                    "mapping": 0,
                    "scalar": 0,
                    "list": 0,
                    "other": 0,
                },
            }
        )
        == []
    )


def test_escalation_policy_yaml_top_level_kinds_table_rows_real_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    pl = escalation_suppress_workflow_explainer_payload(root, workflow_profile="default")
    if not pl.get("escalation_policy_yaml_path_exists"):
        return
    if pl.get("escalation_policy_yaml_load_error"):
        return
    rows = escalation_policy_yaml_top_level_kinds_table_rows(pl)
    kinds = pl.get("escalation_policy_yaml_top_level_kinds")
    if not isinstance(kinds, dict):
        return
    if sum(kinds.values()) == 0:
        assert rows == []
        return
    assert len(rows) == 4
    assert {r["kind"]: int(r["count"]) for r in rows} == {
        k: int(v) for (k, v) in kinds.items() if isinstance(v, int)
    }


def test_escalation_policy_export_filename_slug() -> None:
    assert escalation_policy_export_filename_slug() == "escalation_policy"
