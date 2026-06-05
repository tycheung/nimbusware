from __future__ import annotations

import json
from pathlib import Path

import pytest

from nimbusware_console.integrator_threshold_explainer import (
    integrator_threshold_explainer_export_json,
    integrator_threshold_explainer_operator_metrics,
    integrator_threshold_explainer_operator_metrics_caption,
    integrator_threshold_explainer_operator_metrics_export_filename_slug,
    integrator_threshold_explainer_operator_metrics_export_json,
    integrator_threshold_explainer_operator_metrics_table_rows,
    integrator_threshold_explainer_operator_metrics_table_rows_csv,
    integrator_threshold_explainer_payload,
    integrator_threshold_explainer_table_rows,
    integrator_threshold_explainer_table_rows_csv,
    integrator_threshold_export_filename_slug,
    integrator_threshold_gate_emission_caption,
    integrator_threshold_min_score_agreement_caption,
    integrator_threshold_paste_parse_caption,
    integrator_threshold_project_tags_caption,
    integrator_threshold_thresholds_yaml_version_caption,
)


@pytest.fixture()
def repo_thresholds_only(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "integrator").mkdir(parents=True)
    (tmp_path / "configs" / "integrator" / "thresholds.yaml").write_text(
        "version: 1\nenabled: true\nmin_score_to_pass: 0.7\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def repo_workflow_and_thresholds(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "integrator").mkdir(parents=True)
    (tmp_path / "configs" / "integrator" / "thresholds.yaml").write_text(
        "version: 1\nenabled: false\nmin_score_to_pass: 0.9\n",
        encoding="utf-8",
    )
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "demo.yaml").write_text(
        "version: 1\n"
        "integrator_gate:\n"
        "  enabled: true\n"
        "  min_score_to_pass: 0.4\n"
        "  project_tags:\n"
        "    - auth\n"
        "    - rbac\n",
        encoding="utf-8",
    )
    return tmp_path


def test_integrator_threshold_thresholds_yaml_version_caption(
    repo_thresholds_only: Path,
) -> None:
    pl = integrator_threshold_explainer_payload(
        repo_thresholds_only,
        workflow_profile=None,
        pasted_yaml="",
    )
    cap = integrator_threshold_thresholds_yaml_version_caption(pl)
    assert cap is not None
    assert "**1**" in cap
    assert integrator_threshold_thresholds_yaml_version_caption(None) is None
    assert integrator_threshold_thresholds_yaml_version_caption({}) is None
    assert (
        integrator_threshold_thresholds_yaml_version_caption(
            {"thresholds_yaml": {"exists": False}},
        )
        is None
    )


def test_integrator_threshold_min_score_agreement_caption_agrees() -> None:
    cap = integrator_threshold_min_score_agreement_caption(
        {
            "pipeline_effective_min_score_to_pass": 0.4,
            "preview_effective_min_score_to_pass": 0.4,
            "min_score_agreement_note": "Preview and pipeline agree on min score.",
        },
    )
    assert cap is not None
    assert "agree" in cap


def test_integrator_threshold_min_score_agreement_caption_mismatch() -> None:
    cap = integrator_threshold_min_score_agreement_caption(
        {
            "pipeline_effective_min_score_to_pass": 0.4,
            "preview_effective_min_score_to_pass": 0.05,
        },
    )
    assert cap is not None
    assert "mismatch" in cap
    assert "0.05" in cap
    assert integrator_threshold_min_score_agreement_caption(None) is None


def test_integrator_threshold_gate_emission_caption_would_emit() -> None:
    cap = integrator_threshold_gate_emission_caption(
        {
            "gate_event_emission": {
                "would_emit_integrator_gate_event": True,
            },
        },
    )
    assert cap is not None
    assert "would emit" in cap


def test_integrator_threshold_gate_emission_caption_would_not_emit() -> None:
    cap = integrator_threshold_gate_emission_caption(
        {
            "gate_event_emission": {
                "would_emit_integrator_gate_event": False,
                "not_emit_reason": "NIMBUSWARE_EMIT_INTEGRATOR_GATE forces off",
            },
        },
    )
    assert cap is not None
    assert "would not emit" in cap
    assert "forces off" in cap


def test_integrator_threshold_gate_emission_caption_none_for_bad_payload() -> None:
    assert integrator_threshold_gate_emission_caption(None) is None
    assert integrator_threshold_gate_emission_caption({}) is None


def test_integrator_threshold_paste_parse_caption() -> None:
    cap = integrator_threshold_paste_parse_caption(
        {"paste_parse_errors": ["bad key", "expected mapping"]},
    )
    assert cap is not None
    assert "**2**" in cap
    assert "bad key" in cap
    many = [f"err{i}" for i in range(5)]
    cap_trunc = integrator_threshold_paste_parse_caption(
        {"paste_parse_errors": many},
    )
    assert cap_trunc is not None
    assert "+2 more" in cap_trunc
    assert integrator_threshold_paste_parse_caption(None) is None
    assert integrator_threshold_paste_parse_caption({}) is None
    assert integrator_threshold_paste_parse_caption({"paste_parse_errors": []}) is None


