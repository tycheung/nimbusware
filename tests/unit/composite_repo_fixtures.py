from __future__ import annotations

from pathlib import Path


def write_config_yaml(repo: Path, *rel_parts: str, body: str) -> Path:
    if len(rel_parts) < 2:
        raise ValueError("write_config_yaml requires at least a directory and filename")
    path = repo.joinpath(*rel_parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def write_workflow_profile(repo: Path, name: str, body: str) -> Path:
    return write_config_yaml(repo, "configs", "workflows", f"{name}.yaml", body=body)


def write_integrator_thresholds(repo: Path, body: str) -> Path:
    return write_config_yaml(repo, "configs", "integrator", "thresholds.yaml", body=body)


def write_escalation_policy(repo: Path, body: str) -> Path:
    return write_config_yaml(repo, "configs", "escalation", "policy.yaml", body=body)


def write_critique_pairings(repo: Path, body: str) -> Path:
    return write_config_yaml(repo, "configs", "personas", "critique_pairings.yaml", body=body)


def write_workflow_integrator_min_score(repo: Path, name: str, value: str) -> Path:
    body = f"version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: {value}\n"
    return write_workflow_profile(repo, name, body)
