from __future__ import annotations

from pathlib import Path

from config.resolved_config import (
    ResolvedConfig,
    effective_universal_critique_from_resolved,
    resolve_run_config,
)
from env import find_repo_root
from orchestrator.workflow.profiles import workflow_profile_dict
from orchestrator.workflow.universal_critique import effective_universal_critique


def test_resolve_run_config_security_critique_on() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    resolved = resolve_run_config(root, "security_critique_on")
    assert isinstance(resolved, ResolvedConfig)
    assert resolved.workflow_profile == "security_critique_on"
    assert resolved.workflow_dict["security_critique"]["enabled"] is True
    assert any("extends:" in step for step in resolved.trace)
    assert any("fragments/security_critique" in step for step in resolved.trace)
    assert resolved.trace[-1] == "yaml:resolved profile=security_critique_on"


def test_resolve_run_config_matches_workflow_profile_dict() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    resolved = resolve_run_config(root, "performance_critique_on")
    direct = workflow_profile_dict(root, "performance_critique_on")
    assert resolved.workflow_dict == direct


def test_effective_universal_critique_from_resolved() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    resolved = resolve_run_config(root, "security_critique_on")
    via_resolved = effective_universal_critique_from_resolved(resolved)
    direct = effective_universal_critique(
        root,
        "security_critique_on",
        resolved_config=resolved,
    )
    assert via_resolved == direct
    assert via_resolved.default_enabled is True


def test_resolve_run_config_env_default_profile(monkeypatch) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    monkeypatch.delenv("NIMBUSWARE_WORKFLOW_PROFILE", raising=False)
    monkeypatch.delenv("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", raising=False)
    resolved = resolve_run_config(root, None)
    assert resolved.workflow_profile == "micro_slice"
    assert any(step.startswith("default:") for step in resolved.trace)
