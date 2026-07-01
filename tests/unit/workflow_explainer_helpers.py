from __future__ import annotations

from pathlib import Path
from typing import Any

from unit.composite_repo_fixtures import write_workflow_profile

_POLICY_AND_WORKFLOW_POLICY_TEXT = 'version: 1\nenabled: false\ndescription: "from disk policy"\n'


def write_escalation_policy(tmp_path: Path, yaml_body: str) -> None:
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    (pol_dir / "policy.yaml").write_text(yaml_body, encoding="utf-8")


def build_universal_critique_stub_repo(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "stub.yaml").write_text(
        "version: 1\n"
        "universal_critique:\n"
        "  implementation:\n"
        "    llm: false\n"
        "    stub: true\n"
        "  test_writer:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "    stub: true\n"
        "  planner:\n"
        "    enabled: false\n"
        "  frontend_writer:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "    stub: true\n"
        "  module_integrator:\n"
        "    enabled: true\n"
        "    llm: false\n"
        "    stub: true\n",
        encoding="utf-8",
    )
    return tmp_path


def build_self_refinement_repo(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "self_refinement").mkdir(parents=True)
    (tmp_path / "configs" / "self_refinement" / "policy.yaml").write_text(
        _POLICY_AND_WORKFLOW_POLICY_TEXT,
        encoding="utf-8",
    )
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "on.yaml").write_text(
        "version: 1\nself_refinement:\n  enabled: true\n  version: 9\n",
        encoding="utf-8",
    )
    return tmp_path


def explainer_payload_for_slug(
    repo_root: Path,
    slug: str,
    workflow_profile: str,
    *,
    workflow_yaml: str | None = None,
) -> dict[str, Any]:
    if workflow_yaml is not None:
        write_workflow_profile(repo_root, workflow_profile, workflow_yaml)
    if slug == "agent_evaluator":
        from nimbusware_console.workflow_explainers.agent_evaluator import (
            agent_evaluator_workflow_explainer_payload,
        )

        return agent_evaluator_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
    if slug == "escalation_suppress":
        from nimbusware_console.workflow_explainers.escalation_suppress import (
            escalation_suppress_workflow_explainer_payload,
        )

        return escalation_suppress_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
    if slug == "universal_critique":
        from nimbusware_console.workflow_explainers.universal_critique import (
            universal_critique_workflow_explainer_payload,
        )

        return universal_critique_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
    if slug == "security_scan_metadata":
        from nimbusware_console.workflow_explainers.security_scan_metadata import (
            security_scan_metadata_workflow_explainer_payload,
        )

        return security_scan_metadata_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
    if slug == "self_refinement":
        from nimbusware_console.workflow_explainers.self_refinement import (
            self_refinement_workflow_explainer_payload,
        )

        return self_refinement_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
    raise ValueError(f"unsupported explainer slug: {slug}")


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
    return escalation_suppress_workflow_explainer_payload(
        tmp_path, workflow_profile=workflow_profile
    )
