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
    WorkflowExplainerSpec("agent_evaluator", "workflow_explainers/agent_evaluator"),
    WorkflowExplainerSpec(
        "integration_adapter_writer",
        "workflow_explainers/integration_adapter_writer",
    ),
    WorkflowExplainerSpec("universal_critique", "workflow_explainers/universal_critique"),
    WorkflowExplainerSpec(
        "security_scan_metadata",
        "workflow_explainers/security_scan_metadata",
    ),
    WorkflowExplainerSpec("escalation_suppress", "workflow_explainers/escalation_suppress"),
    WorkflowExplainerSpec("self_refinement", "workflow_explainers/self_refinement"),
    WorkflowExplainerSpec("integrator_threshold", "workflow_explainers/integrator_threshold"),
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
