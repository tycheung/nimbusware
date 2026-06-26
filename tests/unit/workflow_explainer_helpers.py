from __future__ import annotations

from pathlib import Path

from unit.composite_repo_fixtures import write_workflow_profile


def write_escalation_policy(tmp_path: Path, yaml_body: str) -> None:
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / "policy.yaml").write_text(yaml_body, encoding="utf-8")


def escalation_explainer_payload(
    tmp_path: Path,
    *,
    workflow_yaml: str = "version: 1\n",
    workflow_profile: str = "wf",
    policy_yaml: str | None = None,
):
    from nimbusware_console.workflow_explainers.escalation_suppress import (
        escalation_suppress_workflow_explainer_payload,
    )

    write_workflow_profile(tmp_path, workflow_profile, workflow_yaml)
    if policy_yaml is not None:
        write_escalation_policy(tmp_path, policy_yaml)
    return escalation_suppress_workflow_explainer_payload(tmp_path, workflow_profile=workflow_profile)
