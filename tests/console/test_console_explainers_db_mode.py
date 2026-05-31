"""Console explainers read workflow/T2 config from materializer in DB mode (P0-h)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo, seed_t2_policy_documents_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_console.agent_evaluator_workflow_explainer import (
    agent_evaluator_workflow_explainer_payload,
)
from nimbusware_console.escalation_suppress_workflow_explainer import (
    escalation_suppress_workflow_explainer_payload,
)
from nimbusware_console.integrator_threshold_explainer import integrator_threshold_explainer_payload
from nimbusware_console.security_scan_metadata_workflow_explainer import (
    security_scan_metadata_workflow_explainer_payload,
)
from nimbusware_console.self_refinement_workflow_explainer import (
    self_refinement_workflow_explainer_payload,
)
from nimbusware_env import find_repo_root


def _db_materializer(root: Path, tmp_path: Path) -> ConfigMaterializer:
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    seed_t2_policy_documents_from_repo(root, store)
    return ConfigMaterializer(tmp_path, store=store, use_db=True)


def _patch_console_materializer(
    monkeypatch: pytest.MonkeyPatch,
    mat: ConfigMaterializer,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_CONFIG_FROM_DB", "1")
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://test")
    import nimbusware_console.config_materializer as cm

    monkeypatch.setattr(cm, "ConfigMaterializer", lambda repo: mat)


def test_integrator_threshold_explainer_db_mode_without_workflow_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    mat = _db_materializer(root, tmp_path)
    _patch_console_materializer(monkeypatch, mat)
    wf_path = tmp_path / "configs" / "workflows" / "default.yaml"
    assert not wf_path.is_file()

    payload = integrator_threshold_explainer_payload(
        tmp_path,
        workflow_profile="default",
        pasted_yaml="",
    )
    assert payload.get("load_error") is None or payload.get("workflow_profile") == "default"
    thr = payload.get("thresholds_yaml")
    assert isinstance(thr, dict)
    assert thr.get("source") == "materializer"
    assert thr.get("exists") is True
    gate = payload.get("workflow_integrator_gate")
    assert isinstance(gate, dict)


def test_security_scan_explainer_db_mode_without_workflow_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    mat = _db_materializer(root, tmp_path)
    _patch_console_materializer(monkeypatch, mat)

    payload = security_scan_metadata_workflow_explainer_payload(
        tmp_path,
        workflow_profile="default",
    )
    assert payload.get("workflow_profile") == "default"
    assert payload.get("load_error") is None
    assert "yaml_parsed_bool" in payload
    assert "effective_enabled" in payload


def test_escalation_suppress_explainer_db_mode_without_workflow_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    mat = _db_materializer(root, tmp_path)
    _patch_console_materializer(monkeypatch, mat)

    payload = escalation_suppress_workflow_explainer_payload(
        tmp_path,
        workflow_profile="escalation_suppress_on",
    )
    assert payload.get("workflow_profile") == "escalation_suppress_on"
    assert payload.get("load_error") is None
    assert payload.get("suppress_automatic_escalation_effective") is True


def test_self_refinement_explainer_db_mode_without_workflow_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    mat = _db_materializer(root, tmp_path)
    _patch_console_materializer(monkeypatch, mat)

    payload = self_refinement_workflow_explainer_payload(
        tmp_path,
        workflow_profile="self_refinement_on",
    )
    assert payload.get("workflow_profile") == "self_refinement_on"
    assert payload.get("load_error") is None
    pol = payload.get("policy_yaml")
    assert isinstance(pol, dict)
    assert pol.get("source") == "materializer"
    wf = payload.get("workflow_self_refinement")
    assert isinstance(wf, dict)
    assert wf.get("enabled") is True


def test_agent_evaluator_explainer_db_mode_without_workflow_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    mat = _db_materializer(root, tmp_path)
    _patch_console_materializer(monkeypatch, mat)

    payload = agent_evaluator_workflow_explainer_payload(
        tmp_path,
        workflow_profile="agent_evaluator_on",
    )
    assert payload.get("workflow_profile") == "agent_evaluator_on"
    assert payload.get("load_error") is None
    assert payload.get("yaml_parsed_enabled") is True
