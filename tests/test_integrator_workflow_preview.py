"""Unit tests for integrator workflow preview helpers (fo131 / §14 #13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_console.integrator_workflow_preview import (
    integrator_preview_payload,
    list_workflow_profile_keys,
    parse_integrator_gate_yaml_fragment,
    parse_synthetic_tags_json,
    validate_integrator_gate_block,
)

ROOT = Path(__file__).resolve().parents[1]


def test_list_workflow_profile_keys_includes_default() -> None:
    keys = list_workflow_profile_keys(ROOT)
    assert "default" in keys


def test_parse_integrator_gate_nested_key() -> None:
    text = "integrator_gate:\n  enabled: true\n  min_score_to_pass: 0.5\n"
    block, errs = parse_integrator_gate_yaml_fragment(text)
    assert not errs
    assert block is not None
    assert block.get("enabled") is True
    assert block.get("min_score_to_pass") == 0.5


def test_parse_integrator_gate_flat_mapping() -> None:
    text = "enabled: false\nmin_score_to_pass: 0.2\n"
    block, errs = parse_integrator_gate_yaml_fragment(text)
    assert not errs
    assert block is not None
    assert block.get("enabled") is False


def test_parse_integrator_gate_invalid_root() -> None:
    block, errs = parse_integrator_gate_yaml_fragment("[]")
    assert block is None
    assert errs


def test_validate_min_score_out_of_range() -> None:
    errs = validate_integrator_gate_block({"min_score_to_pass": 2.0})
    assert any("0 and 1" in e for e in errs)


def test_validate_project_tags_not_list() -> None:
    errs = validate_integrator_gate_block({"project_tags": "x"})
    assert any("list" in e for e in errs)


def test_parse_synthetic_tags_json_happy() -> None:
    tags, errs = parse_synthetic_tags_json('["auth", "rbac"]')
    assert not errs
    assert tags == ["auth", "rbac"]


def test_parse_synthetic_tags_json_invalid() -> None:
    tags, errs = parse_synthetic_tags_json("{")
    assert tags is None
    assert errs


@pytest.fixture()
def mini_integrator_repo(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "integrator").mkdir(parents=True)
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "demo.yaml").write_text(
        "version: 1\n"
        "integrator_gate:\n"
        "  enabled: true\n"
        "  min_score_to_pass: 0.5\n"
        "  project_tags: [auth]\n",
        encoding="utf-8",
    )
    (tmp_path / "configs" / "integrator" / "thresholds.yaml").write_text(
        "version: 1\nenabled: false\nmin_score_to_pass: 0.9\n",
        encoding="utf-8",
    )
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "bundles:\n"
        "  - id: demo-bundle\n"
        "    tags: [auth, billing]\n",
        encoding="utf-8",
    )
    return tmp_path


def test_integrator_preview_payload_uses_workflow_tags(mini_integrator_repo: Path) -> None:
    out = integrator_preview_payload(
        mini_integrator_repo,
        workflow_profile="demo",
        pasted_yaml="",
        bundle_id="demo-bundle",
        synthetic_tags_json="[]",
    )
    assert not out["validation_errors"]
    assert out["workflow_profile"] == "demo"
    assert out["disk_integrator_gate_enabled"] is True
    assert out["effective_min_score_to_pass"] == 0.5
    assert out["score_fit"] == pytest.approx(1.0 / 2.0)
    assert out["passes_gate"] is (out["score_fit"] >= out["effective_min_score_to_pass"])


def test_integrator_preview_pasted_min_score_overrides(mini_integrator_repo: Path) -> None:
    out = integrator_preview_payload(
        mini_integrator_repo,
        workflow_profile="demo",
        pasted_yaml="min_score_to_pass: 0.1\n",
        bundle_id="demo-bundle",
        synthetic_tags_json="[]",
    )
    assert out["effective_min_score_to_pass"] == pytest.approx(0.1)
    assert out["passes_gate"] is True
