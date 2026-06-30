from __future__ import annotations

from dataclasses import dataclass

from nimbusware_console.explainer_core.workflow_exports import (
    WorkflowExplainerExports,
    install_named_workflow_explainer_exports,
)

EXPORT_INSTALL_MARKER = "# workflow-explainer-exports"


def codegen_install_line(slug: str) -> str:
    return (
        f'install_package_workflow_explainer_exports(globals(), "{slug}")'
        f"  {EXPORT_INSTALL_MARKER}\n"
    )


def codegen_install_block(slug: str) -> str:
    return codegen_install_line(slug)


@dataclass(frozen=True)
class WorkflowExplainerSpec:
    slug: str
    package: str


def explainer_metrics_prefix(slug: str) -> str:
    if slug == "integrator_threshold":
        return "integrator_threshold_explainer"
    return f"{slug}_workflow_explainer"


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
