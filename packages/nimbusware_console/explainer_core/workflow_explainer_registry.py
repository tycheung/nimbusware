from __future__ import annotations

from dataclasses import dataclass

from nimbusware_console.explainer_core.workflow_exports import (
    WorkflowExplainerExports,
    install_named_workflow_explainer_exports,
)

CODEGEN_BLOCK_START = "# codegen: workflow_explainer_exports begin"
CODEGEN_BLOCK_END = "# codegen: workflow_explainer_exports end"


@dataclass(frozen=True)
class WorkflowExplainerSpec:
    slug: str
    package: str


WORKFLOW_EXPLAINER_SPECS: tuple[WorkflowExplainerSpec, ...] = (
    WorkflowExplainerSpec("agent_evaluator", "agent_evaluator_workflow_explainer"),
    WorkflowExplainerSpec(
        "integration_adapter_writer",
        "integration_adapter_writer_workflow_explainer",
    ),
    WorkflowExplainerSpec("universal_critique", "universal_critique_workflow_explainer"),
    WorkflowExplainerSpec(
        "security_scan_metadata",
        "security_scan_metadata_workflow_explainer",
    ),
    WorkflowExplainerSpec("escalation_suppress", "escalation_suppress_workflow_explainer"),
    WorkflowExplainerSpec("self_refinement", "self_refinement_workflow_explainer"),
    WorkflowExplainerSpec("integrator_threshold", "integrator_threshold_explainer"),
)


def install_package_workflow_explainer_exports(
    namespace: dict[str, object],
    slug: str,
) -> WorkflowExplainerExports:
    return install_named_workflow_explainer_exports(namespace, slug)


def codegen_install_block(slug: str) -> str:
    return (
        f"{CODEGEN_BLOCK_START}\n"
        f'install_package_workflow_explainer_exports(globals(), "{slug}")\n'
        f"{CODEGEN_BLOCK_END}\n"
    )