def test_pipeline_effective_prefers_workflow_over_thresholds_yaml(
    repo_workflow_and_thresholds: Path,
) -> None:
    out = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    assert out["pipeline_effective_min_score_to_pass"] == pytest.approx(0.4)
    assert out["preview_effective_min_score_to_pass"] == pytest.approx(0.4)
    assert out["thresholds_yaml"]["top_level_version_int"] == 1
    emit = out["gate_event_emission"]
    assert emit["would_emit_integrator_gate_event"] is True


def test_preview_min_score_paste_overrides_before_workflow(
    repo_workflow_and_thresholds: Path,
) -> None:
    out = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="min_score_to_pass: 0.05\n",
    )
    assert out["pipeline_effective_min_score_to_pass"] == pytest.approx(0.4)
    assert out["preview_effective_min_score_to_pass"] == pytest.approx(0.05)


def test_env_min_score_overrides_workflow(
    repo_workflow_and_thresholds: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS", "0.15")
    out = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    assert out["pipeline_effective_min_score_to_pass"] == pytest.approx(0.15)
    assert out["preview_effective_min_score_to_pass"] == pytest.approx(0.15)
    assert out["env_min_score_to_pass"]["overrides_yaml"] is True


def test_emit_forced_off(
    repo_workflow_and_thresholds: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", "0")
    out = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    assert out["gate_event_emission"]["would_emit_integrator_gate_event"] is False
    assert out["gate_event_emission"]["forces_off"] is True


def test_missing_thresholds_yaml_blocks_emit(tmp_path: Path) -> None:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "solo.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n",
        encoding="utf-8",
    )
    out = integrator_threshold_explainer_payload(
        tmp_path,
        workflow_profile="solo",
        pasted_yaml="",
    )
    assert out["thresholds_yaml"]["exists"] is False
    assert out["thresholds_yaml"].get("thresholds_yaml_file_bytes") is None
    assert out["gate_event_emission"]["would_emit_integrator_gate_event"] is False
    assert out["thresholds_yaml"].get("top_level_version_int") is None


def test_thresholds_disk_snapshot(repo_thresholds_only: Path) -> None:
    out = integrator_threshold_explainer_payload(
        repo_thresholds_only,
        workflow_profile=None,
        pasted_yaml="",
    )
    thr = out["thresholds_yaml"]
    pol_path = repo_thresholds_only / "configs" / "integrator" / "thresholds.yaml"
    assert thr["exists"] is True
    assert thr["thresholds_yaml_file_bytes"] == pol_path.stat().st_size
    assert thr["enabled"] is True
    assert thr["min_score_to_pass"] == pytest.approx(0.7)
    assert thr["top_level_version_int"] == 1


def test_workflow_integrator_gate_project_tags_list_length(
    repo_workflow_and_thresholds: Path,
) -> None:
    out = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    gate = out["workflow_integrator_gate"]
    assert gate["project_tags_list_length"] == 2


def test_integrator_threshold_project_tags_caption_none_for_bad_payload() -> None:
    assert integrator_threshold_project_tags_caption(None) is None
    assert integrator_threshold_project_tags_caption({}) is None
    assert (
        integrator_threshold_project_tags_caption(
            {"workflow_integrator_gate": {"block_present": False}},
        )
        is None
    )
    assert (
        integrator_threshold_project_tags_caption(
            {
                "workflow_integrator_gate": {
                    "block_present": True,
                    "project_tags_list_length": "two",
                },
            },
        )
        is None
    )


def test_integrator_threshold_project_tags_caption_zero_and_positive() -> None:
    zero = integrator_threshold_project_tags_caption(
        {
            "workflow_integrator_gate": {
                "block_present": True,
                "project_tags_list_length": 0,
            },
        },
    )
    assert zero is not None
    assert "**0**" in zero
    pos = integrator_threshold_project_tags_caption(
        {
            "workflow_integrator_gate": {
                "block_present": True,
                "project_tags_list_length": 2,
            },
        },
    )
    assert pos is not None
    assert "**2**" in pos
    assert "tags" in pos


def test_integrator_threshold_project_tags_caption_from_payload(
    repo_workflow_and_thresholds: Path,
) -> None:
    out = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    cap = integrator_threshold_project_tags_caption(out)
    assert cap is not None
    assert "**2**" in cap


def test_thresholds_yaml_top_level_version_non_int_returns_none(tmp_path: Path) -> None:
    (tmp_path / "configs" / "integrator").mkdir(parents=True)
    (tmp_path / "configs" / "integrator" / "thresholds.yaml").write_text(
        'version: "1"\nenabled: true\nmin_score_to_pass: 0.5\n',
        encoding="utf-8",
    )
    out = integrator_threshold_explainer_payload(tmp_path, workflow_profile=None, pasted_yaml="")
    assert out["thresholds_yaml"]["top_level_version_int"] is None


def test_integrator_threshold_explainer_table_rows_known_keys(
    repo_workflow_and_thresholds: Path,
) -> None:
    payload = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    rows = integrator_threshold_explainer_table_rows(payload)
    fields = {r["field"] for r in rows}
    assert "workflow_profile" in fields
    assert "pipeline_effective_min_score_to_pass" in fields
    assert len(rows) == len(payload)
    csv_text = integrator_threshold_explainer_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert integrator_threshold_explainer_table_rows({}) == []  # type: ignore[arg-type]
    assert integrator_threshold_explainer_table_rows_csv([]) == ""
    assert integrator_threshold_export_filename_slug() == "integrator_threshold"


def test_integrator_threshold_explainer_export_json_tmp_path(
    repo_thresholds_only: Path,
) -> None:
    payload = integrator_threshold_explainer_payload(
        repo_thresholds_only,
        workflow_profile=None,
        pasted_yaml="",
    )
    parsed = json.loads(integrator_threshold_explainer_export_json(payload))
    assert parsed == payload
    assert isinstance(parsed.get("thresholds_yaml"), dict)


def test_integrator_threshold_explainer_operator_metrics_project_tags_length(
    repo_workflow_and_thresholds: Path,
) -> None:
    payload = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    m = integrator_threshold_explainer_operator_metrics(payload)
    assert m["project_tags_list_length"] == 2
    cap = integrator_threshold_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "2" in cap


def test_integrator_threshold_explainer_operator_metrics_would_emit(
    repo_workflow_and_thresholds: Path,
) -> None:
    payload = integrator_threshold_explainer_payload(
        repo_workflow_and_thresholds,
        workflow_profile="demo",
        pasted_yaml="",
    )
    m = integrator_threshold_explainer_operator_metrics(payload)
    assert m["thresholds_yaml_exists"] is True
    assert m["min_scores_agree"] is True
    assert isinstance(m["min_score_pipeline"], float)
    assert m["min_score_pipeline"] == m["min_score_preview"]
    cap = integrator_threshold_explainer_operator_metrics_caption(m)
    assert cap is None or "emit" in cap.lower()


def test_integrator_threshold_explainer_operator_metrics_min_score_agree_caption() -> None:
    payload = {
        "pipeline_effective_min_score_to_pass": 0.55,
        "preview_effective_min_score_to_pass": 0.55,
        "gate_event_emission": {
            "would_emit_integrator_gate_event": True,
            "thresholds_yaml_exists": True,
            "forces_on": False,
            "forces_off": False,
        },
        "paste_parse_errors": [],
    }
    m = integrator_threshold_explainer_operator_metrics(payload)
    assert m["min_scores_agree"] is True
    cap = integrator_threshold_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "0.55" in cap
    assert "agree" in cap


def test_integrator_threshold_explainer_operator_metrics_min_score_mismatch() -> None:
    payload = {
        "pipeline_effective_min_score_to_pass": 0.4,
        "preview_effective_min_score_to_pass": 0.9,
        "gate_event_emission": {
            "would_emit_integrator_gate_event": False,
            "thresholds_yaml_exists": True,
            "forces_on": False,
            "forces_off": False,
        },
        "paste_parse_errors": [],
    }
    m = integrator_threshold_explainer_operator_metrics(payload)
    assert m["min_scores_agree"] is False
    cap = integrator_threshold_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "mismatch" in cap


def test_integrator_threshold_explainer_operator_metrics_paste_parse_error() -> None:
    m = integrator_threshold_explainer_operator_metrics(
        {"paste_parse_errors": ["bad yaml"]},
    )
    assert m["load_error_present"] is True
    cap = integrator_threshold_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "parse" in cap.lower()


def test_integrator_threshold_explainer_operator_metrics_env_forces_on_caption() -> None:
    m = integrator_threshold_explainer_operator_metrics(
        {
            "gate_event_emission": {
                "would_emit_integrator_gate_event": True,
                "thresholds_yaml_exists": True,
                "forces_on": True,
                "forces_off": False,
            },
        },
    )
    assert m["env_forces_on"] is True
    cap = integrator_threshold_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "forces gate on" in cap


def test_integrator_threshold_explainer_operator_metrics_export() -> None:
    m = integrator_threshold_explainer_operator_metrics(
        {
            "pipeline_effective_min_score_to_pass": 0.5,
            "preview_effective_min_score_to_pass": 0.5,
            "gate_event_emission": {"would_emit_integrator_gate_event": True},
        },
    )
    parsed = json.loads(integrator_threshold_explainer_operator_metrics_export_json(m))
    assert parsed["would_emit_gate_event"] is True
    assert json.loads(integrator_threshold_explainer_operator_metrics_export_json(None)) == {}
    rows = integrator_threshold_explainer_operator_metrics_table_rows(m)
    assert rows[0]["field"] == "Would emit gate event"
    csv_text = integrator_threshold_explainer_operator_metrics_table_rows_csv(rows)
    assert "Would emit gate event" in csv_text
    assert (
        integrator_threshold_explainer_operator_metrics_export_filename_slug()
        == "integrator_threshold_explainer_operator_metrics"
    )
