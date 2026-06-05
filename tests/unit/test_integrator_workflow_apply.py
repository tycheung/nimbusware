from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.merge import load_yaml
from nimbusware_orchestrator.workflow_agent_evaluator import parse_agent_evaluator_workflow_block
from nimbusware_console.integrator_workflow_apply import (
    ALLOW_WORKFLOW_YAML_WRITE_ENV,
    apply_agent_evaluator_yaml,
    apply_integrator_gate_yaml,
    merge_agent_evaluator_into_profile_document,
    merge_integrator_gate_into_profile_document,
    prepare_agent_evaluator_apply,
    prepare_integrator_gate_apply,
    workflow_yaml_write_enabled,
)


@pytest.fixture()
def mini_workflow_repo(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "demo.yaml").write_text(
        "version: 99\n"
        "other_section:\n"
        "  foo: bar\n"
        "integrator_gate:\n"
        "  enabled: true\n"
        "  min_score_to_pass: 0.5\n"
        "  project_tags: [auth]\n"
        "agent_evaluator:\n"
        "  enabled: false\n"
        "  persona_id: legacy-ae\n",
        encoding="utf-8",
    )
    return tmp_path


def test_merge_integrator_gate_preserves_other_top_level_keys(
    mini_workflow_repo: Path,
) -> None:
    merged, before, after = merge_integrator_gate_into_profile_document(
        mini_workflow_repo,
        "demo",
        {"enabled": False, "min_score_to_pass": 0.1, "project_tags": ["x"]},
    )
    assert merged["version"] == 99
    assert merged["other_section"] == {"foo": "bar"}
    assert merged["integrator_gate"]["enabled"] is False
    assert merged["integrator_gate"]["min_score_to_pass"] == pytest.approx(0.1)
    assert merged["integrator_gate"]["project_tags"] == ["x"]
    assert before is not None and before["enabled"] is True
    assert after == merged["integrator_gate"]


def test_prepare_integrator_gate_apply_empty_paste(mini_workflow_repo: Path) -> None:
    merged, _b, _a, errs = prepare_integrator_gate_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="   \n",
    )
    assert merged is None
    assert any("empty" in e.lower() for e in errs)


def test_prepare_integrator_gate_apply_invalid_score(mini_workflow_repo: Path) -> None:
    merged, _b, _a, errs = prepare_integrator_gate_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="min_score_to_pass: 9\n",
    )
    assert merged is None
    assert errs


def test_apply_integrator_gate_yaml_requires_env(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, raising=False)
    ok, _doc, errs = apply_integrator_gate_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="min_score_to_pass: 0.2\n",
        confirm_profile_stem="demo",
    )
    assert ok is False
    assert any(ALLOW_WORKFLOW_YAML_WRITE_ENV in e for e in errs)


def test_apply_integrator_gate_yaml_confirmation_mismatch(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, "1")
    ok, _doc, errs = apply_integrator_gate_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="min_score_to_pass: 0.2\n",
        confirm_profile_stem="not-demo",
    )
    assert ok is False
    assert any("confirmation" in e.lower() for e in errs)


def test_apply_integrator_gate_yaml_writes_atomically(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, "1")
    wf_path = mini_workflow_repo / "configs" / "workflows" / "demo.yaml"
    ok, merged, errs = apply_integrator_gate_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="min_score_to_pass: 0.01\n",
        confirm_profile_stem="demo",
    )
    assert ok
    assert not errs
    assert merged is not None
    assert merged["integrator_gate"]["min_score_to_pass"] == pytest.approx(0.01)
    disk = load_yaml(wf_path)
    assert disk["version"] == 99
    assert disk["other_section"] == {"foo": "bar"}
    assert disk["integrator_gate"]["min_score_to_pass"] == pytest.approx(0.01)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("", False),
    ],
)
def test_workflow_yaml_write_enabled_truth_table(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    expected: bool,
) -> None:
    if raw:
        monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, raw)
    else:
        monkeypatch.delenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, raising=False)
    assert workflow_yaml_write_enabled() is expected


def test_merge_agent_evaluator_preserves_integrator_gate(
    mini_workflow_repo: Path,
) -> None:
    merged, before, after = merge_agent_evaluator_into_profile_document(
        mini_workflow_repo,
        "demo",
        {"enabled": True, "persona_id": "  custom  "},
    )
    assert merged["version"] == 99
    assert merged["integrator_gate"]["enabled"] is True
    assert merged["agent_evaluator"]["enabled"] is True
    assert merged["agent_evaluator"]["persona_id"] == "custom"
    assert merged["agent_evaluator"]["auto_promote_probation"] is False
    assert merged["agent_evaluator"]["auto_create_persona"] == {
        "enabled": False,
        "shelf": "",
        "display_name": "",
    }
    assert before is not None and before["persona_id"] == "legacy-ae"
    assert after == {
        "enabled": True,
        "persona_id": "custom",
        "auto_promote_probation": False,
        "auto_create_persona": {
            "enabled": False,
            "shelf": "",
            "display_name": "",
        },
    }


def test_prepare_agent_evaluator_apply_normalizes_flat_map(
    mini_workflow_repo: Path,
) -> None:
    merged, _b, after, errs = prepare_agent_evaluator_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="enabled: 1\n",
    )
    assert not errs
    assert merged is not None
    assert after == {
        "enabled": True,
        "persona_id": "default",
        "auto_promote_probation": False,
        "auto_create_persona": {
            "enabled": False,
            "shelf": "",
            "display_name": "",
        },
    }


def test_prepare_agent_evaluator_apply_unknown_key(mini_workflow_repo: Path) -> None:
    merged, _b, _a, errs = prepare_agent_evaluator_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="agent_evaluator:\n  enabled: true\n  foo: bar\n",
    )
    assert merged is None
    assert any("unknown keys" in e for e in errs)


def test_prepare_agent_evaluator_apply_bad_persona_type(
    mini_workflow_repo: Path,
) -> None:
    merged, _b, _a, errs = prepare_agent_evaluator_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="persona_id: [x]\n",
    )
    assert merged is None
    assert errs


def test_apply_agent_evaluator_yaml_requires_env(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, raising=False)
    ok, _doc, errs = apply_agent_evaluator_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="enabled: true\npersona_id: z\n",
        confirm_profile_stem="demo",
    )
    assert ok is False
    assert any(ALLOW_WORKFLOW_YAML_WRITE_ENV in e for e in errs)


def test_apply_agent_evaluator_yaml_confirmation_mismatch(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, "1")
    ok, _doc, errs = apply_agent_evaluator_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="enabled: true\npersona_id: z\n",
        confirm_profile_stem="not-demo",
    )
    assert ok is False
    assert any("confirmation" in e.lower() for e in errs)


def test_apply_agent_evaluator_yaml_writes_and_round_trips(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, "1")
    wf_path = mini_workflow_repo / "configs" / "workflows" / "demo.yaml"
    ok, merged, errs = apply_agent_evaluator_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="agent_evaluator:\n  enabled: true\n  persona_id: roundtrip-id\n",
        confirm_profile_stem="demo",
    )
    assert ok and not errs
    assert merged is not None
    assert merged["agent_evaluator"]["persona_id"] == "roundtrip-id"
    disk = load_yaml(wf_path)
    assert disk["integrator_gate"]["min_score_to_pass"] == pytest.approx(0.5)
    block = parse_agent_evaluator_workflow_block(mini_workflow_repo, "demo")
    assert block.enabled is True
    assert block.persona_id == "roundtrip-id"
