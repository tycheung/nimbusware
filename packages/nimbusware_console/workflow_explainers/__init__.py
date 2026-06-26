"""Unified workflow explainer packages (operator metrics + YAML payload introspection)."""

from nimbusware_console.explainer_core.workflow_explainer_registry import (
    WORKFLOW_EXPLAINER_SPECS,
    WorkflowExplainerSpec,
    codegen_install_block,
    install_package_workflow_explainer_exports,
)

__all__ = [
    "WORKFLOW_EXPLAINER_SPECS",
    "WorkflowExplainerSpec",
    "codegen_install_block",
    "install_package_workflow_explainer_exports",
]
