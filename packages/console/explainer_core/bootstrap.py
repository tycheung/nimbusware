from __future__ import annotations

import importlib

from console.explainer_core.generic_workflow_explainer import install_explainer_metrics
from console.explainer_core.workflow_explainer_registry import (
    WORKFLOW_EXPLAINER_SPECS,
    install_package_workflow_explainer_exports,
)


def bootstrap_standard_explainer(slug: str, namespace: dict[str, object]) -> None:
    install_explainer_metrics(slug, namespace)
    install_package_workflow_explainer_exports(namespace, slug)  # workflow-explainer-exports


def load_all_workflow_explainers() -> None:
    for spec in WORKFLOW_EXPLAINER_SPECS:
        module = f"console.{spec.package.replace('/', '.')}"
        importlib.import_module(module)
